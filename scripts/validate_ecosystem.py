#!/usr/bin/env python3
"""Validate the RenCrow ecosystem manifest without third-party dependencies."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


COMPONENT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
COMMIT_VERSION_PATTERN = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_COMPATIBILITY_STATUSES = {"unpinned", "source-pinned", "verified"}
ALLOWED_DISTRIBUTIONS = {
    "binary",
    "extension",
    "offline-assets",
    "service",
    "snapshot",
    "template",
    "tooling",
}
ALLOWED_RUNTIME_IMPLEMENTATIONS = {"go", "python", "javascript", "mixed"}
ALLOWED_RUNTIME_STATUSES = {"planned", "development", "available"}
ALLOWED_COMPANION_KINDS = {
    "external-compute",
    "system-service",
}
ARTIFACT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
WORKSPACE_PATH_PATTERN = re.compile(r"^\./[A-Za-z0-9][A-Za-z0-9._-]*$")
USER_SYSTEMD_UNIT_PATTERN = re.compile(r"^rencrow[A-Za-z0-9_.@:-]*\.service$")
JSON_PATH_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
DEPLOYMENT_SOURCE_PATH_PATTERN = re.compile(r"^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_PRIMARY_RUNTIME_FIELDS = {"implementation", "artifact", "status"}
REQUIRED_COMPANION_RUNTIME_FIELDS = {
    "id",
    "kind",
    "required",
    "bundled",
    "role",
}
REQUIRED_COMPONENT_FIELDS = {
    "repository",
    "workspace_path",
    "version",
    "required",
    "distribution",
    "role",
}
REQUIRED_RUNTIME_PROFILE_FIELDS = {
    "owner_component",
    "repository",
    "workspace_path",
    "version",
    "required",
    "kind",
    "status",
    "role",
}
FORBIDDEN_KEY_PARTS = {"api_key", "password", "private_key", "secret", "token"}
GOVERNANCE_REQUIRED_FILES = ("AGENTS.md", "README.md")
CONCEPTUAL_INTEGRITY_REQUIRED_MARKERS = (
    "## Conceptual Integrity Guardrail v0.1",
    "### Hard Invariant",
    "### Architecture SmellとSemantic Duplication",
    "### Failure Knowledge",
    "### Architecture Reviewと再構築",
)
LOCAL_TEST_REQUIRED_FILES = (
    "scripts/test-local.ps1",
    "scripts/test-local.plan.json",
)
COVERAGE_POLICY_SCHEMA_VERSION = 2
GUARANTEE_CLASSES = (
    "source_identity",
    "artifact_identity",
    "runtime_identity",
    "readiness",
    "canonical_e2e",
    "actor_result",
    "receipt_trace",
    "security_exposure",
    "durability",
    "lifecycle",
    "publication",
)
CROSS_SYSTEM_REQUIREMENTS = (
    "browser_ui",
    "route_security_exposure",
    "backup_restore",
    "lifecycle_resources",
    "publication",
)
COVERAGE_POLICY_FIELDS = {
    "schema_version",
    "guarantee_classes",
    "required_phases",
    "component_requirements",
    "temporarily_excluded_components",
    "cross_system_requirements",
}
REQUIRED_FULL_SYSTEM_PHASES = (
    "startup",
    "runtime",
    "deploy",
    "backup",
    "diagnostic",
)
COVERAGE_POLICY_FORBIDDEN_KEY_PARTS = {
    "command",
    "commands",
    "port",
    "ports",
    "endpoint",
    "endpoints",
    "test",
    "tests",
    "executor",
    "execution",
    "script",
    "url",
}


class ManifestError(ValueError):
    """Raised when the ecosystem manifest violates its contract."""


def load_manifest(path: Path) -> dict[str, Any]:
    """Load the JSON-compatible YAML 1.2 manifest."""
    try:
        with path.open(encoding="utf-8") as manifest_file:
            data = json.load(manifest_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot load {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ManifestError("manifest root must be an object")
    return data


def load_coverage_policy(path: Path) -> dict[str, Any]:
    """Load the catalog-level full-system coverage policy."""
    try:
        with path.open(encoding="utf-8") as policy_file:
            data = json.load(policy_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot load coverage policy {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ManifestError("coverage policy root must be an object")
    return data


def _reject_secret_keys(value: Any, location: str = "manifest") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = str(key).lower()
            if any(part in normalized_key for part in FORBIDDEN_KEY_PARTS):
                raise ManifestError(f"secret-like key is forbidden at {location}.{key}")
            _reject_secret_keys(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secret_keys(child, f"{location}[{index}]")


def _reject_coverage_operational_keys(
    value: Any, location: str = "coverage policy"
) -> None:
    """Keep operational commands and module-level check details out of policy."""
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = str(key).lower().replace("-", "_")
            key_parts = set(normalized_key.split("_"))
            if key_parts & COVERAGE_POLICY_FORBIDDEN_KEY_PARTS:
                raise ManifestError(
                    "coverage policy contains operational detail key at "
                    f"{location}.{key}"
                )
            _reject_coverage_operational_keys(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_coverage_operational_keys(child, f"{location}[{index}]")


def _validate_coverage_class_list(
    raw_classes: Any,
    location: str,
    known_classes: set[str],
) -> list[str]:
    if not isinstance(raw_classes, list):
        raise ManifestError(f"{location} must be an array of guarantee classes")
    if not raw_classes:
        raise ManifestError(f"{location} must be non-empty")

    seen: set[str] = set()
    validated: list[str] = []
    for index, class_id in enumerate(raw_classes):
        class_location = f"{location}[{index}]"
        if not isinstance(class_id, str) or not class_id.strip():
            raise ManifestError(f"{class_location} must not be an empty guarantee class")
        if class_id not in known_classes:
            raise ManifestError(
                f"{class_location} contains unknown guarantee class: {class_id}"
            )
        if class_id in seen:
            raise ManifestError(
                f"{location} contains duplicate guarantee class: {class_id}"
            )
        seen.add(class_id)
        validated.append(class_id)
    return validated


def validate_coverage_policy(
    policy: dict[str, Any], manifest: dict[str, Any]
) -> None:
    """Validate catalog-wide guarantee classes and component coverage declarations."""
    if not isinstance(policy, dict):
        raise ManifestError("coverage policy root must be an object")
    if not isinstance(manifest, dict):
        raise ManifestError("manifest root must be an object")
    _reject_secret_keys(policy, "coverage policy")
    _reject_coverage_operational_keys(policy)

    if (
        type(policy.get("schema_version")) is not int
        or policy["schema_version"] != COVERAGE_POLICY_SCHEMA_VERSION
    ):
        raise ManifestError(
            "coverage policy schema_version must be "
            f"{COVERAGE_POLICY_SCHEMA_VERSION}"
        )

    missing_fields = COVERAGE_POLICY_FIELDS - policy.keys()
    if missing_fields:
        raise ManifestError(
            "coverage policy missing fields: " + ", ".join(sorted(missing_fields))
        )
    unsupported_fields = policy.keys() - COVERAGE_POLICY_FIELDS
    if unsupported_fields:
        raise ManifestError(
            "coverage policy contains unsupported fields: "
            + ", ".join(sorted(unsupported_fields))
        )

    known_classes = set(GUARANTEE_CLASSES)
    declared_classes = _validate_coverage_class_list(
        policy["guarantee_classes"], "coverage policy.guarantee_classes", known_classes
    )
    if set(declared_classes) != known_classes:
        missing_classes = known_classes - set(declared_classes)
        if missing_classes:
            raise ManifestError(
                "coverage policy missing guarantee class: "
                + ", ".join(sorted(missing_classes))
            )

    required_phases = policy["required_phases"]
    if not isinstance(required_phases, list) or required_phases != list(
        REQUIRED_FULL_SYSTEM_PHASES
    ):
        raise ManifestError(
            "coverage policy.required_phases must exactly match the canonical phase order"
        )

    manifest_components = manifest.get("components")
    if not isinstance(manifest_components, dict) or not manifest_components:
        raise ManifestError("manifest components must be a non-empty object")

    component_requirements = policy["component_requirements"]
    if not isinstance(component_requirements, dict) or not component_requirements:
        raise ManifestError(
            "coverage policy.component_requirements must be a non-empty object"
        )

    manifest_component_ids = set(manifest_components)
    requirement_component_ids = set(component_requirements)
    missing_components = manifest_component_ids - requirement_component_ids
    if missing_components:
        raise ManifestError(
            "coverage policy component_requirements missing component: "
            + ", ".join(sorted(missing_components))
        )
    extra_components = requirement_component_ids - manifest_component_ids
    if extra_components:
        raise ManifestError(
            "coverage policy component_requirements has extra component: "
            + ", ".join(sorted(extra_components))
        )

    requirement_sets: set[frozenset[str]] = set()
    for component_id in sorted(manifest_component_ids):
        classes = _validate_coverage_class_list(
            component_requirements[component_id],
            f"coverage policy.component_requirements.{component_id}",
            known_classes,
        )
        requirement_sets.add(frozenset(classes))
    if len(requirement_sets) < 2:
        raise ManifestError(
            "coverage policy component requirements must vary by component type"
        )

    exclusions = policy["temporarily_excluded_components"]
    if not isinstance(exclusions, dict):
        raise ManifestError(
            "coverage policy.temporarily_excluded_components must be an object"
        )
    extra_exclusions = set(exclusions) - manifest_component_ids
    if extra_exclusions:
        raise ManifestError(
            "coverage policy.temporarily_excluded_components has extra component: "
            + ", ".join(sorted(extra_exclusions))
        )
    for component_id, exclusion in sorted(exclusions.items()):
        location = (
            "coverage policy.temporarily_excluded_components." + component_id
        )
        if not isinstance(exclusion, dict) or set(exclusion) != {
            "reason",
            "reinclude_when",
        }:
            raise ManifestError(
                f"{location} must contain exactly reason and reinclude_when"
            )
        if exclusion["reason"] != "required_component_unimplemented":
            raise ManifestError(
                f"{location}.reason must be required_component_unimplemented"
            )
        if exclusion["reinclude_when"] != "canonical_runtime_implemented":
            raise ManifestError(
                f"{location}.reinclude_when must be canonical_runtime_implemented"
            )
        if manifest_components[component_id].get("required") is not True:
            raise ManifestError(
                f"{location} is valid only for a required component"
            )

    cross_system_requirements = policy["cross_system_requirements"]
    if not isinstance(cross_system_requirements, dict) or not cross_system_requirements:
        raise ManifestError(
            "coverage policy.cross_system_requirements must be a non-empty object"
        )
    expected_cross_ids = set(CROSS_SYSTEM_REQUIREMENTS)
    declared_cross_ids = set(cross_system_requirements)
    missing_cross_ids = expected_cross_ids - declared_cross_ids
    if missing_cross_ids:
        raise ManifestError(
            "coverage policy.cross_system_requirements missing requirement: "
            + ", ".join(sorted(missing_cross_ids))
        )
    extra_cross_ids = declared_cross_ids - expected_cross_ids
    if extra_cross_ids:
        raise ManifestError(
            "coverage policy.cross_system_requirements has extra requirement: "
            + ", ".join(sorted(extra_cross_ids))
        )
    for requirement_id in CROSS_SYSTEM_REQUIREMENTS:
        _validate_coverage_class_list(
            cross_system_requirements[requirement_id],
            f"coverage policy.cross_system_requirements.{requirement_id}",
            known_classes,
        )


def _validate_workspace_path(location: str, raw_path: Any) -> None:
    if not isinstance(raw_path, str) or not WORKSPACE_PATH_PATTERN.fullmatch(raw_path):
        raise ManifestError(
            f"{location}.workspace_path must be a direct child path in the form ./Name"
        )


def _validate_runtime(component_id: str, component: dict[str, Any]) -> None:
    runtime = component.get("runtime")
    if runtime is None:
        return
    if not isinstance(runtime, dict):
        raise ManifestError(f"components.{component_id}.runtime must be an object")

    primary = runtime.get("primary")
    if not isinstance(primary, dict):
        raise ManifestError(
            f"components.{component_id}.runtime.primary must be an object"
        )
    missing_primary = REQUIRED_PRIMARY_RUNTIME_FIELDS - primary.keys()
    if missing_primary:
        missing = ", ".join(sorted(missing_primary))
        raise ManifestError(
            f"components.{component_id}.runtime.primary missing fields: {missing}"
        )

    implementation = primary["implementation"]
    if implementation not in ALLOWED_RUNTIME_IMPLEMENTATIONS:
        raise ManifestError(
            f"components.{component_id}.runtime.primary.implementation "
            "is not supported"
        )
    artifact = primary["artifact"]
    if not isinstance(artifact, str) or not ARTIFACT_NAME_PATTERN.fullmatch(artifact):
        raise ManifestError(
            f"components.{component_id}.runtime.primary.artifact is invalid"
        )
    if primary["status"] not in ALLOWED_RUNTIME_STATUSES:
        raise ManifestError(
            f"components.{component_id}.runtime.primary.status is not supported"
        )
    if implementation == "go" and component["distribution"] != "binary":
        raise ManifestError(
            f"components.{component_id} with a Go primary runtime must use "
            "binary distribution"
        )

    companions = runtime.get("companions", [])
    if not isinstance(companions, list):
        raise ManifestError(
            f"components.{component_id}.runtime.companions must be an array"
        )

    companion_ids: set[str] = set()
    for index, companion in enumerate(companions):
        location = f"components.{component_id}.runtime.companions[{index}]"
        if not isinstance(companion, dict):
            raise ManifestError(f"{location} must be an object")
        missing_companion = REQUIRED_COMPANION_RUNTIME_FIELDS - companion.keys()
        if missing_companion:
            missing = ", ".join(sorted(missing_companion))
            raise ManifestError(f"{location} missing fields: {missing}")

        companion_id = companion["id"]
        if not isinstance(companion_id, str) or not COMPONENT_ID_PATTERN.fullmatch(
            companion_id
        ):
            raise ManifestError(f"{location}.id is invalid")
        if companion_id in companion_ids:
            raise ManifestError(
                f"components.{component_id}.runtime has duplicate companion: "
                f"{companion_id}"
            )
        companion_ids.add(companion_id)

        if companion["kind"] not in ALLOWED_COMPANION_KINDS:
            raise ManifestError(f"{location}.kind is not supported")
        if not isinstance(companion["required"], bool):
            raise ManifestError(f"{location}.required must be boolean")
        if not isinstance(companion["bundled"], bool):
            raise ManifestError(f"{location}.bundled must be boolean")
        if not isinstance(companion["role"], str) or not companion["role"].strip():
            raise ManifestError(f"{location}.role must be non-empty")
        if companion["kind"] == "external-compute" and companion["bundled"]:
            raise ManifestError(f"{location} external-compute cannot be bundled")


def _readiness_error(location: str, message: str) -> ManifestError:
    return ManifestError(f"{location} readiness contract {message}")


def _is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _validate_readiness_url(location: str, raw_url: Any) -> None:
    if not isinstance(raw_url, str) or not raw_url.strip():
        raise _readiness_error(location, "url must be a non-empty absolute URL")
    try:
        parsed = urlsplit(raw_url)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError as exc:
        raise _readiness_error(location, f"url is invalid: {exc}") from exc
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not hostname:
        raise _readiness_error(location, "url must be an absolute http(s) URL")
    if parsed.username is not None or parsed.password is not None:
        raise _readiness_error(location, "url must not contain userinfo")
    if parsed.query or parsed.fragment or "?" in raw_url or "#" in raw_url:
        raise _readiness_error(location, "url must not contain query or fragment")
    if not _is_loopback_host(hostname):
        raise _readiness_error(location, "url host must be localhost or loopback")


def _validate_scalar(location: str, value: Any) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float) and math.isfinite(value):
        return
    raise _readiness_error(location, "expect.equals must be a JSON scalar")


def _validate_user_systemd_deployment(
    component_id: str,
    component: dict[str, Any],
    global_units: set[str],
) -> None:
    deployment = component.get("deployment")
    if deployment is None:
        return
    location = f"components.{component_id}.deployment"
    if not isinstance(deployment, dict):
        raise _readiness_error(location, "must be an object")
    if not deployment or not set(deployment) <= {"user_systemd", "files"}:
        raise _readiness_error(location, "contains unsupported keys")

    files = deployment.get("files", [])
    if not isinstance(files, list):
        raise ManifestError(f"{location}.files must be an array")
    for index, artifact in enumerate(files):
        artifact_location = f"{location}.files[{index}]"
        if not isinstance(artifact, dict) or set(artifact) != {
            "source_path", "installed_path", "sha256", "mode"
        }:
            raise ManifestError(f"{artifact_location} must contain exactly source_path, installed_path, sha256, mode")
        source = artifact["source_path"]
        if not isinstance(source, str) or not DEPLOYMENT_SOURCE_PATH_PATTERN.fullmatch(source) or ".." in source.split("/"):
            raise ManifestError(f"{artifact_location}.source_path must be a safe relative POSIX path")
        installed = artifact["installed_path"]
        if not isinstance(installed, str) or not installed.startswith(("%h/", "%workspace%/")):
            raise ManifestError(f"{artifact_location}.installed_path must start with %h/ or %workspace%/")
        if not isinstance(artifact["sha256"], str) or not SHA256_PATTERN.fullmatch(artifact["sha256"]):
            raise ManifestError(f"{artifact_location}.sha256 must be lowercase SHA-256")
        if artifact["mode"] not in {"0644", "0755"}:
            raise ManifestError(f"{artifact_location}.mode must be 0644 or 0755")

    contracts = deployment.get("user_systemd", [])
    if not isinstance(contracts, list):
        raise _readiness_error(f"{location}.user_systemd", "must be an array")

    local_units: set[str] = set()
    for index, contract in enumerate(contracts):
        contract_location = f"{location}.user_systemd[{index}]"
        if not isinstance(contract, dict):
            raise _readiness_error(contract_location, "must be an object")
        if "unit" not in contract or "kind" not in contract:
            raise _readiness_error(contract_location, "must contain unit and kind")

        unit = contract["unit"]
        if not isinstance(unit, str) or not USER_SYSTEMD_UNIT_PATTERN.fullmatch(unit):
            raise _readiness_error(contract_location, "unit must match rencrow*.service")
        if unit in local_units or unit in global_units:
            raise ManifestError(f"duplicate user systemd unit: {unit}")
        local_units.add(unit)
        global_units.add(unit)

        kind = contract["kind"]
        if kind == "oneshot":
            if set(contract) != {"unit", "kind"}:
                raise _readiness_error(contract_location, "oneshot contains unsupported keys")
            continue
        if kind != "http_json":
            raise _readiness_error(contract_location, "kind must be http_json or oneshot")
        if set(contract) != {"unit", "kind", "url", "timeout_seconds", "expect"}:
            raise _readiness_error(contract_location, "contains unsupported keys")

        _validate_readiness_url(contract_location, contract["url"])
        timeout = contract["timeout_seconds"]
        if type(timeout) is not int or not 1 <= timeout <= 600:
            raise _readiness_error(contract_location, "timeout_seconds must be an integer from 1 to 600")

        expect = contract["expect"]
        if not isinstance(expect, dict) or set(expect) != {"path", "equals"}:
            raise _readiness_error(contract_location, "expect must contain exactly path and equals")
        path = expect["path"]
        if not isinstance(path, str) or not JSON_PATH_PATTERN.fullmatch(path):
            raise _readiness_error(contract_location, "expect.path must be a dotted JSON path")
        _validate_scalar(contract_location, expect["equals"])


def validate_manifest(data: dict[str, Any]) -> None:
    """Validate structure, uniqueness, release state, and safe metadata."""
    _reject_secret_keys(data)

    if data.get("schema_version") != 4:
        raise ManifestError("schema_version must be 4")

    ecosystem = data.get("ecosystem")
    if not isinstance(ecosystem, dict):
        raise ManifestError("ecosystem must be an object")
    for field in ("name", "release", "compatibility_status"):
        if not isinstance(ecosystem.get(field), str) or not ecosystem[field].strip():
            raise ManifestError(f"ecosystem.{field} must be a non-empty string")
    compatibility_status = ecosystem["compatibility_status"]
    if compatibility_status not in ALLOWED_COMPATIBILITY_STATUSES:
        raise ManifestError("ecosystem.compatibility_status is not supported")

    components = data.get("components")
    if not isinstance(components, dict) or not components:
        raise ManifestError("components must be a non-empty object")

    repositories: set[str] = set()
    workspace_paths: set[str] = set()
    user_systemd_units: set[str] = set()
    unpinned_components: list[str] = []

    for component_id, component in components.items():
        if not COMPONENT_ID_PATTERN.fullmatch(component_id):
            raise ManifestError(f"invalid component id: {component_id}")
        if not isinstance(component, dict):
            raise ManifestError(f"components.{component_id} must be an object")

        missing_fields = REQUIRED_COMPONENT_FIELDS - component.keys()
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ManifestError(f"components.{component_id} missing fields: {missing}")

        repository = component["repository"]
        if not isinstance(repository, str) or not REPOSITORY_PATTERN.fullmatch(repository):
            raise ManifestError(f"components.{component_id}.repository is invalid")
        if repository in repositories:
            raise ManifestError(f"duplicate repository: {repository}")
        repositories.add(repository)

        workspace_path = component["workspace_path"]
        _validate_workspace_path(f"components.{component_id}", workspace_path)
        if workspace_path in workspace_paths:
            raise ManifestError(f"duplicate workspace_path: {workspace_path}")
        workspace_paths.add(workspace_path)

        version = component["version"]
        if not isinstance(version, str) or not version.strip():
            raise ManifestError(f"components.{component_id}.version must be non-empty")
        if version == "unpinned":
            unpinned_components.append(component_id)
        elif version == "planned":
            runtime = component.get("runtime")
            primary = runtime.get("primary", {}) if isinstance(runtime, dict) else {}
            if (
                component["required"]
                or not isinstance(primary, dict)
                or primary.get("status") != "planned"
            ):
                raise ManifestError(
                    f"components.{component_id}.version planned requires an "
                    "optional planned runtime"
                )
        elif (
            compatibility_status == "source-pinned"
            and not COMMIT_VERSION_PATTERN.fullmatch(version)
        ):
            raise ManifestError(
                f"components.{component_id}.version must be a full commit SHA "
                "for source-pinned compatibility"
            )

        if not isinstance(component["required"], bool):
            raise ManifestError(f"components.{component_id}.required must be boolean")
        if component["distribution"] not in ALLOWED_DISTRIBUTIONS:
            raise ManifestError(
                f"components.{component_id}.distribution is not supported"
            )
        if not isinstance(component["role"], str) or not component["role"].strip():
            raise ManifestError(f"components.{component_id}.role must be non-empty")
        _validate_runtime(component_id, component)
        _validate_user_systemd_deployment(
            component_id, component, user_systemd_units
        )

    core = components.get("core")
    if not isinstance(core, dict) or core.get("required") is not True:
        raise ManifestError("core must exist and be required")

    runtime_profiles = data.get("runtime_profiles")
    if not isinstance(runtime_profiles, dict) or not runtime_profiles:
        raise ManifestError("runtime_profiles must be a non-empty object")

    for profile_id, profile in runtime_profiles.items():
        location = f"runtime_profiles.{profile_id}"
        if not COMPONENT_ID_PATTERN.fullmatch(profile_id):
            raise ManifestError(f"invalid runtime profile id: {profile_id}")
        if not isinstance(profile, dict):
            raise ManifestError(f"{location} must be an object")

        missing_fields = REQUIRED_RUNTIME_PROFILE_FIELDS - profile.keys()
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ManifestError(f"{location} missing fields: {missing}")

        owner_component = profile["owner_component"]
        if owner_component not in components:
            raise ManifestError(
                f"{location}.owner_component must reference a component"
            )

        repository = profile["repository"]
        if not isinstance(repository, str) or not REPOSITORY_PATTERN.fullmatch(
            repository
        ):
            raise ManifestError(f"{location}.repository is invalid")
        if repository in repositories:
            raise ManifestError(f"duplicate repository: {repository}")
        repositories.add(repository)

        workspace_path = profile["workspace_path"]
        _validate_workspace_path(f"runtime_profiles.{profile_id}", workspace_path)
        if workspace_path in workspace_paths:
            raise ManifestError(f"duplicate workspace_path: {workspace_path}")
        workspace_paths.add(workspace_path)

        version = profile["version"]
        if not isinstance(version, str) or not version.strip():
            raise ManifestError(f"{location}.version must be non-empty")
        if version == "unpinned":
            unpinned_components.append(f"runtime-profile:{profile_id}")
        elif (
            compatibility_status == "source-pinned"
            and not COMMIT_VERSION_PATTERN.fullmatch(version)
        ):
            raise ManifestError(
                f"{location}.version must be a full commit SHA for "
                "source-pinned compatibility"
            )

        if not isinstance(profile["required"], bool):
            raise ManifestError(f"{location}.required must be boolean")
        if profile["kind"] != "external-compute":
            raise ManifestError(f"{location}.kind must be external-compute")
        if profile["status"] not in {"development", "available"}:
            raise ManifestError(f"{location}.status is not supported")
        if not isinstance(profile["role"], str) or not profile["role"].strip():
            raise ManifestError(f"{location}.role must be non-empty")

    if compatibility_status in {"source-pinned", "verified"} and unpinned_components:
        names = ", ".join(sorted(unpinned_components))
        raise ManifestError(
            f"{compatibility_status} manifest has unpinned components: {names}"
        )
    if ecosystem["release"] != "development" and unpinned_components:
        names = ", ".join(sorted(unpinned_components))
        raise ManifestError(f"released ecosystem has unpinned components: {names}")


def _git_head(component_path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(component_path), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git rev-parse failed"
        raise ManifestError(f"cannot read Git HEAD for {component_path}: {detail}")
    return result.stdout.strip().lower()


def _git_blob_sha256(component_path: Path, revision: str, source_path: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(component_path), "show", f"{revision}:{source_path}"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip() or "git show failed"
        raise ManifestError(f"cannot read managed file {source_path}: {detail}")
    return hashlib.sha256(result.stdout).hexdigest()


def validate_workspace(data: dict[str, Any], manifest_path: Path) -> None:
    """Check sibling repositories and source-pinned revisions in a local workspace."""
    base_directory = manifest_path.resolve().parent
    compatibility_status = data.get("ecosystem", {}).get("compatibility_status")
    entries = [
        ("components", component_id, component)
        for component_id, component in data["components"].items()
    ]
    entries.extend(
        ("runtime_profiles", profile_id, profile)
        for profile_id, profile in data.get("runtime_profiles", {}).items()
    )
    for section, entry_id, entry in entries:
        entry_path = (base_directory / entry["workspace_path"]).resolve()
        if not entry_path.is_dir():
            if entry.get("required") is False:
                continue
            raise ManifestError(
                f"{section}.{entry_id} workspace is missing: {entry_path}"
            )
        if not (entry_path / ".git").exists():
            raise ManifestError(
                f"{section}.{entry_id} is not a Git worktree: {entry_path}"
            )
        version = entry.get("version")
        if (
            compatibility_status == "source-pinned"
            and isinstance(version, str)
            and COMMIT_VERSION_PATTERN.fullmatch(version)
        ):
            head = _git_head(entry_path)
            if head != version:
                raise ManifestError(
                    f"{section}.{entry_id} HEAD {head} does not match "
                    f"source-pinned version {version}"
                )
        deployment = entry.get("deployment")
        managed_files = deployment.get("files", []) if isinstance(deployment, dict) else []
        if managed_files and isinstance(version, str) and COMMIT_VERSION_PATTERN.fullmatch(version):
            for artifact in managed_files:
                actual_hash = _git_blob_sha256(entry_path, version, artifact["source_path"])
                if actual_hash != artifact["sha256"]:
                    raise ManifestError(
                        f"{section}.{entry_id} managed file {artifact['source_path']} "
                        f"hash {actual_hash} does not match manifest {artifact['sha256']}"
                    )


def _require_non_empty_file(entry_id: str, entry_path: Path, relative: str) -> None:
    path = entry_path / relative
    if not path.is_file() or path.stat().st_size == 0:
        raise ManifestError(f"{entry_id} governance file is missing or empty: {path}")


def _has_ci_workflow(entry_path: Path) -> bool:
    workflows = entry_path / ".github" / "workflows"
    if not workflows.is_dir():
        return False
    return any(path.is_file() for pattern in ("*.yml", "*.yaml") for path in workflows.glob(pattern))


def _component_requires_test_contract(component: dict[str, Any]) -> bool:
    runtime = component.get("runtime")
    primary = runtime.get("primary", {}) if isinstance(runtime, dict) else {}
    if isinstance(primary, dict) and primary.get("status") == "planned":
        return False
    return component.get("distribution") != "snapshot"


def validate_governance(data: dict[str, Any], manifest_path: Path) -> None:
    """Validate repository-local rule, test, CI, and root snapshot contracts."""
    catalog_path = manifest_path.resolve().parent
    workspace_root = catalog_path

    for relative in (*GOVERNANCE_REQUIRED_FILES, *LOCAL_TEST_REQUIRED_FILES):
        _require_non_empty_file("catalog", catalog_path, relative)
    if not _has_ci_workflow(catalog_path):
        raise ManifestError(f"catalog CI workflow is missing: {catalog_path}")

    entries = [
        ("components", component_id, component)
        for component_id, component in data["components"].items()
    ]
    entries.extend(
        ("runtime_profiles", profile_id, profile)
        for profile_id, profile in data.get("runtime_profiles", {}).items()
    )
    for section, entry_id, entry in entries:
        entry_path = (catalog_path / entry["workspace_path"]).resolve()
        if not entry_path.is_dir():
            if entry.get("required") is False:
                continue
            raise ManifestError(f"{section}.{entry_id} workspace is missing: {entry_path}")
        location = f"{section}.{entry_id}"
        for relative in GOVERNANCE_REQUIRED_FILES:
            _require_non_empty_file(location, entry_path, relative)

        copied_common_rules = entry_path / "rules" / "common"
        if (
            section == "components"
            and entry_id != "core"
            and copied_common_rules.is_dir()
            and any(path.is_file() for path in copied_common_rules.rglob("*"))
        ):
            raise ManifestError(
                f"{location} must not copy cross-project rules into "
                f"{copied_common_rules}"
            )

        if section != "components" or not _component_requires_test_contract(entry):
            continue
        for relative in LOCAL_TEST_REQUIRED_FILES:
            _require_non_empty_file(location, entry_path, relative)
        if not _has_ci_workflow(entry_path):
            raise ManifestError(f"{location} CI workflow is missing: {entry_path}")

    workspace_component = data["components"].get("workspace")
    if isinstance(workspace_component, dict):
        root_agents = workspace_root / "AGENTS.md"
        snapshot_agents = (
            catalog_path / workspace_component["workspace_path"] / "project-root" / "AGENTS.md"
        ).resolve()
        _require_non_empty_file("workspace-root", workspace_root, "AGENTS.md")
        root_agents_text = root_agents.read_text(encoding="utf-8")
        missing_markers = [
            marker
            for marker in CONCEPTUAL_INTEGRITY_REQUIRED_MARKERS
            if marker not in root_agents_text
        ]
        if missing_markers:
            raise ManifestError(
                "workspace root AGENTS.md is missing Conceptual Integrity "
                f"Guardrail markers: {', '.join(missing_markers)}"
            )
        if not snapshot_agents.is_file() or root_agents.read_bytes() != snapshot_agents.read_bytes():
            raise ManifestError(
                "workspace root AGENTS.md does not match "
                f"RenCrow_Workspace snapshot: {snapshot_agents}"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="path to ecosystem.yaml")
    parser.add_argument(
        "--coverage-policy",
        type=Path,
        help="path to the catalog full-system coverage policy",
    )
    parser.add_argument(
        "--check-workspace",
        action="store_true",
        help="also require every declared sibling Git repository",
    )
    parser.add_argument(
        "--check-governance",
        action="store_true",
        help="also check repository rules, test plans, CI, and root snapshot",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = load_manifest(args.manifest)
        validate_manifest(data)
        coverage_policy_path = args.coverage_policy or (
            args.manifest.resolve().parent / "config" / "full-system-coverage.json"
        )
        coverage_policy = load_coverage_policy(coverage_policy_path)
        validate_coverage_policy(coverage_policy, data)
        if args.check_workspace:
            validate_workspace(data, args.manifest)
        if args.check_governance:
            validate_governance(data, args.manifest)
    except ManifestError as exc:
        print(f"[NG] {exc}", file=sys.stderr)
        return 1

    checked = []
    if args.check_workspace:
        checked.append("workspace")
    if args.check_governance:
        checked.append("governance")
    suffix = f" and {', '.join(checked)}" if checked else ""
    print(f"[OK] validated {args.manifest}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

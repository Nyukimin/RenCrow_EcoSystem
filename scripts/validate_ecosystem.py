#!/usr/bin/env python3
"""Validate the RenCrow ecosystem manifest without third-party dependencies."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


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
LOCAL_TEST_REQUIRED_FILES = (
    "scripts/test-local.ps1",
    "scripts/test-local.plan.json",
)


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
        if not snapshot_agents.is_file() or root_agents.read_bytes() != snapshot_agents.read_bytes():
            raise ManifestError(
                "workspace root AGENTS.md does not match "
                f"RenCrow_Workspace snapshot: {snapshot_agents}"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="path to ecosystem.yaml")
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

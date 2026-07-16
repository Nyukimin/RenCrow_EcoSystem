#!/usr/bin/env python3
"""Validate the RenCrow ecosystem manifest without third-party dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


COMPONENT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ALLOWED_DISTRIBUTIONS = {
    "binary",
    "extension",
    "offline-assets",
    "service",
    "template",
    "tooling",
}
ALLOWED_RUNTIME_IMPLEMENTATIONS = {"go", "python", "javascript", "mixed"}
ALLOWED_RUNTIME_STATUSES = {"planned", "development", "available", "compatibility"}
ALLOWED_COMPANION_KINDS = {
    "compatibility-runtime",
    "external-compute",
    "system-service",
}
ARTIFACT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
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
FORBIDDEN_KEY_PARTS = {"api_key", "password", "private_key", "secret", "token"}


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


def _validate_workspace_path(component_id: str, raw_path: Any) -> None:
    if not isinstance(raw_path, str) or not raw_path.startswith("../"):
        raise ManifestError(
            f"components.{component_id}.workspace_path must be a sibling path"
        )
    relative_parts = Path(raw_path).parts
    if len(relative_parts) != 2 or relative_parts[0] != "..":
        raise ManifestError(
            f"components.{component_id}.workspace_path must identify one sibling"
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

    if data.get("schema_version") != 2:
        raise ManifestError("schema_version must be 2")

    ecosystem = data.get("ecosystem")
    if not isinstance(ecosystem, dict):
        raise ManifestError("ecosystem must be an object")
    for field in ("name", "release", "compatibility_status"):
        if not isinstance(ecosystem.get(field), str) or not ecosystem[field].strip():
            raise ManifestError(f"ecosystem.{field} must be a non-empty string")

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
        _validate_workspace_path(component_id, workspace_path)
        if workspace_path in workspace_paths:
            raise ManifestError(f"duplicate workspace_path: {workspace_path}")
        workspace_paths.add(workspace_path)

        version = component["version"]
        if not isinstance(version, str) or not version.strip():
            raise ManifestError(f"components.{component_id}.version must be non-empty")
        if version == "unpinned":
            unpinned_components.append(component_id)

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

    if ecosystem["compatibility_status"] == "verified" and unpinned_components:
        names = ", ".join(sorted(unpinned_components))
        raise ManifestError(f"verified release has unpinned components: {names}")
    if ecosystem["release"] != "development" and unpinned_components:
        names = ", ".join(sorted(unpinned_components))
        raise ManifestError(f"released ecosystem has unpinned components: {names}")


def validate_workspace(data: dict[str, Any], manifest_path: Path) -> None:
    """Check that declared sibling repositories exist in a local workspace."""
    base_directory = manifest_path.resolve().parent
    for component_id, component in data["components"].items():
        component_path = (base_directory / component["workspace_path"]).resolve()
        if not component_path.is_dir():
            raise ManifestError(
                f"components.{component_id} workspace is missing: {component_path}"
            )
        if not (component_path / ".git").exists():
            raise ManifestError(
                f"components.{component_id} is not a Git worktree: {component_path}"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="path to ecosystem.yaml")
    parser.add_argument(
        "--check-workspace",
        action="store_true",
        help="also require every declared sibling Git repository",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = load_manifest(args.manifest)
        validate_manifest(data)
        if args.check_workspace:
            validate_workspace(data, args.manifest)
    except ManifestError as exc:
        print(f"[NG] {exc}", file=sys.stderr)
        return 1

    suffix = " and workspace" if args.check_workspace else ""
    print(f"[OK] validated {args.manifest}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

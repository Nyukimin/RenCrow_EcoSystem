#!/usr/bin/env python3
"""Plan or apply ecosystem source-pin updates from sibling Git HEADs."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, NamedTuple


COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")


class PinSyncError(RuntimeError):
    """Raised when a source pin cannot be derived safely."""


class PinUpdate(NamedTuple):
    section: str
    entry_id: str
    old_version: str
    new_version: str


HeadReader = Callable[[Path], str | None]


def git_head(path: Path) -> str | None:
    if not path.is_dir():
        return None
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "git rev-parse failed"
        raise PinSyncError(f"cannot read Git HEAD for {path}: {detail}")
    head = result.stdout.strip().lower()
    if not COMMIT_SHA.fullmatch(head):
        raise PinSyncError(f"Git HEAD for {path} is not a full commit SHA")
    status = subprocess.run(
        ["git", "-C", str(path), "status", "--porcelain"],
        check=False,
        capture_output=True,
        text=True,
    )
    if status.returncode != 0:
        detail = status.stderr.strip() or "git status failed"
        raise PinSyncError(f"cannot inspect worktree for {path}: {detail}")
    if status.stdout.strip():
        raise PinSyncError(f"workspace is dirty and cannot be pinned: {path}")
    return head


def plan_updates(
    manifest: dict[str, Any], workspace: Path, head_reader: HeadReader = git_head
) -> list[PinUpdate]:
    updates: list[PinUpdate] = []
    for section in ("components", "runtime_profiles"):
        entries = manifest.get(section, {})
        if not isinstance(entries, dict):
            raise PinSyncError(f"{section} must be an object")
        for entry_id, entry in entries.items():
            if not isinstance(entry, dict):
                raise PinSyncError(f"{section}.{entry_id} must be an object")
            old_version = entry.get("version")
            if old_version == "planned":
                continue
            relative = entry.get("workspace_path")
            if not isinstance(relative, str) or not relative.startswith("./"):
                raise PinSyncError(f"{section}.{entry_id}.workspace_path is invalid")
            component_path = (workspace / relative).resolve()
            try:
                component_path.relative_to(workspace.resolve())
            except ValueError as error:
                raise PinSyncError(
                    f"{section}.{entry_id}.workspace_path escapes workspace"
                ) from error
            head = head_reader(component_path)
            if head is None:
                if entry.get("required") is False:
                    continue
                raise PinSyncError(
                    f"{section}.{entry_id} workspace is missing: {component_path}"
                )
            if not isinstance(old_version, str) or not COMMIT_SHA.fullmatch(old_version):
                raise PinSyncError(f"{section}.{entry_id}.version is not a full commit SHA")
            if head != old_version:
                updates.append(PinUpdate(section, entry_id, old_version, head))
    return updates


def apply_updates(manifest_path: Path, updates: list[PinUpdate]) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for update in updates:
        current = manifest[update.section][update.entry_id]["version"]
        if current != update.old_version:
            raise PinSyncError(
                f"{update.section}.{update.entry_id}.version changed during pin sync"
            )
        manifest[update.section][update.entry_id]["version"] = update.new_version

    mode = manifest_path.stat().st_mode & 0o777
    rendered = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=manifest_path.parent,
        prefix=f".{manifest_path.name}.",
        delete=False,
    ) as temporary:
        temporary.write(rendered)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    try:
        temporary_path.chmod(mode)
        os.replace(temporary_path, manifest_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PinSyncError(f"cannot load manifest {path}: {error}") from error
    if not isinstance(value, dict):
        raise PinSyncError("manifest root must be an object")
    return value


def result_payload(updates: list[PinUpdate], applied: bool) -> dict[str, Any]:
    return {
        "ok": applied or not updates,
        "status": "updated" if applied and updates else "clean" if not updates else "drift",
        "applied": applied,
        "update_count": len(updates),
        "updates": [
            {
                "section": update.section,
                "id": update.entry_id,
                "old_version": update.old_version,
                "new_version": update.new_version,
            }
            for update in updates
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="workspaceのGit HEADからecosystem source pinを計画・同期する"
    )
    parser.add_argument("manifest", nargs="?", type=Path, default=Path("ecosystem.yaml"))
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    workspace = args.workspace.resolve() if args.workspace else manifest_path.parent
    try:
        updates = plan_updates(load_manifest(manifest_path), workspace)
        if args.apply and updates:
            apply_updates(manifest_path, updates)
        payload = result_payload(updates, args.apply)
    except PinSyncError as error:
        payload = {"ok": False, "status": "blocked", "error": str(error)}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        else:
            print(f"[NG] {error}")
        return 2

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    elif not updates:
        print("[OK] workspace source pins are current")
    else:
        for update in updates:
            print(
                f"{update.section}.{update.entry_id}: "
                f"{update.old_version[:12]} -> {update.new_version[:12]}"
            )
        print("[OK] source pins updated" if args.apply else "[NG] source pin drift detected")
    return 0 if args.apply or not updates else 1


if __name__ == "__main__":
    raise SystemExit(main())

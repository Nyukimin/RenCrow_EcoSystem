from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPOSITORY_ROOT / "scripts" / "sync_workspace_pins.py"
SPEC = importlib.util.spec_from_file_location("sync_workspace_pins", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
SYNC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNC)


class SyncWorkspacePinsTest(unittest.TestCase):
    def test_plan_updates_implemented_component_to_workspace_head(self) -> None:
        manifest = {
            "components": {
                "core": {"workspace_path": "./RenCrow_CORE", "version": "a" * 40},
                "optional": {"workspace_path": "./Missing", "version": "planned", "required": False},
            },
            "runtime_profiles": {},
        }
        updates = SYNC.plan_updates(
            manifest,
            Path("/workspace"),
            lambda path: "b" * 40 if path.name == "RenCrow_CORE" else None,
        )

        self.assertEqual(
            updates,
            [SYNC.PinUpdate("components", "core", "a" * 40, "b" * 40)],
        )

    def test_plan_fails_closed_when_implemented_required_repo_is_missing(self) -> None:
        manifest = {
            "components": {
                "core": {"workspace_path": "./RenCrow_CORE", "version": "a" * 40, "required": True}
            },
            "runtime_profiles": {},
        }

        with self.assertRaisesRegex(SYNC.PinSyncError, "workspace is missing"):
            SYNC.plan_updates(manifest, Path("/workspace"), lambda _path: None)

    def test_apply_updates_only_version_and_keeps_json_manifest_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "ecosystem.yaml"
            original = {
                "schema_version": 4,
                "ecosystem": {"compatibility_status": "source-pinned"},
                "components": {
                    "core": {
                        "workspace_path": "./RenCrow_CORE",
                        "version": "a" * 40,
                        "role": "owner",
                    }
                },
                "runtime_profiles": {},
            }
            manifest_path.write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8")

            SYNC.apply_updates(
                manifest_path,
                [SYNC.PinUpdate("components", "core", "a" * 40, "b" * 40)],
            )

            updated = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["components"]["core"]["version"], "b" * 40)
            self.assertEqual(updated["components"]["core"]["role"], "owner")

    def test_git_head_fails_closed_for_dirty_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"],
                check=True,
            )
            tracked = repo / "tracked.txt"
            tracked.write_text("clean\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "tracked.txt"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-qm", "initial"], check=True)
            tracked.write_text("dirty\n", encoding="utf-8")

            with self.assertRaisesRegex(SYNC.PinSyncError, "workspace is dirty"):
                SYNC.git_head(repo)


if __name__ == "__main__":
    unittest.main()

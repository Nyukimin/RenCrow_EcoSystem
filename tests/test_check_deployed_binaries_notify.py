from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("notifier", ROOT / "scripts/check_deployed_binaries_notify.py")
assert SPEC and SPEC.loader
NOTIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(NOTIFIER)


class NotifierTest(unittest.TestCase):
    def run_case(
        self,
        root: Path,
        rows: list[dict[str, object]],
        sends: list[list[str]],
        send_code: int = 0,
        *,
        send_output: str | None = None,
        send_error: str = "send failed",
    ):
        def runner(command: list[str]):
            if len(command) > 1 and Path(command[1]).name == "check_deployed_binaries.py":
                code = 1 if any(row["status"] in NOTIFIER.FAILING for row in rows) else 0
                return code, json.dumps(rows), ""
            sends.append(command)
            output = send_output if send_output is not None else json.dumps({"ok": send_code == 0, "status": "dry_run"})
            return send_code, output, send_error
        return NOTIFIER.run_notifier(
            checker=Path("check_deployed_binaries.py"), manifest=Path("ecosystem.yaml"),
            state_path=root / "state.json", core_cli=Path("rencrow"),
            notification_dry_run=True, runner=runner,
        )

    def test_initial_clean_is_silent(self):
        with tempfile.TemporaryDirectory() as directory:
            sends: list[list[str]] = []
            code, result = self.run_case(Path(directory), [{"status": "MATCH"}], sends)
            self.assertEqual(code, 0)
            self.assertFalse(result["changed"])
            self.assertEqual(sends, [])

    def test_new_drift_notifies_once_and_repeat_is_silent(self):
        with tempfile.TemporaryDirectory() as directory:
            root, sends = Path(directory), []
            rows = [{"name": "rencrow", "component": "core", "status": "MISMATCH", "built": "a" * 40, "pin": "b" * 40}]
            first, _ = self.run_case(root, rows, sends)
            second, result = self.run_case(root, rows, sends)
            self.assertEqual((first, second), (0, 0))
            self.assertEqual(len(sends), 1)
            self.assertFalse(result["changed"])
            self.assertIn("--dry-run", sends[0])

    def test_destination_unavailable_receipt_defers_without_advancing_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root, sends = Path(directory), []
            state_path = root / "state.json"
            state_path.write_text(
                '{"schema_version":1,"status":"clean","fingerprint":"before"}\n',
                encoding="utf-8",
            )
            before = state_path.read_bytes()
            drift = [{
                "name": "rencrow",
                "component": "core",
                "status": "MISMATCH",
                "built": "a" * 40,
                "pin": "b" * 40,
            }]
            code, result = self.run_case(
                root,
                drift,
                sends,
                send_code=1,
                send_output=json.dumps({
                    "ok": False,
                    "timestamp": "2026-08-26T00:00:00Z",
                    "component": "channels",
                    "status": "unavailable",
                    "code": "E_NOTIFICATION_DESTINATION_UNAVAILABLE",
                }),
                send_error="target file=/private/rencrow/line-target.json token=secret-token",
            )
            self.assertEqual(code, 0)
            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "notification_deferred")
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["fingerprint"], NOTIFIER.fingerprint(NOTIFIER.drift_items(drift)))
            self.assertEqual(state_path.read_bytes(), before)
            self.assertEqual(len(sends), 1)
            self.assertEqual(sends[0][1:3], ["channels", "send"])

    def test_malformed_destination_unavailable_receipt_fails_without_advancing_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root, sends = Path(directory), []
            drift = [{"name": "tts", "component": "tts", "status": "UNSTAMPED"}]
            code, result = self.run_case(
                root,
                drift,
                sends,
                send_code=1,
                send_output="not json",
            )
            self.assertEqual(code, 1)
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "notification_failed")
            self.assertFalse((root / "state.json").exists())
            self.assertEqual(len(sends), 1)

    def test_empty_destination_unavailable_receipt_fails_without_advancing_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root, sends = Path(directory), []
            drift = [{"name": "tts", "component": "tts", "status": "UNSTAMPED"}]
            code, result = self.run_case(root, drift, sends, send_code=1, send_output="")
            self.assertEqual(code, 1)
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "notification_failed")
            self.assertFalse((root / "state.json").exists())
            self.assertEqual(len(sends), 1)

    def test_other_send_failure_receipt_fails_without_advancing_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root, sends = Path(directory), []
            drift = [{"name": "tts", "component": "tts", "status": "UNSTAMPED"}]
            code, result = self.run_case(
                root,
                drift,
                sends,
                send_code=1,
                send_output=json.dumps({
                    "ok": False,
                    "timestamp": "2026-08-26T00:00:00Z",
                    "component": "channels",
                    "status": "unavailable",
                    "code": "E_OTHER_NOTIFICATION_FAILURE",
                }),
            )
            self.assertEqual(code, 1)
            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "notification_failed")
            self.assertFalse((root / "state.json").exists())
            self.assertEqual(len(sends), 1)

    def test_destination_present_sends_and_advances_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root, sends = Path(directory), []
            drift = [{"name": "tts", "component": "tts", "status": "UNSTAMPED"}]
            code, result = self.run_case(
                root,
                drift,
                sends,
            )
            self.assertEqual(code, 0)
            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "drift")
            self.assertEqual(len(sends), 1)
            self.assertIn("channels", sends[0])
            self.assertNotIn("list", sends[0])
            self.assertTrue((root / "state.json").exists())

    def test_recovery_notifies(self):
        with tempfile.TemporaryDirectory() as directory:
            root, sends = Path(directory), []
            drift = [{"name": "rencrow", "component": "core", "status": "DIRTY", "built": "a", "pin": "a"}]
            self.run_case(root, drift, sends)
            code, result = self.run_case(root, [{"status": "MATCH"}], sends)
            self.assertEqual(code, 0)
            self.assertTrue(result["changed"])
            self.assertEqual(len(sends), 2)
            self.assertIn("recovered", sends[-1][sends[-1].index("--message") + 1])

    def test_send_failure_does_not_advance_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root, sends = Path(directory), []
            drift = [{"name": "tts", "component": "tts", "status": "UNSTAMPED", "built": "", "pin": "a"}]
            code, result = self.run_case(root, drift, sends, send_code=1)
            self.assertEqual(code, 1)
            self.assertEqual(result["status"], "notification_failed")
            self.assertFalse((root / "state.json").exists())

    def test_state_is_private_and_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private" / "state.json"
            NOTIFIER.write_state(path, {"schema_version": 1})
            if os.name != "nt":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)


if __name__ == "__main__":
    unittest.main()

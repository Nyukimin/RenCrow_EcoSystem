from __future__ import annotations

import importlib.util
import plistlib
from pathlib import Path
import tempfile
import unittest
import json

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("adapters", ROOT / "scripts/deployment_host_adapters.py")
assert SPEC and SPEC.loader
A = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A)
CHECK_SPEC = importlib.util.spec_from_file_location("checker_adapter_e2e", ROOT / "scripts/check_deployed_binaries.py")
assert CHECK_SPEC and CHECK_SPEC.loader
CHECKER = importlib.util.module_from_spec(CHECK_SPEC)
CHECK_SPEC.loader.exec_module(CHECKER)


class Response:
    status = 200
    def read(self):
        return json.dumps({"status": "ready"}).encode()
    def close(self):
        return None


class AdapterTest(unittest.TestCase):
    def test_windows_discovers_controls_and_normalizes_service(self):
        calls = []
        def runner(command, **_kwargs):
            calls.append(command)
            script = command[-1]
            if "Get-CimInstance" in script:
                return 0, '{"Name":"rencrow-image","State":"Running","PathName":"\\\"C:\\\\RenCrow\\\\rencrow-image.exe\\\" --config image.json"}', ""
            if "Get-Service" in script:
                return 0, "Running\n", ""
            return 0, "", ""
        adapter = A.WindowsServiceAdapter(runner)
        self.assertEqual(adapter.services("rencrow"), ["rencrow-image"])
        self.assertEqual(adapter.exec_path("rencrow-image"), r"C:\RenCrow\rencrow-image.exe")
        self.assertEqual(adapter.contract_unit("rencrow-image"), "rencrow-image.service")
        self.assertEqual(adapter.properties("rencrow-image")["ActiveState"], "active")
        adapter.stop("rencrow-image")
        adapter.start("rencrow-image")
        self.assertIn("Stop-Service", calls[-2][-1])
        self.assertIn("Start-Service", calls[-1][-1])

    def test_launchd_discovers_controls_and_normalizes_service(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            launch_agents = home / "Library/LaunchAgents"
            launch_agents.mkdir(parents=True)
            plist = launch_agents / "com.rencrow.image.plist"
            with plist.open("wb") as handle:
                plistlib.dump({"Label":"com.rencrow.image","ProgramArguments":["/Users/ren/bin/rencrow-image","--config","image.json"]}, handle)
            calls = []
            def runner(command, **_kwargs):
                calls.append(command)
                if command[:2] == ["launchctl", "print"]:
                    return 0, "state = running\nlast exit code = 0\n", ""
                return 0, "", ""
            adapter = A.LaunchdUserAdapter(runner, home=home, uid=501)
            self.assertEqual(adapter.services("rencrow"), ["com.rencrow.image"])
            self.assertEqual(adapter.exec_path("com.rencrow.image"), "/Users/ren/bin/rencrow-image")
            self.assertEqual(adapter.contract_unit("com.rencrow.image"), "rencrow-image.service")
            self.assertEqual(adapter.properties("com.rencrow.image")["ActiveState"], "active")
            adapter.stop("com.rencrow.image")
            adapter.start("com.rencrow.image")
            self.assertEqual(calls[-2][:2], ["launchctl", "bootout"])
            self.assertEqual(calls[-1][:2], ["launchctl", "bootstrap"])

    def test_launchd_core_identity(self):
        self.assertEqual(A._launchd_contract_unit("com.rencrow.core"), "rencrow")

    def test_windows_stop_start_readiness_e2e(self):
        status = {"value": "Running"}
        def runner(command, **_kwargs):
            script = command[-1]
            if "Get-Service" in script:
                return 0, status["value"] + "\n", ""
            if "Stop-Service" in script:
                status["value"] = "Stopped"
            if "Start-Service" in script:
                status["value"] = "Running"
            return 0, "", ""
        adapter = A.WindowsServiceAdapter(runner)
        adapter.stop("rencrow-image")
        self.assertEqual(status["value"], "Stopped")
        contract = {"unit":"rencrow-image.service","kind":"http_json","url":"http://127.0.0.1:8780/health","timeout_seconds":3,"expect":{"path":"status","equals":"ready"}}
        broken = CHECKER.start_and_settle(
            ["rencrow-image"], {"rencrow-image": contract}, adapter=adapter,
            http_opener=lambda *_args, **_kwargs: Response(), sleep_fn=lambda _seconds: None,
        )
        self.assertIsNone(broken)
        self.assertEqual(status["value"], "Running")

    def test_launchd_stop_start_readiness_e2e(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            agents = home / "Library/LaunchAgents"
            agents.mkdir(parents=True)
            plist = agents / "com.rencrow.image.plist"
            with plist.open("wb") as handle:
                plistlib.dump({"Label":"com.rencrow.image","ProgramArguments":["/Users/ren/bin/rencrow-image"]}, handle)
            loaded = {"value": True}
            def runner(command, **_kwargs):
                if command[:2] == ["launchctl", "bootout"]:
                    loaded["value"] = False
                elif command[:2] == ["launchctl", "bootstrap"]:
                    loaded["value"] = True
                elif command[:2] == ["launchctl", "print"]:
                    return (0, "state = running\nlast exit code = 0\n", "") if loaded["value"] else (1, "", "")
                return 0, "", ""
            adapter = A.LaunchdUserAdapter(runner, home=home, uid=501)
            adapter.services("rencrow")
            adapter.stop("com.rencrow.image")
            self.assertFalse(loaded["value"])
            contract = {"unit":"rencrow-image.service","kind":"http_json","url":"http://127.0.0.1:8780/health","timeout_seconds":3,"expect":{"path":"status","equals":"ready"}}
            broken = CHECKER.start_and_settle(
                ["com.rencrow.image"], {"com.rencrow.image": contract}, adapter=adapter,
                http_opener=lambda *_args, **_kwargs: Response(), sleep_fn=lambda _seconds: None,
            )
            self.assertIsNone(broken)
            self.assertTrue(loaded["value"])


if __name__ == "__main__":
    unittest.main()

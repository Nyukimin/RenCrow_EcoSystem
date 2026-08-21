from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("installer", ROOT / "scripts/install_binary_drift_notifier.py")
assert SPEC and SPEC.loader
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


class InstallerTest(unittest.TestCase):
    def test_installs_snapshot_then_enables_timer(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            calls: list[tuple[list[str], bool]] = []
            INSTALLER.install(ROOT, home, lambda command, check: calls.append((command, check)))
            runtime = home / ".local/share/rencrow/binary-drift-monitor"
            units = home / ".config/systemd/user"
            self.assertTrue((runtime / "check_deployed_binaries.py").is_file())
            self.assertTrue((runtime / "check_deployed_binaries_notify.py").is_file())
            self.assertEqual((runtime / "ecosystem.yaml").read_bytes(), (ROOT / "ecosystem.yaml").read_bytes())
            self.assertTrue((units / "rencrow-binary-drift-notify.service").is_file())
            service = (units / "rencrow-binary-drift-notify.service").read_text(encoding="utf-8")
            self.assertIn("Environment=PATH=%h/.local/bin:/usr/local/bin:/usr/bin:/bin", service)
            self.assertEqual(calls[-1][0], ["systemctl", "--user", "enable", "--now", "rencrow-binary-drift-notify.timer"])


if __name__ == "__main__":
    unittest.main()

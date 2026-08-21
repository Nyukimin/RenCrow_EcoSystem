#!/usr/bin/env python3
"""Install the read-only binary drift notifier for Linux user systemd."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


def install(root: Path, home: Path, runner=subprocess.run) -> None:
    runtime = home / ".local/share/rencrow/binary-drift-monitor"
    units = home / ".config/systemd/user"
    runtime.mkdir(parents=True, exist_ok=True)
    units.mkdir(parents=True, exist_ok=True)
    for name in (
        "check_deployed_binaries.py",
        "check_deployed_binaries_notify.py",
        "deployment_host_adapters.py",
    ):
        shutil.copy2(root / "scripts" / name, runtime / name)
        (runtime / name).chmod(0o755)
    shutil.copy2(root / "ecosystem.yaml", runtime / "ecosystem.yaml")
    for name in ("rencrow-binary-drift-notify.service", "rencrow-binary-drift-notify.timer"):
        shutil.copy2(root / "systemd/user" / name, units / name)
    runner(["systemctl", "--user", "daemon-reload"], check=True)
    runner(["systemctl", "--user", "enable", "--now", "rencrow-binary-drift-notify.timer"], check=True)


def main() -> int:
    install(Path(__file__).resolve().parents[1], Path.home())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

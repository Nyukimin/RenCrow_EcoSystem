#!/usr/bin/env python3
"""Native service-manager adapters for binary redeployment."""

from __future__ import annotations

import json
import os
from pathlib import Path
import plistlib
import re
import shlex
import subprocess
import sys
from typing import Any, Callable

Runner = Callable[..., tuple[int, str, str]]


def default_runner(command: list[str], **kwargs: Any) -> tuple[int, str, str]:
    result = subprocess.run(command, capture_output=True, text=True, timeout=kwargs.get("timeout", 60))
    return result.returncode, result.stdout, result.stderr


class HostAdapter:
    name = "unknown"

    def services(self, prefix: str) -> list[str]:
        raise NotImplementedError

    def exec_path(self, service: str) -> str | None:
        raise NotImplementedError

    def properties(self, service: str) -> dict[str, str] | None:
        raise NotImplementedError

    def contract_unit(self, service: str) -> str:
        raise NotImplementedError

    def reset_failed(self, service: str) -> tuple[int, str, str]:
        return 0, "", ""

    def start(self, service: str) -> tuple[int, str, str]:
        raise NotImplementedError

    def stop(self, service: str) -> tuple[int, str, str]:
        raise NotImplementedError


class SystemdUserAdapter(HostAdapter):
    name = "systemd"

    def __init__(self, runner: Runner = default_runner) -> None:
        self.runner = runner

    def services(self, prefix: str) -> list[str]:
        code, output, _ = self.runner([
            "systemctl", "--user", "list-unit-files", f"{prefix}*.service",
            "--no-legend", "--plain",
        ])
        if code != 0:
            return []
        return sorted({line.split()[0] for line in output.splitlines() if line.split()})

    def exec_path(self, service: str) -> str | None:
        code, output, _ = self.runner(["systemctl", "--user", "show", service, "-p", "ExecStart", "--value"])
        if code != 0:
            return None
        match = re.search(r"\bpath=([^\s;]+)", output)
        if not match:
            return None
        wrapper = match.group(1)
        if os.path.basename(wrapper) != "flock":
            return wrapper
        argv_match = re.search(r"\bargv\[\]=(.+?)(?:\s*;\s*|\s*}\s*$)", output)
        if not argv_match:
            return wrapper
        try:
            argv = shlex.split(argv_match.group(1).strip())
        except ValueError:
            return wrapper
        return argv[3] if len(argv) >= 4 and argv[0] == wrapper and argv[1] == "-n" else wrapper

    def properties(self, service: str) -> dict[str, str] | None:
        keys = ["ActiveState", "SubState", "Result", "ExecMainStatus", "NRestarts"]
        command = ["systemctl", "--user", "show", service]
        for key in keys:
            command.extend(["-p", key])
        code, output, _ = self.runner(command)
        if code != 0:
            return None
        return dict(line.split("=", 1) for line in output.splitlines() if "=" in line)

    def contract_unit(self, service: str) -> str:
        return service

    def reset_failed(self, service: str) -> tuple[int, str, str]:
        return self.runner(["systemctl", "--user", "reset-failed", service])

    def start(self, service: str) -> tuple[int, str, str]:
        return self.runner(["systemctl", "--user", "start", service])

    def stop(self, service: str) -> tuple[int, str, str]:
        return self.runner(["systemctl", "--user", "stop", service])


def _first_command_path(command_line: str) -> str | None:
    command_line = command_line.strip()
    if not command_line:
        return None
    if command_line.startswith('"'):
        end = command_line.find('"', 1)
        return command_line[1:end] if end > 1 else None
    try:
        return shlex.split(command_line, posix=False)[0].strip('"')
    except ValueError:
        return command_line.split()[0]


class WindowsServiceAdapter(HostAdapter):
    name = "windows"

    def __init__(self, runner: Runner = default_runner, powershell: str = "powershell.exe") -> None:
        self.runner = runner
        self.powershell = powershell
        self._records: dict[str, dict[str, str]] = {}

    def _run(self, script: str) -> tuple[int, str, str]:
        return self.runner([self.powershell, "-NoProfile", "-NonInteractive", "-Command", script])

    def services(self, prefix: str) -> list[str]:
        safe = prefix.replace("'", "''")
        code, output, _ = self._run(
            f"Get-CimInstance Win32_Service | Where-Object {{$_.Name -like '{safe}*'}} | "
            "Select-Object Name,State,PathName | ConvertTo-Json -Compress"
        )
        if code != 0 or not output.strip():
            return []
        decoded = json.loads(output)
        records = decoded if isinstance(decoded, list) else [decoded]
        self._records = {str(item["Name"]): {str(k): str(v) for k, v in item.items()} for item in records}
        return sorted(self._records)

    def exec_path(self, service: str) -> str | None:
        return _first_command_path(self._records.get(service, {}).get("PathName", ""))

    def properties(self, service: str) -> dict[str, str] | None:
        safe = service.replace("'", "''")
        code, output, _ = self._run(f"(Get-Service -Name '{safe}').Status.ToString()")
        if code != 0:
            return None
        status = output.strip().lower()
        states = {
            "running": ("active", "running"), "startpending": ("activating", "start"),
            "stopped": ("inactive", "dead"), "stoppending": ("deactivating", "stop"),
            "paused": ("inactive", "paused"),
        }
        active, sub = states.get(status, ("failed", status or "unknown"))
        return {"ActiveState": active, "SubState": sub, "Result": "success", "ExecMainStatus": "0", "NRestarts": ""}

    def contract_unit(self, service: str) -> str:
        return f"{service}.service"

    def start(self, service: str) -> tuple[int, str, str]:
        safe = service.replace("'", "''")
        return self._run(f"Start-Service -Name '{safe}' -ErrorAction Stop")

    def stop(self, service: str) -> tuple[int, str, str]:
        safe = service.replace("'", "''")
        return self._run(f"Stop-Service -Name '{safe}' -ErrorAction Stop")


class LaunchdUserAdapter(HostAdapter):
    name = "launchd"

    def __init__(self, runner: Runner = default_runner, home: Path | None = None, uid: int | None = None) -> None:
        self.runner = runner
        self.home = home or Path.home()
        self.uid = os.getuid() if uid is None else uid
        self._records: dict[str, tuple[Path, list[str]]] = {}

    def services(self, prefix: str) -> list[str]:
        self._records = {}
        directory = self.home / "Library" / "LaunchAgents"
        for path in directory.glob("*.plist") if directory.is_dir() else []:
            try:
                with path.open("rb") as handle:
                    value = plistlib.load(handle)
            except (OSError, plistlib.InvalidFileException):
                continue
            label = value.get("Label")
            arguments = value.get("ProgramArguments") or ([value["Program"]] if value.get("Program") else [])
            if (
                isinstance(label, str)
                and label.startswith("com.rencrow.")
                and isinstance(arguments, list)
                and _launchd_contract_unit(label).startswith(prefix)
            ):
                self._records[label] = (path, [str(item) for item in arguments])
        return sorted(self._records)

    def exec_path(self, service: str) -> str | None:
        arguments = self._records.get(service, (Path(), []))[1]
        return arguments[0] if arguments else None

    def _target(self, service: str) -> str:
        return f"gui/{self.uid}/{service}"

    def properties(self, service: str) -> dict[str, str] | None:
        code, output, _ = self.runner(["launchctl", "print", self._target(service)])
        if code != 0:
            return {"ActiveState": "inactive", "SubState": "dead", "Result": "success", "ExecMainStatus": "0", "NRestarts": ""}
        running = re.search(r"\bstate\s*=\s*running\b", output) is not None
        exit_match = re.search(r"last exit code\s*=\s*(-?\d+)", output)
        exit_code = exit_match.group(1) if exit_match else "0"
        return {
            "ActiveState": "active" if running else "inactive",
            "SubState": "running" if running else "dead",
            "Result": "success" if exit_code == "0" else "exit-code",
            "ExecMainStatus": exit_code, "NRestarts": "",
        }

    def contract_unit(self, service: str) -> str:
        return _launchd_contract_unit(service) + ".service"

    def start(self, service: str) -> tuple[int, str, str]:
        record = self._records.get(service)
        if record is None:
            return 1, "", "unknown launchd service"
        return self.runner(["launchctl", "bootstrap", f"gui/{self.uid}", str(record[0])])

    def stop(self, service: str) -> tuple[int, str, str]:
        return self.runner(["launchctl", "bootout", self._target(service)])


def _launchd_contract_unit(label: str) -> str:
    prefix = "com.rencrow."
    name = label[len(prefix):] if label.startswith(prefix) else label
    return "rencrow" if name == "core" else "rencrow-" + name.replace(".", "-")


def create_adapter(name: str, runner: Runner = default_runner) -> HostAdapter:
    resolved = name
    if name == "auto":
        resolved = "windows" if os.name == "nt" else ("launchd" if sys.platform == "darwin" else "systemd")
    if resolved == "systemd":
        return SystemdUserAdapter(runner)
    if resolved == "windows":
        return WindowsServiceAdapter(runner)
    if resolved == "launchd":
        return LaunchdUserAdapter(runner)
    raise ValueError(f"unsupported host adapter: {name}")

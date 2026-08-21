#!/usr/bin/env python3
"""Notify through CORE when deployed-binary drift changes state."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Callable

FAILING = {"MISMATCH", "DIRTY", "UNSTAMPED"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def command_runner(command: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    return result.returncode, result.stdout, result.stderr


def read_state(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError, UnicodeError, TypeError, ValueError) as exc:
        raise RuntimeError(f"stateを読めません: {exc}") from exc
    return value if isinstance(value, dict) else None


def write_state(path: Path, state: dict[str, Any]) -> None:
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        os.chmod(path.parent, 0o700)
    handle, raw_tmp = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    tmp = Path(raw_tmp)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(state, stream, ensure_ascii=False, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != "nt":
            os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def drift_items(rows: Any) -> list[dict[str, str]]:
    if not isinstance(rows, list):
        raise RuntimeError("checker JSONはarrayではありません")
    items: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("status") not in FAILING:
            continue
        items.append({
            "name": str(row.get("name", "")),
            "component": str(row.get("component") or ""),
            "status": str(row["status"]),
            "built": str(row.get("built", "")),
            "pin": str(row.get("pin", "")),
        })
    return sorted(items, key=lambda item: (item["component"], item["name"]))


def fingerprint(items: list[dict[str, str]]) -> str:
    payload = json.dumps(items, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def notification_message(items: list[dict[str, str]], recovered: bool) -> str:
    if recovered:
        return "RenCrow binary drift recovered: all mapped Go binaries are SHA-verifiable and match ecosystem pins."
    details = ", ".join(
        f"{item['component'] or '-'}:{item['name']}={item['status']}({item['built'][:7]}->{item['pin'][:7]})"
        for item in items[:12]
    )
    suffix = "" if len(items) <= 12 else f", +{len(items) - 12} more"
    return f"RenCrow binary drift detected ({len(items)}): {details}{suffix}"


def run_notifier(
    *,
    checker: Path,
    manifest: Path,
    state_path: Path,
    core_cli: Path,
    notification_dry_run: bool,
    runner: Callable[[list[str]], tuple[int, str, str]] = command_runner,
) -> tuple[int, dict[str, Any]]:
    checked_at = utc_now()
    code, output, error = runner([sys.executable, str(checker), str(manifest), "--json"])
    if code not in {0, 1}:
        return 1, {"ok": False, "status": "checker_failed", "error": error.strip()[:500]}
    try:
        rows = json.loads(output)
        items = drift_items(rows)
        previous = read_state(state_path)
    except (json.JSONDecodeError, RuntimeError) as exc:
        return 1, {"ok": False, "status": "invalid_state", "error": str(exc)[:500]}

    current_status = "drift" if items else "clean"
    current_fingerprint = fingerprint(items)
    previous_status = str((previous or {}).get("status", "clean"))
    previous_fingerprint = str((previous or {}).get("fingerprint", ""))
    notify = bool(items) and current_fingerprint != previous_fingerprint
    recovered = not items and previous_status == "drift"
    notify = notify or recovered

    if notify:
        command = [str(core_cli), "channels", "send", "--message", notification_message(items, recovered), "--json"]
        if notification_dry_run:
            command.append("--dry-run")
        send_code, send_out, send_error = runner(command)
        if send_code != 0:
            return 1, {
                "ok": False,
                "status": "notification_failed",
                "error": send_error.strip()[:500],
            }
        try:
            send_result = json.loads(send_out) if send_out.strip() else {}
        except json.JSONDecodeError:
            send_result = {"raw": send_out.strip()[:500]}
    else:
        send_result = None

    state = {
        "schema_version": 1,
        "checked_at": checked_at,
        "status": current_status,
        "fingerprint": current_fingerprint,
        "items": items,
    }
    try:
        write_state(state_path, state)
    except OSError as exc:
        return 1, {"ok": False, "status": "state_write_failed", "error": str(exc)[:500]}
    result: dict[str, Any] = {
        "ok": True,
        "status": current_status,
        "changed": notify,
        "count": len(items),
        "state_path": str(state_path.expanduser()),
    }
    if send_result is not None:
        result["notification"] = send_result
    return 0, result


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checker", type=Path, default=script_dir / "check_deployed_binaries.py")
    parser.add_argument("--manifest", type=Path, default=script_dir / "ecosystem.yaml")
    parser.add_argument("--state", type=Path, default=Path.home() / ".rencrow/state/binary-drift-notifier.json")
    parser.add_argument("--core-cli", type=Path, default=Path.home() / ".local/bin/rencrow")
    parser.add_argument("--notification-dry-run", action="store_true")
    args = parser.parse_args()
    code, result = run_notifier(
        checker=args.checker,
        manifest=args.manifest,
        state_path=args.state,
        core_cli=args.core_cli,
        notification_dry_run=args.notification_dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())

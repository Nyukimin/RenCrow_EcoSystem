#!/usr/bin/env python3
"""Compare deployed RenCrow binaries against the ecosystem manifest pins.

`validate_ecosystem.py` checks the manifest against the source tree. This
script checks the manifest against what is actually installed and running,
which is the gap that let a 2026-08-03 rencrow-tts binary survive the
2026-08-08 pronunciation dictionary contract change and restart 225k times.

Every mapping is derived, not hand-maintained:

  systemd unit -> ExecStart path        (what is actually running)
  binary       -> main package, module, vcs.revision, vcs.modified
                                        (Go embeds this at build time)
  module       -> manifest component    (matched on the repository field)

Reporting is the default. Redeploying requires --apply and rebuilds from a
local clone checked out at the pinned commit, so an installed binary can never
inherit uncommitted local edits.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
from deployment_host_adapters import HostAdapter, SystemdUserAdapter, create_adapter

MATCH = "MATCH"
MISMATCH = "MISMATCH"
DIRTY = "DIRTY"
UNSTAMPED = "UNSTAMPED"
UNMAPPED = "UNMAPPED"

POLL_INTERVAL_SECONDS = 1
ONESHOT_TIMEOUT_SECONDS = 600

# Restarting CORE takes down Viewer, Agent, Chat, IdleChat and Memory at once,
# so --apply leaves it alone unless it is named explicitly.
GUARDED_COMPONENTS = {"core"}

BACKUP_DIR = Path.home() / ".rencrow" / "backups"
DEFAULT_RECEIPT_LOG = Path.home() / ".rencrow" / "receipts" / "binary-redeployment.jsonl"


def utc_timestamp() -> str:
    """Return a machine-readable UTC timestamp for a redeployment receipt."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def prepare_receipt_log(path: Path) -> None:
    """Ensure that the receipt log can be appended durably before mutation.

    The probe writes no record.  It creates a private parent directory and
    opens/fsyncs the log, so a receipt I/O failure is observed before build,
    backup, stop, or copy can change the host.
    """
    path = Path(path).expanduser()
    parent = path.parent
    if str(parent) not in {"", "."}:
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name != "nt":
            os.chmod(parent, 0o700)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        if os.name != "nt":
            os.chmod(path, 0o600)
        handle.flush()
        os.fsync(handle.fileno())


def append_receipt(path: Path, receipt: dict[str, Any]) -> None:
    """Append exactly one UTF-8 JSONL receipt and fsync it to the log."""
    path = Path(path).expanduser()
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        if os.name != "nt":
            os.chmod(path, 0o600)
        handle.write(json.dumps(receipt, ensure_ascii=False, separators=(",", ":")))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def new_receipt(row: dict[str, Any]) -> dict[str, Any]:
    """Build the stable receipt fields for one non-dry redeploy attempt."""
    return {
        "schema_version": 1,
        "receipt_id": uuid.uuid4().hex,
        "started_at": utc_timestamp(),
        "finished_at": "",
        "component": row["component"],
        "binary_path": str(row["binary"]),
        "from_revision": row.get("built", ""),
        "target_revision": row.get("pin", ""),
        "running_units": [],
        "phase": "preflight",
        "outcome": "failure",
        "rollback_outcome": "not_attempted",
    }


def set_receipt_failure(
    receipt: dict[str, Any],
    phase: str,
    error: str,
    failed_unit: str | None = None,
) -> None:
    """Set bounded failure information without exposing command secrets."""
    receipt["phase"] = phase
    receipt["outcome"] = "failure"
    if failed_unit:
        receipt["failed_unit"] = failed_unit
    receipt["error"] = error.strip()[:500]


def report_exit_code(rows: list[dict[str, Any]]) -> int:
    """Return non-zero unless every mapped Go binary is SHA-verifiable.

    UNMAPPED entries are outside this tool's contract.  MISMATCH, DIRTY, and
    UNSTAMPED are all actionable failures: either the pin differs or the
    deployed contents cannot be proven from the recorded revision.
    """
    failing = {MISMATCH, DIRTY, UNSTAMPED}
    return 1 if any(row["status"] in failing for row in rows) else 0


def run(cmd: list[str], cwd: str | None = None, timeout: int = 600) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
    )
    return proc.returncode, proc.stdout, proc.stderr


def systemd_units(prefix: str) -> list[str]:
    code, out, _ = run(
        ["systemctl", "--user", "list-unit-files", f"{prefix}*.service",
         "--no-pager", "--plain", "--no-legend"]
    )
    if code != 0:
        return []
    units = []
    for line in out.splitlines():
        fields = line.split()
        if fields and fields[0].endswith(".service"):
            units.append(fields[0])
    return units


def parse_exec_start_path(rendered: str) -> str | None:
    """Return the executable path from systemd's rendered ``ExecStart``.

    The checker follows the executable directly for ordinary units.  The
    lyrics collector is intentionally wrapped in the bounded form
    ``flock -n LOCK COMMAND ...``; in that case return the command path so its
    Go build stamp can still be inspected.  Any other flock shape remains
    visible as the wrapper instead of guessing which argument is executable.
    """
    # systemd renders ExecStart as "{ path=/usr/bin/foo ; argv[]=... ; ... }",
    # so the path token carries the leading brace.
    match = re.search(r"\bpath=([^\s;]+)", rendered)
    if not match:
        return None

    wrapper = match.group(1)
    if os.path.basename(wrapper) != "flock":
        return wrapper

    argv_match = re.search(
        r"\bargv\[\]=(.+?)(?:\s*;\s*|\s*}\s*$)", rendered
    )
    if not argv_match:
        return wrapper
    try:
        argv = shlex.split(argv_match.group(1).strip())
    except ValueError:
        return wrapper

    if len(argv) < 4 or argv[0] != wrapper or argv[1] != "-n":
        return wrapper
    if argv[2] in {"", ";", "}"} or argv[3] in {"", ";", "}"}:
        return wrapper
    return argv[3]


def unit_exec_path(unit: str) -> str | None:
    code, out, _ = run(["systemctl", "--user", "show", unit, "-p", "ExecStart", "--value"])
    if code != 0:
        return None
    return parse_exec_start_path(out)


def build_info(binary: str) -> dict[str, Any] | None:
    """Read the Go build stamp. Returns None for non-Go files."""
    code, out, _ = run(["go", "version", "-m", binary], timeout=60)
    if code != 0 or "\tpath\t" not in out:
        return None
    info: dict[str, Any] = {"main_package": "", "module": "", "revision": "", "modified": None}
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        key, value = parts[1], parts[2]
        if key == "path":
            info["main_package"] = value.strip()
        elif key == "mod":
            info["module"] = value.strip()
        elif key == "build":
            if value.startswith("vcs.revision="):
                info["revision"] = value.split("=", 1)[1].strip()
            elif value.startswith("vcs.modified="):
                info["modified"] = value.split("=", 1)[1].strip() == "true"
    return info


def load_components(manifest: Path) -> dict[str, dict[str, Any]]:
    with manifest.open(encoding="utf-8") as handle:
        return json.load(handle).get("components", {})


def match_component(module: str, components: dict[str, dict[str, Any]]) -> str | None:
    """Map a Go module path to a manifest component id via its repository.

    A module may sit in a subdirectory of its repository (RenCrow_TTS keeps its
    module under gateway/), so a prefix match is required. The longest match
    wins so a nested module never resolves to its parent repository.
    """
    best: tuple[int, str] | None = None
    for comp_id, comp in components.items():
        repo = comp.get("repository")
        if not repo:
            continue
        root = f"github.com/{repo}"
        if module == root or module.startswith(root + "/"):
            if best is None or len(root) > best[0]:
                best = (len(root), comp_id)
    return best[1] if best else None


def commits_between(module_dir: Path, old: str, new: str) -> int | None:
    code, out, _ = run(["git", "-C", str(module_dir), "rev-list", "--count", f"{old}..{new}"])
    if code != 0:
        return None
    try:
        return int(out.strip())
    except ValueError:
        return None


def collect(
    manifest: Path,
    workspace: Path,
    prefix: str,
    adapter: HostAdapter | None = None,
) -> list[dict[str, Any]]:
    adapter = adapter or SystemdUserAdapter(run)
    components = load_components(manifest)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for unit in adapter.services(prefix):
        binary = adapter.exec_path(unit)
        if not binary or not os.path.exists(binary):
            continue
        if binary in seen:
            # Several units may share one binary (trade and trade-learning do).
            for row in rows:
                if row["binary"] == binary:
                    row["units"].append(unit)
            continue
        seen.add(binary)

        row: dict[str, Any] = {
            "artifact_kind": "go_binary",
            "units": [unit],
            "binary": binary,
            "name": os.path.basename(binary),
            "component": None,
            "module": "",
            "main_package": "",
            "built": "",
            "pin": "",
            "modified": None,
            "behind": None,
            "status": UNMAPPED,
            "note": "",
        }

        info = build_info(binary)
        if info is None:
            row["note"] = "Go以外のバイナリ (対象外)"
            rows.append(row)
            continue

        row["module"] = info["module"]
        row["main_package"] = info["main_package"]
        row["built"] = info["revision"]
        row["modified"] = info["modified"]

        comp_id = match_component(info["module"], components)
        if comp_id is None:
            row["note"] = "manifestに対応componentなし"
            rows.append(row)
            continue

        row["component"] = comp_id
        row["pin"] = components[comp_id].get("version", "")

        if not info["revision"]:
            row["status"] = UNSTAMPED
            row["note"] = "vcs情報なし。SHAで検証できない"
            rows.append(row)
            continue

        if row["pin"] == row["built"]:
            row["status"] = DIRTY if info["modified"] else MATCH
            if info["modified"]:
                row["note"] = "pinと同一SHAだが未コミット差分入りでビルドされている"
        else:
            row["status"] = MISMATCH
            module_dir = workspace / components[comp_id]["workspace_path"]
            behind = commits_between(module_dir, row["built"], row["pin"])
            row["behind"] = behind
            if behind is None:
                row["note"] = "ビルド元revisionがローカルに存在しない"
            else:
                row["note"] = f"pinより{behind} commits前"
                if info["modified"]:
                    row["note"] += " / 未コミット差分入り"
        rows.append(row)

    managed = collect_managed_files(components, workspace)
    managed_by_path = {row["binary"]: row for row in managed}
    remaining: list[dict[str, Any]] = []
    for row in rows:
        managed_row = managed_by_path.get(row["binary"])
        if managed_row is not None and row["status"] == UNMAPPED:
            managed_row["units"].extend(row["units"])
            continue
        remaining.append(row)
    remaining.extend(managed)
    return remaining


def _installed_file_path(raw: str, workspace: Path) -> Path:
    if raw.startswith("%h/"):
        return Path.home() / Path(raw[len("%h/"):])
    if raw.startswith("%workspace%/"):
        return workspace / Path(raw[len("%workspace%/"):])
    raise ValueError(f"unsupported installed_path: {raw}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_blob(module_dir: Path, revision: str, source_path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(module_dir), "show", f"{revision}:{source_path}"],
        capture_output=True,
        timeout=60,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise OSError(detail or "git show failed")
    return result.stdout


def collect_managed_files(
    components: dict[str, dict[str, Any]], workspace: Path
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for component_id, component in components.items():
        deployment = component.get("deployment")
        files = deployment.get("files", []) if isinstance(deployment, dict) else []
        for artifact in files:
            installed = _installed_file_path(artifact["installed_path"], workspace)
            expected = artifact["sha256"]
            actual = _sha256_file(installed) if installed.is_file() else ""
            rows.append({
                "artifact_kind": "managed_file",
                "units": [],
                "binary": str(installed),
                "name": installed.name,
                "component": component_id,
                "module": "",
                "main_package": artifact["source_path"],
                "built": actual,
                "pin": expected,
                "modified": None,
                "behind": None,
                "status": MATCH if actual == expected else MISMATCH,
                "note": "content hash一致" if actual == expected else (
                    "配置fileが存在しない" if not actual else "content hash不一致"
                ),
                "source_path": artifact["source_path"],
                "mode": artifact["mode"],
            })
    return rows


def _systemd_properties(
    unit: str, runner: Any, adapter: HostAdapter | None = None
) -> dict[str, str] | None:
    if adapter is not None:
        return adapter.properties(unit)
    code, output, _ = runner(
        [
            "systemctl",
            "--user",
            "show",
            unit,
            "-p",
            "ActiveState",
            "-p",
            "SubState",
            "-p",
            "Result",
            "-p",
            "ExecMainStatus",
            "-p",
            "NRestarts",
        ]
    )
    if code != 0:
        return None
    properties: dict[str, str] = {}
    for line in output.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            properties[key] = value.strip()
    return properties


def _dotted_json_value(payload: Any, path: str) -> Any:
    current = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return _MISSING_JSON_VALUE
        current = current[part]
    return current


_MISSING_JSON_VALUE = object()


def _json_scalar_equal(actual: Any, expected: Any) -> bool:
    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is type(expected) and actual == expected
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return actual == expected
    return type(actual) is type(expected) and actual == expected


def _http_readiness_ok(
    contract: dict[str, Any],
    opener: Any,
) -> bool:
    response: Any = None
    try:
        timeout = min(5, int(contract["timeout_seconds"]))
        response = opener(contract["url"], timeout=timeout)
        status = getattr(response, "status", None)
        if status is None and hasattr(response, "getcode"):
            status = response.getcode()
        if not isinstance(status, int) or not 200 <= status < 300:
            return False
        raw_body = response.read()
        if isinstance(raw_body, bytes):
            raw_body = raw_body.decode("utf-8")
        payload = json.loads(raw_body)
        expected = contract["expect"]
        actual = _dotted_json_value(payload, expected["path"])
        return (
            actual is not _MISSING_JSON_VALUE
            and _json_scalar_equal(actual, expected["equals"])
        )
    except (
        OSError,
        ValueError,
        TypeError,
        UnicodeError,
        json.JSONDecodeError,
        TimeoutError,
        urllib.error.URLError,
    ):
        return False
    finally:
        if response is not None and hasattr(response, "close"):
            response.close()


def start_and_settle(
    units: list[str],
    contracts: dict[str, dict[str, Any]],
    *,
    runner: Any | None = None,
    http_opener: Any | None = None,
    sleep_fn: Any | None = None,
    clock: Any | None = None,
    adapter: HostAdapter | None = None,
) -> str | None:
    """Start units and require their manifest-owned readiness contracts.

    HTTP units must return a 2xx JSON response whose dotted path equals the
    manifest scalar.  Oneshot units must finish inactive/dead with a successful
    systemd result and exit status zero.  A missing contract is a hard failure
    before any unit is started.
    """
    runner = runner or run
    adapter = adapter or SystemdUserAdapter(runner)

    missing = [unit for unit in units if unit not in contracts]
    if missing:
        print(f"  readiness contract が無いunit: {', '.join(missing)}", flush=True)
        return missing[0]

    for unit in units:
        adapter.reset_failed(unit)
        code, _, err = adapter.start(unit)
        if code != 0:
            print(f"  {unit} の起動コマンドが失敗: {err.strip()[:200]}", flush=True)
            return unit

    return wait_for_readiness(
        units,
        contracts,
        runner=runner,
        http_opener=http_opener,
        sleep_fn=sleep_fn,
        clock=clock,
        adapter=adapter,
    )


def wait_for_readiness(
    units: list[str],
    contracts: dict[str, dict[str, Any]],
    *,
    runner: Any | None = None,
    http_opener: Any | None = None,
    sleep_fn: Any | None = None,
    clock: Any | None = None,
    adapter: HostAdapter | None = None,
) -> str | None:
    """Poll manifest readiness without changing unit state."""
    runner = runner or run
    http_opener = http_opener or urllib.request.urlopen
    sleep_fn = sleep_fn or time.sleep
    clock = clock or time.monotonic
    adapter = adapter or SystemdUserAdapter(runner)

    missing = [unit for unit in units if unit not in contracts]
    if missing:
        print(f"  readiness contract が無いunit: {', '.join(missing)}", flush=True)
        return missing[0]

    started_at = {unit: clock() for unit in units}
    pending = set(units)
    while pending:
        now = clock()
        for unit in list(pending):
            contract = contracts[unit]
            properties = _systemd_properties(unit, runner, adapter)
            if properties is None:
                print(f"  {unit} のsystemd状態を取得できません", flush=True)
                return unit

            state = properties.get("ActiveState", "")
            sub_state = properties.get("SubState", "")
            if state == "failed" or sub_state == "auto-restart":
                print(f"  {unit} -> {state}/{sub_state}", flush=True)
                return unit

            if contract["kind"] == "oneshot":
                successful = (
                    state == "inactive"
                    and sub_state == "dead"
                    and properties.get("Result") == "success"
                    and properties.get("ExecMainStatus") == "0"
                )
                if successful:
                    pending.remove(unit)
                    continue
                if (
                    state == "inactive"
                    and sub_state == "dead"
                    and (
                        properties.get("Result") not in {"", "success"}
                        or properties.get("ExecMainStatus") not in {"", "0"}
                    )
                ):
                    print(f"  {unit} -> {state}/{sub_state} result={properties.get('Result')}", flush=True)
                    return unit
                timeout = ONESHOT_TIMEOUT_SECONDS
            else:
                timeout = int(contract["timeout_seconds"])
                if state not in {"active", "activating", "reloading"}:
                    print(f"  {unit} -> {state}/{sub_state}", flush=True)
                    return unit
                if _http_readiness_ok(contract, http_opener):
                    pending.remove(unit)
                    continue

            if clock() - started_at[unit] >= timeout:
                print(f"  {unit} readiness timeout ({timeout}s)", flush=True)
                return unit

        if pending:
            next_timeout = min(
                (
                    int(contracts[unit].get("timeout_seconds", ONESHOT_TIMEOUT_SECONDS))
                    - (clock() - started_at[unit])
                    for unit in pending
                ),
                default=POLL_INTERVAL_SECONDS,
            )
            sleep_fn(max(0, min(POLL_INTERVAL_SECONDS, next_timeout)))

    for unit in units:
        properties = _systemd_properties(unit, runner, adapter) or {}
        print(
            f"  {unit} -> {properties.get('ActiveState', '')} "
            f"(NRestarts={properties.get('NRestarts', '')})",
            flush=True,
        )
    return None


def _running_units(
    units: list[str], runner: Any, adapter: HostAdapter | None = None
) -> list[str] | None:
    adapter = adapter or SystemdUserAdapter(runner)
    running: list[str] = []
    for unit in units:
        properties = adapter.properties(unit)
        if properties is None:
            print(f"  {unit} のsystemd状態を取得できないため中止します", flush=True)
            return None
        if properties.get("ActiveState") in ("active", "activating", "reloading"):
            running.append(unit)
        else:
            print(f"  {unit} は停止中のまま据え置きます", flush=True)
    return running


def _unit_contracts(
    component: dict[str, Any],
    units: list[str],
    adapter: HostAdapter | None = None,
) -> dict[str, dict[str, Any]] | None:
    adapter = adapter or SystemdUserAdapter(run)
    deployment = component.get("deployment")
    raw_contracts = deployment.get("user_systemd") if isinstance(deployment, dict) else None
    if not isinstance(raw_contracts, list):
        return None if units else {}
    contracts: dict[str, dict[str, Any]] = {}
    for contract in raw_contracts:
        if not isinstance(contract, dict):
            continue
        contract_unit = contract.get("unit")
        for unit in units:
            if isinstance(contract_unit, str) and contract_unit == adapter.contract_unit(unit):
                if unit in contracts:
                    return None
                contracts[unit] = contract
                break
    return contracts if len(contracts) == len(units) else None


def check_declared_readiness(
    rows: list[dict[str, Any]],
    components: dict[str, dict[str, Any]],
    *,
    runner: Any | None = None,
    adapter: HostAdapter | None = None,
) -> bool:
    """Check deployed mapped units without starting, stopping, or resetting them."""
    runner = runner or run
    adapter = adapter or SystemdUserAdapter(runner)
    checked = 0
    for row in rows:
        if row.get("artifact_kind") == "managed_file":
            continue
        component_id = row.get("component")
        if not isinstance(component_id, str) or component_id not in components:
            continue
        contracts = _unit_contracts(components[component_id], row["units"], adapter)
        if contracts is None:
            print(
                f"[NG] {row['name']}: unitのreadiness contractが不足しています",
                flush=True,
            )
            return False

        units: list[str] = []
        for unit in row["units"]:
            contract = contracts[unit]
            if contract["kind"] == "http_json":
                units.append(unit)
                continue
            properties = adapter.properties(unit)
            if properties is None:
                print(f"[NG] {unit}: systemd状態を取得できません", flush=True)
                return False
            if properties.get("ActiveState") in {"active", "activating", "reloading"}:
                units.append(unit)

        if not units:
            continue
        print(f"readiness: {row['name']} ({', '.join(units)})", flush=True)
        if wait_for_readiness(units, contracts, runner=runner, adapter=adapter):
            return False
        checked += len(units)

    print(f"readiness OK: {checked} unit(s)", flush=True)
    return True


class _RedeployAbort(Exception):
    """Internal control flow for a recorded redeployment failure."""

    def __init__(
        self,
        phase: str,
        error: str,
        failed_unit: str | None = None,
        rollback_outcome: str | None = None,
    ) -> None:
        super().__init__(error)
        self.phase = phase
        self.error = error
        self.failed_unit = failed_unit
        self.rollback_outcome = rollback_outcome


class _RedeployDeferred(Exception):
    """Stop before mutation because an owner job is currently in progress."""

    def __init__(self, units: list[str]) -> None:
        super().__init__("稼働中oneshotの完了待ち: " + ", ".join(units))
        self.units = units


def _atomic_copy(
    source: str | Path,
    destination: str | Path,
    *,
    mode: int,
) -> None:
    """Copy an artifact beside its destination, then replace it atomically."""
    destination_path = Path(destination)
    handle, raw_tmp = tempfile.mkstemp(
        prefix=f".{destination_path.name}.",
        dir=destination_path.parent,
    )
    temporary = Path(raw_tmp)
    try:
        os.close(handle)
        shutil.copy2(source, temporary)
        os.chmod(temporary, mode)
        os.replace(temporary, destination_path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def redeploy(
    row: dict[str, Any],
    components: dict[str, dict[str, Any]],
    workspace: Path,
    dry: bool,
    *,
    runner: Any | None = None,
    receipt_log: Path | None = None,
    adapter: HostAdapter | None = None,
) -> bool:
    """Rebuild one component at its pinned commit and reinstall it."""
    runner = runner or run
    adapter = adapter or SystemdUserAdapter(runner)
    comp = components[row["component"]]
    module_dir = workspace / comp["workspace_path"]
    pin = row["pin"]
    repo_root = f"github.com/{comp['repository']}"
    module_rel = row["module"][len(repo_root):].lstrip("/")
    main_rel = row["main_package"][len(row["module"]):].lstrip("/")
    target = "./" + main_rel if main_rel else "."

    if dry:
        print(f"  [DRY] {module_dir}@{pin[:7]} の local clone で {target} をビルドし "
              f"{row['binary']} へ設置、{', '.join(row['units'])} を再起動", flush=True)
        return True

    receipt_path = Path(receipt_log or DEFAULT_RECEIPT_LOG).expanduser()
    receipt = new_receipt(row)
    try:
        # This is deliberately before any build, backup, stop, or copy.  The
        # probe creates no JSONL record; the completed attempt appends exactly
        # one below after the outcome is known.
        prepare_receipt_log(receipt_path)
    except (OSError, ValueError, TypeError) as exc:
        print(f"  [NG] receipt logを準備できません。バイナリを変更しません: {exc}",
              flush=True)
        return False

    # A linked worktree keeps .git as a file, and Go silently omits the VCS
    # stamp when it sees that, which would make every rebuilt binary
    # unverifiable. A local clone has a real .git directory, so stamping works
    # and the checkout is guaranteed clean.
    tmp: str | None = None
    phase = "preflight"
    result = False
    try:
        # Resolve the readiness contract before any build, backup, stop, or
        # copy. A missing contract must never leave a binary half-replaced.
        running = _running_units(row["units"], runner, adapter)
        receipt["running_units"] = running or []
        if running is None:
            raise _RedeployAbort(
                "preflight", "稼働状態を確認できません。バイナリを変更しません"
            )
        readiness = _unit_contracts(comp, running, adapter)
        if readiness is None:
            missing = [unit for unit in running if not _unit_contracts(comp, [unit], adapter)]
            raise _RedeployAbort(
                "preflight",
                "稼働中unitにreadiness contractがありません: "
                + ", ".join(missing or running),
                missing[0] if missing else running[0],
            )
        active_oneshots = [
            unit for unit in running if readiness[unit].get("kind") == "oneshot"
        ]
        if active_oneshots:
            raise _RedeployDeferred(active_oneshots)

        code, _, _ = runner(
            ["git", "-C", str(module_dir), "cat-file", "-e", f"{pin}^{{commit}}"]
        )
        if code != 0:
            raise _RedeployAbort(
                "preflight", f"pin {pin[:7]} がローカルに存在しない。fetchが必要"
            )

        phase = "build"
        tmp = tempfile.mkdtemp(prefix="rencrow-redeploy-")
        checkout = os.path.join(tmp, "src")
        staged = os.path.join(tmp, "_staged_binary")
        code, _, err = runner(["git", "clone", "--local", "--no-checkout",
                               str(module_dir), checkout], timeout=900)
        if code != 0:
            raise _RedeployAbort("build", f"clone失敗: {err.strip()[:300]}")
        code, _, err = runner(["git", "-C", checkout, "checkout", "--detach", pin])
        if code != 0:
            raise _RedeployAbort(
                "build", f"pin {pin[:7]} のcheckout失敗: {err.strip()[:300]}"
            )

        build_dir = os.path.join(checkout, module_rel) if module_rel else checkout
        print(f"  ビルド中 {target} @ {pin[:7]} ...", flush=True)
        code, _, err = runner(["go", "build", "-o", staged, target], cwd=build_dir)
        if code != 0:
            raise _RedeployAbort("build", f"ビルド失敗: {err.strip()[:400]}")

        # A rebuild that does not actually clear the drift is worse than none,
        # so the new binary is verified before anything on the host is touched.
        fresh = build_info(staged)
        if not fresh or fresh["revision"] != pin or fresh["modified"]:
            got = (fresh or {}).get("revision", "?")[:7]
            raise _RedeployAbort(
                "build",
                f"ビルド結果が pin と一致しない (built={got}, "
                f"dirty={(fresh or {}).get('modified')})",
            )

        phase = "backup"
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup = BACKUP_DIR / f"{row['name']}.replaced-{row['built'][:7] or 'unstamped'}"
        shutil.copy2(row["binary"], backup)
        receipt["backup_path"] = str(backup)
        print(f"  旧バイナリを退避: {backup}", flush=True)

        phase = "stop"
        for unit in row["units"]:
            adapter.stop(unit)
        phase = "copy"
        _atomic_copy(staged, row["binary"], mode=0o755)

        phase = "readiness"
        broken = start_and_settle(running, readiness, runner=runner, adapter=adapter)
        if broken:
            print(f"  [NG] {broken} が新バイナリで安定しません。ロールバックします",
                  flush=True)
            phase = "rollback"
            try:
                for unit in row["units"]:
                    adapter.stop(unit)
                _atomic_copy(backup, row["binary"], mode=0o755)
                still_broken = start_and_settle(running, readiness, runner=runner, adapter=adapter)
            except Exception as exc:
                raise _RedeployAbort(
                    "rollback",
                    f"{broken} のreadiness失敗。ロールバック失敗: {exc}",
                    broken,
                    "failed",
                ) from exc
            if still_broken:
                print(f"  [NG] ロールバック後も {still_broken} が復帰しません。"
                      f"退避先: {backup}", flush=True)
                raise _RedeployAbort(
                    "rollback",
                    f"{broken} のreadiness失敗。ロールバック後も "
                    f"{still_broken} が復帰しません。退避先: {backup}",
                    broken,
                    "failed",
                )
            print(f"  [OK] {row['built'][:7]} へ巻き戻し、稼働を確認しました",
                  flush=True)
            raise _RedeployAbort(
                "rollback",
                f"{broken} のreadiness失敗。旧バイナリへ巻き戻しました",
                broken,
                "success",
            )

        receipt["phase"] = "complete"
        receipt["outcome"] = "success"
        print(f"  [OK] {row['name']} を {pin[:7]} へ更新", flush=True)
        result = True
    except _RedeployDeferred as exc:
        receipt["phase"] = "preflight"
        receipt["outcome"] = "deferred"
        receipt["deferred_units"] = exc.units
        receipt["reason"] = str(exc)[:500]
        print(f"  [DEFER] {exc}", flush=True)
    except _RedeployAbort as exc:
        set_receipt_failure(receipt, exc.phase, exc.error, exc.failed_unit)
        if exc.rollback_outcome is not None:
            receipt["rollback_outcome"] = exc.rollback_outcome
        print(f"  [NG] {exc.error}", flush=True)
    except Exception as exc:
        set_receipt_failure(receipt, phase, str(exc))
        print(f"  [NG] {phase}: {exc}", flush=True)
    finally:
        receipt["finished_at"] = utc_timestamp()
        try:
            append_receipt(receipt_path, receipt)
        except (OSError, ValueError, TypeError) as exc:
            # The preflight probe makes this exceptional, but a final write
            # failure must never be reported as a successful redeployment.
            print(f"  [NG] receiptを書き込めませんでした: {exc}", flush=True)
            result = False
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)
    return result


def redeploy_managed_file(
    row: dict[str, Any],
    components: dict[str, dict[str, Any]],
    workspace: Path,
    dry: bool,
    *,
    runner: Any | None = None,
    blob_loader: Any | None = None,
    receipt_log: Path | None = None,
) -> bool:
    """Install one manifest-hashed file from the component's pinned Git blob."""
    runner = runner or run
    blob_loader = blob_loader or _git_blob
    component = components[row["component"]]
    module_dir = workspace / component["workspace_path"]
    pin = component["version"]
    source_path = row["source_path"]
    target = Path(row["binary"])
    if dry:
        print(f"  [DRY] {module_dir}@{pin[:7]}:{source_path} を {target} へ配置", flush=True)
        return True

    receipt_path = Path(receipt_log or DEFAULT_RECEIPT_LOG).expanduser()
    receipt = new_receipt(row)
    receipt["source_path"] = source_path
    try:
        prepare_receipt_log(receipt_path)
    except (OSError, ValueError, TypeError) as exc:
        print(f"  [NG] receipt logを準備できません。fileを変更しません: {exc}", flush=True)
        return False

    result = False
    phase = "preflight"
    tmp: Path | None = None
    try:
        code, _, error = runner(
            ["git", "-C", str(module_dir), "cat-file", "-e", f"{pin}:{source_path}"]
        )
        if code != 0:
            raise _RedeployAbort("preflight", f"pinned sourceを読めません: {error.strip()[:300]}")
        content = blob_loader(module_dir, pin, source_path)
        actual_hash = hashlib.sha256(content).hexdigest()
        if actual_hash != row["pin"]:
            raise _RedeployAbort(
                "preflight",
                f"pinned source hashがmanifestと不一致 ({actual_hash[:7]} != {row['pin'][:7]})",
            )

        phase = "backup"
        if target.exists():
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            backup = BACKUP_DIR / f"{row['name']}.replaced-{row['built'][:7] or 'missing'}"
            shutil.copy2(target, backup)
            receipt["backup_path"] = str(backup)

        phase = "install"
        target.parent.mkdir(parents=True, exist_ok=True)
        handle, raw_tmp = tempfile.mkstemp(prefix=target.name + ".", dir=target.parent)
        tmp = Path(raw_tmp)
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, int(row["mode"], 8))
        os.replace(tmp, target)
        tmp = None
        if _sha256_file(target) != row["pin"]:
            raise _RedeployAbort("verify", "配置後content hashが一致しません")
        receipt["phase"] = "complete"
        receipt["outcome"] = "success"
        print(f"  [OK] {row['name']} を content hash {row['pin'][:7]} へ更新", flush=True)
        result = True
    except _RedeployAbort as exc:
        set_receipt_failure(receipt, exc.phase, exc.error)
        print(f"  [NG] {exc.error}", flush=True)
    except Exception as exc:
        set_receipt_failure(receipt, phase, str(exc))
        print(f"  [NG] {phase}: {exc}", flush=True)
    finally:
        if tmp is not None:
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass
        receipt["finished_at"] = utc_timestamp()
        try:
            append_receipt(receipt_path, receipt)
        except (OSError, ValueError, TypeError) as exc:
            print(f"  [NG] receiptを書き込めませんでした: {exc}", flush=True)
            result = False
    return result


def render(rows: list[dict[str, Any]]) -> None:
    width = max([len(r["name"]) for r in rows] + [8])
    print(f"{'BINARY'.ljust(width)}  {'COMPONENT':<11} {'BUILT':<8} {'PIN':<8} "
          f"{'STATUS':<9} NOTE")
    for row in rows:
        print(f"{row['name'].ljust(width)}  "
              f"{(row['component'] or '-'):<11} "
              f"{(row['built'][:7] or '-'):<8} "
              f"{(row['pin'][:7] or '-'):<8} "
              f"{row['status']:<9} {row['note']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="配置済みバイナリと ecosystem manifest の pin を突き合わせる")
    parser.add_argument("manifest", nargs="?", default="ecosystem.yaml")
    parser.add_argument("--workspace", default=None,
                        help="catalog root (既定: manifestのあるディレクトリ)")
    parser.add_argument("--prefix", default="rencrow",
                        help="対象native service identityの接頭辞")
    parser.add_argument(
        "--host-adapter",
        choices=("auto", "systemd", "windows", "launchd"),
        default="auto",
        help="native service manager (既定: OSから自動判定)",
    )
    parser.add_argument("--json", action="store_true", help="JSONで出力する")
    parser.add_argument("--apply", action="store_true",
                        help="MISMATCH を pin の local clone から再ビルドして再配置する")
    parser.add_argument("--check-readiness", action="store_true",
                        help="配置済みunitを変更せずmanifest readinessを確認する")
    parser.add_argument("--dry-run", action="store_true",
                        help="--apply の実行計画だけを表示する")
    parser.add_argument("--only", default="",
                        help="対象componentをカンマ区切りで限定する")
    parser.add_argument(
        "--receipt-log",
        default=str(DEFAULT_RECEIPT_LOG),
        help="再配置receiptのJSONL path",
    )
    args = parser.parse_args()
    if args.apply and args.check_readiness:
        parser.error("--apply と --check-readiness は同時に指定できません")

    manifest = Path(args.manifest).resolve()
    if not manifest.exists():
        print(f"manifest not found: {manifest}", file=sys.stderr)
        return 2
    workspace = Path(args.workspace).resolve() if args.workspace else manifest.parent

    adapter = create_adapter(args.host_adapter, run)
    rows = collect(manifest, workspace, args.prefix, adapter)
    if not rows:
        print("対象unitが見つかりません", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        render(rows)

    drifted = [r for r in rows if r["status"] == MISMATCH]
    if not args.json:
        print()
        print(f"MATCH {len([r for r in rows if r['status'] == MATCH])} / "
              f"MISMATCH {len(drifted)} / DIRTY "
              f"{len([r for r in rows if r['status'] == DIRTY])} / "
              f"UNSTAMPED {len([r for r in rows if r['status'] == UNSTAMPED])}")

    if args.apply:
        only = {s.strip() for s in args.only.split(",") if s.strip()}
        components = load_components(manifest)
        # An UNSTAMPED binary carries no revision, so drift cannot be measured
        # at all. Rebuilding is the only way to make it verifiable, but that is
        # a judgement call rather than a detected mismatch, so it is only done
        # for a component named explicitly.
        candidates = list(drifted)
        if only:
            candidates += [r for r in rows
                           if r["status"] == UNSTAMPED and r["component"] in only]

        targets = []
        for row in candidates:
            if only and row["component"] not in only:
                continue
            if row["component"] in GUARDED_COMPONENTS and row["component"] not in only:
                print(f"\n[SKIP] {row['name']}: {row['component']} は --only "
                      f"{row['component']} で明示した場合だけ再配置します", flush=True)
                continue
            targets.append(row)

        if not targets:
            print("\n再配置対象はありません")
        failed = 0
        for row in targets:
            print(f"\n=== {row['name']} ({row['component']}) "
                  f"{row['built'][:7]} -> {row['pin'][:7]} ===", flush=True)
            deployer = redeploy_managed_file if row.get("artifact_kind") == "managed_file" else redeploy
            deploy_kwargs: dict[str, Any] = {"receipt_log": Path(args.receipt_log)}
            if deployer is redeploy:
                deploy_kwargs["adapter"] = adapter
            if not deployer(row, components, workspace, args.dry_run, **deploy_kwargs):
                failed += 1
        if failed:
            return 1
        return 0

    if args.check_readiness:
        components = load_components(manifest)
        return 0 if check_declared_readiness(rows, components, adapter=adapter) else 1

    return report_exit_code(rows)


if __name__ == "__main__":
    sys.exit(main())

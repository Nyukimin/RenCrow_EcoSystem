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
from pathlib import Path
from typing import Any

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


def collect(manifest: Path, workspace: Path, prefix: str) -> list[dict[str, Any]]:
    components = load_components(manifest)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for unit in sorted(systemd_units(prefix)):
        binary = unit_exec_path(unit)
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

    return rows


def _systemd_properties(unit: str, runner: Any) -> dict[str, str] | None:
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
) -> str | None:
    """Start units and require their manifest-owned readiness contracts.

    HTTP units must return a 2xx JSON response whose dotted path equals the
    manifest scalar.  Oneshot units must finish inactive/dead with a successful
    systemd result and exit status zero.  A missing contract is a hard failure
    before any unit is started.
    """
    runner = runner or run

    missing = [unit for unit in units if unit not in contracts]
    if missing:
        print(f"  readiness contract が無いunit: {', '.join(missing)}", flush=True)
        return missing[0]

    for unit in units:
        runner(["systemctl", "--user", "reset-failed", unit])
        code, _, err = runner(["systemctl", "--user", "start", unit])
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
    )


def wait_for_readiness(
    units: list[str],
    contracts: dict[str, dict[str, Any]],
    *,
    runner: Any | None = None,
    http_opener: Any | None = None,
    sleep_fn: Any | None = None,
    clock: Any | None = None,
) -> str | None:
    """Poll manifest readiness without changing unit state."""
    runner = runner or run
    http_opener = http_opener or urllib.request.urlopen
    sleep_fn = sleep_fn or time.sleep
    clock = clock or time.monotonic

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
            properties = _systemd_properties(unit, runner)
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
        properties = _systemd_properties(unit, runner) or {}
        print(
            f"  {unit} -> {properties.get('ActiveState', '')} "
            f"(NRestarts={properties.get('NRestarts', '')})",
            flush=True,
        )
    return None


def _running_units(units: list[str], runner: Any) -> list[str] | None:
    running: list[str] = []
    for unit in units:
        code, state, _ = runner(
            ["systemctl", "--user", "show", unit, "-p", "ActiveState", "--value"]
        )
        if code != 0:
            print(f"  {unit} のsystemd状態を取得できないため中止します", flush=True)
            return None
        if state.strip() in ("active", "activating", "reloading"):
            running.append(unit)
        else:
            print(f"  {unit} は停止中のまま据え置きます", flush=True)
    return running


def _unit_contracts(
    component: dict[str, Any],
    units: list[str],
) -> dict[str, dict[str, Any]] | None:
    deployment = component.get("deployment")
    raw_contracts = deployment.get("user_systemd") if isinstance(deployment, dict) else None
    if not isinstance(raw_contracts, list):
        return None if units else {}
    contracts: dict[str, dict[str, Any]] = {}
    for contract in raw_contracts:
        if not isinstance(contract, dict):
            continue
        unit = contract.get("unit")
        if isinstance(unit, str) and unit in units:
            if unit in contracts:
                return None
            contracts[unit] = contract
    return contracts if len(contracts) == len(units) else None


def check_declared_readiness(
    rows: list[dict[str, Any]],
    components: dict[str, dict[str, Any]],
    *,
    runner: Any | None = None,
) -> bool:
    """Check deployed mapped units without starting, stopping, or resetting them."""
    runner = runner or run
    checked = 0
    for row in rows:
        component_id = row.get("component")
        if not isinstance(component_id, str) or component_id not in components:
            continue
        contracts = _unit_contracts(components[component_id], row["units"])
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
            code, state, _ = runner(
                ["systemctl", "--user", "show", unit, "-p", "ActiveState", "--value"]
            )
            if code != 0:
                print(f"[NG] {unit}: systemd状態を取得できません", flush=True)
                return False
            if state.strip() in {"active", "activating", "reloading"}:
                units.append(unit)

        if not units:
            continue
        print(f"readiness: {row['name']} ({', '.join(units)})", flush=True)
        if wait_for_readiness(units, contracts, runner=runner):
            return False
        checked += len(units)

    print(f"readiness OK: {checked} unit(s)", flush=True)
    return True


def redeploy(
    row: dict[str, Any],
    components: dict[str, dict[str, Any]],
    workspace: Path,
    dry: bool,
    *,
    runner: Any | None = None,
) -> bool:
    """Rebuild one component at its pinned commit and reinstall it."""
    runner = runner or run
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

    # Resolve the readiness contract before any build, backup, stop, or copy.
    # A missing contract must never leave a binary half-replaced.
    running = _running_units(row["units"], runner)
    if running is None:
        print("  [NG] 稼働状態を確認できません。バイナリを変更しません", flush=True)
        return False
    readiness = _unit_contracts(comp, running)
    if readiness is None:
        missing = [unit for unit in running if not _unit_contracts(comp, [unit])]
        print(f"  [NG] 稼働中unitにreadiness contractがありません: "
              f"{', '.join(missing or running)}", flush=True)
        return False

    code, _, _ = runner(
        ["git", "-C", str(module_dir), "cat-file", "-e", f"{pin}^{{commit}}"]
    )
    if code != 0:
        print(f"  [NG] pin {pin[:7]} がローカルに存在しない。fetchが必要", flush=True)
        return False

    # A linked worktree keeps .git as a file, and Go silently omits the VCS
    # stamp when it sees that, which would make every rebuilt binary
    # unverifiable. A local clone has a real .git directory, so stamping works
    # and the checkout is guaranteed clean.
    tmp = tempfile.mkdtemp(prefix="rencrow-redeploy-")
    checkout = os.path.join(tmp, "src")
    staged = os.path.join(tmp, "_staged_binary")
    try:
        code, _, err = runner(["git", "clone", "--local", "--no-checkout",
                               str(module_dir), checkout], timeout=900)
        if code != 0:
            print(f"  [NG] clone失敗: {err.strip()[:300]}", flush=True)
            return False
        code, _, err = runner(["git", "-C", checkout, "checkout", "--detach", pin])
        if code != 0:
            print(f"  [NG] pin {pin[:7]} のcheckout失敗: {err.strip()[:300]}", flush=True)
            return False

        build_dir = os.path.join(checkout, module_rel) if module_rel else checkout
        print(f"  ビルド中 {target} @ {pin[:7]} ...", flush=True)
        code, _, err = runner(["go", "build", "-o", staged, target], cwd=build_dir)
        if code != 0:
            print(f"  [NG] ビルド失敗: {err.strip()[:400]}", flush=True)
            return False

        # A rebuild that does not actually clear the drift is worse than none,
        # so the new binary is verified before anything on the host is touched.
        fresh = build_info(staged)
        if not fresh or fresh["revision"] != pin or fresh["modified"]:
            got = (fresh or {}).get("revision", "?")[:7]
            print(f"  [NG] ビルド結果が pin と一致しない (built={got}, "
                  f"dirty={(fresh or {}).get('modified')})", flush=True)
            return False

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup = BACKUP_DIR / f"{row['name']}.replaced-{row['built'][:7] or 'unstamped'}"
        shutil.copy2(row["binary"], backup)
        print(f"  旧バイナリを退避: {backup}", flush=True)

        for unit in row["units"]:
            runner(["systemctl", "--user", "stop", unit])
        shutil.copy2(staged, row["binary"])
        os.chmod(row["binary"], 0o755)

        broken = start_and_settle(running, readiness, runner=runner)
        if broken:
            print(f"  [NG] {broken} が新バイナリで安定しません。ロールバックします",
                  flush=True)
            for unit in row["units"]:
                runner(["systemctl", "--user", "stop", unit])
            shutil.copy2(backup, row["binary"])
            os.chmod(row["binary"], 0o755)
            still_broken = start_and_settle(running, readiness, runner=runner)
            if still_broken:
                print(f"  [NG] ロールバック後も {still_broken} が復帰しません。"
                      f"退避先: {backup}", flush=True)
            else:
                print(f"  [OK] {row['built'][:7]} へ巻き戻し、稼働を確認しました",
                      flush=True)
            return False

        print(f"  [OK] {row['name']} を {pin[:7]} へ更新", flush=True)
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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
                        help="対象とする systemd unit の接頭辞")
    parser.add_argument("--json", action="store_true", help="JSONで出力する")
    parser.add_argument("--apply", action="store_true",
                        help="MISMATCH を pin の local clone から再ビルドして再配置する")
    parser.add_argument("--check-readiness", action="store_true",
                        help="配置済みunitを変更せずmanifest readinessを確認する")
    parser.add_argument("--dry-run", action="store_true",
                        help="--apply の実行計画だけを表示する")
    parser.add_argument("--only", default="",
                        help="対象componentをカンマ区切りで限定する")
    args = parser.parse_args()
    if args.apply and args.check_readiness:
        parser.error("--apply と --check-readiness は同時に指定できません")

    manifest = Path(args.manifest).resolve()
    if not manifest.exists():
        print(f"manifest not found: {manifest}", file=sys.stderr)
        return 2
    workspace = Path(args.workspace).resolve() if args.workspace else manifest.parent

    rows = collect(manifest, workspace, args.prefix)
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
            if not redeploy(row, components, workspace, args.dry_run):
                failed += 1
        if failed:
            return 1
        return 0

    if args.check_readiness:
        components = load_components(manifest)
        return 0 if check_declared_readiness(rows, components) else 1

    return report_exit_code(rows)


if __name__ == "__main__":
    sys.exit(main())

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
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

MATCH = "MATCH"
MISMATCH = "MISMATCH"
DIRTY = "DIRTY"
UNSTAMPED = "UNSTAMPED"
UNMAPPED = "UNMAPPED"

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


def unit_exec_path(unit: str) -> str | None:
    code, out, _ = run(["systemctl", "--user", "show", unit, "-p", "ExecStart", "--value"])
    if code != 0:
        return None
    # systemd renders ExecStart as "{ path=/usr/bin/foo ; argv[]=... ; ... }",
    # so the path token carries the leading brace.
    match = re.search(r"\bpath=([^\s;]+)", out)
    return match.group(1) if match else None


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


def start_and_settle(units: list[str], dwell: int = 8) -> str | None:
    """Start each unit and confirm it is still alive a moment later.

    Type=simple reports a successful start as soon as the process is forked, so
    a binary that rejects its config and exits immediately still looks started.
    That is exactly how rencrow-tts stayed "deployed" while failing. Waiting and
    re-reading the state is what turns that into a detectable failure. Oneshot
    units legitimately finish and go inactive, so only a failed result counts.

    This proves the process survived, not that it is serving. CORE needs about
    145 seconds to bind its port, so a dwell shorter than that says nothing
    about readiness; raise --dwell for services with a long startup.
    """
    for unit in units:
        run(["systemctl", "--user", "reset-failed", unit])
        code, _, err = run(["systemctl", "--user", "start", unit])
        if code != 0:
            print(f"  {unit} の起動コマンドが失敗: {err.strip()[:200]}", flush=True)
            return unit

    deadline = dwell
    while deadline > 0:
        run(["sleep", "2"])
        deadline -= 2
        for unit in units:
            _, state, _ = run(["systemctl", "--user", "show", unit,
                               "-p", "ActiveState", "--value"])
            _, sub, _ = run(["systemctl", "--user", "show", unit,
                             "-p", "SubState", "--value"])
            state, sub = state.strip(), sub.strip()
            if state == "failed" or sub == "auto-restart":
                print(f"  {unit} -> {state}/{sub}", flush=True)
                return unit

    for unit in units:
        _, state, _ = run(["systemctl", "--user", "show", unit,
                           "-p", "ActiveState", "--value"])
        _, restarts, _ = run(["systemctl", "--user", "show", unit,
                              "-p", "NRestarts", "--value"])
        print(f"  {unit} -> {state.strip()} (NRestarts={restarts.strip()})", flush=True)
    return None


def redeploy(row: dict[str, Any], components: dict[str, dict[str, Any]],
             workspace: Path, dry: bool, dwell: int) -> bool:
    """Rebuild one component at its pinned commit and reinstall it."""
    comp = components[row["component"]]
    module_dir = workspace / comp["workspace_path"]
    pin = row["pin"]
    repo_root = f"github.com/{comp['repository']}"
    module_rel = row["module"][len(repo_root):].lstrip("/")
    main_rel = row["main_package"][len(row["module"]):].lstrip("/")
    target = "./" + main_rel if main_rel else "."

    code, _, _ = run(["git", "-C", str(module_dir), "cat-file", "-e", f"{pin}^{{commit}}"])
    if code != 0:
        print(f"  [NG] pin {pin[:7]} がローカルに存在しない。fetchが必要", flush=True)
        return False

    if dry:
        print(f"  [DRY] {module_dir}@{pin[:7]} の local clone で {target} をビルドし "
              f"{row['binary']} へ設置、{', '.join(row['units'])} を再起動", flush=True)
        return True

    # A linked worktree keeps .git as a file, and Go silently omits the VCS
    # stamp when it sees that, which would make every rebuilt binary
    # unverifiable. A local clone has a real .git directory, so stamping works
    # and the checkout is guaranteed clean.
    tmp = tempfile.mkdtemp(prefix="rencrow-redeploy-")
    checkout = os.path.join(tmp, "src")
    staged = os.path.join(tmp, "_staged_binary")
    try:
        code, _, err = run(["git", "clone", "--local", "--no-checkout",
                            str(module_dir), checkout], timeout=900)
        if code != 0:
            print(f"  [NG] clone失敗: {err.strip()[:300]}", flush=True)
            return False
        code, _, err = run(["git", "-C", checkout, "checkout", "--detach", pin])
        if code != 0:
            print(f"  [NG] pin {pin[:7]} のcheckout失敗: {err.strip()[:300]}", flush=True)
            return False

        build_dir = os.path.join(checkout, module_rel) if module_rel else checkout
        print(f"  ビルド中 {target} @ {pin[:7]} ...", flush=True)
        code, _, err = run(["go", "build", "-o", staged, target], cwd=build_dir)
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

        # Only units that were running get started again. Several binaries also
        # back a manually invoked Type=oneshot unit (rencrow-trade-learning runs
        # an offline learning job), and starting those would execute work nobody
        # asked for.
        running = []
        for unit in row["units"]:
            _, state, _ = run(["systemctl", "--user", "show", unit,
                               "-p", "ActiveState", "--value"])
            if state.strip() in ("active", "activating", "reloading"):
                running.append(unit)
            else:
                print(f"  {unit} は停止中のまま据え置きます", flush=True)

        for unit in row["units"]:
            run(["systemctl", "--user", "stop", unit])
        shutil.copy2(staged, row["binary"])
        os.chmod(row["binary"], 0o755)

        broken = start_and_settle(running, dwell)
        if broken:
            print(f"  [NG] {broken} が新バイナリで安定しません。ロールバックします",
                  flush=True)
            for unit in row["units"]:
                run(["systemctl", "--user", "stop", unit])
            shutil.copy2(backup, row["binary"])
            os.chmod(row["binary"], 0o755)
            still_broken = start_and_settle(running, dwell)
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
    parser.add_argument("--dry-run", action="store_true",
                        help="--apply の実行計画だけを表示する")
    parser.add_argument("--dwell", type=int, default=8,
                        help="再起動後に生存を確認する秒数。COREのように listen まで "
                             "2分以上かかるserviceは長めにする (既定: 8)")
    parser.add_argument("--only", default="",
                        help="対象componentをカンマ区切りで限定する")
    args = parser.parse_args()

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
            if not redeploy(row, components, workspace, args.dry_run, args.dwell):
                failed += 1
        if failed:
            return 1
        return 0

    return report_exit_code(rows)


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPOSITORY_ROOT / "scripts" / "check_deployed_binaries.py"
SPEC = importlib.util.spec_from_file_location("check_deployed_binaries", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class ReportExitCodeTest(unittest.TestCase):
    def test_match_and_unmapped_are_success(self) -> None:
        rows = [{"status": CHECKER.MATCH}, {"status": CHECKER.UNMAPPED}]
        self.assertEqual(CHECKER.report_exit_code(rows), 0)

    def test_mismatch_is_failure(self) -> None:
        self.assertEqual(
            CHECKER.report_exit_code([{"status": CHECKER.MISMATCH}]), 1
        )

    def test_dirty_is_failure(self) -> None:
        self.assertEqual(CHECKER.report_exit_code([{"status": CHECKER.DIRTY}]), 1)

    def test_unstamped_is_failure(self) -> None:
        self.assertEqual(
            CHECKER.report_exit_code([{"status": CHECKER.UNSTAMPED}]), 1
        )


class GoBinaryDeploymentPinTest(unittest.TestCase):
    def test_declared_binary_pin_overrides_component_source_pin(self) -> None:
        component = {
            "version": "a" * 40,
            "deployment": {
                "go_binaries": [
                    {
                        "module": "github.com/Nyukimin/RenCrow_Tools/tools/example",
                        "main_package": "github.com/Nyukimin/RenCrow_Tools/tools/example/cmd/example",
                        "installed_path": "%h/.local/bin/example",
                        "version": "b" * 40,
                    }
                ]
            },
        }
        self.assertEqual(
            CHECKER.go_binary_pin(
                component,
                "github.com/Nyukimin/RenCrow_Tools/tools/example",
                "github.com/Nyukimin/RenCrow_Tools/tools/example/cmd/example",
            ),
            "b" * 40,
        )

    def test_declared_non_service_binary_is_included_in_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed = root / "rencrow-tools-verify"
            installed.write_bytes(b"binary")
            revision = "b" * 40
            manifest = root / "ecosystem.yaml"
            manifest.write_text(json.dumps({
                "components": {
                    "tools": {
                        "repository": "Nyukimin/RenCrow_Tools",
                        "workspace_path": "./RenCrow_Tools",
                        "version": "a" * 40,
                        "deployment": {"go_binaries": [{
                            "module": "github.com/Nyukimin/RenCrow_Tools/tools/quality/full_system_verification",
                            "main_package": "github.com/Nyukimin/RenCrow_Tools/tools/quality/full_system_verification/cmd/rencrow-tools-verify",
                            "installed_path": "%workspace%/rencrow-tools-verify",
                            "version": revision,
                        }]},
                    }
                }
            }), encoding="utf-8")
            adapter = mock.Mock()
            adapter.services.return_value = []
            info = {
                "module": "github.com/Nyukimin/RenCrow_Tools/tools/quality/full_system_verification",
                "main_package": "github.com/Nyukimin/RenCrow_Tools/tools/quality/full_system_verification/cmd/rencrow-tools-verify",
                "revision": revision,
                "modified": False,
            }
            with mock.patch.object(CHECKER, "build_info", return_value=info):
                rows = CHECKER.collect(manifest, root, "rencrow", adapter)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["name"], "rencrow-tools-verify")
            self.assertEqual(rows[0]["status"], CHECKER.MATCH)
            self.assertEqual(rows[0]["units"], [])


class ExecStartPathTest(unittest.TestCase):
    def test_direct_exec_start_returns_path(self) -> None:
        rendered = (
            "{ path=/home/user/.local/bin/rencrow-tts ; "
            "argv[]=/home/user/.local/bin/rencrow-tts --config /etc/rencrow ; ... }"
        )
        self.assertEqual(
            CHECKER.parse_exec_start_path(rendered),
            "/home/user/.local/bin/rencrow-tts",
        )

    def test_bounded_flock_exec_start_returns_locked_command(self) -> None:
        rendered = (
            "{ path=/usr/bin/flock ; "
            "argv[]=/usr/bin/flock -n /home/user/.rencrow/config/lyrics-collector.lock "
            "/home/user/.local/bin/rencrow-lyrics-catalog collect --limit 10 ; ... }"
        )
        self.assertEqual(
            CHECKER.parse_exec_start_path(rendered),
            "/home/user/.local/bin/rencrow-lyrics-catalog",
        )

    def test_malformed_flock_exec_start_stays_visible_as_wrapper(self) -> None:
        rendered = (
            "{ path=/usr/bin/flock ; "
            "argv[]=/usr/bin/flock --exclusive /home/user/.rencrow/config/lock "
            "/home/user/.local/bin/rencrow-lyrics-catalog collect ; ... }"
        )
        self.assertEqual(
            CHECKER.parse_exec_start_path(rendered),
            "/usr/bin/flock",
        )


class ReadinessContractTest(unittest.TestCase):
    class Clock:
        def __init__(self) -> None:
            self.now = 0.0
            self.sleeps: list[float] = []

        def monotonic(self) -> float:
            return self.now

        def sleep(self, seconds: float) -> None:
            self.sleeps.append(seconds)
            self.now += seconds

    @staticmethod
    def http_response(status: int, body: object) -> object:
        class Response:
            def __init__(self) -> None:
                self.status = status

            def read(self) -> bytes:
                return json.dumps(body).encode("utf-8")

            def close(self) -> None:
                return None

        return Response()

    @staticmethod
    def http_contract(timeout: int = 3) -> dict[str, object]:
        return {
            "unit": "rencrow-test.service",
            "kind": "http_json",
            "url": "http://127.0.0.1:9999/ready",
            "timeout_seconds": timeout,
            "expect": {"path": "ready", "equals": True},
        }

    @staticmethod
    def oneshot_contract() -> dict[str, object]:
        return {"unit": "rencrow-test.service", "kind": "oneshot"}

    def runner(self, state: dict[str, str], calls: list[list[str]]):
        def run(command: list[str], **_: object) -> tuple[int, str, str]:
            calls.append(command)
            if command[2:3] == ["show"]:
                unit = command[3]
                requested = [
                    command[index + 1]
                    for index, value in enumerate(command)
                    if value == "-p" and index + 1 < len(command)
                ]
                if "--value" in command:
                    return 0, state.get(requested[0], ""), ""
                output = "".join(
                    f"{key}={state.get(key, '')}\n" for key in requested
                )
                return 0, output, ""
            return 0, "", ""

        return run

    def test_http_readiness_retries_until_delayed_ready(self) -> None:
        clock = self.Clock()
        state = {
            "ActiveState": "active",
            "SubState": "running",
            "Result": "success",
            "ExecMainStatus": "0",
        }
        calls: list[list[str]] = []
        responses = iter(
            [
                self.http_response(200, {"ready": False}),
                self.http_response(200, {"ready": True}),
            ]
        )

        broken = CHECKER.start_and_settle(
            ["rencrow-test.service"],
            {"rencrow-test.service": self.http_contract()},
            runner=self.runner(state, calls),
            http_opener=lambda *_args, **_kwargs: next(responses),
            sleep_fn=clock.sleep,
            clock=clock.monotonic,
        )

        self.assertIsNone(broken)
        self.assertGreaterEqual(len(clock.sleeps), 1)

    def test_http_wrong_body_times_out(self) -> None:
        clock = self.Clock()
        state = {"ActiveState": "active", "SubState": "running"}
        calls: list[list[str]] = []

        broken = CHECKER.start_and_settle(
            ["rencrow-test.service"],
            {"rencrow-test.service": self.http_contract(timeout=2)},
            runner=self.runner(state, calls),
            http_opener=lambda *_args, **_kwargs: self.http_response(200, {"ready": False}),
            sleep_fn=clock.sleep,
            clock=clock.monotonic,
        )

        self.assertEqual(broken, "rencrow-test.service")

    def test_http_ready_response_at_deadline_is_success(self) -> None:
        clock = self.Clock()
        state = {"ActiveState": "active", "SubState": "running"}
        calls: list[list[str]] = []

        def opener(*_args: object, **_kwargs: object) -> object:
            clock.now = 2.0
            return self.http_response(200, {"ready": True})

        broken = CHECKER.start_and_settle(
            ["rencrow-test.service"],
            {"rencrow-test.service": self.http_contract(timeout=2)},
            runner=self.runner(state, calls),
            http_opener=opener,
            sleep_fn=clock.sleep,
            clock=clock.monotonic,
        )

        self.assertIsNone(broken)

    def test_check_readiness_does_not_start_or_reset_unit(self) -> None:
        clock = self.Clock()
        state = {"ActiveState": "active", "SubState": "running"}
        calls: list[list[str]] = []

        broken = CHECKER.wait_for_readiness(
            ["rencrow-test.service"],
            {"rencrow-test.service": self.http_contract()},
            runner=self.runner(state, calls),
            http_opener=lambda *_args, **_kwargs: self.http_response(
                200, {"ready": True}
            ),
            sleep_fn=clock.sleep,
            clock=clock.monotonic,
        )

        self.assertIsNone(broken)
        self.assertFalse(any(command[2:3] == ["start"] for command in calls))
        self.assertFalse(any(command[2:3] == ["reset-failed"] for command in calls))

    def test_http_and_json_failures_are_not_success(self) -> None:
        clock = self.Clock()
        state = {"ActiveState": "active", "SubState": "running"}
        calls: list[list[str]] = []
        failures = iter([self.http_response(503, {}), ValueError("invalid json")])

        def opener(*_args: object, **_kwargs: object) -> object:
            try:
                failure = next(failures)
            except StopIteration:
                return self.http_response(503, {})
            if isinstance(failure, Exception):
                raise failure
            return failure

        broken = CHECKER.start_and_settle(
            ["rencrow-test.service"],
            {"rencrow-test.service": self.http_contract(timeout=2)},
            runner=self.runner(state, calls),
            http_opener=opener,
            sleep_fn=clock.sleep,
            clock=clock.monotonic,
        )

        self.assertEqual(broken, "rencrow-test.service")

    def test_systemd_failure_is_immediate(self) -> None:
        clock = self.Clock()
        state = {"ActiveState": "failed", "SubState": "failed"}
        calls: list[list[str]] = []
        opener = mock.Mock()

        broken = CHECKER.start_and_settle(
            ["rencrow-test.service"],
            {"rencrow-test.service": self.http_contract(timeout=60)},
            runner=self.runner(state, calls),
            http_opener=opener,
            sleep_fn=clock.sleep,
            clock=clock.monotonic,
        )

        self.assertEqual(broken, "rencrow-test.service")
        opener.assert_not_called()
        self.assertEqual(clock.sleeps, [])

    def test_inactive_http_service_is_immediate_failure(self) -> None:
        clock = self.Clock()
        state = {"ActiveState": "inactive", "SubState": "dead"}
        calls: list[list[str]] = []
        opener = mock.Mock()

        broken = CHECKER.wait_for_readiness(
            ["rencrow-test.service"],
            {"rencrow-test.service": self.http_contract(timeout=60)},
            runner=self.runner(state, calls),
            http_opener=opener,
            sleep_fn=clock.sleep,
            clock=clock.monotonic,
        )

        self.assertEqual(broken, "rencrow-test.service")
        opener.assert_not_called()
        self.assertEqual(clock.sleeps, [])

    def test_oneshot_success_requires_success_result_and_zero_status(self) -> None:
        clock = self.Clock()
        state = {
            "ActiveState": "inactive",
            "SubState": "dead",
            "Result": "success",
            "ExecMainStatus": "0",
        }
        calls: list[list[str]] = []

        broken = CHECKER.start_and_settle(
            ["rencrow-test.service"],
            {"rencrow-test.service": self.oneshot_contract()},
            runner=self.runner(state, calls),
            sleep_fn=clock.sleep,
            clock=clock.monotonic,
        )

        self.assertIsNone(broken)

    def test_oneshot_failure_is_reported(self) -> None:
        clock = self.Clock()
        state = {
            "ActiveState": "inactive",
            "SubState": "dead",
            "Result": "exit-code",
            "ExecMainStatus": "1",
        }
        calls: list[list[str]] = []

        broken = CHECKER.start_and_settle(
            ["rencrow-test.service"],
            {"rencrow-test.service": self.oneshot_contract()},
            runner=self.runner(state, calls),
            sleep_fn=clock.sleep,
            clock=clock.monotonic,
        )

        self.assertEqual(broken, "rencrow-test.service")

    def test_missing_running_contract_fails_before_redeploy_mutation(self) -> None:
        calls: list[list[str]] = []
        state = {"ActiveState": "active"}
        row = {
            "component": "core",
            "units": ["rencrow-test.service"],
            "binary": "/tmp/rencrow-test",
            "name": "rencrow-test",
            "module": "github.com/Nyukimin/RenCrow_CORE",
            "main_package": "github.com/Nyukimin/RenCrow_CORE/cmd/rencrow",
            "pin": "a" * 40,
            "built": "b" * 40,
        }
        components = {
            "core": {
                "repository": "Nyukimin/RenCrow_CORE",
                "workspace_path": "./RenCrow_CORE",
                "deployment": {"user_systemd": []},
            }
        }

        with tempfile.TemporaryDirectory() as directory:
            result = CHECKER.redeploy(
                row,
                components,
                REPOSITORY_ROOT,
                dry=False,
                runner=self.runner(state, calls),
                receipt_log=Path(directory) / "receipts.jsonl",
            )

        self.assertFalse(result)
        self.assertFalse(any(command[2:3] == ["stop"] for command in calls))


class RemoteGatewayReadinessTest(unittest.TestCase):
    """The gateway runs on a remote host; a local unit forwards its loopback port."""

    TUNNEL = "rencrow-example-tunnel.service"
    RETIRED = "rencrow-example.service"
    OTHER_TUNNEL = "rencrow-other-tunnel.service"
    GATEWAY_MODULE = "github.com/Nyukimin/RenCrow_Example/gateway"

    class Adapter(CHECKER.HostAdapter):
        name = "fake"

        def __init__(self, services, exec_paths, states) -> None:
            self._services = services
            self._exec_paths = exec_paths
            self.states = states
            self.property_reads: list[str] = []

        def services(self, prefix: str) -> list[str]:
            return list(self._services)

        def exec_path(self, service: str) -> str | None:
            return self._exec_paths.get(service)

        def properties(self, service: str) -> dict[str, str] | None:
            self.property_reads.append(service)
            state = self.states.get(service)
            if state is None:
                return None
            active = state in {"active", "activating", "reloading"}
            return {
                "ActiveState": state,
                "SubState": "running" if active else "dead",
                "Result": "success",
                "ExecMainStatus": "0",
                "NRestarts": "0",
            }

        def contract_unit(self, service: str) -> str:
            return service

    @classmethod
    def components(cls, replaces: str | None = None) -> dict[str, dict[str, object]]:
        contract: dict[str, object] = {
            "unit": cls.TUNNEL,
            "kind": "http_json",
            "url": "http://127.0.0.1:9999/health/ready",
            "timeout_seconds": 3,
            "expect": {"path": "ready", "equals": True},
            "remote_gateway": {"replaces": replaces or cls.RETIRED},
        }
        return {
            "example": {
                "repository": "Nyukimin/RenCrow_Example",
                "workspace_path": "./RenCrow_Example",
                # Differs from the retired binary revision on purpose: a
                # retired binary must never be compared with any pin.
                "version": "c" * 40,
                "deployment": {"user_systemd": [contract]},
            }
        }

    def host(self, services, states, root: Path):
        ssh = root / "ssh"
        retired_binary = root / "rencrow-example"
        ssh.write_bytes(b"ssh")
        retired_binary.write_bytes(b"gateway")
        manifest = root / "ecosystem.yaml"
        manifest.write_text(
            json.dumps({"components": self.components()}), encoding="utf-8"
        )
        adapter = self.Adapter(
            services,
            {
                self.TUNNEL: str(ssh),
                self.OTHER_TUNNEL: str(ssh),
                self.RETIRED: str(retired_binary),
            },
            states,
        )

        def build_info(binary: str) -> dict[str, object] | None:
            if binary == str(retired_binary):
                return {
                    "module": self.GATEWAY_MODULE,
                    "main_package": self.GATEWAY_MODULE + "/cmd/rencrow-example",
                    "revision": "a" * 40,
                    "modified": False,
                }
            return None

        return manifest, adapter, build_info

    def test_collect_maps_forwarder_and_skips_retired_unit(self) -> None:
        orders = (
            [self.TUNNEL, self.OTHER_TUNNEL, self.RETIRED],
            [self.OTHER_TUNNEL, self.RETIRED, self.TUNNEL],
        )
        for services in orders:
            with self.subTest(services=services), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest, adapter, build_info = self.host(
                    services,
                    {self.TUNNEL: "active", self.RETIRED: "inactive"},
                    root,
                )
                with mock.patch.object(CHECKER, "build_info", side_effect=build_info):
                    rows = CHECKER.collect(manifest, root, "rencrow", adapter)

                forwarders = [r for r in rows if r.get("artifact_kind") == "remote_gateway"]
                self.assertEqual(len(forwarders), 1)
                self.assertEqual(forwarders[0]["component"], "example")
                self.assertEqual(forwarders[0]["units"], [self.TUNNEL])
                self.assertEqual(forwarders[0]["status"], CHECKER.UNMAPPED)
                self.assertEqual(forwarders[0]["retired_units"], [self.RETIRED])
                # The retired binary is not a tracked deployment: no row at all,
                # so there is nothing to drift against any pin.
                self.assertFalse(any(r["name"] == "rencrow-example" for r in rows))
                self.assertFalse(any(r["status"] == CHECKER.MISMATCH for r in rows))
                self.assertEqual(CHECKER.report_exit_code(rows), 0)
                # An undeclared forwarder sharing the same ssh binary stays its
                # own unmapped row and is not folded into the declared one.
                others = [r for r in rows if r is not forwarders[0]]
                self.assertEqual(len(others), 1)
                self.assertIsNone(others[0]["component"])
                self.assertEqual(others[0]["units"], [self.OTHER_TUNNEL])

    def test_undeclared_non_go_unit_stays_unmapped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, adapter, build_info = self.host(
                [self.OTHER_TUNNEL], {}, root
            )
            with mock.patch.object(CHECKER, "build_info", side_effect=build_info):
                rows = CHECKER.collect(manifest, root, "rencrow", adapter)

        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["component"])
        self.assertEqual(rows[0]["status"], CHECKER.UNMAPPED)
        self.assertNotEqual(rows[0].get("artifact_kind"), "remote_gateway")

    def check(self, states, opener, *, services=None):
        clock = ReadinessContractTest.Clock()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, adapter, build_info = self.host(
                services or [self.TUNNEL, self.RETIRED], states, root
            )
            with mock.patch.object(CHECKER, "build_info", side_effect=build_info):
                rows = CHECKER.collect(manifest, root, "rencrow", adapter)
        result = CHECKER.check_declared_readiness(
            rows,
            self.components(),
            adapter=adapter,
            http_opener=opener,
            sleep_fn=clock.sleep,
            clock=clock.monotonic,
        )
        return result, adapter

    def test_stopped_retired_unit_is_not_required(self) -> None:
        opener = mock.Mock(
            return_value=ReadinessContractTest.http_response(200, {"ready": True})
        )
        result, adapter = self.check(
            {self.TUNNEL: "active", self.RETIRED: "inactive"}, opener
        )
        self.assertTrue(result)
        opener.assert_called_once()
        self.assertEqual(opener.call_args.args[0], "http://127.0.0.1:9999/health/ready")
        self.assertIn(self.TUNNEL, adapter.property_reads)

    def test_inactive_forwarder_fails_without_calling_url(self) -> None:
        opener = mock.Mock()
        result, _ = self.check(
            {self.TUNNEL: "inactive", self.RETIRED: "inactive"}, opener
        )
        self.assertFalse(result)
        opener.assert_not_called()

    def test_remote_gateway_not_ready_fails(self) -> None:
        opener = mock.Mock(
            return_value=ReadinessContractTest.http_response(200, {"ready": False})
        )
        result, _ = self.check(
            {self.TUNNEL: "active", self.RETIRED: "inactive"}, opener
        )
        self.assertFalse(result)

    def test_active_retired_unit_fails_even_when_url_is_ready(self) -> None:
        # A local gateway holding the port makes the URL look ready without
        # proving the remote gateway is reachable.
        for state in ("active", "activating", "reloading"):
            with self.subTest(state=state):
                opener = mock.Mock(
                    return_value=ReadinessContractTest.http_response(200, {"ready": True})
                )
                result, _ = self.check(
                    {self.TUNNEL: "active", self.RETIRED: state}, opener
                )
                self.assertFalse(result)
                opener.assert_not_called()

    def test_unreadable_retired_unit_state_fails_closed(self) -> None:
        opener = mock.Mock()
        result, _ = self.check({self.TUNNEL: "active"}, opener)
        self.assertFalse(result)
        opener.assert_not_called()

    def test_absent_retired_unit_is_fine(self) -> None:
        opener = mock.Mock(
            return_value=ReadinessContractTest.http_response(200, {"ready": True})
        )
        result, _ = self.check(
            {self.TUNNEL: "active"}, opener, services=[self.TUNNEL]
        )
        self.assertTrue(result)

    def test_checked_in_manifest_checks_forwarder_not_stopped_gateway(self) -> None:
        """Reproduces the original failure on the checked-in manifest.

        The stopped local gateway unit used to fail the whole readiness run with
        inactive/dead before any later component was reached.
        """
        components = CHECKER.load_components(REPOSITORY_ROOT / "ecosystem.yaml")
        contracts = components["stt"]["deployment"]["user_systemd"]
        self.assertEqual(len(contracts), 1)
        tunnel = contracts[0]["unit"]
        retired = contracts[0]["remote_gateway"]["replaces"]
        clock = ReadinessContractTest.Clock()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ssh = root / "ssh"
            ssh.write_bytes(b"ssh")
            adapter = self.Adapter(
                [retired, tunnel],
                {tunnel: str(ssh), retired: str(root / "absent")},
                {tunnel: "active", retired: "inactive"},
            )
            # collect() also inventories files under the home directory; keep
            # the test independent of whatever the tester has installed there.
            with mock.patch.object(CHECKER, "build_info", return_value=None), \
                    mock.patch.object(Path, "home", return_value=root):
                rows = CHECKER.collect(
                    REPOSITORY_ROOT / "ecosystem.yaml", REPOSITORY_ROOT, "rencrow", adapter
                )
            opener = mock.Mock(
                return_value=ReadinessContractTest.http_response(200, {"ready": True})
            )
            result = CHECKER.check_declared_readiness(
                [r for r in rows if r.get("artifact_kind") != "managed_file"],
                components,
                adapter=adapter,
                http_opener=opener,
                sleep_fn=clock.sleep,
                clock=clock.monotonic,
            )
        self.assertTrue(result)
        self.assertEqual(opener.call_args.args[0], contracts[0]["url"])


class AtomicCopyTest(unittest.TestCase):
    def test_copy_uses_sibling_temp_then_replaces_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "staged"
            destination = root / "installed"
            source.write_bytes(b"new")
            destination.write_bytes(b"old")
            copied = mock.Mock(wraps=CHECKER.shutil.copy2)
            replaced = mock.Mock(wraps=CHECKER.os.replace)

            with mock.patch.object(CHECKER.shutil, "copy2", copied), mock.patch.object(
                CHECKER.os, "replace", replaced
            ):
                CHECKER._atomic_copy(source, destination, mode=0o755)

            copied_source, copied_destination = copied.call_args.args[:2]
            self.assertEqual(Path(copied_source), source)
            temporary = Path(copied_destination)
            self.assertNotEqual(temporary, destination)
            self.assertEqual(temporary.parent, destination.parent)
            replaced.assert_called_once_with(temporary, destination)
            self.assertEqual(destination.read_bytes(), b"new")
            if CHECKER.os.name == "posix":
                self.assertEqual(destination.stat().st_mode & 0o777, 0o755)
            self.assertFalse(temporary.exists())

    def test_copy_cleans_sibling_temp_when_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "staged"
            destination = root / "installed"
            source.write_bytes(b"new")
            destination.write_bytes(b"old")

            with mock.patch.object(
                CHECKER.os, "replace", side_effect=OSError("replace failed")
            ):
                with self.assertRaises(OSError):
                    CHECKER._atomic_copy(source, destination, mode=0o755)

            self.assertEqual(destination.read_bytes(), b"old")
            self.assertEqual(sorted(path.name for path in root.iterdir()), ["installed", "staged"])


class RedeployReceiptTest(unittest.TestCase):
    ROW = {
        "component": "tts",
        "units": ["rencrow-test.service", "rencrow-test-learning.service"],
        "binary": "/tmp/rencrow-test",
        "name": "rencrow-test",
        "module": "github.com/Nyukimin/RenCrow_TTS",
        "main_package": "github.com/Nyukimin/RenCrow_TTS/cmd/rencrow-tts",
        "pin": "a" * 40,
        "built": "b" * 40,
    }
    COMPONENTS = {
        "tts": {
            "repository": "Nyukimin/RenCrow_TTS",
            "workspace_path": "./RenCrow_TTS",
            "deployment": {
                "user_systemd": [
                    {
                        "unit": "rencrow-test.service",
                        "kind": "http_json",
                        "url": "http://127.0.0.1:9999/ready",
                        "timeout_seconds": 1,
                        "expect": {"path": "ready", "equals": True},
                    },
                    {
                        "unit": "rencrow-test-learning.service",
                        "kind": "oneshot",
                    },
                ]
            },
        }
    }

    @staticmethod
    def runner(calls: list[list[str]]) -> object:
        def run(command: list[str], **_: object) -> tuple[int, str, str]:
            calls.append(command)
            if command[2:3] == ["show"]:
                if "--value" in command:
                    if command[3] == "rencrow-test-learning.service":
                        return 0, "inactive\n", ""
                    return 0, "active\n", ""
                if command[3] == "rencrow-test-learning.service":
                    return 0, "ActiveState=inactive\nSubState=dead\nResult=success\nExecMainStatus=0\n", ""
                return 0, "ActiveState=active\nSubState=running\n", ""
            return 0, "", ""

        return run

    @staticmethod
    def fresh_build_info() -> dict[str, object]:
        return {
            "main_package": "github.com/Nyukimin/RenCrow_TTS/cmd/rencrow-tts",
            "module": "github.com/Nyukimin/RenCrow_TTS",
            "revision": "a" * 40,
            "modified": False,
        }

    def invoke(
        self,
        root: Path,
        calls: list[list[str]],
        *,
        start_results: list[str | None] | None = None,
        prepare_receipt: object | None = None,
    ) -> tuple[bool, Path]:
        receipt_log = root / "receipts" / "binary-redeployment.jsonl"
        row = {**self.ROW, "binary": str(root / self.ROW["name"])}
        with mock.patch.object(
            CHECKER, "build_info", return_value=self.fresh_build_info()
        ), mock.patch.object(CHECKER.shutil, "copy2"), mock.patch.object(
            CHECKER.os, "chmod"
        ), mock.patch.object(
            CHECKER, "BACKUP_DIR", root / "backups"
        ), mock.patch.object(
            CHECKER, "start_and_settle",
            side_effect=start_results or [None],
        ):
            if prepare_receipt is None:
                result = CHECKER.redeploy(
                    row,
                    self.COMPONENTS,
                    root,
                    dry=False,
                    runner=self.runner(calls),
                    receipt_log=receipt_log,
                )
            else:
                with mock.patch.object(CHECKER, "prepare_receipt_log", prepare_receipt):
                    result = CHECKER.redeploy(
                        row,
                        self.COMPONENTS,
                        root,
                        dry=False,
                        runner=self.runner(calls),
                        receipt_log=receipt_log,
                    )
        return result, receipt_log

    def test_success_writes_one_durable_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result, receipt_log = self.invoke(Path(directory), [])

            self.assertTrue(result)
            lines = receipt_log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            receipt = json.loads(lines[0])
            self.assertEqual(receipt["schema_version"], 1)
            self.assertTrue(receipt["receipt_id"])
            self.assertEqual(receipt["component"], "tts")
            self.assertEqual(receipt["binary_path"], str(Path(directory) / self.ROW["name"]))
            self.assertEqual(receipt["from_revision"], "b" * 40)
            self.assertEqual(receipt["target_revision"], "a" * 40)
            self.assertEqual(receipt["running_units"], ["rencrow-test.service"])
            self.assertEqual(receipt["outcome"], "success")
            self.assertEqual(receipt["rollback_outcome"], "not_attempted")
            self.assertIn("backup_path", receipt)
            self.assertTrue(receipt["started_at"].endswith("Z"))
            self.assertTrue(receipt["finished_at"].endswith("Z"))

    def test_preflight_failure_writes_receipt_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            calls: list[list[str]] = []
            receipt_log = Path(directory) / "receipts" / "binary-redeployment.jsonl"
            bad_components = {
                "tts": {
                    **self.COMPONENTS["tts"],
                    "deployment": {"user_systemd": []},
                }
            }
            result = CHECKER.redeploy(
                self.ROW,
                bad_components,
                Path(directory),
                dry=False,
                runner=self.runner(calls),
                receipt_log=receipt_log,
            )

            self.assertFalse(result)
            self.assertEqual(len(receipt_log.read_text(encoding="utf-8").splitlines()), 1)

    def test_active_oneshot_is_deferred_before_build_or_stop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            calls: list[list[str]] = []
            with mock.patch.object(
                CHECKER,
                "_running_units",
                return_value=["rencrow-test-learning.service"],
            ):
                result, receipt_log = self.invoke(root, calls)

            self.assertFalse(result)
            receipt = json.loads(receipt_log.read_text(encoding="utf-8"))
            self.assertEqual(receipt["outcome"], "deferred")
            self.assertEqual(receipt["phase"], "preflight")
            self.assertEqual(
                receipt["deferred_units"], ["rencrow-test-learning.service"]
            )
            self.assertFalse(any(command[0] in {"git", "go"} for command in calls))
            self.assertFalse(any("stop" in command for command in calls))

    def test_readiness_failure_records_successful_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result, receipt_log = self.invoke(
                Path(directory), [], start_results=["rencrow-test.service", None]
            )

            self.assertFalse(result)
            receipt = json.loads(receipt_log.read_text(encoding="utf-8"))
            self.assertEqual(receipt["outcome"], "failure")
            self.assertEqual(receipt["failed_unit"], "rencrow-test.service")
            self.assertEqual(receipt["rollback_outcome"], "success")

    def test_rollback_failure_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result, receipt_log = self.invoke(
                Path(directory), [],
                start_results=["rencrow-test.service", "rencrow-test.service"],
            )

            self.assertFalse(result)
            receipt = json.loads(receipt_log.read_text(encoding="utf-8"))
            self.assertEqual(receipt["outcome"], "failure")
            self.assertEqual(receipt["rollback_outcome"], "failed")

    def test_receipt_open_failure_happens_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            calls: list[list[str]] = []

            def fail_open(_path: Path) -> None:
                raise OSError("receipt unavailable")

            result, receipt_log = self.invoke(
                Path(directory), calls, prepare_receipt=fail_open
            )

            self.assertFalse(result)
            self.assertFalse(receipt_log.exists())
            self.assertFalse(any(command[2:3] in (["stop"], ["copy"]) for command in calls))
            self.assertFalse(any(command[0] == "go" for command in calls))

    def test_dry_run_does_not_write_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt_log = Path(directory) / "receipts" / "binary-redeployment.jsonl"
            with mock.patch.object(CHECKER, "prepare_receipt_log") as prepare:
                result = CHECKER.redeploy(
                    self.ROW,
                    self.COMPONENTS,
                    Path(directory),
                    dry=True,
                    runner=self.runner([]),
                    receipt_log=receipt_log,
                )

            self.assertTrue(result)
            self.assertFalse(receipt_log.exists())
            prepare.assert_not_called()


class ManagedFileTest(unittest.TestCase):
    def test_collect_reports_match_mismatch_and_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            matching = root / "matching.sh"
            changed = root / "changed.sh"
            matching.write_bytes(b"same\n")
            changed.write_bytes(b"changed\n")
            expected = CHECKER.hashlib.sha256(b"same\n").hexdigest()
            components = {
                "core": {
                    "deployment": {"files": [
                        {"source_path": "scripts/a.sh", "installed_path": "%workspace%/matching.sh", "sha256": expected, "mode": "0755"},
                        {"source_path": "scripts/b.sh", "installed_path": "%workspace%/changed.sh", "sha256": expected, "mode": "0755"},
                        {"source_path": "scripts/c.sh", "installed_path": "%workspace%/missing.sh", "sha256": expected, "mode": "0755"},
                    ]}
                }
            }
            rows = CHECKER.collect_managed_files(components, root)
            self.assertEqual([row["status"] for row in rows], [CHECKER.MATCH, CHECKER.MISMATCH, CHECKER.MISMATCH])
            self.assertEqual(rows[-1]["note"], "配置fileが存在しない")

    def test_redeploy_installs_pinned_blob_and_writes_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "installed" / "tool.sh"
            target.parent.mkdir()
            target.write_text("old\n", encoding="utf-8")
            content = b"new\n"
            expected = CHECKER.hashlib.sha256(content).hexdigest()
            row = {
                "artifact_kind": "managed_file", "component": "core", "units": [],
                "binary": str(target), "name": "tool.sh", "built": "b" * 64,
                "pin": expected, "source_path": "scripts/tool.sh", "mode": "0755",
            }
            components = {"core": {"workspace_path": "./RenCrow_CORE", "version": "a" * 40}}
            receipt = root / "receipt.jsonl"
            def runner(_command: list[str], **_kwargs: object):
                return 0, "", ""
            with mock.patch.object(CHECKER, "BACKUP_DIR", root / "backups"):
                ok = CHECKER.redeploy_managed_file(
                    row, components, root, False, runner=runner,
                    blob_loader=lambda *_args: content, receipt_log=receipt
                )
            self.assertTrue(ok)
            self.assertEqual(target.read_bytes(), content)
            self.assertEqual(json.loads(receipt.read_text())["outcome"], "success")

    def test_redeploy_rejects_manifest_hash_mismatch_before_install(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "tool.sh"
            target.write_text("old\n", encoding="utf-8")
            row = {
                "artifact_kind": "managed_file", "component": "core", "units": [],
                "binary": str(target), "name": "tool.sh", "built": "b" * 64,
                "pin": "a" * 64, "source_path": "scripts/tool.sh", "mode": "0755",
            }
            components = {"core": {"workspace_path": "./RenCrow_CORE", "version": "c" * 40}}
            ok = CHECKER.redeploy_managed_file(
                row, components, root, False,
                runner=lambda *_args, **_kwargs: (0, "", ""),
                blob_loader=lambda *_args: b"unexpected\n",
                receipt_log=root / "receipt.jsonl",
            )
            self.assertFalse(ok)
            self.assertEqual(target.read_text(encoding="utf-8"), "old\n")


if __name__ == "__main__":
    unittest.main()

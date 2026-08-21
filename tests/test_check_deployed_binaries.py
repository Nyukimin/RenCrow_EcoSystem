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


class ExecStartPathTest(unittest.TestCase):
    def test_direct_exec_start_returns_path(self) -> None:
        rendered = (
            "{ path=/home/ren/.local/bin/rencrow-tts ; "
            "argv[]=/home/ren/.local/bin/rencrow-tts --config /etc/rencrow ; ... }"
        )
        self.assertEqual(
            CHECKER.parse_exec_start_path(rendered),
            "/home/ren/.local/bin/rencrow-tts",
        )

    def test_bounded_flock_exec_start_returns_locked_command(self) -> None:
        rendered = (
            "{ path=/usr/bin/flock ; "
            "argv[]=/usr/bin/flock -n /home/ren/.rencrow/config/lyrics-collector.lock "
            "/home/ren/.local/bin/rencrow-lyrics-catalog collect --limit 10 ; ... }"
        )
        self.assertEqual(
            CHECKER.parse_exec_start_path(rendered),
            "/home/ren/.local/bin/rencrow-lyrics-catalog",
        )

    def test_malformed_flock_exec_start_stays_visible_as_wrapper(self) -> None:
        rendered = (
            "{ path=/usr/bin/flock ; "
            "argv[]=/usr/bin/flock --exclusive /home/ren/.rencrow/config/lock "
            "/home/ren/.local/bin/rencrow-lyrics-catalog collect ; ... }"
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
        with mock.patch.object(
            CHECKER, "build_info", return_value=self.fresh_build_info()
        ), mock.patch.object(CHECKER.shutil, "copy2"), mock.patch.object(
            CHECKER.os, "chmod"
        ), mock.patch.object(
            CHECKER, "start_and_settle",
            side_effect=start_results or [None],
        ):
            if prepare_receipt is None:
                result = CHECKER.redeploy(
                    self.ROW,
                    self.COMPONENTS,
                    root,
                    dry=False,
                    runner=self.runner(calls),
                    receipt_log=receipt_log,
                )
            else:
                with mock.patch.object(CHECKER, "prepare_receipt_log", prepare_receipt):
                    result = CHECKER.redeploy(
                        self.ROW,
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
            self.assertEqual(receipt["binary_path"], self.ROW["binary"])
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


if __name__ == "__main__":
    unittest.main()

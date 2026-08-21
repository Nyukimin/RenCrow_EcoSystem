from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()

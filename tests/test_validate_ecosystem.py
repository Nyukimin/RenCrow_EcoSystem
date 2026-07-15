from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPOSITORY_ROOT / "scripts" / "validate_ecosystem.py"
SPEC = importlib.util.spec_from_file_location("validate_ecosystem", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class EcosystemManifestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = VALIDATOR.load_manifest(REPOSITORY_ROOT / "ecosystem.yaml")

    def test_repository_manifest_is_valid(self) -> None:
        VALIDATOR.validate_manifest(self.manifest)

    def test_verified_release_rejects_unpinned_components(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        candidate["ecosystem"]["compatibility_status"] = "verified"

        with self.assertRaisesRegex(VALIDATOR.ManifestError, "unpinned components"):
            VALIDATOR.validate_manifest(candidate)

    def test_duplicate_repository_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        candidate["components"]["cmd"]["repository"] = candidate["components"][
            "core"
        ]["repository"]

        with self.assertRaisesRegex(VALIDATOR.ManifestError, "duplicate repository"):
            VALIDATOR.validate_manifest(candidate)

    def test_secret_like_keys_are_rejected(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        candidate["ecosystem"]["api_key"] = "must-not-be-here"

        with self.assertRaisesRegex(VALIDATOR.ManifestError, "secret-like key"):
            VALIDATOR.validate_manifest(candidate)

    def test_workspace_path_must_be_one_sibling(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        candidate["components"]["core"]["workspace_path"] = "../../RenCrow_CORE"

        with self.assertRaisesRegex(VALIDATOR.ManifestError, "one sibling"):
            VALIDATOR.validate_manifest(candidate)


if __name__ == "__main__":
    unittest.main()

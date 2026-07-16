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

    def test_llm_declares_go_primary_and_external_compute(self) -> None:
        llm_runtime = self.manifest["components"]["llm"]["runtime"]

        self.assertEqual(llm_runtime["primary"]["implementation"], "go")
        self.assertEqual(llm_runtime["primary"]["artifact"], "rencrow-llm")
        self.assertEqual(
            llm_runtime["companions"][0]["kind"], "external-compute"
        )
        self.assertFalse(llm_runtime["companions"][0]["bundled"])

    def test_runtime_primary_requires_known_implementation(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        candidate["components"]["llm"]["runtime"]["primary"][
            "implementation"
        ] = "unknown-language"

        with self.assertRaisesRegex(VALIDATOR.ManifestError, "implementation"):
            VALIDATOR.validate_manifest(candidate)

    def test_runtime_companion_ids_must_be_unique(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        companions = candidate["components"]["llm"]["runtime"]["companions"]
        companions.append(copy.deepcopy(companions[0]))

        with self.assertRaisesRegex(VALIDATOR.ManifestError, "duplicate companion"):
            VALIDATOR.validate_manifest(candidate)

    def test_external_compute_cannot_be_bundled(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        candidate["components"]["llm"]["runtime"]["companions"][0][
            "bundled"
        ] = True

        with self.assertRaisesRegex(VALIDATOR.ManifestError, "external-compute"):
            VALIDATOR.validate_manifest(candidate)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import importlib.util
import tempfile
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
        self.assertEqual(len(llm_runtime["companions"]), 1)
        self.assertEqual(llm_runtime["companions"][0]["id"], "llm-target")
        self.assertEqual(llm_runtime["companions"][0]["kind"], "external-compute")
        self.assertFalse(llm_runtime["companions"][0]["bundled"])

    def test_stt_declares_go_primary_and_external_compute(self) -> None:
        stt_runtime = self.manifest["components"]["stt"]["runtime"]

        self.assertEqual(stt_runtime["primary"]["implementation"], "go")
        self.assertEqual(stt_runtime["primary"]["artifact"], "rencrow-stt")
        self.assertEqual(stt_runtime["companions"][0]["id"], "stt-target")
        self.assertEqual(stt_runtime["companions"][0]["kind"], "external-compute")
        self.assertFalse(stt_runtime["companions"][0]["bundled"])

    def test_tts_declares_go_primary_and_external_compute(self) -> None:
        tts_runtime = self.manifest["components"]["tts"]["runtime"]

        self.assertEqual(tts_runtime["primary"]["implementation"], "go")
        self.assertEqual(tts_runtime["primary"]["artifact"], "rencrow-tts")
        self.assertEqual(tts_runtime["companions"][0]["id"], "tts-target")
        self.assertEqual(tts_runtime["companions"][0]["kind"], "external-compute")
        self.assertFalse(tts_runtime["companions"][0]["bundled"])

    def test_gateways_only_declare_external_compute_targets(self) -> None:
        for component_id in ("llm", "stt", "tts"):
            companions = self.manifest["components"][component_id]["runtime"][
                "companions"
            ]
            self.assertTrue(companions)
            self.assertEqual(
                {companion["kind"] for companion in companions},
                {"external-compute"},
            )

    def test_cmd_and_portal_use_core_public_api(self) -> None:
        cmd_role = self.manifest["components"]["cmd"]["role"]
        portal_role = self.manifest["components"]["portal"]["role"]

        self.assertIn("CORE Public API", cmd_role)
        self.assertIn("CORE Public API", portal_role)
        self.assertNotIn("ASSISTANT", cmd_role)
        self.assertNotIn("ASSISTANT", portal_role)

    def test_image_is_a_service_and_workspace_is_a_snapshot(self) -> None:
        self.assertEqual(
            self.manifest["components"]["image"]["distribution"], "service"
        )
        self.assertEqual(
            self.manifest["components"]["workspace"]["distribution"], "snapshot"
        )

    def test_games_declares_core_initiated_observed_execution(self) -> None:
        games_role = self.manifest["components"]["games"]["role"]
        self.assertIn("CORE-initiated", games_role)
        self.assertIn("observer", games_role.lower())
        self.assertIn("title-local control", games_role)
        self.assertIn("deterministic execution", games_role)
        self.assertIn("result delivery", games_role)

    def test_assistant_declares_planned_go_primary(self) -> None:
        assistant = self.manifest["components"]["assistant"]
        assistant_runtime = assistant["runtime"]

        self.assertEqual(assistant["distribution"], "binary")
        self.assertEqual(assistant_runtime["primary"]["implementation"], "go")
        self.assertEqual(
            assistant_runtime["primary"]["artifact"], "rencrow-assistant"
        )
        self.assertEqual(assistant_runtime["primary"]["status"], "planned")

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

    def test_workspace_validation_skips_missing_optional_component(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            workspace = Path(temp_directory)
            ecosystem = workspace / "RenCrow_EcoSystem"
            ecosystem.mkdir()
            manifest_path = ecosystem / "ecosystem.yaml"
            manifest_path.touch()
            (workspace / "RenCrow_CORE" / ".git").mkdir(parents=True)
            candidate = {
                "components": {
                    "core": {
                        "workspace_path": "../RenCrow_CORE",
                        "required": True,
                    },
                    "assistant": {
                        "workspace_path": "../RenCrow_ASSISTANT",
                        "required": False,
                    },
                }
            }

            VALIDATOR.validate_workspace(candidate, manifest_path)

    def test_workspace_validation_rejects_missing_required_component(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            workspace = Path(temp_directory)
            ecosystem = workspace / "RenCrow_EcoSystem"
            ecosystem.mkdir()
            manifest_path = ecosystem / "ecosystem.yaml"
            manifest_path.touch()
            candidate = {
                "components": {
                    "core": {
                        "workspace_path": "../RenCrow_CORE",
                        "required": True,
                    }
                }
            }

            with self.assertRaisesRegex(
                VALIDATOR.ManifestError, "components.core workspace is missing"
            ):
                VALIDATOR.validate_workspace(candidate, manifest_path)


if __name__ == "__main__":
    unittest.main()

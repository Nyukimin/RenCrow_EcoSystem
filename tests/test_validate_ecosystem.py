from __future__ import annotations

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPOSITORY_ROOT / "scripts" / "validate_ecosystem.py"
SPEC = importlib.util.spec_from_file_location("validate_ecosystem", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class EcosystemManifestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = VALIDATOR.load_manifest(REPOSITORY_ROOT / "ecosystem.yaml")
        self.coverage_policy = VALIDATOR.load_coverage_policy(
            REPOSITORY_ROOT / "config" / "full-system-coverage.json"
        )

    def test_full_system_coverage_policy_is_valid(self) -> None:
        VALIDATOR.validate_coverage_policy(self.coverage_policy, self.manifest)

    def test_full_system_coverage_policy_declares_exact_guarantee_classes(self) -> None:
        self.assertEqual(
            self.coverage_policy["guarantee_classes"],
            [
                "source_identity",
                "artifact_identity",
                "runtime_identity",
                "readiness",
                "canonical_e2e",
                "actor_result",
                "receipt_trace",
                "security_exposure",
                "durability",
                "lifecycle",
                "publication",
            ],
        )

    def test_full_system_coverage_policy_declares_every_required_phase(self) -> None:
        self.assertEqual(
            self.coverage_policy["required_phases"],
            ["startup", "runtime", "deploy", "backup", "diagnostic"],
        )

        candidate = copy.deepcopy(self.coverage_policy)
        candidate["required_phases"].remove("startup")
        with self.assertRaisesRegex(VALIDATOR.ManifestError, "required_phases"):
            VALIDATOR.validate_coverage_policy(candidate, self.manifest)

    def test_assistant_is_required_but_temporarily_excluded_as_unimplemented(
        self,
    ) -> None:
        self.assertTrue(self.manifest["components"]["assistant"]["required"])
        self.assertEqual(
            self.coverage_policy["temporarily_excluded_components"],
            {
                "assistant": {
                    "reason": "required_component_unimplemented",
                    "reinclude_when": "canonical_runtime_implemented",
                }
            },
        )

    def test_coverage_policy_rejects_unknown_or_malformed_temporary_exclusion(
        self,
    ) -> None:
        candidate = copy.deepcopy(self.coverage_policy)
        candidate["temporarily_excluded_components"]["not_in_manifest"] = {
            "reason": "required_component_unimplemented",
            "reinclude_when": "canonical_runtime_implemented",
        }
        with self.assertRaisesRegex(VALIDATOR.ManifestError, "extra component"):
            VALIDATOR.validate_coverage_policy(candidate, self.manifest)

        candidate = copy.deepcopy(self.coverage_policy)
        candidate["temporarily_excluded_components"]["assistant"]["reason"] = ""
        with self.assertRaisesRegex(VALIDATOR.ManifestError, "reason"):
            VALIDATOR.validate_coverage_policy(candidate, self.manifest)

    def test_full_system_coverage_policy_varies_requirements_by_component_type(
        self,
    ) -> None:
        requirements = self.coverage_policy["component_requirements"]
        self.assertNotEqual(requirements["core"], requirements["portal"])
        self.assertNotEqual(requirements["llm"], requirements["workspace"])
        self.assertNotEqual(requirements["games"], requirements["tools"])
        self.assertTrue(all(requirements.values()))

    def test_coverage_policy_rejects_missing_component_requirement(self) -> None:
        candidate = copy.deepcopy(self.coverage_policy)
        del candidate["component_requirements"]["core"]

        with self.assertRaisesRegex(VALIDATOR.ManifestError, "missing component"):
            VALIDATOR.validate_coverage_policy(candidate, self.manifest)

    def test_coverage_policy_rejects_extra_component_requirement(self) -> None:
        candidate = copy.deepcopy(self.coverage_policy)
        candidate["component_requirements"]["not_in_manifest"] = [
            "source_identity"
        ]

        with self.assertRaisesRegex(VALIDATOR.ManifestError, "extra component"):
            VALIDATOR.validate_coverage_policy(candidate, self.manifest)

    def test_coverage_policy_rejects_unknown_duplicate_and_empty_classes(self) -> None:
        candidate = copy.deepcopy(self.coverage_policy)
        candidate["component_requirements"]["core"] = ["unknown_class"]
        with self.assertRaisesRegex(VALIDATOR.ManifestError, "unknown guarantee class"):
            VALIDATOR.validate_coverage_policy(candidate, self.manifest)

        candidate = copy.deepcopy(self.coverage_policy)
        candidate["component_requirements"]["core"] = [
            "source_identity",
            "source_identity",
        ]
        with self.assertRaisesRegex(VALIDATOR.ManifestError, "duplicate guarantee class"):
            VALIDATOR.validate_coverage_policy(candidate, self.manifest)

        candidate = copy.deepcopy(self.coverage_policy)
        candidate["component_requirements"]["core"] = []
        with self.assertRaisesRegex(VALIDATOR.ManifestError, "must be non-empty"):
            VALIDATOR.validate_coverage_policy(candidate, self.manifest)

    def test_coverage_policy_rejects_malformed_cross_system_requirement(self) -> None:
        candidate = copy.deepcopy(self.coverage_policy)
        candidate["cross_system_requirements"]["browser_ui"] = [
            "unknown_class"
        ]

        with self.assertRaisesRegex(VALIDATOR.ManifestError, "cross_system_requirements"):
            VALIDATOR.validate_coverage_policy(candidate, self.manifest)

        candidate = copy.deepcopy(self.coverage_policy)
        del candidate["cross_system_requirements"]["backup_restore"]
        with self.assertRaisesRegex(VALIDATOR.ManifestError, "cross_system_requirements"):
            VALIDATOR.validate_coverage_policy(candidate, self.manifest)

    def test_coverage_policy_rejects_secret_like_and_operational_keys(self) -> None:
        candidate = copy.deepcopy(self.coverage_policy)
        candidate["secret_token"] = "must-not-be-here"
        with self.assertRaisesRegex(VALIDATOR.ManifestError, "secret-like key"):
            VALIDATOR.validate_coverage_policy(candidate, self.manifest)

        candidate = copy.deepcopy(self.coverage_policy)
        candidate["cross_system_requirements"]["browser_ui"] = {
            "commands": ["pytest"]
        }
        with self.assertRaisesRegex(VALIDATOR.ManifestError, "operational detail"):
            VALIDATOR.validate_coverage_policy(candidate, self.manifest)

    def test_repository_manifest_is_valid(self) -> None:
        VALIDATOR.validate_manifest(self.manifest)

    def test_production_user_systemd_readiness_contracts_are_declared(self) -> None:
        expected = {
            "core": {
                "rencrow.service": ("http_json", "http://127.0.0.1:18790/health/ready", 300, "ready", True),
                "rencrow-resilience.service": ("oneshot", None, None, None, None),
            },
            "games": {
                "rencrow-games-observer.service": ("http_json", "http://127.0.0.1:18796/games/status", 60, "ok", True),
            },
            "image": {
                "rencrow-image.service": ("http_json", "http://127.0.0.1:8780/health", 180, "status", "ready"),
            },
            "llm": {
                "rencrow-llm.service": ("http_json", "http://127.0.0.1:8090/health", 180, "status", "ok"),
            },
            "tools": {
                "rencrow-lyrics-collector.service": ("oneshot", None, None, None, None),
                "rencrow-movie-catalog.service": ("http_json", "http://127.0.0.1:8790/health", 60, "status", "ready"),
                "rencrow-person-related-catalog.service": ("http_json", "http://127.0.0.1:18087/ready", 60, "status", "ok"),
            },
            "portal": {
                "rencrow-portal.service": ("http_json", "http://127.0.0.1:18791/health/ready", 180, "status", "ready"),
            },
            "stt": {
                "rencrow-stt.service": ("http_json", "http://127.0.0.1:8766/health/ready", 180, "ready", True),
            },
            "trade": {
                "rencrow-trade.service": ("http_json", "http://127.0.0.1:8767/ready", 120, "ready", True),
                "rencrow-trade-learning.service": ("oneshot", None, None, None, None),
            },
            "tts": {
                "rencrow-tts.service": ("http_json", "http://127.0.0.1:7870/health/ready", 180, "status", "ready"),
            },
            "vision": {
                "rencrow-vision.service": ("http_json", "http://127.0.0.1:8770/health", 180, "status", "ready"),
            },
        }

        for component_id, contracts in expected.items():
            with self.subTest(component_id=component_id):
                declared = self.manifest["components"][component_id]["deployment"][
                    "user_systemd"
                ]
                self.assertEqual({item["unit"] for item in declared}, set(contracts))
                for item in declared:
                    kind, url, timeout, path, equals = contracts[item["unit"]]
                    self.assertEqual(item["kind"], kind)
                    if kind == "oneshot":
                        self.assertEqual(set(item), {"unit", "kind"})
                    else:
                        self.assertEqual(item["url"], url)
                        self.assertEqual(item["timeout_seconds"], timeout)
                        self.assertEqual(item["expect"], {"path": path, "equals": equals})

    def test_manifest_uses_governance_schema_version_four(self) -> None:
        self.assertEqual(self.manifest["schema_version"], 4)

    def test_verified_release_rejects_unpinned_components(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        candidate["ecosystem"]["compatibility_status"] = "verified"
        candidate["components"]["core"]["version"] = "unpinned"

        with self.assertRaisesRegex(VALIDATOR.ManifestError, "unpinned components"):
            VALIDATOR.validate_manifest(candidate)

    def test_source_pinned_manifest_uses_full_commit_shas(self) -> None:
        for component_id, component in self.manifest["components"].items():
            if component["version"] == "planned":
                self.assertEqual(component_id, "assistant")
                continue
            self.assertRegex(
                component["version"],
                VALIDATOR.COMMIT_VERSION_PATTERN,
                component_id,
            )

    def test_source_pinned_rejects_non_commit_version(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        candidate["components"]["cmd"]["version"] = "v0.1.0"

        with self.assertRaisesRegex(VALIDATOR.ManifestError, "full commit SHA"):
            VALIDATOR.validate_manifest(candidate)

    def test_planned_version_requires_optional_planned_runtime(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        candidate["components"]["core"]["version"] = "planned"

        with self.assertRaisesRegex(VALIDATOR.ManifestError, "optional planned runtime"):
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

    def test_readiness_contract_rejects_extra_keys(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        contract = candidate["components"]["core"]["deployment"]["user_systemd"][0]
        contract["unexpected"] = True

        with self.assertRaisesRegex(VALIDATOR.ManifestError, "readiness contract"):
            VALIDATOR.validate_manifest(candidate)

    def test_managed_file_contracts_are_validated(self) -> None:
        files = self.manifest["components"]["core"]["deployment"]["files"]
        self.assertEqual(len(files), 5)
        self.assertEqual(files[0]["mode"], "0755")
        check_manifest = files[-1]
        self.assertEqual(check_manifest["source_path"], "config/checks/core.json")
        self.assertEqual(
            check_manifest["installed_path"],
            "%h/.local/share/rencrow/checks/core.json",
        )
        self.assertEqual(check_manifest["mode"], "0644")

        for component_id in (
            "portal",
            "assistant",
            "cmd",
            "llm",
            "stt",
            "tts",
            "vision",
            "games",
            "trade",
            "tools",
            "image",
            "workspace",
        ):
            module_files = self.manifest["components"][component_id]["deployment"][
                "files"
            ]
            check_files = [
                item
                for item in module_files
                if item["source_path"] == "config/checks/runtime.json"
            ]
            self.assertEqual(len(check_files), 1, component_id)
            self.assertEqual(
                check_files[0]["source_path"], "config/checks/runtime.json"
            )
            self.assertEqual(check_files[0]["mode"], "0644")

        candidate = copy.deepcopy(self.manifest)
        candidate["components"]["core"]["deployment"]["files"][0]["source_path"] = "../secret"
        with self.assertRaisesRegex(VALIDATOR.ManifestError, "safe relative"):
            VALIDATOR.validate_manifest(candidate)

        candidate = copy.deepcopy(self.manifest)
        candidate["components"]["core"]["deployment"]["files"][0]["sha256"] = "bad"
        with self.assertRaisesRegex(VALIDATOR.ManifestError, "SHA-256"):
            VALIDATOR.validate_manifest(candidate)

    def test_readiness_contract_rejects_duplicate_units_globally(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        duplicate = copy.deepcopy(
            candidate["components"]["core"]["deployment"]["user_systemd"][0]
        )
        candidate["components"]["portal"]["deployment"]["user_systemd"].append(
            duplicate
        )

        with self.assertRaisesRegex(VALIDATOR.ManifestError, "duplicate user systemd unit"):
            VALIDATOR.validate_manifest(candidate)

    def test_readiness_contract_rejects_non_loopback_url_and_non_scalar_expectation(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        contract = candidate["components"]["core"]["deployment"]["user_systemd"][0]
        contract["url"] = "https://example.invalid/health/ready"

        with self.assertRaisesRegex(VALIDATOR.ManifestError, "loopback"):
            VALIDATOR.validate_manifest(candidate)

        contract["url"] = "http://127.0.0.1:18790/health/ready"
        contract["expect"]["equals"] = {"ready": True}
        with self.assertRaisesRegex(VALIDATOR.ManifestError, "scalar"):
            VALIDATOR.validate_manifest(candidate)

    def test_workspace_path_must_be_one_ascii_direct_child(self) -> None:
        invalid_paths = (
            "../RenCrow_CORE",
            "RenCrow_CORE",
            "./nested/RenCrow_CORE",
            "./../RenCrow_CORE",
            r".\RenCrow_CORE",
            "./RenCrow CORE",
            "./RenCrow/CORE",
            "./_RenCrow_CORE",
            "./RenCrow-é",
        )
        for invalid_path in invalid_paths:
            with self.subTest(invalid_path=invalid_path):
                candidate = copy.deepcopy(self.manifest)
                candidate["components"]["core"]["workspace_path"] = invalid_path

                with self.assertRaisesRegex(VALIDATOR.ManifestError, "direct child"):
                    VALIDATOR.validate_manifest(candidate)

    def test_llm_declares_go_primary_and_external_compute(self) -> None:
        llm_runtime = self.manifest["components"]["llm"]["runtime"]

        self.assertEqual(llm_runtime["primary"]["implementation"], "go")
        self.assertEqual(llm_runtime["primary"]["artifact"], "rencrow-llm")
        self.assertEqual(len(llm_runtime["companions"]), 1)
        self.assertEqual(llm_runtime["companions"][0]["id"], "llm-runtime")
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

    def test_vision_declares_go_primary_and_external_compute(self) -> None:
        vision_runtime = self.manifest["components"]["vision"]["runtime"]

        self.assertEqual(vision_runtime["primary"]["implementation"], "go")
        self.assertEqual(vision_runtime["primary"]["artifact"], "rencrow-vision")
        self.assertEqual(vision_runtime["companions"][0]["id"], "vision-backend")
        self.assertEqual(vision_runtime["companions"][0]["kind"], "external-compute")
        self.assertFalse(vision_runtime["companions"][0]["bundled"])

    def test_image_declares_go_primary_and_external_compute(self) -> None:
        image_runtime = self.manifest["components"]["image"]["runtime"]

        self.assertEqual(image_runtime["primary"]["implementation"], "go")
        self.assertEqual(image_runtime["primary"]["artifact"], "rencrow-image")
        self.assertEqual(image_runtime["companions"][0]["id"], "image-backend")
        self.assertEqual(image_runtime["companions"][0]["kind"], "external-compute")
        self.assertFalse(image_runtime["companions"][0]["bundled"])

    def test_gateways_only_declare_external_compute_targets(self) -> None:
        for component_id in ("llm", "stt", "tts", "vision", "image"):
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

    def test_vision_and_image_are_binaries_and_workspace_is_a_snapshot(self) -> None:
        self.assertEqual(
            self.manifest["components"]["vision"]["distribution"], "binary"
        )
        self.assertEqual(
            self.manifest["components"]["image"]["distribution"], "binary"
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

    def test_assistant_declares_development_go_primary(self) -> None:
        assistant = self.manifest["components"]["assistant"]
        assistant_runtime = assistant["runtime"]

        self.assertEqual(assistant["distribution"], "binary")
        self.assertEqual(assistant_runtime["primary"]["implementation"], "go")
        self.assertEqual(
            assistant_runtime["primary"]["artifact"], "rencrow-assistant"
        )
        self.assertEqual(assistant_runtime["primary"]["status"], "development")

    def test_trade_declares_development_go_primary(self) -> None:
        trade = self.manifest["components"]["trade"]

        self.assertEqual(trade["distribution"], "binary")
        self.assertEqual(trade["runtime"]["primary"]["implementation"], "go")
        self.assertEqual(
            trade["runtime"]["primary"]["artifact"], "rencrow-trade"
        )
        self.assertEqual(trade["runtime"]["primary"]["status"], "development")
        self.assertEqual(trade["runtime"]["companions"], [])

    def test_model_repositories_are_llm_external_runtime_profiles(self) -> None:
        profiles = self.manifest["runtime_profiles"]

        self.assertEqual(set(profiles), {"gpt120b", "qwen36-27b", "gemma4"})
        for profile in profiles.values():
            self.assertEqual(profile["owner_component"], "llm")
            self.assertEqual(profile["kind"], "external-compute")
            self.assertFalse(profile["required"])
            self.assertRegex(profile["version"], VALIDATOR.COMMIT_VERSION_PATTERN)

    def test_runtime_profile_owner_must_exist(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        candidate["runtime_profiles"]["gpt120b"]["owner_component"] = "missing"

        with self.assertRaisesRegex(VALIDATOR.ManifestError, "owner_component"):
            VALIDATOR.validate_manifest(candidate)

    def test_runtime_profile_repository_cannot_duplicate_component(self) -> None:
        candidate = copy.deepcopy(self.manifest)
        candidate["runtime_profiles"]["gpt120b"]["repository"] = candidate[
            "components"
        ]["llm"]["repository"]

        with self.assertRaisesRegex(VALIDATOR.ManifestError, "duplicate repository"):
            VALIDATOR.validate_manifest(candidate)

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
            manifest_path = workspace / "ecosystem.yaml"
            manifest_path.touch()
            (workspace / "RenCrow_CORE" / ".git").mkdir(parents=True)
            candidate = {
                "components": {
                    "core": {
                        "workspace_path": "./RenCrow_CORE",
                        "required": True,
                    },
                    "assistant": {
                        "workspace_path": "./RenCrow_ASSISTANT",
                        "required": False,
                    },
                }
            }

            VALIDATOR.validate_workspace(candidate, manifest_path)

    def test_workspace_validation_rejects_missing_required_component(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            workspace = Path(temp_directory)
            manifest_path = workspace / "ecosystem.yaml"
            manifest_path.touch()
            candidate = {
                "components": {
                    "core": {
                        "workspace_path": "./RenCrow_CORE",
                        "required": True,
                    }
                }
            }

            with self.assertRaisesRegex(
                VALIDATOR.ManifestError, "components.core workspace is missing"
            ):
                VALIDATOR.validate_workspace(candidate, manifest_path)

    def test_workspace_validation_checks_source_pinned_head(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            workspace = Path(temp_directory)
            manifest_path = workspace / "ecosystem.yaml"
            manifest_path.touch()
            (workspace / "RenCrow_CORE" / ".git").mkdir(parents=True)
            candidate = {
                "ecosystem": {"compatibility_status": "source-pinned"},
                "components": {
                    "core": {
                        "workspace_path": "./RenCrow_CORE",
                        "required": True,
                        "version": "a" * 40,
                    }
                },
            }

            with mock.patch.object(VALIDATOR, "_git_head", return_value="b" * 40):
                with self.assertRaisesRegex(
                    VALIDATOR.ManifestError, "does not match source-pinned"
                ):
                    VALIDATOR.validate_workspace(candidate, manifest_path)

    def test_governance_rejects_missing_agents_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            workspace = Path(temp_directory)
            catalog = workspace
            component = workspace / "RenCrow_CORE"
            self._write_governance_repository(catalog, with_ci=True)
            self._write_governance_repository(component, with_ci=True)
            (catalog / "AGENTS.md").write_text("root\n", encoding="utf-8")
            manifest_path = catalog / "ecosystem.yaml"
            manifest_path.touch()
            (component / "AGENTS.md").unlink()
            candidate = {
                "components": {
                    "core": {
                        "workspace_path": "./RenCrow_CORE",
                        "required": True,
                        "distribution": "binary",
                    }
                },
                "runtime_profiles": {},
            }

            with self.assertRaisesRegex(VALIDATOR.ManifestError, "AGENTS.md"):
                VALIDATOR.validate_governance(candidate, manifest_path)

    def test_governance_rejects_active_component_without_ci(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            workspace = Path(temp_directory)
            catalog = workspace
            component = workspace / "RenCrow_CORE"
            self._write_governance_repository(catalog, with_ci=True)
            self._write_governance_repository(component, with_ci=False)
            (catalog / "AGENTS.md").write_text("root\n", encoding="utf-8")
            manifest_path = catalog / "ecosystem.yaml"
            manifest_path.touch()
            candidate = {
                "components": {
                    "core": {
                        "workspace_path": "./RenCrow_CORE",
                        "required": True,
                        "distribution": "binary",
                    }
                },
                "runtime_profiles": {},
            }

            with self.assertRaisesRegex(VALIDATOR.ManifestError, "CI workflow"):
                VALIDATOR.validate_governance(candidate, manifest_path)

    def test_governance_rejects_copied_common_rules_outside_core(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            workspace = Path(temp_directory)
            catalog = workspace
            component = workspace / "RenCrow_LLM"
            self._write_governance_repository(catalog, with_ci=True)
            self._write_governance_repository(component, with_ci=True)
            copied_rules = component / "rules" / "common"
            copied_rules.mkdir(parents=True)
            (copied_rules / "GLOBAL_AGENT.md").write_text(
                "copied\n", encoding="utf-8"
            )
            (catalog / "AGENTS.md").write_text("root\n", encoding="utf-8")
            manifest_path = catalog / "ecosystem.yaml"
            manifest_path.touch()
            candidate = {
                "components": {
                    "llm": {
                        "workspace_path": "./RenCrow_LLM",
                        "required": True,
                        "distribution": "binary",
                    }
                },
                "runtime_profiles": {},
            }

            with self.assertRaisesRegex(VALIDATOR.ManifestError, "must not copy"):
                VALIDATOR.validate_governance(candidate, manifest_path)

    def test_governance_runtime_profile_requires_only_rule_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            workspace = Path(temp_directory)
            catalog = workspace
            profile = workspace / "RenCrow_Model"
            self._write_governance_repository(catalog, with_ci=True)
            profile.mkdir()
            (profile / "AGENTS.md").write_text("rules\n", encoding="utf-8")
            (profile / "README.md").write_text("model\n", encoding="utf-8")
            (catalog / "AGENTS.md").write_text("root\n", encoding="utf-8")
            manifest_path = catalog / "ecosystem.yaml"
            manifest_path.touch()
            candidate = {
                "components": {},
                "runtime_profiles": {
                    "model": {
                        "workspace_path": "./RenCrow_Model",
                        "required": False,
                    }
                },
            }

            VALIDATOR.validate_governance(candidate, manifest_path)

    def test_governance_accepts_matching_root_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            workspace = Path(temp_directory)
            catalog = workspace
            snapshot = workspace / "RenCrow_Workspace"
            self._write_governance_repository(catalog, with_ci=True)
            self._write_governance_repository(snapshot, with_ci=False)
            (snapshot / "project-root").mkdir()
            root_rules = (
                "\n".join(VALIDATOR.CONCEPTUAL_INTEGRITY_REQUIRED_MARKERS) + "\n"
            )
            (catalog / "AGENTS.md").write_text(root_rules, encoding="utf-8")
            (snapshot / "project-root" / "AGENTS.md").write_text(
                root_rules, encoding="utf-8"
            )
            manifest_path = catalog / "ecosystem.yaml"
            manifest_path.touch()
            candidate = {
                "components": {
                    "workspace": {
                        "workspace_path": "./RenCrow_Workspace",
                        "required": True,
                        "distribution": "snapshot",
                    }
                },
                "runtime_profiles": {},
            }

            VALIDATOR.validate_governance(candidate, manifest_path)

    def test_governance_rejects_root_snapshot_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            workspace = Path(temp_directory)
            catalog = workspace
            snapshot = workspace / "RenCrow_Workspace"
            self._write_governance_repository(catalog, with_ci=True)
            self._write_governance_repository(snapshot, with_ci=False)
            (snapshot / "project-root").mkdir()
            root_rules = (
                "\n".join(VALIDATOR.CONCEPTUAL_INTEGRITY_REQUIRED_MARKERS) + "\n"
            )
            (snapshot / "project-root" / "AGENTS.md").write_text(
                root_rules + "snapshot drift\n", encoding="utf-8"
            )
            (catalog / "AGENTS.md").write_text(root_rules, encoding="utf-8")
            manifest_path = catalog / "ecosystem.yaml"
            manifest_path.touch()
            candidate = {
                "components": {
                    "workspace": {
                        "workspace_path": "./RenCrow_Workspace",
                        "required": True,
                        "distribution": "snapshot",
                    }
                },
                "runtime_profiles": {},
            }

            with self.assertRaisesRegex(VALIDATOR.ManifestError, "does not match"):
                VALIDATOR.validate_governance(candidate, manifest_path)

    def test_governance_rejects_missing_conceptual_integrity_guardrail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            catalog = Path(temp_directory)
            snapshot = catalog / "RenCrow_Workspace"
            self._write_governance_repository(catalog, with_ci=True)
            self._write_governance_repository(snapshot, with_ci=False)
            (snapshot / "project-root").mkdir()
            (catalog / "AGENTS.md").write_text("root\n", encoding="utf-8")
            (snapshot / "project-root" / "AGENTS.md").write_text(
                "root\n", encoding="utf-8"
            )
            manifest_path = catalog / "ecosystem.yaml"
            manifest_path.touch()
            candidate = {
                "components": {
                    "workspace": {
                        "workspace_path": "./RenCrow_Workspace",
                        "required": True,
                        "distribution": "snapshot",
                    }
                },
                "runtime_profiles": {},
            }

            with self.assertRaisesRegex(
                VALIDATOR.ManifestError, "missing Conceptual Integrity Guardrail"
            ):
                VALIDATOR.validate_governance(candidate, manifest_path)

    @staticmethod
    def _write_governance_repository(path: Path, with_ci: bool) -> None:
        (path / "scripts").mkdir(parents=True)
        (path / "AGENTS.md").write_text("rules\n", encoding="utf-8")
        (path / "README.md").write_text("readme\n", encoding="utf-8")
        (path / "scripts" / "test-local.ps1").write_text("test\n", encoding="utf-8")
        (path / "scripts" / "test-local.plan.json").write_text(
            "{}\n", encoding="utf-8"
        )
        if with_ci:
            (path / ".github" / "workflows").mkdir(parents=True)
            (path / ".github" / "workflows" / "test.yml").write_text(
                "name: test\n", encoding="utf-8"
            )


if __name__ == "__main__":
    unittest.main()

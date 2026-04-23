import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = REPO_ROOT / ".ai/workflows/sdd-linear"
CORE_MODULE_PATH = CORE_ROOT / "bin/sdd_linear_core.py"
BOOTSTRAP_SCRIPT = REPO_ROOT / "scripts/bootstrap-sdd-linear.sh"
COMMAND_DIR = REPO_ROOT / ".opencode/commands/sdd-linear"
HELPER_SKILL = REPO_ROOT / ".atl/skills/sdd-linear-flow/SKILL.md"


def load_core_module():
    spec = importlib.util.spec_from_file_location("sdd_linear_core", CORE_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


CORE_MODULE = load_core_module()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def copy_core_to_temp(destination: Path) -> Path:
    target = destination / ".ai/workflows/sdd-linear"
    shutil.copytree(CORE_ROOT, target)
    return target


def make_args(**kwargs):
    return types.SimpleNamespace(**kwargs)


class WorkflowCoreBatch4Tests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.tempdir.name)
        self.temp_core_root = copy_core_to_temp(self.temp_path)
        self.core = CORE_MODULE.WorkflowCore(self.temp_core_root)

    def tearDown(self):
        self.tempdir.cleanup()

    def create_change(self, **overrides):
        args = make_args(
            change_id="linear-integration",
            linear_issue_id="LIN-123",
            linear_feature_id="PROJ-7",
            title="Linear Integration",
            change_type="change",
            sdd_state="draft",
            **overrides,
        )
        return self.core.create_change(args)

    def metadata(self, change_id="linear-integration"):
        return load_json(self.core.metadata_path(change_id))

    def test_schema_contracts_capture_required_fields_and_retry_constraints(self):
        change_schema = load_json(CORE_ROOT / "contracts/change-metadata.schema.json")
        derived_schema = load_json(CORE_ROOT / "contracts/derived-issue.schema.json")
        archive_schema = load_json(CORE_ROOT / "contracts/archive-evidence.schema.json")

        self.assertEqual(
            change_schema["required"],
            ["version", "changeId", "linear", "workflow", "archive", "derivedIssues", "unresolved"],
        )
        self.assertEqual(change_schema["properties"]["derivedIssues"]["items"]["$ref"], "./derived-issue.schema.json")
        self.assertEqual(derived_schema["properties"]["retry"]["properties"]["max"]["const"], 3)
        self.assertEqual(
            derived_schema["properties"]["status"]["enum"],
            ["logged", "synced", "manual-pending"],
        )
        self.assertEqual(
            derived_schema["properties"]["manualFallback"]["properties"]["fieldOrder"]["const"],
            CORE_MODULE.FIELD_ORDER,
        )
        self.assertEqual(
            archive_schema["$defs"]["gateEvaluation"]["properties"]["status"]["enum"],
            ["blocked", "pass"],
        )
        self.assertEqual(
            archive_schema["$defs"]["gateEvaluation"]["properties"]["remoteRevalidationMode"]["enum"],
            ["disabled"],
        )

    def test_state_map_supports_many_to_few_and_unknown_state_errors(self):
        state_map = load_json(CORE_ROOT / "state-map.json")

        self.assertEqual(state_map["mapping"]["draft"], "Backlog")
        self.assertEqual(state_map["mapping"]["design"], "Backlog")
        self.assertEqual(state_map["mapping"]["apply"], "In Progress")
        self.assertEqual(state_map["mapping"]["ready_to_archive"], "In Progress")
        self.assertEqual(state_map["mapping"]["archived"], "Done")

        with self.assertRaises(CORE_MODULE.CoreError) as error:
            self.core.map_state("unknown-state")

        self.assertIn("Unmapped SDD state 'unknown-state'", str(error.exception))
        self.assertIn("state-map.json", str(error.exception))

    def test_create_change_persists_linear_linked_metadata(self):
        result = self.create_change()
        metadata = self.metadata()

        self.assertEqual(result["status"], "created")
        self.assertEqual(metadata["linear"]["issueId"], "LIN-123")
        self.assertEqual(metadata["linear"]["featureId"], "PROJ-7")
        self.assertEqual(metadata["workflow"], {"sddState": "draft", "mappedLinearState": "Backlog"})
        self.assertEqual(metadata["archive"]["gate"]["status"], "blocked")
        self.assertEqual(metadata["derivedIssues"], [])

    def test_create_change_requires_linear_issue_id_and_does_not_create_metadata(self):
        missing_issue_args = make_args(
            change_id="missing-linear-issue",
            linear_issue_id=None,
            linear_feature_id="PROJ-7",
            title="Missing issue",
            change_type="change",
            sdd_state="draft",
        )

        with self.assertRaises(CORE_MODULE.CoreError) as error:
            self.core.create_change(missing_issue_args)

        self.assertIn("linearIssueId is required", str(error.exception))
        self.assertFalse(self.core.metadata_path("missing-linear-issue").exists())

    def test_status_updates_report_local_and_mapped_state(self):
        self.create_change()

        result = self.core.status(make_args(change_id="linear-integration", sdd_state="qa_pending"))
        metadata = self.metadata()

        self.assertEqual(result["workflow"], {"sddState": "qa_pending", "mappedLinearState": "In Progress"})
        self.assertEqual(metadata["workflow"], result["workflow"])

    def test_log_issue_requires_engram_before_persisting_metadata(self):
        self.create_change()

        with self.assertRaises(CORE_MODULE.CoreError) as error:
            self.core.log_issue(
                make_args(
                    change_id="linear-integration",
                    title="Follow-up bug",
                    summary="Something broke",
                    impact="High",
                    blocking=True,
                    engram_observation_id=0,
                    linear_issue_id=None,
                    attempt_error=[],
                    proposed_linear_state=None,
                    evidence_link=[],
                    operator_notes=None,
                )
            )

        self.assertIn("Save to Engram before logging to Linear", str(error.exception))
        self.assertEqual(self.metadata()["derivedIssues"], [])

    def test_log_issue_records_success_within_retry_budget(self):
        self.create_change()

        result = self.core.log_issue(
            make_args(
                change_id="linear-integration",
                title="Follow-up bug",
                summary="Reproducible failure",
                impact="High",
                blocking=True,
                engram_observation_id=41,
                linear_issue_id="LIN-456",
                attempt_error=["attempt-1 failed"],
                proposed_linear_state="In Progress",
                evidence_link=["https://example.com/log"],
                operator_notes="Recovered on retry 2.",
            )
        )

        derived_issue = result["derivedIssue"]
        self.assertEqual(result["status"], "synced")
        self.assertEqual(derived_issue["retry"], {"attempted": 2, "max": 3})
        self.assertEqual(derived_issue["linearIssueId"], "LIN-456")
        self.assertFalse(derived_issue["manualFallback"]["required"])
        self.assertIsNone(derived_issue["manualFallback"]["payload"])

    def test_log_issue_generates_manual_fallback_after_third_failure(self):
        self.create_change()

        result = self.core.log_issue(
            make_args(
                change_id="linear-integration",
                title="Manual follow-up",
                summary="Linear retry budget exhausted",
                impact="Critical",
                blocking=False,
                engram_observation_id=99,
                linear_issue_id=None,
                attempt_error=["attempt-1", "attempt-2", "attempt-3"],
                proposed_linear_state="Backlog",
                evidence_link=["https://example.com/evidence/1", "https://example.com/evidence/2"],
                operator_notes="Escalate to manual creation.",
            )
        )

        derived_issue = result["derivedIssue"]
        manual_fallback = derived_issue["manualFallback"]

        self.assertEqual(result["status"], "manual-pending")
        self.assertEqual(derived_issue["retry"], {"attempted": 3, "max": 3})
        self.assertTrue(manual_fallback["required"])
        self.assertEqual(manual_fallback["fieldOrder"], CORE_MODULE.FIELD_ORDER)
        self.assertEqual(manual_fallback["payload"]["parentLinearIssueId"], "LIN-123")
        self.assertEqual(manual_fallback["payload"]["engramObservationId"], 99)
        self.assertEqual(
            manual_fallback["payload"]["evidenceLinks"],
            ["https://example.com/evidence/1", "https://example.com/evidence/2"],
        )
        self.assertIn("all 3 Linear creation attempts fail", manual_fallback["prompt"])
        self.assertIn("Manual follow-up", manual_fallback["prompt"])

    def test_log_issue_contract_documents_caller_owned_sync_boundary(self):
        command_doc = (COMMAND_DIR / "sdd-log-issue.md").read_text(encoding="utf-8")

        self.assertIn("Save the finding to Engram first and capture `engramObservationId`", command_doc)
        self.assertIn("Accept optional sync outcome data", command_doc)
        self.assertIn("Return the JSON emitted by the neutral core", command_doc)

    def test_archive_pass_renders_comment_and_allows_close(self):
        self.create_change()

        result = self.core.archive(
            make_args(
                change_id="linear-integration",
                pr_url="https://github.com/example/repo/pull/1",
                merge_confirmed=True,
                qa_notes="QA sign-off captured.",
                business_validation="PM approved release.",
                archive_summary="Ready to close.",
                follow_up_notes="No follow-up needed.",
            )
        )

        archive = result["archive"]
        self.assertEqual(result["status"], "pass")
        self.assertEqual(archive["gate"]["missing"], [])
        self.assertTrue(archive["comment"]["commentAllowed"])
        self.assertTrue(archive["comment"]["closeAllowed"])
        self.assertIn("https://github.com/example/repo/pull/1", archive["comment"]["body"])
        self.assertIn("Ready to close.", archive["comment"]["body"])

    def test_archive_missing_evidence_blocks_comment_and_close(self):
        self.create_change()

        result = self.core.archive(
            make_args(
                change_id="linear-integration",
                pr_url="https://github.com/example/repo/pull/1",
                merge_confirmed=True,
                qa_notes=None,
                business_validation="PM approved release.",
                archive_summary=None,
                follow_up_notes=None,
            )
        )

        archive = result["archive"]
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(archive["gate"]["missing"], ["qaNotes"])
        self.assertFalse(archive["comment"]["commentAllowed"])
        self.assertFalse(archive["comment"]["closeAllowed"])
        self.assertIsNone(archive["comment"]["body"])

    def test_archive_contract_documents_render_only_boundary(self):
        command_doc = (COMMAND_DIR / "sdd-archive.md").read_text(encoding="utf-8")

        self.assertIn("Return the JSON emitted by the neutral core", command_doc)
        self.assertIn("do not add adapter-side close/comment behavior", command_doc)
        self.assertIn("Remote Linear revalidation is **disabled in Fase 1**", command_doc)


class AdapterAndBootstrapContractTests(unittest.TestCase):
    def test_command_wrappers_remain_core_driven_when_helper_is_absent(self):
        for path in sorted(COMMAND_DIR.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            self.assertIn("./.ai/workflows/sdd-linear/", content)
            self.assertIn("Optional helper", content)
            self.assertIn("absent", content)
            self.assertIn("continue", content)
            self.assertIn("reduced assistance", content)

    def test_helper_skill_declares_optional_non_blocking_behavior(self):
        content = HELPER_SKILL.read_text(encoding="utf-8")

        self.assertIn("This skill is OPTIONAL", content)
        self.assertIn("MUST still work through the neutral core", content)
        self.assertIn("Never redefine workflow rules", content)
        self.assertIn("Save to Engram first", content)

    def test_bootstrap_first_run_and_rerun_are_idempotent(self):
        with tempfile.TemporaryDirectory() as tempdir:
            target = Path(tempdir) / "target"

            first = subprocess.run(
                [str(BOOTSTRAP_SCRIPT), str(target), "--yes"],
                check=True,
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
            )
            second = subprocess.run(
                [str(BOOTSTRAP_SCRIPT), str(target), "--yes"],
                check=True,
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
            )

            first_output = first.stdout
            second_output = second.stdout

            self.assertRegex(first_output, r"created:\s+14")
            self.assertRegex(first_output, r"updated:\s+0")
            self.assertRegex(first_output, r"skipped:\s+0")
            self.assertIn("Configure Linear and Engram credentials outside the repo", first_output)
            self.assertTrue((target / ".ai/workflows/sdd-linear/bin/sdd_linear_core.py").exists())
            self.assertTrue((target / ".atl/skills/sdd-linear-flow/SKILL.md").exists())

            self.assertRegex(second_output, r"created:\s+0")
            self.assertRegex(second_output, r"updated:\s+0")
            self.assertRegex(second_output, r"skipped:\s+14")
            self.assertIn("SDD Linear bootstrap summary", second_output)


if __name__ == "__main__":
    unittest.main()

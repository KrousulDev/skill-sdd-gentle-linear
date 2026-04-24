import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


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


class FailingStatusAdapter:
    def sync_status(self, **kwargs):
        raise CORE_MODULE.RuntimeAdapterError("Linear API timeout", code="NETWORK", retryable=True)

    def log_issue(self, **kwargs):
        raise NotImplementedError

    def archive(self, **kwargs):
        raise NotImplementedError


def archive_live_handler(**kwargs):
    outcomes = []
    if kwargs.get("comment_allowed"):
        outcomes.append(
            {
                "system": "linear",
                "action_type": "comment",
                "target_id": kwargs.get("linear_issue_id"),
                "status": "success",
                "remote_id": kwargs.get("linear_issue_id"),
                "error_message": "Live comment acknowledged by injected handler.",
            }
        )
    if kwargs.get("close_allowed"):
        outcomes.append(
            {
                "system": "linear",
                "action_type": "close",
                "target_id": kwargs.get("linear_issue_id"),
                "status": "success",
                "remote_id": kwargs.get("linear_issue_id"),
                "error_message": "Live close acknowledged by injected handler.",
            }
        )
    return outcomes


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
        runtime_outcome_schema = load_json(CORE_ROOT / "contracts/runtime-outcome.schema.json")
        runtime_preflight_schema = load_json(CORE_ROOT / "contracts/runtime-preflight.schema.json")

        self.assertEqual(
            change_schema["required"],
            ["version", "changeId", "linear", "workflow", "archive", "derivedIssues", "unresolved"],
        )
        self.assertEqual(change_schema["properties"]["derivedIssues"]["items"]["$ref"], "./derived-issue.schema.json")
        self.assertEqual(derived_schema["properties"]["retry"]["properties"]["max"]["const"], 3)
        self.assertEqual(
            derived_schema["properties"]["status"]["enum"],
            ["logged", "synced", "reconciliation-required", "manual-pending"],
        )
        self.assertEqual(derived_schema["properties"]["reconciliationRequired"]["type"], "boolean")
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
        self.assertEqual(change_schema["properties"]["runtime"]["properties"]["mode"]["enum"], ["stub", "live"])
        self.assertEqual(
            runtime_outcome_schema["properties"]["error"]["properties"]["code"]["enum"],
            ["PRECHECK_FAILED", "AUTH", "NETWORK", "VALIDATION", "REMOTE", "UNKNOWN", None],
        )
        self.assertEqual(runtime_preflight_schema["properties"]["status"]["enum"], ["pass", "fail"])

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
        self.assertEqual(metadata["runtime"], {"mode": "stub", "preflight": None})
        self.assertEqual(metadata["adapterOutcomes"]["statusSync"], [])
        self.assertEqual(metadata["archive"]["gate"]["status"], "blocked")
        self.assertEqual(metadata["derivedIssues"], [])

    def test_create_change_accepts_explicit_runtime_mode_and_returns_it(self):
        result = self.core.create_change(
            make_args(
                change_id="runtime-explicit",
                linear_issue_id="LIN-123",
                linear_feature_id="PROJ-7",
                title="Runtime Explicit",
                change_type="change",
                sdd_state="draft",
                runtime_mode="live",
            )
        )
        metadata = self.metadata("runtime-explicit")

        self.assertEqual(result["runtime"], {"mode": "live", "preflight": None})
        self.assertEqual(metadata["runtime"], {"mode": "live", "preflight": None})

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
        self.assertEqual(result["runtime"]["mode"], "stub")
        self.assertEqual(metadata["adapterOutcomes"]["statusSync"][0]["requestedAction"]["type"], "update_state")
        self.assertEqual(metadata["adapterOutcomes"]["statusSync"][0]["observedResult"]["status"], "success")

    def test_status_rejects_unknown_runtime_mode_before_dispatch(self):
        self.create_change()

        with self.assertRaises(CORE_MODULE.CoreError) as error:
            self.core.status(make_args(change_id="linear-integration", sdd_state="apply", runtime_mode="chaos"))

        self.assertIn("Unsupported runtime mode 'chaos'", str(error.exception))

    def test_status_records_normalized_failure_outcome_when_adapter_errors(self):
        self.create_change()
        self.core.adapter_factories["stub"] = lambda: FailingStatusAdapter()

        result = self.core.status(make_args(change_id="linear-integration", sdd_state="apply", runtime_mode="stub"))
        metadata = self.metadata()

        self.assertEqual(result["status"], "adapter-error")
        self.assertTrue(result["retryable"])
        self.assertEqual(metadata["adapterOutcomes"]["statusSync"][0]["error"]["code"], "NETWORK")
        self.assertEqual(metadata["adapterOutcomes"]["statusSync"][0]["observedResult"]["status"], "failed")

    def test_status_live_preflight_failure_persists_blocked_outcome_and_diagnostics(self):
        self.create_change()

        with mock.patch.dict("os.environ", {"LINEAR_API_KEY": "", "ENGRAM_API_KEY": ""}, clear=False):
            result = self.core.status(make_args(change_id="linear-integration", sdd_state="apply", runtime_mode="live"))

        metadata = self.metadata()
        self.assertEqual(result["status"], "preflight-failed")
        self.assertEqual(result["runtime"]["preflight"]["status"], "fail")
        self.assertFalse(result["runtime"]["preflight"]["allowSideEffects"])
        self.assertEqual(metadata["adapterOutcomes"]["statusSync"][0]["observedResult"]["status"], "blocked")
        self.assertEqual(metadata["adapterOutcomes"]["statusSync"][0]["error"]["code"], "PRECHECK_FAILED")
        self.assertIn("credentials", metadata["adapterOutcomes"]["statusSync"][0]["error"]["message"])

    def test_load_metadata_backfills_runtime_defaults_for_legacy_phase1_files(self):
        result = self.create_change()
        legacy_path = self.core.metadata_path(result["changeId"])
        legacy_metadata = load_json(legacy_path)
        legacy_metadata.pop("runtime")
        legacy_metadata.pop("adapterOutcomes")
        legacy_path.write_text(json.dumps(legacy_metadata, indent=2) + "\n", encoding="utf-8")

        _, loaded = self.core.load_metadata(result["changeId"])

        self.assertEqual(loaded["runtime"], {"mode": "stub", "preflight": None})
        self.assertEqual(loaded["adapterOutcomes"]["archive"], {"gateResult": None, "outcomes": []})

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
        self.assertEqual(result["runtime"]["mode"], "stub")
        self.assertEqual(derived_issue["retry"], {"attempted": 2, "max": 3})
        self.assertEqual(derived_issue["linearIssueId"], "LIN-456")
        self.assertFalse(derived_issue["manualFallback"]["required"])
        self.assertIsNone(derived_issue["manualFallback"]["payload"])
        self.assertEqual(
            [outcome["system"] for outcome in result["adapterOutcomes"]["logIssue"]],
            ["engram", "linear"],
        )
        self.assertEqual(result["adapterOutcomes"]["logIssue"][1]["observedResult"]["status"], "success")

    def test_log_issue_records_partial_success_outcomes_when_linear_retry_is_still_needed(self):
        self.create_change()

        result = self.core.log_issue(
            make_args(
                change_id="linear-integration",
                title="Follow-up bug",
                summary="Engram is canonical but Linear still needs retry",
                impact="Medium",
                blocking=False,
                engram_observation_id=41,
                linear_issue_id=None,
                attempt_error=["Linear create attempt 1 failed"],
                proposed_linear_state="Backlog",
                evidence_link=["https://example.com/log"],
                operator_notes="Retry later.",
                runtime_mode="stub",
            )
        )

        metadata = self.metadata()

        self.assertEqual(result["status"], "logged")
        self.assertEqual(result["runtime"]["mode"], "stub")
        self.assertEqual(
            [outcome["system"] for outcome in result["adapterOutcomes"]["logIssue"]],
            ["engram", "linear"],
        )
        self.assertEqual(result["adapterOutcomes"]["logIssue"][0]["observedResult"]["status"], "success")
        self.assertEqual(result["adapterOutcomes"]["logIssue"][1]["observedResult"]["status"], "failed")
        self.assertEqual(result["adapterOutcomes"]["logIssue"][1]["error"]["code"], "REMOTE")
        self.assertTrue(result["adapterOutcomes"]["logIssue"][1]["error"]["retryable"])
        self.assertEqual(metadata["adapterOutcomes"]["logIssue"], result["adapterOutcomes"]["logIssue"])
        self.assertFalse(result["operatorGuidance"]["reconciliationRequired"])
        self.assertEqual(result["operatorGuidance"]["canonicalRecord"], {"system": "engram", "observationId": 41})
        self.assertEqual(result["operatorGuidance"]["remainingLinearAttempts"], 2)
        self.assertIn("Reuse engramObservationId 41", result["operatorGuidance"]["nextSteps"][0])

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
        self.assertFalse(result["adapterOutcomes"]["logIssue"][1]["error"]["retryable"])

    def test_log_issue_marks_reconciliation_required_when_linear_succeeds_but_engram_follow_up_fails(self):
        self.create_change()

        result = self.core.log_issue(
            make_args(
                change_id="linear-integration",
                title="Follow-up bug",
                summary="Linear exists but Engram linkage still needs repair",
                impact="Medium",
                blocking=False,
                engram_observation_id=41,
                linear_issue_id="LIN-456",
                attempt_error=[],
                proposed_linear_state="Backlog",
                evidence_link=["https://example.com/log"],
                operator_notes="Repair Engram linkage only.",
                runtime_mode="stub",
                engram_linkage_failed=True,
                engram_linkage_error="Engram linkage update failed after Linear creation.",
            )
        )

        metadata = self.metadata()
        derived_issue = result["derivedIssue"]

        self.assertEqual(result["status"], "reconciliation-required")
        self.assertTrue(derived_issue["reconciliationRequired"])
        self.assertEqual(derived_issue["linearIssueId"], "LIN-456")
        self.assertEqual(derived_issue["engramObservationId"], 41)
        self.assertEqual(
            [outcome["system"] for outcome in result["adapterOutcomes"]["logIssue"]],
            ["engram", "linear"],
        )
        self.assertEqual(result["adapterOutcomes"]["logIssue"][0]["observedResult"]["status"], "failed")
        self.assertEqual(result["adapterOutcomes"]["logIssue"][0]["error"]["code"], "REMOTE")
        self.assertEqual(result["adapterOutcomes"]["logIssue"][0]["observedResult"]["remoteId"], "41")
        self.assertEqual(result["adapterOutcomes"]["logIssue"][1]["observedResult"]["status"], "success")
        self.assertEqual(metadata["adapterOutcomes"]["logIssue"], result["adapterOutcomes"]["logIssue"])
        self.assertEqual(metadata["derivedIssues"][-1]["status"], "reconciliation-required")
        self.assertTrue(result["operatorGuidance"]["reconciliationRequired"])
        self.assertEqual(result["operatorGuidance"]["linkedLinearIssueId"], "LIN-456")
        self.assertIn("Do NOT create another Linear issue", result["operatorGuidance"]["nextSteps"][1])

    def test_log_issue_contract_documents_caller_owned_sync_boundary(self):
        command_doc = (COMMAND_DIR / "sdd-log-issue.md").read_text(encoding="utf-8")

        self.assertIn("Save the finding to Engram first and capture `engramObservationId`", command_doc)
        self.assertIn("Accept optional sync outcome data", command_doc)
        self.assertIn("Return the JSON emitted by the neutral core unchanged", command_doc)
        self.assertIn("ALLOW_SDD_LINEAR_LIVE", command_doc)
        self.assertIn("retry guidance", command_doc)

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
        self.assertEqual(result["runtime"]["mode"], "stub")
        self.assertEqual(archive["gate"]["missing"], [])
        self.assertTrue(archive["comment"]["commentAllowed"])
        self.assertTrue(archive["comment"]["closeAllowed"])
        self.assertIn("https://github.com/example/repo/pull/1", archive["comment"]["body"])
        self.assertIn("Ready to close.", archive["comment"]["body"])
        self.assertEqual(result["adapterOutcomes"]["archive"]["gateResult"], "pass")
        self.assertEqual(
            [outcome["requestedAction"]["type"] for outcome in result["adapterOutcomes"]["archive"]["outcomes"]],
            ["comment", "close"],
        )
        self.assertTrue(
            all(outcome["observedResult"]["status"] == "success" for outcome in result["adapterOutcomes"]["archive"]["outcomes"])
        )

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
        self.assertEqual(result["adapterOutcomes"]["archive"]["gateResult"], "blocked")
        self.assertEqual(len(result["adapterOutcomes"]["archive"]["outcomes"]), 1)
        self.assertEqual(result["adapterOutcomes"]["archive"]["outcomes"][0]["observedResult"]["status"], "blocked")
        self.assertEqual(result["adapterOutcomes"]["archive"]["outcomes"][0]["error"]["code"], "PRECHECK_FAILED")

    def test_archive_live_mode_blocks_close_via_smoke_policy_but_keeps_comment_path(self):
        self.create_change()
        self.core.adapter_factories["live"] = lambda: CORE_MODULE.build_live_runtime_adapter(
            handlers={"archive": archive_live_handler}
        )

        with mock.patch.dict(
            "os.environ",
            {"LINEAR_API_KEY": "linear-token", "ENGRAM_API_KEY": "engram-token"},
            clear=False,
        ):
            result = self.core.archive(
                make_args(
                    change_id="linear-integration",
                    pr_url="https://github.com/example/repo/pull/1",
                    merge_confirmed=True,
                    qa_notes="QA sign-off captured.",
                    business_validation="PM approved release.",
                    archive_summary="Ready to close.",
                    follow_up_notes="Keep comment only in live smoke mode.",
                    runtime_mode="live",
                )
            )

        metadata = self.metadata()
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["runtime"]["preflight"]["status"], "pass")
        self.assertTrue(result["archive"]["comment"]["commentAllowed"])
        self.assertFalse(result["archive"]["comment"]["closeAllowed"])
        self.assertEqual(
            [outcome["requestedAction"]["type"] for outcome in result["adapterOutcomes"]["archive"]["outcomes"]],
            ["comment", "close"],
        )
        self.assertEqual(result["adapterOutcomes"]["archive"]["outcomes"][0]["observedResult"]["status"], "success")
        self.assertEqual(result["adapterOutcomes"]["archive"]["outcomes"][1]["observedResult"]["status"], "blocked")
        self.assertEqual(result["adapterOutcomes"]["archive"]["outcomes"][1]["error"]["code"], "PRECHECK_FAILED")
        self.assertEqual(metadata["adapterOutcomes"]["archive"], result["adapterOutcomes"]["archive"])

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

    def test_command_wrappers_document_runtime_passthrough_and_live_confirmation(self):
        for path in sorted(COMMAND_DIR.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            self.assertIn("runtimeMode", content)
            self.assertIn("--runtime-mode \"<stub|live>\"", content)
            self.assertIn("ALLOW_SDD_LINEAR_LIVE", content)

    def test_helper_skill_declares_optional_non_blocking_behavior(self):
        content = HELPER_SKILL.read_text(encoding="utf-8")

        self.assertIn("This skill is OPTIONAL", content)
        self.assertIn("MUST still work through the neutral core", content)
        self.assertIn("Never redefine workflow rules", content)
        self.assertIn("Save to Engram first", content)
        self.assertIn("ALLOW_SDD_LINEAR_LIVE", content)
        self.assertIn("reconciliation guidance", content)

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

            self.assertRegex(first_output, r"created:\s+22")
            self.assertRegex(first_output, r"updated:\s+0")
            self.assertRegex(first_output, r"skipped:\s+0")
            self.assertIn("Configure Linear and Engram credentials outside the repo", first_output)
            self.assertTrue((target / ".ai/workflows/sdd-linear/bin/sdd_linear_core.py").exists())
            self.assertTrue((target / ".atl/skills/sdd-linear-flow/SKILL.md").exists())
            self.assertTrue((target / ".ai/workflows/sdd-linear/runtime/adapters/live.py").exists())

            self.assertRegex(second_output, r"created:\s+0")
            self.assertRegex(second_output, r"updated:\s+0")
            self.assertRegex(second_output, r"skipped:\s+22")
            self.assertIn("SDD Linear bootstrap summary", second_output)


if __name__ == "__main__":
    unittest.main()

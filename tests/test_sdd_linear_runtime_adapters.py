import importlib.util
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = REPO_ROOT / ".ai/workflows/sdd-linear"
CORE_MODULE_PATH = CORE_ROOT / "bin/sdd_linear_core.py"
PREFLIGHT_MODULE_PATH = CORE_ROOT / "runtime/preflight.py"
LIVE_MODULE_PATH = CORE_ROOT / "runtime/adapters/live.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CORE_MODULE = load_module("sdd_linear_core_runtime_tests", CORE_MODULE_PATH)
PREFLIGHT_MODULE = load_module("sdd_linear_preflight_tests", PREFLIGHT_MODULE_PATH)
LIVE_MODULE = load_module("sdd_linear_live_adapter_tests", LIVE_MODULE_PATH)


def copy_core_to_temp(destination: Path) -> Path:
    target = destination / ".ai/workflows/sdd-linear"
    shutil.copytree(CORE_ROOT, target)
    return target


def make_args(**kwargs):
    return types.SimpleNamespace(**kwargs)


class PreflightEvaluatorTests(unittest.TestCase):
    def test_missing_credentials_fail_preflight(self):
        result = PREFLIGHT_MODULE.evaluate_live_preflight(
            runtime_config=CORE_MODULE.load_json(CORE_ROOT / "config.json")["runtime"],
            actions=[{"system": "linear", "action_type": "update_state", "target_id": "LIN-123"}],
            linear_issue_id="LIN-123",
            env={"LINEAR_API_KEY": ""},
        ).to_dict()

        self.assertEqual(result["status"], "fail")
        self.assertFalse(result["allowSideEffects"])
        self.assertEqual(result["checks"][0]["name"], "credentials")

    def test_close_scope_respects_smoke_policy(self):
        check = PREFLIGHT_MODULE.evaluate_target_scope(
            actions=[{"system": "linear", "action_type": "close", "target_id": "LIN-123"}],
            smoke_policy={"allowClose": False, "allowedLinearProjects": []},
            linear_issue_id="LIN-123",
            linear_feature_id="PROJ-7",
        ).to_dict()

        self.assertEqual(check["status"], "fail")
        self.assertIn("allowClose", check["detail"])

    def test_update_scope_passes_with_credentials_and_probe(self):
        result = PREFLIGHT_MODULE.evaluate_live_preflight(
            runtime_config=CORE_MODULE.load_json(CORE_ROOT / "config.json")["runtime"],
            actions=[{"system": "linear", "action_type": "update_state", "target_id": "LIN-123"}],
            linear_issue_id="LIN-123",
            env={"LINEAR_API_KEY": "linear-token"},
            connectivity_probe=lambda context: (True, f"Probe OK for {context['linear_issue_id']}"),
        ).to_dict()

        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["allowSideEffects"])
        self.assertEqual(result["checks"][1]["status"], "pass")


class LiveAdapterUnitTests(unittest.TestCase):
    def test_handler_dicts_are_normalized_into_runtime_outcomes(self):
        adapter = LIVE_MODULE.build_live_runtime_adapter(
            handlers={
                "sync_status": lambda **kwargs: [
                    {
                        "system": "linear",
                        "action_type": "update_state",
                        "target_id": kwargs["linear_issue_id"],
                        "status": "success",
                        "remote_id": kwargs["linear_issue_id"],
                        "error_message": "normalized",
                    }
                ]
            }
        )

        outcomes = adapter.sync_status(change_id="change-1", linear_issue_id="LIN-123", mapped_linear_state="Done")

        self.assertEqual(outcomes[0].requestedAction.type, "update_state")
        self.assertEqual(outcomes[0].observedResult.status, "success")

    def test_handler_exceptions_are_normalized(self):
        adapter = LIVE_MODULE.build_live_runtime_adapter(
            handlers={"sync_status": lambda **kwargs: (_ for _ in ()).throw(ConnectionError("api down"))}
        )

        with self.assertRaises(CORE_MODULE.RuntimeAdapterError) as error:
            adapter.sync_status(change_id="change-1", linear_issue_id="LIN-123", mapped_linear_state="Done")

        self.assertEqual(error.exception.code, "NETWORK")
        self.assertTrue(error.exception.retryable)

    def test_unconfigured_live_operation_fails_safe(self):
        adapter = LIVE_MODULE.build_live_runtime_adapter()

        with self.assertRaises(CORE_MODULE.RuntimeAdapterError) as error:
            adapter.archive(linear_issue_id="LIN-123")

        self.assertEqual(error.exception.code, "REMOTE")
        self.assertFalse(error.exception.retryable)


class WorkflowLiveDispatcherIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.tempdir.name)
        self.temp_core_root = copy_core_to_temp(self.temp_path)
        self.core = CORE_MODULE.WorkflowCore(self.temp_core_root)
        self.core.create_change(
            make_args(
                change_id="runtime-live",
                linear_issue_id="LIN-123",
                linear_feature_id="PROJ-7",
                title="Runtime Live",
                change_type="change",
                sdd_state="draft",
            )
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_workflow_dispatches_live_status_when_preflight_passes(self):
        self.core.adapter_factories["live"] = lambda: LIVE_MODULE.build_live_runtime_adapter(
            handlers={
                "sync_status": lambda **kwargs: [
                    {
                        "system": "linear",
                        "action_type": "update_state",
                        "target_id": kwargs["linear_issue_id"],
                        "status": "success",
                        "remote_id": kwargs["linear_issue_id"],
                    }
                ]
            }
        )

        with mock.patch.dict(os.environ, {"LINEAR_API_KEY": "linear-token"}, clear=False):
            result = self.core.status(make_args(change_id="runtime-live", sdd_state="apply", runtime_mode="live"))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["runtime"]["mode"], "live")
        self.assertEqual(result["runtime"]["preflight"]["status"], "pass")
        self.assertEqual(result["adapterOutcomes"]["statusSync"][0]["observedResult"]["status"], "success")


if __name__ == "__main__":
    unittest.main()

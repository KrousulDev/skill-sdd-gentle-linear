#!/usr/bin/env python3
"""Neutral core behaviors for SDD + Linear Fase 1."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


WORKFLOW_ROOT = Path(__file__).resolve().parent.parent
if str(WORKFLOW_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKFLOW_ROOT))

from runtime.adapters.live import build_live_runtime_adapter
from runtime.adapters.stub import StubRuntimeAdapter
from runtime.preflight import evaluate_live_preflight, evaluate_target_scope
from runtime.ports import RuntimeAdapterError, make_outcome


FIELD_ORDER = [
    "parentLinearIssueId",
    "parentLinearFeatureId",
    "title",
    "summary",
    "impact",
    "blocking",
    "proposedLinearState",
    "sourceChangeId",
    "engramObservationId",
    "evidenceLinks",
    "operatorNotes",
]


class CoreError(Exception):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"Expected boolean value, received: {value}")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def render_template(template: str, values: dict) -> str:
    rendered = template
    for key, raw_value in values.items():
        if isinstance(raw_value, bool):
            replacement = "true" if raw_value else "false"
        elif raw_value is None:
            replacement = ""
        elif isinstance(raw_value, list):
            replacement = ", ".join(str(item) for item in raw_value)
        else:
            replacement = str(raw_value)
        rendered = rendered.replace(f"{{{{{key}}}}}", replacement)
    return rendered


class WorkflowCore:
    def __init__(self, root: Path):
        self.root = root
        self.config = load_json(root / "config.json")
        self.state_map = load_json(root / self.config["statusSync"]["mappingFile"])
        self.adapter_factories = {
            "stub": lambda: StubRuntimeAdapter(),
            "live": lambda: build_live_runtime_adapter(),
        }

    def metadata_path(self, change_id: str) -> Path:
        pattern = self.config["metadata"]["filePattern"]
        relative = pattern.replace("{change}", change_id)
        return self.root / self.config["metadata"]["root"] / relative

    def map_state(self, sdd_state: str) -> str:
        mapped = self.state_map["mapping"].get(sdd_state)
        if mapped is None:
            raise CoreError(
                f"Unmapped SDD state '{sdd_state}'. Update {self.root / self.config['statusSync']['mappingFile']} first."
            )
        return mapped

    def empty_archive(self, change_id: str) -> dict:
        missing = deepcopy(self.config["archive"]["requiredEvidence"])
        return {
            "evidence": {
                "prUrl": None,
                "mergeConfirmed": None,
                "qaNotes": None,
                "businessValidation": None,
            },
            "gate": {
                "status": "blocked",
                "missing": missing,
                "evaluatedAt": utc_now(),
                "remoteRevalidationMode": self.config["archive"]["remoteRevalidation"]["mode"],
            },
            "comment": {
                "template": self.config["archive"]["commentTemplate"],
                "body": None,
                "renderedAt": None,
                "commentAllowed": False,
                "closeAllowed": False,
            },
        }

    def load_metadata(self, change_id: str) -> tuple[Path, dict]:
        path = self.metadata_path(change_id)
        if not path.exists():
            raise CoreError(f"Change metadata not found for '{change_id}' at {path}")
        return path, self.ensure_runtime_defaults(load_json(path))

    def default_runtime_mode(self) -> str:
        return self.config["runtime"]["mode"]

    def resolve_runtime_mode(self, requested_mode: str | None) -> str:
        mode = requested_mode or self.default_runtime_mode()
        allowed_modes = self.config["runtime"]["allowedModes"]
        if mode not in allowed_modes:
            raise CoreError(f"Unsupported runtime mode '{mode}'. Allowed modes: {', '.join(allowed_modes)}")
        return mode

    def empty_adapter_outcomes(self) -> dict:
        return {
            "statusSync": [],
            "logIssue": [],
            "archive": {
                "gateResult": None,
                "outcomes": [],
            },
        }

    def ensure_runtime_defaults(self, metadata: dict) -> dict:
        metadata.setdefault(
            "runtime",
            {
                "mode": self.default_runtime_mode(),
                "preflight": None,
            },
        )
        metadata.setdefault("adapterOutcomes", self.empty_adapter_outcomes())
        metadata["runtime"].setdefault("mode", self.default_runtime_mode())
        metadata["runtime"].setdefault("preflight", None)
        metadata["adapterOutcomes"].setdefault("statusSync", [])
        metadata["adapterOutcomes"].setdefault("logIssue", [])
        metadata["adapterOutcomes"].setdefault("archive", {"gateResult": None, "outcomes": []})
        metadata["adapterOutcomes"]["archive"].setdefault("gateResult", None)
        metadata["adapterOutcomes"]["archive"].setdefault("outcomes", [])
        return metadata

    def runtime_adapter(self, mode: str):
        factory = self.adapter_factories.get(mode)
        if factory is None:
            raise CoreError(f"Runtime mode '{mode}' is recognized but not yet implemented in this core batch.")
        return factory()

    def planned_action(self, *, system: str, action_type: str, target_id: str | None) -> dict:
        return {
            "system": system,
            "action_type": action_type,
            "target_id": target_id,
        }

    def blocked_outcomes(self, *, actions: list[dict], message: str) -> list[dict]:
        return [
            self.normalize_adapter_failure(
                system=action["system"],
                action_type=action["action_type"],
                target_id=action["target_id"],
                message=message,
                code="PRECHECK_FAILED",
                retryable=False,
                status="blocked",
            )
            for action in actions
        ]

    def preflight_block_message(self, preflight: dict) -> str:
        failing_checks = [
            f"{check['name']}: {check['detail']}"
            for check in preflight.get("checks", [])
            if check.get("status") == "fail"
        ]
        if not failing_checks:
            return "Live runtime preflight blocked side effects."
        return "Live runtime preflight blocked side effects: " + " | ".join(failing_checks)

    def evaluate_live_preflight(self, *, actions: list[dict], metadata: dict) -> dict:
        return evaluate_live_preflight(
            runtime_config=self.config["runtime"],
            actions=actions,
            linear_issue_id=metadata["linear"].get("issueId"),
            linear_feature_id=metadata["linear"].get("featureId"),
        ).to_dict()

    def live_close_scope_check(self, *, metadata: dict) -> dict:
        return evaluate_target_scope(
            actions=[self.planned_action(system="linear", action_type="close", target_id=metadata["linear"].get("issueId"))],
            smoke_policy=self.config["runtime"]["live"]["smokePolicy"],
            linear_issue_id=metadata["linear"].get("issueId"),
            linear_feature_id=metadata["linear"].get("featureId"),
        ).to_dict()

    def normalize_status_failure(self, *, linear_issue_id: str, message: str, code: str, retryable: bool | None) -> dict:
        return make_outcome(
            system="linear",
            action_type="update_state",
            target_id=linear_issue_id,
            status="failed",
            remote_id=None,
            error_code=code,
            error_message=message,
            retryable=retryable,
        ).to_dict()

    def normalize_adapter_failure(
        self,
        *,
        system: str,
        action_type: str,
        target_id: str | None,
        message: str,
        code: str,
        retryable: bool | None,
        status: str = "failed",
    ) -> dict:
        return make_outcome(
            system=system,
            action_type=action_type,
            target_id=target_id,
            status=status,
            remote_id=None,
            error_code=code,
            error_message=message,
            retryable=retryable,
        ).to_dict()

    def create_change(self, args: argparse.Namespace) -> dict:
        if not args.linear_issue_id:
            raise CoreError("linearIssueId is required. Re-run /sdd-new with --linear-issue-id LIN-123.")

        target = self.metadata_path(args.change_id)
        if target.exists():
            raise CoreError(f"Change metadata already exists for '{args.change_id}' at {target}")

        sdd_state = args.sdd_state or "draft"
        runtime_mode = self.resolve_runtime_mode(getattr(args, "runtime_mode", None))
        metadata = {
            "version": self.config["version"],
            "changeId": args.change_id,
            "title": args.title or args.change_id,
            "type": args.change_type or "change",
            "linear": {
                "issueId": args.linear_issue_id,
                "featureId": args.linear_feature_id,
                "originIssueId": None,
            },
            "workflow": {
                "sddState": sdd_state,
                "mappedLinearState": self.map_state(sdd_state),
            },
            "runtime": {
                "mode": runtime_mode,
                "preflight": None,
            },
            "adapterOutcomes": self.empty_adapter_outcomes(),
            "archive": self.empty_archive(args.change_id),
            "derivedIssues": [],
            "unresolved": [],
        }
        save_json(target, metadata)
        return {
            "status": "created",
            "changeId": args.change_id,
            "metadataPath": str(target.relative_to(self.root)),
            "workflow": metadata["workflow"],
            "linear": metadata["linear"],
            "runtime": metadata["runtime"],
        }

    def reconciliation_guidance(
        self,
        *,
        engram_observation_id: int,
        attempted: int,
        max_attempts: int,
    ) -> dict:
        remaining_attempts = max_attempts - attempted
        return {
            "reconciliationRequired": False,
            "canonicalRecord": {
                "system": "engram",
                "observationId": engram_observation_id,
            },
            "remainingLinearAttempts": remaining_attempts,
            "message": (
                "Engram is the canonical record for this derived issue. Retry Linear creation "
                "without creating a duplicate Engram observation."
            ),
            "nextSteps": [
                f"Reuse engramObservationId {engram_observation_id} on the next /sdd-log-issue retry.",
                "If the retry fails again, append the new error with --attempt-error so the retry budget stays accurate.",
                "Escalate to the manual fallback only after the final Linear retry is exhausted.",
            ],
        }

    def engram_linkage_guidance(
        self,
        *,
        engram_observation_id: int,
        linear_issue_id: str,
        error_message: str | None,
    ) -> dict:
        return {
            "reconciliationRequired": True,
            "canonicalRecord": {
                "system": "engram",
                "observationId": engram_observation_id,
            },
            "linkedLinearIssueId": linear_issue_id,
            "message": (
                "Linear issue creation succeeded, but the Engram follow-up update failed. "
                "Reconcile the existing Engram observation instead of creating another Linear issue."
            ),
            "error": error_message,
            "nextSteps": [
                f"Update Engram observation {engram_observation_id} to reference Linear issue {linear_issue_id}.",
                "Do NOT create another Linear issue during reconciliation.",
                "Record the linkage fix in the existing derived-issue trail once Engram is updated.",
            ],
        }

    def status(self, args: argparse.Namespace) -> dict:
        path, metadata = self.load_metadata(args.change_id)
        sdd_state = args.sdd_state or metadata["workflow"]["sddState"]
        mapped = self.map_state(sdd_state)
        runtime_mode = self.resolve_runtime_mode(getattr(args, "runtime_mode", None))
        metadata["workflow"] = {
            "sddState": sdd_state,
            "mappedLinearState": mapped,
        }
        metadata["runtime"]["mode"] = runtime_mode
        metadata["runtime"]["preflight"] = None
        planned_actions = [
            self.planned_action(system="linear", action_type="update_state", target_id=metadata["linear"]["issueId"])
        ]
        if runtime_mode == "live":
            preflight = self.evaluate_live_preflight(actions=planned_actions, metadata=metadata)
            metadata["runtime"]["preflight"] = preflight
            if not preflight["allowSideEffects"]:
                outcomes = self.blocked_outcomes(
                    actions=planned_actions,
                    message=self.preflight_block_message(preflight),
                )
                metadata["adapterOutcomes"]["statusSync"] = outcomes
                save_json(path, metadata)
                return {
                    "status": "preflight-failed",
                    "changeId": args.change_id,
                    "metadataPath": str(path.relative_to(self.root)),
                    "workflow": metadata["workflow"],
                    "linear": metadata["linear"],
                    "runtime": metadata["runtime"],
                    "adapterOutcomes": {
                        "statusSync": metadata["adapterOutcomes"]["statusSync"],
                    },
                    "retryable": False,
                }
        adapter = self.runtime_adapter(runtime_mode)
        try:
            outcomes = [outcome.to_dict() for outcome in adapter.sync_status(
                change_id=args.change_id,
                linear_issue_id=metadata["linear"]["issueId"],
                mapped_linear_state=mapped,
            )]
            result_status = "ok"
            retryable = None
        except RuntimeAdapterError as error:
            outcomes = [
                self.normalize_status_failure(
                    linear_issue_id=metadata["linear"]["issueId"],
                    message=str(error),
                    code=error.code,
                    retryable=error.retryable,
                )
            ]
            result_status = "adapter-error"
            retryable = error.retryable

        metadata["adapterOutcomes"]["statusSync"] = outcomes
        save_json(path, metadata)
        result = {
            "status": result_status,
            "changeId": args.change_id,
            "metadataPath": str(path.relative_to(self.root)),
            "workflow": metadata["workflow"],
            "linear": metadata["linear"],
            "runtime": metadata["runtime"],
            "adapterOutcomes": {
                "statusSync": metadata["adapterOutcomes"]["statusSync"],
            },
        }
        if retryable is not None:
            result["retryable"] = retryable
        return result

    def log_issue(self, args: argparse.Namespace) -> dict:
        path, metadata = self.load_metadata(args.change_id)
        if args.engram_observation_id <= 0:
            raise CoreError("engramObservationId must be a positive integer. Save to Engram before logging to Linear.")

        engram_linkage_failed = bool(getattr(args, "engram_linkage_failed", False))
        engram_linkage_error = getattr(args, "engram_linkage_error", None)
        if engram_linkage_failed and not args.linear_issue_id:
            raise CoreError(
                "engramLinkageFailed requires linearIssueId because reconciliation applies only after Linear creation succeeds."
            )

        runtime_mode = self.resolve_runtime_mode(getattr(args, "runtime_mode", None))
        metadata["runtime"]["mode"] = runtime_mode
        metadata["runtime"]["preflight"] = None
        planned_actions = [
            self.planned_action(
                system="engram",
                action_type="save_observation",
                target_id=str(args.engram_observation_id),
            ),
            self.planned_action(
                system="linear",
                action_type="create_issue",
                target_id=metadata["linear"]["issueId"],
            ),
        ]
        if runtime_mode == "live":
            preflight = self.evaluate_live_preflight(actions=planned_actions, metadata=metadata)
            metadata["runtime"]["preflight"] = preflight
            if not preflight["allowSideEffects"]:
                metadata["adapterOutcomes"]["logIssue"] = self.blocked_outcomes(
                    actions=planned_actions,
                    message=self.preflight_block_message(preflight),
                )
                save_json(path, metadata)
                return {
                    "status": "preflight-failed",
                    "changeId": args.change_id,
                    "metadataPath": str(path.relative_to(self.root)),
                    "runtime": metadata["runtime"],
                    "adapterOutcomes": {
                        "logIssue": metadata["adapterOutcomes"]["logIssue"],
                    },
                }
        adapter = self.runtime_adapter(runtime_mode)
        max_attempts = self.config["derivedIssue"]["retry"]["maxAttempts"]
        failure_count = len(args.attempt_error or [])
        attempted = failure_count + (1 if args.linear_issue_id else 0)
        if attempted > max_attempts or failure_count > max_attempts:
            raise CoreError(f"Retry budget exceeded. Max allowed attempts: {max_attempts}")

        proposed_linear_state = args.proposed_linear_state or self.map_state("draft")
        manual_fallback = {
            "required": False,
            "fieldOrder": FIELD_ORDER,
            "payload": None,
            "prompt": None,
        }
        status = "logged"

        if args.linear_issue_id:
            status = "synced"
        elif failure_count >= max_attempts:
            status = "manual-pending"
            payload = {
                "parentLinearIssueId": metadata["linear"]["issueId"],
                "parentLinearFeatureId": metadata["linear"].get("featureId"),
                "title": args.title,
                "summary": args.summary,
                "impact": args.impact or "Not provided",
                "blocking": args.blocking,
                "proposedLinearState": proposed_linear_state,
                "sourceChangeId": args.change_id,
                "engramObservationId": args.engram_observation_id,
                "evidenceLinks": args.evidence_link or [],
                "operatorNotes": args.operator_notes or "Linear automatic creation exhausted retry budget.",
            }
            template = (self.root / self.config["derivedIssue"]["manualFallbackTemplate"]).read_text(encoding="utf-8")
            manual_fallback = {
                "required": True,
                "fieldOrder": FIELD_ORDER,
                "payload": payload,
                "prompt": render_template(template, payload),
            }

        if engram_linkage_failed:
            status = "reconciliation-required"

        try:
            log_outcomes = [
                outcome.to_dict()
                for outcome in adapter.log_issue(
                    change_id=args.change_id,
                    title=args.title,
                    summary=args.summary,
                    impact=args.impact or "Not provided",
                    blocking=args.blocking,
                    engram_observation_id=args.engram_observation_id,
                    linear_issue_id=args.linear_issue_id,
                    parent_linear_issue_id=metadata["linear"]["issueId"],
                    parent_linear_feature_id=metadata["linear"].get("featureId"),
                    proposed_linear_state=proposed_linear_state,
                    attempt_errors=args.attempt_error or [],
                    max_attempts=max_attempts,
                    evidence_links=args.evidence_link or [],
                    operator_notes=args.operator_notes,
                    manual_fallback_required=manual_fallback["required"],
                    engram_linkage_failed=engram_linkage_failed,
                    engram_linkage_error=engram_linkage_error,
                )
            ]
        except RuntimeAdapterError as error:
            log_outcomes = [
                self.normalize_adapter_failure(
                    system="linear",
                    action_type="create_issue",
                    target_id=metadata["linear"]["issueId"],
                    message=str(error),
                    code=error.code,
                    retryable=error.retryable,
                )
            ]

        derived_issue = {
            "title": args.title,
            "summary": args.summary,
            "impact": args.impact or "Not provided",
            "blocking": args.blocking,
            "originChangeId": args.change_id,
            "originLinearIssueId": metadata["linear"]["issueId"],
            "originLinearFeatureId": metadata["linear"].get("featureId"),
            "linearIssueId": args.linear_issue_id,
            "engramObservationId": args.engram_observation_id,
            "reconciliationRequired": engram_linkage_failed,
            "retry": {
                "attempted": attempted,
                "max": max_attempts,
            },
            "status": status,
            "manualFallback": manual_fallback,
        }
        metadata["adapterOutcomes"]["logIssue"] = log_outcomes
        metadata.setdefault("derivedIssues", []).append(derived_issue)
        save_json(path, metadata)
        return {
            "status": status,
            "changeId": args.change_id,
            "metadataPath": str(path.relative_to(self.root)),
            "runtime": metadata["runtime"],
            "adapterOutcomes": {
                "logIssue": metadata["adapterOutcomes"]["logIssue"],
            },
            "derivedIssue": derived_issue,
            **(
                {
                    "operatorGuidance": self.reconciliation_guidance(
                        engram_observation_id=args.engram_observation_id,
                        attempted=attempted,
                        max_attempts=max_attempts,
                    )
                }
                if status == "logged" and not args.linear_issue_id
                else {}
            ),
            **(
                {
                    "operatorGuidance": self.engram_linkage_guidance(
                        engram_observation_id=args.engram_observation_id,
                        linear_issue_id=args.linear_issue_id,
                        error_message=engram_linkage_error,
                    )
                }
                if status == "reconciliation-required" and args.linear_issue_id
                else {}
            ),
        }

    def archive(self, args: argparse.Namespace) -> dict:
        path, metadata = self.load_metadata(args.change_id)
        runtime_mode = self.resolve_runtime_mode(getattr(args, "runtime_mode", None))
        metadata["runtime"]["mode"] = runtime_mode
        metadata["runtime"]["preflight"] = None
        evidence = deepcopy(metadata["archive"]["evidence"])
        overrides = {
            "prUrl": args.pr_url,
            "mergeConfirmed": args.merge_confirmed,
            "qaNotes": args.qa_notes,
            "businessValidation": args.business_validation,
        }
        for key, value in overrides.items():
            if value is not None:
                evidence[key] = value

        missing = []
        for field in self.config["archive"]["requiredEvidence"]:
            value = evidence.get(field)
            if field == "mergeConfirmed":
                if value is not True:
                    missing.append(field)
            elif value is None or (isinstance(value, str) and not value.strip()):
                missing.append(field)

        gate_status = "pass" if not missing else "blocked"
        gate = {
            "status": gate_status,
            "missing": missing,
            "evaluatedAt": utc_now(),
            "remoteRevalidationMode": self.config["archive"]["remoteRevalidation"]["mode"],
        }

        comment = {
            "template": self.config["archive"]["commentTemplate"],
            "body": None,
            "renderedAt": None,
            "commentAllowed": False,
            "closeAllowed": False,
        }

        if gate_status == "pass":
            template = (self.root / self.config["archive"]["commentTemplate"]).read_text(encoding="utf-8")
            body = render_template(
                template,
                {
                    "changeId": metadata["changeId"],
                    "linearIssueId": metadata["linear"]["issueId"],
                    "linearFeatureId": metadata["linear"].get("featureId"),
                    "sddState": metadata["workflow"]["sddState"],
                    "mappedLinearState": metadata["workflow"]["mappedLinearState"],
                    "prUrl": evidence["prUrl"],
                    "mergeConfirmed": evidence["mergeConfirmed"],
                    "qaNotes": evidence["qaNotes"],
                    "businessValidation": evidence["businessValidation"],
                    "archiveSummary": args.archive_summary or "Archive completed with required evidence.",
                    "followUpNotes": args.follow_up_notes or "None.",
                },
            )
            comment = {
                "template": self.config["archive"]["commentTemplate"],
                "body": body,
                "renderedAt": utc_now(),
                "commentAllowed": bool(self.config["archive"]["commentOnPass"]),
                "closeAllowed": bool(self.config["archive"]["closeIssueOnPass"]),
            }
        else:
            comment["commentAllowed"] = not bool(self.config["archive"]["blockCommentOnFailure"])
            comment["closeAllowed"] = not bool(self.config["archive"]["blockCloseOnFailure"])

        blocked_archive_outcomes = []
        requested_close = bool(comment["closeAllowed"])
        if runtime_mode == "live" and requested_close:
            close_scope_check = self.live_close_scope_check(metadata=metadata)
            if close_scope_check["status"] != "pass":
                comment["closeAllowed"] = False
                blocked_archive_outcomes = self.blocked_outcomes(
                    actions=[
                        self.planned_action(
                            system="linear",
                            action_type="close",
                            target_id=metadata["linear"]["issueId"],
                        )
                    ],
                    message=close_scope_check["detail"],
                )

        metadata["archive"] = {
            "evidence": evidence,
            "gate": gate,
            "comment": comment,
        }
        archive_actions = []
        if comment["commentAllowed"]:
            archive_actions.append(
                self.planned_action(system="linear", action_type="comment", target_id=metadata["linear"]["issueId"])
            )
        if comment["closeAllowed"]:
            archive_actions.append(
                self.planned_action(system="linear", action_type="close", target_id=metadata["linear"]["issueId"])
            )

        archive_outcomes = []
        if runtime_mode == "live" and archive_actions:
            preflight = self.evaluate_live_preflight(actions=archive_actions, metadata=metadata)
            metadata["runtime"]["preflight"] = preflight
            if not preflight["allowSideEffects"]:
                archive_outcomes = self.blocked_outcomes(
                    actions=archive_actions,
                    message=self.preflight_block_message(preflight),
                )
            else:
                adapter = self.runtime_adapter(runtime_mode)
                try:
                    archive_outcomes = [
                        outcome.to_dict()
                        for outcome in adapter.archive(
                            change_id=args.change_id,
                            linear_issue_id=metadata["linear"]["issueId"],
                            gate_status=gate_status,
                            gate_missing=missing,
                            comment_allowed=comment["commentAllowed"],
                            close_allowed=comment["closeAllowed"],
                            comment_body=comment["body"],
                        )
                    ]
                except RuntimeAdapterError as error:
                    archive_outcomes = [
                        self.normalize_adapter_failure(
                            system="linear",
                            action_type="comment",
                            target_id=metadata["linear"]["issueId"],
                            message=str(error),
                            code=error.code,
                            retryable=error.retryable,
                        )
                    ]
        else:
            adapter = self.runtime_adapter(runtime_mode)
            try:
                archive_outcomes = [
                    outcome.to_dict()
                    for outcome in adapter.archive(
                        change_id=args.change_id,
                        linear_issue_id=metadata["linear"]["issueId"],
                        gate_status=gate_status,
                        gate_missing=missing,
                        comment_allowed=comment["commentAllowed"],
                        close_allowed=comment["closeAllowed"],
                        comment_body=comment["body"],
                    )
                ]
            except RuntimeAdapterError as error:
                archive_outcomes = [
                    self.normalize_adapter_failure(
                        system="linear",
                        action_type="comment",
                        target_id=metadata["linear"]["issueId"],
                        message=str(error),
                        code=error.code,
                        retryable=error.retryable,
                    )
                ]

        if blocked_archive_outcomes:
            archive_outcomes.extend(blocked_archive_outcomes)

        metadata["adapterOutcomes"]["archive"] = {
            "gateResult": gate_status,
            "outcomes": archive_outcomes,
        }
        save_json(path, metadata)
        return {
            "status": gate_status,
            "changeId": args.change_id,
            "metadataPath": str(path.relative_to(self.root)),
            "runtime": metadata["runtime"],
            "adapterOutcomes": {
                "archive": metadata["adapterOutcomes"]["archive"],
            },
            "archive": metadata["archive"],
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SDD Linear neutral core")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Path to .ai/workflows/sdd-linear root",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser("new", help="Create change metadata")
    new_parser.add_argument("--change-id", required=True)
    new_parser.add_argument("--linear-issue-id", required=True)
    new_parser.add_argument("--linear-feature-id")
    new_parser.add_argument("--title")
    new_parser.add_argument("--change-type")
    new_parser.add_argument("--sdd-state")
    new_parser.add_argument("--runtime-mode")

    status_parser = subparsers.add_parser("status", help="Read or update mapped status")
    status_parser.add_argument("--change-id", required=True)
    status_parser.add_argument("--sdd-state")
    status_parser.add_argument("--runtime-mode")

    log_parser = subparsers.add_parser("log-issue", help="Persist derived issue result")
    log_parser.add_argument("--change-id", required=True)
    log_parser.add_argument("--title", required=True)
    log_parser.add_argument("--summary", required=True)
    log_parser.add_argument("--impact")
    log_parser.add_argument("--blocking", type=parse_bool, required=True)
    log_parser.add_argument("--engram-observation-id", type=int, required=True)
    log_parser.add_argument("--linear-issue-id")
    log_parser.add_argument("--attempt-error", action="append")
    log_parser.add_argument("--proposed-linear-state")
    log_parser.add_argument("--evidence-link", action="append")
    log_parser.add_argument("--operator-notes")
    log_parser.add_argument("--runtime-mode")
    log_parser.add_argument("--engram-linkage-failed", action="store_true")
    log_parser.add_argument("--engram-linkage-error")

    archive_parser = subparsers.add_parser("archive", help="Evaluate archive gate and render comment")
    archive_parser.add_argument("--change-id", required=True)
    archive_parser.add_argument("--pr-url")
    archive_parser.add_argument("--merge-confirmed", type=parse_bool)
    archive_parser.add_argument("--qa-notes")
    archive_parser.add_argument("--business-validation")
    archive_parser.add_argument("--archive-summary")
    archive_parser.add_argument("--follow-up-notes")
    archive_parser.add_argument("--runtime-mode")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    core = WorkflowCore(args.root)
    try:
        if args.command == "new":
            result = core.create_change(args)
        elif args.command == "status":
            result = core.status(args)
        elif args.command == "log-issue":
            result = core.log_issue(args)
        elif args.command == "archive":
            result = core.archive(args)
        else:
            raise CoreError(f"Unsupported command: {args.command}")
    except CoreError as error:
        print(json.dumps({"status": "error", "message": str(error)}, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

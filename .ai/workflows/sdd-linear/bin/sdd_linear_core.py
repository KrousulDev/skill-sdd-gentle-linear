#!/usr/bin/env python3
"""Neutral core behaviors for SDD + Linear Fase 1."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


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
        return path, load_json(path)

    def create_change(self, args: argparse.Namespace) -> dict:
        if not args.linear_issue_id:
            raise CoreError("linearIssueId is required. Re-run /sdd-new with --linear-issue-id LIN-123.")

        target = self.metadata_path(args.change_id)
        if target.exists():
            raise CoreError(f"Change metadata already exists for '{args.change_id}' at {target}")

        sdd_state = args.sdd_state or "draft"
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
        }

    def status(self, args: argparse.Namespace) -> dict:
        path, metadata = self.load_metadata(args.change_id)
        sdd_state = args.sdd_state or metadata["workflow"]["sddState"]
        mapped = self.map_state(sdd_state)
        metadata["workflow"] = {
            "sddState": sdd_state,
            "mappedLinearState": mapped,
        }
        save_json(path, metadata)
        return {
            "status": "ok",
            "changeId": args.change_id,
            "metadataPath": str(path.relative_to(self.root)),
            "workflow": metadata["workflow"],
            "linear": metadata["linear"],
        }

    def log_issue(self, args: argparse.Namespace) -> dict:
        path, metadata = self.load_metadata(args.change_id)
        if args.engram_observation_id <= 0:
            raise CoreError("engramObservationId must be a positive integer. Save to Engram before logging to Linear.")

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
            "retry": {
                "attempted": attempted,
                "max": max_attempts,
            },
            "status": status,
            "manualFallback": manual_fallback,
        }
        metadata.setdefault("derivedIssues", []).append(derived_issue)
        save_json(path, metadata)
        return {
            "status": status,
            "changeId": args.change_id,
            "metadataPath": str(path.relative_to(self.root)),
            "derivedIssue": derived_issue,
        }

    def archive(self, args: argparse.Namespace) -> dict:
        path, metadata = self.load_metadata(args.change_id)
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

        metadata["archive"] = {
            "evidence": evidence,
            "gate": gate,
            "comment": comment,
        }
        save_json(path, metadata)
        return {
            "status": gate_status,
            "changeId": args.change_id,
            "metadataPath": str(path.relative_to(self.root)),
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

    status_parser = subparsers.add_parser("status", help="Read or update mapped status")
    status_parser.add_argument("--change-id", required=True)
    status_parser.add_argument("--sdd-state")

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

    archive_parser = subparsers.add_parser("archive", help="Evaluate archive gate and render comment")
    archive_parser.add_argument("--change-id", required=True)
    archive_parser.add_argument("--pr-url")
    archive_parser.add_argument("--merge-confirmed", type=parse_bool)
    archive_parser.add_argument("--qa-notes")
    archive_parser.add_argument("--business-validation")
    archive_parser.add_argument("--archive-summary")
    archive_parser.add_argument("--follow-up-notes")

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

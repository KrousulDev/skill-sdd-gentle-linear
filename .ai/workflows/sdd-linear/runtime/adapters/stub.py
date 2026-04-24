from __future__ import annotations

from runtime.ports import RuntimePort, RuntimeOutcome, make_outcome


class StubRuntimeAdapter(RuntimePort):
    mode = "stub"

    def sync_status(self, *, change_id: str, linear_issue_id: str, mapped_linear_state: str) -> list[RuntimeOutcome]:
        return [
            make_outcome(
                system="linear",
                action_type="update_state",
                target_id=linear_issue_id,
                status="success",
                remote_id=linear_issue_id,
                error_message=f"Stub runtime acknowledged state '{mapped_linear_state}' for change '{change_id}'.",
            )
        ]

    def log_issue(self, **kwargs) -> list[RuntimeOutcome]:
        engram_observation_id = kwargs.get("engram_observation_id")
        engram_target_id = str(engram_observation_id) if engram_observation_id else None
        engram_linkage_failed = bool(kwargs.get("engram_linkage_failed"))
        engram_linkage_error = kwargs.get("engram_linkage_error") or "Stub runtime recorded an Engram linkage update failure."
        outcomes = [
            make_outcome(
                system="engram",
                action_type="save_observation",
                target_id=engram_target_id,
                status="failed" if engram_linkage_failed else "success",
                remote_id=engram_target_id,
                error_code="REMOTE" if engram_linkage_failed else None,
                error_message=engram_linkage_error if engram_linkage_failed else "Stub runtime acknowledged Engram persistence.",
                retryable=False if engram_linkage_failed else None,
            )
        ]

        linear_issue_id = kwargs.get("linear_issue_id")
        attempt_errors = kwargs.get("attempt_errors") or []
        parent_linear_issue_id = kwargs.get("parent_linear_issue_id")

        if linear_issue_id:
            outcomes.append(
                make_outcome(
                    system="linear",
                    action_type="create_issue",
                    target_id=parent_linear_issue_id,
                    status="success",
                    remote_id=linear_issue_id,
                    error_message="Stub runtime acknowledged Linear derived issue sync.",
                )
            )
        elif attempt_errors:
            max_attempts = kwargs.get("max_attempts")
            retryable = None if max_attempts is None else len(attempt_errors) < max_attempts
            outcomes.append(
                make_outcome(
                    system="linear",
                    action_type="create_issue",
                    target_id=parent_linear_issue_id,
                    status="failed",
                    error_code="REMOTE",
                    error_message=str(attempt_errors[-1]),
                    retryable=retryable,
                )
            )
        else:
            outcomes.append(
                make_outcome(
                    system="linear",
                    action_type="create_issue",
                    target_id=parent_linear_issue_id,
                    status="skipped",
                    error_message="Stub runtime recorded canonical Engram issue without Linear creation attempt.",
                )
            )

        return outcomes

    def archive(self, **kwargs) -> list[RuntimeOutcome]:
        linear_issue_id = kwargs.get("linear_issue_id")
        gate_status = kwargs.get("gate_status")

        if gate_status != "pass":
            return [
                make_outcome(
                    system="linear",
                    action_type="comment",
                    target_id=linear_issue_id,
                    status="blocked",
                    error_code="PRECHECK_FAILED",
                    error_message="Archive evidence gate blocked remote archive actions.",
                    retryable=False,
                )
            ]

        outcomes = []
        if kwargs.get("comment_allowed"):
            outcomes.append(
                make_outcome(
                    system="linear",
                    action_type="comment",
                    target_id=linear_issue_id,
                    status="success",
                    remote_id=linear_issue_id,
                    error_message="Stub runtime acknowledged archive comment without remote side effects.",
                )
            )
        if kwargs.get("close_allowed"):
            outcomes.append(
                make_outcome(
                    system="linear",
                    action_type="close",
                    target_id=linear_issue_id,
                    status="success",
                    remote_id=linear_issue_id,
                    error_message="Stub runtime acknowledged archive close without remote side effects.",
                )
            )
        return outcomes

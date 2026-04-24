from __future__ import annotations

from typing import Callable, Mapping

from runtime.ports import RuntimeAdapterError, RuntimeOutcome, make_outcome


Handler = Callable[..., list[RuntimeOutcome | dict]]


class LiveRuntimeAdapter:
    mode = "live"

    def __init__(self, *, handlers: Mapping[str, Handler] | None = None):
        self.handlers = dict(handlers or {})

    def sync_status(self, *, change_id: str, linear_issue_id: str, mapped_linear_state: str) -> list[RuntimeOutcome]:
        return self._dispatch(
            "sync_status",
            default_system="linear",
            default_action="update_state",
            default_target=linear_issue_id,
            change_id=change_id,
            linear_issue_id=linear_issue_id,
            mapped_linear_state=mapped_linear_state,
        )

    def log_issue(self, **kwargs) -> list[RuntimeOutcome]:
        return self._dispatch(
            "log_issue",
            default_system="linear",
            default_action="create_issue",
            default_target=kwargs.get("parent_linear_issue_id"),
            **kwargs,
        )

    def archive(self, **kwargs) -> list[RuntimeOutcome]:
        return self._dispatch(
            "archive",
            default_system="linear",
            default_action="comment",
            default_target=kwargs.get("linear_issue_id"),
            **kwargs,
        )

    def _dispatch(
        self,
        operation: str,
        *,
        default_system: str,
        default_action: str,
        default_target: str | None,
        **kwargs,
    ) -> list[RuntimeOutcome]:
        handler = self.handlers.get(operation)
        if handler is None:
            raise RuntimeAdapterError(
                f"Live runtime adapter operation '{operation}' is not configured.",
                code="REMOTE",
                retryable=False,
            )
        try:
            raw_outcomes = handler(**kwargs)
        except RuntimeAdapterError:
            raise
        except Exception as error:  # pragma: no cover - exercised through normalization tests
            raise self.normalize_exception(error) from error

        return [
            self.normalize_outcome(
                item,
                default_system=default_system,
                default_action=default_action,
                default_target=default_target,
            )
            for item in raw_outcomes
        ]

    def normalize_outcome(
        self,
        item: RuntimeOutcome | dict,
        *,
        default_system: str,
        default_action: str,
        default_target: str | None,
    ) -> RuntimeOutcome:
        if isinstance(item, RuntimeOutcome):
            return item

        requested_action = item.get("requestedAction", {})
        observed_result = item.get("observedResult", {})
        error = item.get("error", {})
        return make_outcome(
            system=item.get("system", default_system),
            action_type=item.get("action_type", requested_action.get("type", default_action)),
            target_id=item.get("target_id", requested_action.get("targetId", default_target)),
            status=item.get("status", observed_result.get("status", "success")),
            remote_id=item.get("remote_id", observed_result.get("remoteId")),
            error_code=item.get("error_code", error.get("code")),
            error_message=item.get("error_message", error.get("message")),
            retryable=item.get("retryable", error.get("retryable")),
            timestamp=item.get("timestamp", observed_result.get("timestamp")),
        )

    def normalize_exception(self, error: Exception) -> RuntimeAdapterError:
        if isinstance(error, PermissionError):
            return RuntimeAdapterError(str(error), code="AUTH", retryable=False)
        if isinstance(error, (ConnectionError, TimeoutError, OSError)):
            return RuntimeAdapterError(str(error), code="NETWORK", retryable=True)
        if isinstance(error, ValueError):
            return RuntimeAdapterError(str(error), code="VALIDATION", retryable=False)
        if isinstance(error, RuntimeError):
            return RuntimeAdapterError(str(error), code="REMOTE", retryable=True)
        return RuntimeAdapterError(str(error), code="UNKNOWN", retryable=None)


def build_live_runtime_adapter(*, handlers: Mapping[str, Handler] | None = None) -> LiveRuntimeAdapter:
    return LiveRuntimeAdapter(handlers=handlers)

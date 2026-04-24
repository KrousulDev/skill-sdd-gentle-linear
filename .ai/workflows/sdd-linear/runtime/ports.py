from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


ERROR_CODES = (
    "PRECHECK_FAILED",
    "AUTH",
    "NETWORK",
    "VALIDATION",
    "REMOTE",
    "UNKNOWN",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class RequestedAction:
    type: str
    targetId: str | None


@dataclass(frozen=True)
class ObservedResult:
    status: str
    remoteId: str | None
    timestamp: str


@dataclass(frozen=True)
class RuntimeErrorInfo:
    code: str | None
    message: str | None
    retryable: bool | None


@dataclass(frozen=True)
class RuntimeOutcome:
    system: str
    requestedAction: RequestedAction
    observedResult: ObservedResult
    error: RuntimeErrorInfo

    def to_dict(self) -> dict:
        return {
            "system": self.system,
            "requestedAction": {
                "type": self.requestedAction.type,
                "targetId": self.requestedAction.targetId,
            },
            "observedResult": {
                "status": self.observedResult.status,
                "remoteId": self.observedResult.remoteId,
                "timestamp": self.observedResult.timestamp,
            },
            "error": {
                "code": self.error.code,
                "message": self.error.message,
                "retryable": self.error.retryable,
            },
        }


class RuntimeAdapterError(Exception):
    def __init__(self, message: str, *, code: str = "UNKNOWN", retryable: bool | None = None):
        if code not in ERROR_CODES:
            raise ValueError(f"Unsupported runtime error code: {code}")
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def make_outcome(
    *,
    system: str,
    action_type: str,
    target_id: str | None,
    status: str,
    remote_id: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    retryable: bool | None = None,
    timestamp: str | None = None,
) -> RuntimeOutcome:
    if error_code is not None and error_code not in ERROR_CODES:
        raise ValueError(f"Unsupported runtime error code: {error_code}")
    return RuntimeOutcome(
        system=system,
        requestedAction=RequestedAction(type=action_type, targetId=target_id),
        observedResult=ObservedResult(status=status, remoteId=remote_id, timestamp=timestamp or utc_now()),
        error=RuntimeErrorInfo(code=error_code, message=error_message, retryable=retryable),
    )


class RuntimePort(Protocol):
    def sync_status(self, *, change_id: str, linear_issue_id: str, mapped_linear_state: str) -> list[RuntimeOutcome]:
        ...

    def log_issue(self, **kwargs) -> list[RuntimeOutcome]:
        ...

    def archive(self, **kwargs) -> list[RuntimeOutcome]:
        ...

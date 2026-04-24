from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping


ConnectivityProbe = Callable[[dict], bool | str | tuple[bool, str] | None]


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    status: str
    detail: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class PreflightResult:
    status: str
    checks: list[PreflightCheck]
    allowSideEffects: bool

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "checks": [check.to_dict() for check in self.checks],
            "allowSideEffects": self.allowSideEffects,
        }


def resolve_linear_scope_identifier(*, linear_issue_id: str | None, linear_feature_id: str | None = None) -> str | None:
    for candidate in (linear_feature_id, linear_issue_id):
        if candidate and "-" in candidate:
            return candidate.split("-", 1)[0]
    return linear_feature_id or linear_issue_id


def _normalize_probe_result(result: bool | str | tuple[bool, str] | None) -> tuple[str, str]:
    if isinstance(result, tuple):
        passed, detail = result
        return ("pass" if passed else "fail", detail)
    if isinstance(result, bool):
        return ("pass" if result else "fail", "Connectivity probe returned a boolean result.")
    if isinstance(result, str):
        return ("pass", result)
    return ("pass", "Connectivity probe was not provided; relying on credential validation for safe opt-in.")


def evaluate_target_scope(
    *,
    actions: Iterable[Mapping[str, str | None]],
    smoke_policy: Mapping[str, object],
    linear_issue_id: str | None,
    linear_feature_id: str | None = None,
) -> PreflightCheck:
    action_types = {str(action.get("action_type")) for action in actions}
    if "close" not in action_types:
        return PreflightCheck(
            name="targetScope",
            status="pass",
            detail="Requested live actions stay within the smoke-safe scope.",
        )

    if not bool(smoke_policy.get("allowClose")):
        return PreflightCheck(
            name="targetScope",
            status="fail",
            detail="Live close is disabled by runtime.live.smokePolicy.allowClose.",
        )

    allowed_projects = [str(project) for project in smoke_policy.get("allowedLinearProjects", [])]
    scope_identifier = resolve_linear_scope_identifier(
        linear_issue_id=linear_issue_id,
        linear_feature_id=linear_feature_id,
    )
    if allowed_projects and scope_identifier not in allowed_projects:
        return PreflightCheck(
            name="targetScope",
            status="fail",
            detail=(
                f"Live close is limited to smoke-test projects {allowed_projects}; "
                f"resolved scope '{scope_identifier}' is not allow-listed."
            ),
        )

    return PreflightCheck(
        name="targetScope",
        status="pass",
        detail="Live close is allowed for the resolved smoke-safe target scope.",
    )


def evaluate_live_preflight(
    *,
    runtime_config: Mapping[str, object],
    actions: Iterable[Mapping[str, str | None]],
    linear_issue_id: str | None,
    linear_feature_id: str | None = None,
    env: Mapping[str, str] | None = None,
    connectivity_probe: ConnectivityProbe | None = None,
) -> PreflightResult:
    action_list = list(actions)
    env = env or os.environ
    live_config = dict(runtime_config.get("live", {}))
    preflight_config = dict(live_config.get("preflight", {}))
    smoke_policy = dict(live_config.get("smokePolicy", {}))
    systems = {str(action.get("system")) for action in action_list}
    checks: list[PreflightCheck] = []

    credentials_check = PreflightCheck(name="credentials", status="pass", detail="Credential validation disabled by config.")
    if preflight_config.get("credentials", False):
        missing = []
        if "linear" in systems and not env.get("LINEAR_API_KEY"):
            missing.append("LINEAR_API_KEY")
        if "engram" in systems and not env.get("ENGRAM_API_KEY"):
            missing.append("ENGRAM_API_KEY")
        credentials_check = PreflightCheck(
            name="credentials",
            status="fail" if missing else "pass",
            detail=(
                f"Missing live credential environment variables: {', '.join(missing)}."
                if missing
                else "Required live credentials are present in the environment."
            ),
        )
    checks.append(credentials_check)

    connectivity_check = PreflightCheck(name="connectivity", status="pass", detail="Connectivity validation disabled by config.")
    if preflight_config.get("connectivity", False):
        if credentials_check.status == "fail":
            connectivity_check = PreflightCheck(
                name="connectivity",
                status="fail",
                detail="Connectivity probe skipped because credential validation already failed.",
            )
        else:
            status, detail = _normalize_probe_result(
                connectivity_probe(
                    {
                        "actions": action_list,
                        "linear_issue_id": linear_issue_id,
                        "linear_feature_id": linear_feature_id,
                    }
                )
                if connectivity_probe is not None
                else None
            )
            connectivity_check = PreflightCheck(name="connectivity", status=status, detail=detail)
    checks.append(connectivity_check)

    target_scope_check = PreflightCheck(name="targetScope", status="pass", detail="Target-scope validation disabled by config.")
    if preflight_config.get("targetScope", False):
        target_scope_check = evaluate_target_scope(
            actions=action_list,
            smoke_policy=smoke_policy,
            linear_issue_id=linear_issue_id,
            linear_feature_id=linear_feature_id,
        )
    checks.append(target_scope_check)

    allow_side_effects = all(check.status == "pass" for check in checks)
    return PreflightResult(
        status="pass" if allow_side_effects else "fail",
        checks=checks,
        allowSideEffects=allow_side_effects,
    )

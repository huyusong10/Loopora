from __future__ import annotations

"""Strategy Source step action-policy defaults and validation."""

from collections.abc import Mapping
from typing import Any

from loopora.strategy_source_constants import LEGACY_ROLE_TO_ARCHETYPE
from loopora.strategy_source_errors import WorkflowError
from loopora.strategy_source_validation import unknown_keys

STEP_ACTION_POLICY_KEYS = {"workspace", "can_block", "can_finish_run"}
STEP_ACTION_POLICY_WORKSPACES = {"read_only", "workspace_write"}


def normalize_step_policy_boolean(value: Any, *, field_name: str, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise WorkflowError(f"workflow step action_policy.{field_name} must be a boolean")


def default_strategy_step_action_policy(*, archetype: str | None = None, on_pass: str = "continue") -> dict[str, Any]:
    normalized_archetype = LEGACY_ROLE_TO_ARCHETYPE.get(str(archetype or "").strip().lower(), "")
    if normalized_archetype == "builder":
        return {"workspace": "workspace_write", "can_block": False, "can_finish_run": False}
    if normalized_archetype == "inspector":
        return {"workspace": "read_only", "can_block": True, "can_finish_run": False}
    if normalized_archetype == "gatekeeper":
        return {
            "workspace": "read_only",
            "can_block": True,
            "can_finish_run": str(on_pass or "continue").strip() == "finish_run",
        }
    return {"workspace": "read_only", "can_block": False, "can_finish_run": False}


def default_step_action_policy(*, archetype: str | None = None, on_pass: str = "continue") -> dict[str, Any]:
    return default_strategy_step_action_policy(archetype=archetype, on_pass=on_pass)


def normalize_strategy_step_action_policy_workspace(value: Any, *, default: str) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        raw_workspace = str(default)
    elif not isinstance(value, str):
        raise WorkflowError("workflow step action_policy.workspace must be read_only or workspace_write")
    else:
        raw_workspace = value
    normalized = raw_workspace.strip().lower().replace("-", "_")
    if normalized in {"readonly", "read"}:
        normalized = "read_only"
    elif normalized in {"write", "workspace"}:
        normalized = "workspace_write"
    if normalized not in STEP_ACTION_POLICY_WORKSPACES:
        raise WorkflowError("workflow step action_policy.workspace must be read_only or workspace_write")
    return normalized


def normalize_step_action_policy_workspace(value: Any, *, default: str) -> str:
    return normalize_strategy_step_action_policy_workspace(value, default=default)


def normalize_strategy_step_action_policy(
    value: Any,
    *,
    archetype: str | None = None,
    on_pass: str = "continue",
) -> dict[str, Any]:
    normalized_archetype = LEGACY_ROLE_TO_ARCHETYPE.get(str(archetype or "").strip().lower(), "")
    defaults = default_strategy_step_action_policy(archetype=normalized_archetype, on_pass=on_pass)
    if value is None:
        policy = dict(defaults)
    else:
        if not isinstance(value, Mapping):
            raise WorkflowError("workflow step action_policy must be an object")
        action_policy_unknown_keys = unknown_keys(value, STEP_ACTION_POLICY_KEYS)
        if action_policy_unknown_keys:
            raise WorkflowError(
                f"workflow step action_policy contains unknown keys: {', '.join(action_policy_unknown_keys)}"
            )
        policy = {
            "workspace": normalize_strategy_step_action_policy_workspace(
                value.get("workspace", defaults["workspace"]),
                default=str(defaults["workspace"]),
            ),
            "can_block": normalize_step_policy_boolean(
                value.get("can_block"),
                field_name="can_block",
                default=bool(defaults["can_block"]),
            ),
            "can_finish_run": normalize_step_policy_boolean(
                value.get("can_finish_run"),
                field_name="can_finish_run",
                default=bool(defaults["can_finish_run"]),
            ),
        }

    if policy["workspace"] == "workspace_write" and normalized_archetype != "builder":
        raise WorkflowError("only Builder steps may set action_policy.workspace=workspace_write in v1")
    if policy["can_finish_run"] and normalized_archetype != "gatekeeper":
        raise WorkflowError("only GateKeeper steps may set action_policy.can_finish_run=true")
    if policy["can_finish_run"] and str(on_pass or "continue").strip() != "finish_run":
        raise WorkflowError("action_policy.can_finish_run=true requires on_pass=finish_run")
    return policy


def normalize_step_action_policy(
    value: Any,
    *,
    archetype: str | None = None,
    on_pass: str = "continue",
) -> dict[str, Any]:
    return normalize_strategy_step_action_policy(value, archetype=archetype, on_pass=on_pass)

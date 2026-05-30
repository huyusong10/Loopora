from __future__ import annotations

from typing import Any


def agent_native_step_view_continuation_context(step_instruction_context: object) -> dict[str, Any]:
    step_context = step_instruction_context if isinstance(step_instruction_context, dict) else {}
    continuation = step_context.get("continuation") if isinstance(step_context.get("continuation"), dict) else {}
    return dict(continuation) if continuation.get("active") is True else {}

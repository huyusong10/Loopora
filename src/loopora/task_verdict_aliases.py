from __future__ import annotations

from collections.abc import Mapping

from loopora.kernel.verdict import VerdictStatus

PUBLIC_TO_KERNEL_TASK_VERDICT_STATUS_ALIASES = {
    "insufficient_evidence": "continue_required",
    "failed": "blocked",
}
KERNEL_TO_PUBLIC_TASK_VERDICT_STATUS_ALIASES = {
    kernel_status: public_status for public_status, kernel_status in PUBLIC_TO_KERNEL_TASK_VERDICT_STATUS_ALIASES.items()
}
KERNEL_TO_PUBLIC_TASK_VERDICT_SOURCE_ALIASES = {
    "system": "run_status",
    "human": "legacy",
}


def canonical_task_verdict_status(value: object, *, default: str = "not_evaluated") -> str:
    status = _status_value(value, default=default)
    return PUBLIC_TO_KERNEL_TASK_VERDICT_STATUS_ALIASES.get(status, status)


def public_task_verdict_status(value: object, *, default: str = "not_evaluated") -> str:
    status = _status_value(value, default=default)
    return KERNEL_TO_PUBLIC_TASK_VERDICT_STATUS_ALIASES.get(status, status)


def public_task_verdict_source(value: object) -> str:
    source = str(value or "").strip().lower()
    return KERNEL_TO_PUBLIC_TASK_VERDICT_SOURCE_ALIASES.get(source, source)


def verdict_status_from_task_status(value: object) -> VerdictStatus:
    status = canonical_task_verdict_status(value)
    try:
        return VerdictStatus(status)
    except ValueError:
        return VerdictStatus.NOT_EVALUATED


def _status_value(value: object, *, default: str) -> str:
    raw_value = value.get("status") if isinstance(value, Mapping) else value
    return str(raw_value or default).strip().lower() or default

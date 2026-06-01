from __future__ import annotations

ALIGNMENT_READINESS_EVIDENCE_KEYS = (
    "loop_fit",
    "task_scope",
    "success_surface",
    "fake_done_risks",
    "evidence_preferences",
    "execution_strategy",
    "residual_risk_policy",
    "judgment_tradeoffs",
    "local_governance",
    "role_posture",
    "workflow_shape",
    "workdir_facts",
)


def has_any_marker(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)

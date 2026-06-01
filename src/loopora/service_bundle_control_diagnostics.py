from __future__ import annotations

from loopora.residual_risk_support import residual_risk_is_unmanaged
from loopora.service_bundle_control_diagnostic_entries import (
    append_bundle_control_diagnostic as _append_diagnostic,
)
from loopora.service_bundle_control_input_diagnostics import append_strategy_input_diagnostics


def build_bundle_control_diagnostics(
    *,
    bundle: dict,
    raw_sections: dict,
    step_contexts: list[dict],
    traceability: dict,
) -> list[dict]:
    diagnostics: list[dict] = []
    _append_traceability_diagnostics(diagnostics, traceability)
    _append_residual_risk_policy_diagnostics(diagnostics, raw_sections)
    _append_completion_mode_diagnostics(diagnostics, bundle)
    append_strategy_input_diagnostics(diagnostics, step_contexts)
    return diagnostics


def _append_traceability_diagnostics(diagnostics: list[dict], traceability: dict) -> None:
    missing = [str(item).strip() for item in list(traceability.get("missing") or []) if str(item).strip()]
    if not missing:
        return
    _append_diagnostic(
        diagnostics,
        {
            "code": "traceability_missing",
            "severity": "warning",
            "title_en": "Judgment projection is incomplete",
            "title_zh": "判断投影不完整",
            "message_en": "Some confirmed judgment areas do not map to a runnable bundle surface.",
            "message_zh": "部分已确认判断没有映射到可运行的方案表面。",
            "surfaces": ["collaboration_summary", "spec.markdown", "role_definitions[]", "workflow"],
            "details": {"missing": missing},
        },
    )


def _append_residual_risk_policy_diagnostics(diagnostics: list[dict], raw_sections: dict) -> None:
    residual_risk = str(raw_sections.get("Residual Risk") or "").strip()
    if not residual_risk or not residual_risk_is_unmanaged(residual_risk):
        return
    _append_diagnostic(
        diagnostics,
        {
            "code": "residual_risk_unmanaged",
            "severity": "warning",
            "title_en": "Residual risk policy is not actionable",
            "title_zh": "残余风险策略不可执行",
            "message_en": "Residual risk must name what may remain and who owns, tracks, follows up, accepts, or blocks it.",
            "message_zh": "残余风险必须说明哪些风险可以留下，以及由谁负责、如何跟踪、后续处理、接受或阻断。",
            "surfaces": ["spec.markdown#Residual Risk"],
        },
    )


def _append_completion_mode_diagnostics(diagnostics: list[dict], bundle: dict) -> None:
    completion_mode = str((bundle.get("loop") or {}).get("completion_mode") or "").strip().lower()
    if completion_mode == "gatekeeper":
        return
    _append_diagnostic(
        diagnostics,
        {
            "code": "completion_not_gatekeeper",
            "severity": "info",
            "title_en": "Run closes without evidence-backed GateKeeper mode",
            "title_zh": "运行不是由证据守门模式收束",
            "message_en": "Expert bundles may use this, but the task verdict will lean more on runtime lifecycle than GateKeeper evidence closure.",
            "message_zh": "专家方案可以这样运行，但 Loop 裁决会更依赖运行生命周期，而不是 GateKeeper 的证据收口。",
            "surfaces": ["loop.completion_mode"],
        },
    )

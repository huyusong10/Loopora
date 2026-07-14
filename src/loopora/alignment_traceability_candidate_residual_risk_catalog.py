from __future__ import annotations

"""Agent-candidate traceability residual-risk policy category catalogs."""

RESIDUAL_RISK_POLICY_MARKER_PATTERNS = (
    r"\bresidual risks?\b",
    r"\bremaining risks?\b",
    r"残余风险",
    r"剩余风险",
)


RESIDUAL_RISK_BASE_CATEGORY = (
    "residual-risk",
    r"\bresidual risks?\b|\bremaining risks?\b|残余风险|剩余风险",
)


NO_ACCEPTED_RESIDUAL_RISK_TASK_PATTERN = (
    r"\b(?:no|none|zero)\b.{0,60}\b(?:accepted|acceptable|allowed)?\s*residual risks?\b"
    r"|\b(?:do not|don't|cannot|can't|must not|never)\b.{0,60}\baccept\b.{0,60}\bresidual risks?\b"
    r"|(?:不接受|不能接受|不可接受|不允许).{0,24}残余风险"
    r"|残余风险.{0,24}(?:不接受|不能接受|不可接受|不允许)"
)


NO_ACCEPTED_RESIDUAL_RISK_BUNDLE_PATTERN = (
    r"\b(?:no|none|zero)\b.{0,80}\b(?:accepted|acceptable|allowed)?\s*residual risks?\b"
    r"|\b(?:do not|don't|cannot|can't|must not|never)\b.{0,80}\baccept\b.{0,80}\bresidual risks?\b"
    r"|(?:不接受|不能接受|不可接受|不允许).{0,30}残余风险"
    r"|残余风险.{0,30}(?:不接受|不能接受|不可接受|不允许)"
)


RESIDUAL_RISK_POLICY_CATEGORY_PATTERNS = (
    (
        "acceptance",
        r"\b(?:accept|accepted|acceptable|allow|allowed|carry)\b|接受|可接受|允许|带着走",
        (
            r"(?:\bresidual risks?\b|残余风险|剩余风险).{0,160}"
            r"(?:\b(?:accept|accepted|acceptable|allow|allowed|carry)\b|接受|可接受|允许|带着走)"
            r"|(?:\b(?:accept|accepted|acceptable|allow|allowed|carry)\b|接受|可接受|允许|带着走)"
            r".{0,160}(?:\bresidual risks?\b|残余风险|剩余风险)"
        ),
    ),
    (
        "owner/follow-up",
        (
            r"\b(?:owner|owned|assignee|follow[- ]?up|followup|ticket|tracked|tracking|"
            r"revisit|monitor|mitigation)\b|负责人|负责|接手|接管|跟进|工单|跟踪|追踪|监控|缓解"
        ),
        (
            r"(?:\bresidual risks?\b|残余风险|剩余风险).{0,180}"
            r"(?:\b(?:owner|owned|assignee|follow[- ]?up|followup|ticket|tracked|tracking|"
            r"revisit|monitor|mitigation)\b|负责人|负责|接手|接管|跟进|工单|跟踪|追踪|监控|缓解)"
            r"|(?:\b(?:owner|owned|assignee|follow[- ]?up|followup|ticket|tracked|tracking|"
            r"revisit|monitor|mitigation)\b|负责人|负责|接手|接管|跟进|工单|跟踪|追踪|监控|缓解)"
            r".{0,180}(?:\bresidual risks?\b|残余风险|剩余风险)"
        ),
    ),
    (
        "fail-closed",
        r"\b(?:fail closed|must block|must fail|block|blocking|reject)\b|失败关闭|必须阻断|必须失败|阻断|拒绝",
        (
            r"(?:\bresidual risks?\b|残余风险|剩余风险).{0,180}"
            r"(?:\b(?:fail closed|must block|must fail|block|blocking|reject)\b|失败关闭|必须阻断|必须失败|阻断|拒绝)"
            r"|(?:\b(?:fail closed|must block|must fail|block|blocking|reject)\b|失败关闭|必须阻断|必须失败|阻断|拒绝)"
            r".{0,180}(?:\bresidual risks?\b|残余风险|剩余风险)"
        ),
    ),
)

__all__ = (
    "NO_ACCEPTED_RESIDUAL_RISK_BUNDLE_PATTERN",
    "NO_ACCEPTED_RESIDUAL_RISK_TASK_PATTERN",
    "RESIDUAL_RISK_BASE_CATEGORY",
    "RESIDUAL_RISK_POLICY_CATEGORY_PATTERNS",
    "RESIDUAL_RISK_POLICY_MARKER_PATTERNS",
)

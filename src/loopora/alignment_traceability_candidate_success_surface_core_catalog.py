from __future__ import annotations

"""Agent-candidate success-surface markers, base category, and core outcome categories."""

from loopora.alignment_traceability_domain_patterns import (
    AUTHORIZATION_POLICY_CONSISTENCY_PATTERN,
)

SUCCESS_SURFACE_MARKER_PATTERNS = (
    r"\bsuccess\s+(?:means|requires|is)\b",
    r"\bdone when\b",
    r"\bcomplete when\b",
    r"\bacceptance criteria\b",
    r"\bto pass\b.{0,80}\b(?:must|needs?|should|requires?)\b",
    r"\b(?:must|needs?|should|requires?)\b.{0,80}\b(?:pass|succeed|be complete|be done)\b",
    r"成功.{0,16}(?:必须|需要|应当|要).{0,16}(?:证明|验证|包含|包括)",
    r"成功(?:标准|意味着|要求|面)",
    r"完成(?:标准|条件|时)",
    r"验收(?:标准|条件)",
)


SUCCESS_SURFACE_BASE_CATEGORY = (
    "success/done-when",
    r"\b(?:success|done when|acceptance criteria|complete when|completion criteria)\b|成功|完成标准|验收",
)


SUCCESS_SURFACE_CORE_CATEGORY_PATTERNS = (
    (
        "actor/user-facing-outcome",
        r"\b(?:user|customer|admin|operator|buyer|merchant|support)\b|用户|客户|管理员|运营|买家|商家|客服",
    ),
    (
        "notification/message",
        r"\b(?:notification|notify|email|message|receipt|alert)\b|通知|邮件|消息|回执|提醒",
    ),
    (
        "idempotency/duplicate-prevention",
        r"\b(?:duplicate|duplicated|dedupe|deduplicat(?:e|ed|ion)|idempotent|idempotency|exactly\s+once|only\s+once|one\s+time)\b|重复|去重|幂等|只发一次|仅发一次|只.*一次|仅.*一次",
    ),
    (
        "audit/log",
        r"\b(?:audit|auditing|audit[- ]?log|log|logs|ledger|trace|recorded|records?)\b|审计|日志|账本|记录|追踪",
    ),
    (
        "permission/auth",
        r"\b(?:permission|permissions|authorization|auth|access|role|acl|access[- ]?control|"
        r"permission[- ]?filter(?:ing)?|access[- ]?filter(?:ing)?)\b|权限|授权|访问|角色|ACL|权限过滤|访问控制",
    ),
    (
        "access/authorization-policy-consistency",
        AUTHORIZATION_POLICY_CONSISTENCY_PATTERN,
    ),
    (
        "payment/refund/billing",
        r"\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账",
    ),
    (
        "data/export/report",
        r"\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板",
    ),
)

__all__ = (
    "SUCCESS_SURFACE_BASE_CATEGORY",
    "SUCCESS_SURFACE_CORE_CATEGORY_PATTERNS",
    "SUCCESS_SURFACE_MARKER_PATTERNS",
)

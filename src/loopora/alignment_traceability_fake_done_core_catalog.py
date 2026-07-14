from __future__ import annotations

"""Fake-done catalog entries for core generic task-risk blockers."""

from loopora.alignment_traceability_domain_patterns import (
    AUTHORIZATION_POLICY_CONSISTENCY_PATTERN,
)

from loopora.alignment_traceability_risk_markers import (
    FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
    risk_marker_near_domain_pattern,
)

FAKE_DONE_CORE_CATEGORY_PATTERNS = (
    (
        "permission/audit",
        r"\b(?:permission|permissions|authorization|auth|access|acl|access[- ]?control|"
        r"permission[- ]?filter(?:ing)?|access[- ]?filter(?:ing)?|audit|auditing|audit[- ]?log)\b|"
        r"权限|授权|审计|日志|ACL|权限过滤|访问控制",
        r"\b(?:permission|permissions|authorization|auth|access|acl|access[- ]?control|"
        r"permission[- ]?filter(?:ing)?|access[- ]?filter(?:ing)?|audit|auditing|audit[- ]?log)\b|"
        r"权限|授权|审计|日志|ACL|权限过滤|访问控制",
    ),
    (
        "access/authorization-policy-consistency",
        risk_marker_near_domain_pattern(
            FAKE_DONE_HAPPY_PATH_MARKER_PATTERN,
            AUTHORIZATION_POLICY_CONSISTENCY_PATTERN,
            window=220,
            extra_marker_pattern=r"hide[- ]?button|hidden[- ]?button|middleware|只隐藏按钮|只加中间件|只检查管理员",
        ),
        AUTHORIZATION_POLICY_CONSISTENCY_PATTERN,
    ),
    (
        "idempotency/duplicate-prevention",
        (
            r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
            r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过).{0,80}"
            r"(?:\b(?:duplicate|duplicated|dedupe|deduplicat(?:e|ed|ion)|idempotent|idempotency|exactly\s+once|only\s+once)\b|重复|去重|幂等|只发一次|仅发一次)"
            r"|(?:\b(?:duplicate|duplicated|dedupe|deduplicat(?:e|ed|ion)|idempotent|idempotency|exactly\s+once|only\s+once)\b|重复|去重|幂等|只发一次|仅发一次)"
            r".{0,80}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
            r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过)"
        ),
        r"\b(?:duplicate|duplicated|dedupe|deduplicat(?:e|ed|ion)|idempotent|idempotency|exactly\s+once|only\s+once)\b|重复|去重|幂等|只发一次|仅发一次",
    ),
    (
        "download/export-only",
        r"\b(?:csv|download|export|file)\b|下载|导出|文件",
        r"\b(?:csv|download|export|file)\b|下载|导出|文件",
    ),
    (
        "privacy/secrets-redaction",
        (
            r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
            r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过).{0,100}"
            r"(?:\b(?:privacy|private|pii|personal\s+data|sensitive\s+data|secret|secrets|token|tokens|password|credential|credentials|redact|redacted|redaction|mask|masked|leak|leakage|plain[- ]?text)\b|隐私|个人信息|敏感数据|敏感信息|密钥|令牌|口令|密码|凭据|脱敏|掩码|泄露|明文|手机号|身份证)"
            r"|(?:\b(?:privacy|private|pii|personal\s+data|sensitive\s+data|secret|secrets|token|tokens|password|credential|credentials|redact|redacted|redaction|mask|masked|leak|leakage|plain[- ]?text)\b|隐私|个人信息|敏感数据|敏感信息|密钥|令牌|口令|密码|凭据|脱敏|掩码|泄露|明文|手机号|身份证)"
            r".{0,100}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
            r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过)"
        ),
        (
            r"\b(?:privacy|private|pii|personal\s+data|sensitive\s+data|secret|secrets|token|tokens|password|credential|credentials|redact|redacted|redaction|mask|masked|leak|leakage|plain[- ]?text)\b"
            r"|隐私|个人信息|敏感数据|敏感信息|密钥|令牌|口令|密码|凭据|脱敏|掩码|泄露|明文|手机号|身份证"
        ),
    ),
    (
        "payment/refund/billing",
        (
            r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
            r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过).{0,80}"
            r"(?:\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账)"
            r"|(?:\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账)"
            r".{0,80}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
            r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过)"
        ),
        (
            r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
            r"\b(?:only|just|merely)\b|假完成|不得通过|不能通过).{0,80}"
            r"(?:\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账)"
            r"|(?:\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账)"
            r".{0,80}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
            r"\b(?:only|just|merely)\b|假完成|不得通过|不能通过)"
        ),
    ),
    (
        "data/export/report",
        (
            r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
            r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过).{0,80}"
            r"(?:\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板)"
            r"|(?:\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板)"
            r".{0,80}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
            r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过)"
        ),
        (
            r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
            r"\b(?:only|just|merely)\b|假完成|不得通过|不能通过).{0,80}"
            r"(?:\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板)"
            r"|(?:\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板)"
            r".{0,80}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
            r"\b(?:only|just|merely)\b|假完成|不得通过|不能通过)"
        ),
    ),
)

__all__ = ("FAKE_DONE_CORE_CATEGORY_PATTERNS",)

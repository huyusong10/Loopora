from __future__ import annotations

"""Agent-candidate success-surface trust, privacy, accessibility, and locale categories."""

from loopora.alignment_traceability_domain_patterns import (
    ACCESSIBILITY_A11Y_PATTERN,
    AUTH_SESSION_TOKEN_LIFECYCLE_PATTERN,
    IDENTITY_PROVISIONING_ROLE_MAPPING_PATTERN,
    IDENTITY_SSO_ASSERTION_PATTERN,
    KEY_ROTATION_SECRET_LIFECYCLE_PATTERN,
    LOCALE_I18N_PATTERN,
    NOTIFICATION_SUBSCRIPTION_DELIVERABILITY_PATTERN,
)

SUCCESS_SURFACE_TRUST_LOCALE_CATEGORY_PATTERNS = (
    (
        "identity/sso-assertion",
        IDENTITY_SSO_ASSERTION_PATTERN,
    ),
    (
        "identity/provisioning-role-mapping",
        IDENTITY_PROVISIONING_ROLE_MAPPING_PATTERN,
    ),
    (
        "auth/session-token-lifecycle",
        AUTH_SESSION_TOKEN_LIFECYCLE_PATTERN,
    ),
    (
        "security/key-rotation-lifecycle",
        KEY_ROTATION_SECRET_LIFECYCLE_PATTERN,
    ),
    (
        "notification/subscription-deliverability",
        NOTIFICATION_SUBSCRIPTION_DELIVERABILITY_PATTERN,
    ),
    (
        "privacy/secrets-redaction",
        (
            r"\b(?:privacy|private|pii|personal\s+data|sensitive\s+data|secret|secrets|token|tokens|"
            r"password|credential|credentials|redact|redacted|redaction|mask|masked|leak|leakage|plain[- ]?text)\b"
            r"|隐私|个人信息|敏感数据|敏感信息|密钥|令牌|口令|密码|凭据|脱敏|掩码|泄露|明文|手机号|身份证"
        ),
    ),
    (
        "accessibility/a11y",
        ACCESSIBILITY_A11Y_PATTERN,
    ),
    (
        "locale/i18n",
        LOCALE_I18N_PATTERN,
    ),
)

__all__ = ("SUCCESS_SURFACE_TRUST_LOCALE_CATEGORY_PATTERNS",)

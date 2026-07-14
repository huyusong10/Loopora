from __future__ import annotations

"""SSO, provisioning, session, and secret-lifecycle domain-risk patterns."""

IDENTITY_SSO_ASSERTION_PATTERN = (
    r"\b(?:saml|oidc|openid[- ]?connect|idp[- ]?metadata|identity[- ]?provider[- ]?metadata|"
    r"assertion[- ]?signature|signed[- ]?assertion|saml[- ]?assertion|oidc[- ]?claims?|"
    r"metadata[- ]?signature|issuer[- ]?validation|audience[- ]?validation)\b"
    r"|单点登录|身份提供商|身份断言|断言签名|签名断言|元数据签名|IdP\s*元数据|发行方校验|受众校验"
)


IDENTITY_PROVISIONING_ROLE_MAPPING_PATTERN = (
    r"\b(?:jit[- ]?provision(?:ing)?|just[- ]?in[- ]?time[- ]?provision(?:ing)?|scim|"
    r"role[- ]?mapping|group[- ]?mapping|attribute[- ]?mapping|provision(?:ed|ing)?[- ]?user|"
    r"owner/admin/member|admin/member|sso[- ]?role(?:s)?)\b"
    r"|即时开通|用户开通|自动开通|角色映射|组映射|属性映射|权限映射|SSO\s*角色|owner/admin/member"
)


AUTH_SESSION_TOKEN_LIFECYCLE_PATTERN = (
    r"(?:(?:\b(?:password[- ]?reset|reset[- ]?(?:token|link|email)|email[- ]?verification|"
    r"verification[- ]?(?:token|link)|session(?:s)?|refresh[- ]?token(?:s)?|auth[- ]?token(?:s)?)\b|"
    r"密码重置|重置(?:令牌|链接|邮件)|验证(?:令牌|链接)|会话|刷新令牌|登录令牌|认证令牌).{0,220}"
    r"(?:\b(?:one[- ]?time|single[- ]?use|expiry|expires?|expiration|ttl|replay|replayed|"
    r"replay[- ]?prevention|token[- ]?hash(?:ing)?|hash(?:ed)?[- ]?token|revocation|revoke|revoked|"
    r"session[- ]?invalidation|session[- ]?revocation|invalidate[- ]?(?:session|sessions|tokens?)|"
    r"refresh[- ]?token[- ]?rotation|enumeration[- ]?resistance|rate[- ]?limit(?:ing)?)\b|"
    r"一次性|单次使用|过期|有效期|重放|防重放|令牌哈希|哈希存储|撤销|失效|会话失效|会话撤销|"
    r"刷新令牌轮换|枚举防护|限流)"
    r"|(?:\b(?:one[- ]?time|single[- ]?use|expiry|expires?|expiration|ttl|replay|replayed|"
    r"replay[- ]?prevention|token[- ]?hash(?:ing)?|hash(?:ed)?[- ]?token|revocation|revoke|revoked|"
    r"session[- ]?invalidation|session[- ]?revocation|invalidate[- ]?(?:session|sessions|tokens?)|"
    r"refresh[- ]?token[- ]?rotation|enumeration[- ]?resistance|rate[- ]?limit(?:ing)?)\b|"
    r"一次性|单次使用|过期|有效期|重放|防重放|令牌哈希|哈希存储|撤销|失效|会话失效|会话撤销|"
    r"刷新令牌轮换|枚举防护|限流).{0,220}"
    r"(?:\b(?:password[- ]?reset|reset[- ]?(?:token|link|email)|email[- ]?verification|"
    r"verification[- ]?(?:token|link)|session(?:s)?|refresh[- ]?token(?:s)?|auth[- ]?token(?:s)?)\b|"
    r"密码重置|重置(?:令牌|链接|邮件)|验证(?:令牌|链接)|会话|刷新令牌|登录令牌|认证令牌))"
)


KEY_ROTATION_SECRET_LIFECYCLE_PATTERN = (
    r"(?:(?:\b(?:api[- ]?key(?:s)?|access[- ]?key(?:s)?|service[- ]?account[- ]?secret(?:s)?|"
    r"client[- ]?secret(?:s)?|secret(?:s)?|credential(?:s)?|kms[- ]?key(?:s)?)\b|"
    r"API\s*key|访问密钥|服务账号密钥|客户端密钥|密钥|凭据|KMS\s*密钥).{0,260}"
    r"(?:\b(?:key[- ]?rotation|secret[- ]?rotation|rotat(?:e|ed|ion)|"
    r"overlap[- ]?window|zero[- ]?downtime|compromised[- ]?key|revoke|revoked|revocation|"
    r"key[- ]?scope|scope|tenant[- ]?binding|hash(?:ed)?|kms[- ]?encrypt(?:ed|ion)|encrypted[- ]?storage|"
    r"rotation[- ]?schedule|expiry|expires?|expiration|last[- ]?used|telemetry|key[- ]?id|"
    r"stale[- ]?key|rotation[- ]?failure|failed[- ]?rotation|rollback)\b|"
    r"密钥轮换|密钥旋转|轮换|重叠窗口|无中断|被盗密钥|泄露密钥|撤销|吊销|失效|"
    r"密钥范围|权限范围|租户绑定|哈希|哈希存储|KMS\s*加密|加密存储|轮换计划|过期|有效期|"
    r"最后使用|使用遥测|密钥\s*id|陈旧密钥|轮换失败|回滚)"
    r"|(?:\b(?:key[- ]?rotation|secret[- ]?rotation|rotat(?:e|ed|ion)|"
    r"overlap[- ]?window|zero[- ]?downtime|compromised[- ]?key|revoke|revoked|revocation|"
    r"key[- ]?scope|scope|tenant[- ]?binding|hash(?:ed)?|kms[- ]?encrypt(?:ed|ion)|encrypted[- ]?storage|"
    r"rotation[- ]?schedule|expiry|expires?|expiration|last[- ]?used|telemetry|key[- ]?id|"
    r"stale[- ]?key|rotation[- ]?failure|failed[- ]?rotation|rollback)\b|"
    r"密钥轮换|密钥旋转|轮换|重叠窗口|无中断|被盗密钥|泄露密钥|撤销|吊销|失效|"
    r"密钥范围|权限范围|租户绑定|哈希|哈希存储|KMS\s*加密|加密存储|轮换计划|过期|有效期|"
    r"最后使用|使用遥测|密钥\s*id|陈旧密钥|轮换失败|回滚).{0,260}"
    r"(?:\b(?:api[- ]?key(?:s)?|access[- ]?key(?:s)?|service[- ]?account[- ]?secret(?:s)?|"
    r"client[- ]?secret(?:s)?|secret(?:s)?|credential(?:s)?|kms[- ]?key(?:s)?)\b|"
    r"API\s*key|访问密钥|服务账号密钥|客户端密钥|密钥|凭据|KMS\s*密钥))"
)


__all__ = (
    "AUTH_SESSION_TOKEN_LIFECYCLE_PATTERN",
    "IDENTITY_PROVISIONING_ROLE_MAPPING_PATTERN",
    "IDENTITY_SSO_ASSERTION_PATTERN",
    "KEY_ROTATION_SECRET_LIFECYCLE_PATTERN",
)

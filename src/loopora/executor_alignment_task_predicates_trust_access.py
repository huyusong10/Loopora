from __future__ import annotations

import re

from loopora.executor_alignment_task_predicates_trust_governance import is_data_residency_task
from loopora.executor_alignment_task_predicates_trust_secrets import is_key_rotation_task


def is_auth_session_token_lifecycle_task(task: str) -> bool:
    text = str(task or "")
    if is_identity_sso_task(text) or is_key_rotation_task(text) or is_support_impersonation_task(text):
        return False
    if re.search(r"API\s+token\s+usage\s+analytics|token\s+volume|usage\s+trends|用量分析|使用趋势", text, re.IGNORECASE):
        return False
    if not re.search(
        r"auth\s+session|session\s+token|token\s+lifecycle|access\s+token|refresh\s+token|password\s+reset|reset\s+token|logout|all[- ]?devices?|MFA\s+step[- ]?up|session\s+revocation|session\s+invalidation|认证会话|会话|访问\s*token|刷新\s*token|密码重置|重置\s*token|登出|退出登录|多设备|撤销|失效",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"expir(?:y|e|ed|ation)|rotat(?:e|ion)|reuse|replay|revok(?:e|ed|ing|ation)?|stolen|secure|httpOnly|SameSite|cookie|CSRF|audit|monitoring|migration|过期|轮换|重用|复用|重放|撤销|失效|被盗|安全|审计|监控|迁移",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"auth\s+session|session\s+token|token\s+lifecycle|认证会话|会话|token\s*生命周期",
        r"access\s+token|refresh\s+token|访问\s*token|刷新\s*token",
        r"refresh\s+rotation|reuse\s+detection|refresh\s+reuse|rotation|reuse|轮换|重用|复用",
        r"logout|all[- ]?devices?|session\s+revocation|revok(?:e|ed|ing|ation)?|登出|退出登录|全设备|撤销",
        r"password\s+reset|reset\s+token|old\s+session|密码重置|重置\s*token|旧\s*session|旧会话",
        r"MFA\s+step[- ]?up|step[- ]?up|multi[- ]?factor|二次验证|多因素|提升验证",
        r"expired|expiry|expiration|stolen|replay|revoked|negative|过期|被盗|重放|负向",
        r"secure|httpOnly|SameSite|cookie|CSRF|API\s+token\s+boundary|安全|边界",
        r"tenant|device|session\s+audit|audit\s+trail|audit[- ]?log|monitoring|alert|租户|设备|审计|监控|告警",
        r"backward[- ]?compat|migration|rollback|兼容|迁移|回滚",
        r"login/logout\s+happy|frontend[- ]?only|framework\s+defaults?|short[- ]?expiry[- ]?only|follow[- ]?up|前端|默认|短过期|后续",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def is_support_impersonation_task(task: str) -> bool:
    text = str(task or "")
    if is_data_residency_task(text):
        return False
    if not re.search(r"support\s+impersonation|impersonat|break[- ]?glass|login[- ]as|代理登录|破窗|代入|模拟登录", text, re.IGNORECASE):
        return False
    markers = (
        r"support\s+impersonation|impersonat|break[- ]?glass|login[- ]as|代理登录|破窗|代入|模拟登录",
        r"approved\s+ticket|customer\s+consent|reason\s+code|supervisor\s+approval|审批|同意|原因码|主管",
        r"actor|acting_as|on_behalf_of|attribution|session|MFA|step[- ]?up|归因|会话|限时",
        r"PII|privacy|tenant|audit|tamper|revoke|expiry|export|monitoring|隐私|租户|审计|撤销|过期|导出|监控",
        r"shared\s+admin\s+token|shared[- ]?token|banner|feature\s+flag|no[- ]?ticket|after[- ]?hours|共享.*token|横幅",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 3


def is_identity_sso_task(task: str) -> bool:
    text = str(task or "")
    if is_authorization_policy_task(text):
        return False
    if not re.search(
        r"\b(?:SAML|OIDC|OpenID[- ]?Connect|SSO|IdP|identity[- ]?provider)\b|单点登录|身份提供商|身份断言",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"\b(?:SAML|OIDC|OpenID[- ]?Connect|SSO|IdP|identity[- ]?provider|metadata|assertion|issuer|audience)\b|单点登录|身份提供商|身份断言|断言|发行方|受众",
        r"signature|signed|forged|replay|expired|expiry|session|logout|签名|伪造|重放|过期|会话|登出",
        r"tenant|domain\s+binding|cross[- ]?tenant|company\s+[AB]|租户|域名绑定|跨租户",
        r"SCIM|JIT|provision|deprovision|role\s+mapping|group\s+mapping|owner|admin|member|开通|停用|角色映射|组映射",
        r"password[- ]?login|backward\s+compat|migration|audit|monitoring|alert|密码登录|兼容|迁移|审计|监控|告警",
        r"Okta|library|UI\s+enabled|admin[- ]?only|happy[- ]?path|测试用户|已启用|只.*admin",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 3


def is_authorization_policy_task(task: str) -> bool:
    text = str(task or "")
    if re.search(r"\bRAG\b|retrieval|retrieval\s*ACL|grounded|citation|source\s+span|知识库|检索增强", text, re.IGNORECASE):
        return False
    if not re.search(r"authorization|policy\s+decision|RBAC|ABAC|权限|授权|访问策略|权限策略", text, re.IGNORECASE):
        return False
    markers = (
        r"authorization|policy\s+decision|permission\s+matrix|RBAC|ABAC|权限|授权|权限矩阵|访问策略|权限策略",
        r"API|UI|background\s+jobs?|CSV|exports?|reports?|audit|cache|endpoint|后台任务|导出|报表|审计|缓存",
        r"tenant|cross[- ]?tenant|field[- ]?level|role\s+hierarchy|owner|admin|viewer|租户|字段级|角色",
        r"SCIM|SSO|group\s+mapping|temporary\s+access|version\s+rollout|backward\s+compat|临时权限|版本|兼容",
        r"hidden\s+buttons?|middleware|happy[- ]?path|negative\s+authorization|stale\s+cache|revocation|隐藏按钮|负向授权|撤销",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 3

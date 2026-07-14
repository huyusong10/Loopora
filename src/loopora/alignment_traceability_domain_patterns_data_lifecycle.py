from __future__ import annotations

"""Data lifecycle, retention, and consent-governance domain-risk patterns."""

DATA_LIFECYCLE_DELETION_RETENTION_PATTERN = (
    r"(?:(?:\b(?:gdpr|erasure|right[- ]?to[- ]?be[- ]?forgotten|purge|purged|purging|"
    r"anonymi[sz](?:e|ed|ation)|retention|retention[- ]?exception|data[- ]?lifecycle|"
    r"async[- ]?cleanup|personal[- ]?data|pii)\b|"
    r"擦除|清除个人信息|删除个人信息|匿名化|留存|保留例外|保留期限|异步清理|个人信息).{0,220}"
    r"(?:\b(?:primary[- ]?database|search[- ]?index(?:es)?|cache(?:s|d)?|backup(?:s)?|"
    r"export[- ]?reports?|audit|billing|retention[- ]?exception|async[- ]?cleanup)\b|"
    r"主库|搜索索引|缓存|备份|导出报表|审计|账务|保留例外|异步清理)"
    r"|(?:\b(?:primary[- ]?database|search[- ]?index(?:es)?|cache(?:s|d)?|backup(?:s)?|"
    r"export[- ]?reports?|audit|billing|retention[- ]?exception|async[- ]?cleanup)\b|"
    r"主库|搜索索引|缓存|备份|导出报表|审计|账务|保留例外|异步清理).{0,220}"
    r"(?:\b(?:gdpr|erasure|right[- ]?to[- ]?be[- ]?forgotten|purge|purged|purging|"
    r"anonymi[sz](?:e|ed|ation)|retention|retention[- ]?exception|data[- ]?lifecycle|"
    r"async[- ]?cleanup|personal[- ]?data|pii)\b|"
    r"擦除|清除个人信息|删除个人信息|匿名化|留存|保留例外|保留期限|异步清理|个人信息))"
)


CONSENT_PREFERENCE_GOVERNANCE_PATTERN = (
    r"(?:(?:\b(?:consent[- ]?(?:management|governance|ledger|record|version|proof|center|preference[- ]?center)|"
    r"consent\s+(?:and\s+)?preference[- ]?center|"
    r"cookie[- ]?consent|privacy[- ]?preference(?:s)?|consent[- ]?preference(?:s)?|"
    r"marketing[- ]?opt[- ]?in|tracking[- ]?consent|vendor[- ]?consent|"
    r"third[- ]?party[- ]?vendor[- ]?consent|legal[- ]?basis|purpose[- ]?id|"
    r"do[- ]?not[- ]?(?:sell|share)|ccpa[- ]?opt[- ]?out|withdraw(?:al)?[- ]?consent|"
    r"re[- ]?consent[- ]?required)\b|"
    r"同意管理|同意治理|同意账本|同意记录|同意版本|Cookie\s*同意|隐私偏好|同意偏好|"
    r"营销同意|追踪同意|供应商同意|第三方供应商同意|法律依据|处理目的|目的\s*id|"
    r"撤回同意|重新同意|拒绝出售|拒绝共享).{0,320}"
    r"(?:\b(?:policy[- ]?version|purpose[- ]?id|purpose(?:s)?|legal[- ]?basis|region(?:al)?[- ]?rules?|"
    r"source|timestamp|ip|user[- ]?agent|immutable[- ]?audit|audit[- ]?log|withdraw(?:al)?|"
    r"analytics[- ]?event(?:s)?|marketing[- ]?campaign(?:s)?|vendor[- ]?sync|provider[- ]?sync|"
    r"double[- ]?opt[- ]?in|unsubscribe|suppression[- ]?list|dsar[- ]?export|deletion[- ]?request|"
    r"account[- ]?preference[- ]?merge|preference[- ]?cache|stale[- ]?preference[- ]?cache|"
    r"consent[- ]?drift|vendor[- ]?mismatch|tracking[- ]?without[- ]?consent|"
    r"localstorage|consent=true)\b|"
    r"政策版本|处理目的|目的\s*id|法律依据|区域规则|地区规则|来源|时间戳|用户代理|"
    r"不可篡改审计|审计日志|撤回|分析事件|营销活动|供应商同步|服务商同步|双重同意|"
    r"退订|抑制名单|抑制列表|DSAR\s*导出|删除请求|账号偏好合并|偏好缓存|陈旧偏好缓存|"
    r"同意漂移|供应商不匹配|未同意追踪|localStorage|consent=true)"
    r"|(?:\b(?:policy[- ]?version|purpose[- ]?id|purpose(?:s)?|legal[- ]?basis|region(?:al)?[- ]?rules?|"
    r"source|timestamp|ip|user[- ]?agent|immutable[- ]?audit|audit[- ]?log|withdraw(?:al)?|"
    r"analytics[- ]?event(?:s)?|marketing[- ]?campaign(?:s)?|vendor[- ]?sync|provider[- ]?sync|"
    r"double[- ]?opt[- ]?in|unsubscribe|suppression[- ]?list|dsar[- ]?export|deletion[- ]?request|"
    r"account[- ]?preference[- ]?merge|preference[- ]?cache|stale[- ]?preference[- ]?cache|"
    r"consent[- ]?drift|vendor[- ]?mismatch|tracking[- ]?without[- ]?consent|"
    r"localstorage|consent=true)\b|"
    r"政策版本|处理目的|目的\s*id|法律依据|区域规则|地区规则|来源|时间戳|用户代理|"
    r"不可篡改审计|审计日志|撤回|分析事件|营销活动|供应商同步|服务商同步|双重同意|"
    r"退订|抑制名单|抑制列表|DSAR\s*导出|删除请求|账号偏好合并|偏好缓存|陈旧偏好缓存|"
    r"同意漂移|供应商不匹配|未同意追踪|localStorage|consent=true).{0,320}"
    r"(?:\b(?:consent[- ]?(?:management|governance|ledger|record|version|proof|center|preference[- ]?center)|"
    r"consent\s+(?:and\s+)?preference[- ]?center|"
    r"cookie[- ]?consent|privacy[- ]?preference(?:s)?|consent[- ]?preference(?:s)?|"
    r"marketing[- ]?opt[- ]?in|tracking[- ]?consent|vendor[- ]?consent|"
    r"third[- ]?party[- ]?vendor[- ]?consent|legal[- ]?basis|purpose[- ]?id|"
    r"do[- ]?not[- ]?(?:sell|share)|ccpa[- ]?opt[- ]?out|withdraw(?:al)?[- ]?consent|"
    r"re[- ]?consent[- ]?required)\b|"
    r"同意管理|同意治理|同意账本|同意记录|同意版本|Cookie\s*同意|隐私偏好|同意偏好|"
    r"营销同意|追踪同意|供应商同意|第三方供应商同意|法律依据|处理目的|目的\s*id|"
    r"撤回同意|重新同意|拒绝出售|拒绝共享))"
)


__all__ = (
    "CONSENT_PREFERENCE_GOVERNANCE_PATTERN",
    "DATA_LIFECYCLE_DELETION_RETENTION_PATTERN",
)

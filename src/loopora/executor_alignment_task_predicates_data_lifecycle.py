from __future__ import annotations

import re

from loopora.executor_alignment_task_predicates_data_cross_domain import (
    is_data_residency_task,
    is_support_impersonation_task,
)
from loopora.executor_alignment_task_predicates_data_resilience import is_audit_log_integrity_retention_task


def is_dsar_data_export_task(task: str) -> bool:
    text = str(task or "")
    if is_data_residency_task(text) or is_support_impersonation_task(text):
        return False
    explicit_export = re.search(
        r"\b(?:DSAR|subject\s+access\s+request|data\s+subject\s+access|privacy\s+export|data\s+export|export\s+request)\b|"
        r"个人信息导出|隐私导出|数据主体访问|数据访问请求",
        text,
        re.IGNORECASE,
    )
    subject_access_export = re.search(
        r"\b(?:DSAR|subject\s+access\s+request|data\s+subject\s+access|privacy\s+export|export\s+request)\b|"
        r"个人信息导出|隐私导出|数据主体访问|数据访问请求",
        text,
        re.IGNORECASE,
    )
    compliance_export = re.search(r"\b(?:GDPR|CCPA|GDPR\s*/?\s*CCPA)\b", text, re.IGNORECASE) and re.search(
        r"export|download|subject\s+access|access\s+request|导出|下载|访问请求",
        text,
        re.IGNORECASE,
    )
    if not explicit_export and not compliance_export:
        return False
    if not subject_access_export and re.search(
        r"erase|erasure|delete|deletion|right[- ]?to[- ]?be[- ]?forgotten|account\s+deletion|数据删除|删除|擦除|遗忘权",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"export|download|request|identity|verification|permission|admin|API|scope|profile|billing|orders?|messages?|attachments?|metadata|tenant|redact|PII|secret|legal[- ]?hold|retention|async|job|signed\s+URL|expiry|cleanup|download\s+audit|notification|rate\s+limit|导出|下载|请求|身份|权限|范围|资料|账单|订单|消息|附件|元数据|租户|脱敏|法务保留|保留|异步|签名|过期|清理|审计|通知|限流",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"\b(?:DSAR|subject\s+access\s+request|data\s+subject\s+access|GDPR\s*/?\s*CCPA|GDPR|CCPA|privacy\s+export|data\s+export|export\s+request)\b|个人信息导出|隐私导出|数据主体访问|数据访问请求",
        r"identity\s+verification|requester|admin|API|permission|authorization|身份|请求者|管理员|权限|授权",
        r"profile|billing|orders?|messages?|attachments?|audit[- ]?visible\s+metadata|metadata|资料|账单|订单|消息|附件|元数据",
        r"tenant|cross[- ]?tenant|other\s+users?|user\s+exclusion|租户|跨租户|其他用户|用户排除",
        r"PII|secret|redact|redaction|privacy|脱敏|隐私|敏感",
        r"legal[- ]?hold|retention\s+exceptions?|retention|法务保留|保留例外|保留",
        r"async|export\s+job|retry|cancel|timeout|idempot|异步|导出任务|重试|取消|超时|幂等",
        r"encrypt|signed\s+URL|presigned|expiry|expires?|cleanup|delete\s+expired|加密|签名|过期|清理",
        r"download\s+audit|audit|notification|dedupe|rate\s+limit|monitoring|下载审计|审计|通知|去重|限流|监控",
        r"CSV[- ]?only|download[- ]?button[- ]?only|dashboard[- ]?ready|export\s+ready|只有.*CSV|下载按钮|看板",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def is_data_lifecycle_deletion_retention_task(task: str) -> bool:
    text = str(task or "")
    if is_data_residency_task(text) or is_audit_log_integrity_retention_task(text) or is_dsar_data_export_task(text):
        return False
    if not re.search(
        r"delete|deletion|erase|erasure|right[- ]?to[- ]?be[- ]?forgotten|GDPR|tombstone|legal[- ]?hold|backup\s+expiry|search[- ]?index\s+purge|cache\s+purge|analytics\s+anonymization|export\s+suppression|数据删除|删除|擦除|遗忘权|法务保留|备份过期|搜索.*清理|缓存.*清理|匿名化|导出.*抑制",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"account\s+deletion|delete|deletion|erase|erasure|tombstone|soft[- ]?delete|数据删除|删除|擦除|墓碑|软删除",
        r"retention|retention\s+exception|billing[- ]?record|legal[- ]?hold|backup\s+expiry|expired\s+backup|保留|例外|账单记录|法务保留|备份过期",
        r"search[- ]?index\s+purge|cache\s+purge|purge|analytics\s+anonymization|anonymi[sz]ation|export\s+suppression|搜索.*清理|缓存.*清理|匿名化|导出.*抑制",
        r"tenant\s+isolation|cross[- ]?tenant|permission|audit\s+trail|audit[- ]?log|monitoring|alert|租户隔离|跨租户|权限|审计|监控|告警",
        r"UI\s+delete|delete\s+button|happy[- ]?path|soft[- ]?delete|docs[- ]?only|UI.*删除|按钮|单一正向|文档",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 3

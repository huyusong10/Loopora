from __future__ import annotations

import re

from loopora.executor_alignment_task_predicates_data_cross_domain import (
    is_authorization_policy_task,
    is_data_residency_task,
    is_kyc_aml_screening_task,
    is_metric_reporting_reconciliation_task,
    is_support_impersonation_task,
)


def is_backup_restore_recovery_task(task: str) -> bool:
    text = str(task or "")
    if not re.search(
        r"restore|recover|disaster[- ]?recovery|PITR|point[- ]?in[- ]?time|RPO|RTO|恢复|灾备|灾难恢复|时间点恢复",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"backup|restore|disaster[- ]?recovery|PITR|point[- ]?in[- ]?time|RPO|RTO|备份|恢复|灾备|灾难恢复|时间点恢复",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"restore[- ]?drill|cross[- ]?region|snapshot|retention|legal[- ]?hold|checksum|row[- ]?count|smoke|encryption[- ]?key|audit|monitoring|备份任务|快照|恢复演练|保留|法务保留|校验和|行数|冒烟|密钥|审计|监控",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"backup|restore|disaster[- ]?recovery|PITR|point[- ]?in[- ]?time|RPO|RTO|备份|恢复|灾备|灾难恢复|时间点恢复",
        r"nightly|snapshot|cross[- ]?region|replication\s+lag|复制延迟|快照|跨区",
        r"restore[- ]?drill|isolated|tenant\s+restore|full\s+database|schema\s+migration|恢复演练|隔离|租户恢复|全量库|schema\s*migration",
        r"checksum|row[- ]?count|application\s+smoke|integrity|校验和|行数|冒烟|完整性",
        r"retention|legal[- ]?hold|expired\s+backup|过期|保留|法务保留",
        r"encryption[- ]?key|key\s+access|permission|operator|restore\s+permission|KMS|密钥|权限|操作员",
        r"audit|backup\s+id|snapshot\s+id|restore\s+run|failure\s+reason|monitoring|alert|审计|监控|告警|失败原因",
        r"backup[- ]?job[- ]?green|snapshot\s+file|dashboard\s+green|备份任务成功|备份作业成功|快照文件|看板绿色",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 4


def is_audit_log_integrity_retention_task(task: str) -> bool:
    text = str(task or "")
    if (
        is_data_residency_task(text)
        or is_metric_reporting_reconciliation_task(text)
        or is_support_impersonation_task(text)
        or is_kyc_aml_screening_task(text)
        or is_authorization_policy_task(text)
    ):
        return False
    if re.search(
        r"GDPR|account\s+deletion|delete|deletion|erase|erasure|right[- ]?to[- ]?be[- ]?forgotten|search[- ]?index\s+purge|cache\s+purge|analytics\s+anonymization|export\s+suppression|数据删除|删除|擦除|遗忘权|搜索.*清理|缓存.*清理|匿名化|导出.*抑制",
        text,
        re.IGNORECASE,
    ) and not re.search(
        r"audit[- ]?log\s+integrity|audit\s+trail\s+integrity|append[- ]?only|tamper|hash[- ]?chain|WORM|immutable|sequence\s+gap|logging\s+failure|stale\s+exporter|不可篡改|防篡改|哈希链|序列缺口|日志失败|导出滞后",
        text,
        re.IGNORECASE,
    ):
        return False
    if re.search(
        r"audit[- ]?log\s+integrity|audit\s+trail\s+integrity|compliance\s+audit|审计日志.*完整性|合规审计",
        text,
        re.IGNORECASE,
    ) and re.search(
        r"contract[- ]?first|parallel|retention\s+direction|Audit\s+Contract\s+Inspector|Audit\s+Trail\s+Builder|Audit\s+Integrity\s+Inspector|Retention\s+Export\s+Inspector|合约优先|并行|留存",
        text,
        re.IGNORECASE,
    ):
        return True
    if not re.search(
        r"audit\s+(?:trail|log)|compliance\s+audit|audit[- ]?log\s+integrity|审计日志|审计链路|合规审计",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"append[- ]?only|tamper|hash[- ]?chain|WORM|immutable|retention|legal[- ]?hold|SIEM|export|sequence\s+gap|logging\s+failure|stale\s+exporter|追加|不可篡改|防篡改|哈希链|保留|法务保留|导出|序列|漏记|告警",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"audit\s+(?:trail|log)|compliance\s+audit|审计日志|审计链路|合规审计",
        r"create/update/delete|permission\s+change|failed\s+attempt|敏感操作|权限变更|失败尝试|增删改",
        r"actor|subject|tenant|request\s+id|IP|user\s+agent|before/after|reason\s+code|timestamp|sequence|租户|请求|原因码|时间戳|序列",
        r"PII|token|redact|redaction|脱敏|敏感",
        r"append[- ]?only|immutable|tamper|hash[- ]?chain|WORM|不可变|不可篡改|防篡改|哈希链|追加",
        r"clock\s+skew|monotonic|单调|时钟偏移",
        r"retention|legal[- ]?hold|保留|法务保留",
        r"SIEM|export|reconciliation|导出|对账",
        r"access\s+control|tenant\s+isolation|cross[- ]?tenant|访问控制|租户隔离|跨租户",
        r"retry|duplicate|no[- ]?miss|no[- ]?duplicate|idempot|重试|重复|漏记|幂等",
        r"logging\s+failure|stale\s+exporter|sequence\s+gap|monitoring|alert|日志失败|导出滞后|序列缺口|监控|告警",
        r"database\s+row|console\s+log|UI\s+history|reviewability|follow[- ]?up|数据库表|控制台|历史|可审计|后续",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 4

from __future__ import annotations

import re

from loopora.executor_alignment_task_predicates_data_cross_domain import (
    is_analytics_experiment_instrumentation_task,
)


def is_database_schema_migration_task(task: str) -> bool:
    text = str(task or "")
    if is_cdc_replication_consistency_task(text):
        return False
    if not re.search(
        r"database|schema\s+migration|DB\s+migration|data\s+model|table|normalized|migration/backfill|数据库|数据表|表结构|数据模型|迁移|回填",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"backfill|dual[- ]?write|old/new\s+reader|reader\s+compat|rollback|expand[- ]?contract|"
        r"data\s+consistency|mixed\s+migrated|schema\s+semantics|normalized\s+tables?|回填|双写|旧读|新读|读兼容|回滚|混合迁移",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"schema\s+migration|old/new\s+schema|schema\s+semantics|normalized|plan_entitlements|table\s+changes?|表结构|新旧.*schema|规范化",
        r"expand[- ]?contract|dual[- ]?write|read[- ]?after[- ]?write|old/new\s+reader|reader\s+compat|compatibility\s+adapter|双写|读后写|旧读|新读|兼容",
        r"backfill|cursor|idempotenc|retry|failed\s+batch|partial\s+failure|pause/resume|resume|回填|游标|幂等|重试|失败批次|暂停|恢复",
        r"tenant\s+isolation|mixed\s+migrated|unmigrated|cross[- ]?tenant|租户隔离|混合迁移|未迁移|跨租户",
        r"data\s+consistency|consistency\s+checks?|invoice|billing|reconciliation|no[- ]?drift|ledger|发票|账单|对账|漂移",
        r"rollback|old\s+readers?|cleanup|migration\s+rollback|回滚|旧读|清理",
        r"monitoring|progress|lag|alert|监控|进度|滞后|告警",
        r"table[- ]?only|one[- ]?time\s+backfill|happy[- ]?path|docs[- ]?only|schema[- ]?only|只建表|单次回填|文档",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 4


def is_cdc_replication_consistency_task(task: str) -> bool:
    text = str(task or "")
    if is_analytics_experiment_instrumentation_task(text):
        return False
    if not re.search(
        r"\b(?:CDC|change[- ]?data[- ]?capture|logical[- ]?replication|streaming[- ]?replication|"
        r"replication|replica|replicate|read[- ]?model|warehouse|sync[- ]?connector|Debezium)\b|"
        r"变更数据捕获|逻辑复制|流式复制|复制|同步|数仓|读模型",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"ordering|out[- ]?of[- ]?order|replay|checkpoint|lag|schema\s+evolution|schema[- ]?version|"
        r"snapshot|backfill|tombstone|delete|tenant\s+(?:filter|isolation)|reconciliation|"
        r"row\s+count|checksum|event\s+count|target\s+drift|connector\s+failure|"
        r"顺序|乱序|回放|检查点|延迟|schema\s*演进|快照|回填|墓碑|删除|租户|对账|漂移|恢复",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"source\s+event\s+schema|event\s+schema|source\s+table|源事件|事件\s*schema|源表",
        r"ordering|out[- ]?of[- ]?order|deterministic\s+order|顺序|乱序",
        r"replay|checkpoint|watermark|LSN|idempot(?:ent|ency)|duplicate|回放|检查点|水位|幂等|重复",
        r"lag|SLO|alert|stale\s+checkpoint|monitoring|延迟|告警|监控|滞后",
        r"schema\s+evolution|schema[- ]?version|column\s+rename|additive\s+column|schema\s*演进|版本|列重命名",
        r"snapshot|backfill|concurrent\s+writes?|快照|回填|并发写",
        r"delete|tombstone|墓碑|删除",
        r"tenant\s+(?:filter|isolation)|cross[- ]?tenant|tenant\s+negative|租户|跨租户",
        r"warehouse|read[- ]?model|reconciliation|row\s+count|checksum|event\s+count|aggregate|target\s+drift|数仓|读模型|对账|漂移",
        r"connector\s+failure|DLQ|poison\s+event|sync\s+failure|restart|recovery|连接器|死信|毒丸|失败|恢复",
        r"green\s+sync\s+job|sync\s+job\s+green|row[- ]?count\s+sample|dashboard\s+(?:latest|shows)|dashboard.*latest|绿色|抽样|看板|latest",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 4

from __future__ import annotations

import re


def is_database_schema_migration_task(task: str) -> bool:
    from loopora.executor_alignment_task_predicates_data import is_database_schema_migration_task as predicate

    return predicate(task)


def is_feature_flag_rollout_task(task: str) -> bool:
    text = str(task or "")
    if is_database_schema_migration_task(text):
        return False
    if not re.search(
        r"feature[- ]?flag|release[- ]?flag|rollout|canary|灰度|功能开关|特性开关|发布开关",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"default[- ]?off|cohort|targeting|percentage|percent[- ]?rollout|sticky[- ]?assignment|exposure|kill[- ]?switch|rollback|roll\s+back|canary|默认关闭|分群|百分比|稳定分配|曝光|熔断|回滚|灰度",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"feature[- ]?flag|release[- ]?flag|rollout|canary|功能开关|特性开关|发布开关|灰度",
        r"default[- ]?off|cohort|targeting|percentage|percent[- ]?rollout|默认关闭|分群|百分比",
        r"sticky[- ]?assignment|exposure|session\s+consistency|session|稳定分配|曝光|会话一致",
        r"kill[- ]?switch|rollback|roll\s+back|cleanup|dirty\s+state|熔断|回滚|脏状态",
        r"monitoring|alerts?|error[- ]?rate|conversion|payment\s+conversion|监控|告警|错误率|转化率",
        r"audit|flag\s+change|who\s+changed|local[- ]?only|local\s+flag|UI\s+toggle|docs[- ]?only|审计|本地|按钮|文档",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 4


def is_incident_root_cause_task(task: str) -> bool:
    text = str(task or "")
    if not re.search(r"incident|outage|production\s+bug|duplicate\s+charge|root[- ]?cause|RCA|事故|故障|重复扣款|根因", text, re.IGNORECASE):
        return False
    markers = (
        r"incident|outage|production\s+bug|事故|故障|duplicate\s+charge|重复扣款",
        r"root[- ]?cause|RCA|根因",
        r"repro|reproduce|trigger\s+condition|failure\s+mode|复现|触发条件",
        r"regression|monitoring|alert|recurrence|rollback|release|回归|监控|告警|复发|回滚|发布",
        r"patch|repair|fix|修复|补丁",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 3

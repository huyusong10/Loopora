from __future__ import annotations

import re

from loopora.executor_alignment_task_predicates_commercial_cross_domain import (
    is_analytics_experiment_instrumentation_task,
    is_cdc_replication_consistency_task,
)


def is_metric_reporting_reconciliation_task(task: str) -> bool:
    text = str(task or "")
    if is_analytics_experiment_instrumentation_task(text) or is_cdc_replication_consistency_task(text):
        return False
    if not re.search(
        r"\b(?:MRR|ARR|NRR|net\s+revenue\s+retention|revenue\s+report(?:ing)?|revenue\s+dashboard|"
        r"MRR\s+dashboard|metric\s+(?:definition|contract|reconciliation|reporting)|metrics?\s+dashboard|"
        r"reporting\s+dashboard|churn|expansion|contraction)\b|收入报表|收入看板|指标口径|指标对账|指标报表|月经常性收入",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"metric\s+definition|trial|coupon|discount|refund|proration|downgrade|upgrade|paused\s+subscription|"
        r"currency|FX|cutoff|timezone|ledger|invoice|provider\s+reconciliation|locked[- ]?month|backfill|"
        r"permission|segment|export|audit|chart[- ]?only|CSV[- ]?only|口径|试用|优惠券|折扣|退款|按比例|降级|升级|暂停|"
        r"币种|汇率|截断|时区|账本|发票|对账|锁账|回填|权限|分段|导出|审计|图表",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"\b(?:MRR|ARR|NRR|net\s+revenue\s+retention|churn|expansion|contraction)\b|月经常性收入|收入留存|流失|扩张|收缩",
        r"metric\s+definition|metric\s+version|definition\s+version|指标口径|指标版本|口径版本",
        r"trial|coupon|discount|refund|proration|downgrade|upgrade|paused\s+subscription|试用|优惠券|折扣|退款|按比例|降级|升级|暂停",
        r"currency|FX|foreign\s+exchange|exchange\s+rate|币种|汇率|外汇",
        r"month\s+cutoff|cutoff|timezone|月.*截断|时区",
        r"billing\s+ledger|ledger|invoice|subscription\s+provider|provider\s+reconciliation|账本|发票|订阅供应商|对账",
        r"historical\s+backfill|backfill|locked[- ]?month|locked\s+months?|锁账|历史回填|回填",
        r"permission|revenue\s+segment|segment\s+permission|tenant|权限|收入分段|分段|租户",
        r"export|CSV|dashboard/export|导出|CSV",
        r"audit|backfill\s+run|metric\s+definition\s+version|审计|回填运行",
        r"chart[- ]?only|charts?\s+showing|CSV[- ]?only|provider[- ]?total[- ]?only|dashboard\s+matches|图表|只.*CSV|只.*provider|看板.*总数",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5

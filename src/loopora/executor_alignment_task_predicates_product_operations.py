from __future__ import annotations

import re

from loopora.executor_alignment_task_predicates_product_cross_domain import is_usage_quota_metering_task


def is_analytics_experiment_instrumentation_task(task: str) -> bool:
    text = str(task or "")
    if not re.search(
        r"analytics|telemetry|instrumentation|tracking|analytics\s+events?|funnel|clickstream|Segment|埋点|漏斗",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"\bA/B\b|\bab[- ]?test\b|\bsplit[- ]?test\b|\bexperiment(?:s)?\b|\bassignment(?:s)?\b|\bexposure(?:s)?\b|\bvariant(?:s)?\b|\bholdout(?:s)?\b|\breassignment\b|实验|分流|曝光|变体|对照组|重分配",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"event[- ]?schema|event\s+payload|versioned|schema\s+version|app_open|signup|onboarding|paywall|事件.*schema|版本",
        r"anonymous|logged[- ]?in|identity\s+merge|double\s+count|user\s+id|匿名|登录|身份.*合并|重复计数",
        r"consent|PII|privacy|redact|tracking\s+denial|同意|隐私|脱敏|拒绝.*跟踪",
        r"duplicate|dedupe|retry|refresh|offline\s+replay|SDK\s+callback|idempot|重复|去重|重试|离线|回放|幂等",
        r"\bexperiment(?:s)?\b|\bassignment(?:s)?\b|\bexposure(?:s)?\b|\bvariant(?:s)?\b|\bholdout(?:s)?\b|\breassignment\b|restart|device|实验|分流|曝光|变体|对照|重分配|重启|设备",
        r"warehouse|dashboard|raw[- ]?event|assignment\s+log|reconciliation|Segment|provider\s+accepted|数仓|仪表盘|原始事件|对账|供应商",
        r"monitoring|drift|missing\s+exposure|duplicate\s+spike|schema\s+mismatch|alert|监控|漂移|缺失曝光|峰值|不匹配|告警",
        r"button|click|console\.?log|mock\s+analytics|mock\s+call|follow[- ]?up|按钮|控制台|模拟|后续",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def is_concurrency_conflict_resolution_task(task: str) -> bool:
    text = str(task or "")
    if is_inventory_reservation_consistency_task(text) or is_usage_quota_metering_task(text):
        return False
    if not re.search(
        r"collaborative\s+(?:document|editing|editor)|collab(?:oration)?\s+(?:document|editing)|document\s+editing|same[- ]paragraph|协作文档|协同编辑|协作编辑|同一段|文档编辑",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"conflict|concurrent|optimistic\s+lock|version|lost[- ]update|silent\s+overwrite|last[- ]write[- ]wins|offline\s+replay|冲突|并发|乐观锁|版本|覆盖|离线|重放",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"two\s+users?|same[- ]paragraph|concurrent\s+edit|双用户|两个用户|同一段|并发编辑",
        r"silent\s+overwrite|lost[- ]update|last[- ]write[- ]wins|静默覆盖|覆盖|最后写入",
        r"version\s+conflict|optimistic\s+lock|base_version|版本冲突|乐观锁|版本",
        r"safe\s+merge|merge\s+outcome|reject|both\s+sides|保留两边|安全\s*merge|合并|拒绝",
        r"offline\s+(?:edit|queue|replay)|reconnect|idempot(?:ent|ency)|retry|离线|重连|幂等|重试",
        r"permission|unauthorized|lower[- ]permission|revocation|权限|无权限|低权限|撤销",
        r"audit|resolved_by|base_version|merge\s+outcome|审计",
        r"single[- ]user[- ]save|WebSocket[- ]only|happy[- ]path|单人保存|单用户|happy path",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 4


def is_inventory_reservation_consistency_task(task: str) -> bool:
    text = str(task or "")
    if re.search(r"\b(?:stock|inventory|SKU)\s+report\b|库存报表|库存报告", text, re.IGNORECASE) and not re.search(
        r"reservation|reserve|oversell|checkout|hold|预留|超卖|下单",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"inventory\s+reservation|reservation\s+hold|stock\s+reservation|oversell|over[- ]?sell|same[- ]?SKU|SKU|checkout\s+inventory|库存预留|库存|预留|超卖|售罄|低库存",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"checkout|payment\s+webhook|payment|refund|cancellation|failed\s+payment|TTL|expiry|release|ledger|reconciliation|concurrent|race|idempot|retry|sold[- ]?out|low[- ]?stock|audit|monitoring|下单|支付|退款|取消|失败支付|到期|释放|账本|对账|并发|竞态|幂等|重试|售罄|低库存|审计|监控",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"inventory\s+reservation|reservation\s+hold|stock\s+reservation|SKU|checkout\s+inventory|库存预留|库存|预留",
        r"oversell|over[- ]?sell|same[- ]?SKU|cannot\s+oversell|防超卖|超卖",
        r"concurrent|race\s+condition|lock|conflict|same[- ]?SKU\s+checkout|并发|竞态|冲突|锁",
        r"TTL|expiry|expires?|hold\s+expiry|release|释放|到期|过期",
        r"payment\s+webhook|webhook|payment\s+success|confirm|decrement|支付|扣减|确认",
        r"cancellation|cancel|refund|failed\s+payment|release\s+reason|取消|退款|失败支付|释放原因",
        r"idempot(?:ent|ency)|retry|duplicate\s+webhook|replay|幂等|重试|重复|重放",
        r"ledger|reconciliation|reconcile|order\s+rows?|provider|账本|对账|订单|供应商",
        r"sold[- ]?out|low[- ]?stock|user\s+state|售罄|低库存|用户状态",
        r"audit|reservation\s+id|hold\s+expiry|monitoring|alert|审计|预留\s*id|监控|告警",
        r"happy[- ]?path|UI\s+stock|DB\s+decrement|database\s+decrement|follow[- ]?up|单个用户|界面|数据库|后续",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5

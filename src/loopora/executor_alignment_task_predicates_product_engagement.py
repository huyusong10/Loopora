from __future__ import annotations

import re

from loopora.executor_alignment_task_predicates_product_cross_domain import (
    is_dispute_chargeback_lifecycle_task,
    is_dsar_data_export_task,
    is_subscription_entitlement_billing_task,
    is_support_impersonation_task,
)
from loopora.executor_alignment_task_predicates_product_operations import is_analytics_experiment_instrumentation_task


def is_schedule_phase_task(task: str) -> bool:
    text = str(task or "")
    if re.search(
        r"usage\s+meter(?:ing|ed)?|usage\s+event|quota\s+(?:enforcement|limit|window)|plan\s+(?:quota|limit)|api\s+usage|usage\s+ledger|额度|配额|限额",
        text,
        re.IGNORECASE,
    ) and re.search(
        r"concurrent|duplicate|idempot|plan\s+upgrade|plan\s+downgrade|billing\s+period|grace\s+limit|hard\s+limit|over[- ]?limit|invoice|subscription\s+provider|并发|重复|幂等|套餐|计费周期|宽限|硬限制|超限|发票|订阅",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(r"weekly\s+digest|digest|schedule|scheduler|cron|timezone|DST|定时|周一|夏令时", text, re.IGNORECASE):
        return False
    phase_markers = (
        r"timezone|时区",
        r"\bDST\b|daylight|夏令时",
        r"missed[- ]?run|catch[- ]?up|错过执行|补偿|补一次",
        r"retry|provider\s+replay|duplicate|idempotenc|重试|重复|幂等",
        r"subscription|unsubscribe|disabled|tenant|locale|退订|禁用|租户",
        r"audit|scheduled_at|due_at|sent_at|skipped_reason|job_run_id|审计",
        r"monitoring|alert|drift|backlog|provider\s+failure|监控|告警|漂移|积压",
        r"cron[- ]?only|local[- ]?trigger|UTC[- ]?only|single[- ]?timezone|本地触发|只测|一个时区",
    )
    return sum(1 for pattern in phase_markers if re.search(pattern, text, re.IGNORECASE)) >= 4


def is_support_ticket_sla_task(task: str) -> bool:
    text = str(task or "")
    if is_support_impersonation_task(text):
        return False
    if not re.search(
        r"support\s+ticket|ticket\s+triage|ticket\s+queue|ticket\s+lifecycle|SLA\s+escalation|"
        r"客服工单|工单|客服.*SLA|SLA.*升级|工单.*升级|客服.*队列",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"SLA|escalat(?:e|ion)?|breach|queue|triage|dedupe|deduplicat|merge|email|API|claim|assign|priority|status|agent|manager|tenant|PII|redact|audit|notification|"
        r"升级|违约|队列|分诊|去重|合并|邮件|领取|分配|优先级|状态|坐席|经理|租户|脱敏|审计|通知",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"support\s+ticket|ticket\s+triage|ticket\s+queue|ticket\s+lifecycle|客服工单|工单|客服",
        r"email|API|import|ingest|dedupe|deduplicat|merge|邮件|导入|接入|去重|合并",
        r"queue|enqueue|dequeue|claim|assign|priority|status|state\s+machine|lifecycle|队列|入队|领取|分配|优先级|状态|状态机|生命周期",
        r"SLA|breach|escalat(?:e|ion)?|clock|timer|pause|resume|SLO|违约|升级|计时|暂停|恢复",
        r"agent|manager|queue\s+health|backlog|ownership|owner|负责人|坐席|经理|队列健康|积压",
        r"permission|authorization|RBAC|ACL|role|unauthorized|权限|授权|角色|无权限",
        r"tenant|cross[- ]?tenant|租户|跨租户",
        r"notification|notify|email|message|duplicate\s+notification|suppress|通知|消息|重复通知|抑制",
        r"audit|notes?|audit\s+note|trace|审计|备注|追踪",
        r"PII|redact|redaction|privacy|mask|脱敏|隐私|掩码",
        r"Kanban|dashboard[- ]?only|manager\s+dashboard|queued/open|status[- ]?only|看板|状态",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def is_notification_subscription_deliverability_task(task: str) -> bool:
    text = str(task or "")
    if (
        is_schedule_phase_task(text)
        or is_analytics_experiment_instrumentation_task(text)
        or is_dispute_chargeback_lifecycle_task(text)
        or is_support_ticket_sla_task(text)
        or is_dsar_data_export_task(text)
        or is_subscription_entitlement_billing_task(text)
    ):
        return False
    if re.search(
        r"notification\s+subscription[- ]?deliverability|subscription[- ]?deliverability|notification\s+deliverability",
        text,
        re.IGNORECASE,
    ) and re.search(
        r"contract[- ]?first|parallel|evidence\s+direction|Notification\s+Contract\s+Inspector|Deliverability\s+Evidence\s+Inspector|Template\s+Privacy\s+Inspector|合约优先|并行",
        text,
        re.IGNORECASE,
    ):
        return True
    if not re.search(
        r"notification|email|campaign|lifecycle\s+campaign|deliverability|subscription\s+preferences?|preference\s+center|unsubscribe|suppression\s+list|bounce|complaint|通知|邮件|退订|订阅|偏好|投递",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"subscribed|eligible|unsubscribe|preference|suppression|bounce|complaint|dropped|disabled\s+user|locale|template|PII|token|provider|webhook|delivered|delivery\s+audit|duplicate|retry|DLQ|manual\s+replay|monitoring|订阅|退订|偏好|抑制|退信|投诉|模板|脱敏|投递|重复|重试|监控",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"notification|email|campaign|lifecycle\s+campaign|message|通知|邮件|消息",
        r"subscription|subscribed|eligible|preference\s+center|preference|unsubscribe|订阅|偏好|退订",
        r"suppression\s+list|suppression|bounce|complaint|dropped|drop|抑制|退信|投诉|丢弃",
        r"provider|accepted|delivered|delivery\s+event|webhook|replay|signature|供应商|已接收|已投递|投递事件|重放|签名",
        r"duplicate|idempot(?:ent|ency)|retry|backoff|rate\s+limit|DLQ|dead[- ]?letter|manual\s+replay|重复|幂等|重试|速率|死信|手动重放",
        r"locale|i18n|template|variable|English|Chinese|fallback|中文|英文|模板|变量|回退",
        r"PII|token|redact|redaction|privacy|leak|脱敏|隐私|泄露",
        r"disabled\s+user|tenant|cross[- ]?tenant|禁用用户|租户|跨租户",
        r"audit|reason\s+code|reconciliation|monitoring|alert|审计|原因码|对账|监控|告警",
        r"one\s+test\s+email|test\s+email|provider\s+accepted|UI\s+toggle|happy[- ]?path|docs[- ]?only|follow[- ]?up|测试邮件|只.*provider|UI|文档|后续",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5

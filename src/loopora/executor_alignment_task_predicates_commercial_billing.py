from __future__ import annotations

import re

from loopora.executor_alignment_task_predicates_commercial_cross_domain import (
    is_inventory_reservation_consistency_task,
    is_notification_subscription_deliverability_task,
)


def is_usage_quota_metering_task(task: str) -> bool:
    text = str(task or "")
    if (
        is_inventory_reservation_consistency_task(text)
        or is_notification_subscription_deliverability_task(text)
        or is_subscription_entitlement_billing_task(text)
    ):
        return False
    if not re.search(
        r"usage\s+meter(?:ing|ed)?|usage\s+event|metered\s+usage|quota\s+(?:enforcement|limit|window)|plan\s+(?:quota|limit)|rate[- ]?limit|api\s+usage|usage\s+ledger|usage\s+limit|计量|用量|额度|配额|限额",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"concurrent|duplicate|retry|idempot|plan\s+upgrade|plan\s+downgrade|billing\s+period|reset\s+timezone|grace\s+limit|hard\s+limit|over[- ]?limit|invoice|subscription\s+provider|audit|monitoring|并发|重复|重试|幂等|套餐|计费周期|重置|宽限|硬限制|超限|发票|订阅|审计|监控",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"usage\s+meter(?:ing|ed)?|usage\s+event|metered\s+usage|api\s+usage|usage\s+ledger|计量|用量",
        r"quota\s+(?:enforcement|limit|window)|plan\s+(?:quota|limit)|usage\s+limit|rate[- ]?limit|quota|额度|配额|限额",
        r"concurrent|same\s+org|race|parallel\s+calls|并发|同一\s*org|同一组织",
        r"duplicate\s+usage\s+events?|idempot(?:ent|ency)|retry|幂等|重复|重试",
        r"plan\s+upgrade|plan\s+downgrade|plan\s+change|套餐|升降级|变更",
        r"billing\s+period|reset\s+timezone|quota\s+window|reset\s+run|计费周期|重置|窗口|时区",
        r"grace\s+limit|hard\s+limit|over[- ]?limit|429|permission[- ]?safe|宽限|硬限制|超限|权限",
        r"ledger|invoice|subscription\s+provider|reconciliation|对账|账本|发票|订阅",
        r"low[- ]?quota|exhaust(?:ed|ion)?|alert|monitoring|低余量|用尽|告警|监控",
        r"audit|usage\s+event\s+id|metering\s+version|actor|org|plan|审计|版本",
        r"dashboard|single\s+429|cron\s+reset|provider\s+total|follow[- ]?up|看板|单次|定时|后续",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def is_subscription_entitlement_billing_task(task: str) -> bool:
    text = str(task or "")
    has_entitlement_anchor = bool(
        re.search(
            r"entitlement(?:s)?|entitlement[- ]?(?:sync|state|propagation)|feature[- ]?access|"
            r"seat[- ]?access|team[- ]?member|权益|权益生效|权益同步|功能权限|团队成员",
            text,
            re.IGNORECASE,
        )
    )
    has_plan_change_execution_anchor = bool(
        re.search(
            r"proration|prorated|credit[- ]?memo|按比例|贷项|credit\s*memo",
            text,
            re.IGNORECASE,
        )
        and re.search(
            r"provider[- ]?checkout|checkout|webhook|duplicate[- ]?click|"
            r"upgrade[- ]?immediate|downgrade[- ]?(?:next[- ]?cycle|delayed|at[- ]?period[- ]?end)|"
            r"effective[- ]?(?:now|next[- ]?cycle)|重复点击|立即生效|下个周期生效|降级延迟|周期结束生效",
            text,
            re.IGNORECASE,
        )
    )
    if not (has_entitlement_anchor or has_plan_change_execution_anchor):
        return False
    if not re.search(
        r"subscription[- ]?(?:plan|billing|change|upgrade|downgrade)|plan[- ]?(?:upgrade|downgrade|change)|"
        r"entitlement(?:s)?|proration|prorated|credit[- ]?memo|trial|grace[- ]?period|"
        r"订阅套餐|套餐升级|套餐降级|套餐变更|订阅升级|订阅降级|权益|权益生效|proration|按比例|credit\s*memo|试用期|宽限期",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"invoice|ledger|provider|checkout|webhook|idempot|duplicate|billing[- ]?period|quota|permission|tenant|audit|rollback|monitoring|"
        r"发票|账本|供应商|provider|checkout|webhook|幂等|重复|计费周期|配额|权限|租户|审计|回滚|监控",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"subscription[- ]?(?:plan|billing|change|upgrade|downgrade)|plan[- ]?(?:upgrade|downgrade|change)|订阅套餐|套餐升级|套餐降级|套餐变更|订阅升级|订阅降级",
        r"entitlement(?:s)?|feature[- ]?access|seat[- ]?access|team[- ]?member|权益|功能权限|团队成员",
        r"proration|prorated|credit[- ]?memo|invoice|ledger|按比例|credit\s*memo|贷项|发票|账本",
        r"trial|grace[- ]?period|billing[- ]?period|试用期|宽限期|计费周期",
        r"provider|checkout|webhook|replay|out[- ]?of[- ]?order|供应商|provider|checkout|webhook|重放|乱序",
        r"duplicate[- ]?click|idempot|concurrent|重复点击|幂等|并发",
        r"quota|historical[- ]?usage|usage\s+history|历史用量|配额",
        r"permission|tenant|cross[- ]?tenant|权限|租户|跨租户",
        r"audit|rollback|monitoring|审计|回滚|监控",
        r"button[- ]?only|checkout[- ]?success|provider[- ]?total|happy[- ]?path|只做按钮|按钮能点|只信\s*provider|只信\s*checkout",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def is_tax_calculation_compliance_task(task: str) -> bool:
    text = str(task or "")
    if is_subscription_entitlement_billing_task(text):
        return False
    if re.search(r"tax\s+report|tax\s+export|monthly\s+tax\s+totals|CSV|报税报表|税务报表|税务导出", text, re.IGNORECASE) and not re.search(
        r"checkout|calculation|calculate|VAT|GST|sales\s+tax|taxability|exemption|rounding|refund|invoice|结账|计算|免税|舍入|退款|发票",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"tax\s+calculation|sales\s+tax|\bVAT\b|\bGST\b|taxability|taxable\s+nexus|checkout\s+tax|tax\s+provider|税务计算|税率|增值税|消费税|销售税|免税",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"jurisdiction|nexus|shipping\s+address|billing\s+address|digital\s+goods|physical\s+goods|exemption|reverse\s+charge|inclusive|exclusive|rounding|refund|credit\s+memo|invoice|receipt|provider|effective\s+date|timezone|audit|reconciliation|辖区|地址|免税|反向征收|含税|不含税|舍入|退款|贷项|发票|供应商|生效|时区|审计|对账",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"tax\s+calculation|checkout\s+tax|sales\s+tax|\bVAT\b|\bGST\b|税务计算|税率|增值税|消费税|销售税",
        r"taxable\s+nexus|nexus|US\s+state|EU\s+VAT|jurisdiction|辖区|州|欧盟",
        r"shipping\s+address|billing\s+address|address\s+jurisdiction|收货地址|账单地址|地址",
        r"digital\s+goods|physical\s+goods|product\s+tax(?:ability|able)|taxability|数字商品|实物商品|商品税",
        r"exemption|certificate|B2B\s+reverse\s+charge|reverse\s+charge|免税|证书|反向征收",
        r"inclusive|exclusive|display|含税|不含税|展示",
        r"discount|coupon|shipping\s+fee|rounding|currency|折扣|优惠券|运费|舍入|币种",
        r"refund|credit\s+memo|reversal|退款|贷项|冲销|反转",
        r"invoice|receipt|line\s+item|ledger|reconciliation|provider\s+report|发票|收据|账本|对账|供应商报告",
        r"provider|sandbox|fallback|retry|idempot(?:ent|ency)|request\s+id|供应商|沙箱|降级|重试|幂等|请求",
        r"rate\s+(?:change|effective|version|source)|effective\s+date|timezone|rate\s+version|生效|时区|版本|来源",
        r"audit|jurisdiction|rate\s+source|exemption\s+id|provider\s+request\s+id|monitoring|审计|监控",
        r"one\s+(?:checkout\s+)?tax\s+number|hardcoded\s+rate|provider\s+quote\s+only|UI\s+total|follow[- ]?up|一个.*税|硬编码|只.*provider|只.*UI|后续",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5

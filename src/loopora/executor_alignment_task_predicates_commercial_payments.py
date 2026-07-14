from __future__ import annotations

import re

from loopora.executor_alignment_task_predicates_commercial_billing import (
    is_subscription_entitlement_billing_task,
    is_tax_calculation_compliance_task,
    is_usage_quota_metering_task,
)
from loopora.executor_alignment_task_predicates_commercial_cross_domain import (
    is_cdc_replication_consistency_task,
    is_identity_sso_task,
    is_inventory_reservation_consistency_task,
    is_kyc_aml_screening_task,
    is_notification_subscription_deliverability_task,
)
from loopora.executor_alignment_task_predicates_commercial_metrics import is_metric_reporting_reconciliation_task


def is_dispute_chargeback_lifecycle_task(task: str) -> bool:
    text = str(task or "")
    if is_metric_reporting_reconciliation_task(text) or is_inventory_reservation_consistency_task(text):
        return False
    if re.search(
        r"\b(?:KYC|KYB|AML)\b|sanctions?|PEP|watchlist|identity\s+verification|business\s+registry|"
        r"beneficial\s+owner|document\s+OCR|liveness|risk\s+score|manual\s+review|periodic\s+rescreen|"
        r"provider\s+sandbox\s+approved|身份核验|反洗钱|制裁筛查|受益所有人",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"dispute(?:\.created|\.updated|\.closed)?|chargeback|representment|retrieval\s+request|"
        r"issuer|acquirer|reason\s+code|win/loss|won/lost|partial\s+dispute|duplicate\s+dispute|"
        r"争议|拒付|调单|申诉举证|原因码",
        text,
        re.IGNORECASE,
    ):
        return False
    if re.search(
        r"seller\s+balance\s+ledger|seller[- ]?payout|marketplace[- ]?payout|payout[- ]?settlement|"
        r"double[- ]?payout|provider\s+transfer|bank\s+statement|卖家余额|重复打款",
        text,
        re.IGNORECASE,
    ) and not re.search(
        r"representment|retrieval\s+request|reason\s+code|win/loss|won/lost|partial\s+dispute|duplicate\s+dispute|"
        r"evidence\s+(?:package|submission)|调单|申诉举证|原因码",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"dispute(?:\.created|\.updated|\.closed)?|chargeback|争议|拒付",
        r"retrieval\s+request|representment|evidence\s+(?:package|submission)|deadline|调单|申诉举证|截止",
        r"issuer|acquirer|reason\s+code|win/loss|won/lost|partial\s+dispute|duplicate\s+dispute|原因码|部分争议|重复争议",
        r"refund\s+overlap|chargeback\s+overlap|order\s+fulfillment|退款.*重叠|履约",
        r"provider\s+dispute|webhook|signature|replay|out[- ]?of[- ]?order|供应商|重放|乱序",
        r"ledger|invoice|balance\s+adjustment|provisional\s+credit|provisional\s+debit|fee|账本|发票|余额调整|临时贷记|临时借记|费用",
        r"payout\s+hold|payout\s+release|hold/release|打款冻结|打款释放",
        r"customer\s+notification|merchant\s+response|SLA|notification\s+delivery|客户通知|商户响应",
        r"audit|monitoring|failed\s+dispute|stale\s+dispute|审计|监控|过期争议",
        r"dashboard\s+(?:won|lost)|provider\s+dispute\s+id|happy[- ]?path\s+close|UI\s+status|看.*won/lost|只保存",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def is_payout_settlement_reconciliation_task(task: str) -> bool:
    text = str(task or "")
    if is_inventory_reservation_consistency_task(text) or is_metric_reporting_reconciliation_task(text) or is_dispute_chargeback_lifecycle_task(text):
        return False
    if re.search(
        r"\b(?:KYB|AML)\b|sanctions?|PEP|watchlist|identity\s+verification|business\s+registry|"
        r"beneficial\s+owner|document\s+OCR|manual\s+review|rescreening|身份核验|反洗钱|制裁筛查|受益所有人",
        text,
        re.IGNORECASE,
    ):
        return False
    if re.search(
        r"Webhook\s+Contract\s+Inspector|payment\s+provider\s+webhook|webhook\s+ingestion|provider\s+event\s+schemas?|"
        r"signature\s+verification|timestamp\s+tolerance|replay\s+protection|dead[- ]?letter|DLQ|manual\s+replay|"
        r"checkout\.session|支付.*webhook|供应商事件",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"\b(?:marketplace[- ]?payout|seller[- ]?payout|merchant[- ]?payout|payout[- ]?settlement|"
        r"payout[- ]?batch|seller\s+balance|merchant\s+balance|provider\s+transfer|failed\s+payout|"
        r"double[- ]?payout|stuck\s+payout)\b|"
        r"打款|结算|卖家余额|商户余额|付款批次",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"seller\s+balance\s+ledger|ledger|captured|refunded|chargeback|platform\s+fee|tax|adjustment|"
        r"hold|reserve|negative\s+balance|batch\s+cutoff|timezone|currency|FX|provider\s+transfer|bank\s+account|"
        r"KYC\s+hold|failed\s+payout|retry|reversal|double[- ]?payout|payout\s+report|bank\s+statement|tenant|audit|monitoring|"
        r"账本|捕获|退款|拒付|费用|税|调整|冻结|准备金|负余额|批次|截断|时区|币种|转账|银行|失败|重试|冲销|重复打款|对账|租户|审计|监控",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"marketplace[- ]?payout|seller[- ]?payout|merchant[- ]?payout|payout[- ]?settlement|payout[- ]?batch|seller\s+balance|打款|结算|卖家余额",
        r"seller\s+balance\s+ledger|ledger|captured|refunded|chargeback|账本|捕获|退款|拒付",
        r"platform\s+fee|tax|adjustment|hold|reserve|negative\s+balance|费用|税|调整|冻结|准备金|负余额",
        r"batch\s+cutoff|timezone|currency|FX|rounding|批次|截断|时区|币种|舍入",
        r"provider\s+transfer|bank\s+account|payout\s+report|bank\s+statement|Stripe|Adyen|转账|银行|报告|对账单",
        r"KYC\s+hold|failed\s+payout|retry|reversal|idempot(?:ent|ency)|double[- ]?payout|失败|重试|冲销|幂等|重复打款",
        r"reconciliation|local\s+ledger|invoice|bank\s+statement|provider[- ]?bank|对账|本地账本|发票|银行",
        r"tenant|seller\s+access|cross[- ]?tenant|permission|租户|权限|跨租户",
        r"audit|payout\s+batch\s+id|ledger\s+entry\s+id|provider\s+transfer\s+id|failure\s+reason|审计|失败原因",
        r"monitoring|stuck\s+payout|failed\s+transfer|mismatch|alert|监控|告警|卡住|失败转账|不一致",
        r"dashboard\s+paid|test\s+payout|UI\s+balance|dashboard.*paid|一笔|余额减少",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def is_payment_webhook_ledger_task(task: str) -> bool:
    text = str(task or "")
    if (
        is_cdc_replication_consistency_task(text)
        or is_dispute_chargeback_lifecycle_task(text)
        or is_kyc_aml_screening_task(text)
        or is_identity_sso_task(text)
        or is_notification_subscription_deliverability_task(text)
        or is_usage_quota_metering_task(text)
        or is_tax_calculation_compliance_task(text)
        or is_inventory_reservation_consistency_task(text)
        or is_subscription_entitlement_billing_task(text)
    ):
        return False
    if not re.search(
        r"webhook|provider\s+event|event\s+(?:schema|id)|signed\s+fixture|checkout\.session|支付.*事件|付款.*事件|供应商事件",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"payment\s+provider|checkout|refund|dispute|chargeback|payout|settlement|payment|invoice|balance|ledger|reconciliation|stripe|adyen|支付|结账|退款|争议|拒付|打款|结算|发票|余额|账本|对账",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"webhook|provider\s+event|event\s+schema|signature|timestamp|replay|out[- ]?of[- ]?order|idempot|duplicate|签名|时间戳|重放|乱序|幂等|重复",
        r"checkout|refund|dispute|chargeback|payout|settlement|payment|invoice|balance|支付|结账|退款|争议|拒付|打款|结算|发票|余额",
        r"ledger|reconciliation|reconcile|accounting|settlement\s+report|bank\s+statement|账本|对账|会计|结算报告|银行流水",
        r"retry|backoff|dead[- ]?letter|DLQ|queue|manual\s+replay|provider\s+failure|重试|退避|死信|队列|手动重放|供应商失败",
        r"audit|privacy|redaction|monitoring|alert|审计|隐私|脱敏|监控|告警",
        r"happy[- ]?path|unsigned|dev\s+mode|provider[- ]?status|database\s+unique|unique\s+constraint|docs[- ]?only|无签名|开发模式|状态|唯一约束|文档",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 3

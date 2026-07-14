from __future__ import annotations

import re


PROJECTION_LABEL_ANCHOR_PATTERNS = {
    "payment/refund/billing": (
        r"\b(?:payment|payments|refund|refunds|invoice|checkout|subscription|entitlement|proration|"
        r"balance[- ]?adjustment)\b|支付|退款|发票|结账|订阅|权益|按比例调整|余额调整"
    ),
    "data/export/report": r"\b(?:export|download|csv|report|dashboard)\b|导出|下载|报表|看板",
    "download/export-only": r"\b(?:export|download|csv|file)\b|导出|下载|文件",
    "evaluation/eval-set": (
        r"\b(?:eval(?:uation)?[- ]?set|evaluation[- ]?set|test[- ]?set|golden[- ]?"
        r"(?:set|queries?|examples?)|benchmark|holdout|regression[- ]?(?:samples?|set|queries?))\b"
        r"|评测集|评估集|黄金样本|黄金查询|benchmark|回归样本|回归集"
    ),
    "audit/log-integrity-retention": (
        r"\b(?:append[- ]?only|immutable|tamper[- ]?evident|tamper[- ]?proof|hash[- ]?chain|"
        r"worm[- ]?storage|write[- ]?once[- ]?read[- ]?many|clock[- ]?skew|"
        r"monotonic[- ]?timestamp|sequence[- ]?gap|gap[- ]?in[- ]?sequence|siem|stale[- ]?exporter|"
        r"logging[- ]?failure|log[- ]?integrity)\b|追加写|只追加|不可变|不可篡改|防篡改|篡改可见|"
        r"哈希链|WORM|一次写入多次读取|时钟偏移|"
        r"时间戳单调|序列缺口|序号缺口|日志缺口|SIEM|导出延迟|日志失败|日志完整性"
    ),
}


def projection_scoped_labels(task_text: str, labels) -> list[str]:
    text = str(task_text or "")
    scoped = _dedupe(label for label in labels if _projection_label_has_task_anchor(label, text))
    if _projection_is_prompt_asset_ownership_task(text):
        scoped = _dedupe([*scoped, "prompt-asset-ownership"])
    if _projection_is_dsar_data_export_task(text):
        scoped = ["privacy/dsar-data-export"]
    if _projection_is_subscription_entitlement_billing_task(text):
        scoped = ["billing/subscription-entitlement-proration"]
    return _projection_filter_primary_domain_noise(scoped)


def _projection_filter_primary_domain_noise(labels: list[str]) -> list[str]:
    if "prompt-asset-ownership" in labels:
        labels = [
            label
            for label in labels
            if label
            not in {
                "permission/auth",
                "permission/audit",
                "locale/i18n",
            }
        ]
    if "data/cdc-replication-consistency" in labels:
        return [
            label
            for label in labels
            if label
            not in {
                "notification/message",
                "notification/subscription-deliverability",
                "data/export/report",
                "download/export-only",
            }
        ]
    if "reporting/metric-reconciliation" in labels:
        return [label for label in labels if label != "data-lifecycle/deletion-retention"]
    if "payment/dispute-chargeback-lifecycle" in labels:
        return [label for label in labels if label != "notification/subscription-deliverability"]
    if "billing/subscription-entitlement-proration" in labels:
        labels = [
            label
            for label in labels
            if label
            not in {
                "notification/subscription-deliverability",
                "notification/message",
                "usage/quota-metering",
                "tax/calculation-compliance",
                "payment/refund/billing",
                "webhook/signature-replay-ordering",
            }
        ]
    if "notification/subscription-deliverability" in labels and "privacy/consent-preference-governance" not in labels:
        return [
            label
            for label in labels
            if label
            not in {
                "data-lifecycle/deletion-retention",
                "download/export-only",
                "permission/audit",
                "usage/quota-metering",
            }
        ]
    if "payout/settlement-reconciliation" in labels:
        return [
            label
            for label in labels
            if label
            not in {
                "compliance/kyc-aml-sanctions-screening",
                "payment/dispute-chargeback-lifecycle",
            }
        ]
    return labels


def _projection_label_has_task_anchor(label: str, task_text: str) -> bool:
    if _projection_is_prompt_asset_ownership_task(task_text) and label == "prompt-asset-ownership":
        return True
    pattern = PROJECTION_LABEL_ANCHOR_PATTERNS.get(str(label or "").strip())
    if not pattern:
        return True
    return bool(re.search(pattern, task_text, re.IGNORECASE))


def _projection_is_prompt_asset_ownership_task(task_text: str) -> bool:
    text = str(task_text or "")
    if not re.search(
        r"system[-_ ]?prompts?|developer[-_ ]?prompts?|fixed\s+prompts?|prompt\s+assets?|"
        r"system_prompt_assets|system_prompts|系统提示词|提示词资产|固定提示词",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"hardcod|inline|literal|asset(?:ize|s|ed)?|decoupl|migrat|ownership|locale|"
        r"language[- ]?specific|branch|\.zh|\.en|硬编码|内联|解耦|迁移|资产|归属|语言分支|多语言",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"system[-_ ]?prompts?|developer[-_ ]?prompts?|fixed\s+prompts?|系统提示词|固定提示词",
        r"Agent\s+Native|managed\s+entries?|role[- ]?agent|Claude\s+session|runtime\s+(?:role\s+)?prefix|"
        r"output\s+contracts?|alignment\s+compiler|role\s+metadata|托管入口|角色",
        r"system_prompt_assets|system_prompts|prompt\s+assets?|asset\s+refs?|load(?:ed|ing)?|render(?:ed|ing)?|"
        r"提示词资产|资产引用",
        r"hardcod|inline|literal|Python|code|硬编码|内联|代码",
        r"locale|language[- ]?specific|\.zh|\.en|named\s+user\s+language|语言|多语言|中文|英文",
        r"test|AST|long[- ]?instruction|static\s+asset\s+refs?|unresolved\s+placeholders?|placeholder|测试|占位符",
        r"Strategy\s+Source|user[- ]?editable\s+presets?|preset\s+boundary|策略源|预设",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 4


def _projection_is_dsar_data_export_task(task_text: str) -> bool:
    text = str(task_text or "")
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


def _projection_is_subscription_entitlement_billing_task(task_text: str) -> bool:
    text = str(task_text or "")
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
        r"订阅套餐|套餐升级|套餐降级|套餐变更|订阅升级|订阅降级|权益|proration|按比例|credit\s*memo|试用期|宽限期",
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


def _dedupe(values) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result

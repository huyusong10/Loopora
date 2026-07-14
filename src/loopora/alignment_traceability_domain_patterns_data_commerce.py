from __future__ import annotations

"""Inventory, quota, entitlement, and tax domain-risk patterns."""

INVENTORY_RESERVATION_CONSISTENCY_PATTERN = (
    r"(?:(?:\b(?:stock|sku|inventory[- ]?reservation|reserved[- ]?inventory|seat|event[- ]?ticket|ticket[- ]?inventory|ticket[- ]?stock|capacity|"
    r"availability|booking|appointment|inventory[- ]?(?:ledger|journal))\b|"
    r"库存|SKU|库存预留|座位|票务|票|名额|容量|可用量|预约|库存流水|库存账本).{0,240}"
    r"(?:\b(?:oversell|over[- ]?sell|overbook|over[- ]?book|concurrent|race[- ]?condition|ttl|"
    r"expiry|expire|release|released|cancel(?:lation)?|refund|payment[- ]?webhook|webhook|"
    r"idempotent|idempotency|ledger|reconcile|reconciliation|low[- ]?stock|out[- ]?of[- ]?stock|"
    r"sold[- ]?out|stock[- ]?out|retry|hold[- ]?expiry|release[- ]?reason)\b|"
    r"超卖|超订|并发|竞争|竞态|到期|过期|释放|取消|退款|支付回调|回调|幂等|库存流水|"
    r"库存账本|对账|低库存|售罄|无库存|失败支付|重试|释放原因)"
    r"|(?:\b(?:oversell|over[- ]?sell|overbook|over[- ]?book|concurrent|race[- ]?condition|ttl|"
    r"expiry|expire|release|released|cancel(?:lation)?|refund|payment[- ]?webhook|webhook|"
    r"idempotent|idempotency|ledger|reconcile|reconciliation|low[- ]?stock|out[- ]?of[- ]?stock|"
    r"sold[- ]?out|stock[- ]?out|retry|hold[- ]?expiry|release[- ]?reason)\b|"
    r"超卖|超订|并发|竞争|竞态|到期|过期|释放|取消|退款|支付回调|回调|幂等|库存流水|"
    r"库存账本|对账|低库存|售罄|无库存|失败支付|重试|释放原因).{0,240}"
    r"(?:\b(?:stock|sku|inventory[- ]?reservation|reserved[- ]?inventory|seat|event[- ]?ticket|ticket[- ]?inventory|ticket[- ]?stock|capacity|"
    r"availability|booking|appointment|inventory[- ]?(?:ledger|journal))\b|"
    r"库存|SKU|库存预留|座位|票务|票|名额|容量|可用量|预约|库存流水|库存账本))"
)


USAGE_QUOTA_METERING_PATTERN = (
    r"(?:(?:\b(?:usage[- ]?meter(?:ing|ed)?|usage[- ]?event(?:s)?|metering|metered[- ]?usage|"
    r"usage[- ]?ledger|quota(?:s)?|quota[- ]?enforcement|usage[- ]?limit(?:s)?|"
    r"rate[- ]?limit(?:s|ing)?|api[- ]?usage|billing[- ]?period|plan[- ]?(?:quota|limit)|"
    r"metering[- ]?version)\b|"
    r"用量计量|用量事件|用量账本|配额|额度|用量限制|限额|API\s*用量|计量版本|计费周期).{0,260}"
    r"(?:\b(?:duplicate[- ]?usage[- ]?events?|idempotenc(?:y|e)|idempotent[- ]?key|"
    r"concurrent[- ]?(?:api[- ]?)?calls?|plan[- ]?(?:upgrade|downgrade|change)|"
    r"billing[- ]?period[- ]?reset|reset[- ]?timezone|quota[- ]?window|hard[- ]?limit|"
    r"grace[- ]?limit|overage|over[- ]?use|under[- ]?count|over[- ]?count|"
    r"invoice|subscription[- ]?provider|reconcile|reconciliation|low[- ]?balance|"
    r"low[- ]?quota|exhaust(?:ed|ion)?|retry|reset[- ]?run)\b|"
    r"重复用量|幂等|幂等键|并发调用|套餐升级|套餐降级|套餐变更|计费周期重置|"
    r"重置时区|配额窗口|硬限额|宽限额度|超用|少计|多计|发票|订阅供应商|"
    r"对账|低余量|低额度|额度耗尽|重试|重置任务)"
    r"|(?:\b(?:duplicate[- ]?usage[- ]?events?|idempotenc(?:y|e)|idempotent[- ]?key|"
    r"concurrent[- ]?(?:api[- ]?)?calls?|plan[- ]?(?:upgrade|downgrade|change)|"
    r"billing[- ]?period[- ]?reset|reset[- ]?timezone|quota[- ]?window|hard[- ]?limit|"
    r"grace[- ]?limit|overage|over[- ]?use|under[- ]?count|over[- ]?count|"
    r"invoice|subscription[- ]?provider|reconcile|reconciliation|low[- ]?balance|"
    r"low[- ]?quota|exhaust(?:ed|ion)?|retry|reset[- ]?run)\b|"
    r"重复用量|幂等|幂等键|并发调用|套餐升级|套餐降级|套餐变更|计费周期重置|"
    r"重置时区|配额窗口|硬限额|宽限额度|超用|少计|多计|发票|订阅供应商|"
    r"对账|低余量|低额度|额度耗尽|重试|重置任务).{0,260}"
    r"(?:\b(?:usage[- ]?meter(?:ing|ed)?|usage[- ]?event(?:s)?|metering|metered[- ]?usage|"
    r"usage[- ]?ledger|quota(?:s)?|quota[- ]?enforcement|usage[- ]?limit(?:s)?|"
    r"rate[- ]?limit(?:s|ing)?|api[- ]?usage|billing[- ]?period|plan[- ]?(?:quota|limit)|"
    r"metering[- ]?version)\b|"
    r"用量计量|用量事件|用量账本|配额|额度|用量限制|限额|API\s*用量|计量版本|计费周期))"
)


SUBSCRIPTION_ENTITLEMENT_BILLING_PATTERN = (
    r"(?:(?:\b(?:entitlement(?:s)?|entitlement[- ]?(?:sync|state|propagation)|"
    r"team[- ]?member[- ]?entitlement(?:s)?|feature[- ]?access|seat[- ]?(?:entitlement|access)|"
    r"proration|prorated|credit[- ]?memo|invoice[- ]?total|provider[- ]?checkout|"
    r"upgrade[- ]?immediate|downgrade[- ]?(?:next[- ]?cycle|delayed|at[- ]?period[- ]?end)|"
    r"effective[- ]?(?:now|next[- ]?cycle))\b|"
    r"权益|权益生效|权益同步|团队成员权益|团队成员|功能权限|按比例|按比例调整|proration|贷项|credit\s*memo|"
    r"发票总额|provider\s*checkout|立即生效|下个周期生效|降级延迟|周期结束生效).{0,320}"
    r"(?:\b(?:upgrade[- ]?immediate|downgrade[- ]?(?:next[- ]?cycle|delayed|at[- ]?period[- ]?end)|"
    r"effective[- ]?(?:now|next[- ]?cycle)|team[- ]?member[- ]?entitlement(?:s)?|feature[- ]?access|"
    r"quota[- ]?(?:history|carryover)|historical[- ]?usage|ledger[- ]?reconciliation|"
    r"invoice[- ]?reconciliation|provider[- ]?reconciliation|webhook[- ]?replay|out[- ]?of[- ]?order|"
    r"duplicate[- ]?click(?:s)?|idempotenc(?:y|e)|rollback|tenant[- ]?boundary)\b|"
    r"立即生效|下个周期生效|降级延迟|周期结束生效|团队成员|功能权限|历史用量|配额历史|"
    r"账本对账|发票对账|供应商对账|provider\s*对账|webhook\s*重放|乱序|重复点击|幂等|回滚|租户边界|"
    r"订阅套餐|套餐升级|套餐降级|套餐变更|订阅升级|订阅降级|订阅变更)"
    r"|(?:\b(?:upgrade[- ]?immediate|downgrade[- ]?(?:next[- ]?cycle|delayed|at[- ]?period[- ]?end)|"
    r"effective[- ]?(?:now|next[- ]?cycle)|team[- ]?member[- ]?entitlement(?:s)?|feature[- ]?access|"
    r"quota[- ]?(?:history|carryover)|historical[- ]?usage|ledger[- ]?reconciliation|"
    r"invoice[- ]?reconciliation|provider[- ]?reconciliation|webhook[- ]?replay|out[- ]?of[- ]?order|"
    r"duplicate[- ]?click(?:s)?|idempotenc(?:y|e)|rollback|tenant[- ]?boundary)\b|"
    r"立即生效|下个周期生效|降级延迟|周期结束生效|团队成员|功能权限|历史用量|配额历史|"
    r"账本对账|发票对账|供应商对账|provider\s*对账|webhook\s*重放|乱序|重复点击|幂等|回滚|租户边界).{0,320}"
    r"(?:\b(?:entitlement(?:s)?|entitlement[- ]?(?:sync|state|propagation)|"
    r"team[- ]?member[- ]?entitlement(?:s)?|feature[- ]?access|seat[- ]?(?:entitlement|access)|"
    r"proration|prorated|credit[- ]?memo|invoice[- ]?total|provider[- ]?checkout|"
    r"upgrade[- ]?immediate|downgrade[- ]?(?:next[- ]?cycle|delayed|at[- ]?period[- ]?end)|"
    r"effective[- ]?(?:now|next[- ]?cycle))\b|"
    r"权益|权益生效|权益同步|团队成员权益|团队成员|功能权限|按比例|按比例调整|proration|贷项|credit\s*memo|"
    r"发票总额|provider\s*checkout|立即生效|下个周期生效|降级延迟|周期结束生效))"
)


TAX_CALCULATION_COMPLIANCE_PATTERN = (
    r"(?:(?:\b(?:sales[- ]?tax|vat|gst|tax[- ]?calculation|tax[- ]?calculator|tax[- ]?rate(?:s)?|"
    r"tax[- ]?provider|tax[- ]?ledger|tax[- ]?inclusive|tax[- ]?exclusive|taxability|tax[- ]?exemption|"
    r"exemption[- ]?certificate|reverse[- ]?charge|jurisdiction(?:s)?|nexus|tax[- ]?version|"
    r"tax[- ]?code(?:s)?)\b|"
    r"税费|销售税|增值税|VAT|GST|税率|税费计算|税务供应商|税费账本|税务账本|"
    r"含税|不含税|征税|免税|免税证书|反向征税|税区|税务辖区|经济关联|税务版本|税码).{0,280}"
    r"(?:\b(?:jurisdiction(?:s)?|nexus|taxability|digital[- ]?goods|physical[- ]?goods|"
    r"shipping[- ]?address|billing[- ]?address|exemption[- ]?certificate|reverse[- ]?charge|"
    r"round(?:ing)?|discount|coupon|shipping[- ]?fee|refund|invoice|provider[- ]?request[- ]?id|"
    r"rate[- ]?(?:source|change|effective[- ]?date)|effective[- ]?date|timezone|tax[- ]?ledger|"
    r"reconcile|reconciliation|currency[- ]?rounding|inclusive|exclusive)\b|"
    r"税区|税务辖区|经济关联|商品税类|数字商品|实物商品|收货地址|账单地址|免税证书|"
    r"反向征税|四舍五入|折扣|优惠券|运费|退款|发票|供应商请求|税率来源|税率变更|"
    r"生效日期|时区|税费账本|税务账本|对账|币种取整|含税|不含税)"
    r"|(?:\b(?:jurisdiction(?:s)?|nexus|taxability|digital[- ]?goods|physical[- ]?goods|"
    r"shipping[- ]?address|billing[- ]?address|exemption[- ]?certificate|reverse[- ]?charge|"
    r"round(?:ing)?|discount|coupon|shipping[- ]?fee|refund|invoice|provider[- ]?request[- ]?id|"
    r"rate[- ]?(?:source|change|effective[- ]?date)|effective[- ]?date|timezone|tax[- ]?ledger|"
    r"reconcile|reconciliation|currency[- ]?rounding|inclusive|exclusive)\b|"
    r"税区|税务辖区|经济关联|商品税类|数字商品|实物商品|收货地址|账单地址|免税证书|"
    r"反向征税|四舍五入|折扣|优惠券|运费|退款|发票|供应商请求|税率来源|税率变更|"
    r"生效日期|时区|税费账本|税务账本|对账|币种取整|含税|不含税).{0,280}"
    r"(?:\b(?:sales[- ]?tax|vat|gst|tax[- ]?calculation|tax[- ]?calculator|tax[- ]?rate(?:s)?|"
    r"tax[- ]?provider|tax[- ]?ledger|tax[- ]?inclusive|tax[- ]?exclusive|taxability|tax[- ]?exemption|"
    r"exemption[- ]?certificate|reverse[- ]?charge|jurisdiction(?:s)?|nexus|tax[- ]?version|"
    r"tax[- ]?code(?:s)?)\b|"
    r"税费|销售税|增值税|VAT|GST|税率|税费计算|税务供应商|税费账本|税务账本|"
    r"含税|不含税|征税|免税|免税证书|反向征税|税区|税务辖区|经济关联|税务版本|税码))"
)


__all__ = (
    "INVENTORY_RESERVATION_CONSISTENCY_PATTERN",
    "SUBSCRIPTION_ENTITLEMENT_BILLING_PATTERN",
    "TAX_CALCULATION_COMPLIANCE_PATTERN",
    "USAGE_QUOTA_METERING_PATTERN",
)

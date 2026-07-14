from __future__ import annotations

import re

from loopora.executor_alignment_task_predicates_trust_cross_domain import is_payout_settlement_reconciliation_task


def is_data_residency_task(task: str) -> bool:
    text = str(task or "")
    if not re.search(
        r"data[- ]?residen|regional[- ]?isolation|region[- ]?isolation|tenant[- ]?residency|wrong[- ]?region|数据驻留|区域隔离|租户驻留|错区",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"data[- ]?residen|regional[- ]?isolation|tenant[- ]?residency|wrong[- ]?region|region[- ]?routing|residency[- ]?policy|数据驻留|区域隔离|租户驻留|错区|区域路由",
        r"primary[- ]?(?:db|database)|object[- ]?storage|search[- ]?index|cache|queue|backup|logs?|analytics|DB|数据库|对象存储|搜索索引|缓存|队列|备份|日志|分析",
        r"processor|subprocessor|DPA|allowlist|third[- ]?party|处理方|子处理方",
        r"key[- ]?region|encryption|failover|migration|backfill|密钥|故障转移|迁移|回填",
        r"support/admin|support[- ]?access|admin[- ]?access|data[- ]?export|audit|observability|trace|egress|客服|管理员|导出|审计|观测|出站",
        r"UI\s+showing\s+region|env\s+var|tenant\s+table\s+region|one\s+routed\s+request|docs[- ]?only\s+DPA|region=EU|字段|配置",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 3


def is_kyc_aml_screening_task(task: str) -> bool:
    text = str(task or "")
    if is_payout_settlement_reconciliation_task(text):
        return False
    if not re.search(
        r"\bKYC\b|\bKYB\b|\bAML\b|sanctions?|PEP|watchlist|身份核验|反洗钱|制裁筛查|受益所有人",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"\bKYC\b|\bKYB\b|\bAML\b|sanctions?|PEP|watchlist|adverse\s+media|身份核验|反洗钱|制裁",
        r"identity|business\s+registry|beneficial\s+owner|document|OCR|liveness|address|身份|企业|受益所有人|证件|活体",
        r"manual\s+review|appeal|resubmission|risk\s+score|periodic\s+rescreen|人工审核|申诉|复筛|风险评分",
        r"provider|webhook|signature|replay|out[- ]?of[- ]?order|idempot|供应商|重放|乱序|幂等",
        r"payout|ledger|hold|release|retention|audit\s+reason|privacy|monitoring|打款|账本|冻结|释放|保留|审计|隐私|监控",
        r"sandbox\s+approved|UI\s+verified|provider\s+status|happy[- ]?path|沙箱|已验证",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 3

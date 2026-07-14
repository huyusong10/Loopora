from __future__ import annotations

import re


def is_rag_long_chain_task(task: str) -> bool:
    text = str(task or "")
    if not re.search(r"\bRAG\b|retrieval|知识库|检索增强", text, re.IGNORECASE):
        return False
    phase_markers = (
        r"\bingestion\b|文档\s*ingestion|语料|corpus",
        r"retrieval\s*ACL|permission-filtered\s+retrieval|tenant\s+filtering|检索权限|租户过滤",
        r"answer/tool|tool\s+gating|tool\s+allowlist|答案.*工具|工具.*白名单",
        r"\beval(?:uation)?\b|eval\s*set|human\s+review|评估|评测集|人工评审",
        r"monitoring|regression\s+monitoring|监控|告警",
        r"evidence\s+hardening|hardening|证据.*修复|补证据",
    )
    matched = sum(1 for pattern in phase_markers if re.search(pattern, text, re.IGNORECASE))
    if matched >= 4 and re.search(r"独立阶段|阶段|long[- ]?chain|长链|phase|multiple\s+evidence\s+rounds", text, re.IGNORECASE):
        return True
    success_markers = (
        r"grounded|source\s+chunks?|source\s+span|citation|document\s+version|答案.*来源|文档版本|引用",
        r"retrieval\s*ACL|tenant\s+filtering|permission-filtered|检索权限|租户过滤|权限过滤",
        r"prompt[- ]?injection|system\s+prompt|系统提示词|提示词注入",
        r"tool\s+allowlist|unauthorized\s+tool|tool[- ]?call|工具.*白名单|未授权\s*tool",
        r"PII|secrets?|redaction|脱敏|敏感|隐私",
        r"hallucination|fallback|handoff|no[- ]?answer|幻觉|兜底|转人工|无法回答",
        r"eval\s*set|golden\s+Q&A|faithfulness|citation\s+precision|top[- ]?k|human\s+review|评测集|人工评审",
        r"demo\s+question|plausible|embedding\s+search|UI\s+citations?|单个\s*demo|看起来合理|UI.*citation",
    )
    return sum(1 for pattern in success_markers if re.search(pattern, text, re.IGNORECASE)) >= 6


def is_search_index_consistency_task(task: str) -> bool:
    text = str(task or "")
    if re.search(r"\bRAG\b|检索增强", text, re.IGNORECASE):
        return False
    if not re.search(
        r"search\s+index|full[- ]?text\s+search|全文搜索|搜索索引|索引重建|reindex|indexing|indexer|索引",
        text,
        re.IGNORECASE,
    ):
        return False
    if re.search(
        r"\beval(?:uation)?\b|eval\s*set|benchmark|top[- ]?5|human\s+review|manual\s+review|relevance|groundedness|hallucination|评测|评估集|基准|人工评审|相关性|幻觉",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"create|update|delete|deleted[- ]?document|incremental|document\s+event|新建|更新|删除|已删除|增量|文档事件",
        r"ACL|permission|revocation|unauthorized|tenant|cross[- ]?tenant|权限|撤销|无权限|租户|跨租户",
        r"reindex|backfill|idempot(?:ent|ency)|rerun|重建|回填|幂等|重跑",
        r"watermark|cursor|checkpoint|recovery|retry|DLQ|failure|水位|游标|检查点|恢复|重试|死信|失败",
        r"lag|stale\s+index|SLO|alert|monitoring|延迟|陈旧索引|告警|监控",
        r"pagination|sort|ordering|分页|排序",
        r"audit|审计",
        r"local[- ]?search[- ]?only|green[- ]?index[- ]?job|row[- ]?count\s+sample|dashboard\s+latest|本地搜索|绿色|抽样|看板",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 4


def is_search_quality_task(task: str) -> bool:
    text = str(task or "")
    if re.search(r"\bRAG\b|检索增强", text, re.IGNORECASE):
        return False
    if not re.search(r"semantic\s+search|search|retrieval|ranking|top[- ]?5|搜索|检索|排序|相关性", text, re.IGNORECASE):
        return False
    quality_markers = (
        r"\beval(?:uation)?\b|eval\s*set|benchmark|评测|评估集|评测集|基准",
        r"human\s+review|manual\s+review|人工评审|人工审核",
        r"relevance|groundedness|hallucination|quality|相关性|幻觉|质量",
        r"negative\s+quer|negative\s+example|regression\s+sample|负例|负向|回归样本",
        r"demo\s+query|single\s+score|单点|单个\s*demo|单个\s*benchmark",
    )
    matched = sum(1 for pattern in quality_markers if re.search(pattern, text, re.IGNORECASE))
    return matched >= 3

from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import (
    _rag_long_chain_readiness_evidence,
    _search_index_consistency_readiness_evidence,
    _search_quality_readiness_evidence,
)
from loopora.executor_alignment_agreement_task_responses import (
    _agreement_task_clause,
    alignment_chinese_task_anchored_agreement_response,
    alignment_english_task_anchored_agreement_response,
    alignment_spanish_task_anchored_agreement_response,
)


def alignment_english_search_index_consistency_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed search index consistency task")
    payload["assistant_message"] = (
        "Please confirm this search-index consistency working agreement; I will compile a search-index-contract-first "
        "workflow with parallel Index Consistency and Access Freshness inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this knowledge-base search-index consistency task through a contract-first Loop: {task}. "
        "Search Index Contract Inspector first freezes document event schema, create/update/delete semantics, tenant ACL and permission-change rules, index alias/versioning, reindex/backfill cursor and idempotency, watermark recovery, lag SLO/alerts, pagination/sort stability samples, audit fields, retry/DLQ behavior, and governance; "
        "Search Index Builder implements only from that handoff; Index Consistency Inspector and Access Freshness Inspector inspect in parallel; "
        "GateKeeper fails closed on local-search-only, green-index-job-only, row-count-sample-only, dashboard-latest-only, missing ACL negatives, missing deleted-document proof, missing reindex idempotency, missing cursor recovery, missing lag alert, missing audit, or skipped governance."
    )
    payload["readiness_evidence"] = _search_index_consistency_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_search_index_consistency_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 search index consistency 任务")
    payload["assistant_message"] = (
        "请确认这份 search-index consistency 工作协议；确认后我会生成 Search Index Contract Inspector 先固定索引契约、"
        "Search Index Builder 再实现、Index Consistency Inspector 与 Access Freshness Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 knowledge-base search-index consistency 任务编排 contract-first Loop：{task}。"
        "Search Index Contract Inspector 先固定 document event schema、create/update/delete 语义、tenant ACL 与 permission-change rules、index alias/versioning、reindex/backfill cursor 与 idempotency、watermark recovery、lag SLO/alerts、pagination/sort stability samples、audit fields、retry/DLQ behavior 和 governance；"
        "Search Index Builder 只能基于该 handoff 实现；Index Consistency Inspector 与 Access Freshness Inspector 并行检查；"
        "GateKeeper 对 local-search-only、green-index-job-only、row-count-sample-only、dashboard-latest-only、ACL negatives 缺失、deleted-document proof 缺失、reindex idempotency 缺失、cursor recovery 缺失、lag alert 缺失、audit 缺失或 governance 跳过 fail closed。"
    )
    payload["readiness_evidence"] = _search_index_consistency_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_search_index_consistency_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de search index consistency confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de search-index consistency; después compilaré un workflow search-index-contract-first "
        "con inspecciones paralelas de Index Consistency y Access Freshness antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de knowledge-base search-index consistency con un Loop contract-first: {task}. "
        "Search Index Contract Inspector fija event schema, create/update/delete, tenant ACL, permission changes, alias/versioning, reindex/backfill cursor e idempotency, watermark recovery, lag alerts, pagination/sort samples, audit, retry/DLQ y governance; "
        "Search Index Builder implementa desde ese handoff; Index Consistency y Access Freshness inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante local-search-only, green-index-job-only, row-count-sample-only, dashboard-latest-only, missing ACL negatives, deleted-document proof, reindex idempotency, cursor recovery, lag alert, audit o governance."
    )
    payload["readiness_evidence"] = _search_index_consistency_readiness_evidence(task, language="es")
    return payload


def alignment_english_search_quality_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed search-quality task")
    payload["assistant_message"] = (
        "Please confirm this search-quality working agreement; I will compile a workflow that freezes the eval baseline before any search/ranking changes."
    )
    payload["agreement_summary"] = (
        f"Govern this search-quality task through an eval-first Loop: {task}. "
        "Evaluation Baseline Inspector freezes eval set, negative queries, regression samples, Top-5 baseline, and human-review rubric; "
        "Search Quality Builder changes retrieval/ranking from that handoff; Quality Evidence Inspector compares before/after and human quality records; "
        "GateKeeper fails closed on demo-query-only, single-score-only, or cherry-picked progress."
    )
    payload["readiness_evidence"] = _search_quality_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_search_quality_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 search quality 任务")
    payload["assistant_message"] = "请确认这份 search quality 工作协议；确认后我会生成先冻结 eval baseline、再改检索/排序、最后由 GateKeeper 裁决的 Loop。"
    payload["agreement_summary"] = (
        f"围绕这条 search quality 任务编排 eval-first Loop：{task}。"
        "Evaluation Baseline Inspector 先固定 eval set、负向查询、回归样本、Top-5 baseline 和人工评审 rubric；"
        "Search Quality Builder 只基于 baseline handoff 改检索/排序；Quality Evidence Inspector 比较 before/after 和人工质量记录；"
        "GateKeeper 对 demo-query-only、single-score-only 或 cherry-picked progress fail closed。"
    )
    payload["readiness_evidence"] = _search_quality_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_search_quality_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de search quality confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de search quality; después compilaré un Loop que congela eval baseline antes de cambiar retrieval/ranking."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de search quality con un Loop eval-first: {task}. "
        "Evaluation Baseline Inspector congela eval set, negativos, regresión, Top-5 baseline y rúbrica humana; "
        "Search Quality Builder cambia retrieval/ranking desde ese handoff; Quality Evidence Inspector compara before/after y revisión humana; "
        "GateKeeper falla cerrado ante demo-query-only o single-score-only."
    )
    payload["readiness_evidence"] = _search_quality_readiness_evidence(task, language="es")
    return payload


def alignment_english_rag_long_chain_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed RAG grounding task")
    payload["assistant_message"] = (
        "Please confirm this RAG grounding long-chain working agreement; I will compile a workflow with contract inspection, "
        "corpus ingestion, retrieval ACL, answer/tool gating, evaluation inspection, evidence hardening, and GateKeeper fan-in."
    )
    payload["agreement_summary"] = (
        f"Govern this enterprise RAG support chatbot grounding task through a long-chain Loop: {task}. "
        "RAG Contract Inspector first freezes document-version, source-span, retrieval ACL, tenant filtering, prompt-injection, tool allowlist, PII redaction, fallback/no-answer, eval, human-review, monitoring, and governance proof targets; "
        "Corpus Ingestion Builder, Retrieval ACL Builder, and Answer Tooling Builder create narrow staged handoffs; "
        "RAG Evaluation Inspector reads all three builder handoffs; Evidence Hardening Builder only repairs Weak, Unproven, or Blocking proof gaps from evaluation; "
        "RAG GateKeeper reads contract, evaluation, and hardening handoffs and fails closed on demo-only, plausible-answer-only, embedding-search-only, UI-citation-only, missing source spans, missing permission/tenant negatives, missing prompt-injection negatives, missing tool-safety, missing privacy redaction, missing eval/human-review/monitoring, or skipped local governance."
    )
    payload["readiness_evidence"] = _rag_long_chain_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_rag_long_chain_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 RAG grounding 任务")
    payload["assistant_message"] = (
        "请确认这份 RAG grounding 长链工作协议；确认后我会生成先 contract inspection，再分阶段 ingestion、retrieval ACL、"
        "answer/tool gating、evaluation inspection、evidence hardening，最后 GateKeeper 汇总裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条企业 RAG support chatbot grounding 任务编排 long-chain Loop：{task}。"
        "RAG Contract Inspector 先只读固定 document-version、source-span、retrieval ACL、tenant filtering、prompt-injection、tool allowlist、PII redaction、fallback/no-answer、eval、human-review、monitoring 和 governance proof targets；"
        "Corpus Ingestion Builder、Retrieval ACL Builder 与 Answer Tooling Builder 生成窄阶段 handoff；"
        "RAG Evaluation Inspector 读取三个 builder handoff；Evidence Hardening Builder 只修 evaluation 点名的 Weak、Unproven 或 Blocking proof gaps；"
        "RAG GateKeeper 读取 contract、evaluation 和 hardening handoff，并对 demo-only、plausible-answer-only、embedding-search-only、UI-citation-only、source span 缺失、permission/tenant negatives 缺失、prompt-injection negatives 缺失、tool-safety 缺失、privacy redaction 缺失、eval/human-review/monitoring 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _rag_long_chain_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_rag_long_chain_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea RAG grounding confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo RAG grounding long-chain; después compilaré contract inspection, ingestion, retrieval ACL, "
        "answer/tool gating, evaluation, evidence hardening y GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea enterprise RAG support chatbot grounding con un Loop long-chain: {task}. "
        "RAG Contract Inspector fija document version, source spans, retrieval ACL, tenant filtering, prompt injection, tool allowlist, redaction, fallback/no-answer, eval, human review, monitoring y governance; "
        "Corpus Ingestion Builder, Retrieval ACL Builder y Answer Tooling Builder producen handoffs estrechos; "
        "RAG Evaluation Inspector lee los tres handoffs; Evidence Hardening Builder repara solo gaps Weak/Unproven/Blocking; "
        "RAG GateKeeper lee contract, evaluation y hardening y falla cerrado ante demo-only, plausible answer, embedding-search-only, UI-citation-only, missing permissions, tool safety, privacy, eval, monitoring o governance."
    )
    payload["readiness_evidence"] = _rag_long_chain_readiness_evidence(task, language="es")
    return payload

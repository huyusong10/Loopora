from __future__ import annotations

from pathlib import Path
import re

from loopora.alignment_semantics import text_mentions_loop_fit_contradiction
from loopora.service_alignment_context import alignment_workdir_snapshot, alignment_workdir_snapshot_has_governance_markers
from loopora.service_alignment_stage import (
    alignment_bundle_agreement_projection_text,
    alignment_bundle_runtime_responsibility_projection_text,
    alignment_governance_marker_responsibility_issues,
    alignment_traceability_term_is_present,
    normalize_alignment_traceability_text,
)

ALIGNMENT_AGREEMENT_TRACEABILITY_KEYS = [
    "loop_fit",
    "task_scope",
    "success_surface",
    "fake_done_risks",
    "evidence_preferences",
    "execution_strategy",
    "residual_risk_policy",
    "judgment_tradeoffs",
    "local_governance",
    "role_posture",
    "workflow_shape",
    "workdir_facts",
]
ALIGNMENT_TRACEABILITY_GENERIC_TERMS = {
    "agent",
    "agents",
    "alignment",
    "and",
    "answer",
    "answers",
    "any",
    "artifact",
    "artifacts",
    "assumptions",
    "auditable",
    "behavior",
    "before",
    "because",
    "block",
    "blocked",
    "blocker",
    "blockers",
    "blocking",
    "bug",
    "bugs",
    "builder",
    "buckets",
    "built",
    "bundle",
    "bundles",
    "candidate",
    "carefully",
    "case",
    "cases",
    "change",
    "changes",
    "chat",
    "check",
    "checks",
    "claims",
    "clear",
    "close",
    "closed",
    "closes",
    "closure",
    "collects",
    "collaboration",
    "command",
    "complete",
    "completed",
    "completion",
    "complex",
    "concrete",
    "context",
    "correct",
    "created",
    "current",
    "direct",
    "distinguish",
    "drift",
    "during",
    "done",
    "early",
    "enough",
    "error",
    "evidence",
    "exact",
    "existing",
    "expected",
    "experience",
    "exercise",
    "exportable",
    "exposed",
    "fail",
    "failed",
    "fails",
    "facts",
    "fake-done",
    "final",
    "fit",
    "fits",
    "flow",
    "focused",
    "from",
    "future",
    "gains",
    "gaps",
    "gatekeeper",
    "gated",
    "generic",
    "goal",
    "good",
    "handle",
    "handoff",
    "handoffs",
    "happy-path-only",
    "hide",
    "hides",
    "important",
    "inspected",
    "inspector",
    "inspectors",
    "judge",
    "judged",
    "judgment",
    "keeps",
    "limited",
    "local",
    "loop",
    "loopora",
    "making",
    "means",
    "minor",
    "missing",
    "must",
    "named",
    "narrow",
    "new",
    "observed",
    "observable",
    "open",
    "open-ended",
    "only",
    "one-pass",
    "output",
    "over",
    "pass",
    "patch",
    "path",
    "polish",
    "polished-looking",
    "posture",
    "prefer",
    "preference",
    "preferences",
    "primary",
    "primary-flow",
    "produce",
    "project",
    "project-owned",
    "proof",
    "prove",
    "proven",
    "provided",
    "ready",
    "real",
    "reject",
    "remain",
    "reproducible",
    "result",
    "residual",
    "revised",
    "review",
    "risk",
    "risks",
    "role",
    "roles",
    "round",
    "rounds",
    "run",
    "run-owned",
    "scope",
    "should",
    "slice",
    "smaller",
    "snapshot",
    "specific",
    "speed",
    "stack",
    "standalone",
    "starter",
    "strongest",
    "success",
    "surface",
    "survive",
    "task",
    "tasks",
    "target",
    "test",
    "tests",
    "that",
    "the",
    "them",
    "then",
    "they",
    "through",
    "true",
    "unknown",
    "until",
    "unproven",
    "useful",
    "user",
    "user-facing",
    "vague",
    "verifiable",
    "verify",
    "verified",
    "verification",
    "wants",
    "weak",
    "when",
    "while",
    "with",
    "without",
    "work",
    "workflow",
    "workdir",
    "works",
}
ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS = {
    "以及",
    "因为",
    "如果",
    "任务",
    "证据",
    "角色",
    "流程",
    "风险",
    "判断",
    "工作",
    "用户",
    "确认",
    "运行",
    "检查",
    "证明",
    "验证",
    "阻断",
    "完成",
    "成功",
    "失败",
    "必须",
    "优先",
    "方案",
    "服务",
    "选择",
    "使用",
    "测试",
    "命令",
    "产物",
    "主流程",
    "主流",
    "而不",
    "起来",
    "真实",
    "结果",
    "输出",
    "项目",
    "路径",
    "规则",
    "未知",
    "修复",
    "改进",
    "可见",
    "收束",
    "交接",
    "构建",
    "裁决",
    "质量",
    "偏差",
    "具体",
    "技术",
    "复退",
}
ALIGNMENT_LOOP_FIT_TRACEABILITY_GENERIC_TERMS = {
    "audit",
    "export",
    "human",
    "material",
    "plus",
    "reuse",
    "this",
}
ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS = frozenset("的一是在和与或及并但而为由让把被只已未就才需能会应可其此个这那")
ALIGNMENT_AGENT_CANDIDATE_GENERIC_TERMS = {
    "agent-native",
    "already",
    "across",
    "after",
    "bind",
    "build",
    "bundle",
    "candidate",
    "claim",
    "codex",
    "control",
    "context",
    "counts",
    "coverage",
    "dispatch",
    "evidence",
    "evidence-backed",
    "elapses",
    "enforce",
    "enters",
    "exhausted",
    "fire",
    "governed",
    "host",
    "inside",
    "invented",
    "isolated",
    "iterations",
    "keep",
    "known",
    "ledger",
    "lifecycle",
    "limit",
    "malformed",
    "native",
    "non-gatekeeper",
    "outputs",
    "parallel",
    "peer",
    "plane",
    "proof",
    "ready",
    "ref",
    "refs",
    "rejection",
    "require",
    "required",
    "requires",
    "reviewers",
    "separate",
    "set",
    "skip",
    "stalled",
    "stay",
    "submit",
    "submitted",
    "surface",
    "this",
    "thread",
    "treat",
    "window",
}


def alignment_bundle_agreement_traceability_issues(session: dict, bundle: dict) -> list[str]:
    agreement = session.get("working_agreement") if isinstance(session.get("working_agreement"), dict) else {}
    evidence = agreement.get("readiness_evidence") if isinstance(agreement.get("readiness_evidence"), dict) else {}
    bundle_text = alignment_bundle_agreement_projection_text(bundle)
    normalized_bundle_text = normalize_alignment_traceability_text(bundle_text)
    normalized_runtime_text = normalize_alignment_traceability_text(alignment_bundle_runtime_responsibility_projection_text(bundle))
    issues: list[str] = []
    if evidence:
        repeated_cjk_terms = agreement_repeated_cjk_traceability_terms(evidence.values())
        for key in ALIGNMENT_AGREEMENT_TRACEABILITY_KEYS:
            terms = agreement_traceability_terms(evidence.get(key))
            if key == "loop_fit":
                terms = [term for term in terms if term not in ALIGNMENT_LOOP_FIT_TRACEABILITY_GENERIC_TERMS]
            terms.extend(term for term in repeated_cjk_terms if term in str(evidence.get(key) or "") and term not in terms)
            if key == "workdir_facts":
                terms = [term for term in terms if "/" in term or "." in term]
            if key == "local_governance":
                terms = [term for term in terms if "/" in term or "." in term]
            if not terms:
                continue
            matched = [term for term in terms if alignment_traceability_term_is_present(term, normalized_bundle_text=normalized_bundle_text)]
            required_matches = 1 if len(terms) < 4 else 2
            if len(matched) >= required_matches:
                continue
            issues.append(
                "alignment bundle must project confirmed working agreement evidence into runnable surfaces: "
                f"{key} missing {', '.join(terms[:5])}"
            )
        issues.extend(
            alignment_governance_marker_responsibility_issues(
                evidence,
                normalized_runtime_text=normalized_runtime_text,
            )
        )
        issues.extend(
            alignment_agreement_category_projection_issues(
                evidence,
                normalized_bundle_text=normalized_bundle_text,
            )
        )
    workdir_snapshot = alignment_workdir_snapshot(Path(session["workdir"])) if session.get("workdir") else ""
    if alignment_workdir_snapshot_has_governance_markers(workdir_snapshot):
        issues.extend(
            alignment_governance_marker_responsibility_issues(
                {"workdir_snapshot": workdir_snapshot},
                normalized_runtime_text=normalized_runtime_text,
            )
        )
    return issues


def alignment_agreement_category_projection_issues(evidence: dict, *, normalized_bundle_text: str) -> list[str]:
    category_checks = (
        (
            "success_surface",
            "success surface",
            agent_candidate_success_surface_categories(
                str(evidence.get("success_surface") or ""),
                require_explicit_marker=False,
            ),
            1,
        ),
        (
            "fake_done_risks",
            "fake-done risks",
            agent_candidate_fake_done_categories(
                str(evidence.get("fake_done_risks") or ""),
                require_explicit_marker=False,
            ),
            1,
        ),
        (
            "evidence_preferences",
            "evidence preferences",
            agent_candidate_evidence_preference_categories(
                str(evidence.get("evidence_preferences") or ""),
                require_explicit_marker=False,
            ),
            1,
        ),
        (
            "execution_strategy",
            "execution strategy",
            agent_candidate_execution_strategy_categories(
                str(evidence.get("execution_strategy") or ""),
                require_explicit_marker=False,
            ),
            2,
        ),
        (
            "residual_risk_policy",
            "residual-risk policy",
            agent_candidate_residual_risk_policy_categories(
                str(evidence.get("residual_risk_policy") or ""),
                require_explicit_marker=False,
            ),
            1,
        ),
        (
            "judgment_tradeoffs",
            "judgment tradeoffs",
            agent_candidate_tradeoff_categories(str(evidence.get("judgment_tradeoffs") or "")),
            2,
        ),
    )
    issues: list[str] = []
    for _key, label, categories, minimum_category_count in category_checks:
        if len(categories) < minimum_category_count:
            continue
        missing = [
            category_label
            for category_label, bundle_pattern in categories
            if not re.search(bundle_pattern, normalized_bundle_text, re.I)
        ]
        if not missing:
            continue
        issues.append(
            "alignment bundle must project confirmed working agreement "
            f"{label} into runnable surfaces: missing {', '.join(missing)}"
        )
    return issues


def alignment_agent_candidate_traceability_issues(task_text: str, bundle: dict) -> list[str]:
    task_text = str(task_text or "")
    issues: list[str] = []
    if text_mentions_loop_fit_contradiction(task_text):
        issues.append(
            "agent-first candidate cannot compile a Loop when the host Agent task summary says Loopora is not fit; "
            "ask the user or use Web review before generating a runnable Loop"
        )
    normalized_bundle_text = normalize_alignment_traceability_text(alignment_bundle_agreement_projection_text(bundle))
    normalized_runtime_text = normalize_alignment_traceability_text(alignment_bundle_runtime_responsibility_projection_text(bundle))
    terms = agent_candidate_traceability_terms(task_text)
    if terms:
        matched = [term for term in terms if alignment_traceability_term_is_present(term, normalized_bundle_text=normalized_bundle_text)]
        required_matches = 1 if len(terms) < 4 else 2
        if len(matched) < required_matches:
            issues.append(
                "agent-first candidate must project the host Agent task summary into runnable surfaces: "
                + "missing "
                + ", ".join(terms[:5])
            )
    issues.extend(
        alignment_governance_marker_responsibility_issues(
            {"agent_candidate": task_text},
            normalized_runtime_text=normalized_runtime_text,
        )
    )
    issues.extend(
        alignment_agent_candidate_tradeoff_issues(
            task_text,
            normalized_bundle_text=normalized_bundle_text,
        )
    )
    issues.extend(
        alignment_agent_candidate_execution_strategy_issues(
            task_text,
            normalized_bundle_text=normalized_bundle_text,
        )
    )
    issues.extend(
        alignment_agent_candidate_residual_risk_policy_issues(
            task_text,
            normalized_bundle_text=normalized_bundle_text,
        )
    )
    issues.extend(
        alignment_agent_candidate_success_surface_issues(
            task_text,
            normalized_bundle_text=normalized_bundle_text,
        )
    )
    issues.extend(
        alignment_agent_candidate_fake_done_issues(
            task_text,
            normalized_bundle_text=normalized_bundle_text,
        )
    )
    issues.extend(
        alignment_agent_candidate_evidence_preference_issues(
            task_text,
            normalized_bundle_text=normalized_bundle_text,
        )
    )
    return issues


def alignment_agent_candidate_tradeoff_issues(task_text: str, *, normalized_bundle_text: str) -> list[str]:
    categories = agent_candidate_tradeoff_categories(task_text)
    if len(categories) < 2:
        return []
    missing = [
        label
        for label, bundle_pattern in categories
        if not re.search(bundle_pattern, normalized_bundle_text, re.I)
    ]
    if not missing:
        return []
    return [
        "agent-first candidate must project explicit host Agent judgment tradeoffs into runnable surfaces: "
        + "missing "
        + ", ".join(missing)
    ]


def agent_candidate_tradeoff_categories(task_text: str) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    explicit_tradeoff_markers = (
        r"\b(?:proof|evidence|verify|verification)\b.{0,80}\b(?:over|before|rather than|instead of)\b.{0,80}\b(?:speed|fast|quick|polish|ui|narrative|story)\b",
        r"\b(?:speed|fast|quick|polish|ui|narrative|story)\b.{0,80}\b(?:wait|after|behind|until|rather than|instead of)\b.{0,80}\b(?:proof|evidence|verify|verification)\b",
        r"\b(?:strict|blocking|block|reject|fail closed)\b.{0,80}\b(?:over|before|rather than|instead of|beats?)\b.{0,80}\b(?:pragmatic|pragmatism|progress)\b",
        r"\b(?:pragmatic|pragmatism|progress)\b.{0,80}\b(?:wait|after|behind|until|rather than|instead of)\b.{0,80}\b(?:strict|blocking|block|reject|fail closed)\b",
        r"\b(?:prioriti[sz]e|prefer)\b.{0,80}\b(?:proof|evidence|verify|verification|blocking|fail closed)\b",
        r"\b(?:block|reject|fail closed)\b.{0,80}\b(?:fake[- ]?done|fake completion|polished-looking|narrative)\b",
        r"(?:优先|先).{0,24}(?:证明|证据|验证|阻断)",
        r"(?:证明|证据|验证|阻断).{0,24}(?:优先|先于|高于)",
        r"(?:严格|阻断|拒绝).{0,20}(?:优先|先于|高于).{0,20}(?:务实|推进|进度)",
        r"(?:务实|推进|进度).{0,20}(?:等|让位|后于).{0,20}(?:严格|阻断|拒绝)",
        r"(?:先别|不要|别).{0,16}(?:美化|润色|打磨|漂亮|界面)",
        r"(?:阻断|拒绝).{0,20}(?:假完成|漂亮叙事|证据不足)",
    )
    if not any(re.search(pattern, text, re.I) for pattern in explicit_tradeoff_markers):
        return []
    category_patterns = (
        (
            "proof/evidence",
            r"\b(?:proof|prove|proven|evidence|verify|verification)\b|证明|证据|验证|已证明",
        ),
        (
            "speed/polish",
            r"\b(?:speed|fast|quick|polish|ui|narrative|story|pretty|polished-looking)\b|速度|快速|美化|润色|打磨|界面|漂亮|叙事",
        ),
        (
            "blocking/fake-completion",
            r"\b(?:block|blocking|reject|fail closed|fake[- ]?done|fake completion|unproven|weak)\b|阻断|拒绝|假完成|未证明|弱证据|证据不足",
        ),
        (
            "pragmatic/progress",
            r"\b(?:pragmatic|pragmatism|progress)\b|务实|推进|进度",
        ),
    )
    return [(label, pattern) for label, pattern in category_patterns if re.search(pattern, text, re.I)]


def alignment_agent_candidate_execution_strategy_issues(task_text: str, *, normalized_bundle_text: str) -> list[str]:
    categories = agent_candidate_execution_strategy_categories(task_text)
    if not categories:
        return []
    if len(categories) < 2 and not agent_candidate_has_labeled_execution_strategy(task_text):
        return []
    missing = [
        label
        for label, bundle_pattern in categories
        if not re.search(bundle_pattern, normalized_bundle_text, re.I)
    ]
    if not missing:
        return []
    return [
        "agent-first candidate must project explicit host Agent execution strategy into runnable surfaces: "
        + "missing "
        + ", ".join(missing)
    ]


def agent_candidate_has_labeled_execution_strategy(task_text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:execution strategy|priority|priorities|priority order|next round|next pass)\b|执行策略|优先级|下一轮|下一步",
            str(task_text or ""),
            re.I,
        )
    )


def agent_candidate_execution_strategy_categories(task_text: str, *, require_explicit_marker: bool = True) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    explicit_strategy_markers = (
        r"\b(?:execution strategy|next round|next pass|priority|priorities)\b",
        r"\b(?:first|before|then|after|defer|prioriti[sz]e|start with|do not start|don't start|avoid)\b",
        r"(?:执行策略|下一轮|下一步|优先级|优先|先|再|然后|之后|暂缓|推迟|先别|不要先|别先)",
    )
    if require_explicit_marker and not any(re.search(pattern, text, re.I) for pattern in explicit_strategy_markers):
        return []
    category_patterns = (
        (
            "repair/root-cause",
            r"\b(?:root[- ]?cause|regression|failure|failing|bug)\b|根因|故障|失败|回归|缺陷",
        ),
        (
            "evidence/proof",
            r"\b(?:proof|prove|proven|evidence|verify|verification|audit|test|tests)\b|证明|证据|验证|审计|测试|已证明",
        ),
        (
            "scope/narrow",
            r"\b(?:scope|narrow|focused|focus|small|minimal|limit|bounded)\b|范围|收窄|聚焦|小而|最小|有限",
        ),
        (
            "expand/breadth",
            r"\b(?:expand|expansion|broaden|broad|breadth|new feature|dashboard|report)\b|扩展|扩大|铺开|宽泛|新功能|看板|报表",
        ),
        (
            "polish/ui",
            r"\b(?:polish|ui|visual|pretty|styling|copy|narrative|story)\b|美化|打磨|润色|界面|视觉|文案|叙事|漂亮",
        ),
    )
    return [(label, pattern) for label, pattern in category_patterns if re.search(pattern, text, re.I)]


def alignment_agent_candidate_residual_risk_policy_issues(task_text: str, *, normalized_bundle_text: str) -> list[str]:
    categories = agent_candidate_residual_risk_policy_categories(task_text)
    if not categories:
        return []
    missing = [
        label
        for label, bundle_pattern in categories
        if not re.search(bundle_pattern, normalized_bundle_text, re.I)
    ]
    if not missing:
        return []
    return [
        "agent-first candidate must project explicit host Agent residual-risk policy into runnable surfaces: "
        + "missing "
        + ", ".join(missing)
    ]


def agent_candidate_residual_risk_policy_categories(task_text: str, *, require_explicit_marker: bool = True) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    explicit_policy_markers = (
        r"\bresidual risks?\b",
        r"\bremaining risks?\b",
        r"残余风险",
        r"剩余风险",
    )
    if require_explicit_marker and not any(re.search(pattern, text, re.I) for pattern in explicit_policy_markers):
        return []
    no_acceptance_pattern = (
        r"\b(?:no|none|zero)\b.{0,60}\b(?:accepted|acceptable|allowed)?\s*residual risks?\b"
        r"|\b(?:do not|don't|cannot|can't|must not|never)\b.{0,60}\baccept\b.{0,60}\bresidual risks?\b"
        r"|(?:不接受|不能接受|不可接受|不允许).{0,24}残余风险"
        r"|残余风险.{0,24}(?:不接受|不能接受|不可接受|不允许)"
    )
    categories: list[tuple[str, str]] = [
        ("residual-risk", r"\bresidual risks?\b|\bremaining risks?\b|残余风险|剩余风险"),
    ]
    if re.search(no_acceptance_pattern, text, re.I):
        categories.append(
            (
                "no-accepted-residual-risk",
                (
                    r"\b(?:no|none|zero)\b.{0,80}\b(?:accepted|acceptable|allowed)?\s*residual risks?\b"
                    r"|\b(?:do not|don't|cannot|can't|must not|never)\b.{0,80}\baccept\b.{0,80}\bresidual risks?\b"
                    r"|(?:不接受|不能接受|不可接受|不允许).{0,30}残余风险"
                    r"|残余风险.{0,30}(?:不接受|不能接受|不可接受|不允许)"
                ),
            )
        )
        return categories
    category_patterns = (
        (
            "acceptance",
            r"\b(?:accept|accepted|acceptable|allow|allowed|carry)\b|接受|可接受|允许|带着走",
            (
                r"(?:\bresidual risks?\b|残余风险|剩余风险).{0,160}"
                r"(?:\b(?:accept|accepted|acceptable|allow|allowed|carry)\b|接受|可接受|允许|带着走)"
                r"|(?:\b(?:accept|accepted|acceptable|allow|allowed|carry)\b|接受|可接受|允许|带着走)"
                r".{0,160}(?:\bresidual risks?\b|残余风险|剩余风险)"
            ),
        ),
        (
            "owner/follow-up",
            (
                r"\b(?:owner|owned|assignee|follow[- ]?up|followup|ticket|tracked|tracking|"
                r"revisit|monitor|mitigation)\b|负责人|负责|接手|接管|后续|跟进|工单|跟踪|追踪|监控|缓解"
            ),
            (
                r"(?:\bresidual risks?\b|残余风险|剩余风险).{0,180}"
                r"(?:\b(?:owner|owned|assignee|follow[- ]?up|followup|ticket|tracked|tracking|"
                r"revisit|monitor|mitigation)\b|负责人|负责|接手|接管|后续|跟进|工单|跟踪|追踪|监控|缓解)"
                r"|(?:\b(?:owner|owned|assignee|follow[- ]?up|followup|ticket|tracked|tracking|"
                r"revisit|monitor|mitigation)\b|负责人|负责|接手|接管|后续|跟进|工单|跟踪|追踪|监控|缓解)"
                r".{0,180}(?:\bresidual risks?\b|残余风险|剩余风险)"
            ),
        ),
        (
            "fail-closed",
            r"\b(?:fail closed|must block|must fail|block|blocking|reject)\b|失败关闭|必须阻断|必须失败|阻断|拒绝",
            (
                r"(?:\bresidual risks?\b|残余风险|剩余风险).{0,180}"
                r"(?:\b(?:fail closed|must block|must fail|block|blocking|reject)\b|失败关闭|必须阻断|必须失败|阻断|拒绝)"
                r"|(?:\b(?:fail closed|must block|must fail|block|blocking|reject)\b|失败关闭|必须阻断|必须失败|阻断|拒绝)"
                r".{0,180}(?:\bresidual risks?\b|残余风险|剩余风险)"
            ),
        ),
    )
    categories.extend(
        (label, bundle_pattern)
        for label, task_pattern, bundle_pattern in category_patterns
        if re.search(task_pattern, text, re.I)
    )
    return categories


def alignment_agent_candidate_success_surface_issues(task_text: str, *, normalized_bundle_text: str) -> list[str]:
    categories = agent_candidate_success_surface_categories(task_text)
    if not categories:
        return []
    missing = [
        label
        for label, bundle_pattern in categories
        if not re.search(bundle_pattern, normalized_bundle_text, re.I)
    ]
    if not missing:
        return []
    return [
        "agent-first candidate must project explicit host Agent success criteria into runnable surfaces: "
        + "missing "
        + ", ".join(missing)
    ]


def agent_candidate_success_surface_categories(task_text: str, *, require_explicit_marker: bool = True) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    explicit_success_markers = (
        r"\bsuccess\s+(?:means|requires|is)\b",
        r"\bdone when\b",
        r"\bcomplete when\b",
        r"\bacceptance criteria\b",
        r"\bto pass\b.{0,80}\b(?:must|needs?|should|requires?)\b",
        r"\b(?:must|needs?|should|requires?)\b.{0,80}\b(?:pass|succeed|be complete|be done)\b",
        r"成功(?:标准|意味着|要求|面)",
        r"完成(?:标准|条件|时)",
        r"验收(?:标准|条件)",
    )
    if require_explicit_marker and not any(re.search(pattern, text, re.I) for pattern in explicit_success_markers):
        return []
    categories: list[tuple[str, str]] = [
        (
            "success/done-when",
            r"\b(?:success|done when|acceptance criteria|complete when|completion criteria)\b|成功|完成标准|验收",
        ),
    ]
    category_patterns = (
        (
            "actor/user-facing-outcome",
            r"\b(?:user|customer|admin|operator|buyer|merchant|support)\b|用户|客户|管理员|运营|买家|商家|客服",
        ),
        (
            "notification/message",
            r"\b(?:notification|notify|email|message|receipt|alert)\b|通知|邮件|消息|回执|提醒",
        ),
        (
            "audit/log",
            r"\b(?:audit|auditing|audit[- ]?log|log|logs|ledger|trace|recorded|records?)\b|审计|日志|账本|记录|追踪",
        ),
        (
            "permission/auth",
            r"\b(?:permission|permissions|authorization|auth|access|role)\b|权限|授权|访问|角色",
        ),
        (
            "payment/refund/billing",
            r"\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账",
        ),
        (
            "data/export/report",
            r"\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板",
        ),
        (
            "accessibility/a11y",
            r"\b(?:accessibility|a11y|screen[- ]?reader|keyboard|aria|focus|wcag)\b|无障碍|可访问|读屏|屏幕阅读器|键盘|焦点",
        ),
        (
            "locale/i18n",
            r"\b(?:locale|locali[sz]ation|i18n|translation|language|chinese|english)\b|多语言|国际化|本地化|翻译|语言|中文|英文|英语",
        ),
    )
    categories.extend((label, pattern) for label, pattern in category_patterns if re.search(pattern, text, re.I))
    return categories


def alignment_agent_candidate_fake_done_issues(task_text: str, *, normalized_bundle_text: str) -> list[str]:
    categories = agent_candidate_fake_done_categories(task_text)
    if not categories:
        return []
    missing = [
        label
        for label, bundle_pattern in categories
        if not re.search(bundle_pattern, normalized_bundle_text, re.I)
    ]
    if not missing:
        return []
    return [
        "agent-first candidate must project explicit host Agent fake-done risks into runnable surfaces: "
        + "missing "
        + ", ".join(missing)
    ]


def agent_candidate_fake_done_categories(task_text: str, *, require_explicit_marker: bool = True) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    explicit_fake_done_markers = (
        r"\bfake[- ]?(?:done|completion)\b",
        r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b",
        r"\b(?:looks|appears|seems)\s+(?:done|complete|finished|working)\b",
        r"\b(?:only|just|merely)\s+(?:a\s+)?(?:claim|screenshot|download|export|mock|stub|static)\b",
        r"\bhappy[- ]path[- ]only\b",
        r"假完成",
        r"看起来.{0,12}(?:完成|可用|通过)",
        r"(?:不能|不可|不要|不得).{0,16}(?:通过|算完成|收尾)",
    )
    if require_explicit_marker and not any(re.search(pattern, text, re.I) for pattern in explicit_fake_done_markers):
        return []
    categories: list[tuple[str, str]] = [
        (
            "fake-done/blocking",
            r"\bfake[- ]?(?:done|completion)\b|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|假完成|阻断|不得通过|不能通过",
        ),
    ]
    category_patterns = (
        (
            "permission/audit",
            r"\b(?:permission|permissions|authorization|auth|access|audit|auditing|audit[- ]?log)\b|权限|授权|审计|日志",
            r"\b(?:permission|permissions|authorization|auth|access|audit|auditing|audit[- ]?log)\b|权限|授权|审计|日志",
        ),
        (
            "download/export-only",
            r"\b(?:csv|download|export|file)\b|下载|导出|文件",
            r"\b(?:csv|download|export|file)\b|下载|导出|文件",
        ),
        (
            "payment/refund/billing",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过).{0,80}"
                r"(?:\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账)"
                r"|(?:\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账)"
                r".{0,80}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过)"
            ),
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|不得通过|不能通过).{0,80}"
                r"(?:\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账)"
                r"|(?:\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账)"
                r".{0,80}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|不得通过|不能通过)"
            ),
        ),
        (
            "data/export/report",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过).{0,80}"
                r"(?:\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板)"
                r"|(?:\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板)"
                r".{0,80}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过)"
            ),
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|不得通过|不能通过).{0,80}"
                r"(?:\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板)"
                r"|(?:\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板)"
                r".{0,80}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|不得通过|不能通过)"
            ),
        ),
        (
            "visual/polish/screenshot-only",
            r"\b(?:screenshot|visual|polish|ui|pretty|polished-looking)\b|截图|视觉|界面|美化|漂亮",
            r"\b(?:screenshot|visual|polish|ui|pretty|polished-looking)\b|截图|视觉|界面|美化|漂亮",
        ),
        (
            "claim/narrative-only",
            r"\b(?:claim|claims|narrative|story|description|self[- ]?report)\b|声明|叙事|描述|自述",
            r"\b(?:claim|claims|narrative|story|description|self[- ]?report)\b|声明|叙事|描述|自述",
        ),
        (
            "happy-path-only",
            r"\bhappy[- ]?path\b|主路径|快乐路径",
            r"\bhappy[- ]?path\b|主路径|快乐路径",
        ),
        (
            "mock/static/stub-only",
            r"\b(?:mock|stub|static|placeholder|fixture)\b|模拟|桩|静态|占位",
            r"\b(?:mock|stub|static|placeholder|fixture)\b|模拟|桩|静态|占位",
        ),
        (
            "accessibility/i18n",
            r"\b(?:accessibility|a11y|screen[- ]?reader|keyboard|aria|focus|wcag|locale|locali[sz]ation|i18n|translation|language)\b|无障碍|可访问|读屏|屏幕阅读器|键盘|焦点|多语言|国际化|本地化|翻译|语言",
            r"\b(?:accessibility|a11y|screen[- ]?reader|keyboard|aria|focus|wcag|locale|locali[sz]ation|i18n|translation|language)\b|无障碍|可访问|读屏|屏幕阅读器|键盘|焦点|多语言|国际化|本地化|翻译|语言",
        ),
    )
    categories.extend((label, bundle_pattern) for label, task_pattern, bundle_pattern in category_patterns if re.search(task_pattern, text, re.I))
    return categories


def alignment_agent_candidate_evidence_preference_issues(task_text: str, *, normalized_bundle_text: str) -> list[str]:
    categories = agent_candidate_evidence_preference_categories(task_text)
    if not categories:
        return []
    missing = [
        label
        for label, bundle_pattern in categories
        if not re.search(bundle_pattern, normalized_bundle_text, re.I)
    ]
    if not missing:
        return []
    return [
        "agent-first candidate must project explicit host Agent evidence preferences into runnable surfaces: "
        + "missing "
        + ", ".join(missing)
    ]


def agent_candidate_evidence_preference_categories(task_text: str, *, require_explicit_marker: bool = True) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    explicit_evidence_markers = (
        r"\b(?:evidence|proof|verification|verify)\b.{0,80}\b(?:must|should|prefer|include|require|needs?)\b",
        r"\b(?:must|should|prefer|include|require|needs?)\b.{0,80}\b(?:evidence|proof|verification|verify)\b",
        r"证据.{0,24}(?:必须|需要|优先|包括|包含)",
        r"(?:必须|需要|优先|包括|包含).{0,24}(?:证据|证明|验证)",
    )
    if require_explicit_marker and not any(re.search(pattern, text, re.I) for pattern in explicit_evidence_markers):
        return []
    categories: list[tuple[str, str]] = [
        (
            "evidence/proof",
            r"\b(?:evidence|proof|verify|verification|verified|proven)\b|证据|证明|验证|已证明",
        ),
    ]
    category_patterns = (
        (
            "browser/journey",
            r"\b(?:browser|playwright|journey|end[- ]?to[- ]?end|e2e)\b|浏览器|旅程|端到端",
        ),
        (
            "command/test",
            r"\b(?:command|cli|script|test|tests|pytest|unit|contract|lint|typecheck)\b|命令|脚本|测试|契约|类型检查",
        ),
        (
            "audit/log",
            r"\b(?:audit|auditing|audit[- ]?log|log|logs|ledger|trace)\b|审计|日志|账本|追踪",
        ),
        (
            "permission/auth",
            r"\b(?:permission|permissions|authorization|auth|access)\b|权限|授权|访问",
        ),
        (
            "payment/refund/billing",
            r"\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账",
        ),
        (
            "data/export/report",
            r"\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板",
        ),
        (
            "artifact/ref",
            r"\b(?:artifact|artifacts|file|files|ref|refs|report)\b|产物|文件|引用|报告",
        ),
        (
            "accessibility/a11y",
            r"\b(?:accessibility|a11y|screen[- ]?reader|keyboard|aria|focus|wcag|axe)\b|无障碍|可访问|读屏|屏幕阅读器|键盘|焦点",
        ),
        (
            "locale/i18n",
            r"\b(?:locale|locali[sz]ation|i18n|translation|language|chinese|english)\b|多语言|国际化|本地化|翻译|语言|中文|英文|英语",
        ),
        (
            "screenshot-is-weak",
            r"\b(?:screenshot|screenshots)\b|截图",
        ),
    )
    categories.extend((label, pattern) for label, pattern in category_patterns if re.search(pattern, text, re.I))
    return categories


def agent_candidate_traceability_terms(value: object) -> list[str]:
    terms = agreement_traceability_terms(value)
    for term in agreement_cjk_traceability_terms(value):
        if term not in terms:
            terms.append(term)
    return [term for term in terms if term not in ALIGNMENT_AGENT_CANDIDATE_GENERIC_TERMS][:12]


def agreement_traceability_terms(value: object) -> list[str]:
    text = str(value or "")
    if not text.strip():
        return []
    lowered_text = text.lower()
    markers = (
        "AGENTS.md",
        "design/README.md",
        "design/",
        "tests/",
        "package.json",
        "pyproject.toml",
    )
    terms: list[str] = [marker.lower() for marker in markers if marker.lower() in lowered_text]
    normalized = normalize_alignment_traceability_text(text)
    for raw_term in re.findall(r"[a-z0-9][a-z0-9_.-]{3,}", normalized):
        term = raw_term.strip("._-")
        if not term or term in ALIGNMENT_TRACEABILITY_GENERIC_TERMS:
            continue
        if re.fullmatch(r"\d+", term):
            continue
        if term not in terms:
            terms.append(term)
    return terms[:12]


def agreement_repeated_cjk_traceability_terms(values: object) -> list[str]:
    counts: dict[str, int] = {}
    order: dict[str, int] = {}
    for value in list(values or []):
        seen_in_value: set[str] = set()
        for term in agreement_cjk_traceability_terms(value):
            if term in seen_in_value:
                continue
            seen_in_value.add(term)
            counts[term] = counts.get(term, 0) + 1
            if term not in order:
                order[term] = len(order)
    return [term for term, count in sorted(counts.items(), key=lambda item: (-item[1], order[item[0]])) if count >= 3][:12]


def agreement_cjk_traceability_terms(value: object) -> list[str]:
    terms: list[str] = []
    for raw_sequence in re.findall(r"[\u4e00-\u9fff]{2,}", str(value or "")):
        sequence = raw_sequence.strip("".join(ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS))
        if len(sequence) < 2:
            continue
        if (
            2 <= len(sequence) <= 4
            and sequence not in ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS
            and not any(char in ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS for char in sequence)
        ):
            terms.append(sequence)
        for index in range(0, len(sequence) - 1, 2):
            term = sequence[index : index + 2]
            if term not in ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS and not any(char in ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS for char in term):
                terms.append(term)
    return list(dict.fromkeys(terms))

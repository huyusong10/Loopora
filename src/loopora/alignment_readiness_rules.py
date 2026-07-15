from __future__ import annotations

import re

from loopora.alignment_readiness_improvement import (
    alignment_improvement_readiness_issues as alignment_improvement_readiness_issues,
)
from loopora.alignment_readiness_improvement import (
    ALIGNMENT_READINESS_EVIDENCE_KEYS as ALIGNMENT_READINESS_EVIDENCE_KEYS,
    has_any_marker as has_any_marker,
)
from loopora.alignment_semantics import semantic_antipattern_match_is_negated, text_mentions_loop_fit_contradiction
from loopora.residual_risk_support import residual_risk_is_unmanaged




from loopora.service_alignment_workdir_snapshot import alignment_workdir_snapshot_has_governance_markers

GOVERNANCE_MARKER_PATTERN = (
    r"agents\.md|design/readme\.md|design/|tests/|project-local|project local|"
    r"local\s+design/test|design/test\s+obligations?|skipped\s+local\s+governance|项目本地"
)

def local_governance_evidence_issue(text: str, *, workdir_snapshot: str = "") -> bool:
    if not re.search(GOVERNANCE_MARKER_PATTERN, text, re.IGNORECASE) and not alignment_workdir_snapshot_has_governance_markers(
        workdir_snapshot
    ):
        return False
    return not alignment_governance_marker_responsibilities_present(text)

def alignment_governance_marker_responsibilities_present(text: str) -> bool:
    builder_reads = alignment_governance_marker_responsibility_present(
        text,
        actor_pattern=r"\b(?:builder|generator)\b|构建者|构建|执行方|实施方",
        action_pattern=(
            r"\b(?:read|reads|consult|consults|follow|follows|respect|respects|use|uses|using|locate|locates|identify|identifies)\b"
            r"|读取|查阅|查找|定位|识别|遵守|遵循|使用|读"
        ),
    )
    review_checks = alignment_governance_marker_responsibility_present(
        text,
        actor_pattern=r"\b(?:inspector|inspectors|custom|review|reviewer|reviewers)\b|检查者|巡检|检查|审查|验证|检视方|评审方",
        action_pattern=r"\b(?:verify|verifies|verification|check|checks|review|reviews|validate|validates|test|tests)\b|检查|审查|验证|测试|核对",
    )
    gatekeeper_gates = alignment_governance_marker_responsibility_present(
        text,
        actor_pattern=r"\b(?:gatekeeper|gate keeper|verifier)\b|守门|裁决|最终判断|最终裁决|收口|验收",
        action_pattern=(
            r"\b(?:weak|unproven|blocking|block|blocks|missing|skipped|fail closed|reject|rejects|gate|gates|gating)\b"
            r"|弱证据|未证明|阻断|缺少|跳过|拒绝|视为"
        ),
    )
    return builder_reads and review_checks and gatekeeper_gates

def alignment_governance_marker_responsibility_present(
    text: str,
    *,
    actor_pattern: str,
    action_pattern: str,
) -> bool:
    segments = re.split(r"[\n.;。；]+", text)
    marker_windows: list[str] = []
    for match in re.finditer(GOVERNANCE_MARKER_PATTERN, text, flags=re.IGNORECASE):
        start = max(0, match.start() - 320)
        end = min(len(text), match.end() + 320)
        marker_windows.append(text[start:end])
    for segment in [*segments, *marker_windows]:
        if (
            re.search(GOVERNANCE_MARKER_PATTERN, segment, flags=re.IGNORECASE)
            and re.search(actor_pattern, segment, flags=re.IGNORECASE)
            and re.search(action_pattern, segment, flags=re.IGNORECASE)
        ):
            return True
    return False

def workdir_facts_evidence_issue(text: str, *, workdir_snapshot: str = "") -> bool:
    has_grounding_marker = has_any_marker(
        text,
        (
            "observed",
            "snapshot",
            "appears",
            "assumption",
            "assumed",
            "unknown",
            "uncertain",
            "cannot confirm",
            "empty",
            "观察",
            "看到",
            "快照",
            "看起来",
            "假设",
            "未知",
            "不确定",
            "无法确认",
            "空目录",
        ),
    )
    if not has_grounding_marker:
        return True
    return workdir_facts_claims_unsupported_observed_stack(text, workdir_snapshot=workdir_snapshot)

def workdir_facts_claims_unsupported_observed_stack(text: str, *, workdir_snapshot: str = "") -> bool:
    if not has_any_marker(text, ("observed", "snapshot", "appears", "观察", "看到", "快照", "看起来")):
        return False
    if has_any_marker(text, ("unknown", "uncertain", "assumption", "无法确认", "未知", "不确定", "假设")):
        return False
    snapshot = str(workdir_snapshot or "").lower()
    support_markers = {
        "package.json": (
            r"\breact\b",
            r"\bvue\b",
            r"\bsvelte\b",
            r"\bnext(?:\.js|js)\b",
            r"\bvite\b",
            r"\bnode(?:\.js|js)?\b",
            r"\bnpm\b",
            r"\bpnpm\b",
            r"\byarn\b",
            r"\bjavascript\b",
            r"\btypescript\b",
            r"\bfrontend\b",
            "前端",
        ),
        "pyproject.toml": (
            r"\bpython\b",
            r"\bpytest\b",
            r"\bruff\b",
            r"\buv\b",
            r"\bfastapi\b",
            r"\bdjango\b",
            r"\bflask\b",
        ),
        "requirements.txt": (r"\bpython\b", r"\bpytest\b", r"\bfastapi\b", r"\bdjango\b", r"\bflask\b"),
        "cargo.toml": (r"\brust\b", r"\bcargo\b"),
        "go.mod": (r"\bgolang\b", r"\bgo\s+(?:service|backend|app|module|project|codebase|stack|server)\b"),
    }
    unsupported_terms: list[str] = []
    for marker, terms in support_markers.items():
        if _snapshot_supports_marker(snapshot, marker):
            continue
        unsupported_terms.extend(term for term in terms if _term_has_unsupported_stack_claim(term, text))
    return bool(unsupported_terms)

def _term_has_unsupported_stack_claim(term_pattern: str, text: str) -> bool:
    for match in re.finditer(term_pattern, text):
        context = text[max(0, match.start() - 140) : match.end() + 140]
        if not has_any_marker(context, ("observed", "snapshot", "appears", "观察", "看到", "快照", "看起来")):
            continue
        if _stack_term_context_is_fake_done_or_negated(context):
            continue
        return True
    return False

def _stack_term_context_is_fake_done_or_negated(context: str) -> bool:
    return has_any_marker(
        context,
        (
            "fake done",
            "fake-done",
            "fail closed",
            "fails closed",
            "must fail",
            "must not pass",
            "cannot pass",
            "block ",
            "blocking",
            "do not accept",
            "not accept",
            "do not claim",
            "shallow",
            "frontend-only",
            "ui-only",
            "screenshot-only",
            "mock-only",
            "happy-path-only",
            "status-only",
            "prose-only",
            "missing ",
            "缺失",
            "阻断",
            "浅层",
            "只前端",
            "仅前端",
            "只.*界面",
            "solo frontend",
            "frontend-only",
        ),
    )

def _snapshot_supports_marker(snapshot: str, marker: str) -> bool:
    marker_text = marker.lower()
    marker_pattern = re.escape(marker_text)
    if re.search(rf"(?m)^\s*-\s*{marker_pattern}\s*$", snapshot):
        return True
    if re.search(rf"(?m)^\s*{marker_pattern}\s*$", snapshot):
        return True
    for line in snapshot.splitlines():
        label, separator, value = line.partition(":")
        if separator and label.strip().lower() == "detected markers":
            detected = {item.strip().lower() for item in value.split(",")}
            if marker_text in detected:
                return True
    return False


def readiness_evidence_issues(output: dict, *, workdir_snapshot: str = "") -> list[str]:
    evidence = output.get("readiness_evidence")
    if not isinstance(evidence, dict):
        return ["readiness_evidence"]
    generic_values = {
        "ok",
        "yes",
        "true",
        "done",
        "ready",
        "clear",
        "确认",
        "已确认",
        "无",
        "none",
        "n/a",
        "na",
        "unknown",
        "tbd",
    }
    issues: list[str] = []
    for key in ALIGNMENT_READINESS_EVIDENCE_KEYS:
        text = str(evidence.get(key, "") or "").strip()
        normalized = text.lower()
        if (
            len(text) < 16
            or normalized in generic_values
            or readiness_evidence_semantic_issue(
                key,
                text,
                workdir_snapshot=workdir_snapshot,
            )
        ):
            issues.append(key)
    if open_questions_readiness_issue(evidence):
        issues.append("open_questions")
    if readiness_evidence_bucket_projection_issue(evidence):
        issues.append("evidence_buckets")
    if readiness_evidence_task_scoped_issue(evidence):
        issues.append("task_scoped_judgment")
    return issues


def readiness_evidence_bucket_projection_issue(evidence: dict) -> bool:
    text = " ".join(str(evidence.get(key, "") or "") for key in ALIGNMENT_READINESS_EVIDENCE_KEYS)
    bucket_patterns = {
        "proven": r"\bproven\b|已证明",
        "weak": r"\bweak\b|弱证据|证据薄弱",
        "unproven": r"\bunproven\b|未证明",
        "blocking": r"\bblocking\b|阻断",
        "residual": r"\bresidual risk\b|残余风险",
    }
    return not all(re.search(pattern, text, re.IGNORECASE) for pattern in bucket_patterns.values())


def readiness_evidence_task_scoped_issue(evidence: dict) -> bool:
    text = re.sub(
        r"\s+",
        " ",
        " ".join(str(evidence.get(key, "") or "") for key in ALIGNMENT_READINESS_EVIDENCE_KEYS),
    ).strip()
    patterns = (
        r"\b(?:global|permanent|always-on|chat-wide)\s+(?:user\s+)?"
        r"(?:persona|personality|preference|preferences|memory|trait|style)\b",
        r"\b(?:persona|personality|preference|preferences|style)\s+(?:memory|profile)\b",
        r"\b(?:remember|store|capture|codify)\s+(?:the\s+)?(?:user's|my)\s+"
        r"(?:persona|personality|preference|preferences|style|traits?)\b",
        r"\balways\s+(?:follow|use|prefer|behave|act|answer)\b.{0,80}\b(?:user|my)\b.{0,80}"
        r"\b(?:persona|personality|preference|preferences|style|trait)\b",
        r"全局(?:人格|偏好|记忆|画像)",
        r"永久(?:人格|偏好|记忆|画像)",
        r"(?:人格|偏好|用户画像|用户特质).{0,8}(?:记忆|长期记住|全局继承)",
        r"记住.{0,12}(?:我的|用户).{0,8}(?:偏好|人格|风格)",
        r"总是.{0,16}(?:按|遵循|使用).{0,12}(?:偏好|人格|风格)",
    )
    value = text.lower()
    for pattern in patterns:
        for match in re.finditer(pattern, value, re.IGNORECASE):
            if semantic_antipattern_match_is_negated(value, match.start()):
                continue
            return True
    return False

def open_questions_readiness_issue(evidence: dict) -> bool:
    text = str(evidence.get("open_questions", "") or "").strip()
    if not text:
        return False
    normalized = text.lower()
    normalized_value = normalized.strip(" \t\r\n.。:：;；")
    exact_closed_values = {
        "none",
        "n/a",
        "na",
        "无",
        "没有",
    }
    closed_markers = (
        "no open questions",
        "no-open-questions",
        "no unresolved questions",
        "no unresolved bundle-shaping questions",
        "no unresolved bundle shaping questions",
        "no remaining questions",
        "no remaining task-shaping questions",
        "none beyond explicit confirmation",
        "explicit confirmation only",
        "explicit-confirmation-only",
        "only remaining step is explicit confirmation",
        "无未解决问题",
        "没有未解决问题",
        "没有开放问题",
        "没有剩余问题",
        "只等待明确确认",
        "仅等待明确确认",
        "仅剩明确确认",
    )
    confirmation_only_markers = (
        "waiting for explicit user confirmation of the working agreement",
        "waiting for explicit user confirmation of the improvement agreement",
        "waiting for user confirmation of the working agreement",
        "waiting for user confirmation of the improvement agreement",
        "esperando confirmación explícita del usuario sobre el acuerdo de trabajo",
        "esperando confirmación del usuario sobre el acuerdo de trabajo",
        "solo falta confirmación explícita del usuario sobre el acuerdo de trabajo",
        "等待用户明确确认这份工作协议",
        "等待用户明确确认这份改进协议",
        "等待用户确认这份工作协议",
        "等待用户确认这份改进协议",
    )
    return not (
        normalized_value in exact_closed_values
        or has_any_marker(normalized, closed_markers)
        or has_any_marker(normalized, confirmation_only_markers)
    )


def readiness_evidence_semantic_issue(key: str, text: str, *, workdir_snapshot: str = "") -> bool:
    normalized = str(text or "").lower()
    simple_checks = {
        "loop_fit": loop_fit_evidence_contradiction_issue,
        "success_surface": success_surface_evidence_placeholder_issue,
        "fake_done_risks": fake_done_evidence_placeholder_issue,
        "evidence_preferences": evidence_preference_placeholder_issue,
        "role_posture": role_posture_placeholder_issue,
    }
    if key in simple_checks:
        return simple_checks[key](normalized)
    if key == "local_governance":
        return local_governance_evidence_issue(
            normalized,
            workdir_snapshot=workdir_snapshot,
        )
    if key == "workdir_facts":
        return workdir_facts_evidence_issue(normalized, workdir_snapshot=workdir_snapshot)
    if key == "residual_risk_policy":
        return residual_risk_is_unmanaged(text)
    return False


def loop_fit_evidence_contradiction_issue(value: str) -> bool:
    return text_mentions_loop_fit_contradiction(value)


def success_surface_evidence_placeholder_issue(value: str) -> bool:
    if success_surface_evidence_has_concrete_anchor(value):
        return False
    generic_patterns = (
        r"\b(?:good and useful|works? well|high[- ]quality result|successful result|good result)\b",
        r"(?:好用|有用(?:的|性|处|价值|结果|产物|成果|且|并|又|、|，|。|；|,|\.|;|\s|$)|效果好|高质量|结果好)",
    )
    return any(re.search(pattern, value, re.IGNORECASE) for pattern in generic_patterns)


def success_surface_evidence_has_concrete_anchor(value: str) -> bool:
    observable_markers = (
        r"\b(?:primary path|primary flow|journey|audit record|provider|permission|refund|download|export|"
        r"register|sign[- ]up|onboard|checkout|payment|upload|import|search|error|recovery|fallback)\b",
        r"新用户|主流程|核心路径|关键操作|注册|进入|错误|恢复路径|失败时|权限|退款|下载|导出|支付|上传|导入|搜索|审计记录|provider|fallback",
    )
    proof_markers = (
        r"\b(?:prove|proves|verified|verifiable|evidence|artifact|audit|runnable|check|checks|test|tests|"
        r"command|log|gatekeeper|handoff)\b",
        r"证明|可验证|证据|产物|审计|可审计|可追踪|可运行|检查|测试|命令|日志|gatekeeper|handoff|裁决",
    )
    return any(re.search(pattern, value, re.IGNORECASE) for pattern in observable_markers) and any(
        re.search(pattern, value, re.IGNORECASE) for pattern in proof_markers
    )


def fake_done_evidence_placeholder_issue(value: str) -> bool:
    if not re.search(r"\b(?:avoid bugs?|no bugs?|high[- ]quality|bug[- ]free)\b|避免\s*bug|高质量|没有\s*bug", value, re.IGNORECASE):
        return False
    concrete_risk_markers = (
        r"\b(?:claim|claims|screenshot|happy[- ]path|proof|evidence|artifact|audit|permission|export|download|unproven|weak)\b",
        r"声称|截图|happy path|证明|证据|产物|审计|权限|导出|下载|未证明|弱证据",
    )
    return not any(re.search(pattern, value, re.IGNORECASE) for pattern in concrete_risk_markers)


def evidence_preference_placeholder_issue(value: str) -> bool:
    if not re.search(r"\b(?:need proof|enough proof|feel confident|evidence is needed|needs evidence)\b|需要证明|足够证明|有信心", value, re.IGNORECASE):
        return False
    proof_type_markers = (
        r"\b(?:test|tests|command|browser|journey|artifact|log|audit|screenshot|fixture|trace|coverage|contract|schema|lint)\b",
        r"测试|命令|浏览器|旅程|产物|日志|审计|截图|fixture|覆盖|契约|schema|lint",
    )
    return not any(re.search(pattern, value, re.IGNORECASE) for pattern in proof_type_markers)


def role_posture_placeholder_issue(value: str) -> bool:
    if role_posture_without_gatekeeper_judgment_issue(value):
        return True
    if not re.search(r"\b(?:use|add|configure)\s+(?:two|three|multiple|[2-9])\s+roles?\b|使用.{0,8}(?:两个|三个|多个|[2-9]\s*个).{0,6}角色", value, re.IGNORECASE):
        return False
    role_responsibility_markers = (
        r"\b(?:builder|inspector|guide|gatekeeper|custom|build|inspect|verify|judge|block|repair)\b",
        r"builder|inspector|guide|gatekeeper|构建|检查|验证|裁决|阻断|修复",
    )
    return not any(re.search(pattern, value, re.IGNORECASE) for pattern in role_responsibility_markers)


def role_posture_without_gatekeeper_judgment_issue(value: str) -> bool:
    mentions_role_work = re.search(
        r"\b(?:builder|inspector|guide|custom|build|inspect|verify|review|handoff)\b|构建|检查|验证|审查|交接",
        value,
        re.IGNORECASE,
    )
    if not mentions_role_work:
        return False
    gatekeeper_judgment = re.search(
        r"\bgatekeeper\b.{0,80}\b(?:judges?|decides?|verdict|blocks?|blockers?|closes?|finishes?|fails?[- ]closed|final|strict)\b|"
        r"\b(?:judges?|decides?|verdict|blocks?|blockers?|closes?|finishes?|fails?[- ]closed|final|strict)\b.{0,80}\bgatekeeper\b|"
        r"\bgatekeeper\b.{0,80}\b(?:juzga|decide|veredicto|bloquea|cierra|finaliza|falla\s+cerrado|final|estricto)\b|"
        r"\b(?:juzga|decide|veredicto|bloquea|cierra|finaliza|falla\s+cerrado|final|estricto)\b.{0,80}\bgatekeeper\b|"
        r"gatekeeper.{0,40}(?:裁决|判定|判断|阻断|收束|关闭|严格|失败关闭|最终)",
        value,
        re.IGNORECASE,
    )
    return gatekeeper_judgment is None

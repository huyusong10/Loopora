from __future__ import annotations

import re

from loopora.alignment_semantics import semantic_antipattern_match_is_negated, text_mentions_loop_fit_contradiction
from loopora.residual_risk_support import residual_risk_is_unmanaged
from loopora.service_alignment_context import alignment_workdir_snapshot_has_governance_markers

ALIGNMENT_READINESS_EVIDENCE_KEYS = (
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
)


def has_any_marker(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


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
    return not all(re.search(pattern, text, re.I) for pattern in bucket_patterns.values())


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
        for match in re.finditer(pattern, value, re.I):
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
        "no unresolved questions",
        "no remaining questions",
        "no remaining task-shaping questions",
        "none beyond explicit confirmation",
        "explicit confirmation only",
        "无未解决问题",
        "没有未解决问题",
        "没有开放问题",
        "没有剩余问题",
        "只等待明确确认",
        "仅等待明确确认",
    )
    confirmation_only_markers = (
        "waiting for explicit user confirmation of the working agreement",
        "waiting for explicit user confirmation of the improvement agreement",
        "waiting for user confirmation of the working agreement",
        "waiting for user confirmation of the improvement agreement",
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
    generic_patterns = (
        r"\b(?:good and useful|works? well|high[- ]quality result|successful result|good result)\b",
        r"(?:好用|有用|效果好|高质量|结果好)",
    )
    return any(re.search(pattern, value, re.I) for pattern in generic_patterns)


def fake_done_evidence_placeholder_issue(value: str) -> bool:
    if not re.search(r"\b(?:avoid bugs?|no bugs?|high[- ]quality|bug[- ]free)\b|避免\s*bug|高质量|没有\s*bug", value, re.I):
        return False
    concrete_risk_markers = (
        r"\b(?:claim|claims|screenshot|happy[- ]path|proof|evidence|artifact|audit|permission|export|download|unproven|weak)\b",
        r"声称|截图|happy path|证明|证据|产物|审计|权限|导出|下载|未证明|弱证据",
    )
    return not any(re.search(pattern, value, re.I) for pattern in concrete_risk_markers)


def evidence_preference_placeholder_issue(value: str) -> bool:
    if not re.search(r"\b(?:need proof|enough proof|feel confident|evidence is needed|needs evidence)\b|需要证明|足够证明|有信心", value, re.I):
        return False
    proof_type_markers = (
        r"\b(?:test|tests|command|browser|journey|artifact|log|audit|screenshot|fixture|trace|coverage|contract|schema|lint)\b",
        r"测试|命令|浏览器|旅程|产物|日志|审计|截图|fixture|覆盖|契约|schema|lint",
    )
    return not any(re.search(pattern, value, re.I) for pattern in proof_type_markers)


def role_posture_placeholder_issue(value: str) -> bool:
    if role_posture_without_gatekeeper_judgment_issue(value):
        return True
    if not re.search(r"\b(?:use|add|configure)\s+(?:two|three|multiple|[2-9])\s+roles?\b|使用.{0,8}(?:两个|三个|多个|[2-9]\s*个).{0,6}角色", value, re.I):
        return False
    role_responsibility_markers = (
        r"\b(?:builder|inspector|guide|gatekeeper|custom|build|inspect|verify|judge|block|repair)\b",
        r"builder|inspector|guide|gatekeeper|构建|检查|验证|裁决|阻断|修复",
    )
    return not any(re.search(pattern, value, re.I) for pattern in role_responsibility_markers)


def role_posture_without_gatekeeper_judgment_issue(value: str) -> bool:
    mentions_role_work = re.search(
        r"\b(?:builder|inspector|guide|custom|build|inspect|verify|review|handoff)\b|构建|检查|验证|审查|交接",
        value,
        re.I,
    )
    if not mentions_role_work:
        return False
    gatekeeper_judgment = re.search(
        r"\bgatekeeper\b.{0,80}\b(?:judges?|decides?|verdict|blocks?|blockers?|closes?|finishes?|fails?[- ]closed|final|strict)\b|"
        r"\b(?:judges?|decides?|verdict|blocks?|blockers?|closes?|finishes?|fails?[- ]closed|final|strict)\b.{0,80}\bgatekeeper\b|"
        r"gatekeeper.{0,40}(?:裁决|判定|判断|阻断|收束|关闭|严格|失败关闭|最终)",
        value,
        re.I,
    )
    return gatekeeper_judgment is None


def local_governance_evidence_issue(text: str, *, workdir_snapshot: str = "") -> bool:
    marker_pattern = r"agents\.md|design/readme\.md|design/|tests/|project-local|project local|项目本地|本地治理"
    if not re.search(marker_pattern, text, re.I) and not alignment_workdir_snapshot_has_governance_markers(
        workdir_snapshot
    ):
        return False
    return not alignment_governance_marker_responsibilities_present(text)


def alignment_governance_marker_responsibilities_present(text: str) -> bool:
    builder_reads = _alignment_governance_marker_responsibility_present(
        text,
        actor_pattern=r"\b(?:builder|generator)\b|构建者|构建",
        action_pattern=r"\b(?:read|reads|consult|consults|follow|follows|respect|respects)\b|读取|查阅|遵守|遵循",
    )
    review_checks = _alignment_governance_marker_responsibility_present(
        text,
        actor_pattern=r"\b(?:inspector|custom|review|reviewer)\b|检查者|巡检|检查|审查|验证",
        action_pattern=r"\b(?:verify|verifies|check|checks|review|reviews|validate|validates|test|tests)\b|检查|审查|验证|测试",
    )
    gatekeeper_gates = _alignment_governance_marker_responsibility_present(
        text,
        actor_pattern=r"\b(?:gatekeeper|gate keeper|verifier)\b|守门|裁决",
        action_pattern=(
            r"\b(?:weak|unproven|blocking|block|blocks|missing|skipped|fail closed|reject|rejects)\b"
            r"|弱证据|未证明|阻断|缺少|跳过|拒绝"
        ),
    )
    return builder_reads and review_checks and gatekeeper_gates


def _alignment_governance_marker_responsibility_present(text: str, *, actor_pattern: str, action_pattern: str) -> bool:
    marker_pattern = r"agents\.md|design/readme\.md|design/|tests/|project-local|project local|项目本地|本地治理"
    segments = re.split(r"[\n.;。；]+", text)
    marker_windows: list[str] = []
    for match in re.finditer(marker_pattern, text, flags=re.I):
        start = max(0, match.start() - 180)
        end = min(len(text), match.end() + 180)
        marker_windows.append(text[start:end])
    for segment in [*segments, *marker_windows]:
        if (
            re.search(marker_pattern, segment, flags=re.I)
            and re.search(actor_pattern, segment, flags=re.I)
            and re.search(action_pattern, segment, flags=re.I)
        ):
            return True
    return False


def alignment_improvement_readiness_issues(session: dict, output: dict) -> list[str]:
    previous_agreement = session.get("working_agreement") if isinstance(session.get("working_agreement"), dict) else {}
    if str(previous_agreement.get("mode") or "") != "improvement":
        return []
    evidence = output.get("readiness_evidence") if isinstance(output.get("readiness_evidence"), dict) else {}
    combined = " ".join(
        [
            str(output.get("agreement_summary", "") or ""),
            *(str(evidence.get(key, "") or "") for key in ALIGNMENT_READINESS_EVIDENCE_KEYS),
        ]
    ).lower()
    issues: list[str] = []
    if not has_any_marker(
        combined,
        (
            "preserve",
            "keep",
            "stable",
            "unchanged",
            "existing intent",
            "保留",
            "保持",
            "稳定",
            "不变",
            "既有意图",
        ),
    ):
        issues.append("improvement_preservation")
    if not has_any_marker(
        combined,
        (
            "change",
            "revise",
            "improve",
            "adjust",
            "feedback-driven",
            "source feedback",
            "user feedback",
            "review feedback",
            "run feedback",
            "feedback shows",
            "feedback proves",
            "evidence gap",
            "改进",
            "修订",
            "调整",
            "反馈驱动",
            "来源反馈",
            "用户反馈",
            "评审反馈",
            "运行反馈",
            "反馈证明",
            "证据缺口",
        ),
    ):
        issues.append("improvement_delta")
    if not has_any_marker(
        combined,
        (
            "spec",
            "role",
            "workflow",
            "evidence",
            "gatekeeper",
            "surface",
            "roles",
            "证据",
            "角色",
            "裁决",
            "治理面",
        ),
    ):
        issues.append("improvement_surface")
    source = previous_agreement.get("source") if isinstance(previous_agreement.get("source"), dict) else {}
    has_run_context = str(source.get("source_type") or "") == "run" and (
        source.get("coverage_summary") or source.get("evidence_summary") or source.get("task_verdict") or source.get("gatekeeper_verdict")
    )
    if has_run_context and not has_any_marker(
        combined,
        (
            "run evidence",
            "coverage",
            "verdict",
            "gatekeeper verdict",
            "evidence summary",
            "运行证据",
            "覆盖",
            "裁决",
            "证据摘要",
        ),
    ):
        issues.append("run_evidence_translation")
    source_completion_mode = str(source.get("source_completion_mode") or "").strip().lower()
    if source_completion_mode and source_completion_mode != "gatekeeper":
        has_source_completion_mode_delta = has_any_marker(
            combined,
            (
                "completion mode",
                "completion_mode",
                "`rounds`",
                "rounds completion",
                "source uses rounds",
                "run lifecycle",
                "lifecycle completion",
                "source completion",
                "完成模式",
                "运行生命周期",
                "生命周期收束",
            ),
        ) and has_any_marker(
            combined,
            (
                "gatekeeper",
                "task verdict",
                "evidence-based verdict",
                "证据裁决",
                "loop 裁决",
                "任务裁决",
                "守门",
            ),
        )
        if not has_source_completion_mode_delta:
            issues.append("improvement_completion_mode_delta")
    return issues


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
        "package.json": ("react", "vue", "svelte", "next", "vite", "node", "npm", "pnpm", "yarn", "javascript", "typescript", "frontend", "前端"),
        "pyproject.toml": ("python", "pytest", "ruff", "uv", "fastapi", "django", "flask"),
        "requirements.txt": ("python", "pytest", "fastapi", "django", "flask"),
        "cargo.toml": ("rust", "cargo"),
        "go.mod": ("go ", "golang"),
        "tests/ exists: yes": ("test", "tests", "testing", "测试"),
    }
    unsupported_terms = []
    for marker, terms in support_markers.items():
        if marker in snapshot:
            continue
        unsupported_terms.extend(term for term in terms if term in text)
    return bool(unsupported_terms)

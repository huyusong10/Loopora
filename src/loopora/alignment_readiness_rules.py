from __future__ import annotations

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

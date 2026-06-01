from __future__ import annotations

from loopora.alignment_readiness_shared import has_any_marker


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

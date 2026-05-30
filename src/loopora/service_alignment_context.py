from __future__ import annotations

import json
import os
import re
from hashlib import sha256
from pathlib import Path

from loopora.branding import APP_STATE_DIRNAME
from loopora.bundles import (
    BundleError,
    lint_alignment_bundle_generation_text,
    lint_alignment_bundle_semantics,
    load_bundle_text,
    read_bundle_file_text,
)
from loopora.event_redaction import redact_sensitive_text, redact_sensitive_value
from loopora.evidence_coverage import load_or_build_evidence_coverage_projection, summarize_evidence_coverage_projection
from loopora.run_artifacts import RunArtifactLayout
from loopora.run_artifacts import read_jsonl
from loopora.run_takeaways import build_judgment_contract
from loopora.service_types import LooporaError


ALIGNMENT_SOURCE_ARTIFACT_REF_KEYS = ("kind", "label", "relative_path", "workspace_path", "absolute_path")
ALIGNMENT_LANGUAGE_NEUTRAL_CONFIRMATIONS = {
    "确认",
    "已确认",
    "同意",
    "可以",
    "好",
    "好的",
    "没问题",
    "继续",
    "ok",
    "yes",
    "confirm",
    "approved",
    "go ahead",
    "proceed",
}


def alignment_source_option_id(source_type: str, identifier: object) -> str:
    normalized_identifier = str(identifier or "").strip()
    if source_type == "spec_file":
        digest = sha256(normalized_identifier.encode("utf-8")).hexdigest()[:16]
        return f"spec_file:{digest}"
    safe_identifier = re.sub(r"[^A-Za-z0-9_.:-]+", "-", normalized_identifier).strip("-")
    return f"{source_type}:{safe_identifier}"


def alignment_bundle_completion_mode(source_bundle: dict) -> str:
    bundle_loop = source_bundle.get("loop") if isinstance(source_bundle.get("loop"), dict) else {}
    return str(bundle_loop.get("completion_mode", "") or "")


def alignment_loop_bundle_id(loop: dict) -> str:
    bundle = loop.get("bundle") if isinstance(loop.get("bundle"), dict) else {}
    return str(bundle.get("id") or "").strip()


def alignment_revision_seed_bundle(source_bundle: dict) -> dict:
    seed = json.loads(json.dumps(source_bundle, ensure_ascii=False))
    metadata = dict(seed.get("metadata") or {})
    metadata["bundle_id"] = ""
    metadata.pop("source_bundle_id", None)
    metadata.pop("revision", None)
    seed["metadata"] = metadata
    return seed


def alignment_context_title_preview(content: str, *, limit: int = 80) -> str:
    text = " ".join(str(content or "").split()).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def alignment_context_title_from_session(session: dict) -> str:
    for entry in session.get("transcript") or []:
        if not isinstance(entry, dict) or entry.get("role") != "user":
            continue
        content = redact_sensitive_text(str(entry.get("content", "") or "").strip())
        if content:
            return alignment_context_title_preview(content)
    return str(session.get("id") or "alignment session")


def alignment_project_boundary(root: Path) -> Path | None:
    project_markers = (".git", "pyproject.toml", "package.json", "Cargo.toml", "go.mod")
    for candidate in (root, *root.parents):
        if any((candidate / marker).exists() for marker in project_markers):
            return candidate
    return None


def alignment_applicable_agents_paths(root: Path) -> list[Path]:
    boundary = alignment_project_boundary(root)
    search_dirs = [root]
    if boundary is not None:
        for parent in root.parents:
            search_dirs.append(parent)
            if parent == boundary:
                break

    agents_paths: list[Path] = []
    seen: set[Path] = set()
    for directory in search_dirs:
        agents_path = directory / "AGENTS.md"
        if agents_path in seen or not agents_path.is_file():
            continue
        seen.add(agents_path)
        agents_paths.append(agents_path)
    return agents_paths


def alignment_workdir_snapshot(workdir: Path) -> str:
    try:
        root = workdir.expanduser().resolve()
        if not root.exists() or not root.is_dir():
            return f"Workdir is not an accessible directory: {root}"
        entries = sorted(root.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
    except OSError as exc:
        return f"Workdir could not be inspected: {exc}"
    visible = [item for item in entries if item.name not in {".DS_Store", APP_STATE_DIRNAME}][:40]
    workdir_appears_empty = not visible
    marker_names = {
        "README.md",
        "README.zh-CN.md",
        "package.json",
        "pyproject.toml",
        "Cargo.toml",
        "go.mod",
        "pnpm-lock.yaml",
        "uv.lock",
        "requirements.txt",
        "AGENTS.md",
    }
    markers = [item.name for item in visible if item.name in marker_names]
    design_dir = root / "design"
    design_readme = design_dir / "README.md"
    tests_dir = root / "tests"
    agents_file = root / "AGENTS.md"
    applicable_agents = alignment_applicable_agents_paths(root)
    lines = [f"Top-level entries ({len(visible)} shown):"]
    if workdir_appears_empty:
        lines.append("Workdir appears empty. Treat technology choices as assumptions until the run verifies them.")
    for item in visible:
        suffix = "/" if item.is_dir() else ""
        lines.append(f"- {item.name}{suffix}")
    if markers:
        lines.append("Detected markers: " + ", ".join(markers))
    lines.append(f"AGENTS.md exists: {'yes' if agents_file.is_file() else 'no'}")
    lines.append(f"Applicable AGENTS.md exists: {'yes' if applicable_agents else 'no'}")
    if applicable_agents:
        agents_relpaths = [os.path.relpath(path, root) for path in applicable_agents]
        lines.append("Applicable AGENTS.md paths: " + ", ".join(agents_relpaths))
    lines.append(f"design/ exists: {'yes' if design_dir.is_dir() else 'no'}")
    lines.append(f"design/README.md exists: {'yes' if design_readme.is_file() else 'no'}")
    lines.append(f"tests/ exists: {'yes' if tests_dir.is_dir() else 'no'}")
    return "\n".join(lines)


def alignment_workdir_snapshot_has_governance_markers(workdir_snapshot: str) -> bool:
    snapshot = str(workdir_snapshot or "").lower()
    return any(
        marker in snapshot
        for marker in (
            "agents.md exists: yes",
            "applicable agents.md exists: yes",
            "design/ exists: yes",
            "design/readme.md exists: yes",
            "tests/ exists: yes",
        )
    )


def alignment_workdir_spec_candidates(state_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    root_spec = state_dir / "spec.md"
    if root_spec.is_file():
        candidates.append(root_spec)
    loops_dir = state_dir / "loops"
    if loops_dir.is_dir():
        candidates.extend(path for path in sorted(loops_dir.glob("*/spec.md")) if path.is_file())
    return candidates[:20]


def alignment_same_workdir(candidate: object, expected: Path) -> bool:
    candidate_text = str(candidate or "").strip()
    if not candidate_text:
        return False
    try:
        return Path(candidate_text).expanduser().resolve() == expected.expanduser().resolve()
    except OSError:
        return False


def alignment_assert_bundle_workdir(bundle: dict, *, expected_workdir: Path) -> None:
    actual = Path(str(bundle["loop"]["workdir"])).expanduser().resolve()
    expected = expected_workdir.expanduser().resolve()
    if actual != expected:
        raise LooporaError(f"bundle loop.workdir must be {expected}, got {actual}")


def alignment_bundle_file_is_valid_alignment_bundle(
    bundle_path: Path,
    *,
    expected_workdir: Path | None = None,
) -> bool:
    try:
        raw_yaml = read_bundle_file_text(bundle_path)
        generation_issues = lint_alignment_bundle_generation_text(raw_yaml)
        bundle = load_bundle_text(raw_yaml)
        if expected_workdir is not None:
            alignment_assert_bundle_workdir(bundle, expected_workdir=expected_workdir)
        semantic_issues = lint_alignment_bundle_semantics(bundle)
    except (BundleError, LooporaError, OSError):
        return False
    return not generation_issues and not semantic_issues


def alignment_bundle_file_has_ready_validation(bundle_path: Path, *, expected_workdir: Path | None = None) -> bool:
    validation_path = bundle_path.parent / "validation.json"
    try:
        payload = json.loads(validation_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        return False
    return alignment_bundle_file_is_valid_alignment_bundle(
        bundle_path,
        expected_workdir=expected_workdir,
    )


def alignment_session_has_current_ready_bundle(session: dict, bundle_path: Path) -> bool:
    expected_workdir = Path(session["workdir"]) if session.get("workdir") else None
    validation = session.get("validation") if isinstance(session.get("validation"), dict) else {}
    if validation.get("ok") is True:
        return alignment_bundle_file_is_valid_alignment_bundle(
            bundle_path,
            expected_workdir=expected_workdir,
        )
    return alignment_bundle_file_has_ready_validation(bundle_path, expected_workdir=expected_workdir)


def alignment_session_context_options(session: dict) -> list[dict]:
    session_id = str(session.get("id") or "").strip()
    if not session_id:
        return []
    title = alignment_context_title_from_session(session)
    status = str(session.get("status") or "")
    options: list[dict] = []
    if status in {"idle", "running", "waiting_user", "ready", "failed"}:
        options.append(
            {
                "option_id": alignment_source_option_id("continue_session", session_id),
                "action": "continue_session",
                "source_type": "alignment_session",
                "session_id": session_id,
                "status": status,
                "updated_at": session.get("updated_at", ""),
                "label_zh": f"继续对话：{title}",
                "label_en": f"Continue chat: {title}",
                "description_zh": "回到这个已有对话，并把下一条消息追加到同一个对话。",
                "description_en": "Return to this chat and append the next message to the same session.",
            }
        )
    bundle_path = Path(str(session.get("bundle_path") or ""))
    if status == "ready" and bundle_path.exists() and alignment_session_has_current_ready_bundle(session, bundle_path):
        options.append(
            {
                "option_id": alignment_source_option_id("alignment_session", session_id),
                "action": "improve",
                "source_type": "alignment_session",
                "source_alignment_session_id": session_id,
                "status": status,
                "bundle_path": str(bundle_path),
                "updated_at": session.get("updated_at", ""),
                "label_zh": f"基于 READY 方案改进：{title}",
                "label_en": f"Improve READY plan: {title}",
                "description_zh": "把这个对话的 READY 方案文件和对话摘要作为新对话的来源上下文。",
                "description_en": "Use this session's READY plan file and conversation summary as source context for a new chat.",
            }
        )
    return options


def alignment_text_has_cjk(value: object) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(value or ""))


def alignment_message_is_language_neutral_confirmation(message: object) -> bool:
    normalized = str(message or "").strip().lower()
    normalized = normalized.strip(" \t\r\n.!?。！？,，;；:：\"'“”‘’")
    return normalized in ALIGNMENT_LANGUAGE_NEUTRAL_CONFIRMATIONS


def alignment_prefers_chinese(session: dict) -> bool:
    text = "\n".join(
        str(item.get("content", "") or "")
        for item in (session.get("transcript") or [])
        if item.get("role") == "user" and not alignment_message_is_language_neutral_confirmation(item.get("content"))
    )
    return alignment_text_has_cjk(text)


def alignment_working_agreement_language_text(session: dict) -> str:
    agreement = session.get("working_agreement") if isinstance(session.get("working_agreement"), dict) else {}
    if not agreement:
        return ""
    language_projection = {
        "summary": agreement.get("summary", ""),
        "readiness_evidence": agreement.get("readiness_evidence") or {},
    }
    return json.dumps(language_projection, ensure_ascii=False)


def alignment_generation_prefers_chinese(session: dict) -> bool:
    agreement = session.get("working_agreement") if isinstance(session.get("working_agreement"), dict) else {}
    if str(session.get("alignment_stage") or "") == "ready_review" or isinstance(agreement.get("ready_review"), dict):
        agreement_text = alignment_working_agreement_language_text(session)
        if agreement_text.strip():
            return alignment_text_has_cjk(agreement_text)
    return alignment_prefers_chinese(session)


def alignment_user_language_hint(session: dict) -> str:
    agreement = session.get("working_agreement") if isinstance(session.get("working_agreement"), dict) else {}
    if (
        str(session.get("alignment_stage") or "") == "ready_review"
        or isinstance(agreement.get("ready_review"), dict)
    ) and alignment_working_agreement_language_text(session).strip():
        if alignment_generation_prefers_chinese(session):
            return "Chinese. Preserve the existing READY preview and working-agreement language unless the review feedback explicitly asks to translate; preserve Loopora terms unchanged."
        return "Preserve the existing READY preview and working-agreement language unless the review feedback explicitly asks to translate; preserve Loopora terms unchanged."
    if alignment_prefers_chinese(session):
        return "Chinese. Keep user-facing prose in Chinese and preserve Loopora terms unchanged."
    return "Follow the user's language from the transcript and preserve Loopora terms unchanged."


def add_alignment_context_option(option: dict, options: list[dict], seen_option_ids: set[str]) -> None:
    option_id = str(option.get("option_id") or "").strip()
    if not option_id or option_id in seen_option_ids:
        return
    for key in ("label_zh", "label_en", "description_zh", "description_en"):
        if key in option:
            option[key] = redact_sensitive_text(str(option.get(key) or ""))
    seen_option_ids.add(option_id)
    options.append(option)


def alignment_context_option_by_id(options: list[dict], option_id: str) -> dict:
    normalized_option_id = str(option_id or "").strip()
    if not normalized_option_id:
        return {}
    return next(
        (
            option
            for option in options
            if isinstance(option, dict) and str(option.get("option_id") or "").strip() == normalized_option_id
        ),
        {},
    )


def alignment_source_option_seed_kind(option: dict) -> str:
    source_type = str(option.get("source_type") or "").strip()
    if source_type in {"alignment_session", "alignment_session_file"}:
        return "alignment_session"
    return source_type


def bounded_alignment_context_options(options: list[dict], *, limit: int = 20) -> list[dict]:
    if len(options) <= limit:
        return options
    regenerate = next((option for option in options if option.get("option_id") == "regenerate"), None)
    bounded = options[:limit]
    if regenerate is not None and all(option.get("option_id") != "regenerate" for option in bounded):
        bounded = [*bounded[: max(0, limit - 1)], regenerate]
    return bounded


def alignment_file_bundle_context_option(*, source_session_id: str, bundle_path: Path) -> dict:
    return {
        "option_id": alignment_source_option_id("alignment_session_file", bundle_path),
        "action": "improve",
        "source_type": "alignment_session_file",
        "source_alignment_session_id": source_session_id,
        "bundle_path": str(bundle_path),
        "label_zh": f"基于本地 READY 方案改进：{source_session_id}",
        "label_en": f"Improve local READY plan: {source_session_id}",
        "description_zh": "读取同目录 .loopora 中的 READY 方案文件作为来源上下文。",
        "description_en": "Read the READY plan file from this workdir's .loopora state as source context.",
    }


def alignment_bundle_context_option(bundle_id: str, *, loop: dict, bundle: dict) -> dict:
    name = str(bundle.get("name") or loop.get("name") or bundle_id)
    return {
        "option_id": alignment_source_option_id("bundle", bundle_id),
        "action": "improve",
        "source_type": "bundle",
        "source_bundle_id": bundle_id,
        "source_loop_id": str(loop.get("id") or ""),
        "label_zh": f"基于已有方案改进：{name}",
        "label_en": f"Improve existing plan: {name}",
        "description_zh": "使用已导入方案文件里的任务契约、角色责任和运行流程作为候选基础。",
        "description_en": "Use the imported plan file's task contract, role responsibilities, and run flow as the candidate base.",
    }


def alignment_loop_context_option(loop: dict) -> dict:
    loop_id = str(loop.get("id") or "").strip()
    name = str(loop.get("name") or loop_id)
    return {
        "option_id": alignment_source_option_id("loop", loop_id),
        "action": "improve",
        "source_type": "loop",
        "source_loop_id": loop_id,
        "label_zh": f"基于已有 Loop 改进：{name}",
        "label_en": f"Improve existing Loop: {name}",
        "description_zh": "从这个 Loop 已保存的任务契约、角色责任和运行流程派生候选方案。",
        "description_en": "Derive a candidate plan from this Loop's saved task contract, role responsibilities, and run flow.",
    }


def alignment_run_artifact_paths(run: dict) -> dict:
    layout = RunArtifactLayout(Path(run["runs_dir"]))
    return {
        "run_contract": layout.relative(layout.run_contract_path),
        "task_verdict": layout.relative(layout.task_verdict_path),
        "evidence_ledger": layout.relative(layout.evidence_ledger_path),
        "evidence_coverage": layout.relative(layout.evidence_coverage_path),
        "evidence_manifest": layout.relative(layout.evidence_manifest_path),
    }


def alignment_run_judgment_contract(run: dict) -> dict:
    return build_judgment_contract(run)


def alignment_source_string_list(value: object, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)][:limit]


def alignment_source_artifact_refs(value: object, *, limit: int) -> list[dict]:
    if not isinstance(value, list):
        return []
    refs: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        refs.append(
            {
                key: item.get(key, "") if isinstance(item.get(key, ""), str) else ""
                for key in ALIGNMENT_SOURCE_ARTIFACT_REF_KEYS
            }
        )
        if len(refs) >= limit:
            break
    return refs


def alignment_run_evidence_summary(run: dict, *, limit: int = 8) -> list[dict]:
    layout = RunArtifactLayout(Path(run["runs_dir"]))
    if not layout.evidence_ledger_path.exists():
        return []
    items = [
        {
            "id": str(item.get("id") or ""),
            "kind": str(item.get("evidence_kind") or ""),
            "archetype": str(item.get("archetype") or ""),
            "step_id": str(item.get("step_id") or ""),
            "claim": str(item.get("claim") or "")[:500],
            "result": str(item.get("result") or ""),
            "residual_risk": str(item.get("residual_risk") or "")[:300],
            "verifies": alignment_source_string_list(item.get("verifies"), limit=8),
            "artifact_refs": alignment_source_artifact_refs(item.get("artifact_refs"), limit=6),
        }
        for item in read_jsonl(layout.evidence_ledger_path)
    ]
    return items[-limit:]


def alignment_run_coverage_summary(run: dict) -> dict:
    layout = RunArtifactLayout(Path(run["runs_dir"]))
    projection = load_or_build_evidence_coverage_projection(layout)
    summary = summarize_evidence_coverage_projection(
        projection,
        coverage_path_available=layout.evidence_coverage_path.exists(),
    )
    return {
        "ledger_path": summary.get("ledger_path", ""),
        "status": summary.get("status", ""),
        "reason": (summary.get("summary") or {}).get("reason", ""),
        "coverage_path": summary.get("coverage_path", ""),
        "evidence_count": summary.get("evidence_count", 0),
        "check_count": summary.get("check_count", 0),
        "covered_check_count": summary.get("covered_check_count", 0),
        "missing_check_count": summary.get("missing_check_count", 0),
        "covered_check_ids": list(summary.get("covered_check_ids") or [])[:20],
        "missing_check_ids": list(summary.get("missing_check_ids") or [])[:20],
        "target_count": summary.get("target_count", 0),
        "covered_target_count": summary.get("covered_target_count", 0),
        "weak_target_count": summary.get("weak_target_count", 0),
        "missing_target_count": summary.get("missing_target_count", 0),
        "blocked_target_count": summary.get("blocked_target_count", 0),
        "top_gaps": list(summary.get("top_gaps") or [])[:5],
        "evidence_kind_counts": summary.get("evidence_kind_counts") or {},
        "artifact_ref_count": summary.get("artifact_ref_count", 0),
        "residual_risk_count": summary.get("residual_risk_count", 0),
        "risk_signals": list(summary.get("risk_signals") or [])[:5],
        "latest_gatekeeper": summary.get("latest_gatekeeper") or {},
    }


def alignment_run_context_option(run: dict, *, loop: dict) -> dict:
    run_id = str(run.get("id") or "").strip()
    loop_name = str(loop.get("name") or run.get("loop_id") or "")
    return {
        "option_id": alignment_source_option_id("run", run_id),
        "action": "improve",
        "source_type": "run",
        "source_run_id": run_id,
        "source_loop_id": str(run.get("loop_id") or loop.get("id") or ""),
        "status": str(run.get("status") or ""),
        "artifact_paths": alignment_run_artifact_paths(run),
        "label_zh": f"基于最近运行证据改进：{loop_name}",
        "label_en": f"Improve from latest run evidence: {loop_name}",
        "description_zh": "把最近一次运行的 Loop 裁决、证据覆盖、守门裁决和证据路径作为改进依据。",
        "description_en": "Use the latest run's Loop verdict, evidence coverage, GateKeeper verdict, and evidence refs as improvement input.",
    }


def alignment_spec_file_context_option(spec_path: Path) -> dict:
    return {
        "option_id": alignment_source_option_id("spec_file", spec_path),
        "action": "start_from_spec",
        "source_type": "spec_file",
        "spec_path": str(spec_path),
        "label_zh": f"从已有任务契约开始：{spec_path.name}",
        "label_en": f"Start from existing spec: {spec_path.name}",
        "description_zh": "把这份任务契约作为线索，但仍通过对话补齐角色责任、运行流程和证据裁决。",
        "description_en": "Use this task contract as context while the chat still fills role responsibilities, run flow, and verdict evidence.",
    }


def bounded_alignment_file_text(path: Path, *, limit: int = 16000) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError:
        return "Source file could not be read as UTF-8 text."
    except OSError as exc:
        return f"Source file could not be read: {exc}"
    text = redact_sensitive_text(text)
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[Loopora truncated this source context for prompt size.]"


def alignment_transcript_source_summary(session: dict) -> list[dict]:
    entries = [entry for entry in (session.get("transcript") or []) if isinstance(entry, dict)]
    summary: list[dict] = []
    for entry in entries[-8:]:
        content = redact_sensitive_text(str(entry.get("content", "") or "").strip())
        if not content:
            continue
        summary.append(
            {
                "role": str(entry.get("role") or ""),
                "content": content[:600],
                "created_at": entry.get("created_at", ""),
            }
        )
    return summary


def redact_alignment_source_value(value: object, *, key: str = "") -> object:
    if isinstance(value, list):
        return [redact_alignment_source_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(child_key): redact_alignment_source_value(item, key=str(child_key))
            for child_key, item in value.items()
        }
    return redact_sensitive_value(key, value)


def alignment_source_seed_payload(
    source: dict,
    *,
    seed_bundle: dict | None = None,
    linked_bundle_id: str = "",
    linked_loop_id: str = "",
    linked_run_id: str = "",
) -> dict:
    redacted_source = redact_alignment_source_value(source)
    working_agreement = {
        "mode": str(source.get("mode") or "selected_source"),
        "source": redacted_source,
    }
    if isinstance(seed_bundle, dict) and seed_bundle:
        working_agreement["seed_bundle_metadata"] = redact_alignment_source_value(seed_bundle.get("metadata", {}))
    return {
        "working_agreement": working_agreement,
        "seed_bundle": seed_bundle or {},
        "linked_bundle_id": linked_bundle_id,
        "linked_loop_id": linked_loop_id,
        "linked_run_id": linked_run_id,
        "event": {
            "source_type": redacted_source.get("source_type", "") if isinstance(redacted_source, dict) else "",
            "source_bundle_id": redacted_source.get("source_bundle_id", "") if isinstance(redacted_source, dict) else "",
            "source_loop_id": redacted_source.get("source_loop_id", "") if isinstance(redacted_source, dict) else "",
            "source_run_id": redacted_source.get("source_run_id", "") if isinstance(redacted_source, dict) else "",
            "source_alignment_session_id": redacted_source.get("source_alignment_session_id", "") if isinstance(redacted_source, dict) else "",
            "spec_path": redacted_source.get("spec_path", "") if isinstance(redacted_source, dict) else "",
            "reason": redacted_source.get("reason", "") if isinstance(redacted_source, dict) else "",
        },
    }


def alignment_spec_file_source_seed(option: dict) -> dict:
    spec_path = Path(str(option.get("spec_path") or ""))
    source = {
        "mode": "selected_source",
        "source_type": "spec_file",
        "spec_path": str(spec_path),
        "reason": "start_from_workdir_spec",
        "spec_markdown": bounded_alignment_file_text(spec_path),
        "artifact_paths": {"spec": str(spec_path)},
    }
    return alignment_source_seed_payload(source)


def alignment_bundle_source_seed(option: dict, source_bundle: dict, *, seed_bundle: dict | None = None) -> dict:
    bundle_id = str(option.get("source_bundle_id") or "").strip()
    source = {
        "mode": "improvement",
        "source_type": "bundle",
        "source_bundle_id": bundle_id,
        "source_loop_id": str(option.get("source_loop_id") or source_bundle.get("loop_id") or ""),
        "source_run_id": "",
        "source_completion_mode": alignment_bundle_completion_mode(source_bundle),
        "reason": "improve_from_workdir_context",
        "run_status": "",
        "evidence_summary": [],
        "task_verdict": {},
        "gatekeeper_verdict": {},
    }
    return alignment_source_seed_payload(source, seed_bundle=seed_bundle, linked_bundle_id=bundle_id)


def alignment_bundle_revision_source_context(bundle_id: str, source_bundle: dict) -> dict:
    return {
        "mode": "improvement",
        "source_type": "bundle",
        "source_bundle_id": str(bundle_id or ""),
        "source_run_id": "",
        "source_completion_mode": alignment_bundle_completion_mode(source_bundle),
        "reason": "improve_imported_bundle",
        "run_status": "",
        "evidence_summary": [],
        "task_verdict": {},
        "gatekeeper_verdict": {},
    }


def alignment_loop_source_seed(
    option: dict,
    loop: dict,
    source_bundle: dict,
    *,
    seed_bundle: dict | None = None,
) -> dict:
    loop_id = str(option.get("source_loop_id") or "").strip()
    source = {
        "mode": "improvement",
        "source_type": "loop",
        "source_bundle_id": "",
        "source_loop_id": loop_id,
        "source_run_id": "",
        "source_completion_mode": alignment_bundle_completion_mode(source_bundle),
        "reason": "improve_from_workdir_loop",
        "source_loop_name": str(loop.get("name") or ""),
        "run_status": "",
        "evidence_summary": [],
        "task_verdict": {},
        "gatekeeper_verdict": {},
    }
    return alignment_source_seed_payload(source, seed_bundle=seed_bundle, linked_loop_id=loop_id)


def alignment_run_source_seed(  # noqa: PLR0913 - run source seeds expose explicit projection inputs from service lookup.
    option: dict,
    run: dict,
    source_bundle: dict,
    *,
    source_bundle_id: str = "",
    artifact_paths: dict | None = None,
    judgment_contract: dict | None = None,
    coverage_summary: dict | None = None,
    evidence_summary: list | None = None,
    seed_bundle: dict | None = None,
) -> dict:
    run_id = str(option.get("source_run_id") or "").strip()
    loop_id = str(run.get("loop_id") or "")
    source = {
        "mode": "improvement",
        "source_type": "run",
        "source_bundle_id": source_bundle_id,
        "source_loop_id": loop_id,
        "source_run_id": run_id,
        "source_completion_mode": alignment_bundle_completion_mode(source_bundle),
        "reason": "improve_from_workdir_run_evidence",
        "run_status": str(run.get("status") or ""),
        "artifact_paths": artifact_paths or {},
        "judgment_contract": judgment_contract or {},
        "coverage_summary": coverage_summary or {},
        "evidence_summary": evidence_summary or [],
        "task_verdict": run.get("task_verdict") or {},
        "gatekeeper_verdict": run.get("last_verdict_json") or {},
    }
    return alignment_source_seed_payload(
        source,
        seed_bundle=seed_bundle,
        linked_bundle_id=source_bundle_id,
        linked_loop_id=loop_id,
        linked_run_id=run_id,
    )


def alignment_run_revision_source_context(  # noqa: PLR0913 - run revision context exposes explicit projection inputs.
    run_id: str,
    run: dict,
    source_bundle: dict,
    *,
    source_bundle_id: str = "",
    artifact_paths: dict | None = None,
    judgment_contract: dict | None = None,
    coverage_summary: dict | None = None,
    evidence_summary: list | None = None,
) -> dict:
    return {
        "mode": "improvement",
        "source_type": "run",
        "source_bundle_id": source_bundle_id,
        "source_run_id": str(run_id or ""),
        "source_completion_mode": alignment_bundle_completion_mode(source_bundle),
        "reason": "improve_from_run_evidence",
        "run_status": str(run.get("status") or ""),
        "artifact_paths": artifact_paths or {},
        "judgment_contract": judgment_contract or {},
        "coverage_summary": coverage_summary or {},
        "evidence_summary": evidence_summary or [],
        "task_verdict": run.get("task_verdict") or {},
        "gatekeeper_verdict": run.get("last_verdict_json") or {},
    }


def alignment_session_source_seed(
    option: dict,
    source_session: dict,
    source_bundle: dict,
    *,
    seed_bundle: dict | None = None,
) -> dict:
    source_session_id = str(option.get("source_alignment_session_id") or "").strip()
    bundle_path = Path(str(option.get("bundle_path") or ""))
    source = {
        "mode": "improvement",
        "source_type": str(option.get("source_type") or "alignment_session"),
        "source_alignment_session_id": source_session_id,
        "source_bundle_id": "",
        "source_loop_id": "",
        "source_run_id": "",
        "source_completion_mode": alignment_bundle_completion_mode(source_bundle),
        "reason": "improve_from_workdir_alignment_session",
        "source_status": str(source_session.get("status") or option.get("status") or ""),
        "source_bundle_path": str(bundle_path),
        "transcript_summary": alignment_transcript_source_summary(source_session) if source_session else [],
        "run_status": "",
        "evidence_summary": [],
        "task_verdict": {},
        "gatekeeper_verdict": {},
    }
    return alignment_source_seed_payload(source, seed_bundle=seed_bundle)

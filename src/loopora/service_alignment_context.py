from __future__ import annotations

import re
from hashlib import sha256
from pathlib import Path

from loopora.event_redaction import redact_sensitive_text
from loopora.service_alignment_language import (
    alignment_generation_prefers_chinese as alignment_generation_prefers_chinese,
    alignment_message_is_language_neutral_confirmation as alignment_message_is_language_neutral_confirmation,
    alignment_prefers_chinese as alignment_prefers_chinese,
    alignment_text_has_cjk as alignment_text_has_cjk,
    alignment_user_language_hint as alignment_user_language_hint,
    alignment_working_agreement_language_text as alignment_working_agreement_language_text,
)
from loopora.service_alignment_source_seed import (
    alignment_bundle_completion_mode as alignment_bundle_completion_mode,
    alignment_bundle_revision_source_context as alignment_bundle_revision_source_context,
    alignment_bundle_source_seed as alignment_bundle_source_seed,
    alignment_loop_bundle_id as alignment_loop_bundle_id,
    alignment_loop_source_seed as alignment_loop_source_seed,
    alignment_revision_seed_bundle as alignment_revision_seed_bundle,
    alignment_run_revision_source_context as alignment_run_revision_source_context,
    alignment_run_source_seed as alignment_run_source_seed,
    alignment_session_source_seed as alignment_session_source_seed,
    alignment_source_seed_payload as alignment_source_seed_payload,
    alignment_spec_file_source_seed as alignment_spec_file_source_seed,
)
from loopora.service_alignment_source_seed import (
    alignment_transcript_source_summary as alignment_transcript_source_summary,
    bounded_alignment_file_text as bounded_alignment_file_text,
    redact_alignment_source_value as redact_alignment_source_value,
)
from loopora.service_alignment_workdir_snapshot import (
    alignment_applicable_agents_paths as alignment_applicable_agents_paths,
    alignment_project_boundary as alignment_project_boundary,
    alignment_same_workdir as alignment_same_workdir,
    alignment_workdir_snapshot as alignment_workdir_snapshot,
    alignment_workdir_snapshot_has_governance_markers as alignment_workdir_snapshot_has_governance_markers,
    alignment_workdir_spec_candidates as alignment_workdir_spec_candidates,
)
from loopora.service_alignment_run_source_projection import (
    alignment_run_artifact_paths as alignment_run_artifact_paths,
    alignment_run_coverage_summary as alignment_run_coverage_summary,
    alignment_run_evidence_summary as alignment_run_evidence_summary,
    alignment_run_judgment_contract as alignment_run_judgment_contract,
    alignment_source_artifact_refs as alignment_source_artifact_refs,
    alignment_source_string_list as alignment_source_string_list,
)

import json


from loopora.bundles import (
    BundleError,
    lint_alignment_bundle_generation_text,
    lint_alignment_bundle_semantics,
    load_bundle_text,
    read_bundle_file_text,
)

from loopora.service_types import LooporaError

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


ALIGNMENT_CONTEXT_TITLE_PREVIEW_LIMIT = 80


def alignment_source_option_id(source_type: str, identifier: object) -> str:
    normalized_identifier = str(identifier or "").strip()
    if source_type == "spec_file":
        digest = sha256(normalized_identifier.encode("utf-8")).hexdigest()[:16]
        return f"spec_file:{digest}"
    safe_identifier = re.sub(r"[^A-Za-z0-9_.:-]+", "-", normalized_identifier).strip("-")
    return f"{source_type}:{safe_identifier}"


def alignment_context_title_preview(content: str, *, limit: int = ALIGNMENT_CONTEXT_TITLE_PREVIEW_LIMIT) -> str:
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

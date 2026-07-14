from __future__ import annotations

import json
from pathlib import Path

from loopora.alignment_guidance import load_alignment_guidance_assets
from loopora.bundles import BundleError, read_bundle_file_text
from loopora.event_redaction import redact_sensitive_text
from loopora.service_alignment_prompt_templates import render_alignment_template
from loopora.service_alignment_source_context import redact_alignment_model_context_value
from loopora.workdir_inputs import PATH_PROBE_ERRORS


def alignment_improvement_context_text(session: dict) -> str:
    agreement = session.get("working_agreement") if isinstance(session.get("working_agreement"), dict) else {}
    mode = str(agreement.get("mode") or "")
    if mode not in {"improvement", "selected_source"}:
        return ""
    source = agreement.get("source") if isinstance(agreement.get("source"), dict) else {}
    prompt_source = redact_alignment_model_context_value(source)
    prompt_source = prompt_source if isinstance(prompt_source, dict) else {}
    artifact_paths_text = redact_sensitive_text(json.dumps(prompt_source.get("artifact_paths") or {}, ensure_ascii=False, indent=2))
    transcript_summary_text = redact_sensitive_text(json.dumps(prompt_source.get("transcript_summary") or [], ensure_ascii=False, indent=2))
    spec_markdown = redact_sensitive_text(str(prompt_source.get("spec_markdown") or ""))
    guidance = load_alignment_guidance_assets()
    selected_spec_markdown_block = ""
    if spec_markdown:
        selected_spec_markdown_block = render_alignment_template(
            guidance.selected_spec_markdown_template,
            {"spec_markdown": spec_markdown},
        )
    source_values = {
        "source_type": prompt_source.get("source_type", ""),
        "source_alignment_session_id": prompt_source.get("source_alignment_session_id", ""),
        "source_bundle_id": prompt_source.get("source_bundle_id", ""),
        "source_loop_id": prompt_source.get("source_loop_id", ""),
        "source_run_id": prompt_source.get("source_run_id", ""),
        "spec_path": prompt_source.get("spec_path", ""),
        "reason": prompt_source.get("reason", ""),
        "artifact_paths_json": artifact_paths_text,
        "transcript_summary_json": transcript_summary_text,
        "selected_spec_markdown_block": selected_spec_markdown_block,
    }
    selected_context = render_alignment_template(guidance.selected_source_context_template, source_values)
    if mode == "selected_source":
        return selected_context
    evidence_items = prompt_source.get("evidence_summary") if isinstance(prompt_source.get("evidence_summary"), list) else []
    evidence_text = redact_sensitive_text(json.dumps(evidence_items[:8], ensure_ascii=False, indent=2))
    coverage_text = redact_sensitive_text(json.dumps(prompt_source.get("coverage_summary") or {}, ensure_ascii=False, indent=2))
    judgment_contract_text = redact_sensitive_text(json.dumps(prompt_source.get("judgment_contract") or {}, ensure_ascii=False, indent=2))
    task_verdict_text = redact_sensitive_text(json.dumps(prompt_source.get("task_verdict") or {}, ensure_ascii=False, indent=2))
    verdict_text = redact_sensitive_text(json.dumps(prompt_source.get("gatekeeper_verdict") or {}, ensure_ascii=False, indent=2))
    improvement_context = render_alignment_template(
        guidance.bundle_improvement_context_template,
        {
            **source_values,
            "run_status": prompt_source.get("run_status", ""),
            "source_completion_mode": prompt_source.get("source_completion_mode", ""),
            "judgment_contract_json": judgment_contract_text,
            "coverage_summary_json": coverage_text,
            "task_verdict_json": task_verdict_text,
            "evidence_summary_json": evidence_text,
            "gatekeeper_verdict_json": verdict_text,
        },
    )
    return selected_context + "\n\n" + improvement_context


def alignment_current_bundle_prompt_text(bundle_path: Path) -> str:
    path = Path(bundle_path)
    try:
        if not path.exists():
            return ""
        return redact_sensitive_text(read_bundle_file_text(path))
    except (BundleError, *PATH_PROBE_ERRORS):
        return "Current bundle file could not be read."

from __future__ import annotations

import json


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


def alignment_agreement_language_issues(output: dict, *, evidence_keys: list[str], prefers_chinese: bool) -> list[str]:
    if not prefers_chinese:
        return []
    issues = []
    if not alignment_text_has_cjk(output.get("agreement_summary")):
        issues.append("agreement_summary")
    evidence = output.get("readiness_evidence")
    if not isinstance(evidence, dict):
        return [*issues, "readiness_evidence"]
    issues.extend(key for key in evidence_keys if not alignment_text_has_cjk(evidence.get(key)))
    return issues


def alignment_bundle_language_issues(bundle: dict, *, prefers_chinese: bool) -> list[str]:
    if not prefers_chinese:
        return []
    issues = []
    metadata = bundle.get("metadata") if isinstance(bundle.get("metadata"), dict) else {}
    loop = bundle.get("loop") if isinstance(bundle.get("loop"), dict) else {}
    field_values = {
        "metadata.name": metadata.get("name"),
        "metadata.description": metadata.get("description"),
        "loop.name": loop.get("name"),
        "collaboration_summary": bundle.get("collaboration_summary"),
        "spec.markdown": (bundle.get("spec") or {}).get("markdown") if isinstance(bundle.get("spec"), dict) else "",
        "workflow.collaboration_intent": ((bundle.get("workflow") or {}).get("collaboration_intent") if isinstance(bundle.get("workflow"), dict) else ""),
    }
    issues.extend(
        f"bundle field {field_name} must follow Chinese user language"
        for field_name, value in field_values.items()
        if not alignment_text_has_cjk(value)
    )
    for role in bundle.get("role_definitions", []):
        if not isinstance(role, dict):
            continue
        key = str(role.get("key", "") or "role")
        issues.extend(
            f"bundle role_definition {key}.{field_name} must follow Chinese user language"
            for field_name in ("name", "description", "prompt_markdown", "posture_notes")
            if not alignment_text_has_cjk(role.get(field_name))
        )
    return issues


def alignment_assistant_message_language_issue(assistant_message: str, *, prefers_chinese: bool) -> bool:
    return prefers_chinese and not alignment_text_has_cjk(assistant_message)


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

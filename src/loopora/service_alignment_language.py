from __future__ import annotations

import json
import re

from loopora.system_prompt_assets import load_system_prompt_asset


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
ALIGNMENT_LANGUAGE_NEUTRAL_CONFIRMATION_COMPACT_PHRASES = {
    "确认采用这份工作协议",
    "确认采用这份协议",
    "确认采用这份方案",
    "确认采用这个方向",
    "确认采用当前协议",
    "确认采用当前方案",
    "同意采用这份工作协议",
    "同意采用这份协议",
    "同意采用这份方案",
    "可以继续",
    "好的继续",
    "confirmusethisdirection",
    "confirmthisworkingagreement",
    "confirmothisworkingagreement",
    "confirmoesteacuerdodetrabajo",
    "confirmoesteacuerdo",
    "confirmousaestadirección",
    "confirmousaestadireccion",
}
ALIGNMENT_SPANISH_MARKER_RE = re.compile(
    r"\b(?:necesito|implementar|exportaci[oó]n|datos|clientes|auditor[ií]a|debe|probar|solo|"
    r"administradores|autorizados|pueden|tel[eé]fonos|redactados|fuga|tenants|archivo|generado|"
    r"prefiero|bloquear|cierre|falta|prueba|negativa|permisos|aislamiento|continuar|"
    r"revisión|evidencia|riesgo|gobernanza|acuerdo|trabajo|criterios|"
    r"éxito|falso|terminado|estrategia|ejecuci[oó]n|juicio|vista|previa|"
    r"consentimiento|preferencias|exportar|redacci[oó]n|autorizado|autorizada)\b",
    re.IGNORECASE,
)


def alignment_agreement_language_issues(
    output: dict,
    *,
    evidence_keys: list[str],
    prefers_chinese: bool,
    display_language: str = "",
) -> list[str]:
    language = alignment_language_from_preferences(prefers_chinese=prefers_chinese, display_language=display_language)
    if not language:
        return []
    issues = []
    if not alignment_text_matches_display_language(output.get("agreement_summary"), language=language):
        issues.append("agreement_summary")
    evidence = output.get("readiness_evidence")
    if not isinstance(evidence, dict):
        return [*issues, "readiness_evidence"]
    issues.extend(
        key
        for key in evidence_keys
        if not alignment_text_matches_display_language(evidence.get(key), language=language)
    )
    return issues


def alignment_bundle_language_issues(
    bundle: dict,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> list[str]:
    language = alignment_language_from_preferences(prefers_chinese=prefers_chinese, display_language=display_language)
    if not language:
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
        f"bundle field {field_name} must follow the user-facing task language"
        for field_name, value in field_values.items()
        if not alignment_text_matches_display_language(value, language=language)
    )
    for role in bundle.get("role_definitions", []):
        if not isinstance(role, dict):
            continue
        key = str(role.get("key", "") or "role")
        issues.extend(
            f"bundle role_definition {key}.{field_name} must follow the user-facing task language"
            for field_name in ("name", "description", "posture_notes")
            if not alignment_text_matches_display_language(role.get(field_name), language=language)
        )
    return issues


def alignment_assistant_message_language_issue(
    assistant_message: str,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> bool:
    language = alignment_language_from_preferences(prefers_chinese=prefers_chinese, display_language=display_language)
    return bool(language and not alignment_text_matches_display_language(assistant_message, language=language))


def alignment_language_from_preferences(*, prefers_chinese: bool, display_language: str = "") -> str:
    normalized = str(display_language or "").strip().lower()
    if normalized in {"zh", "es"}:
        return normalized
    return "zh" if prefers_chinese else ""


def alignment_text_has_cjk(value: object) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(value or ""))


def alignment_text_has_spanish(value: object) -> bool:
    normalized = str(value or "").strip().lower()
    if not normalized or alignment_text_has_cjk(normalized):
        return False
    if re.search(r"[áéíóúñ¿¡]", normalized, re.IGNORECASE):
        return True
    return len(set(ALIGNMENT_SPANISH_MARKER_RE.findall(normalized))) >= 2


def alignment_text_matches_display_language(value: object, *, language: str) -> bool:
    normalized = str(language or "").strip().lower()
    if normalized == "zh":
        return alignment_text_has_cjk(value)
    if normalized == "es":
        return alignment_text_has_spanish(value)
    return True


def alignment_text_looks_spanish(value: object) -> bool:
    normalized = str(value or "").strip().lower()
    if not normalized or alignment_text_has_cjk(normalized):
        return False
    markers = ALIGNMENT_SPANISH_MARKER_RE.findall(normalized)
    return len(set(markers)) >= 3


def alignment_message_is_language_neutral_confirmation(message: object) -> bool:
    normalized = str(message or "").strip().lower()
    normalized = normalized.strip(" \t\r\n.!?。！？,，;；:：\"'“”‘’")
    if normalized in ALIGNMENT_LANGUAGE_NEUTRAL_CONFIRMATIONS:
        return True
    if re.fullmatch(
        r"(?:confirm|confirmed|approve|approved|ok(?:ay)?|looks good)"
        r"[\s,;:.]*(?:use|adopt|go with|proceed with)?"
        r"[\s,;:.]*(?:this|the|that)?(?:[\s\w/-]{0,64})?"
        r"(?:direction|agreement|plan|workflow)",
        normalized,
    ):
        return True
    if re.fullmatch(
        r"(?:confirmo|confirmado|de acuerdo|ok)"
        r"[\s,;:.]*(?:usa|usar|adopta|adoptar)?"
        r"[\s,;:.]*(?:este|esta|el|la)?(?:[\s\w/-]{0,64})?"
        r"(?:direcci[oó]n|acuerdo|plan|workflow)",
        normalized,
    ):
        return True
    compact = re.sub(r"[\s.!?。！？,，;；:：\"'“”‘’]+", "", normalized)
    if re.fullmatch(r"(?:确认|同意)(?:采用|接受)?(?:这份|这个|当前)?.{0,24}(?:工作协议|协议|方案|方向)", compact):
        return True
    return compact in ALIGNMENT_LANGUAGE_NEUTRAL_CONFIRMATION_COMPACT_PHRASES


def alignment_prefers_chinese(session: dict) -> bool:
    text = "\n".join(
        str(item.get("content", "") or "")
        for item in (session.get("transcript") or [])
        if item.get("role") == "user" and not alignment_message_is_language_neutral_confirmation(item.get("content"))
    )
    return alignment_text_has_cjk(text)


def alignment_prefers_spanish(session: dict) -> bool:
    text = "\n".join(
        str(item.get("content", "") or "")
        for item in (session.get("transcript") or [])
        if item.get("role") == "user" and not alignment_message_is_language_neutral_confirmation(item.get("content"))
    )
    return alignment_text_looks_spanish(text)


def alignment_display_language(session: dict) -> str:
    if alignment_prefers_chinese(session):
        return "zh"
    if alignment_prefers_spanish(session):
        return "es"
    return ""


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
    agreement_text = alignment_generation_existing_agreement_language_text(session)
    if agreement_text.strip():
        return alignment_text_has_cjk(agreement_text)
    return alignment_prefers_chinese(session)


def alignment_generation_display_language(session: dict) -> str:
    agreement_text = alignment_generation_existing_agreement_language_text(session)
    if agreement_text.strip():
        if alignment_text_has_cjk(agreement_text):
            return "zh"
        if alignment_text_looks_spanish(agreement_text):
            return "es"
        return ""
    return alignment_display_language(session)


def alignment_generation_existing_agreement_language_text(session: dict) -> str:
    agreement = session.get("working_agreement") if isinstance(session.get("working_agreement"), dict) else {}
    if not agreement:
        return ""
    stage = str(session.get("alignment_stage") or "").strip()
    status = str(session.get("status") or "").strip()
    if (
        stage in {"confirmed", "compiling", "ready", "ready_review"}
        or status == "ready"
        or isinstance(agreement.get("ready_review"), dict)
    ):
        return alignment_working_agreement_language_text(session)
    return ""


def alignment_user_language_hint(session: dict) -> str:
    agreement = session.get("working_agreement") if isinstance(session.get("working_agreement"), dict) else {}
    if (
        str(session.get("alignment_stage") or "") == "ready_review"
        or isinstance(agreement.get("ready_review"), dict)
    ) and alignment_working_agreement_language_text(session).strip():
        return load_system_prompt_asset("alignment/ready-review-language-hint.md").strip()
    return load_system_prompt_asset("alignment/user-language-hint.md").strip()

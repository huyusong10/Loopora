from __future__ import annotations

from pathlib import Path

from alignment_language_service_test_support import create_chinese_alignment_session
from alignment_test_support import _confirm_alignment_agreement, _wait_for_status
from loopora.bundles import bundle_to_yaml, load_bundle_text
from loopora.executor import FakeCodexExecutor
from loopora.executor_alignment_bundle_fixtures import alignment_chinese_bundle_yaml
from loopora.executor_alignment_responses import alignment_response
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_language import alignment_bundle_language_issues


SPANISH_CHECKLIST = {
    "loop_fit": True,
    "task_scope": True,
    "success_surface": True,
    "fake_done_risks": True,
    "evidence_preferences": True,
    "execution_strategy": True,
    "residual_risk_policy": True,
    "judgment_tradeoffs": True,
    "local_governance": True,
    "role_posture": True,
    "workflow_shape": True,
}

SPANISH_EVIDENCE = {
    "loop_fit": (
        "La ejecución necesita evidencia posterior, handoffs y cierre con GateKeeper porque una sola pasada "
        "llega tarde para descubrir permisos débiles o redacción incompleta."
    ),
    "task_scope": "La exportación CSV queda limitada a permisos, redacción y auditoría.",
    "success_surface": "El éxito prueba permisos, redacción de datos y evidencia de auditoría.",
    "fake_done_risks": "Una descarga feliz o captura visual sin evidencia debe bloquear el cierre.",
    "evidence_preferences": (
        "La evidencia debe incluir prueba negativa de permisos, redacción, aislamiento y buckets Proven, Weak, Unproven, Blocking y Residual risk."
    ),
    "execution_strategy": (
        "Primero fijar contrato, luego construir exportación, después inspección y cierre; si la evidencia es Weak o Unproven, reparar antes de GateKeeper."
    ),
    "residual_risk_policy": ("El Residual risk menor necesita owner y follow-up; permisos, redacción y aislamiento deben fail closed."),
    "judgment_tradeoffs": "La evidencia estricta gana sobre velocidad de entrega o una vista previa bonita.",
    "local_governance": (
        "La gobernanza local de AGENTS.md, design/README.md, design/ y tests/ influye en la ejecución: "
        "Builder reads reglas locales, Inspector verifies evidencia de design/tests, y GateKeeper treats "
        "skipped governance as Weak, Unproven o Blocking."
    ),
    "role_posture": (
        "Builder construye, Inspector verifies evidencia y GateKeeper judges, blocks y closes según Proven, Weak, Unproven, Blocking y Residual risk."
    ),
    "workflow_shape": ("El flujo usa handoffs, inspección de evidencia y cierre con GateKeeper; evidencia Weak o Unproven cambia reparación antes del cierre."),
    "workdir_facts": ("El snapshot observed AGENTS.md, design/ y tests/ como gobernanza local; la pila de ejecución queda unknown."),
    "open_questions": "No open questions; solo queda confirmación explícita de ejecución.",
}


def spanish_export_bundle_with_english_summary(workdir: Path) -> dict:
    bundle = load_bundle_text(alignment_bundle_yaml(str(workdir.resolve())))
    bundle["metadata"]["name"] = "Exportación CSV"
    bundle["metadata"]["description"] = "Gobernanza de exportación CSV con permisos y redacción."
    bundle["loop"]["name"] = "Exportación CSV"
    bundle["collaboration_summary"] = "This Loop needs evidence-first governance before closure."
    bundle["spec"]["markdown"] = """# Task

Implementar exportación CSV de datos de clientes con permisos, redacción y auditoría.

# Done When

- Solo administradores autorizados pueden exportar datos.
- Teléfonos y tokens quedan redactados.
- La auditoría reconcilia cada archivo generado.

# Success Surface

- La revisión puede comprobar permisos, redacción, aislamiento y auditoría.

# Fake Done

- No puede pasar solo por una descarga feliz o una captura visual.

# Evidence Preferences

- Priorizar pruebas negativas de permisos, redacción de datos y evidencia de auditoría.

# Residual Risk

Riesgo residual menor necesita dueño; permisos, redacción y aislamiento fallan cerrado.

# Role Notes

## Exportación Builder Notes

Construye la exportación con permisos, redacción y evidencia local.

## Evidencia Inspector Notes

Verifica permisos, redacción, aislamiento y auditoría.

## Cierre GateKeeper Notes

Bloquea cierre sin evidencia probada.
"""
    for role in bundle["role_definitions"]:
        key = role["key"]
        archetype = role["archetype"]
        if key == "builder":
            role["name"] = "Exportación Builder"
            role["description"] = "Construye la exportación con permisos y redacción."
            role["prompt_markdown"] = (
                f"---\nversion: 1\narchetype: {archetype}\n---\n\nConstruye la exportación CSV y conserva evidencia de permisos y redacción."
            )
            role["posture_notes"] = "No aceptar una descarga feliz sin evidencia."
        elif key == "contract-inspector":
            role["name"] = "Evidencia Inspector"
            role["description"] = "Verifica permisos, redacción, aislamiento y auditoría."
            role["prompt_markdown"] = f"---\nversion: 1\narchetype: {archetype}\n---\n\nInspecciona evidencia de permisos, redacción, aislamiento y auditoría."
            role["posture_notes"] = "Clasifica evidencia débil como Blocking."
        elif key == "gatekeeper":
            role["name"] = "Cierre GateKeeper"
            role["description"] = "Decide cierre con evidencia probada."
            role["prompt_markdown"] = f"---\nversion: 1\narchetype: {archetype}\n---\n\nBloquea el cierre si faltan permisos, redacción o auditoría."
            role["posture_notes"] = "El cierre solo pasa con evidencia probada."
    bundle["workflow"]["collaboration_intent"] = "Builder construye, Inspector verifica evidencia y GateKeeper decide cierre."
    return bundle


class SpanishEnglishBundleExecutor(FakeCodexExecutor):
    def _build_payload(self, request) -> dict:
        if request.role != "alignment":
            return super()._build_payload(request)
        stage = str(request.extra_context.get("alignment_stage") or "clarifying")
        workdir = Path(str(request.extra_context.get("target_workdir") or request.workdir))
        if stage not in {"confirmed", "compiling", "ready_review"}:
            payload = alignment_response(
                status="question",
                assistant_message="Confirma este acuerdo de exportación CSV.",
                needs_user_input=True,
                bundle_yaml="",
                phase="agreement",
            )
            payload["agreement_summary"] = "Gobernanza de exportación CSV con permisos, redacción y auditoría."
            payload["readiness_checklist"] = {**SPANISH_CHECKLIST, "explicit_confirmation": False}
            payload["readiness_evidence"] = SPANISH_EVIDENCE
            payload["decision_options"] = [
                {
                    "id": "confirm_spanish_export",
                    "label": "Confirmar acuerdo (recomendado)",
                    "description": "Generar el workflow con permisos, redacción y auditoría.",
                    "recommended": True,
                    "user_reply": "Confirmo este acuerdo de exportación CSV.",
                }
            ]
            return payload
        payload = alignment_response(
            status="bundle",
            assistant_message="Vista previa preparada.",
            needs_user_input=False,
            bundle_yaml=bundle_to_yaml(spanish_export_bundle_with_english_summary(workdir)),
            phase="bundle",
        )
        payload["agreement_summary"] = "Gobernanza de exportación CSV con permisos, redacción y auditoría."
        payload["readiness_evidence"] = SPANISH_EVIDENCE
        return payload


def test_alignment_service_blocks_chinese_bundle_with_english_evidence(
    service_factory,
    sample_workdir: Path,
) -> None:
    service, created = create_chinese_alignment_session(
        service_factory,
        sample_workdir,
        scenario="alignment_english_bundle_for_chinese_user",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert "需要使用中文" in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_stage_blocked" and "agreement_summary" in event["payload"].get("missing", []) for event in events)


def test_alignment_service_rewrites_english_bundle_message_for_chinese_user(
    service_factory,
    sample_workdir: Path,
) -> None:
    service, created = create_chinese_alignment_session(
        service_factory,
        sample_workdir,
        scenario="alignment_english_assistant_message_for_chinese_bundle",
    )
    session = _confirm_alignment_agreement(service, created["id"])

    assert session["validation"]["ok"] is True
    assert session["transcript"][-1]["content"] == "已整理成一个可导入的 Loopora bundle。"
    assert "I prepared" not in session["transcript"][-1]["content"]
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_language_mismatch" and event["payload"].get("missing") == ["assistant_message"] for event in events)


def test_alignment_bundle_language_allows_locale_neutral_prompt_markdown(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_chinese_bundle_yaml(str(sample_workdir.resolve())))

    issues = alignment_bundle_language_issues(bundle, prefers_chinese=True)

    assert not any("prompt_markdown" in issue for issue in issues)


def test_alignment_chinese_bundle_projects_role_prompts_from_localized_asset(sample_workdir: Path) -> None:
    (sample_workdir / "AGENTS.md").write_text("# Rules\n\nRead local rules before editing.\n", encoding="utf-8")
    bundle = load_bundle_text(alignment_chinese_bundle_yaml(str(sample_workdir.resolve())))
    roles = {role["key"]: role for role in bundle["role_definitions"]}

    assert "谨慎构建聚焦 starter slice" in roles["builder"]["prompt_markdown"]
    assert "Builder 读取适用的项目本地治理入口" in roles["builder"]["prompt_markdown"]
    assert "对照 Done When" in roles["contract-inspector"]["prompt_markdown"]
    assert "GateKeeper 将跳过" in roles["gatekeeper"]["prompt_markdown"]
    assert "Build the focused starter slice" not in roles["builder"]["prompt_markdown"]


def test_alignment_service_blocks_chinese_bundle_with_english_prose(
    service_factory,
    sample_workdir: Path,
) -> None:
    service, created = create_chinese_alignment_session(
        service_factory,
        sample_workdir,
        scenario="alignment_english_bundle_prose_for_chinese_user",
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert not session["validation"]["ok"]
    assert "bundle field collaboration_summary must follow the user-facing task language" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_validation_failed" and "bundle field collaboration_summary" in event["payload"].get("error", "") for event in events
    )


def test_alignment_service_blocks_chinese_bundle_with_english_visible_names(
    service_factory,
    sample_workdir: Path,
) -> None:
    service, created = create_chinese_alignment_session(
        service_factory,
        sample_workdir,
        scenario="alignment_english_visible_bundle_names_for_chinese_user",
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert not session["validation"]["ok"]
    assert "bundle field metadata.name must follow the user-facing task language" in session["error_message"]
    assert "bundle field loop.name must follow the user-facing task language" in session["error_message"]
    assert "bundle role_definition builder.name must follow the user-facing task language" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_validation_failed" and "bundle role_definition builder.name" in event["payload"].get("error", "") for event in events
    )


def test_alignment_service_blocks_spanish_bundle_with_english_prose(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    service.executor_factory = lambda: SpanishEnglishBundleExecutor(scenario="success")
    created = service.create_alignment_session(
        workdir=sample_workdir,
        message=(
            "Necesito implementar una exportación CSV de datos de clientes para auditoría. "
            "Debe probar permisos, redacción de teléfonos y aislamiento; prefiero bloquear cierre sin evidencia."
        ),
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert not session["validation"]["ok"]
    assert "bundle field collaboration_summary must follow the user-facing task language" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_validation_failed" and "bundle field collaboration_summary" in event["payload"].get("error", "") for event in events
    )

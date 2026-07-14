from __future__ import annotations

from loopora.service_alignment_language import (
    alignment_agreement_language_issues,
    alignment_assistant_message_language_issue,
    alignment_bundle_language_issues,
    alignment_generation_display_language,
    alignment_message_is_language_neutral_confirmation,
    alignment_prefers_spanish,
)
from loopora.executor_alignment_task_anchors import alignment_task_anchor_from_user_message


def test_alignment_agreement_language_issues_are_disabled_when_chinese_is_not_preferred() -> None:
    assert (
        alignment_agreement_language_issues(
            {
                "agreement_summary": "English agreement.",
                "readiness_evidence": {"loop_fit": "English evidence."},
            },
            evidence_keys=["loop_fit"],
            prefers_chinese=False,
        )
        == []
    )


def test_alignment_agreement_language_issues_report_user_visible_non_chinese_fields() -> None:
    assert alignment_agreement_language_issues(
        {
            "agreement_summary": "English agreement.",
            "readiness_evidence": {
                "loop_fit": "需要持续证据。",
                "task_scope": "English scope.",
            },
        },
        evidence_keys=["loop_fit", "task_scope"],
        prefers_chinese=True,
    ) == ["agreement_summary", "task_scope"]


def test_alignment_agreement_language_issues_fail_closed_for_missing_evidence() -> None:
    assert alignment_agreement_language_issues(
        {"agreement_summary": "协议已经明确。", "readiness_evidence": ["bad"]},
        evidence_keys=["loop_fit"],
        prefers_chinese=True,
    ) == ["readiness_evidence"]


def test_alignment_bundle_language_issues_are_disabled_when_chinese_is_not_preferred() -> None:
    assert alignment_bundle_language_issues({"collaboration_summary": "English summary."}, prefers_chinese=False) == []


def test_alignment_bundle_language_issues_report_non_chinese_bundle_surfaces() -> None:
    issues = alignment_bundle_language_issues(
        {
            "metadata": {"name": "Starter", "description": "English description."},
            "loop": {"name": "Starter Loop"},
            "collaboration_summary": "English collaboration summary.",
            "spec": {"markdown": "中文 spec。"},
            "workflow": {"collaboration_intent": "中文 workflow。"},
            "role_definitions": [
                {
                    "key": "builder",
                    "name": "Builder",
                    "description": "中文描述。",
                    "prompt_markdown": "English prompt.",
                    "posture_notes": "中文姿态。",
                }
            ],
        },
        prefers_chinese=True,
    )

    assert issues == [
        "bundle field metadata.name must follow the user-facing task language",
        "bundle field metadata.description must follow the user-facing task language",
        "bundle field loop.name must follow the user-facing task language",
        "bundle field collaboration_summary must follow the user-facing task language",
        "bundle role_definition builder.name must follow the user-facing task language",
    ]


def test_alignment_bundle_language_issues_reject_rag_role_names_from_another_display_language() -> None:
    issues = alignment_bundle_language_issues(
        {
            "metadata": {"name": "RAG 长链治理", "description": "治理企业知识库 RAG 证据。"},
            "loop": {"name": "RAG 长链治理"},
            "collaboration_summary": "这个 RAG 任务需要分阶段证据治理。",
            "spec": {"markdown": "构建企业知识库 RAG support chatbot。"},
            "workflow": {"collaboration_intent": "先冻结合同，再分阶段构建与验证。"},
            "role_definitions": [
                {
                    "key": "rag-contract-inspector",
                    "name": "RAG Contract Inspector",
                    "description": "验证 RAG 合同。",
                    "prompt_markdown": "验证 source span、ACL 和工具安全。",
                    "posture_notes": "缺少证据时阻断。",
                },
                {
                    "key": "retrieval-acl-builder",
                    "name": "检索 ACL Builder",
                    "description": "实现权限过滤检索。",
                    "prompt_markdown": "构建 tenant filtering 证据。",
                    "posture_notes": "保留负向样本。",
                },
            ],
        },
        prefers_chinese=True,
    )

    assert "bundle role_definition rag-contract-inspector.name must follow the user-facing task language" in issues
    assert "bundle role_definition retrieval-acl-builder.name must follow the user-facing task language" not in issues


def test_alignment_language_issues_can_validate_spanish_visible_surfaces() -> None:
    agreement_issues = alignment_agreement_language_issues(
        {
            "agreement_summary": "English agreement.",
            "readiness_evidence": {
                "loop_fit": "La evidencia posterior y el juicio de GateKeeper son necesarios.",
                "task_scope": "English scope.",
            },
        },
        evidence_keys=["loop_fit", "task_scope"],
        prefers_chinese=False,
        display_language="es",
    )
    bundle_issues = alignment_bundle_language_issues(
        {
            "metadata": {"name": "Exportación CSV", "description": "English description."},
            "loop": {"name": "Exportación CSV"},
            "collaboration_summary": "La gobernanza necesita evidencia posterior.",
            "spec": {"markdown": "# Task\n\nProbar permisos y redacción de datos."},
            "workflow": {"collaboration_intent": "La evidencia guía el cierre."},
            "role_definitions": [
                {
                    "key": "builder",
                    "name": "Exportación Builder",
                    "description": "Construye la exportación con permisos.",
                    "prompt_markdown": "English prompt.",
                    "posture_notes": "Bloquear cierre sin evidencia.",
                }
            ],
        },
        prefers_chinese=False,
        display_language="es",
    )

    assert agreement_issues == ["agreement_summary", "task_scope"]
    assert bundle_issues == [
        "bundle field metadata.description must follow the user-facing task language",
    ]


def test_alignment_assistant_message_language_issue_tracks_chinese_preference() -> None:
    assert alignment_assistant_message_language_issue("I prepared the bundle.", prefers_chinese=True) is True
    assert alignment_assistant_message_language_issue("已整理方案。", prefers_chinese=True) is False
    assert alignment_assistant_message_language_issue("I prepared the bundle.", prefers_chinese=False) is False


def test_alignment_prefers_spanish_uses_substantive_task_text_not_confirmation() -> None:
    assert alignment_message_is_language_neutral_confirmation("Confirm; use this direction.")
    assert alignment_message_is_language_neutral_confirmation("Confirm; use this break-glass policy-first direction.")
    assert alignment_message_is_language_neutral_confirmation("Confirm; use this compliance contract-first direction.")
    assert alignment_message_is_language_neutral_confirmation("Confirm; use this residency contract-first direction.")
    assert alignment_message_is_language_neutral_confirmation("Confirm; use this webhook contract-first parallel evidence direction.")
    assert alignment_message_is_language_neutral_confirmation("Confirm; use this identity contract-first parallel evidence direction.")
    assert alignment_message_is_language_neutral_confirmation("Confirm; use this key rotation contract-first parallel evidence direction.")
    assert alignment_message_is_language_neutral_confirmation("Confirm; use this prompt asset ownership contract-first parallel evidence direction.")
    assert alignment_message_is_language_neutral_confirmation("Confirm; use this backup recovery contract-first parallel evidence direction.")
    assert alignment_message_is_language_neutral_confirmation("Confirmo; usa esta dirección.")
    assert alignment_message_is_language_neutral_confirmation("Confirmo; usa esta policy-first dirección.")
    assert alignment_message_is_language_neutral_confirmation("Confirmo este acuerdo de trabajo.")
    assert alignment_message_is_language_neutral_confirmation("确认，采用这份 RAG 长链工作协议。")

    assert alignment_prefers_spanish(
        {
            "transcript": [
                {
                    "role": "user",
                    "content": (
                        "Necesito implementar una exportación CSV de datos de clientes para auditoría; "
                        "debe probar permisos, redacción de teléfonos y aislamiento."
                    ),
                },
                {"role": "user", "content": "ok"},
            ]
        }
    )
    assert not alignment_prefers_spanish({"transcript": [{"role": "user", "content": "ok"}]})


def test_alignment_task_anchor_strips_mixed_confirmation_adjustment_prefix() -> None:
    assert (
        alignment_task_anchor_from_user_message("确认，但要调整：GateKeeper 不能接受截图或口头总结，必须看到命令输出。")
        == "GateKeeper 不能接受截图或口头总结，必须看到命令输出"
    )
    assert alignment_task_anchor_from_user_message("Looks good, but add a stricter proof gate.") == ("add a stricter proof gate")
    assert alignment_task_anchor_from_user_message("Confirmo, pero ajusta la evidencia mínima.") == ("ajusta la evidencia mínima")


def test_alignment_generation_display_language_projects_spanish_from_substantive_task_text() -> None:
    session = {
        "alignment_stage": "agreement_ready",
        "transcript": [
            {
                "role": "user",
                "content": (
                    "Necesito implementar una exportación CSV de datos de clientes para auditoría; debe probar permisos, redacción de teléfonos y aislamiento."
                ),
            },
            {"role": "user", "content": "ok"},
        ],
    }

    assert alignment_generation_display_language(session) == "es"


def test_alignment_generation_display_language_does_not_treat_repeated_english_loanword_as_spanish() -> None:
    session = {
        "alignment_stage": "confirmed",
        "status": "waiting_user",
        "transcript": [
            {
                "role": "user",
                "content": (
                    "Build SAML SSO plus SCIM provisioning for enterprise tenants. Existing password-login "
                    "tenants need migration notes, audit evidence, and security proof."
                ),
            },
            {"role": "user", "content": "Confirm; use this direction."},
        ],
        "working_agreement": {
            "summary": ("This task needs Loopora because enterprise identity tenants can fail in production if SAML, SCIM, audit, or migration proof is weak."),
            "readiness_evidence": {
                "loop_fit": (
                    "One Agent pass plus one human review is not enough for IdP variability, SCIM lifecycle drift, "
                    "audit completeness, and migration risks for existing tenants."
                )
            },
        },
    }

    assert alignment_generation_display_language(session) == ""

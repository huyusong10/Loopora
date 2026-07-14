from __future__ import annotations

from loopora.executor_alignment_agreement_evidence import (
    _auth_session_token_lifecycle_readiness_evidence,
    _identity_sso_readiness_evidence,
)
from loopora.executor_alignment_agreement_task_responses import (
    _agreement_task_clause,
    alignment_chinese_task_anchored_agreement_response,
    alignment_english_task_anchored_agreement_response,
    alignment_spanish_task_anchored_agreement_response,
)


def alignment_english_auth_session_token_lifecycle_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed auth session task")
    payload["assistant_message"] = (
        "Please confirm this auth session/token lifecycle working agreement; I will compile a session-token contract-first "
        "workflow with parallel Token Misuse and Session Revocation Audit inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this auth session/token lifecycle task through a contract-first Loop: {task}. "
        "Session Token Contract Inspector first freezes access/refresh expiry, refresh rotation, reuse detection, logout/all-device revocation, password reset and MFA invalidation, cookie flags, CSRF/API token boundaries, audit fields, monitoring, migration, and governance; "
        "Session Token Builder implements only from that handoff; Token Misuse Inspector and Session Revocation Audit Inspector inspect in parallel; "
        "GateKeeper fails closed on login/logout happy path, frontend-only clear, framework defaults, short-expiry-only, missing revoked/stolen/expired token negatives, missing refresh reuse proof, missing session invalidation, missing audit/monitoring, missing migration, or skipped local governance."
    )
    payload["readiness_evidence"] = _auth_session_token_lifecycle_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_auth_session_token_lifecycle_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的 auth session 任务")
    payload["assistant_message"] = (
        "请确认这份 auth session/token lifecycle 工作协议；确认后我会生成 Session Token Contract Inspector 先固定 token/session 契约、"
        "Session Token Builder 再实现、Token Misuse Inspector 与 Session Revocation Audit Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条 auth session/token lifecycle 任务编排 contract-first Loop：{task}。"
        "Session Token Contract Inspector 先只读固定 access/refresh expiry、refresh rotation、reuse detection、logout/all-device revocation、password reset/MFA invalidation、cookie flags、CSRF/API token boundaries、audit fields、monitoring、migration 和 governance；"
        "Session Token Builder 只能基于该 handoff 实现；Token Misuse Inspector 与 Session Revocation Audit Inspector 并行检查；"
        "GateKeeper 对 login/logout happy path、frontend-only clear、framework defaults、short-expiry-only、revoked/stolen/expired token negatives 缺失、refresh reuse proof 缺失、session invalidation 缺失、audit/monitoring 缺失、migration 缺失或本地治理跳过 fail closed。"
    )
    payload["readiness_evidence"] = _auth_session_token_lifecycle_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_auth_session_token_lifecycle_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de auth session confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de auth session/token lifecycle; después compilaré un workflow contract-first "
        "con inspecciones paralelas de Token Misuse y Session Revocation Audit antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de auth session/token lifecycle con un Loop contract-first: {task}. "
        "Session Token Contract Inspector fija expiry access/refresh, refresh rotation, reuse detection, revocation, password reset/MFA invalidation, cookie flags, CSRF/API boundaries, audit, monitoring, migration y governance; "
        "Session Token Builder implementa desde ese handoff; Token Misuse Inspector y Session Revocation Audit Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante login/logout happy path, frontend-only clear, framework defaults, short-expiry-only, missing token negatives, refresh reuse proof, session invalidation, audit/monitoring, migration o governance omitida."
    )
    payload["readiness_evidence"] = _auth_session_token_lifecycle_readiness_evidence(task, language="es")
    return payload


def alignment_english_identity_sso_agreement_response(task_text: str) -> dict:
    payload = alignment_english_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "the user-confirmed enterprise SSO task")
    payload["assistant_message"] = (
        "Please confirm this enterprise SSO working agreement; I will compile an identity-contract-first workflow "
        "with parallel SSO Assertion Evidence and Provisioning Mapping inspections before GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Govern this enterprise SAML/OIDC SSO and provisioning task through a contract-first Loop: {task}. "
        "Identity Contract Inspector first freezes IdP metadata, issuer/audience, signed assertion, tenant domain binding, replay/expiry, role/group mapping, SCIM/JIT provisioning, deprovisioning, password-login compatibility, audit, and monitoring proof targets; "
        "SSO Builder implements only from that handoff; SSO Assertion Evidence Inspector and Provisioning Mapping Inspector inspect in parallel; "
        "GateKeeper fails closed on Okta-happy-path-only, SAML-library-only, UI-enabled-only, admin-only mapping, missing forged assertion negatives, missing tenant-binding proof, missing deprovisioning proof, or missing audit/monitoring proof."
    )
    payload["readiness_evidence"] = _identity_sso_readiness_evidence(task, language="en")
    return payload


def alignment_chinese_identity_sso_agreement_response(task_text: str) -> dict:
    payload = alignment_chinese_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "用户确认的企业 SSO 任务")
    payload["assistant_message"] = (
        "请确认这份 enterprise SSO 工作协议；确认后我会生成 Identity Contract Inspector 先固定身份契约、"
        "SSO Builder 再实现、SSO Assertion Evidence Inspector 与 Provisioning Mapping Inspector 并行检查、最后 GateKeeper 裁决的 Loop。"
    )
    payload["agreement_summary"] = (
        f"围绕这条企业 SAML/OIDC SSO 与 provisioning 任务编排 contract-first Loop：{task}。"
        "Identity Contract Inspector 先只读固定 IdP metadata、issuer/audience、signed assertion、tenant domain binding、replay/expiry、role/group mapping、"
        "SCIM/JIT provisioning、deprovisioning、password-login compatibility、audit 和 monitoring proof targets；"
        "SSO Builder 只能基于该 handoff 实现；SSO Assertion Evidence Inspector 与 Provisioning Mapping Inspector 并行检查；"
        "GateKeeper 对 Okta-happy-path-only、SAML-library-only、UI-enabled-only、admin-only mapping、forged assertion 负向缺失、tenant-binding proof 缺失、deprovisioning proof 缺失或 audit/monitoring proof 缺失 fail closed。"
    )
    payload["readiness_evidence"] = _identity_sso_readiness_evidence(task, language="zh")
    return payload


def alignment_spanish_identity_sso_agreement_response(task_text: str) -> dict:
    payload = alignment_spanish_task_anchored_agreement_response(task_text)
    task = _agreement_task_clause(task_text or "la tarea de enterprise SSO confirmada")
    payload["assistant_message"] = (
        "Confirma este acuerdo de enterprise SSO; después compilaré un workflow identity-contract-first con inspecciones paralelas de SSO Assertion Evidence y Provisioning Mapping antes de GateKeeper."
    )
    payload["agreement_summary"] = (
        f"Gobernar esta tarea de SAML/OIDC SSO y provisioning con un Loop contract-first: {task}. "
        "Identity Contract Inspector fija IdP metadata, issuer/audience, signed assertion, tenant domain binding, replay/expiry, role/group mapping, SCIM/JIT provisioning, deprovisioning, password-login compatibility, audit y monitoring targets; "
        "SSO Builder implementa desde ese handoff; SSO Assertion Evidence Inspector y Provisioning Mapping Inspector inspeccionan en paralelo; "
        "GateKeeper falla cerrado ante Okta-happy-path-only, SAML-library-only, UI-enabled-only, admin-only mapping, forged assertion negatives faltantes, tenant-binding proof faltante, deprovisioning proof faltante o audit/monitoring faltante."
    )
    payload["readiness_evidence"] = _identity_sso_readiness_evidence(task, language="es")
    return payload

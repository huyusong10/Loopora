from __future__ import annotations

from agent_bundle_candidates_test_support import (
    CliRunner,
    Path,
    _assert_labeled_loopora_agent_command,
    _assert_web_review_json_payload,
    _assert_web_review_plain_output,
    _error_text,
    _invoke_codex_plan,
    cli,
    cli_agent_runtime_support,
    json,
    yaml,
)
from agent_adapter_test_common import _labeled_value


def _assert_ready_task_anchor(summary: dict, *, task_message: str, confirmation_text: str) -> None:
    assert summary["task_anchor"] == task_message
    assert "first /loopora-plan user message" in summary["task_anchor_status"]
    assert confirmation_text not in summary["task_anchor"]
    assert "ready_review_projection.task_scope" in summary["review_scope"]
    assert summary["ready_next_step"].startswith("compare task_anchor with the candidate task scope")


def test_cli_agent_gen_without_bundle_reports_web_alignment_needed(sample_workdir: Path) -> None:
    runner = CliRunner()
    task_message = "Prepare a governed implementation loop."

    result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=task_message,
        entry_source="codex_project_skill",
    )

    assert result.exit_code == 0, result.stdout
    _assert_web_review_plain_output(result.stdout, task_message=task_message, workdir=sample_workdir)

    json_task_message = "Prepare a second governed implementation loop."
    json_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=json_task_message,
        entry_source="codex_project_skill",
        json_output=True,
    )

    assert json_result.exit_code == 0, json_result.stdout
    _assert_web_review_json_payload(json.loads(json_result.stdout), task_message=json_task_message, workdir=sample_workdir)


def test_cli_agent_gen_without_bundle_keeps_spanish_review_language(sample_workdir: Path) -> None:
    runner = CliRunner()
    task_message = (
        "Necesito implementar una exportación CSV de datos de clientes para auditoría. "
        "Debe probar que solo administradores autorizados pueden exportar, que tokens y teléfonos quedan redactados, "
        "que no hay fuga entre tenants, y que el log de auditoría permite reconciliar cada archivo generado. "
        "Prefiero bloquear el cierre si falta una prueba negativa de permisos o aislamiento."
    )

    result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=task_message,
        entry_source="codex_project_skill",
        json_output=True,
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summary = payload["summary"]
    summary_text = json.dumps(summary, ensure_ascii=False)
    assert summary["review_status"] == "no ejecutable; no se envió ningún archivo de plan candidato"
    assert summary["task_anchor_status"].startswith("ancla de tarea preservada desde /loopora-plan")
    assert summary["review_scope"].startswith("review_focus enumera las superficies de Loop")
    assert summary["review_recommended_action"] == "Continuar revisión con evidencia primero (recomendado)"
    assert summary["review_reply_preview"].startswith("Continuar Web review desde este ancla de tarea")
    assert any("Superficie de éxito: nombra el resultado visible" in item for item in summary["review_focus"])
    assert summary["next_review_step"].startswith("abre la URL de preview")
    assert summary["after_review_ready"].startswith("vuelve a esta sesión de Agent")
    assert "Continue evidence-first review" not in summary_text
    assert "not runnable; no candidate plan file was submitted" not in summary_text


def test_cli_agent_plan_spanish_rounds_preserve_language_and_traceability(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-spanish-csv-contract",
    }
    task_message = (
        "Necesito planear una exportación CSV de clientes para auditoría. Debe probar que solo administradores "
        "autorizados pueden exportar, que teléfonos y tokens quedan redactados, que no hay fuga entre tenants "
        "y que el log de auditoría permite reconciliar cada archivo generado. Una demo happy path o un CSV de muestra no cuenta."
    )

    first_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=task_message,
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    first_summary = json.loads(first_result.stdout)["summary"]

    assert first_result.exit_code == 0, first_result.stdout
    assert first_summary["ready"] is False
    assert first_summary["alignment_stage"] == "clarifying"
    assert first_summary["review_reply_message"].startswith("Continuar Web review desde este ancla de tarea")

    second_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=(
            "Prefiero bloquear el cierre si falta prueba negativa de permisos, aislamiento por tenant, "
            "redacción de PII o reconciliación del log de auditoría; la velocidad pierde frente a evidencia reproducible."
        ),
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    second_summary = json.loads(second_result.stdout)["summary"]

    assert second_result.exit_code == 0, second_result.stdout
    assert second_summary["ready"] is False
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == first_summary["alignment_session_id"]
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert agreement_text.startswith("Confirma primero este acuerdo de trabajo")
    for term in ("CSV", "administradores", "tenant", "auditoría", "PII"):
        assert term in agreement_text
    assert "Please confirm this working agreement" not in agreement_text

    third_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message="Confirmo este acuerdo de trabajo.",
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    third_summary = json.loads(third_result.stdout)["summary"]

    assert third_result.exit_code == 0, third_result.stdout
    assert third_summary["ready"] is True
    assert third_summary["status"] == "ready"
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == first_summary["alignment_session_id"]
    ready_projection = third_summary["ready_review_projection"]
    ready_projection_text = json.dumps(ready_projection, ensure_ascii=False)
    for term in ("CSV", "administradores", "tenant", "auditoría", "PII"):
        assert term in ready_projection_text
    assert "Confirmo este acuerdo de trabajo" not in ready_projection_text
    bundle_text = (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / third_summary["alignment_session_id"]
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")
    assert "Confirmo este acuerdo de trabajo" not in bundle_text
    assert ready_projection["traceability"]["mapped_count"] == ready_projection["traceability"]["required_count"]


def test_cli_agent_plan_message_only_rounds_continue_same_alignment_session(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-interactive-contract",
    }
    task_message = (
        "Prepare a RAG support chatbot Loop. Success must prove grounded source chunks, retrieval ACL, "
        "negative prompt-injection docs, PII redaction, tool allowlist, eval set, and monitoring. "
        "Fake done is one demo answer or UI citations only; evidence beats speed."
    )

    first_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=task_message,
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    first_summary = json.loads(first_result.stdout)["summary"]

    assert first_result.exit_code == 0, first_result.stdout
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"
    assert first_summary["alignment_stage"] == "clarifying"
    assert first_summary["review_reply_message"].startswith("Continue Web review from this /loopora-plan task anchor:")
    assert task_message in first_summary["review_reply_message"]
    _assert_labeled_loopora_agent_command(
        f"next_plan_cli_command: {first_summary['next_plan_cli_command']}",
        "next_plan_cli_command",
        "plan",
    )

    second_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: this needs multiple evidence rounds because retrieval ACL, prompt-injection negatives, "
            "PII redaction, tool allowlist, eval-set quality, and monitoring cannot be proven by one demo answer. "
            "Block UI-only citations, unverifiable source snippets, and happy-path chatbot replies."
        ),
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    second_summary = json.loads(second_result.stdout)["summary"]

    assert second_result.exit_code == 0, second_result.stdout
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == first_summary["alignment_session_id"]
    assert second_summary["alignment_stage"] == "agreement_ready"
    assert second_summary["status"] == "waiting_user"
    assert second_summary["alignment_assistant_message"]
    assert "RAG support chatbot" in second_summary["alignment_assistant_message"]
    assert "retrieval ACL" in second_summary["alignment_assistant_message"]
    assert "starter experience" not in second_summary["alignment_assistant_message"]
    assert len(second_summary["alignment_decision_options"]) == 2
    assert second_summary["ask_user"] == second_summary["alignment_assistant_message"]
    assert second_summary["question_action"]["target"] == "main_agent_session"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert "Do not answer this alignment question from host inference" in second_summary["question_action"]["subagent_policy"]
    assert "do not infer or probe the answer" in second_summary["next_alignment_step"]

    third_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=second_summary["alignment_decision_options"][0]["user_reply"],
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    third_summary = json.loads(third_result.stdout)["summary"]

    assert third_result.exit_code == 0, third_result.stdout
    assert third_summary["ready"] is True
    assert third_summary["status"] == "ready"
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == first_summary["alignment_session_id"]
    assert third_summary["alignment_stage"] == "ready"
    assert third_summary["ready_slash_command"] == "/loopora-run"
    _assert_ready_task_anchor(third_summary, task_message=task_message, confirmation_text="Confirm; use this direction")
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    assert "RAG support chatbot" in ready_projection_text
    assert "retrieval ACL" in ready_projection_text
    assert "starter experience" not in ready_projection_text
    assert "Confirm; use this direction" not in ready_projection_text
    bundle_text = (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / third_summary["alignment_session_id"]
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")
    assert "Confirm; use this direction" not in bundle_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary["ready_review_projection"]["traceability"]["required_count"]


def test_cli_agent_plan_chinese_webhook_rounds_preserve_task_anchor_to_ready_projection(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-chinese-webhook-contract",
    }
    task_message = (
        "我要让 Loopora 规划一个 Stripe webhook 到内部 ledger 的闭环实现：invoice.paid、payment_failed、refund、dispute "
        "事件要幂等写入账本，对重复、乱序、重放、签名失败、跨租户污染都必须有负向证据；成功不是 handler 返回 200，"
        "而是 ledger 对账、审计日志和异常 handoff 都可追踪。"
    )

    first_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=task_message,
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    first_summary = json.loads(first_result.stdout)["summary"]

    assert first_result.exit_code == 0, first_result.stdout
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"
    assert first_summary["alignment_stage"] == "clarifying"

    second_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=(
            "补充判断：宁愿第一版范围小，也不能放过 webhook 签名验证、event id 幂等、乱序事件、租户隔离、"
            "退款/争议反向分录、ledger reconciliation 和 audit log。只有 happy path fixture、mock-only "
            "或单条 invoice.paid 测试都要阻断。"
        ),
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    second_summary = json.loads(second_result.stdout)["summary"]

    assert second_result.exit_code == 0, second_result.stdout
    assert second_summary["ready"] is False
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == first_summary["alignment_session_id"]
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    for term in ("Stripe", "webhook", "ledger", "幂等", "对账"):
        assert term in agreement_text
    assert "starter experience" not in agreement_text

    third_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message="确认，采用这份工作协议。",
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    third_summary = json.loads(third_result.stdout)["summary"]

    assert third_result.exit_code == 0, third_result.stdout
    assert third_summary["ready"] is True
    assert third_summary["status"] == "ready"
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == first_summary["alignment_session_id"]
    assert third_summary["alignment_stage"] == "ready"
    _assert_ready_task_anchor(third_summary, task_message=task_message, confirmation_text="确认，采用这份工作协议")
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("Stripe", "webhook", "ledger", "幂等", "对账"):
        assert term in ready_projection_text
    assert "starter experience" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary["ready_review_projection"]["traceability"]["required_count"]


def test_cli_agent_plan_vague_message_only_round_keeps_asking_specific_question(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-vague-question-contract",
    }

    first_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message="帮我规划一个更好的用户体验，先别太复杂。",
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    first_summary = json.loads(first_result.stdout)["summary"]

    assert first_result.exit_code == 0, first_result.stdout
    assert first_summary["ready"] is False
    assert first_summary["alignment_stage"] == "clarifying"
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message="我还不确定具体范围，主要希望它更稳定、更好用。",
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    second_summary = json.loads(second_result.stdout)["summary"]

    assert second_result.exit_code == 0, second_result.stdout
    assert second_summary["ready"] is False
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == first_summary["alignment_session_id"]
    assert second_summary["alignment_stage"] == "clarifying"
    assert second_summary["alignment_missing_items"] == ["success_surface"]
    assert "必须证明哪个具体的用户可见结果或可审计结果" in second_summary["alignment_assistant_message"]
    assert "补一个会改变 Loop 方案的问题" not in second_summary["alignment_assistant_message"]
    assert "confirm_agreement" not in {option["id"] for option in second_summary["alignment_decision_options"]}

    third_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=(
            "完成时必须证明新用户能从注册进入第一个关键操作，失败时有清晰错误和恢复路径；"
            "只有截图或 happy path demo 不算完成。"
        ),
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    third_summary = json.loads(third_result.stdout)["summary"]

    assert third_result.exit_code == 0, third_result.stdout
    assert third_summary["ready"] is False
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == first_summary["alignment_session_id"]
    assert third_summary["alignment_stage"] == "agreement_ready"
    assert third_summary["status"] == "waiting_user"
    assert third_summary.get("alignment_missing_items", []) == []
    agreement_text = third_summary["alignment_assistant_message"]
    for term in ("新用户", "注册", "第一个关键操作", "恢复路径", "happy path demo"):
        assert term in agreement_text
    assert "必须证明哪个具体的用户可见结果或可审计结果" not in agreement_text
    assert "confirm_agreement" in {option["id"] for option in third_summary["alignment_decision_options"]}

    fourth_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message="确认，采用这份工作协议。",
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    fourth_summary = json.loads(fourth_result.stdout)["summary"]

    assert fourth_result.exit_code == 0, fourth_result.stdout
    assert fourth_summary["ready"] is True
    assert fourth_summary["continued_alignment_session"] is True
    assert fourth_summary["alignment_session_id"] == first_summary["alignment_session_id"]
    assert fourth_summary["alignment_stage"] == "ready"
    ready_projection_text = json.dumps(fourth_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("新用户", "注册", "第一个关键操作", "恢复路径", "happy path demo"):
        assert term in ready_projection_text
    assert fourth_summary["ready_review_projection"]["traceability"]["mapped_count"] == fourth_summary["ready_review_projection"]["traceability"]["required_count"]


def test_cli_agent_plan_data_deletion_rounds_do_not_import_unrelated_domain_templates(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-data-deletion-contract",
    }

    first_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=(
            "Plan a governed data deletion and retention workflow for GDPR erase requests. Success must prove "
            "account deletion, billing-record retention exceptions, anonymized analytics, search-index purge, "
            "backup expiry handling, audit-log retention, and tenant isolation. Fake done is a UI delete button "
            "or one happy-path API response; evidence beats speed."
        ),
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    first_summary = json.loads(first_result.stdout)["summary"]

    assert first_result.exit_code == 0, first_result.stdout
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: fail closed if deletion skips design/README, tests, local retention policy, tenant "
            "isolation checks, or audit-log retention proof. Builder must read project design/tests before changing "
            "deletion behavior; Inspector must verify negative cases for billing retention exceptions, search purge, "
            "analytics anonymization, backup expiry, and cross-tenant access; GateKeeper should block Weak or Unproven "
            "evidence even if the UI delete flow works."
        ),
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    second_summary = json.loads(second_result.stdout)["summary"]

    assert second_result.exit_code == 0, second_result.stdout
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == first_summary["alignment_session_id"]
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True

    third_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message="Confirm; use this direction.",
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    third_summary = json.loads(third_result.stdout)["summary"]

    assert third_result.exit_code == 0, third_result.stdout
    assert third_summary["ready"] is True
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    assert "deletion, retention, legal hold, restore, tombstone, search/cache purge, and audit evidence" in ready_projection_text
    assert "tenant isolation and cross-tenant negative cases" in ready_projection_text
    assert "tamper-evident audit integrity and retention" not in ready_projection_text
    assert "payment, refund, proration, invoice, entitlement" not in ready_projection_text
    assert "golden eval set, negative examples" not in ready_projection_text
    assert "export/download attempts and report evidence" not in ready_projection_text

    bundle_text = (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / third_summary["alignment_session_id"]
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")
    assert "audit-integrity" not in bundle_text
    assert "payment-refund-billing" not in bundle_text
    assert "eval-set" not in bundle_text
    assert "data-export" not in bundle_text
    assert "deletion-retention" in bundle_text
    assert "audit-log" in bundle_text


def test_cli_agent_plan_incident_rounds_use_repro_first_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-incident-repro-contract",
    }
    task_message = (
        "Plan an incident repair Loop for intermittent checkout duplicate charges. Success must first reproduce or explain "
        "trigger conditions, prove the root cause with evidence, add regression coverage, show monitoring or alerts would catch "
        "recurrence, and leave a release/rollback path. Fake done is patching one branch, existing tests passing, or a happy-path "
        "checkout with no repro, root-cause proof, or monitoring evidence; evidence beats speed."
    )

    first_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=task_message,
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    first_summary = json.loads(first_result.stdout)["summary"]

    assert first_result.exit_code == 0, first_result.stdout
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: start read-only. Repro Inspector must first pin reproduction evidence or trigger conditions "
            "before any patch. Builder may only change code after reading that repro handoff. Monitoring Inspector must verify "
            "regression coverage plus recurrence detection, alerts, and rollback/release handoff. GateKeeper should block if "
            "root cause is narrative-only, if patch evidence is not tied to the repro, or if monitoring/rollback proof is missing."
        ),
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    second_summary = json.loads(second_result.stdout)["summary"]

    assert second_result.exit_code == 0, second_result.stdout
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == first_summary["alignment_session_id"]
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Repro Inspector" in agreement_text
    assert "Monitoring Inspector" in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text

    third_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message="Confirm; use this direction.",
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    third_summary = json.loads(third_result.stdout)["summary"]

    assert third_result.exit_code == 0, third_result.stdout
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == first_summary["alignment_session_id"]
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    assert "root-cause reproduction, trigger conditions" in ready_projection_text
    assert "monitoring, alerting, and regression guard evidence" in ready_projection_text
    assert "Confirm; use this direction" not in ready_projection_text

    bundle_text = (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / third_summary["alignment_session_id"]
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert workflow["preset"] == "incident-root-cause-repro"
    assert [step["id"] for step in workflow["steps"]] == [
        "repro_inspection_step",
        "incident_builder_step",
        "monitoring_inspection_step",
        "incident_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["repro_inspection_step"]
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == ["repro_inspection_step", "incident_builder_step"]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in ("root-cause-repro", "monitoring", "negative_evidence", "local-governance"):
        assert verify_ref in gatekeeper_verifies
    assert "Incident Root-Cause Workflow Notes" in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Confirm; use this direction" not in bundle_text

def test_cli_agent_gen_reports_reused_web_review_url(sample_workdir: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr(
        cli_agent_runtime_support,
        "discover_local_web_service",
        lambda: {"base_url": "http://127.0.0.1:9876", "reused": True, "port": 9876},
    )

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "Prepare a governed implementation loop.",
            "--entry-source",
            "codex_project_skill",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "Loopora Loop preview needs Web review" in result.stdout
    assert "review_status: not runnable; no candidate plan file was submitted" in result.stdout
    assert "task_anchor_status: task anchor preserved from /loopora-plan" in result.stdout
    assert "review_scope: review_focus lists Loop surfaces to compile" in result.stdout
    assert "not missing chat input" in result.stdout
    assert "review_recommended_action: Continue evidence-first review (Recommended)" in result.stdout
    assert "review_focus:" in result.stdout
    assert "preview_url: http://127.0.0.1:9876/loops/new/bundle?alignment_session_id=" in result.stdout
    assert "run_blocked_until_web_review: yes" in result.stdout
    assert "after_review_cli_command_status: blocked_until_web_review_complete" in result.stdout
    assert "after_review_slash_command: /loopora-run" in result.stdout
    _assert_labeled_loopora_agent_command(result.stdout, "after_review_cli_command", "run")
    assert "after_web_review_cli_command:" not in result.stdout
    assert "after_review_command:" not in result.stdout
    assert "agent_surface: current host Agent remains the executor" in result.stdout
    assert "agent surface:" not in result.stdout
    assert "- host dispatch:" not in result.stdout
    assert "web: reused http://127.0.0.1:9876" in result.stdout


def test_cli_agent_gen_reports_relative_preview_when_web_unavailable(sample_workdir: Path, monkeypatch) -> None:
    runner = CliRunner()
    web_cases = (
        {
            "base_url": "http://127.0.0.1:8742",
            "reused": False,
            "start_available": False,
            "port": 8742,
            "warning": "no available Loopora Web port was found",
        },
        {
            "base_url": "http://127.0.0.1:8747",
            "reused": False,
            "start_available": True,
            "port": 8747,
            "warning": "Loopora Web is not running; start it explicitly with the provided foreground command",
        },
    )

    for web in web_cases:
        port = int(web["port"])
        workdir = sample_workdir / f"web-unavailable-{port}"
        workdir.mkdir()
        monkeypatch.setattr(cli_agent_runtime_support, "discover_local_web_service", lambda web=web: dict(web))

        result = runner.invoke(
            cli.app,
            [
                "agent",
                "codex",
                "plan",
                "--workdir",
                str(workdir),
                "--message",
                "Prepare a governed implementation loop.",
                "--entry-source",
                "codex_project_skill",
            ],
        )

        assert result.exit_code == 0, result.stdout
        assert "preview_url: /loops/new/bundle?alignment_session_id=" in result.stdout
        assert f"preview_url: http://127.0.0.1:{port}/loops/new/bundle" not in result.stdout
        expected_status = "relative_path_web_not_running" if web["start_available"] else "relative_path_web_unavailable"
        assert f"preview_url_status: {expected_status}" in result.stdout
        assert _labeled_value(result.stdout, "preview_url_web_start_command").endswith(
            f"loopora serve --open --workdir {workdir.resolve()} --host 127.0.0.1 --port {port}"
        )
        assert f"web_warning: {web['warning']}" in result.stdout
        expected_web_state = "not running" if web["start_available"] else "unavailable"
        assert f"web: {expected_web_state} http://127.0.0.1:{port}" in result.stdout
        assert result.stdout.index("preview_url:") < result.stdout.index("preview_url_status:")
        assert result.stdout.index("preview_url_web_start_command:") < result.stdout.index(
            "next_plan_cli_command_policy:"
        )


def test_cli_agent_loop_after_web_review_fallback_reprints_review_url_and_focus(sample_workdir: Path, monkeypatch) -> None:
    runner = CliRunner()
    gen_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "Prepare a governed implementation loop with later evidence and GateKeeper review.",
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )
    monkeypatch.setattr(
        cli_agent_runtime_support,
        "discover_local_web_service",
        lambda: {"base_url": "http://127.0.0.1:9988", "reused": True, "port": 9988},
    )

    loop_result = runner.invoke(cli.app, ["agent", "codex", "run", "--workdir", str(sample_workdir)])

    assert gen_result.exit_code == 0, gen_result.stdout
    assert loop_result.exit_code == 1
    output_text = loop_result.output
    assert "loop_recovery: finish the current Web review before /loopora-run can start" in output_text
    assert "review_status: not runnable; no candidate plan file was submitted" in output_text
    assert "task_anchor_status: task anchor preserved from /loopora-plan" in output_text
    assert "review_scope: review_focus lists Loop surfaces to compile" in output_text
    assert "not missing chat input" in output_text
    assert "review_focus:" in output_text
    assert "Success surface:" in output_text
    assert "Fake-done risks:" in output_text
    assert "Evidence expectations:" in output_text
    assert "review_recommended_action: Continue evidence-first review (Recommended)" in output_text
    assert "next_review_step: open the preview URL" in output_text
    assert "after_review_ready: return to this Agent session and run /loopora-run" in output_text
    assert "run_blocked_until_web_review: yes" in output_text
    assert "after_review_cli_command_status: blocked_until_web_review_complete" in output_text
    assert "after_review_slash_command: /loopora-run" in output_text
    _assert_labeled_loopora_agent_command(output_text, "after_review_cli_command", "run")
    assert "after_web_review_cli_command:" not in output_text
    assert "after_review_command:" not in output_text
    assert "preview_url: http://127.0.0.1:9988/loops/new/bundle?alignment_session_id=" in output_text
    assert output_text.count("preview_url:") == 1
    assert "web: reused http://127.0.0.1:9988" in output_text
    assert "Traceback" not in output_text
    assert _error_text(loop_result) == ""
    assert "cli.command.failed" not in output_text
    assert "current status: idle" not in output_text

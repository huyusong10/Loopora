from __future__ import annotations

# Merged from test_alignment_prompt_build_context.py
from pathlib import Path

from loopora.alignment_guidance import load_alignment_guidance_assets
from loopora.service_alignment_prompting import (
    AlignmentPromptBuildContext,
    alignment_prompt_guidance_profile,
    alignment_prompt_transcript_projection,
    build_alignment_prompt,
    build_alignment_prompt_text,
)


def test_build_alignment_prompt_collects_context_inputs_before_rendering(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.yml"
    workdir = tmp_path / "project"
    calls: list[tuple[str, str]] = []

    context = AlignmentPromptBuildContext(
        current_bundle_text=lambda path: calls.append(("bundle", str(path))) or "version: 1\nmetadata:\n  name: Context Bundle\n",
        workdir_snapshot=lambda path: calls.append(("workdir", str(path))) or "Top-level entries (1 shown):\n- src/",
        user_language_hint=lambda session: calls.append(("language", str(session["id"]))) or "Use Chinese.",
    )

    prompt = build_alignment_prompt(
        context,
        {
            "id": "align_prompt",
            "bundle_path": str(bundle_path),
            "workdir": str(workdir),
            "alignment_stage": "clarifying",
            "transcript": [],
            "working_agreement": {},
        },
        mode="normal",
    )

    assert calls == [
        ("bundle", str(bundle_path)),
        ("workdir", str(workdir)),
        ("language", "align_prompt"),
    ]
    assert "Context Bundle" in prompt
    assert "Top-level entries (1 shown):" in prompt
    assert "Use Chinese." in prompt


def test_alignment_prompt_transcript_projection_preserves_task_anchor_and_recent_branch() -> None:
    transcript = [{"role": "user", "content": "Original task anchor", "created_at": "0"}]
    transcript.extend(
        {
            "role": "assistant" if index % 2 == 0 else "user",
            "content": f"decision-branch-{index}",
            "created_at": str(index + 1),
        }
        for index in range(20)
    )

    projection = alignment_prompt_transcript_projection(transcript)

    metadata = projection[0]
    assert metadata["kind"] == "transcript_projection"
    assert metadata["total_entries"] == len(transcript)
    assert metadata["omitted_entries"] > 0
    assert metadata["task_anchor_retained"] is True
    projected_content = [entry.get("content") for entry in projection[1:]]
    assert projected_content[0] == "Original task anchor"
    assert "decision-branch-0" not in projected_content
    assert "decision-branch-19" in projected_content

    prompt = build_alignment_prompt_text(
        {
            "bundle_path": "/tmp/bundle.yml",
            "workdir": "/tmp/project",
            "alignment_stage": "clarifying",
            "transcript": transcript,
            "working_agreement": {},
        },
        mode="normal",
    )
    assert '"kind": "transcript_projection"' in prompt
    assert "Original task anchor" in prompt
    assert "decision-branch-0" not in prompt
    assert "decision-branch-19" in prompt


def test_alignment_prompt_transcript_projection_bounds_long_content_without_hiding_truncation() -> None:
    task_anchor = "ANCHOR-BEGIN\n" + ("x" * 30_000) + "\nANCHOR-END"
    transcript = [{"role": "user", "content": task_anchor}]
    transcript.extend({"role": "assistant", "content": "y" * 10_000} for _ in range(20))

    projection = alignment_prompt_transcript_projection(transcript)

    metadata = projection[0]
    projected_anchor = projection[1]
    assert metadata["content_truncated"] is True
    assert metadata["omitted_entries"] > 0
    assert projected_anchor["content_truncated"] is True
    assert projected_anchor["original_content_chars"] == len(task_anchor)
    assert projected_anchor["content"].startswith("ANCHOR-BEGIN")
    assert projected_anchor["content"].endswith("ANCHOR-END")
    assert len(projected_anchor["content"]) < len(task_anchor)


def test_alignment_prompt_guidance_profiles_keep_full_bundle_material_for_compile_stages() -> None:
    assets = load_alignment_guidance_assets()
    base_session = {
        "bundle_path": "/tmp/bundle.yml",
        "workdir": "/tmp/project",
        "transcript": [],
        "working_agreement": {},
    }

    clarifying = build_alignment_prompt_text(
        {**base_session, "alignment_stage": "clarifying"},
        mode="normal",
    )
    agreement = build_alignment_prompt_text(
        {**base_session, "alignment_stage": "agreement_ready"},
        mode="normal",
    )
    confirmed = build_alignment_prompt_text(
        {**base_session, "alignment_stage": "confirmed"},
        mode="normal",
    )
    repair = build_alignment_prompt_text(
        {**base_session, "alignment_stage": "clarifying"},
        mode="repair",
    )

    assert assets.bundle_contract.strip() not in clarifying
    assert assets.bundle_contract.strip() not in agreement
    assert assets.bundle_contract.strip() in confirmed
    assert assets.bundle_contract.strip() in repair
    assert "Private complete-run rehearsal example" not in clarifying
    assert "Private complete-run rehearsal example" in confirmed
    assert len(agreement) < len(clarifying) < len(confirmed)
    assert alignment_prompt_guidance_profile({"alignment_stage": "agreement_ready"}, mode="normal") == "agreement"
    assert alignment_prompt_guidance_profile({"alignment_stage": "clarifying"}, mode="repair") == "bundle"


def test_alignment_prompt_guidance_loads_improvement_policy_only_for_improvement_sessions() -> None:
    assets = load_alignment_guidance_assets()
    base_session = {
        "bundle_path": "/tmp/bundle.yml",
        "workdir": "/tmp/project",
        "alignment_stage": "clarifying",
        "transcript": [],
        "working_agreement": {},
    }

    normal_prompt = build_alignment_prompt_text(base_session, mode="normal")
    improvement_prompt = build_alignment_prompt_text(
        {
            **base_session,
            "working_agreement": {"mode": "improvement", "source": {}},
        },
        mode="normal",
    )

    assert assets.feedback_improvement.strip() not in normal_prompt
    assert assets.feedback_improvement.strip() in improvement_prompt


# Merged from test_alignment_prompt_source_context.py

from loopora.service_alignment_prompting import (
    alignment_current_bundle_prompt_text,
    alignment_improvement_context_text,
)


def test_alignment_improvement_context_text_renders_selected_spec_and_redacts_sources() -> None:
    context = alignment_improvement_context_text(
        {
            "working_agreement": {
                "mode": "selected_source",
                "source": {
                    "source_type": "spec_file",
                    "spec_path": "/tmp/spec.md",
                    "reason": "start_from_workdir_spec",
                    "artifact_paths": {"spec": "/tmp/spec.md"},
                    "spec_markdown": "Use Authorization: Bearer PROMPT_SPEC_TOKEN_SECRET",
                },
            }
        }
    )

    assert "Selected Loopora Source Context" in context
    assert "PROMPT_SPEC_TOKEN_SECRET" not in context
    assert "<secret omitted>" in context
    assert "Bundle Improvement Context" not in context


def test_alignment_prompt_omits_model_visible_local_source_paths() -> None:
    source_spec_path = "/private/source-context/spec.md"
    prompt = build_alignment_prompt_text(
        {
            "id": "align_prompt_paths",
            "bundle_path": "/tmp/current-session/bundle.yml",
            "workdir": "/tmp/current-session/project",
            "alignment_stage": "clarifying",
            "transcript": [],
            "working_agreement": {
                "mode": "selected_source",
                "source": {
                    "source_type": "spec_file",
                    "spec_path": source_spec_path,
                    "source_bundle_path": "/private/source-context/artifacts/bundle.yml",
                    "artifact_paths": {
                        "spec": source_spec_path,
                        "run_contract": "contract/run_contract.json",
                    },
                    "spec_markdown": "Preserve the selected source content.",
                },
            },
        },
        mode="normal",
        workdir_snapshot="Workdir could not be inspected.",
    )

    assert source_spec_path not in prompt
    assert "/private/source-context/artifacts/bundle.yml" not in prompt
    assert "<local path omitted>" in prompt
    assert "contract/run_contract.json" in prompt
    assert "Preserve the selected source content." in prompt


def test_alignment_improvement_context_text_renders_run_evidence_context_with_redaction() -> None:
    context = alignment_improvement_context_text(
        {
            "working_agreement": {
                "mode": "improvement",
                "source": {
                    "source_type": "run",
                    "source_run_id": "run_1",
                    "run_status": "succeeded",
                    "source_completion_mode": "all_checks_pass",
                    "evidence_summary": [{"claim": "Cookie: sid=PROMPT_COOKIE_SECRET"}],
                    "coverage_summary": {"summary": "Authorization: Bearer PROMPT_COVERAGE_SECRET"},
                    "judgment_contract": {"done_when": ["proof"]},
                    "task_verdict": {"summary": "insufficient"},
                    "gatekeeper_verdict": {"summary": "needs evidence"},
                },
            }
        }
    )

    assert "Selected Loopora Source Context" in context
    assert "Bundle Improvement Context" in context
    assert "PROMPT_COOKIE_SECRET" not in context
    assert "PROMPT_COVERAGE_SECRET" not in context
    assert "<secret omitted>" in context


def test_alignment_current_bundle_prompt_text_reads_and_redacts_bundle(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.yml"
    bundle_path.write_text(
        "version: 1\nmetadata:\n  name: Authorization: Bearer CURRENT_BUNDLE_TOKEN_SECRET\n",
        encoding="utf-8",
    )

    text = alignment_current_bundle_prompt_text(bundle_path)

    assert "CURRENT_BUNDLE_TOKEN_SECRET" not in text
    assert "<secret omitted>" in text
    assert alignment_current_bundle_prompt_text(tmp_path / "missing.yml") == ""


def test_alignment_current_bundle_prompt_text_redacts_low_level_read_errors(tmp_path: Path, monkeypatch) -> None:
    bundle_path = tmp_path / "bundle.yml"
    local_path = tmp_path / "private" / "bundle.yml"
    bundle_path.write_text("version: 1\nmetadata:\n  name: Existing Bundle\n", encoding="utf-8")

    def fail_read_bundle_file_text(*_args, **_kwargs):
        raise OSError(f"permission denied: {local_path}")

    monkeypatch.setattr(
        "loopora.service_alignment_prompt_source_projection.read_bundle_file_text",
        fail_read_bundle_file_text,
    )

    text = alignment_current_bundle_prompt_text(bundle_path)

    assert text == "Current bundle file could not be read."
    assert str(local_path) not in text
    assert "permission denied" not in text


def test_alignment_current_bundle_prompt_text_redacts_low_level_probe_errors(tmp_path: Path, monkeypatch) -> None:
    bundle_path = tmp_path / "bundle.yml"
    local_path = tmp_path / "private" / "bundle.yml"
    original_exists = Path.exists

    def fail_exists(path: Path) -> bool:
        if path == bundle_path:
            raise OSError(f"permission denied: {local_path}")
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", fail_exists)

    text = alignment_current_bundle_prompt_text(bundle_path)

    assert text == "Current bundle file could not be read."
    assert str(local_path) not in text
    assert "permission denied" not in text


# Merged from test_alignment_prompt_stage_policy.py
import pytest

from loopora.service_alignment_prompting import alignment_stage_policy_text
from loopora.service_types import LooporaError


def test_alignment_stage_policy_text_selects_repair_and_ready_sections() -> None:
    compiler_gates = "\n".join(
        [
            "## Common",
            "Common policy.",
            "## Repair",
            "Repair policy.",
            "## Ready Review",
            "Ready policy.",
            "## Clarifying",
            "Clarifying policy.",
            "## Confirmed Agreement",
            "Confirmed policy.",
        ]
    )

    repair_policy = alignment_stage_policy_text({"alignment_stage": "ready_review"}, mode="repair", compiler_gates=compiler_gates)
    ready_policy = alignment_stage_policy_text({"alignment_stage": "ready_review"}, mode="generate", compiler_gates=compiler_gates)
    confirmed_policy = alignment_stage_policy_text({"alignment_stage": "confirmed"}, mode="generate", compiler_gates=compiler_gates)

    assert repair_policy == "Common policy.\n\nRepair policy."
    assert ready_policy == "Common policy.\n\nReady policy."
    assert confirmed_policy == "Common policy.\n\nConfirmed policy."


def test_alignment_stage_policy_text_fails_closed_when_policy_section_is_missing() -> None:
    with pytest.raises(LooporaError, match="Common"):
        alignment_stage_policy_text({"alignment_stage": "clarifying"}, mode="generate", compiler_gates="## Clarifying\nPolicy")


# Merged from test_alignment_prompt_template_helpers.py

from loopora.service_alignment_prompting import alignment_markdown_h2_sections, render_alignment_template


def test_render_alignment_template_replaces_known_values_and_rejects_unknowns() -> None:
    assert render_alignment_template("Hello {{ name }}", {"name": "Loopora"}) == "Hello Loopora"

    with pytest.raises(LooporaError, match="unknown value"):
        render_alignment_template("Hello {{ missing }}", {})


def test_alignment_markdown_h2_sections_collects_section_bodies() -> None:
    assert alignment_markdown_h2_sections("# Title\n\n## Common\nA\n## Repair\nB\n") == {
        "Common": "A",
        "Repair": "B",
    }


def test_alignment_relevant_examples_prompt_text_selects_core_and_task_examples() -> None:
    assets = load_alignment_guidance_assets()

    selected = alignment_relevant_examples_prompt_text(
        assets.examples,
        context_text=(
            "Migrate SaaS subscription billing from legacy invoices to an event-sourced ledger. "
            "Preserve Stripe webhook idempotency, refunds, chargebacks, tax adjustments, payout "
            "reconciliation, MRR reporting, audit export, backward compatibility, and rollback proof."
        ),
    )

    assert len(selected) < len(assets.examples)
    assert "Good creation example: English learning website" in selected
    assert "Private traceability checklist example" in selected
    assert "Long-chain multi-Builder example" in selected
    assert "Payment webhook reconciliation example" in selected
    assert "Dispute chargeback lifecycle example" in selected
    assert "Tax calculation compliance example" in selected
    assert "Marketplace payout settlement example" in selected
    assert "Migration rollback example" in selected
    assert "MRR metric reconciliation example" in selected
    assert "Compliance audit trail example" in selected
    assert "Price cache invalidation example" not in selected
    assert "RAG grounding and tool safety example" not in selected
    assert "AI quality evaluation example" not in selected
    assert "Consent preference governance example" not in selected
    assert "Async job queue example" not in selected


def test_alignment_relevant_examples_prompt_text_selects_rag_long_chain_example() -> None:
    assets = load_alignment_guidance_assets()

    selected = alignment_relevant_examples_prompt_text(
        assets.examples,
        context_text=(
            "Enterprise RAG support chatbot with citation span verification, retrieval ACL, tenant filtering, "
            "prompt injection documents, tool gating, PII redaction, eval set, human review, and monitoring."
        ),
    )

    assert "RAG grounding and tool safety example" in selected
    assert "Long-chain RAG grounding workflow example" in selected
    assert "Long-chain multi-Builder example" in selected
    assert "Support impersonation break-glass example" not in selected
    assert "Sensitive export example" not in selected


def test_alignment_relevant_examples_prompt_text_selects_breakglass_without_generic_support_false_positive() -> None:
    assets = load_alignment_guidance_assets()

    generic_support_selected = alignment_relevant_examples_prompt_text(
        assets.examples,
        context_text=(
            "Build a customer support ticket dashboard with assignment, notes, SLA filters, and response templates. "
            "Success means agents can triage tickets and managers can review queue health."
        ),
    )
    breakglass_selected = alignment_relevant_examples_prompt_text(
        assets.examples,
        context_text=(
            "Add support impersonation / break-glass admin access with approved ticket, customer consent, "
            "supervisor approval, acting_as attribution, PII masking, revoke, expiry, tenant isolation, and audit proof."
        ),
    )

    assert "Support impersonation break-glass example" not in generic_support_selected
    assert "Support impersonation break-glass example" in breakglass_selected


def test_alignment_relevant_examples_prompt_text_avoids_generic_audit_compliance_token_false_positives() -> None:
    assets = load_alignment_guidance_assets()

    support_dashboard_selected = alignment_relevant_examples_prompt_text(
        assets.examples,
        context_text=(
            "Build a customer support ticket dashboard with assignment, notes, SLA filters, response templates, "
            "queue health, and audit notes for manager review."
        ),
    )
    token_analytics_selected = alignment_relevant_examples_prompt_text(
        assets.examples,
        context_text=(
            "Build API token usage analytics showing token volume by customer, rate limits, anomaly monitoring, "
            "audit export, and usage trends. This is not password reset or secret rotation."
        ),
    )
    consent_selected = alignment_relevant_examples_prompt_text(
        assets.examples,
        context_text=(
            "Build consent preference governance for marketing email, privacy consent, unsubscribe, audit trail, "
            "data deletion request, and regional compliance."
        ),
    )
    consent_merge_selected = alignment_relevant_examples_prompt_text(
        assets.examples,
        context_text=("Build consent preference governance where anonymous cookie consent can merge into the user's account preference ledger after login."),
    )

    assert "Compliance audit trail example" not in support_dashboard_selected
    assert "Async job queue example" not in support_dashboard_selected
    assert "Incident remediation example" not in token_analytics_selected
    assert "Password reset token lifecycle example" not in token_analytics_selected
    assert "API key rotation lifecycle example" not in token_analytics_selected
    assert "Tax calculation compliance example" not in consent_selected
    assert "KYC AML sanctions screening example" not in consent_selected
    assert "Consent preference governance example" in consent_selected
    assert "Collaborative edit conflict example" not in consent_merge_selected
    assert "Consent preference governance example" in consent_merge_selected


def test_alignment_relevant_examples_prompt_text_still_selects_specific_audit_tax_password_incident_examples() -> None:
    assets = load_alignment_guidance_assets()

    password_reset_selected = alignment_relevant_examples_prompt_text(
        assets.examples,
        context_text="Implement password reset token lifecycle with expiry, single-use token, audit log, and account recovery.",
    )
    incident_selected = alignment_relevant_examples_prompt_text(
        assets.examples,
        context_text="Create incident remediation workflow with root cause analysis, postmortem, owner handoff, and regression guard evidence.",
    )
    tax_selected = alignment_relevant_examples_prompt_text(
        assets.examples,
        context_text="Implement tax calculation for VAT and sales tax jurisdiction rules with invoice reconciliation proof.",
    )
    audit_selected = alignment_relevant_examples_prompt_text(
        assets.examples,
        context_text="Build immutable audit log and audit trail retention for compliance audit review.",
    )
    async_job_selected = alignment_relevant_examples_prompt_text(
        assets.examples,
        context_text="Build an async job queue with background job retry, queue worker visibility, and dead-letter handling.",
    )
    collaborative_edit_selected = alignment_relevant_examples_prompt_text(
        assets.examples,
        context_text="Build collaborative editing with same-paragraph merge conflict handling and offline replay.",
    )

    assert "Password reset token lifecycle example" in password_reset_selected
    assert "Incident remediation example" in incident_selected
    assert "Tax calculation compliance example" in tax_selected
    assert "Compliance audit trail example" in audit_selected
    assert "Async job queue example" in async_job_selected
    assert "Collaborative edit conflict example" in collaborative_edit_selected


def test_alignment_relevant_examples_prompt_text_selects_run_evidence_improvement_example() -> None:
    assets = load_alignment_guidance_assets()

    selected = alignment_relevant_examples_prompt_text(
        assets.examples,
        context_text=(
            "Improve this Loop from run evidence: GateKeeper found weak browser journey proof, "
            "missing refund audit reconciliation, and residual risk without owner."
        ),
    )

    assert "Improvement from run evidence example" in selected
    assert "Payment webhook reconciliation example" in selected
    assert "Compliance audit trail example" in selected
    assert "Improvement from vague refactor critique example" not in selected


def test_alignment_relevant_examples_prompt_text_selects_vague_refactor_only_for_refactor_feedback() -> None:
    assets = load_alignment_guidance_assets()

    selected = alignment_relevant_examples_prompt_text(
        assets.examples,
        context_text="这份 Loop 太保守，不够重构，帮我改激进一点。",
    )

    assert "Improvement from vague refactor critique example" in selected
    assert "Improvement from run evidence example" not in selected


# Merged from test_alignment_prompt_text_rendering.py
from loopora.service_alignment_prompting import alignment_relevant_examples_prompt_text


def test_build_alignment_prompt_text_renders_repair_context_and_redacts_session_values() -> None:
    prompt = build_alignment_prompt_text(
        {
            "bundle_path": "/tmp/bundle.yml",
            "workdir": "/tmp/project",
            "executor_kind": "codex",
            "executor_mode": "preset",
            "command_args_text": "--token PROMPT_COMMAND_TOKEN_SECRET",
            "alignment_stage": "ready_review",
            "transcript": [{"role": "user", "content": "Cookie: sid=PROMPT_TRANSCRIPT_COOKIE_SECRET"}],
            "working_agreement": {"summary": "Authorization: Bearer PROMPT_AGREEMENT_TOKEN_SECRET"},
        },
        mode="repair",
        workdir_snapshot="Top-level entries (0 shown):",
        user_language_hint="Use Chinese.",
        validation_error="bundle field missing",
        invalid_yaml="version: 1",
    )

    assert "bundle field missing" in prompt
    assert "Use Chinese." in prompt
    assert "PROMPT_COMMAND_TOKEN_SECRET" not in prompt
    assert "PROMPT_TRANSCRIPT_COOKIE_SECRET" not in prompt
    assert "PROMPT_AGREEMENT_TOKEN_SECRET" not in prompt
    assert "<secret omitted>" in prompt


def test_build_alignment_prompt_text_renders_current_bundle_context() -> None:
    prompt = build_alignment_prompt_text(
        {
            "bundle_path": "/tmp/bundle.yml",
            "workdir": "/tmp/project",
            "alignment_stage": "clarifying",
            "transcript": [],
            "working_agreement": {},
        },
        mode="normal",
        current_bundle="version: 1\nmetadata:\n  name: Current\n",
    )

    assert "Current Bundle" in prompt
    assert "metadata:" in prompt

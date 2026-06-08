from __future__ import annotations

from pathlib import Path

from alignment_test_support import _wait_for_status
from bundle_semantic_lint_long_chain_support import long_chain_multi_builder_bundle
from loopora.bundles import bundle_to_yaml, lint_alignment_bundle_semantics, load_bundle_text
from loopora.executor import FakeCodexExecutor
from loopora.executor_alignment_responses import alignment_response


LONG_CHAIN_ALIGNMENT_READINESS_EVIDENCE = {
    "loop_fit": (
        "This search rollout needs Loopora because each later phase creates new query, retrieval, ranking, "
        "regression, and evidence-hardening proof that should survive one chat and govern future iterations."
    ),
    "task_scope": (
        "Scope is a staged search relevance rollout: baseline inspection, query rewrite, retrieval, ranking, "
        "regression review, evidence hardening, then closure; broad personalization and full search UI redesign are non-goals."
    ),
    "success_surface": (
        "Success means each phase leaves durable artifacts or command output, final search behavior is judged from "
        "baseline, phase, regression, and hardening handoffs, and GateKeeper can audit the evidence IDs."
    ),
    "fake_done_risks": (
        "Reject metric theater, final-story-only summaries, ranking changes that mask recall regressions, "
        "unsupported phase claims, and happy-path demos without baseline evidence."
    ),
    "evidence_preferences": (
        "Trusted proof is baseline artifacts, phase handoffs, regression checks, exact evidence IDs, and final "
        "Proven / Weak / Unproven / Blocking / Residual risk buckets."
    ),
    "execution_strategy": (
        "Move one phase at a time; first pin the baseline, then build query, retrieval, and ranking separately, "
        "let regression review expose proof gaps, and let evidence hardening repair only missing proof."
    ),
    "residual_risk_policy": (
        "Minor tuning risk may remain only when it is labeled as Residual risk, assigned to a follow-up owner or "
        "acceptance path, and separated from Blocking risks; unproven recall regressions, missing baseline, or "
        "missing phase evidence must fail closed."
    ),
    "judgment_tradeoffs": (
        "Prefer slower phase proof over a broad final implementation story; speed loses when proof is Weak or "
        "Unproven, and GateKeeper should treat Blocking evidence gaps as stronger than polish progress."
    ),
    "local_governance": (
        "Project-local governance markers are present: AGENTS.md, design/README.md, design/, and tests/. Builder "
        "must read applicable local rules, Inspector must verify design/test obligations, and GateKeeper must treat "
        "skipped governance as Weak, Unproven, or Blocking without inventing contents."
    ),
    "role_posture": (
        "Baseline Inspector pins facts; phase Builders own narrow handoffs; Regression Inspector tries to disprove "
        "claims; Evidence Builder repairs proof; GateKeeper fails closed from Proven / Weak / Unproven / Blocking / "
        "Residual risk buckets."
    ),
    "workflow_shape": (
        "A long-chain workflow is required because each phase creates a distinct artifact; GateKeeper must read "
        "earlier baseline, phase, review, and final hardening handoffs so weak evidence, drift, fake done, and "
        "Blocking gaps surface before closure."
    ),
    "workdir_facts": (
        "Observed workdir facts are limited to AGENTS.md, design/README.md, design/, tests/, and the target path; "
        "search implementation files and proof commands remain unknown until run roles inspect them."
    ),
    "open_questions": "",
}


LONG_CHAIN_ALIGNMENT_CHECKLIST = {
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


class LongChainAlignmentExecutor(FakeCodexExecutor):
    def _build_payload(self, request) -> dict:
        if request.role != "alignment":
            return super()._build_payload(request)
        stage = str(request.extra_context.get("alignment_stage") or "clarifying")
        workdir = Path(str(request.extra_context.get("target_workdir") or request.workdir))
        if stage not in {"confirmed", "compiling", "ready_review"}:
            payload = alignment_response(
                status="question",
                assistant_message=(
                    "Please confirm this working agreement before I compile the Loop bundle.\n\n"
                    "Summary: long-chain search rollout with baseline inspection, phase-scoped Builders, "
                    "regression review, evidence hardening, and strict GateKeeper closure."
                ),
                needs_user_input=True,
                bundle_yaml="",
                phase="agreement",
            )
            payload["agreement_summary"] = (
                "Long-chain search rollout with phase-scoped Builders, regression evidence, repair, "
                "and strict GateKeeper closure."
            )
            payload["readiness_checklist"] = {
                **LONG_CHAIN_ALIGNMENT_CHECKLIST,
                "explicit_confirmation": False,
            }
            payload["readiness_evidence"] = {
                **LONG_CHAIN_ALIGNMENT_READINESS_EVIDENCE,
                "open_questions": "Waiting for explicit user confirmation of the working agreement.",
            }
            payload["decision_options"] = [
                {
                    "id": "confirm",
                    "label": "Confirm long-chain agreement (recommended)",
                    "description": "Compile the staged workflow.",
                    "recommended": True,
                    "user_reply": "Confirm this long-chain agreement.",
                },
                {
                    "id": "adjust",
                    "label": "Adjust evidence stance",
                    "description": "Change one judgment before compiling.",
                    "recommended": False,
                    "user_reply": "Adjust the agreement:",
                },
            ]
            return payload
        payload = alignment_response(
            status="bundle",
            assistant_message="I compiled the confirmed long-chain Loopora bundle.",
            needs_user_input=False,
            bundle_yaml=bundle_to_yaml(long_chain_multi_builder_bundle(workdir)),
            phase="bundle",
        )
        payload["agreement_summary"] = (
            "Long-chain search rollout with phase-scoped Builders, regression evidence, repair, "
            "and strict GateKeeper closure."
        )
        payload["readiness_evidence"] = LONG_CHAIN_ALIGNMENT_READINESS_EVIDENCE
        return payload


def test_alignment_semantic_lint_accepts_long_chain_multi_builder_workflows(
    sample_workdir: Path,
) -> None:
    bundle = long_chain_multi_builder_bundle(sample_workdir)

    issues = lint_alignment_bundle_semantics(bundle)

    assert issues == []


def test_alignment_semantic_lint_requires_long_chain_gatekeeper_to_read_phase_handoffs(
    sample_workdir: Path,
) -> None:
    bundle = long_chain_multi_builder_bundle(sample_workdir)
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["gatekeeper_step"]["inputs"]["handoffs_from"] = ["evidence_hardening_builder_step"]

    issues = lint_alignment_bundle_semantics(bundle)

    assert ("long-chain GateKeeper must include an earlier phase, review, or Guide handoff in inputs.handoffs_from: gatekeeper_step") in issues


def test_alignment_service_accepts_confirmed_long_chain_workflow_traceability(
    service_factory,
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "search-workdir"
    (workdir / "design").mkdir(parents=True)
    (workdir / "tests").mkdir()
    (workdir / "AGENTS.md").write_text("# Rules\n\nRead design before changing contracts.\n", encoding="utf-8")
    (workdir / "design" / "README.md").write_text("# Design\n\nSearch boundaries.\n", encoding="utf-8")
    (workdir / "README.md").write_text("# Search stack\n\nPrototype search rollout.\n", encoding="utf-8")
    service = service_factory(scenario="success")
    service.executor_factory = lambda: LongChainAlignmentExecutor(scenario="success")

    created = service.create_alignment_session(
        workdir=workdir,
        message=(
            "I need a Loopora plan for a search relevance rollout. The task has query rewrite, retrieval, "
            "ranking, regression proof, and evidence hardening phases. Fake done is a final impressive ranking "
            "story with no baseline, no phase evidence, or masked recall regressions. GateKeeper should trust "
            "baseline artifacts, phase handoffs, regression checks, evidence IDs, and risk buckets more than summaries."
        ),
    )
    agreement = _wait_for_status(service, created["id"], "waiting_user")

    assert agreement["alignment_stage"] == "agreement_ready"
    assert not Path(agreement["bundle_path"]).exists()

    service.append_alignment_message(created["id"], "Confirm this long-chain agreement.")
    ready = _wait_for_status(service, created["id"], "ready")
    preview = service.get_alignment_bundle(created["id"])
    bundle = load_bundle_text(Path(ready["bundle_path"]).read_text(encoding="utf-8"))
    gatekeeper_inputs = bundle["workflow"]["steps"][-1]["inputs"]

    assert ready["validation"]["ok"] is True
    assert preview["ok"] is True
    assert preview["traceability"]["mapped_count"] == preview["traceability"]["required_count"]
    assert preview["traceability"]["mapped_count"] >= len(LONG_CHAIN_ALIGNMENT_CHECKLIST)
    assert [step["id"] for step in bundle["workflow"]["steps"]] == [
        "baseline_inspection_step",
        "query_builder_step",
        "retrieval_builder_step",
        "ranking_builder_step",
        "regression_inspection_step",
        "evidence_hardening_builder_step",
        "gatekeeper_step",
    ]
    assert gatekeeper_inputs["handoffs_from"] == [
        "baseline_inspection_step",
        "regression_inspection_step",
        "evidence_hardening_builder_step",
    ]
    assert gatekeeper_inputs["evidence_query"] == {"archetypes": ["builder", "inspector"], "limit": 40}
    assert lint_alignment_bundle_semantics(bundle) == []

from __future__ import annotations


GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE = (
    "Keep residual_risks empty on a clean pass. Do not put out-of-scope future expansion notes, already-verified "
    "baselines, fixtures, artifacts, or run-context facts in residual_risks. Use residual_risks only for accepted "
    "current-scope risk that still remains after evidence is inspected, and each item must name an owner, follow-up, "
    "or acceptance path. If that risk is not explicitly accepted, put it in blocking_issues or fail closed instead. "
    "Put verified baseline, fixture, artifact, or run-context facts in evidence_claims or decision_summary instead "
    "of residual_risks. "
)


GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE = (
    "GateKeeper evidence reuse rule: inspect known evidence, coverage gaps, handoffs, and cited artifacts before "
    "running new proof commands. When supporting upstream evidence already covers every required check and no current "
    "Blocking, Weak, Unproven, conflict, or unaccepted Residual risk remains except the core-derived gatekeeper.finish "
    "closure, decide from those exact evidence_refs without rerunning the same successful proof command. Run a new "
    "command or probe only to resolve missing, weak, conflicting, or stale evidence, to inspect a cited artifact needed "
    "for judgment, or when the step contract explicitly requires measured self evidence. "
)


AGENT_PLAN_RESIDUAL_RISK_SKELETON_GUIDANCE = (
    "- Residual risk: only accepted risks that still remain after evidence is inspected; put verified "
    "baseline, fixture, artifact, or run-context facts in Evidence Preferences or GateKeeper evidence_claims, "
    "not in Residual Risk. Future-scope notes are not residual risk unless they name an accepted current-scope risk "
    "with an owner, follow-up, or acceptance path."
)

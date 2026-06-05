from __future__ import annotations

import json

from loopora.proof_command_prompt_guidance import (
    INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE,
    PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE,
)
from loopora.residual_risk_prompt_guidance import (
    GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE,
    GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE,
)


def render_step_prompt(
    *,
    role: dict,
    prompt_label: str,
    prompt_body: str,
    step_instruction_context: dict,
    compiled_spec: dict,
) -> str:
    from loopora.headless_prompt import HeadlessPromptRequest, build_headless_prompt

    return build_headless_prompt(
        HeadlessPromptRequest(
            role=role,
            prompt_label=prompt_label,
            prompt_body=prompt_body,
            step_instruction_context=step_instruction_context,
            compiled_spec=compiled_spec,
        )
    )


def system_prompt_prefix(archetype: str) -> str:
    if archetype == "builder":
        return (
            "System safety rules:\n"
            "- You may edit files inside the workdir.\n"
            "- Preserve existing non-.loopora files and avoid destructive rewrites.\n"
            "- Prefer focused, incremental changes over broad resets.\n"
            "- Treat project-local instructions, design docs, and tests as contract and evidence inputs when they exist.\n"
            f"- {PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE}\n"
            "- If downstream review steps run in a parallel_group, leave one coherent handoff for all reviewers instead of splitting evidence across private notes.\n"
            "- Treat the run contract as frozen: do not reinterpret or lower Task, Done When, Guardrails, bundle collaboration summary, Loopora fit, strategy collaboration intent, role posture, Success Surface, Fake Done, Evidence Preferences, Execution Strategy, Judgment Tradeoffs, Local Governance, or Residual Risk; "
            "surface contract problems as evidence gaps or blockers instead.\n"
            "- In the handoff, name which claim moved toward Proven and what remains Weak, Unproven, Blocking, or Residual risk."
        )
    if archetype == "inspector":
        return (
            "System safety rules:\n"
            "- Collect evidence with project-owned commands, files, and artifacts.\n"
            "- Prefer concrete commands and observations.\n"
            "- Treat project-local instructions, design docs, and tests as contract and evidence inputs when they exist.\n"
            f"- {PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE}\n"
            f"- {INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE}\n"
            "- Classify important observations as Proven, Weak, Unproven, Blocking, or Residual risk when that helps downstream judgment.\n"
            "- If this step is in a parallel_group, cover only your assigned evidence responsibility and do not wait for peer reviewers.\n"
            "- Treat the run contract as frozen: do not reinterpret or lower Task, Done When, Guardrails, bundle collaboration summary, Loopora fit, strategy collaboration intent, role posture, Success Surface, Fake Done, Evidence Preferences, Execution Strategy, Judgment Tradeoffs, Local Governance, or Residual Risk; "
            "surface contract problems as evidence gaps or blockers instead.\n"
            "- Do not rewrite source files as part of inspection."
        )
    if archetype == "gatekeeper":
        return (
            "System safety rules:\n"
            "- Decide conservatively from direct evidence.\n"
            "- When evidence is weak, fail closed and explain what is missing.\n"
            "- Treat project-local instructions, design docs, and tests as contract and evidence inputs when they exist.\n"
            f"- {PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE}\n"
            "- Keep run status separate from task verdict, and organize the verdict as Proven, Weak, Unproven, Blocking, or Residual risk.\n"
            "- If upstream reviewers ran in a parallel_group, fan in every relevant review branch instead of treating the last handoff as the whole review.\n"
            "- Treat the run contract as frozen: do not reinterpret or lower Task, Done When, Guardrails, bundle collaboration summary, Loopora fit, strategy collaboration intent, role posture, Success Surface, Fake Done, Evidence Preferences, Execution Strategy, Judgment Tradeoffs, Local Governance, or Residual Risk; "
            "surface contract problems as evidence gaps or blockers instead.\n"
            "- Keep the verdict short and operational."
        )
    if archetype == "custom":
        return (
            "System safety rules:\n"
            "- You are a low-permission supporting role.\n"
            "- Read the workspace and evidence, but do not claim write actions or final authority.\n"
            "- Prefer concrete observations and next-step recommendations.\n"
            "- Treat project-local instructions, design docs, and tests as contract and evidence inputs when they exist.\n"
            "- Mark specialized observations as Proven, Weak, Unproven, Blocking, or Residual risk when useful.\n"
            "- If this step is in a parallel_group, cover only your custom specialization and leave evidence GateKeeper can fan in with peer branches.\n"
            "- Treat the run contract as frozen: do not reinterpret or lower Task, Done When, Guardrails, bundle collaboration summary, Loopora fit, strategy collaboration intent, role posture, Success Surface, Fake Done, Evidence Preferences, Execution Strategy, Judgment Tradeoffs, Local Governance, or Residual Risk; "
            "surface contract problems as evidence gaps or blockers instead.\n"
            "- Always return a stable takeaway with status, summary, blocking_items, and recommended_next_action."
        )
    return (
        "System safety rules:\n"
        "- Suggest the smallest useful direction change.\n"
        "- Do not act like a second GateKeeper.\n"
        "- Turn Blocking or Unproven gaps into a smaller proof or repair direction while keeping Residual risk visible.\n"
        "- Treat project-local instructions, design docs, and tests as contract and evidence inputs when they exist.\n"
        "- Treat the run contract as frozen: do not reinterpret or lower Task, Done When, Guardrails, bundle collaboration summary, Loopora fit, strategy collaboration intent, role posture, Success Surface, Fake Done, Evidence Preferences, Execution Strategy, Judgment Tradeoffs, Local Governance, or Residual Risk; "
        "surface contract problems as evidence gaps or blockers instead.\n"
        "- Keep the advice grounded in the current evidence."
    )


def output_contract_prompt(archetype: str) -> str:
    if archetype == "builder":
        return (
            "Output contract: return JSON with attempted, abandoned, assumption, summary, changed_files, "
            "proof_files, proof_artifacts, and artifact_paths. Use empty arrays for proof_files, "
            "proof_artifacts, artifact_paths, and changed_files when no files or proof artifacts were created. "
            "Use abandoned only for unfinished work or real downstream risk; use an empty string for deliberate scope limits."
        )
    if archetype == "inspector":
        return (
            "Output contract: return JSON with execution_summary, check_results, dynamic_checks, tester_observations, "
            "and coverage_results. Use empty arrays for check_results, dynamic_checks, and coverage_results when there are no items. "
            "Leave dynamic_checks empty unless you performed a new reproducible check that is not already represented by check_results or coverage_results. "
            "If a command verifies a listed Done When/check id, Fake Done, Evidence Preference, scope, checksum, or coverage target, put that evidence in check_results, coverage_results, or tester_observations instead of dynamic_checks; do not duplicate file-read, artifact-presence, checksum/scope, or command-success facts there. "
            "Each dynamic_checks item must name the extra nonduplicated claim it proves. "
            "Only populate coverage_results when you can explicitly verify or reject coverage target ids. "
            "Inside execution_summary, return total_checks, passed, failed, errored, and total_duration_ms. "
            "For every check_results item and dynamic_checks item, return id, title, status, and notes. "
            "For every coverage_results item, return target_id, status, evidence_refs, and note; use coverage status words such as covered, weak, blocked, or missing. "
            "Use notes to distinguish Proven, Weak, Unproven, Blocking, and Residual risk evidence."
        )
    if archetype == "gatekeeper":
        return (
            "Output contract: return JSON with passed, decision_summary, composite_score, metrics, metric_scores, "
            "blocking_issues, hard_constraint_violations, failed_check_ids, priority_failures, feedback_to_builder, "
            "feedback_to_generator, evidence_refs, evidence_claims, residual_risks, and coverage_results. "
            "Use empty arrays for metrics, blocking_issues, hard_constraint_violations, failed_check_ids, "
            "priority_failures, evidence_refs, evidence_claims, residual_risks, and coverage_results when there are no items. "
            "Metrics rows must include name, value, threshold, and passed. Inside metric_scores, provide exactly "
            "check_pass_rate and quality_score, each with value, threshold, and passed. Priority failures must include error_code and summary. "
            "For every coverage_results item, return target_id, status, evidence_refs, and note; use covered for a verified target and keep Proven/Weak/Unproven/Blocking/Residual risk as verdict buckets. "
            "A pass must cite supporting upstream evidence_refs from the Evidence ledger; a plain Builder handoff is not support unless it carries a proof artifact or measured evidence. If this is the first gate in the workflow, "
            "claims alone are not enough; provide concrete metric_scores tied to the evidence you inspected. "
            f"{GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE}"
            "Accepted residual_risks must name the risk plus an owner, follow-up, or acceptance path; vague residual risk keeps the pass blocked. "
            f"{GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE}"
            "If the run contract disallows accepted residual risk, keep residual_risks empty and report any remaining risk as blocking instead of passing. "
            "The decision_summary should separate run status from task verdict and name any Weak, Unproven, Blocking, or Residual risk evidence."
        )
    if archetype == "custom":
        return (
            "Output contract: return JSON with status, summary, blocking_items, recommended_next_action, "
            "observations, recommendations, risks, and handoff_note. Use empty arrays for blocking_items, "
            "observations, recommendations, and risks when there are no items."
        )
    return (
        "Output contract: return JSON with created_at_iter, mode, consumed, analysis, seed_question, and meta_note. "
        "Inside analysis, turn Blocking or Unproven gaps into the smallest repair direction, strengthen Weak evidence only when it changes the decision, "
        "and keep Residual risk visible."
    )


def render_run_contract_section(contract: dict, compiled_spec: dict) -> str:
    constraints = contract.get("constraints") or "No explicit constraints were provided."
    success_surface = json.dumps(contract.get("success_surface") or [], ensure_ascii=False, indent=2)
    fake_done_states = json.dumps(contract.get("fake_done_states") or [], ensure_ascii=False, indent=2)
    evidence_preferences = json.dumps(contract.get("evidence_preferences") or [], ensure_ascii=False, indent=2)
    coverage_targets = json.dumps(contract.get("coverage_targets") or [], ensure_ascii=False, indent=2)
    collaboration_summary = str(
        contract.get("collaboration_summary") or "No explicit bundle collaboration summary was provided."
    ).strip()
    strategy_collaboration_intent = str(
        contract.get("strategy_collaboration_intent")
        or "No explicit strategy collaboration intent was provided."
    ).strip()
    loop_fit_reasons = json.dumps(contract.get("loop_fit_reasons") or [], ensure_ascii=False, indent=2)
    judgment_tradeoffs = json.dumps(contract.get("judgment_tradeoffs") or [], ensure_ascii=False, indent=2)
    execution_strategy = json.dumps(contract.get("execution_strategy") or [], ensure_ascii=False, indent=2)
    local_governance = json.dumps(contract.get("local_governance") or [], ensure_ascii=False, indent=2)
    role_postures = json.dumps(contract.get("role_postures") or [], ensure_ascii=False, indent=2)
    residual_risk = str(contract.get("residual_risk") or "No explicit residual-risk stance was provided.").strip()
    return (
        "Run contract summary:\n"
        f"- Completion mode: {contract.get('completion_mode')}\n"
        f"- Bundle collaboration summary: {collaboration_summary}\n"
        f"- Loopora fit: {loop_fit_reasons}\n"
        f"- Judgment tradeoffs: {judgment_tradeoffs}\n"
        f"- Execution strategy: {execution_strategy}\n"
        f"- Local governance: {local_governance}\n"
        f"- Role postures: {role_postures}\n"
        f"- Strategy preset: {contract.get('strategy_preset')}\n"
        f"- Strategy collaboration intent: {strategy_collaboration_intent}\n"
        f"- Check mode: {contract.get('check_mode')}\n"
        f"- Check count: {contract.get('check_count')}\n\n"
        f"Goal:\n{contract.get('goal', '').strip()}\n\n"
        f"Checks:\n{json.dumps(compiled_spec.get('checks', []), ensure_ascii=False, indent=2)}\n\n"
        f"Constraints:\n{constraints}\n\n"
        f"Coverage targets:\n{coverage_targets}\n\n"
        f"Success surface:\n{success_surface}\n\n"
        f"Fake done states:\n{fake_done_states}\n\n"
        f"Evidence preferences:\n{evidence_preferences}\n\n"
        f"Residual risk:\n{residual_risk}"
    )


def render_role_note_section(role_note: str) -> str:
    if not str(role_note or "").strip():
        return ""
    return f"Role notes for the current role:\n{str(role_note).strip()}"


def _combine_role_guidance(spec_role_note: str, role_posture: str) -> str:
    parts: list[str] = []
    if str(role_posture or "").strip():
        parts.append(f"Role definition posture:\n{str(role_posture).strip()}")
    if str(spec_role_note or "").strip():
        parts.append(f"Spec role notes:\n{str(spec_role_note).strip()}")
    return "\n\n".join(parts).strip()

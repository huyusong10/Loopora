from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loopora.service_prompt_checks import normalize_generated_checks, render_checks
from loopora.service_prompt_requests import (
    GeneratorPromptRequest as GeneratorPromptRequest,
    generator_prompt_request_from_args,
)
from loopora.service_prompt_schemas import (
    BUILDER_SCHEMA as BUILDER_SCHEMA,
    CHALLENGER_SCHEMA as CHALLENGER_SCHEMA,
    CHECK_PLANNER_SCHEMA as CHECK_PLANNER_SCHEMA,
    CUSTOM_SCHEMA as CUSTOM_SCHEMA,
    GATEKEEPER_SCHEMA as GATEKEEPER_SCHEMA,
    GENERATOR_SCHEMA as GENERATOR_SCHEMA,
    GUIDE_SCHEMA as GUIDE_SCHEMA,
    INSPECTOR_SCHEMA as INSPECTOR_SCHEMA,
    TESTER_SCHEMA as TESTER_SCHEMA,
    VERIFIER_SCHEMA as VERIFIER_SCHEMA,
)
from loopora.proof_command_prompt_guidance import (
    INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE,
    PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE,
)
from loopora.residual_risk_prompt_guidance import (
    GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE,
    GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE,
)
from loopora.specs import resolve_role_note


FROZEN_CONTRACT_GUIDANCE = (
    "Treat the run contract as frozen: do not reinterpret or lower the Task, Done When, checks, guardrails, "
    "bundle collaboration summary, Loopora fit, workflow intent, role posture, Success Surface, Fake Done, Evidence Preferences, Execution Strategy, Judgment Tradeoffs, Local Governance, or Residual Risk. "
    "If the contract seems too narrow, too loose, or conflicted, surface that as an evidence gap, blocker, "
    "or Loop-adjustment recommendation instead of silently changing the target. "
    "Treat project-local instructions, design docs, and tests as contract and evidence inputs when they exist.\n"
)


class ServiceRunPromptMixin:
    def _check_planner_prompt(self, compiled_spec: dict) -> str:
        constraints = compiled_spec.get("constraints") or "No explicit constraints were provided."
        return (
            "You are the Check Planner inside Loopora.\n"
            "The spec did not provide explicit checks, so you must derive a frozen exploratory set for this run.\n"
            "Inspect the current workdir, stay close to the stated goal, and do not invent unrelated requirements.\n"
            f"{FROZEN_CONTRACT_GUIDANCE}"
            "Generate 3 to 5 independently judgeable checks. Prefer concise titles and practical evaluation criteria.\n"
            "Do not edit files.\n"
            f"Goal:\n{compiled_spec['goal']}\n\n"
            f"Constraints:\n{constraints}\n\n"
            "Return JSON with `checks` and `generation_notes`. Each check must include `title`, `details`, `when`, `expect`, and `fail_if`. "
            "Use empty strings only when a field truly cannot be made more specific."
        )

    def _role_note_block(self, compiled_spec: dict, *, role_name: str, archetype: str) -> str:
        role_note = resolve_role_note(compiled_spec, role_name=role_name, archetype=archetype)
        if not role_note:
            return ""
        return f"Role notes for this role:\n{role_note}\n\n"

    def _generator_prompt(
        self,
        request: GeneratorPromptRequest | dict,
        workdir: Path | None = None,
        iter_id: int | None = None,
        mode: str | None = None,
        **feedback: Any,
    ) -> str:
        prompt_request = generator_prompt_request_from_args(request, workdir, iter_id, mode, feedback)
        compiled_spec = prompt_request.compiled_spec
        constraints = compiled_spec.get("constraints") or "No explicit constraints were provided."
        role_note = self._role_note_block(compiled_spec, role_name="Builder", archetype="builder")
        bootstrap_guidance = ""
        action_guidance = (
            "This role must end with a concrete attempt, not only repo inspection.\n"
            "Once you have enough context to act, prefer making a focused change and/or running the most relevant existing verification, build, benchmark, or diagnosis command in the workdir.\n"
            "If the repository already contains a project-owned script that directly measures the goal, prefer using it to establish evidence in this iteration.\n"
            "If you launch a long-running project-owned command, do not wait idly for stdout alone. While it runs, inspect fresh status files, logs, reports, and intermediate artifacts so you can tell healthy progress from a harness defect.\n"
            "If those observations reveal a real process defect in the owned evaluation flow (for example stale progress snapshots, ineffective timeouts, misleading status reporting, or broken report generation), fixing that defect is in scope before the benchmark fully finishes.\n"
            "For benchmark-driven goals, prefer one real end-to-end run plus targeted harness fixes over many ad hoc spot checks.\n"
            "Do not spend the whole turn only reading files unless you are blocked by missing information that truly cannot be resolved any other way.\n\n"
        )
        if prompt_request.iter_id == 0 and self._is_bootstrap_workspace(prompt_request.workdir):
            bootstrap_guidance = (
                "Workspace state:\n"
                "Only the spec is present right now, so this iteration should bootstrap the first implementation.\n"
                "Create the smallest runnable prototype in this round instead of spending the whole turn on planning.\n"
                "Because the workspace is essentially empty, it is safe to add the first app files now; this is not permission to wipe or reset a non-empty project.\n"
                "Prefer a minimal static entry point plus tiny supporting files when needed.\n\n"
            )
        prior_iteration_feedback = self._generator_prior_iteration_feedback(
            prompt_request.iter_id,
            previous_generator_result=prompt_request.previous_generator_result,
            previous_tester_result=prompt_request.previous_tester_result,
            previous_verifier_result=prompt_request.previous_verifier_result,
            previous_challenger_result=prompt_request.previous_challenger_result,
        )
        return (
            "You are the Generator role inside Loopora.\n"
            "Goal: improve the workspace to satisfy the spec with one coherent change direction.\n"
            f"Iteration: {prompt_request.iter_id}\n"
            f"Mode: {prompt_request.mode}\n"
            f"Check mode: {compiled_spec.get('check_mode', 'specified')}\n"
            "You may edit files inside the workdir. Do not write into .loopora except for explicitly requested outputs.\n"
            "Treat existing non-.loopora files as user-owned. Never wipe the whole workdir, bulk-delete existing files, or reset the project from scratch.\n"
            "Prefer targeted in-place edits and additive changes. Delete a file only when that deletion is narrowly necessary to your change.\n"
            f"{FROZEN_CONTRACT_GUIDANCE}"
            f"{PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE}\n"
            f"{action_guidance}"
            f"{bootstrap_guidance}"
            f"{prior_iteration_feedback}"
            f"Spec goal:\n{compiled_spec['goal']}\n\n"
            f"Checks:\n{self._render_checks(compiled_spec['checks'])}\n\n"
            f"Constraints:\n{constraints}\n\n"
            f"{role_note}"
            "Return JSON with attempted, abandoned, assumption, summary, changed_files, proof_files, proof_artifacts, and artifact_paths. "
            "Use empty arrays for changed_files, proof_files, proof_artifacts, and artifact_paths when no files or proof artifacts were created. "
            "Use abandoned only for unfinished work or real downstream risk; use an empty string for deliberate scope limits."
        )

    def _generator_prior_iteration_feedback(
        self,
        iter_id: int,
        *,
        previous_generator_result: dict | None = None,
        previous_tester_result: dict | None = None,
        previous_verifier_result: dict | None = None,
        previous_challenger_result: dict | None = None,
    ) -> str:
        if iter_id <= 0:
            return ""
        lines = ["Previous iteration evidence:"]
        if previous_generator_result:
            lines.append(
                f"- Last attempted: {self._truncate_text(previous_generator_result.get('attempted') or previous_generator_result.get('summary'), 220) or 'none'}"
            )
        if previous_tester_result:
            failed_items = list(previous_tester_result.get("failed_items", []))
            lines.append(f"- Tester observations: {self._truncate_text(previous_tester_result.get('tester_observations'), 220) or 'none'}")
            lines.append(f"- Non-passing items last round: {self._format_failure_refs(failed_items)}")
        if previous_verifier_result:
            lines.append(f"- Verifier decision: {self._truncate_text(previous_verifier_result.get('decision_summary'), 240) or 'none'}")
            lines.append(f"- Previous composite score: `{previous_verifier_result.get('composite_score', 'n/a')}`")
            lines.append(
                "- Failed checks last round: "
                f"{self._format_inline_code_list(list(previous_verifier_result.get('failed_check_titles', []) or previous_verifier_result.get('failed_check_ids', [])), empty='none', limit=4)}"
            )
            lines.append(
                f"- Next actions from verifier: {self._format_inline_code_list(list(previous_verifier_result.get('next_actions', [])), empty='none', limit=4)}"
            )
        if previous_challenger_result:
            lines.append(
                f"- Challenger recommended shift: {self._truncate_text((previous_challenger_result.get('analysis') or {}).get('recommended_shift'), 220) or 'none'}"
            )
            lines.append(f"- Challenger seed question: {self._truncate_text(previous_challenger_result.get('seed_question'), 220) or 'none'}")
        lines.append("Use this evidence as your starting point for the next focused improvement. Do not restart from scratch.")
        return "\n".join(lines) + "\n\n"

    def _tester_prompt(self, compiled_spec: dict, iter_id: int, mode: str) -> str:
        checks = json.dumps(compiled_spec["checks"], ensure_ascii=False, indent=2)
        role_note = self._role_note_block(compiled_spec, role_name="Inspector", archetype="inspector")
        return (
            "You are the Tester role inside Loopora.\n"
            "Inspect the workdir, run the most relevant commands, and evaluate the listed checks.\n"
            "Do not edit source files.\n"
            "Keep notes concise and evidence-focused. Prefer concrete commands, files, and observed outputs over restating the whole spec.\n"
            "Use the stable evidence buckets in notes when useful: Proven, Weak, Unproven, Blocking, and Residual risk.\n"
            f"{FROZEN_CONTRACT_GUIDANCE}"
            f"{PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE}\n"
            f"{INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE}\n"
            "When fresh project-owned benchmark artifacts already exist, inspect them first and reuse them as primary evidence before rerunning an expensive end-to-end flow.\n"
            "If a long-running evaluation appears stalled, confirm that with live status files, logs, or preserved artifacts instead of guessing from silent stdout alone.\n"
            f"Iteration: {iter_id}\n"
            f"Mode: {mode}\n"
            f"Checks:\n{checks}\n\n"
            f"{role_note}"
            "Inside `execution_summary`, return `total_checks`, `passed`, `failed`, `errored`, and `total_duration_ms`.\n"
            "For every `check_results` item and every `dynamic_checks` item, return `id`, `title`, `status`, and `notes`.\n"
            "Return `check_results`, `dynamic_checks`, and `coverage_results` as empty lists when there are no items.\n"
            "Leave `dynamic_checks` empty unless you performed a new reproducible check that is not already represented by `check_results` or `coverage_results`. "
            "If a command verifies a listed Done When/check id, Fake Done, Evidence Preference, scope, checksum, or coverage target, put that evidence in `check_results`, `coverage_results`, or `tester_observations` instead of `dynamic_checks`; do not duplicate file-read, artifact-presence, checksum/scope, or command-success facts there. "
            "Each `dynamic_checks` item must name the extra nonduplicated claim it proves.\n"
            "Only populate `coverage_results` when you can explicitly verify or reject Fake Done or Evidence Preferences coverage targets; "
            "entries must include target_id, status, evidence_refs, and note. Use coverage status words such as `covered`, `weak`, `blocked`, or `missing`; keep Proven/Weak/Unproven/Blocking/Residual risk as note buckets, not status values.\n"
            "Return JSON with execution_summary, check_results, dynamic_checks, tester_observations, and coverage_results."
        )

    def _verifier_prompt(self, compiled_spec: dict, tester_output: dict, iter_id: int, mode: str) -> str:
        constraints = compiled_spec.get("constraints") or "No explicit constraints were provided."
        role_note = self._role_note_block(compiled_spec, role_name="GateKeeper", archetype="gatekeeper")
        return (
            "You are the Verifier role inside Loopora.\n"
            "Judge the tester output conservatively against the goal, checks, and constraints.\n"
            "Keep the verdict concise and tied to direct evidence. Do not rewrite the whole spec as policy prose.\n"
            "When the main evidence comes from a project-owned benchmark or harness, treat those artifacts as primary evidence.\n"
            "Distinguish product or knowledge failures from harness-process defects, and surface harness defects as first-class failures when they block trustworthy evaluation.\n"
            "Separate run status from task verdict. Organize evidence as Proven, Weak, Unproven, Blocking, and Residual risk; do not treat a normal run lifecycle as task proof.\n"
            f"{FROZEN_CONTRACT_GUIDANCE}"
            f"{PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE}\n"
            "Return `coverage_results` as an empty list unless you can explicitly verify or reject Fake Done or Evidence Preferences coverage targets; entries must include target_id, status, evidence_refs, and note. Use coverage status words such as `covered`, `weak`, `blocked`, or `missing`; keep Proven/Weak/Unproven/Blocking/Residual risk as verdict buckets, not status values.\n"
            f"Iteration: {iter_id}\n"
            f"Mode: {mode}\n"
            f"Goal:\n{compiled_spec['goal']}\n\n"
            f"Checks:\n{self._render_checks(compiled_spec['checks'])}\n\n"
            f"Constraints:\n{constraints}\n\n"
            f"{role_note}"
            f"Tester output:\n{json.dumps(tester_output, ensure_ascii=False, indent=2)}\n\n"
            "Return `metrics` as rows with `name`, `value`, `threshold`, and `passed`.\n"
            "Inside `metric_scores`, provide exactly `check_pass_rate` and `quality_score`, each with `value`, `threshold`, and `passed`.\n"
            "For every `priority_failures` item, return `error_code` and `summary`.\n"
            "For every `coverage_results` item, return `target_id`, `status`, `evidence_refs`, and `note`; use `covered` for a verified target.\n"
            "When passing, cite concrete supporting Evidence ledger item ids in `evidence_refs`; a plain Builder handoff is not support unless it carries a proof artifact or measured evidence. "
            "If this GateKeeper step is the first evidence reader, prose claims alone are not enough; include measured `metric_scores` and put concise proof statements in `evidence_claims`.\n"
            f"{GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE}\n"
            "Accepted `residual_risks` must name the risk plus an owner, follow-up, or acceptance path; vague residual risk keeps the pass blocked.\n"
            f"{GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE}\n"
            "Return `metrics`, `blocking_issues`, `hard_constraint_violations`, `failed_check_ids`, `priority_failures`, `evidence_refs`, `evidence_claims`, `residual_risks`, and `coverage_results` as arrays; "
            "use empty arrays when there are no items.\n"
            "Return JSON with passed, decision_summary, composite_score, metrics, metric_scores, blocking_issues, "
            "hard_constraint_violations, failed_check_ids, priority_failures, feedback_to_builder, feedback_to_generator, evidence_refs, evidence_claims, residual_risks, and coverage_results."
        )

    def _challenger_prompt(self, compiled_spec: dict, stagnation: dict, iter_id: int) -> str:
        constraints = compiled_spec.get("constraints") or "No explicit constraints were provided."
        role_note = self._role_note_block(compiled_spec, role_name="Guide", archetype="guide")
        return (
            "You are the Challenger role inside Loopora.\n"
            "Suggest the smallest high-leverage direction change when progress stalls.\n"
            "Use the stable evidence buckets to choose the repair direction: Proven, Weak, Unproven, Blocking, and Residual risk.\n"
            "Turn Blocking or Unproven gaps into the next smallest proof or fix, strengthen Weak evidence only when it changes the decision, and keep Residual risk visible.\n"
            f"{FROZEN_CONTRACT_GUIDANCE}"
            f"Iteration: {iter_id}\n"
            f"Spec goal:\n{compiled_spec['goal']}\n\n"
            f"Checks:\n{self._render_checks(compiled_spec['checks'])}\n\n"
            f"Constraints:\n{constraints}\n\n"
            f"{role_note}"
            f"Stagnation state:\n{json.dumps(stagnation, ensure_ascii=False, indent=2)}\n\n"
            "Inside `analysis`, return `stagnation_pattern`, `recommended_shift`, and `risk_note`.\n"
            "Return JSON with created_at_iter, mode, consumed, analysis, seed_question, and meta_note."
        )

    def _normalize_generated_checks(self, checks: object) -> list[dict]:
        return normalize_generated_checks(checks)

    def _render_checks(self, checks: list[dict]) -> str:
        return render_checks(checks)

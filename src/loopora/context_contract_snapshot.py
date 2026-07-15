from __future__ import annotations

from dataclasses import dataclass

from loopora.run_artifacts import RunArtifactLayout, artifact_ref
from loopora.service_bundle_control_trace_mining import (
    build_execution_strategy_trace,
    build_judgment_tradeoff_trace,
    build_loop_fit_trace,
    build_runtime_local_governance_trace,
)
from loopora.service_bundle_control_trace_mining import role_posture_preview
from loopora.utils import coerced_non_negative_int, structured_non_negative_int


@dataclass(frozen=True)
class RunContractSnapshotRequest:
    run: dict
    compiled_spec: dict
    strategy_source: dict
    prompt_files: dict[str, str]
    workspace_baseline: dict
    layout: RunArtifactLayout
    collaboration_summary: str = ""
    source_bundle: dict | None = None


def build_run_contract_snapshot(request: RunContractSnapshotRequest) -> dict:
    run = request.run
    layout = request.layout
    compiled_spec = request.compiled_spec if isinstance(request.compiled_spec, dict) else {}
    strategy_source = request.strategy_source
    tradeoff_roles = _strategy_source_roles_with_prompt_files(strategy_source, request.prompt_files)
    role_posture_roles = _strategy_source_roles_with_runtime_prompt_markdown(strategy_source, request.prompt_files)
    source_bundle = contract_source_bundle(request.source_bundle)
    return {
        "run_id": run["id"],
        "loop_id": run.get("loop_id"),
        "source_bundle": source_bundle,
        "workdir": str(run.get("workdir") or ""),
        "completion_mode": str(run.get("completion_mode") or "gatekeeper"),
        "max_iters": coerced_non_negative_int(run.get("max_iters")),
        "max_role_retries": coerced_non_negative_int(run.get("max_role_retries")),
        "delta_threshold": float(run.get("delta_threshold") or 0.0),
        "trigger_window": coerced_non_negative_int(run.get("trigger_window")),
        "regression_window": coerced_non_negative_int(run.get("regression_window")),
        "iteration_interval_seconds": float(run.get("iteration_interval_seconds") or 0.0),
        "executor": {
            "kind": str(run.get("executor_kind") or "codex"),
            "mode": str(run.get("executor_mode") or "preset"),
            "model": str(run.get("model") or ""),
            "reasoning_effort": str(run.get("reasoning_effort") or ""),
        },
        "compiled_spec": compiled_spec,
        "collaboration_summary": str(request.collaboration_summary or "").strip(),
        "success_surface": contract_string_list(compiled_spec.get("success_surface")),
        "fake_done_states": contract_string_list(compiled_spec.get("fake_done_states")),
        "evidence_preferences": contract_string_list(compiled_spec.get("evidence_preferences")),
        "residual_risk": contract_string(compiled_spec.get("residual_risk")),
        "loop_fit_reasons": build_loop_fit_trace(request.collaboration_summary),
        "judgment_tradeoffs": build_judgment_tradeoff_trace(
            collaboration_summary=request.collaboration_summary,
            raw_sections=compiled_spec.get("raw_sections"),
            roles=tradeoff_roles,
            strategy_source=strategy_source,
        ),
        "execution_strategy": build_execution_strategy_trace(
            collaboration_summary=request.collaboration_summary,
            raw_sections=compiled_spec.get("raw_sections"),
            roles=tradeoff_roles,
            strategy_source=strategy_source,
        ),
        "local_governance": build_runtime_local_governance_trace(
            raw_sections=compiled_spec.get("raw_sections"),
            roles=tradeoff_roles,
            strategy_source=strategy_source,
        ),
        "role_postures": contract_role_postures(role_posture_roles),
        "workflow": {
            "preset": str(strategy_source.get("preset") or "custom"),
            "collaboration_intent": str(strategy_source.get("collaboration_intent") or "").strip(),
            "roles": [
                {
                    "id": str(role.get("id") or ""),
                    "name": str(role.get("name") or ""),
                    "archetype": str(role.get("archetype") or ""),
                    "prompt_ref": str(role.get("prompt_ref") or ""),
                    "posture_notes": str(role.get("posture_notes") or "").strip(),
                }
                for role in strategy_source.get("roles", [])
            ],
            "steps": [
                {
                    "id": str(step.get("id") or ""),
                    "role_id": str(step.get("role_id") or ""),
                    "on_pass": str(step.get("on_pass") or ""),
                    "model": str(step.get("model") or ""),
                    "inherit_session": bool(step.get("inherit_session")),
                    "extra_cli_args": str(step.get("extra_cli_args") or ""),
                    "parallel_group": str(step.get("parallel_group") or ""),
                    "inputs": dict(step.get("inputs") or {}),
                    "action_policy": dict(step.get("action_policy") or {}),
                }
                for step in strategy_source.get("steps", [])
            ],
            "controls": list(strategy_source.get("controls") or []),
        },
        "prompt_refs": sorted(request.prompt_files.keys()),
        "workspace_baseline": {
            "file_count": coerced_non_negative_int(request.workspace_baseline.get("file_count")),
            "artifact": artifact_ref(layout, layout.workspace_baseline_path, kind="workspace", label="workspace-baseline"),
        },
        "artifacts": {
            "summary": artifact_ref(layout, layout.summary_path, kind="summary", label="summary"),
            "compiled_spec": artifact_ref(layout, layout.contract_compiled_spec_path, kind="contract", label="compiled-spec"),
            "strategy_source": artifact_ref(layout, layout.contract_strategy_source_path, kind="contract", label="strategy-source"),
            "workflow": artifact_ref(layout, layout.contract_workflow_path, kind="contract", label="workflow"),
            "run_contract": artifact_ref(layout, layout.run_contract_path, kind="contract", label="run-contract"),
            "workspace_baseline": artifact_ref(
                layout,
                layout.workspace_baseline_path,
                kind="workspace",
                label="workspace-baseline",
            ),
            "latest_state": artifact_ref(layout, layout.latest_state_path, kind="state", label="latest-state"),
            "latest_iteration_summary": artifact_ref(
                layout,
                layout.latest_iteration_summary_path,
                kind="state",
                label="latest-iteration-summary",
            ),
            "timeline_events": artifact_ref(layout, layout.timeline_events_path, kind="timeline", label="timeline-events"),
            "timeline_iterations": artifact_ref(
                layout,
                layout.timeline_iterations_path,
                kind="timeline",
                label="timeline-iterations",
            ),
            "timeline_metrics": artifact_ref(layout, layout.timeline_metrics_path, kind="timeline", label="timeline-metrics"),
            "evidence_ledger": artifact_ref(layout, layout.evidence_ledger_path, kind="evidence", label="evidence-ledger"),
            "evidence_coverage": artifact_ref(layout, layout.evidence_coverage_path, kind="evidence", label="evidence-coverage"),
            "evidence_manifest": artifact_ref(layout, layout.evidence_manifest_path, kind="evidence", label="evidence-manifest"),
        },
    }


def contract_string(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def contract_source_bundle(value: object) -> dict:
    if not isinstance(value, dict):
        return {}
    bundle_id = contract_string(value.get("id"))
    if not bundle_id:
        return {}
    source = {
        "id": bundle_id,
        "name": contract_string(value.get("name")),
        "revision": structured_non_negative_int(value.get("revision")),
        "source_bundle_id": contract_string(value.get("source_bundle_id")),
        "imported_from_path": contract_string(value.get("imported_from_path")),
    }
    bundle_sha256 = contract_string(value.get("bundle_sha256"))
    bundle_bytes = structured_non_negative_int(value.get("bundle_bytes"))
    bundle_yaml_path = contract_string(value.get("bundle_yaml_path"))
    if bundle_sha256:
        source["bundle_sha256"] = bundle_sha256
    if bundle_bytes:
        source["bundle_bytes"] = bundle_bytes
    if bundle_yaml_path:
        source["bundle_yaml_path"] = bundle_yaml_path
    return source


def contract_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def contract_mapping_list(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def contract_role_postures(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    postures: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        posture_notes = contract_string(item.get("posture_notes")) or role_posture_preview(item)
        if not posture_notes:
            continue
        postures.append(
            {
                "role_id": contract_string(item.get("role_id") or item.get("id")),
                "role_name": contract_string(item.get("role_name") or item.get("name")),
                "archetype": contract_string(item.get("archetype")),
                "posture_notes": posture_notes,
            }
        )
    return postures


def _strategy_source_roles_with_prompt_files(strategy_source: dict, prompt_files: dict[str, str]) -> list[dict]:
    roles = (
        [dict(role) for role in list(strategy_source.get("roles") or []) if isinstance(role, dict)]
        if isinstance(strategy_source, dict)
        else []
    )
    if not isinstance(prompt_files, dict):
        return roles
    for prompt_ref, prompt_markdown in prompt_files.items():
        text = str(prompt_markdown or "").strip()
        if not text:
            continue
        roles.append({"key": str(prompt_ref or ""), "prompt_markdown": text})
    return roles


def _strategy_source_roles_with_runtime_prompt_markdown(strategy_source: dict, prompt_files: dict[str, str]) -> list[dict]:
    roles = (
        [dict(role) for role in list(strategy_source.get("roles") or []) if isinstance(role, dict)]
        if isinstance(strategy_source, dict)
        else []
    )
    if not isinstance(prompt_files, dict):
        return roles
    for role in roles:
        prompt_ref = str(role.get("prompt_ref") or "").strip()
        prompt_markdown = str(prompt_files.get(prompt_ref) or "").strip() if prompt_ref else ""
        if prompt_markdown:
            role["prompt_markdown"] = prompt_markdown
    return roles

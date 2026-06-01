from __future__ import annotations

from loopora.runner_support_requests import RunnerSummaryRequest
from loopora.score_history_values import structured_score_value, structured_score_values
from loopora.structured_booleans import structured_bool_is_true
from loopora.structured_numbers import structured_non_negative_int
from loopora.utils import utc_now


def build_runner_iteration_entry(
    iter_id: int,
    step_results: list[dict],
    stagnation: dict,
    *,
    previous_composite: float | None,
) -> dict:
    by_archetype = {item["role"]["archetype"]: item["output"] for item in step_results}
    gatekeeper_output = by_archetype.get("gatekeeper", {})
    composite_score = _score_value(gatekeeper_output.get("composite_score"))
    previous_score = _score_value(previous_composite)
    strategy_steps = [
        {
            "step_id": item["step"]["id"],
            "role_id": item["role"]["id"],
            "runtime_role": item.get("runtime_role"),
            "role_name": item["role"]["name"],
            "archetype": item["role"]["archetype"],
            "model": item.get("resolved_model") or "",
            "parallel_group": str(item["step"].get("parallel_group") or ""),
        }
        for item in step_results
    ]
    entry = {
        "phase": "complete",
        "iter": iter_id,
        "timestamp": utc_now(),
        "strategy_steps": strategy_steps,
        "workflow": strategy_steps,
        "builder": by_archetype.get("builder", {}),
        "inspector": by_archetype.get("inspector", {}),
        "gatekeeper": gatekeeper_output,
        "guide": by_archetype.get("guide", {}),
        "evidence": {
            "gatekeeper_refs": list(gatekeeper_output.get("evidence_refs", [])),
            "gatekeeper_status": gatekeeper_output.get("evidence_gate_status"),
        },
        "score": {
            "composite": composite_score,
            "delta": round(composite_score - previous_score, 6) if composite_score is not None and previous_score is not None else None,
            "passed": structured_bool_is_true(gatekeeper_output.get("passed")),
        },
        "stagnation": {
            "mode": stagnation.get("stagnation_mode", "none"),
            "evidence_progress_mode": stagnation.get("evidence_progress_mode", "none"),
            "recent_composites": structured_score_values(stagnation.get("recent_composites")),
            "recent_deltas": structured_score_values(stagnation.get("recent_deltas")),
            "consecutive_low_delta": structured_non_negative_int(stagnation.get("consecutive_low_delta")),
            "covered_check_count": structured_non_negative_int(stagnation.get("latest_covered_check_count")),
            "missing_check_count": structured_non_negative_int(stagnation.get("latest_missing_check_count")),
            "consecutive_no_required_coverage_delta": structured_non_negative_int(
                stagnation.get("consecutive_no_required_coverage_delta")
            ),
        },
    }
    entry["generator"] = entry["builder"]
    entry["tester"] = entry["inspector"]
    entry["verifier"] = entry["gatekeeper"]
    if entry["guide"]:
        entry["challenger"] = entry["guide"]
    return entry


def build_runner_summary(request: RunnerSummaryRequest) -> str:
    gatekeeper_output = next(
        (item["output"] for item in reversed(request.step_results) if item["role"]["archetype"] == "gatekeeper"),
        {},
    )
    gatekeeper_passed = structured_bool_is_true(gatekeeper_output.get("passed"))
    completion_mode = str(request.run.get("completion_mode", "gatekeeper")).strip().lower() or "gatekeeper"
    status_line = (
        "Planned rounds completed."
        if request.exhausted and completion_mode == "rounds"
        else "Max iterations exhausted."
        if request.exhausted
        else "Still iterating."
    )
    if gatekeeper_passed and completion_mode == "gatekeeper":
        status_line = "All checks passed in this iteration."
    elif gatekeeper_passed:
        status_line = "GateKeeper passed in this iteration, but the run stays in round-based mode."
    delta_text = (
        f"`{round(gatekeeper_output['composite_score'] - request.previous_composite, 6):+}`"
        if request.previous_composite is not None and gatekeeper_output.get("composite_score") is not None
        else "`n/a`"
    )
    covered_check_count = structured_non_negative_int(request.stagnation.get("latest_covered_check_count"))
    missing_check_count = structured_non_negative_int(request.stagnation.get("latest_missing_check_count"))
    lines = [
        "# Loopora Run Summary",
        "",
        f"- Workdir: `{request.run['workdir']}`",
        f"- Iteration: `{request.iter_id + 1 if request.iter_id >= 0 else 0}`",
        f"- Strategy preset: `{request.strategy_source.get('preset') or 'custom'}`",
        f"- Check mode: `{request.compiled_spec.get('check_mode', 'specified')}`",
        f"- Check count: `{len(request.compiled_spec.get('checks', []))}`",
        f"- Completion mode: `{completion_mode}`",
        f"- Iteration interval seconds: `{request.run.get('iteration_interval_seconds', 0.0)}`",
        f"- Composite score: `{gatekeeper_output.get('composite_score', 'n/a')}`",
        f"- Score delta vs previous iteration: {delta_text}",
        f"- Passed: `{gatekeeper_passed}`",
        f"- Stagnation mode: `{request.stagnation.get('stagnation_mode', 'none')}`",
        f"- Evidence progress mode: `{request.stagnation.get('evidence_progress_mode', 'none')}`",
        f"- Required coverage: `{covered_check_count} covered, {missing_check_count} missing`",
        "",
        status_line,
    ]
    for item in request.step_results:
        role = item["role"]
        output = item["output"]
        heading = {
            "builder": "Builder",
            "inspector": "Inspector",
            "gatekeeper": "GateKeeper",
            "guide": "Guide",
            "custom": "Restricted Custom Role",
        }.get(role["archetype"], role["name"])
        lines.extend(
            [
                "",
                f"## {heading}",
                f"- Archetype: `{role['archetype']}`",
                f"- Summary: {summary_line_for_step(role['archetype'], output)}",
            ]
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "- Inspect `evidence/ledger.jsonl`, `contract/strategy_source.json`, `timeline/iterations.jsonl`, `timeline/events.jsonl`, and `iterations/` for full details.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def summary_line_for_step(archetype: str, output: dict) -> str:
    if archetype == "builder":
        return truncate_runner_summary_text(output.get("attempted") or output.get("summary"), 280) or "none"
    if archetype == "inspector":
        return truncate_runner_summary_text(output.get("tester_observations"), 280) or "none"
    if archetype == "gatekeeper":
        return truncate_runner_summary_text(output.get("decision_summary"), 280) or "none"
    if archetype == "custom":
        return truncate_runner_summary_text(output.get("summary") or output.get("handoff_note"), 280) or "none"
    return truncate_runner_summary_text(output.get("seed_question") or output.get("meta_note"), 280) or "none"


def truncate_runner_summary_text(value: object, max_length: int = 220) -> str:
    text = str(value or "").strip()
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 1].rstrip()}..."


def _score_value(value: object) -> float | None:
    return structured_score_value(value)

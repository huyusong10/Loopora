from __future__ import annotations

from pathlib import Path


def test_generator_prompt_uses_bootstrap_guidance_for_spec_only_workspace(
    service_factory,
    tmp_path: Path,
) -> None:
    service = service_factory()
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    (workdir / "spec.md").write_text("# Task\n\nBuild something useful.\n", encoding="utf-8")
    compiled_spec = _compiled_spec(goal="Build something useful.")

    prompt = service._generator_prompt(compiled_spec, workdir, 0, "default")
    assert "this iteration should bootstrap the first implementation" in prompt
    assert "Create the smallest runnable prototype from scratch" not in prompt
    assert "Never wipe the whole workdir" in prompt
    assert "safe to add the first app files now" in prompt
    assert "This role must end with a concrete attempt" in prompt
    assert "prefer using it to establish evidence in this iteration" in prompt

    (workdir / "index.html").write_text("<!doctype html><title>Prototype</title>", encoding="utf-8")
    prompt_with_app = service._generator_prompt(compiled_spec, workdir, 0, "default")
    assert "this iteration should bootstrap the first implementation" not in prompt_with_app
    assert "This role must end with a concrete attempt" in prompt_with_app


def test_generator_prompt_includes_previous_iteration_feedback(service_factory, tmp_path: Path) -> None:
    service = service_factory()
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    prompt = service._generator_prompt(
        _compiled_spec(),
        workdir,
        1,
        "default",
        previous_generator_result={"attempted": "Updated the main flow copy.", "summary": "Focused on the hero section."},
        previous_tester_result={
            "failed_items": [{"id": "check_001", "title": "Main flow works", "source": "specified"}],
            "tester_observations": "The CTA still does not start the workflow.",
        },
        previous_verifier_result={
            "decision_summary": "The primary flow still stalls before completion.",
            "composite_score": 0.61,
            "failed_check_titles": ["Main flow works"],
            "next_actions": ["Make the CTA complete the core workflow."],
        },
        previous_challenger_result={
            "analysis": {"recommended_shift": "Try a smaller but end-to-end interaction fix."},
            "seed_question": "What is the smallest end-to-end fix that removes the stall?",
        },
    )

    assert "Previous iteration evidence:" in prompt
    assert "The CTA still does not start the workflow." in prompt
    assert "The primary flow still stalls before completion." in prompt
    assert "Try a smaller but end-to-end interaction fix." in prompt
    assert "Do not restart from scratch." in prompt


def test_challenger_prompt_uses_evidence_buckets_for_repair_direction(service_factory) -> None:
    service = service_factory()

    prompt = service._challenger_prompt(
        _compiled_spec(),
        {"stagnation_mode": "plateau", "recent_composites": [0.62, 0.63]},
        2,
    )

    assert "Proven, Weak, Unproven, Blocking, and Residual risk" in prompt
    assert "Turn Blocking or Unproven gaps into the next smallest proof or fix" in prompt
    assert "keep Residual risk visible" in prompt


def test_legacy_runtime_prompts_treat_run_contract_as_frozen(service_factory, tmp_path: Path) -> None:
    service = service_factory()
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    compiled_spec = _compiled_spec()
    prompts = [
        service._check_planner_prompt(compiled_spec),
        service._generator_prompt(compiled_spec, workdir, 0, "default"),
        service._tester_prompt(compiled_spec, 0, "default"),
        service._verifier_prompt(compiled_spec, _tester_output(), 0, "default"),
        service._challenger_prompt(compiled_spec, {"stagnation_mode": "plateau"}, 1),
    ]

    for prompt in prompts:
        _assert_prompt_treats_run_contract_as_frozen(prompt)


def _compiled_spec(**overrides: str) -> dict:
    values = {
        "goal": "Improve the primary flow.",
        "title": "Main flow works",
        "details": "The main flow is usable.",
        "when": "When the user follows the main path.",
        "expect": "The main path succeeds.",
        "fail_if": "The path breaks.",
        "constraints": "- Keep changes focused.",
    }
    values.update(overrides)
    return {
        "goal": values["goal"],
        "checks": [
            {
                "id": "check_001",
                "title": values["title"],
                "details": values["details"],
                "when": values["when"],
                "expect": values["expect"],
                "fail_if": values["fail_if"],
            }
        ],
        "constraints": values["constraints"],
    }


def _tester_output() -> dict:
    return {
        "execution_summary": "The flow still breaks.",
        "check_results": [],
        "dynamic_checks": [],
        "tester_observations": "No passing proof.",
    }


def _assert_prompt_treats_run_contract_as_frozen(prompt: str) -> None:
    assert "Treat the run contract as frozen" in prompt
    assert (
        "do not reinterpret or lower the Task, Done When, checks, guardrails, bundle collaboration summary, Loopora fit, workflow intent, role posture, "
        "Success Surface, Fake Done, Evidence Preferences, Execution Strategy, Judgment Tradeoffs, Local Governance, or Residual Risk"
    ) in prompt
    assert "evidence gap, blocker, or Loop-adjustment recommendation" in prompt
    assert "project-local instructions, design docs, and tests" in prompt

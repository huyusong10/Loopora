from __future__ import annotations

from pathlib import Path

from loopora.context_flow import (
    output_contract_prompt,
    render_iteration_section,
    system_prompt_prefix,
)

from runner_helpers import (
    _assert_prompt_assets_contract_frozen,
    _assert_prompt_bucket_rules,
    _assert_prompt_evidence_fallback_rules,
    _assert_prompt_parallel_review_rules,
    _assert_runtime_contract_frozen_prefixes,
    _runtime_prompt_assets,
)


def test_builtin_prompts_define_runtime_evidence_fallback_rules() -> None:
    prompts, zh_prompts = _runtime_prompt_assets()

    _assert_prompt_evidence_fallback_rules(prompts, zh_prompts)
    _assert_prompt_parallel_review_rules(prompts, zh_prompts)
    _assert_prompt_bucket_rules(prompts, zh_prompts)
    assert "run status is not a task pass" in prompts["gatekeeper"]
    assert "run 正常结束不等于任务通过" in zh_prompts["gatekeeper"]
    assert "用稳定证据桶组织 Loop 裁决" in zh_prompts["gatekeeper"]
    assert "用稳定证据桶组织任务裁决" not in zh_prompts["gatekeeper"]
    assert "downstream review steps run in a parallel_group" in system_prompt_prefix("builder")
    assert "this step is in a parallel_group" in system_prompt_prefix("inspector")
    assert "upstream reviewers ran in a parallel_group" in system_prompt_prefix("gatekeeper")
    assert "custom specialization" in system_prompt_prefix("custom")
    assert "run status separate from task verdict" in system_prompt_prefix("gatekeeper")
    _assert_runtime_contract_frozen_prefixes()
    assert "Proven, Weak, Unproven, Blocking, and Residual risk" in output_contract_prompt("inspector")
    assert "run status from task verdict" in output_contract_prompt("gatekeeper")
    assert "Blocking or Unproven gaps into the smallest repair direction" in output_contract_prompt("guide")


def test_control_runtime_frame_renders_trigger_evidence_refs() -> None:
    prompt_frame = render_iteration_section(
        {
            "iteration": {
                "iter_index": 1,
                "is_first_iteration": False,
                "previous_composite": 0.42,
                "stagnation_mode": "none",
                "evidence_progress_mode": "stalled",
                "covered_check_count": 1,
                "missing_check_count": 2,
                "consecutive_no_required_coverage_delta": 3,
            },
            "current_step": {
                "step_id": "control__guide",
                "step_order": 5,
                "role_name": "Guide",
                "archetype": "guide",
                "model": "",
                "executor_kind": "codex",
                "executor_mode": "preset",
                "parallel_group": "",
                "inputs": {"evidence_query": {"limit": 40}},
                "action_policy": {"workspace": "read_only"},
                "control": {
                    "signal": "gatekeeper_rejected",
                    "mode": "repair_guidance",
                    "reason": "GateKeeper rejected cited evidence.",
                    "trigger_evidence_refs": ["ev_000_01_inspector_step"],
                },
            },
        }
    )

    assert "- Control trigger: gatekeeper_rejected" in prompt_frame
    assert "- Control mode: repair_guidance" in prompt_frame
    assert '- Control evidence refs: ["ev_000_01_inspector_step"]' in prompt_frame


def test_builtin_prompt_assets_treat_run_contract_as_frozen() -> None:
    prompts_dir = Path(__file__).resolve().parents[3] / "src" / "loopora" / "assets" / "prompts"
    prompts = [
        (prompts_dir / "builder.md").read_text(encoding="utf-8"),
        (prompts_dir / "inspector.md").read_text(encoding="utf-8"),
        (prompts_dir / "custom.md").read_text(encoding="utf-8"),
        (prompts_dir / "guide.md").read_text(encoding="utf-8"),
        (prompts_dir / "gatekeeper.md").read_text(encoding="utf-8"),
        (prompts_dir / "gatekeeper-benchmark.md").read_text(encoding="utf-8"),
    ]
    zh_prompts = [
        (prompts_dir / "builder.zh.md").read_text(encoding="utf-8"),
        (prompts_dir / "inspector.zh.md").read_text(encoding="utf-8"),
        (prompts_dir / "custom.zh.md").read_text(encoding="utf-8"),
        (prompts_dir / "guide.zh.md").read_text(encoding="utf-8"),
        (prompts_dir / "gatekeeper.zh.md").read_text(encoding="utf-8"),
        (prompts_dir / "gatekeeper-benchmark.zh.md").read_text(encoding="utf-8"),
    ]

    _assert_prompt_assets_contract_frozen(prompts, zh_prompts)

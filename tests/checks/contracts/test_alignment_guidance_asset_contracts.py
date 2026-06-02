from __future__ import annotations

from pathlib import Path

from compacted_contract_support import assert_contains_all
from loopora.alignment_guidance import alignment_guidance_dir, load_alignment_guidance_assets


def test_alignment_guidance_assets_are_internal_compiler_material() -> None:
    source_dir = alignment_guidance_dir()
    assert source_dir.exists()
    assert not (Path(__file__).resolve().parents[3] / "skills" / "loopora-task-alignment").exists()

    assets = load_alignment_guidance_assets()
    assert assets.source_dir == source_dir
    assert_contains_all(
        assets.system_prompt_template,
        (
            "You are Loopora's built-in Web Loop alignment agent",
            "Important output discipline",
            "{{bundle_path}}",
            "{{stage_policy}}",
            "{{session_transcript_json}}",
        ),
    )
    assert_contains_all(
        assets.compiler_gates,
        (
            "Current compiler gate: clarifying",
            "Current compiler gate: confirmed agreement",
            "Before asking the user, answer anything you can from the transcript",
        ),
    )
    assert_contains_all(
        assets.compiler_policy,
        (
            "internal compiler flow",
            "not an external Skill workflow",
            "The background Agent drives semantic conversation",
            "Loopora backend owns phase acceptance",
            "Repairable issues may be fixed by the Agent",
            "Human-required issues must go back to conversation",
            "branch-aware pressure testing",
            "answer everything you can from the transcript",
            "Follow the user's chosen or corrected branch",
            "status-only checkpoints",
            "Agent as conversation driver",
            "Backend as compiler guard",
        ),
    )


def test_alignment_guidance_preserves_product_and_bundle_contracts() -> None:
    assets = load_alignment_guidance_assets()
    assert_contains_all(
        assets.product_primer,
        (
            "local-first platform for composing human-shaped governance loops",
            "human-in-the-loop -> human-shaped loop",
            "feedforward governance for slow-feedback work",
            "Control points are not control capability by themselves",
            "compile the user's task judgment into a runnable Loop candidate",
        ),
    )
    assert_contains_all(
        assets.alignment_playbook,
        (
            "Loopora fit gate",
            "Branch-aware pressure test",
            "Make control points decision-capable",
            "A status-only checkpoint is process theater",
            "confirm the working agreement, review the READY Loop",
            "agreement-to-bundle traceability checklist",
            "long-chain phase workflow",
            "Do not use arbitrary DAG language",
        ),
    )
    assert "confirm Loop" not in assets.alignment_playbook
    assert_contains_all(
        assets.bundle_contract,
        (
            "raw YAML document",
            "version: 1",
            "GateKeeper",
            "Proven, Weak, Unproven, Blocking, or Residual risk",
            "what they measure, what decision they trigger, and how they change later execution",
            "Default Web compiler bundles",
            "Do not emit nested Loops, arbitrary branch syntax",
        ),
    )
    assert "A control point that cannot change later execution is also role theater" in assets.system_prompt_template
    assert_contains_all(
        assets.quality_rubric,
        (
            "final feedback is too slow",
            "intermediate control points must measure a task-specific risk",
            "status-only milestones, reviews, or checkpoints",
        ),
    )

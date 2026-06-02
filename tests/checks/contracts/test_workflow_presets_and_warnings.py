from __future__ import annotations

from loopora.workflows import build_preset_workflow, normalize_workflow, preset_names, workflow_warnings


def test_workflow_warnings_cover_stale_and_prechange_gatekeeper_paths() -> None:
    benchmark_loop = build_preset_workflow("benchmark_loop")
    fast_lane = build_preset_workflow("fast_lane")

    assert workflow_warnings(benchmark_loop) == [
        "GateKeeper appears before a later Builder step, so it may only judge pre-change evidence."
    ]
    assert workflow_warnings(fast_lane) == [
        "GateKeeper appears after Builder without a later Inspector step, so it may judge stale evidence."
    ]


def test_workflow_warnings_surface_guide_steps_without_upstream_inputs() -> None:
    workflow = normalize_workflow(
        {
            "version": 1,
            "roles": [
                {"id": "inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
                {"id": "guide", "archetype": "guide", "prompt_ref": "guide.md"},
                {"id": "gatekeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
            ],
            "steps": [
                {"id": "inspection_step", "role_id": "inspector"},
                {"id": "guide_step", "role_id": "guide"},
                {
                    "id": "gatekeeper_step",
                    "role_id": "gatekeeper",
                    "on_pass": "finish_run",
                    "inputs": {
                        "handoffs_from": ["inspection_step", "guide_step"],
                        "evidence_query": {"archetypes": ["inspector", "guide"], "limit": 20},
                    },
                },
            ],
        }
    )

    assert workflow["warnings"] == [
        "Guide step guide_step has incomplete upstream inputs, so it may rely on ambient context."
    ]


def test_workflow_warnings_accept_guide_steps_with_upstream_handoff_and_evidence_inputs() -> None:
    workflow = normalize_workflow(
        {
            "version": 1,
            "roles": [
                {"id": "inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
                {"id": "guide", "archetype": "guide", "prompt_ref": "guide.md"},
                {"id": "gatekeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
            ],
            "steps": [
                {"id": "inspection_step", "role_id": "inspector"},
                {
                    "id": "guide_step",
                    "role_id": "guide",
                    "inputs": {
                        "handoffs_from": ["inspection_step"],
                        "evidence_query": {"archetypes": ["inspector"], "limit": 12},
                    },
                },
                {
                    "id": "gatekeeper_step",
                    "role_id": "gatekeeper",
                    "on_pass": "finish_run",
                    "inputs": {
                        "handoffs_from": ["inspection_step", "guide_step"],
                        "evidence_query": {"archetypes": ["inspector", "guide"], "limit": 20},
                    },
                },
            ],
        }
    )

    assert workflow["warnings"] == []


def test_visible_workflow_presets_are_curated_governance_shapes() -> None:
    assert preset_names() == [
        "evidence_first",
        "benchmark_gate",
        "quality_gate",
    ]

    default_workflow = normalize_workflow(None)
    assert default_workflow["preset"] == "quality_gate"
    assert [step["role_id"] for step in default_workflow["steps"]] == ["builder", "inspector", "gatekeeper"]
    assert all(not step.get("parallel_group") for step in default_workflow["steps"])
    assert default_workflow["steps"][-1]["on_pass"] == "finish_run"


def test_builtin_guide_steps_read_upstream_handoffs_and_evidence() -> None:
    for preset in ("build_first", "inspect_first", "triage_first", "repair_loop"):
        workflow = build_preset_workflow(preset)
        guide_steps = [
            step
            for step in workflow["steps"]
            if next(role for role in workflow["roles"] if role["id"] == step["role_id"])["archetype"] == "guide"
        ]

        assert guide_steps, preset
        for step in guide_steps:
            inputs = step["inputs"]
            assert inputs["handoffs_from"], preset
            assert inputs["evidence_query"]["archetypes"], preset
            assert inputs["iteration_memory"] == "summary_only"


def test_builtin_builder_steps_after_guide_keep_previous_gatekeeper_summary_visible() -> None:
    for preset in ("triage_first", "repair_loop"):
        workflow = build_preset_workflow(preset)
        role_archetypes = {role["id"]: role["archetype"] for role in workflow["roles"]}
        guide_seen = False
        builder_after_guide_inputs = []
        for step in workflow["steps"]:
            archetype = role_archetypes[step["role_id"]]
            if archetype == "guide":
                guide_seen = True
                continue
            if archetype == "builder" and guide_seen:
                builder_after_guide_inputs.append(step["inputs"])
                guide_seen = False

        assert builder_after_guide_inputs, preset
        for inputs in builder_after_guide_inputs:
            assert inputs["handoffs_from"], preset
            assert inputs["iteration_memory"] == "summary_only"

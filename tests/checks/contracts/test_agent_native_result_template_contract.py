from __future__ import annotations

from loopora.agent_native_result_template import agent_native_step_view_result_template


def test_agent_native_result_template_uses_schema_shaped_null_scaffold() -> None:
    template = agent_native_step_view_result_template(
        {
            "adapter": "codex",
            "run_id": "run-scaffold",
            "step_id": "builder_step",
            "role_dispatch": {
                "target_agent": "loopora-builder",
                "native_trace_contract": {
                    "optional": True,
                    "field": "native_trace",
                    "trace_ref_field": "native_trace_ref",
                },
            },
            "native_todo": {
                "recommended": True,
                "not_evidence": True,
                "items": ["Dispatch loopora-builder through the native task tool."],
            },
            "output_schema": {
                "type": "object",
                "required": ["summary", "checks", "nested"],
                "properties": {
                    "summary": {"type": "string"},
                    "checks": {"type": "array", "items": {"type": "string"}},
                    "nested": {
                        "type": "object",
                        "required": ["status"],
                        "properties": {
                            "status": {"type": "string", "enum": ["covered", "weak"]},
                            "notes": {"type": "array", "items": {"type": "string"}},
                        },
                        "additionalProperties": False,
                    },
                    "optional_flag": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            "submit_hint": {
                "command": (
                    "loopora agent codex submit --run-id run-scaffold --step-id builder_step "
                    "--result-file /tmp/builder.result.json --json --compact-json"
                ),
                "result_file_absolute_path": "/tmp/builder.result.json",
                "result_template_absolute_path": "/tmp/builder.result.template.json",
            },
            "judgment_contract": {
                "coverage_targets": [
                    {
                        "id": "done_when.check_001",
                        "kind": "done_when",
                        "text": "The primary user flow works end to end.",
                        "required": True,
                    },
                    {
                        "id": "success_surface.surface_001",
                        "kind": "success_surface",
                        "label": "Success surface 1",
                        "required": False,
                    },
                ]
            },
        }
    )

    contract = template["loopora_result_contract"]
    dispatch = template["loopora_host_dispatch"]
    assert (contract["result_is_schema_shaped_scaffold"], contract["replace_null_placeholders_before_submit"]) == (True, True)
    assert contract["coverage_target_ids"] == [
        "done_when.check_001",
        "success_surface.surface_001",
    ]
    assert contract["coverage_targets"] == [
        {
            "id": "done_when.check_001",
            "kind": "done_when",
            "required": True,
            "text": "The primary user flow works end to end.",
        },
        {
            "id": "success_surface.surface_001",
            "kind": "success_surface",
            "required": False,
            "text": "Success surface 1",
        },
    ]
    assert (
        contract["result_file_to_write"],
        contract["result_template_path"],
    ) == ("/tmp/builder.result.json", "/tmp/builder.result.template.json")
    assert contract["submit_command"].endswith("--json --compact-json")
    assert (contract["native_todo"]["not_evidence"], contract["native_trace_contract"]["field"]) == (True, "native_trace")
    assert (dispatch["native_trace"]["available"], dispatch["native_tool_name"], dispatch["native_trace_ref"]) == (False, "", "")
    assert template["result"] == {
        "summary": None,
        "checks": [None],
        "nested": {"status": None, "notes": [None]},
        "optional_flag": None,
    }


def test_agent_native_result_template_reuses_step_view_coverage_projection() -> None:
    template = agent_native_step_view_result_template(
        {
            "adapter": "codex",
            "run_id": "run-scaffold",
            "step_id": "gatekeeper_step",
            "role_dispatch": {"target_agent": "loopora-gatekeeper"},
            "coverage_target_ids": ["done_when.check_001"],
            "coverage_targets": [
                {
                    "id": "done_when.check_001",
                    "kind": "done_when",
                    "required": True,
                    "text": "The primary user flow works end to end.",
                }
            ],
            "judgment_contract": {"coverage_targets": []},
            "output_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        }
    )

    assert template["loopora_result_contract"]["coverage_target_ids"] == ["done_when.check_001"]
    assert template["loopora_result_contract"]["coverage_targets"] == [
        {
            "id": "done_when.check_001",
            "kind": "done_when",
            "required": True,
            "text": "The primary user flow works end to end.",
        }
    ]


def test_agent_native_result_template_projects_active_iteration_repair_focus() -> None:
    template = agent_native_step_view_result_template(
        {
            "adapter": "codex",
            "run_id": "run-repair",
            "step_id": "builder_step",
            "role_dispatch": {"target_agent": "loopora-builder"},
            "iteration_repair": {
                "active": True,
                "source_step_id": "gatekeeper_step",
                "source_role": "GateKeeper",
                "status": "blocked",
                "summary": "GateKeeper rejected the pass attempt.",
                "blocking_items": ["gatekeeper_pass_refs_not_supporting_evidence: cite supporting upstream proof."],
                "recommended_next_action": "Produce direct project-owned proof before asking GateKeeper to pass again.",
                "evidence_refs": ["ev_000_03_gatekeeper_step"],
                "top_gaps": [
                    {
                        "target_id": "gatekeeper.finish",
                        "status": "blocked",
                        "text": "GateKeeper needs supporting evidence.",
                    }
                ],
            },
            "output_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        }
    )

    repair = template["loopora_result_contract"]["iteration_repair"]
    assert repair["source_step_id"] == "gatekeeper_step"
    assert repair["blocking_items"][0].startswith("gatekeeper_pass_refs_not_supporting_evidence:")
    assert repair["recommended_next_action"].startswith("Produce direct project-owned proof")
    assert repair["top_gaps"][0]["target_id"] == "gatekeeper.finish"
    assert "prompt" not in template["loopora_result_contract"]

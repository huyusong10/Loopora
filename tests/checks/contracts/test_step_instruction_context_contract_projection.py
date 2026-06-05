from __future__ import annotations

from pathlib import Path

from loopora.context_flow import STEP_INSTRUCTION_CONTEXT_SCHEMA

from step_instruction_context_test_support import build_step_context


def test_step_instruction_context_preserves_judgment_contract_fields(tmp_path: Path) -> None:
    step_context = build_step_context(tmp_path, run_contract=_judgment_run_contract())

    assert step_context["contract"]["collaboration_summary"] == "Prefer evidence before closure."
    assert step_context["contract"]["loop_fit_reasons"] == ["Future iterations keep the proof target visible."]
    assert step_context["contract"]["judgment_tradeoffs"] == ["Evidence before polish."]
    assert step_context["contract"]["execution_strategy"] == [
        "Prove the smallest path first, then expand only after evidence is strong."
    ]
    assert step_context["contract"]["local_governance"] == [
        "GateKeeper treats skipped AGENTS.md responsibilities as Blocking."
    ]
    assert step_context["contract"]["role_postures"] == [
        {
            "role_id": "gatekeeper",
            "role_name": "GateKeeper",
            "archetype": "gatekeeper",
            "posture_notes": "Fail closed when evidence is weak.",
        }
    ]


def test_step_instruction_context_exposes_coverage_targets_without_template_lookup(tmp_path: Path) -> None:
    step_context = build_step_context(
        tmp_path,
        run_contract={
            **_judgment_run_contract(),
            "compiled_spec": {
                "coverage_targets": [
                    {
                        "id": "done_when.check_001",
                        "kind": "done_when",
                        "required": True,
                        "text": "The primary proof passes.",
                    },
                    {
                        "target_id": "gatekeeper.finish",
                        "kind": "gatekeeper",
                        "required": True,
                        "text": "GateKeeper closes only with upstream proof.",
                    },
                ]
            },
        },
    )

    assert step_context["coverage_target_ids"] == ["done_when.check_001", "gatekeeper.finish"]
    assert step_context["coverage_targets"] == step_context["contract"]["coverage_targets"]
    assert step_context["coverage_targets"][0]["text"] == "The primary proof passes."


def test_step_instruction_context_exposes_workspace_baseline_artifact(tmp_path: Path) -> None:
    step_context = build_step_context(
        tmp_path,
        run_contract={
            **_judgment_run_contract(),
            "workspace_baseline": {
                "file_count": 3,
                "artifact": {
                    "kind": "workspace",
                    "label": "workspace-baseline",
                    "relative_path": "contract/workspace_baseline.json",
                    "workspace_path": ".loopora/runs/run_prompt/contract/workspace_baseline.json",
                    "absolute_path": str((tmp_path / "run_prompt" / "contract" / "workspace_baseline.json").resolve()),
                },
            },
        },
    )

    baseline = step_context["contract"]["workspace_baseline"]
    assert baseline["file_count"] == 3
    assert baseline["artifact"]["label"] == "workspace-baseline"
    assert baseline["artifact"]["relative_path"] == "contract/workspace_baseline.json"
    assert any(item["label"] == "workspace-baseline" for item in step_context["artifacts"])


def test_step_instruction_context_schema_requires_judgment_contract_fields() -> None:
    contract_schema = STEP_INSTRUCTION_CONTEXT_SCHEMA["properties"]["contract"]

    for key in ("loop_fit_reasons", "judgment_tradeoffs", "execution_strategy", "local_governance", "role_postures"):
        assert key in contract_schema["required"]
        assert contract_schema["properties"][key]["type"] == "array"
    assert "workspace_baseline" in contract_schema["required"]
    assert "coverage_target_ids" in STEP_INSTRUCTION_CONTEXT_SCHEMA["required"]
    assert "coverage_targets" in STEP_INSTRUCTION_CONTEXT_SCHEMA["required"]
    assert STEP_INSTRUCTION_CONTEXT_SCHEMA["properties"]["coverage_target_ids"]["items"]["type"] == "string"
    assert STEP_INSTRUCTION_CONTEXT_SCHEMA["properties"]["coverage_targets"]["items"]["type"] == "object"
    assert contract_schema["properties"]["workspace_baseline"]["properties"]["artifact"]["required"] == [
        "kind",
        "label",
        "relative_path",
        "workspace_path",
        "absolute_path",
    ]


def _judgment_run_contract() -> dict:
    return {
        "compiled_spec": {},
        "workflow": {"preset": "custom"},
        "completion_mode": "gatekeeper",
        "collaboration_summary": "Prefer evidence before closure.",
        "loop_fit_reasons": ["Future iterations keep the proof target visible."],
        "judgment_tradeoffs": ["Evidence before polish."],
        "execution_strategy": ["Prove the smallest path first, then expand only after evidence is strong."],
        "local_governance": ["GateKeeper treats skipped AGENTS.md responsibilities as Blocking."],
        "role_postures": [
            {
                "role_id": "gatekeeper",
                "role_name": "GateKeeper",
                "archetype": "gatekeeper",
                "posture_notes": "Fail closed when evidence is weak.",
            }
        ],
    }

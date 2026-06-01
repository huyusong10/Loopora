from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from bundle_lifecycle_test_support import _bundle_yaml
from loopora.bundles import bundle_to_yaml, load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service import LooporaError


def test_bundle_round_trip_preserves_parallel_groups_and_step_inputs(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    yaml_text = (
        _bundle_yaml(sample_workdir)
        .replace(
            '  - key: "gatekeeper"\n    name: "Conservative GateKeeper"',
            '  - key: "semantic-inspector"\n'
            '    name: "Semantic Inspector"\n'
            '    description: "Checks task posture and fake-done risk."\n'
            '    archetype: "inspector"\n'
            "    prompt_markdown: |\n"
            "      ---\n"
            "      version: 1\n"
            "      archetype: inspector\n"
            "      ---\n\n"
            "      Inspect semantic task fit and evidence gaps.\n"
            "    posture_notes: |\n"
            "      Prefer task-specific fake-done evidence over generic checklist confidence.\n"
            '  - key: "gatekeeper"\n'
            '    name: "Conservative GateKeeper"',
        )
        .replace(
            "  roles:\n"
            '    - id: "inspector"\n'
            '      role_definition_key: "inspector"\n'
            '    - id: "builder"\n'
            '      role_definition_key: "builder"\n'
            '    - id: "gatekeeper"\n'
            '      role_definition_key: "gatekeeper"\n'
            "  steps:\n"
            '    - id: "inspector_step"\n'
            '      role_id: "inspector"\n'
            '    - id: "builder_step"\n'
            '      role_id: "builder"\n'
            '    - id: "gatekeeper_step"\n'
            '      role_id: "gatekeeper"\n'
            '      on_pass: "finish_run"',
            "  roles:\n"
            '    - id: "builder"\n'
            '      role_definition_key: "builder"\n'
            '    - id: "inspector"\n'
            '      role_definition_key: "inspector"\n'
            '    - id: "semantic"\n'
            '      role_definition_key: "semantic-inspector"\n'
            '    - id: "gatekeeper"\n'
            '      role_definition_key: "gatekeeper"\n'
            "  steps:\n"
            '    - id: "builder_step"\n'
            '      role_id: "builder"\n'
            '    - id: "inspector_step"\n'
            '      role_id: "inspector"\n'
            '      parallel_group: "inspection_pack"\n'
            "      inputs:\n"
            '        handoffs_from: ["builder_step"]\n'
            "        evidence_query:\n"
            '          archetypes: ["builder"]\n'
            "          limit: 8\n"
            '    - id: "semantic_step"\n'
            '      role_id: "semantic"\n'
            '      parallel_group: "inspection_pack"\n'
            '    - id: "gatekeeper_step"\n'
            '      role_id: "gatekeeper"\n'
            '      on_pass: "finish_run"\n'
            "      inputs:\n"
            '        handoffs_from: ["inspector_step", "semantic_step"]',
        )
    )

    imported = service.import_bundle_text(yaml_text)
    exported = service.export_bundle(imported["id"])
    steps = exported["workflow"]["steps"]

    assert steps[1]["parallel_group"] == "inspection_pack"
    assert steps[1]["inputs"]["handoffs_from"] == ["builder_step"]
    assert steps[1]["inputs"]["evidence_query"] == {"archetypes": ["builder"], "limit": 8}
    assert steps[2]["parallel_group"] == "inspection_pack"
    assert steps[3]["inputs"] == {"handoffs_from": ["inspector_step", "semantic_step"]}


def test_bundle_round_trip_preserves_explicit_step_action_policy(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    yaml_text = _bundle_yaml(sample_workdir).replace(
        '    - id: "inspector_step"\n      role_id: "inspector"\n    - id: "builder_step"\n      role_id: "builder"\n',
        '    - id: "inspector_step"\n'
        '      role_id: "inspector"\n'
        "      action_policy:\n"
        '        workspace: "read_only"\n'
        "        can_block: false\n"
        "        can_finish_run: false\n"
        '    - id: "builder_step"\n'
        '      role_id: "builder"\n'
        "      action_policy:\n"
        '        workspace: "workspace_write"\n'
        "        can_block: false\n"
        "        can_finish_run: false\n",
    )

    imported = service.import_bundle_text(yaml_text)
    exported = service.export_bundle(imported["id"])
    policies = {step["id"]: step["action_policy"] for step in exported["workflow"]["steps"]}

    assert policies["inspector_step"] == {
        "workspace": "read_only",
        "can_block": False,
        "can_finish_run": False,
    }
    assert policies["builder_step"] == {
        "workspace": "workspace_write",
        "can_block": False,
        "can_finish_run": False,
    }


def test_bundle_round_trip_preserves_workflow_controls(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    yaml_text = _bundle_yaml(sample_workdir).replace(
        '      on_pass: "finish_run"\n',
        '      on_pass: "finish_run"\n'
        "  controls:\n"
        '    - id: "gatekeeper_rejection_review"\n'
        "      when:\n"
        '        signal: "gatekeeper_rejected"\n'
        '        after: "0s"\n'
        "      call:\n"
        '        role_id: "inspector"\n'
        '      mode: "advisory"\n'
        "      max_fires_per_run: 1\n",
    )

    imported = service.import_bundle_text(yaml_text)
    exported = service.export_bundle(imported["id"])

    assert exported["workflow"]["controls"] == [
        {
            "id": "gatekeeper_rejection_review",
            "when": {"signal": "gatekeeper_rejected", "after": "0s"},
            "call": {"role_id": "inspector"},
            "mode": "advisory",
            "max_fires_per_run": 1,
        }
    ]


def test_bundle_rejects_controls_that_call_builders(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    yaml_text = _bundle_yaml(sample_workdir).replace(
        '      on_pass: "finish_run"\n',
        '      on_pass: "finish_run"\n'
        "  controls:\n"
        '    - id: "implicit_repair"\n'
        "      when:\n"
        '        signal: "step_failed"\n'
        '        after: "0s"\n'
        "      call:\n"
        '        role_id: "builder"\n',
    )

    with pytest.raises(LooporaError, match="controls may only call Inspector, Guide, or GateKeeper"):
        service.preview_bundle_text(yaml_text)


def test_bundle_rejects_zero_workflow_control_max_fires(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    yaml_text = _bundle_yaml(sample_workdir).replace(
        '      on_pass: "finish_run"\n',
        '      on_pass: "finish_run"\n'
        "  controls:\n"
        '    - id: "disabled_review"\n'
        "      when:\n"
        '        signal: "gatekeeper_rejected"\n'
        '        after: "0s"\n'
        "      call:\n"
        '        role_id: "inspector"\n'
        '      mode: "advisory"\n'
        "      max_fires_per_run: 0\n",
    )

    with pytest.raises(LooporaError, match="control max_fires_per_run must be between 1 and 20"):
        service.preview_bundle_text(yaml_text)


def test_bundle_rejects_string_workflow_control_max_fires(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    yaml_text = _bundle_yaml(sample_workdir).replace(
        '      on_pass: "finish_run"\n',
        '      on_pass: "finish_run"\n'
        "  controls:\n"
        '    - id: "quoted_review"\n'
        "      when:\n"
        '        signal: "gatekeeper_rejected"\n'
        '        after: "0s"\n'
        "      call:\n"
        '        role_id: "inspector"\n'
        '      mode: "advisory"\n'
        '      max_fires_per_run: "2"\n',
    )

    with pytest.raises(LooporaError, match="control max_fires_per_run must be an integer"):
        service.preview_bundle_text(yaml_text)


def test_bundle_preview_projects_error_control_summary(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")

    yaml_text = _bundle_yaml(sample_workdir).replace(
        '      on_pass: "finish_run"\n',
        '      on_pass: "finish_run"\n'
        "  controls:\n"
        '    - id: "gatekeeper_rejection_review"\n'
        "      when:\n"
        '        signal: "gatekeeper_rejected"\n'
        '        after: "0s"\n'
        "      call:\n"
        '        role_id: "inspector"\n'
        '      mode: "advisory"\n',
    )
    preview = service.preview_bundle_text(yaml_text)

    summary = preview["control_summary"]
    traceability = summary["traceability"]
    assert summary["success_surface"]
    assert summary["fake_done_risks"]
    assert summary["evidence_preferences"]
    assert summary["risks"]
    assert summary["evidence"]
    assert summary["gatekeeper"]["enabled"] is True
    assert summary["gatekeeper"]["requires_evidence_refs"] is True
    assert summary["workflow"]["step_count"] == 3
    assert summary["controls"][0]["signal"] == "gatekeeper_rejected"
    assert summary["controls"][0]["role_name"] == "Evidence Inspector"
    assert preview["diagnostics"] == summary["diagnostics"]
    assert {item["code"] for item in summary["diagnostics"]} >= {
        "gatekeeper_missing_handoff_fan_in",
        "gatekeeper_missing_evidence_fan_in",
    }
    assert preview["traceability"] == traceability
    assert "loop_fit" in traceability["missing"]
    assert traceability["mapped_count"] == traceability["required_count"] - 1
    assert "spec.markdown#Fake Done" in traceability["surfaces"]
    assert "workflow.controls[]" in traceability["surfaces"]
    workflow_trace = next(item for item in traceability["items"] if item["key"] == "workflow_judgment")
    assert workflow_trace["label"] == "Run flow"
    assert workflow_trace["label"] != "Workflow judgment"


def test_bundle_control_summary_uses_loop_verdict_language_for_completion_diagnostics(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(
        _bundle_yaml(sample_workdir).replace('  completion_mode: "gatekeeper"', '  completion_mode: "rounds"')
    )

    summary = service._bundle_control_summary(bundle)
    diagnostic = next(item for item in summary["diagnostics"] if item["code"] == "completion_not_gatekeeper")

    assert "Loop 裁决" in diagnostic["message_zh"]
    assert "任务裁决" not in diagnostic["message_zh"]


def test_bundle_control_summary_marks_gatekeeper_refs_not_applicable_when_disabled(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(
        dedent(
            f"""
            version: 1
            metadata:
              name: "Round Builder"
            collaboration_summary: |
              Use a short rounds loop where no GateKeeper finish step is configured.
            loop:
              name: "Round Builder"
              workdir: "{sample_workdir}"
              completion_mode: "rounds"
              executor_kind: "codex"
              executor_mode: "preset"
              model: "gpt-5.4"
              reasoning_effort: "medium"
              max_iters: 2
              max_role_retries: 1
              delta_threshold: 0.005
              trigger_window: 2
              regression_window: 2
            spec:
              markdown: |
                # Task

                Build one small, reviewable change.

                # Done When

                - The primary path has a reproducible check.

                # Guardrails

                - Keep changes narrow.

                # Success Surface

                - The change is visible in a focused artifact.

                # Fake Done

                - A self-report without command evidence is fake done.

                # Evidence Preferences

                - Prefer project command output.

                # Residual Risk

                Minor polish can remain as a tracked follow-up owned by product.
            role_definitions:
              - key: "builder"
                name: "Builder"
                archetype: "builder"
                prompt_markdown: |
                  ---
                  version: 1
                  archetype: builder
                  ---

                  Build the focused change.
            workflow:
              version: 1
              preset: "round_builder"
              collaboration_intent: "Run a bounded builder-only loop."
              roles:
                - id: "builder"
                  role_definition_key: "builder"
              steps:
                - id: "builder_step"
                  role_id: "builder"
            """
        ).strip()
        + "\n"
    )

    summary = service._bundle_control_summary(bundle)
    gatekeeper = summary["gatekeeper"]
    closure_trace = next(item for item in summary["traceability"]["items"] if item["key"] == "gatekeeper_closure")

    assert gatekeeper["enabled"] is False
    assert gatekeeper["requires_evidence_refs"] is False
    assert gatekeeper["roles"] == []
    assert gatekeeper["finish_steps"] == []
    assert closure_trace["mapped"] is False
    assert "gatekeeper_closure" in summary["traceability"]["missing"]


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ('  completion_mode: "unknown"', "unsupported completion mode: unknown"),
        ("  completion_mode: false", "unsupported completion mode: False"),
        ("  completion_mode: 1", "unsupported completion mode: 1"),
    ],
)
def test_bundle_preview_rejects_invalid_completion_mode(
    service_factory,
    sample_workdir: Path,
    replacement: str,
    message: str,
) -> None:
    service = service_factory(scenario="success")
    invalid_yaml = _bundle_yaml(sample_workdir).replace('  completion_mode: "gatekeeper"', replacement, 1)

    with pytest.raises(LooporaError, match=message):
        service.preview_bundle_text(invalid_yaml)


def test_bundle_loader_normalizes_supported_completion_mode(sample_workdir: Path) -> None:
    bundle = load_bundle_text(
        _bundle_yaml(sample_workdir).replace('  completion_mode: "gatekeeper"', '  completion_mode: " RoundS "', 1)
    )

    assert bundle["loop"]["completion_mode"] == "rounds"


@pytest.mark.parametrize(
    ("yaml_edit", "message"),
    [
        (
            lambda text: text.replace('  executor_kind: "codex"', '  executor_kind: "unknown"', 1),
            "unsupported executor kind",
        ),
        (
            lambda text: text.replace('  executor_mode: "preset"', '  executor_mode: "unknown"', 1),
            "unsupported executor mode",
        ),
        (
            lambda text: text.replace('  executor_kind: "codex"', '  executor_kind: "custom"', 1),
            "Custom Command only supports command mode",
        ),
        (
            lambda text: text.replace('  executor_mode: "preset"', '  executor_mode: "command"', 1),
            "custom command arguments are required in command mode",
        ),
    ],
)
def test_bundle_preview_rejects_invalid_loop_executor_settings(
    service_factory,
    sample_workdir: Path,
    yaml_edit,
    message: str,
) -> None:
    service = service_factory(scenario="success")

    with pytest.raises(LooporaError, match=message):
        service.preview_bundle_text(yaml_edit(_bundle_yaml(sample_workdir)))


def test_bundle_loader_normalizes_loop_executor_aliases(sample_workdir: Path) -> None:
    bundle = load_bundle_text(
        _bundle_yaml(sample_workdir)
        .replace('  executor_kind: "codex"', '  executor_kind: "claude-code"', 1)
        .replace('  executor_mode: "preset"', '  executor_mode: " PRESET "', 1)
        .replace('  model: "gpt-5.4"', '  model: ""', 1)
        .replace('  reasoning_effort: "medium"', '  reasoning_effort: "xhigh"', 1)
    )

    assert bundle["loop"]["executor_kind"] == "claude"
    assert bundle["loop"]["executor_mode"] == "preset"
    assert bundle["loop"]["command_cli"] == ""
    assert bundle["loop"]["command_args_text"] == ""
    assert bundle["loop"]["model"] == ""
    assert bundle["loop"]["reasoning_effort"] == "max"


def test_bundle_roles_inherit_loop_executor_when_role_fields_are_omitted(sample_workdir: Path) -> None:
    bundle = load_bundle_text(
        _bundle_yaml(sample_workdir)
        .replace('  executor_kind: "codex"', '  executor_kind: "claude-code"', 1)
        .replace('  model: "gpt-5.4"', '  model: ""', 1)
        .replace('  reasoning_effort: "medium"', '  reasoning_effort: "xhigh"', 1)
    )

    assert {role["executor_kind"] for role in bundle["role_definitions"]} == {"claude"}
    assert {role["executor_mode"] for role in bundle["role_definitions"]} == {"preset"}
    assert {role["model"] for role in bundle["role_definitions"]} == {""}
    assert {role["reasoning_effort"] for role in bundle["role_definitions"]} == {"max"}


def test_bundle_roles_inherit_loop_command_executor_when_role_fields_are_omitted(sample_workdir: Path) -> None:
    bundle = load_bundle_text(
        _bundle_yaml(sample_workdir)
        .replace('  executor_kind: "codex"', '  executor_kind: "custom"', 1)
        .replace(
            '  executor_mode: "preset"',
            '  executor_mode: "command"\n'
            '  command_cli: "my-agent"\n'
            "  command_args_text: |\n"
            "    {prompt}\n"
            "    --output\n"
            "    {output_path}",
            1,
        )
        .replace('  model: "gpt-5.4"', '  model: ""', 1)
        .replace('  reasoning_effort: "medium"', '  reasoning_effort: ""', 1)
    )

    assert {role["executor_kind"] for role in bundle["role_definitions"]} == {"custom"}
    assert {role["executor_mode"] for role in bundle["role_definitions"]} == {"command"}
    assert {role["command_cli"] for role in bundle["role_definitions"]} == {"my-agent"}
    assert {role["command_args_text"] for role in bundle["role_definitions"]} == {
        "{prompt}\n--output\n{output_path}\n"
    }


def test_bundle_preview_warns_about_legacy_guide_and_weak_builder_handoff(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    yaml_text = (
        _bundle_yaml(sample_workdir)
        .replace(
            '  - key: "gatekeeper"\n',
            '  - key: "guide"\n'
            '    name: "Repair Guide"\n'
            '    description: "Narrows the next move from upstream evidence."\n'
            '    archetype: "guide"\n'
            "    prompt_markdown: |\n"
            "      ---\n"
            "      version: 1\n"
            "      archetype: guide\n"
            "      ---\n\n"
            "      Guide the next repair slice.\n"
            "    posture_notes: |\n"
            "      Turn weak or unproven evidence into a smaller repair direction.\n"
            '  - key: "gatekeeper"\n',
        )
        .replace(
            '    - id: "builder"\n      role_definition_key: "builder"\n',
            '    - id: "guide"\n      role_definition_key: "guide"\n    - id: "builder"\n      role_definition_key: "builder"\n',
        )
        .replace(
            '    - id: "builder_step"\n      role_id: "builder"\n',
            '    - id: "guide_step"\n      role_id: "guide"\n    - id: "builder_step"\n      role_id: "builder"\n',
        )
    )

    preview = service.preview_bundle_text(yaml_text)

    codes = {item["code"] for item in preview["diagnostics"]}
    assert "guide_missing_upstream_handoff" in codes
    assert "guide_missing_upstream_evidence" in codes
    assert "builder_missing_guide_handoff" in codes


def test_bundle_preview_warns_when_gatekeeper_drops_parallel_review_fan_in(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["contract_inspection_step"]["parallel_group"] = "inspection_pack"
    steps_by_id["evidence_inspection_step"]["parallel_group"] = "inspection_pack"
    gatekeeper_inputs = steps_by_id["gatekeeper_step"]["inputs"]
    gatekeeper_inputs["handoffs_from"] = ["evidence_inspection_step"]
    gatekeeper_inputs["evidence_query"]["archetypes"] = ["builder"]

    preview = service.preview_bundle_text(bundle_to_yaml(bundle))

    diagnostics_by_code = {item["code"]: item for item in preview["diagnostics"]}
    assert diagnostics_by_code["gatekeeper_missing_parallel_review_handoff"]["details"]["missing_handoffs"] == [
        "contract_inspection_step"
    ]
    assert diagnostics_by_code["gatekeeper_missing_parallel_review_evidence"]["details"]["missing_archetypes"] == ["inspector"]


def test_bundle_control_summary_does_not_hide_invalid_fire_limit_projection(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    yaml_text = _bundle_yaml(sample_workdir).replace(
        '      on_pass: "finish_run"\n',
        '      on_pass: "finish_run"\n'
        "  controls:\n"
        '    - id: "gatekeeper_rejection_review"\n'
        "      when:\n"
        '        signal: "gatekeeper_rejected"\n'
        '        after: "0s"\n'
        "      call:\n"
        '        role_id: "inspector"\n'
        '      mode: "advisory"\n',
    )
    bundle = service.preview_bundle_text(yaml_text)["bundle"]
    bundle["workflow"]["controls"][0]["max_fires_per_run"] = 0

    assert service._bundle_control_summary(bundle)["controls"][0]["max_fires_per_run"] == 0

    bundle["workflow"]["controls"][0]["max_fires_per_run"] = "not-a-number"
    assert service._bundle_control_summary(bundle)["controls"][0]["max_fires_per_run"] == "not-a-number"

    bundle["workflow"]["controls"][0]["max_fires_per_run"] = "2"
    assert service._bundle_control_summary(bundle)["controls"][0]["max_fires_per_run"] == "2"

    bundle["workflow"]["controls"][0]["max_fires_per_run"] = "+2"
    assert service._bundle_control_summary(bundle)["controls"][0]["max_fires_per_run"] == "+2"

    bundle["workflow"]["controls"][0]["max_fires_per_run"] = True
    assert service._bundle_control_summary(bundle)["controls"][0]["max_fires_per_run"] == "true"

    bundle["workflow"]["controls"][0]["max_fires_per_run"] = 1.5
    assert service._bundle_control_summary(bundle)["controls"][0]["max_fires_per_run"] == "1.5"

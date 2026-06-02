from __future__ import annotations

from pathlib import Path

from bundle_lifecycle_test_support import _bundle_yaml


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

from __future__ import annotations

from loopora.specs import render_spec_template, render_spec_template_for_strategy_source


def test_render_spec_template_renders_unique_role_note_sections() -> None:
    template = render_spec_template(
        locale="en",
        workflow={
            "version": 1,
            "roles": [
                {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
                {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
            ],
            "steps": [
                {"id": "builder_step", "role_id": "builder"},
                {"id": "builder_retry", "role_id": "builder"},
                {"id": "gatekeeper_step", "role_id": "gatekeeper"},
            ],
        },
    )

    assert "# Task" in template
    assert "# Done When" in template
    assert "# Guardrails" in template
    assert "# Role Notes" in template
    assert template.count("## Builder Notes") == 1
    assert template.count("## GateKeeper Notes") == 1


def test_render_spec_template_accepts_strategy_source_boundary_name() -> None:
    template = render_spec_template_for_strategy_source(
        locale="en",
        strategy_source={
            "version": 1,
            "roles": [
                {"id": "builder", "name": "Focused Builder", "archetype": "builder", "prompt_ref": "builder.md"},
            ],
            "steps": [{"id": "builder_step", "role_id": "builder"}],
        },
    )

    assert "## Focused Builder Notes" in template

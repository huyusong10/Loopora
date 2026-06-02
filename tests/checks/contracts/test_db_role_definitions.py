from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository


def test_role_definition_crud_round_trips_through_repository(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")

    created = repository.create_role_definition(
        {
            "id": "role_release_builder",
            "name": "Release Builder",
            "description": "Ship release work.",
            "archetype": "builder",
            "prompt_ref": "release-builder.md",
            "prompt_markdown": "---\nversion: 1\narchetype: builder\n---\n\nFocus on release work.\n",
            "executor_kind": "claude",
            "executor_mode": "preset",
            "command_cli": "claude",
            "command_args_text": "",
            "model": "gpt-5.4-mini",
            "reasoning_effort": "high",
        }
    )

    assert created["name"] == "Release Builder"
    assert created["archetype"] == "builder"
    assert created["executor_kind"] == "claude"

    updated = repository.update_role_definition(
        created["id"],
        {
            "name": "Release Builder v2",
            "description": "Ship release work safely.",
            "archetype": "builder",
            "prompt_ref": "release-builder.md",
            "prompt_markdown": "---\nversion: 1\narchetype: builder\n---\n\nFocus on safe release work.\n",
            "executor_kind": "codex",
            "executor_mode": "command",
            "command_cli": "codex",
            "command_args_text": "exec\n{prompt}\n",
            "model": "gpt-5.4",
            "reasoning_effort": "",
        },
    )
    assert updated is not None
    assert updated["name"] == "Release Builder v2"
    assert updated["executor_mode"] == "command"

    listed = repository.list_role_definitions()
    assert len(listed) == 1
    assert listed[0]["model"] == "gpt-5.4"

    assert repository.delete_role_definition(created["id"]) is True
    assert repository.get_role_definition(created["id"]) is None

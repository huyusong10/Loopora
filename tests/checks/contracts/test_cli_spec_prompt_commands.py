from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from loopora import cli


def _result_error_text(result) -> str:
    try:
        return result.stderr
    except ValueError:
        return result.output


def test_cli_spec_init_accepts_locale_and_validate_reports_check_mode(tmp_path: Path) -> None:
    spec_path = tmp_path / "created-spec.md"
    runner = CliRunner()

    init_result = runner.invoke(cli.app, ["spec", "init", "--locale", "en", str(spec_path)])

    assert init_result.exit_code == 0, init_result.stdout
    created_text = spec_path.read_text(encoding="utf-8")
    assert "# Task" in created_text
    assert "# Done When" in created_text
    assert "# Guardrails" in created_text
    assert "# Role Notes" in created_text
    assert "delete `# Done When`" in created_text

    validate_result = runner.invoke(cli.app, ["spec", "validate", str(spec_path)])

    assert validate_result.exit_code == 0, validate_result.stdout
    payload = json.loads(validate_result.stdout)
    assert payload["ok"] is True
    assert payload["check_mode"] == "specified"

    invalid_spec_path = tmp_path / "invalid-spec.md"
    invalid_spec_path.write_bytes(b"\xff")
    invalid_result = runner.invoke(cli.app, ["spec", "validate", str(invalid_spec_path)])
    assert invalid_result.exit_code == 1
    assert "UTF-8 encoded Markdown" in _result_error_text(invalid_result)


def test_cli_spec_init_accepts_workflow_preset(tmp_path: Path) -> None:
    spec_path = tmp_path / "repair-loop-spec.md"
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        ["spec", "init", "--locale", "en", "--workflow-preset", "repair_loop", str(spec_path)],
    )

    assert result.exit_code == 0, result.stdout
    created_text = spec_path.read_text(encoding="utf-8")
    assert "## Builder Notes" in created_text
    assert "## Regression Inspector Notes" in created_text
    assert "## Contract Inspector Notes" in created_text
    assert "## Guide Notes" in created_text
    assert "## GateKeeper Notes" in created_text
    assert created_text.count("## Builder Notes") == 1


def test_cli_spec_template_read_and_write(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    spec_path = tmp_path / "spec.md"
    source_path = tmp_path / "source.md"
    source_path.write_text("# Task\n\nUpdated task.\n", encoding="utf-8")

    class FakeService:
        def get_orchestration(self, orchestration_id: str):
            assert orchestration_id == "builtin:repair_loop"
            return {"workflow_json": {"preset": "repair_loop"}}

    monkeypatch.setattr(cli, "create_service", FakeService)

    template_result = runner.invoke(
        cli.app,
        ["spec", "template", "--locale", "en", "--orchestration-id", "builtin:repair_loop", "--json"],
    )
    assert template_result.exit_code == 0, template_result.stdout
    template_payload = json.loads(template_result.stdout)
    assert "# Task" in template_payload["markdown"]
    assert any(item["heading"] == "Builder Notes" for item in template_payload["role_note_sections"])

    write_result = runner.invoke(cli.app, ["spec", "write", str(spec_path), "--from-file", str(source_path)])
    assert write_result.exit_code == 0, write_result.stdout
    write_payload = json.loads(write_result.stdout)
    assert write_payload["validation"]["ok"] is True

    read_result = runner.invoke(cli.app, ["spec", "read", str(spec_path)])
    assert read_result.exit_code == 0, read_result.stdout
    read_payload = json.loads(read_result.stdout)
    assert read_payload["content"] == "# Task\n\nUpdated task.\n"
    assert read_payload["validation"]["ok"] is True

    invalid_source_path = tmp_path / "invalid-source.md"
    invalid_source_path.write_bytes(b"\xff")
    invalid_read = runner.invoke(cli.app, ["spec", "read", str(invalid_source_path)])
    assert invalid_read.exit_code == 1
    assert "UTF-8 encoded Markdown" in _result_error_text(invalid_read)
    invalid_write = runner.invoke(cli.app, ["spec", "write", str(spec_path), "--from-file", str(invalid_source_path)])
    assert invalid_write.exit_code == 1
    assert "UTF-8 encoded Markdown" in _result_error_text(invalid_write)


def test_cli_prompts_list_template_and_validate(tmp_path: Path) -> None:
    runner = CliRunner()
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("---\nversion: 1\narchetype: builder\n---\nPrompt body.\n", encoding="utf-8")

    list_result = runner.invoke(cli.app, ["prompts", "list"])
    assert list_result.exit_code == 0, list_result.stdout
    assert any(item["prompt_ref"] == "builder.md" for item in json.loads(list_result.stdout))

    template_result = runner.invoke(cli.app, ["prompts", "template", "builder.md", "--locale", "en"])
    assert template_result.exit_code == 0, template_result.stdout
    assert "version: 1" in template_result.stdout

    validate_result = runner.invoke(cli.app, ["prompts", "validate", str(prompt_path), "--archetype", "builder"])
    assert validate_result.exit_code == 0, validate_result.stdout
    payload = json.loads(validate_result.stdout)
    assert payload["ok"] is True
    assert payload["metadata"]["archetype"] == "builder"

    invalid_prompt_path = tmp_path / "invalid-prompt.md"
    invalid_prompt_path.write_bytes(b"\xff")
    invalid_result = runner.invoke(cli.app, ["prompts", "validate", str(invalid_prompt_path)])
    assert invalid_result.exit_code == 1
    assert "UTF-8 encoded Markdown" in _result_error_text(invalid_result)

from __future__ import annotations

from pathlib import Path

import pytest

from loopora.workflows import WorkflowError, load_prompt_file, load_workflow_file


def test_workflow_file_reports_encoding_and_parse_errors(tmp_path) -> None:
    missing_workflow_file = tmp_path / "missing.yml"
    with pytest.raises(WorkflowError, match="strategy source file does not exist") as missing_exc:
        load_workflow_file(missing_workflow_file)
    assert str(missing_workflow_file) not in str(missing_exc.value)

    invalid_utf8_file = tmp_path / "workflow.yml"
    invalid_utf8_file.write_bytes(b"\xff")
    with pytest.raises(WorkflowError, match="UTF-8 encoded YAML or JSON"):
        load_workflow_file(invalid_utf8_file)

    invalid_yaml_file = tmp_path / "workflow.yaml"
    invalid_yaml_file.write_text("workflow:\n  roles: [", encoding="utf-8")
    with pytest.raises(WorkflowError, match="invalid workflow YAML"):
        load_workflow_file(invalid_yaml_file)

    invalid_json_file = tmp_path / "workflow.json"
    invalid_json_file.write_text("{", encoding="utf-8")
    with pytest.raises(WorkflowError, match="invalid workflow JSON"):
        load_workflow_file(invalid_json_file)


def test_workflow_and_prompt_file_inputs_expand_home_paths(monkeypatch, tmp_path) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setenv("HOME", str(home_dir))
    workflow_file = home_dir / "strategy.yml"
    workflow_file.write_text("workflow:\n  roles: []\n  steps: []\nprompt_files: {}\n", encoding="utf-8")
    prompt_file = home_dir / "prompt.md"
    prompt_file.write_text("---\nversion: 1\narchetype: builder\n---\nBuilder body\n", encoding="utf-8")

    workflow, prompt_files = load_workflow_file(Path("~/strategy.yml"))

    assert workflow == {"roles": [], "steps": []}
    assert prompt_files == {}
    assert load_prompt_file(Path("~/prompt.md")).endswith("Builder body\n")


def test_workflow_file_rejects_non_object_nested_workflow(tmp_path) -> None:
    workflow_file = tmp_path / "workflow.yml"
    workflow_file.write_text("workflow:\n  - not\n  - an\n  - object\n", encoding="utf-8")

    with pytest.raises(WorkflowError, match="workflow file workflow must be an object"):
        load_workflow_file(workflow_file)


def test_prompt_file_reports_encoding_errors(tmp_path) -> None:
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_bytes(b"\xff")

    with pytest.raises(WorkflowError, match="UTF-8 encoded Markdown"):
        load_prompt_file(prompt_file)


def test_prompt_file_reports_read_errors(tmp_path) -> None:
    prompt_file = tmp_path / "missing.md"

    with pytest.raises(WorkflowError, match="prompt file does not exist") as exc_info:
        load_prompt_file(prompt_file)
    assert str(prompt_file) not in str(exc_info.value)


def test_prompt_file_reports_unreadable_errors_without_local_path(monkeypatch, tmp_path) -> None:
    prompt_file = tmp_path / "unreadable.md"
    prompt_file.write_text("---\nversion: 1\narchetype: builder\n---\nBuilder body\n", encoding="utf-8")
    resolved_prompt_file = prompt_file.resolve()
    local_path = tmp_path / "private" / "prompt.md"
    original_read_text = type(prompt_file).read_text

    def fail_read_text(path, *args, **kwargs):
        if path == resolved_prompt_file:
            raise OSError(f"permission denied: {local_path}")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(type(prompt_file), "read_text", fail_read_text)

    with pytest.raises(WorkflowError, match="prompt file could not be read") as exc_info:
        load_prompt_file(prompt_file)
    assert "permission denied" not in str(exc_info.value)
    assert str(local_path) not in str(exc_info.value)

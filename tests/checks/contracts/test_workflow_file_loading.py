from __future__ import annotations

import pytest

from loopora.workflows import WorkflowError, load_prompt_file, load_workflow_file


def test_workflow_file_reports_encoding_and_parse_errors(tmp_path) -> None:
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

    with pytest.raises(WorkflowError, match="could not be read"):
        load_prompt_file(prompt_file)

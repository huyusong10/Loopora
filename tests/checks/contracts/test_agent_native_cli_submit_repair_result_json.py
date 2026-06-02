from __future__ import annotations

from agent_native_cli_submit_repair_core_blockers_test_support import (
    assert_labeled_loopora_agent_command,
    error_text,
    submit_repair_summary,
)
from agent_native_cli_test_support import (
    CliRunner,
    Path,
    RunArtifactLayout,
    _invoke_codex_submit,
    cli,
    json,
)


def test_cli_agent_submit_invalid_json_prints_result_file_repair_guidance(monkeypatch, tmp_path: Path) -> None:
    fixture = write_result_json_repair_fixture(tmp_path)
    install_result_json_repair_service(monkeypatch, fixture)
    runner = CliRunner()

    result = invoke_result_json_repair_submit(runner, fixture, fixture["bad_result_file"], json_output=False)

    output = error_text(result)
    assert result.exit_code == 1
    assert "submit_repair: result JSON needs repair before this Loopora step can advance" in output
    assert f"result_file_to_repair: {fixture['bad_result_file']}" in output
    assert "active_step_id: builder_step" in output
    assert "active_role: Builder" in output
    assert "active_target_agent: loopora-builder" in output
    assert "fix JSON syntax" in output
    schema_lookup = assert_labeled_loopora_agent_command(output, "schema_lookup", "next")
    assert f"--workdir {fixture['workdir'].resolve()}" in schema_lookup
    assert "--run-id run_bad_json" in schema_lookup
    assert "Traceback" not in output

    json_result = invoke_result_json_repair_submit(runner, fixture, fixture["bad_result_file"], json_output=True)
    summary = assert_result_json_repair_summary(json_result, fixture["bad_result_file"])
    assert any("fix JSON syntax" in item for item in summary["repair_focus"])
    assert summary["schema_lookup"].endswith("--run-id run_bad_json --json --entry-source codex_project_skill")

    missing_file = tmp_path / "missing-filled.result.json"
    missing = invoke_result_json_repair_submit(runner, fixture, missing_file, json_output=True)
    missing_summary = assert_result_json_repair_summary(missing, missing_file)
    assert any("create the filled result JSON file at result_file_to_repair" in item for item in missing_summary["repair_focus"])
    assert "create the missing filled result file" in missing_summary["next_repair_step"]
    assert "run_bad_json__builder_step.result.template.json" in missing_summary["next_repair_step"]


def write_result_json_repair_fixture(tmp_path: Path) -> dict:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / "run_bad_json")
    layout.initialize()
    agent_native_dir = layout.run_dir / "agent_native"
    agent_native_dir.mkdir(parents=True, exist_ok=True)
    active_template = tmp_path / "run_bad_json__builder_step.result.template.json"
    (agent_native_dir / "state.json").write_text(json.dumps(active_step_state(layout, active_template), ensure_ascii=False), encoding="utf-8")
    bad_result_file = tmp_path / "bad-json.result.json"
    bad_result_file.write_text('{"loopora_host_dispatch": ', encoding="utf-8")
    return {"workdir": workdir, "layout": layout, "bad_result_file": bad_result_file}


def active_step_state(layout: RunArtifactLayout, active_template: Path) -> dict:
    return {
        "active_step": {
            "agent_step_view": {
                "step_id": "builder_step",
                "role": {"name": "Builder", "id": "builder", "archetype": "builder"},
                "role_dispatch": {"target_agent": "loopora-builder"},
                "context_absolute_path": str(layout.step_instruction_context_path(0, 0, "builder_step")),
                "output_schema": {
                    "type": "object",
                    "required": ["summary"],
                    "properties": {"summary": {"type": "string"}},
                },
                "submit_hint": {"result_template_absolute_path": str(active_template)},
            }
        }
    }


def install_result_json_repair_service(monkeypatch, fixture: dict) -> None:
    layout = fixture["layout"]

    class FakeService:
        def get_run(self, run_id: str):
            assert run_id == "run_bad_json"
            return {"id": "run_bad_json", "runs_dir": str(layout.run_dir)}

    monkeypatch.setattr(cli, "create_service", FakeService)


def invoke_result_json_repair_submit(runner: CliRunner, fixture: dict, result_file: Path, *, json_output: bool):
    return _invoke_codex_submit(
        runner,
        fixture["workdir"],
        run_id="run_bad_json",
        step_id="builder_step",
        result_file=result_file,
        json_output=json_output,
    )


def assert_result_json_repair_summary(result, result_file: Path) -> dict:
    assert result.exit_code == 1
    assert error_text(result) == ""
    summary = submit_repair_summary(result)
    assert summary["ready"] is False
    assert summary["submit_repair"] == "repair_result_json"
    assert summary["result_file_to_repair"] == str(result_file)
    assert summary["active_step_id"] == "builder_step"
    assert summary["active_role"] == "Builder"
    assert summary["active_target_agent"] == "loopora-builder"
    return summary

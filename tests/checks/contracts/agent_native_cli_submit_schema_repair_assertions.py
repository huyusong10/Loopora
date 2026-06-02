from agent_native_cli_submit_schema_repair_fixture_support import UnfilledTemplateFixture
from agent_native_cli_test_support import _error_text, assert_agent_v3_envelope, json


def assert_plain_unfilled_template_repair(result, fixture: UnfilledTemplateFixture) -> None:
    plain_error = _error_text(result)
    assert result.exit_code == 1
    assert f"active_result_template: {fixture.result_file}" in plain_error
    assert f"active_result_file_to_write: {fixture.filled_result_file}" in plain_error
    assert f"result_outbox_dir: {fixture.result_outbox_dir}" in plain_error
    assert "do not overwrite the .result.template.json audit template" in plain_error


def assert_json_unfilled_template_repair(result, fixture: UnfilledTemplateFixture) -> None:
    assert result.exit_code == 1
    assert _error_text(result) == ""
    payload = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload,
        kind="agent_submit_repair",
        summary_key="agent_submit_repair_summary",
        status="blocked",
    )
    assert summary["submit_repair"] == "repair_result_json"
    assert summary["active_step_id"] == "builder_step"
    assert summary["submitted_template_file"] is True
    assert summary["active_result_file_to_write"] == str(fixture.filled_result_file)
    assert "save a filled result copy" in summary["next_repair_step"]
    assert "do not overwrite the .result.template.json audit template" in summary["next_repair_step"]
    assert str(fixture.filled_result_file) in summary["next_repair_step"]
    repair_focus = summary["repair_focus"]
    assert repair_focus[0] == (
        "replace null placeholders before submit: "
        "$.attempted, $.abandoned, $.assumption, $.summary, $.changed_files[0], $.proof_files[0], "
        "$.proof_artifacts[0], $.artifact_paths[0]"
    )
    assert "$.attempted must be string" in repair_focus
    assert "$.summary must be string" in repair_focus
    assert "$.changed_files[0] must be string" in repair_focus

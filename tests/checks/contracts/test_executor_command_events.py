from __future__ import annotations

from pathlib import Path

from loopora.executor import RoleRequest, build_command_event_payload


EXPECTED_COMMON_SECRET_ALIAS_REDACTION_COUNT = 4


def test_command_event_payload_redacts_prompt_schema_and_secret_values(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    request = RoleRequest(
        run_id="run_test",
        role="custom_helper",
        prompt="PROMPT_SECRET_MARKER write the whole plan",
        workdir=tmp_path,
        model="",
        reasoning_effort="",
        output_schema={
            "type": "object",
            "properties": {"SCHEMA_SECRET_MARKER": {"type": "string"}},
        },
        output_path=run_dir / "custom_output.json",
        run_dir=run_dir,
    )
    schema_text = '{"type": "object", "properties": {"SCHEMA_SECRET_MARKER": {"type": "string"}}}'

    payload = build_command_event_payload(
        request,
        [
            "custom-tool",
            "--json-schema",
            schema_text,
            "--auth-token",
            "TOKEN_SECRET_MARKER",
            "prefix PROMPT_SECRET_MARKER write the whole plan",
        ],
    )

    assert payload["type"] == "command"
    assert payload["prompt_omitted"] is True
    assert payload["json_schema_omitted"] is True
    assert payload["token_omitted"] is True
    assert payload["command_truncated"] is False
    assert "PROMPT_SECRET_MARKER" not in payload["message"]
    assert "SCHEMA_SECRET_MARKER" not in payload["message"]
    assert "TOKEN_SECRET_MARKER" not in payload["message"]
    assert "<prompt omitted>" in payload["message"]
    assert "<json schema omitted>" in payload["message"]
    assert "<secret omitted>" in payload["message"]


def test_command_event_payload_redacts_common_secret_alias_flags(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    request = RoleRequest(
        run_id="run_test",
        role="custom_helper",
        prompt="normal prompt",
        workdir=tmp_path,
        model="",
        reasoning_effort="",
        output_schema={"type": "object", "properties": {}},
        output_path=run_dir / "custom_output.json",
        run_dir=run_dir,
    )

    payload = build_command_event_payload(
        request,
        [
            "custom-tool",
            "--private-key",
            "PRIVATE_KEY_SECRET_MARKER",
            "--client_secret=CLIENT_SECRET_MARKER",
            "--x-api-key",
            "X_API_KEY_SECRET_MARKER",
            "--x-loopora-token",
            "LOOPORA_TOKEN_SECRET_MARKER",
        ],
    )

    assert payload["token_omitted"] is True
    assert "PRIVATE_KEY_SECRET_MARKER" not in payload["message"]
    assert "CLIENT_SECRET_MARKER" not in payload["message"]
    assert "X_API_KEY_SECRET_MARKER" not in payload["message"]
    assert "LOOPORA_TOKEN_SECRET_MARKER" not in payload["message"]
    assert payload["message"].count("<secret omitted>") == EXPECTED_COMMON_SECRET_ALIAS_REDACTION_COUNT

from __future__ import annotations

import json
from pathlib import Path

from loopora.db import LooporaRepository

from db_test_support import _create_run


def test_append_event_redacts_sensitive_payload_before_storage_and_mirrors(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path, run_id="run_sensitive_event", status="running")

    event = repository.append_event(
        run["id"],
        "codex_event",
        {
            "type": "stdout",
            "prompt": "PROMPT_SECRET_MARKER",
            "output_schema": {"properties": {"SCHEMA_SECRET_MARKER": {"type": "string"}}},
            "message": "tool --auth-token TOKEN_SECRET_MARKER Authorization: Bearer BEARER_SECRET_MARKER",
            "nested": {
                "api_key": "API_KEY_SECRET_MARKER",
                "safe": "keep me",
            },
        },
    )

    stored = repository.list_events(run["id"])[0]
    timeline_text = (Path(run["runs_dir"]) / "timeline" / "events.jsonl").read_text(encoding="utf-8")
    combined_text = json.dumps([event, stored], ensure_ascii=False) + timeline_text

    assert event["payload"]["payload_omitted"] is True
    assert set(event["payload"]["omitted_keys"]) == {"nested", "output_schema", "prompt"}
    assert "PROMPT_SECRET_MARKER" not in combined_text
    assert "SCHEMA_SECRET_MARKER" not in combined_text
    assert "TOKEN_SECRET_MARKER" not in combined_text
    assert "BEARER_SECRET_MARKER" not in combined_text
    assert "API_KEY_SECRET_MARKER" not in combined_text


def test_append_event_redacts_auth_and_cookie_headers(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path, run_id="run_sensitive_headers", status="running")

    event = repository.append_event(
        run["id"],
        "web_diagnostic",
        {
            "headers": {
                "Authorization": "Basic HEADER_AUTH_SECRET_MARKER",
                "Cookie": "session=HEADER_COOKIE_SECRET_MARKER",
            },
            "message": (
                "curl -H 'Authorization: Basic INLINE_AUTH_SECRET_MARKER' "
                "-H 'Cookie: session=INLINE_COOKIE_SECRET_MARKER'"
            ),
        },
    )

    stored = repository.list_events(run["id"])[0]
    timeline_text = (Path(run["runs_dir"]) / "timeline" / "events.jsonl").read_text(encoding="utf-8")
    combined_text = json.dumps([event, stored], ensure_ascii=False) + timeline_text

    assert event["payload"]["headers"]["Authorization"] == "<secret omitted>"
    assert event["payload"]["headers"]["Cookie"] == "<secret omitted>"
    assert "HEADER_AUTH_SECRET_MARKER" not in combined_text
    assert "HEADER_COOKIE_SECRET_MARKER" not in combined_text
    assert "INLINE_AUTH_SECRET_MARKER" not in combined_text
    assert "INLINE_COOKIE_SECRET_MARKER" not in combined_text


def test_append_codex_event_keeps_safe_shape_and_drops_raw_item_details(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = _create_run(repository, tmp_path, run_id="run_codex_raw_event", status="running")
    long_output = "visible output\n" + ("x" * 5000)

    event = repository.append_event(
        run["id"],
        "codex_event",
        {
            "type": "item.completed",
            "message": long_output,
            "input": {"prompt": "RAW_PROMPT_MARKER"},
            "item": {
                "type": "file_change",
                "changes": [
                    {
                        "path": "src/app.py",
                        "diff": "RAW_DIFF_MARKER",
                        "content": "RAW_CONTENT_MARKER",
                    }
                ],
            },
            "step_id": "builder_step",
            "role_name": "Builder",
            "archetype": "builder",
        },
    )

    stored = repository.list_events(run["id"])[0]
    timeline_text = (Path(run["runs_dir"]) / "timeline" / "events.jsonl").read_text(encoding="utf-8")
    combined_text = json.dumps([event, stored], ensure_ascii=False) + timeline_text

    assert event["payload"]["type"] == "item.completed"
    assert event["payload"]["step_id"] == "builder_step"
    assert event["payload"]["message_truncated"] is True
    assert event["payload"]["payload_omitted"] is True
    assert event["payload"]["omitted_keys"] == ["input"]
    assert event["payload"]["item"] == {"type": "file_change", "changes": [{"path": "src/app.py"}]}
    assert "visible output" in event["payload"]["message"]
    assert "RAW_PROMPT_MARKER" not in combined_text
    assert "RAW_DIFF_MARKER" not in combined_text
    assert "RAW_CONTENT_MARKER" not in combined_text

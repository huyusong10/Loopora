from __future__ import annotations

import json

from loopora.executor import RealCodexExecutor


def test_claude_stream_parser_extracts_structured_output() -> None:
    _executor, state, emitted = handle_claude_records(
        {
            "type": "stream_event",
            "event": {
                "type": "content_block_start",
                "content_block": {"name": "StructuredOutput", "input": {}, "id": "tool_1", "type": "tool_use"},
                "index": 1,
            },
        },
        {"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "input_json_delta", "partial_json": '{"ok": true'}, "index": 1}},
        {"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "input_json_delta", "partial_json": "}"}, "index": 1}},
        {"type": "result", "result": "done", "structured_output": {"ok": True}},
    )

    assert state["structured_output"] == {"ok": True}
    assert ("codex_event", {"type": "stdout", "message": "done"}) in emitted


def test_claude_stream_parser_logs_tool_use_and_tool_result() -> None:
    _executor, _state, emitted = handle_claude_records(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "pwd", "description": "Get current working directory"},
                    }
                ]
            },
        },
        {
            "type": "user",
            "message": {"content": [{"type": "tool_result", "content": "/tmp/workdir"}]},
            "tool_use_result": {"stdout": "/tmp/workdir", "stderr": "", "interrupted": False},
        },
    )

    assert ("codex_event", {"type": "stdout", "message": "Tool use · Bash · pwd · Get current working directory"}) in emitted
    assert ("codex_event", {"type": "stdout", "message": "Tool result · /tmp/workdir"}) in emitted


def test_claude_stream_parser_summarizes_system_metadata() -> None:
    _executor, _state, emitted = handle_claude_records({"type": "system", "model": "claude-sonnet", "claude_code_version": "1.2.3"})

    assert emitted == [
        ("codex_event", {"type": "stdout", "message": "Claude Code ready · model=claude-sonnet · cli=1.2.3"})
    ]


def test_claude_stream_parser_truncates_large_tool_results() -> None:
    long_stdout = "\n".join(f"line {index}" for index in range(40))

    _executor, _state, emitted = handle_claude_records(
        {
            "type": "user",
            "message": {"content": [{"type": "tool_result", "content": long_stdout}]},
            "tool_use_result": {"stdout": long_stdout, "stderr": "", "interrupted": False},
        }
    )

    assert emitted
    message = emitted[0][1]["message"]
    assert message.startswith("Tool result · line 0")
    assert "... (truncated)" in message
    assert "line 39" not in message


def test_opencode_text_parser_extracts_json_object() -> None:
    executor, state, emitted = handle_opencode_record({"type": "text", "part": {"text": '{"ok": true}'}})

    assert state["latest_text"] == '{"ok": true}'
    assert executor._parse_structured_output_from_text(state["latest_text"]) == {"ok": True}
    assert ("codex_event", {"type": "stdout", "message": '{"ok": true}'}) in emitted


def handle_claude_records(*records: dict) -> tuple[RealCodexExecutor, dict, list[tuple[str, dict]]]:
    executor = RealCodexExecutor()
    state = {"blocks": {}, "structured_output": None}
    emitted: list[tuple[str, dict]] = []
    for record in records:
        executor._handle_claude_line(json.dumps(record), state, lambda event_type, payload: emitted.append((event_type, payload)))
    return executor, state, emitted


def handle_opencode_record(record: dict) -> tuple[RealCodexExecutor, dict, list[tuple[str, dict]]]:
    executor = RealCodexExecutor()
    state = {"latest_text": "", "text_parts": []}
    emitted: list[tuple[str, dict]] = []
    executor._handle_opencode_line(json.dumps(record), state, lambda event_type, payload: emitted.append((event_type, payload)))
    return executor, state, emitted

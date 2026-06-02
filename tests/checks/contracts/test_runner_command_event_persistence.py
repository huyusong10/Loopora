from __future__ import annotations

import json
from pathlib import Path

from loopora.executor import FakeCodexExecutor, build_command_event_payload

from runner_helpers import _create_loop


def test_command_events_do_not_persist_prompt_or_secret_markers(
    service_factory,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    prompt_marker = "RUN_EVENT_PROMPT_SECRET_MARKER"
    token_marker = "RUN_EVENT_TOKEN_SECRET_MARKER"
    spec_path = tmp_path / "sensitive-spec.md"
    spec_path.write_text(
        f"""# Task

Ship the requested behavior with {prompt_marker}.

# Done When

- The primary experience completes successfully.

# Guardrails

- Keep changes focused.

# Success Surface

- The result remains easy for the next role to verify.

# Fake Done

- A happy-path-only result that leaves the edge path unverifiable.

# Evidence Preferences

- Prefer structured run artifacts and reproducible checks over role self-report.
""",
        encoding="utf-8",
    )

    class CommandEventExecutor(FakeCodexExecutor):
        def execute(self, request, emit_event, should_stop, set_child_pid):
            emit_event(
                "codex_event",
                build_command_event_payload(
                    request,
                    [
                        "codex",
                        "exec",
                        "--auth-token",
                        token_marker,
                        request.prompt,
                    ],
                ),
            )
            return super().execute(request, emit_event, should_stop, set_child_pid)

    service = service_factory(scenario="success")
    service.executor_factory = lambda: CommandEventExecutor(scenario="success")
    loop = _create_loop(service, spec_path, sample_workdir, max_iters=1)

    run = service.rerun(loop["id"])
    events = service.repository.list_events(run["id"])
    timeline_events = (Path(run["runs_dir"]) / "timeline" / "events.jsonl").read_text(encoding="utf-8")
    event_text = json.dumps(events, ensure_ascii=False)
    command_payloads = [
        event["payload"]
        for event in events
        if event["event_type"] == "codex_event" and event["payload"].get("type") == "command"
    ]

    assert command_payloads
    assert all(payload["prompt_omitted"] for payload in command_payloads)
    assert all(payload["token_omitted"] for payload in command_payloads)
    assert prompt_marker not in event_text
    assert token_marker not in event_text
    assert prompt_marker not in timeline_events
    assert token_marker not in timeline_events

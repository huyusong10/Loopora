from __future__ import annotations

import json
from pathlib import Path

from loopora.executor import FakeCodexExecutor

from alignment_test_support import _wait_for_status


def test_alignment_executor_events_redact_sensitive_values_before_persistence(
    service_factory,
    sample_workdir: Path,
) -> None:
    class SensitiveAlignmentExecutor(FakeCodexExecutor):
        def execute(self, request, emit_event, _should_stop, set_child_pid) -> dict:
            set_child_pid(None)
            emit_event(
                "codex_event",
                {
                    "type": "command",
                    "message": (
                        "codex exec --token leak-command-token\n"
                        "Authorization: Bearer leak-bearer-token\n"
                        "Cookie: sid=leak-cookie-token"
                    ),
                    "auth_token": "leak-field-token",
                    "prompt": "leak-prompt-body",
                    "json_schema": {"secret": "leak-schema-body"},
                },
            )
            payload = self._alignment_agreement_response()
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = SensitiveAlignmentExecutor
    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Create an alignment session with sensitive executor output.",
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    persisted_events = service.list_alignment_events(session["id"])
    artifact_events = (Path(session["artifact_dir"]) / "events" / "events.jsonl").read_text(encoding="utf-8")
    stdout_text = (Path(session["artifact_dir"]) / "invocations" / "0001" / "stdout.log").read_text(encoding="utf-8")
    persisted_session = json.dumps(service.get_alignment_session(session["id"]), ensure_ascii=False)
    persisted_events_text = json.dumps(persisted_events, ensure_ascii=False)

    for text in (persisted_session, persisted_events_text, artifact_events, stdout_text):
        assert "leak-command-token" not in text
        assert "leak-bearer-token" not in text
        assert "leak-cookie-token" not in text
        assert "leak-field-token" not in text
        assert "leak-prompt-body" not in text
        assert "leak-schema-body" not in text
    assert any(event["event_type"] == "alignment_waiting_user" for event in persisted_events)

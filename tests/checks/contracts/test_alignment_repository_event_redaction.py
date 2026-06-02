from __future__ import annotations

import json
from pathlib import Path


def test_alignment_repository_redacts_sensitive_values_before_db_and_artifact(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Create a local alignment event sink.",
        start_immediately=False,
    )

    event = service.repository.append_alignment_event(
        session["id"],
        "alignment_failed",
        {
            "message": "OPENAI_API_KEY=leak-env-token",
            "error": "Authorization: Bearer leak-error-token",
            "headers": {"Cookie": "sid=leak-cookie-token"},
            "auth_token": "leak-field-token",
            "prompt": "leak-prompt-body",
            "json_schema": {"secret": "leak-schema-body"},
            "bundle_yaml": "leak-bundle-body",
        },
    )
    listed = service.list_alignment_events(session["id"])[-1]
    artifact_events = (Path(session["artifact_dir"]) / "events" / "events.jsonl").read_text(encoding="utf-8")

    for text in (json.dumps(event, ensure_ascii=False), json.dumps(listed, ensure_ascii=False), artifact_events):
        assert "leak-env-token" not in text
        assert "leak-error-token" not in text
        assert "leak-cookie-token" not in text
        assert "leak-field-token" not in text
        assert "leak-prompt-body" not in text
        assert "leak-schema-body" not in text
        assert "leak-bundle-body" not in text
    assert listed["payload"]["auth_token"] == "<secret omitted>"
    assert listed["payload"]["prompt_omitted"] is True
    assert listed["payload"]["json_schema_omitted"] is True
    assert listed["payload"]["bundle_yaml_omitted"] is True

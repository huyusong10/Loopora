from pathlib import Path

from alignment_test_support import (
    _assert_alignment_stage_blocked,
    _assert_alignment_stage_blocked_for_key,
    _wait_for_status,
)
from loopora.service_alignment_stage_messages import alignment_missing_item_label


def _assert_transcript_uses_public_missing_label(session: dict, missing_key: str) -> None:
    content = session["transcript"][-1]["content"]
    labels = {
        alignment_missing_item_label(missing_key, prefers_chinese=False),
        alignment_missing_item_label(missing_key, prefers_chinese=True),
    }
    assert any(label in content for label in labels)
    if "_" in missing_key:
        assert missing_key not in content


def readiness_blocked_session(
    service_factory,
    sample_workdir: Path,
    *,
    scenario: str,
    message: str,
) -> tuple[object, str, dict]:
    service = service_factory(scenario=scenario)
    created = service.create_alignment_session(workdir=sample_workdir, message=message)
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "waiting_user")
    return service, created["id"], session


def assert_readiness_blocked(service: object, session_id: str, session: dict, content_fragment: str) -> None:
    assert not Path(session["bundle_path"]).exists()
    assert content_fragment in session["transcript"][-1]["content"]
    _assert_alignment_stage_blocked(service, session_id)


def assert_readiness_key_blocked(service: object, session_id: str, session: dict, missing_key: str) -> None:
    assert not Path(session["bundle_path"]).exists()
    _assert_transcript_uses_public_missing_label(session, missing_key)
    _assert_alignment_stage_blocked_for_key(service, session_id, missing_key)


__all__ = [
    "assert_readiness_blocked",
    "assert_readiness_key_blocked",
    "readiness_blocked_session",
]

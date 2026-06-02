from pathlib import Path

from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_requests import RevisionAlignmentSessionRequest, default_alignment_executor_settings
from loopora.service_alignment_revision import create_revision_alignment_session

from alignment_revision_test_support import FakeAlignmentRevisionRepository, revision_context


def test_alignment_revision_command_keeps_session_idle_when_not_starting(tmp_path: Path) -> None:
    bundle_path = tmp_path / ".loopora" / "alignment_sessions" / "align_revision" / "artifacts" / "bundle.yml"
    repo = FakeAlignmentRevisionRepository(
        {
            "id": "align_revision",
            "status": "idle",
            "bundle_path": str(bundle_path),
            "working_agreement": {},
        }
    )
    context, _created_sessions, started_sessions, logged_sessions = revision_context(repo)
    seed_bundle = load_bundle_text(alignment_bundle_yaml(str(tmp_path)))

    session = create_revision_alignment_session(
        context,
        RevisionAlignmentSessionRequest(
            seed_bundle=seed_bundle,
            message="Improve later.",
            start_immediately=False,
            source_context={"source_type": "bundle", "source_bundle_id": "bundle_2"},
            linked_bundle_id="bundle_2",
            linked_run_id="",
            executor_settings=default_alignment_executor_settings(),
        ),
    )

    assert session["status"] == "idle"
    assert started_sessions == []
    assert logged_sessions[0]["linked_bundle_id"] == "bundle_2"

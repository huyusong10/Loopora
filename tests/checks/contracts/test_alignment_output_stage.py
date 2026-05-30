from pathlib import Path

from loopora.service_alignment_output_stage import (
    AlignmentOutputStageContext,
    AlignmentOutputStageRequest,
    apply_alignment_output_stage,
    alignment_output_bundle_stage_error,
    alignment_output_stage_plan,
)


class FakeAlignmentOutputStageRepository:
    def __init__(self, session: dict) -> None:
        self.session = dict(session)
        self.events: list[dict] = []
        self.updates: list[dict] = []

    def update_alignment_session(self, session_id: str, **fields: object) -> dict:
        assert session_id == self.session["id"]
        self.updates.append(fields)
        self.session.update(fields)
        return dict(self.session)

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict:
        assert session_id == self.session["id"]
        event = {"event_type": event_type, "payload": payload}
        self.events.append(event)
        return event


def test_alignment_output_stage_plan_projects_agreement_block(tmp_path: Path) -> None:
    plan = alignment_output_stage_plan(
        {
            "workdir": str(tmp_path),
            "alignment_stage": "clarifying",
            "transcript": [{"role": "user", "content": "请帮我对齐这个长任务。"}],
        },
        {
            "alignment_phase": "agreement",
            "agreement_summary": "这是一份需要继续补齐证据的协议。",
            "readiness_checklist": {"loop_fit": False},
        },
        captured_at="2026-05-29T00:00:00Z",
        readiness_keys=["loop_fit"],
        readiness_evidence_keys=[],
    )

    assert plan is not None
    assert plan.update_fields == {"alignment_stage": "clarifying"}
    assert plan.event_type == "alignment_checklist_incomplete"
    assert plan.event_payload == {"alignment_stage": "clarifying", "missing": ["loop_fit"]}
    assert plan.output_updates["needs_user_input"] is True
    assert plan.output_updates["bundle_yaml"] == ""


def test_apply_alignment_output_stage_updates_session_event_and_output(tmp_path: Path) -> None:
    session = {
        "id": "align_output_stage",
        "workdir": str(tmp_path),
        "alignment_stage": "clarifying",
        "transcript": [{"role": "user", "content": "请帮我对齐这个长任务。"}],
    }
    repo = FakeAlignmentOutputStageRepository(session)
    context = AlignmentOutputStageContext(
        repository=repo,
        decorate_session=lambda payload: {**payload, "decorated": True},
        now=lambda: "2026-05-30T00:00:00Z",
    )
    output = {
        "alignment_phase": "agreement",
        "agreement_summary": "这是一份需要继续补齐证据的协议。",
        "readiness_checklist": {"loop_fit": False},
    }

    updated = apply_alignment_output_stage(
        context,
        AlignmentOutputStageRequest(
            session_id="align_output_stage",
            session=session,
            output=output,
            readiness_keys=["loop_fit"],
            readiness_evidence_keys=[],
        ),
    )

    assert repo.updates == [{"alignment_stage": "clarifying"}]
    assert repo.events == [
        {
            "event_type": "alignment_checklist_incomplete",
            "payload": {"alignment_stage": "clarifying", "missing": ["loop_fit"]},
        }
    ]
    assert output["needs_user_input"] is True
    assert output["bundle_yaml"] == ""
    assert updated["decorated"] is True
    assert updated["alignment_stage"] == "clarifying"


def test_apply_alignment_output_stage_leaves_non_stage_output_untouched(tmp_path: Path) -> None:
    session = {"id": "align_no_stage", "workdir": str(tmp_path), "alignment_stage": "ready", "transcript": []}
    repo = FakeAlignmentOutputStageRepository(session)
    context = AlignmentOutputStageContext(
        repository=repo,
        decorate_session=lambda payload: {**payload, "decorated": True},
    )
    output = {"assistant_message": "No alignment phase here."}

    updated = apply_alignment_output_stage(
        context,
        AlignmentOutputStageRequest(
            session_id="align_no_stage",
            session=session,
            output=output,
            readiness_keys=[],
            readiness_evidence_keys=[],
        ),
    )

    assert updated is session
    assert output == {"assistant_message": "No alignment phase here."}
    assert repo.updates == []
    assert repo.events == []


def test_alignment_output_bundle_stage_error_blocks_unconfirmed_bundle(tmp_path: Path) -> None:
    error = alignment_output_bundle_stage_error(
        {
            "workdir": str(tmp_path),
            "alignment_stage": "clarifying",
            "transcript": [],
        },
        {
            "alignment_phase": "bundle",
            "agreement_summary": "Agreement",
            "readiness_checklist": {"loop_fit": True},
            "readiness_evidence": {},
        },
        confirmed_stages={"confirmed"},
        readiness_keys=["loop_fit"],
        readiness_evidence_keys=[],
    )

    assert "explicit confirmation" in error

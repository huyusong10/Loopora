from pathlib import Path

from loopora.alignment_readiness_rules import ALIGNMENT_READINESS_EVIDENCE_KEYS
from loopora.service_alignment_output_message import (
    AlignmentOutputMessageContext,
    AlignmentOutputMessageRequest,
    alignment_output_message_bundle_and_options,
)


class FakeAlignmentOutputMessageRepository:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict:
        event = {"session_id": session_id, "event_type": event_type, "payload": payload}
        self.events.append(event)
        return event


def complete_readiness_evidence() -> dict:
    evidence = {
        key: (
            f"{key} task-scoped evidence uses tests command artifact proof; proven path, weak signals, "
            "unproven gaps, blocking blockers, and residual risk accepted with owner follow-up."
        )
        for key in ALIGNMENT_READINESS_EVIDENCE_KEYS
    }
    evidence["local_governance"] = (
        "Project-local design/ and tests/: builder reads the contract, inspector verifies tests, "
        "and gatekeeper blocks weak unproven missing proof; proven weak unproven blocking residual risk owner follow-up."
    )
    evidence["workdir_facts"] = (
        "Snapshot observation is unknown and uncertain beyond this temporary workdir; proven weak unproven "
        "blocking residual risk owner follow-up."
    )
    return evidence


def output_message_request(
    tmp_path: Path,
    output: dict,
    *,
    alignment_stage: str = "confirmed",
    confirmed_stages: set[str] | None = None,
) -> AlignmentOutputMessageRequest:
    return AlignmentOutputMessageRequest(
        session_id="align_output_message",
        session={
            "id": "align_output_message",
            "workdir": str(tmp_path),
            "alignment_stage": alignment_stage,
            "transcript": [{"role": "user", "content": "请帮我整理这个任务。"}],
        },
        output=output,
        confirmed_stages=confirmed_stages or {"confirmed"},
        missing_item_ids={"task_scope", "loop_fit"},
        readiness_keys=["loop_fit"],
        readiness_evidence_keys=[],
    )


def test_alignment_output_message_preserves_valid_bundle_and_normalized_missing_items(tmp_path: Path) -> None:
    output = {
        "assistant_message": "已整理成 bundle。",
        "bundle_yaml": "version: 1\n",
        "alignment_phase": "bundle",
        "agreement_summary": "已确认这次任务的判断协议。",
        "readiness_checklist": {"loop_fit": True},
        "readiness_evidence": complete_readiness_evidence(),
        "alignment_missing_items": ["task_scope", "unknown", "task_scope"],
    }

    repo, result = output_message_result(tmp_path, output)

    assert result.assistant_message == "已整理成 bundle。"
    assert result.bundle_yaml == "version: 1"
    assert result.missing_items == ["task_scope"]
    assert result.decision_options == []
    assert output["bundle_yaml"] == "version: 1\n"
    assert repo.events == []


def test_alignment_output_message_blocks_unconfirmed_bundle_and_projects_default_options(tmp_path: Path) -> None:
    output = {
        "assistant_message": "已整理完成。",
        "bundle_yaml": "version: 1\n",
        "alignment_phase": "bundle",
        "agreement_summary": "Agreement",
        "readiness_checklist": {"loop_fit": True},
        "readiness_evidence": {},
    }

    repo, result = output_message_result(tmp_path, output, alignment_stage="clarifying")

    assert "明确确认" in result.assistant_message
    assert result.bundle_yaml == ""
    assert result.missing_items is None
    assert output["needs_user_input"] is True
    assert output["decision_options"][0]["recommended"] is True
    assert [option["id"] for option in result.decision_options] == ["evidence_first", "speed_first", "add_judgment"]
    assert repo.events == [
        {
            "session_id": "align_output_message",
            "event_type": "alignment_stage_blocked",
            "payload": {"status": "waiting_user", "error": result.assistant_message},
        }
    ]


def test_alignment_output_message_records_language_mismatch_without_forcing_needs_user_input(tmp_path: Path) -> None:
    output = {
        "assistant_message": "I prepared a follow-up question.",
        "needs_user_input": True,
        "alignment_missing_items": ["loop_fit"],
    }

    repo, result = output_message_result(tmp_path, output)

    assert "确认一个会改变 Loop 形状的点" in result.assistant_message
    assert result.bundle_yaml == ""
    assert result.missing_items == ["loop_fit"]
    assert output["needs_user_input"] is True
    assert output["decision_options"][0]["recommended"] is True
    assert result.decision_options[0]["id"] == "evidence_first"
    assert repo.events == [
        {
            "session_id": "align_output_message",
            "event_type": "alignment_language_mismatch",
            "payload": {"missing": ["assistant_message"], "surface": "assistant_message"},
        }
    ]


def output_message_result(tmp_path: Path, output: dict, **request_overrides):
    repo = FakeAlignmentOutputMessageRepository()
    return repo, alignment_output_message_bundle_and_options(
        AlignmentOutputMessageContext(repository=repo), output_message_request(tmp_path, output, **request_overrides)
    )

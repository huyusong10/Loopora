from __future__ import annotations

from pathlib import Path

from alignment_test_support import _wait_for_status


def test_alignment_language_hint_ignores_confirmation_only_chinese(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a focused starter experience.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "ready")
    prompt_text = (Path(session["artifact_dir"]) / "invocations" / "0001" / "prompt.md").read_text(encoding="utf-8")

    assert "I prepared an importable Loopora bundle." in session["transcript"][-1]["content"]
    assert "User language hint: `Follow the dominant substantive task language" in prompt_text
    assert "User language hint: `Chinese" not in prompt_text


def test_alignment_language_hint_ignores_chinese_agreement_adoption_confirmation(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a focused starter experience.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认，采用这份工作协议。")
    session = _wait_for_status(service, created["id"], "ready")
    prompt_text = (Path(session["artifact_dir"]) / "invocations" / "0001" / "prompt.md").read_text(encoding="utf-8")

    assert "I prepared an importable Loopora bundle." in session["transcript"][-1]["content"]
    assert "User language hint: `Follow the dominant substantive task language" in prompt_text
    assert "User language hint: `Chinese" not in prompt_text

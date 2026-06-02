from __future__ import annotations

from pathlib import Path

from alignment_test_support import _confirm_alignment_agreement


def test_alignment_service_normalizes_custom_command_settings(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")

    session = service.create_alignment_session(
        workdir=sample_workdir,
        executor_kind="custom",
        executor_mode="preset",
        command_cli="my-aligner",
        command_args_text="{prompt}\n--output\n{output_path}",
        start_immediately=False,
    )

    assert session["executor_kind"] == "custom"
    assert session["executor_mode"] == "command"
    assert session["command_cli"] == "my-aligner"
    assert session["model"] == ""
    assert session["reasoning_effort"] == ""


def test_alignment_service_blocks_custom_executor_bundle_that_drops_session_settings(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Generate a bundle that preserves the selected runtime.",
        executor_kind="custom",
        executor_mode="preset",
        command_cli="my-aligner",
        command_args_text="{prompt}\n--output\n{output_path}",
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert session["validation"]["ok"] is False
    assert "must preserve selected Web executor settings" in session["error_message"]
    assert "loop.executor_kind" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_validation_failed" and "command/custom sessions" in event["payload"].get("error", "")
        for event in events
    )

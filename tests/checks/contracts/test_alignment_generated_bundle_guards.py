from __future__ import annotations

from pathlib import Path

from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_bundle_control_summary import build_bundle_control_summary

from alignment_test_support import _confirm_alignment_agreement


def test_bundle_control_summary_projects_execution_strategy(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))

    summary = build_bundle_control_summary(bundle)

    assert any("Future iterations build the focused starter slice first" in item for item in summary["execution_strategy"])
    assert any(item["key"] == "execution_strategy" and item["mapped"] for item in summary["traceability"]["items"])


def test_alignment_service_blocks_generated_bundle_lineage_metadata(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_generated_lineage_metadata")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a standalone candidate bundle, not a lineage revision.",
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert session["validation"]["ok"] is False
    assert "must omit metadata.source_bundle_id and metadata.revision" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_validation_failed"
        and "source context is temporary" in event["payload"].get("error", "")
        for event in events
    )


def test_alignment_service_blocks_markdown_fenced_bundle_yaml(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_markdown_fenced_bundle")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a raw YAML bundle without wrappers.",
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert session["validation"]["ok"] is False
    assert "must be one raw YAML document" in session["error_message"]
    assert "must start with version: 1" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_validation_failed"
        and "markdown-fenced output" in event["payload"].get("error", "")
        for event in events
    )

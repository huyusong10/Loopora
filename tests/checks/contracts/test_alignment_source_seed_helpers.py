from __future__ import annotations

from loopora.service_alignment_context import alignment_source_option_seed_kind
from loopora.service_alignment_source_seed import (
    alignment_bundle_completion_mode,
    alignment_loop_bundle_id,
    alignment_revision_seed_bundle,
)


SOURCE_BUNDLE_REVISION = 3


def test_alignment_source_option_seed_kind_normalizes_session_sources() -> None:
    assert alignment_source_option_seed_kind({"source_type": "alignment_session"}) == "alignment_session"
    assert alignment_source_option_seed_kind({"source_type": "alignment_session_file"}) == "alignment_session"
    assert alignment_source_option_seed_kind({"source_type": "run"}) == "run"
    assert alignment_source_option_seed_kind({}) == ""


def test_alignment_bundle_completion_mode_handles_missing_or_invalid_loop() -> None:
    assert alignment_bundle_completion_mode({"loop": {"completion_mode": "all_checks_pass"}}) == "all_checks_pass"
    assert alignment_bundle_completion_mode({"loop": "not-a-dict"}) == ""
    assert alignment_bundle_completion_mode({}) == ""


def test_alignment_loop_bundle_id_handles_missing_or_invalid_bundle() -> None:
    assert alignment_loop_bundle_id({"bundle": {"id": "bundle_1"}}) == "bundle_1"
    assert alignment_loop_bundle_id({"bundle": "not-a-dict"}) == ""
    assert alignment_loop_bundle_id({}) == ""


def test_alignment_revision_seed_bundle_clears_import_identity_without_mutating_source() -> None:
    source_bundle = {
        "metadata": {
            "name": "Source bundle",
            "bundle_id": "bundle_1",
            "source_bundle_id": "bundle_source",
            "revision": 3,
        },
        "spec": {"markdown": "Task"},
    }

    seed = alignment_revision_seed_bundle(source_bundle)

    assert seed["metadata"] == {"name": "Source bundle", "bundle_id": ""}
    assert source_bundle["metadata"]["bundle_id"] == "bundle_1"
    assert source_bundle["metadata"]["source_bundle_id"] == "bundle_source"
    assert source_bundle["metadata"]["revision"] == SOURCE_BUNDLE_REVISION

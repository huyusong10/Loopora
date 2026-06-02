from __future__ import annotations

from loopora.evidence_coverage import _overall_coverage_status
from loopora.evidence_coverage_summary import top_coverage_gaps as _top_coverage_gaps
from loopora.evidence_coverage_targets import build_coverage_targets


def test_coverage_targets_include_success_surface_as_advisory() -> None:
    targets = build_coverage_targets(
        {
            "checks": [{"id": "check_001", "title": "Required proof"}],
            "success_surface": ["The result remains easy for the next role to verify."],
            "fake_done_states": ["Happy-path-only proof is fake done."],
            "evidence_preferences": ["Prefer reproducible checks."],
        },
        completion_mode="gatekeeper",
    )
    targets_by_id = {target["id"]: target for target in targets}

    assert targets_by_id["success_surface.surface_001"] == {
        "id": "success_surface.surface_001",
        "kind": "success_surface",
        "source_section": "Success Surface",
        "source_id": "surface_001",
        "label": "Success surface 1",
        "text": "The result remains easy for the next role to verify.",
        "required": False,
    }
    assert targets_by_id["done_when.check_001"]["required"] is True
    assert targets_by_id["fake_done.risk_001"]["required"] is False
    assert targets_by_id["evidence_preference.pref_001"]["required"] is False


def test_coverage_blocks_explicit_advisory_blockers_without_promoting_required_flag() -> None:
    rows = {
        "advisory_string_required": {
            "id": "advisory_string_required",
            "kind": "fake_done",
            "source_section": "Fake Done",
            "source_id": "risk_001",
            "label": "Advisory risk",
            "text": "String required should remain advisory.",
            "required": "true",
            "status": "blocked",
            "reason": "Advisory target is blocked.",
            "evidence_refs": [],
        }
    }

    assert _overall_coverage_status(rows) == "blocked"

    gaps = _top_coverage_gaps(
        [
            {
                **rows["advisory_string_required"],
                "artifact_refs": [],
            },
            {
                "id": "literal_required",
                "kind": "done_when",
                "source_section": "Done When",
                "source_id": "check_001",
                "label": "Required proof",
                "text": "Literal required stays first.",
                "required": True,
                "status": "missing",
                "reason": "Missing.",
                "evidence_refs": [],
                "artifact_refs": [],
            },
        ]
    )

    assert gaps[0]["target_id"] == "literal_required"
    assert gaps[1]["target_id"] == "advisory_string_required"
    assert gaps[1]["required"] is False


def test_coverage_treats_intrinsic_required_targets_as_required_when_marker_is_malformed() -> None:
    rows = {
        "done_when.check_001": {
            "id": "done_when.check_001",
            "kind": "done_when",
            "source_section": "Done When",
            "source_id": "check_001",
            "label": "Required proof",
            "text": "Malformed required marker must not downgrade this target.",
            "required": "true",
            "status": "missing",
            "reason": "Missing.",
            "evidence_refs": [],
        },
        "gatekeeper.finish": {
            "id": "gatekeeper.finish",
            "kind": "gatekeeper",
            "source_section": "Workflow",
            "source_id": "finish",
            "label": "GateKeeper finish",
            "text": "Malformed required marker must not downgrade this target.",
            "required": False,
            "status": "covered",
            "reason": "Covered.",
            "evidence_refs": [],
        },
    }

    assert _overall_coverage_status(rows) == "partial"

    gaps = _top_coverage_gaps([{**row, "artifact_refs": []} for row in rows.values()])

    assert gaps[0]["target_id"] == "done_when.check_001"
    assert gaps[0]["required"] is True

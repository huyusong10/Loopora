from __future__ import annotations

# Merged from test_alignment_service_facade_architecture.py
import ast

from service_architecture_test_support import design_contracts_source, loopora_source


def test_service_alignment_facade_only_exposes_public_delegates_and_context_factory() -> None:
    source = loopora_source("service_alignment.py")
    tree = ast.parse(source)
    top_level_functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    mixin = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ServiceAlignmentMixin")
    private_methods = [node.name for node in mixin.body if isinstance(node, ast.FunctionDef) and node.name.startswith("_")]

    assert top_level_functions == []
    assert private_methods == ["_alignment_context_factory"]
    assert "explicit public compatibility delegates plus the context-factory hook" in design_contracts_source()

# Merged from test_alignment_service_governance_marker_responsibilities.py
from pathlib import Path

from alignment_test_support import _confirm_alignment_agreement


def test_alignment_service_blocks_governance_markers_without_bundle_responsibilities(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_governance_markers_listed_without_responsibilities")
    (sample_workdir / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
    (sample_workdir / "design").mkdir()
    (sample_workdir / "design" / "README.md").write_text("# Design\n", encoding="utf-8")
    (sample_workdir / "tests").mkdir()

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a starter experience that must respect local project governance markers.",
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert not session["validation"]["ok"]
    assert "project-local governance markers" in session["error_message"]
    assert "Builder reading" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_validation_failed"
        and "project-local governance markers" in event["payload"].get("error", "")
        for event in events
    )

# Merged from test_alignment_service_loop_fit_readiness_blocks.py

import pytest

from alignment_readiness_service_block_test_support import assert_readiness_key_blocked, readiness_blocked_session


@pytest.mark.parametrize(
    "scenario",
    [
        "alignment_contradictory_loop_fit_readiness_evidence",
        "alignment_single_pass_sufficient_loop_fit_readiness_evidence",
        "alignment_benchmark_only_loop_fit_readiness_evidence",
        "alignment_chinese_direct_chat_loop_fit_readiness_evidence",
    ],
)
def test_alignment_service_blocks_agreement_that_contradicts_loop_fit(
    service_factory,
    sample_workdir: Path,
    scenario: str,
) -> None:
    service, session_id, session = readiness_blocked_session(
        service_factory,
        sample_workdir,
        scenario=scenario,
        message="Build a task that may only need one Agent pass.",
    )

    assert_readiness_key_blocked(service, session_id, session, "loop_fit")

# Merged from test_alignment_service_placeholder_readiness_blocks.py

import pytest



@pytest.mark.parametrize(
    ("scenario", "missing_key"),
    [
        ("alignment_vague_success_surface_readiness_evidence", "success_surface"),
        ("alignment_vague_fake_done_readiness_evidence", "fake_done_risks"),
        ("alignment_vague_evidence_preferences_readiness_evidence", "evidence_preferences"),
        ("alignment_vague_role_posture_readiness_evidence", "role_posture"),
        ("alignment_role_posture_without_gatekeeper_readiness_evidence", "role_posture"),
    ],
)
def test_alignment_service_blocks_placeholder_judgment_readiness_evidence(
    service_factory,
    sample_workdir: Path,
    scenario: str,
    missing_key: str,
) -> None:
    service, session_id, session = readiness_blocked_session(
        service_factory,
        sample_workdir,
        scenario=scenario,
        message=f"Build a starter experience with placeholder {missing_key} evidence.",
    )

    assert_readiness_key_blocked(service, session_id, session, missing_key)

# Merged from test_alignment_service_required_readiness_blocks.py

import pytest

from alignment_readiness_service_block_test_support import (
    assert_readiness_blocked,
)


def test_alignment_service_blocks_bundle_without_readiness_evidence(
    service_factory,
    sample_workdir: Path,
) -> None:
    service, session_id, session = readiness_blocked_session(
        service_factory,
        sample_workdir,
        scenario="alignment_missing_readiness_evidence",
        message="Build a starter experience, but do not explain the posture evidence.",
    )

    assert_readiness_blocked(service, session_id, session, "readiness evidence")


@pytest.mark.parametrize(
    ("scenario", "missing_key", "message"),
    [
        (
            "alignment_missing_loop_fit_readiness_evidence",
            "loop_fit",
            "Build a one-pass starter experience without proving Loopora is needed.",
        ),
        (
            "alignment_missing_residual_risk_readiness_evidence",
            "residual_risk_policy",
            "Build a starter experience without clarifying what risks can remain.",
        ),
        (
            "alignment_missing_execution_strategy_readiness_evidence",
            "execution_strategy",
            "Build a starter experience without deciding what the next rounds should prioritize.",
        ),
        (
            "alignment_missing_local_governance_readiness_evidence",
            "local_governance",
            "Build a starter experience without clarifying local governance responsibilities.",
        ),
    ],
)
def test_alignment_service_blocks_bundle_without_required_readiness_key(
    service_factory,
    sample_workdir: Path,
    scenario: str,
    missing_key: str,
    message: str,
) -> None:
    service, session_id, session = readiness_blocked_session(
        service_factory,
        sample_workdir,
        scenario=scenario,
        message=message,
    )

    assert_readiness_key_blocked(service, session_id, session, missing_key)

# Merged from test_alignment_service_task_scoped_readiness_blocks.py



def test_alignment_service_blocks_global_persona_readiness_evidence(
    service_factory,
    sample_workdir: Path,
) -> None:
    service, session_id, session = readiness_blocked_session(
        service_factory,
        sample_workdir,
        scenario="alignment_global_persona_readiness_evidence",
        message="Build a starter experience without turning task judgment into memory.",
    )

    assert not Path(session["bundle_path"]).exists()
    assert "task_scoped_judgment" in session["transcript"][-1]["content"]
    events = service.list_alignment_events(session_id)
    assert any(
        event["event_type"] in {"alignment_evidence_incomplete", "alignment_stage_blocked"}
        and (
            "task_scoped_judgment" in event["payload"].get("missing", [])
            or "task_scoped_judgment" in event["payload"].get("error", "")
        )
        for event in events
    )

# Merged from test_alignment_service_workdir_fact_grounding.py

from alignment_test_support import _wait_for_status


def test_alignment_service_blocks_invented_workdir_facts_readiness_evidence(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_invented_workdir_facts_readiness_evidence")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a starter experience without grounding workdir facts.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert "workdir_facts" in session["transcript"][-1]["content"]


def test_alignment_service_blocks_observed_stack_claims_not_in_workdir_snapshot(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_invented_observed_workdir_facts_readiness_evidence")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a starter experience without inventing stack facts.",
    )
    _wait_for_status(service, created["id"], "waiting_user")
    service.append_alignment_message(created["id"], "确认")
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert "workdir_facts" in session["transcript"][-1]["content"]
    prompt_text = (Path(session["artifact_dir"]) / "invocations" / "0001" / "prompt.md").read_text(encoding="utf-8")
    assert "package.json" not in prompt_text
    assert "tests/ exists: no" in prompt_text


def test_alignment_service_blocks_bundle_observed_stack_claims_not_in_workdir_snapshot(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_bundle_unsupported_observed_workdir_claim")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a starter experience without inventing stack facts in the final bundle.",
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert not session["validation"]["ok"]
    assert "bundle field spec.markdown must not claim an observed workdir stack" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_validation_failed"
        and "bundle field spec.markdown" in event["payload"].get("error", "")
        for event in events
    )

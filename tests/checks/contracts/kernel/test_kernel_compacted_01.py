from __future__ import annotations

# Merged from kernel/test_core_event_identity.py
from pathlib import Path

import pytest

from loopora.db import LooporaRepository
from loopora.events import loop_stream_id, run_stream_id
from loopora.events.store import DomainEventAppendRequest


def test_run_event_payload_run_id_must_match_aggregate_id(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_payload_identity_boundary"

    with pytest.raises(ValueError, match="payload run_id must match aggregate_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id(run_id),
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="RunStarted",
                payload={"run_id": "other_run"},
            )
        )


def test_loop_event_payload_loop_id_must_match_aggregate_id(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    loop_id = "loop_payload_identity_boundary"

    with pytest.raises(ValueError, match="payload loop_id must match aggregate_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=loop_stream_id(loop_id),
                aggregate_type="loop",
                aggregate_id=loop_id,
                event_type="LoopArchived",
                payload={"loop_id": "other_loop"},
            )
        )


def test_core_event_causation_id_must_reference_existing_event(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_unknown_causation_boundary"

    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id(run_id),
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": "loop_unknown_causation_boundary"},
        )
    )

    with pytest.raises(ValueError, match="causation_id must reference existing event"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id(run_id),
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="RunStarted",
                payload={"run_id": run_id},
                causation_id="event_missing",
            )
        )

# Merged from kernel/test_coverage_status_count_consistency_store.py




def test_domain_event_store_rejects_inconsistent_coverage_status_counts(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_coverage_counts_boundary"
    stream_id = run_stream_id(run_id)

    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": "loop_coverage_counts_boundary"},
        )
    )
    evidence_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="EvidenceAccepted",
            payload={"run_id": run_id, "evidence_id": "ev_counts", "verifies": ["target:done_when.proof:covered"]},
        )
    )
    with pytest.raises(ValueError, match="covered_target_count"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={"run_id": run_id, "status": "covered", "target_count": 2, "covered_target_count": 1},
                causation_id=evidence_event.event_id,
            )
        )
    with pytest.raises(ValueError, match="cannot include blocked"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="CoverageRecomputed",
                payload={"run_id": run_id, "status": "weak", "target_count": 2, "blocked_target_count": 1},
                causation_id=evidence_event.event_id,
            )
        )
    coverage_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="CoverageRecomputed",
            payload={"run_id": run_id, "status": "covered", "target_count": 1, "covered_target_count": 1},
            causation_id=evidence_event.event_id,
        )
    )

    assert coverage_event.payload["covered_target_count"] == 1
    assert [event.event_type for event in repository.list_domain_events(stream_id)] == [
        "RunCreated",
        "EvidenceAccepted",
        "CoverageRecomputed",
    ]

# Merged from kernel/test_current_step_projection_cache_guards.py
from current_step_projection_test_support import (
    CURRENT_STEP_CACHE_SOURCE_SEQUENCE,
    CurrentStepCacheRepository,
    current_step_cache_payload,
)
from loopora.events.projection_cache import current_step_projection_for_run


def test_current_step_projection_cache_hit_uses_latest_sequence_without_replaying_events() -> None:
    repository = CurrentStepCacheRepository(cached_payload=current_step_cache_payload(iteration=1))

    projection = current_step_projection_for_run(repository, "run_cached")

    assert projection["run_id"] == "run_cached"
    assert projection["step_id"] == "builder"
    assert projection["source_sequence"] == CURRENT_STEP_CACHE_SOURCE_SEQUENCE


def test_current_step_projection_ignores_cached_payload_for_different_run() -> None:
    repository = CurrentStepCacheRepository(
        cached_payload=current_step_cache_payload(run_id="other_run", step_id="wrong_builder"),
        refreshed_payload=current_step_cache_payload(),
    )

    projection = current_step_projection_for_run(repository, "run_cached")

    assert projection["run_id"] == "run_cached"
    assert projection["step_id"] == "builder"


def test_current_step_projection_ignores_cached_payload_with_wrong_kind() -> None:
    repository = CurrentStepCacheRepository(
        cached_payload=current_step_cache_payload(kind="not_current_step", step_id="wrong_builder"),
        refreshed_payload=current_step_cache_payload(),
    )

    projection = current_step_projection_for_run(repository, "run_cached")

    assert projection["run_id"] == "run_cached"
    assert projection["step_id"] == "builder"


def test_current_step_projection_ignores_future_source_sequence_cache() -> None:
    repository = CurrentStepCacheRepository(
        cached_payload=current_step_cache_payload(step_id="stale_builder", source_sequence=6),
        cached_source_sequence=6,
        refreshed_payload=current_step_cache_payload(source_sequence=CURRENT_STEP_CACHE_SOURCE_SEQUENCE),
    )

    projection = current_step_projection_for_run(repository, "run_cached")

    assert projection["run_id"] == "run_cached"
    assert projection["step_id"] == "builder"
    assert projection["source_sequence"] == CURRENT_STEP_CACHE_SOURCE_SEQUENCE

# Merged from kernel/test_current_step_projection_claim_replay.py

from loopora.events.projection_cache import replay_run_projections
from loopora.kernel import ActorRef

from current_step_projection_test_support import claim_builder_step, create_current_step_projection_run


def test_run_engine_replays_current_step_projection_from_claim_events(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_current_step_projection_run(repository, tmp_path)
    actor = ActorRef(kind="agent", id="codex", adapter="codex")
    claim_builder_step(repository, run, actor)

    projections = replay_run_projections(repository, run["id"])
    cached_current_step = repository.get_projection_record("current_step", run["id"])
    cached_step_surfaces = repository.get_projection_record("step_surfaces", run["id"])

    assert projections["run_snapshot"]["lifecycle_status"] == "awaiting_actor"
    assert projections["current_step"] == {
        "schema_version": 1,
        "kind": "event_replayed_current_step",
        "source_sequence": 4,
        "run_id": run["id"],
        "step_id": "builder",
        "iteration": 1,
        "pending_actor": actor.to_dict(),
        "claimable": True,
        "lifecycle_status": "awaiting_actor",
    }
    assert projections["step_surfaces"]["available"] is True
    assert projections["step_surfaces"]["agent_step_view"]["step_id"] == "builder"
    assert projections["step_surfaces"]["cli_summary"]["role_archetype"] == "builder"
    assert projections["step_surfaces"]["cli_step_summary"]["kind"] == "cli_step_summary"
    assert cached_current_step["payload"] == projections["current_step"]
    assert cached_step_surfaces["payload"] == projections["step_surfaces"]

# Merged from kernel/test_current_step_projection_malformed_iteration.py

from loopora.events.streams import run_stream_id  # noqa: F811 - compacted test keeps source-local import binding.



def test_run_projection_replay_keeps_prior_iteration_when_event_iteration_is_malformed(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_current_step_projection_run(repository, tmp_path)
    actor = ActorRef(kind="agent", id="codex", adapter="codex")
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id(run["id"]),
            aggregate_type="run",
            aggregate_id=run["id"],
            event_type="IterationStarted",
            payload={"run_id": run["id"], "iteration": "not-a-number", "step_count": 1},
            actor=actor,
        )
    )
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=run_stream_id(run["id"]),
            aggregate_type="run",
            aggregate_id=run["id"],
            event_type="StepInstructionIssued",
            payload={
                "run_id": run["id"],
                "step_id": "builder",
                "iteration": "still-not-a-number",
                "pending_actor": actor.to_dict(),
            },
            actor=actor,
        )
    )

    projections = replay_run_projections(repository, run["id"])

    assert projections["run_snapshot"]["current_iteration"] == 0
    assert projections["current_step"]["iteration"] == 0
    assert projections["current_step"]["step_id"] == "builder"

# Merged from kernel/test_domain_event_store_evidence_identity.py


from loopora.events import run_stream_id  # noqa: F811 - compacted test keeps source-local import binding.


def test_domain_event_store_rejects_accepted_evidence_without_identity(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run_id = "run_evidence_identity_boundary"
    stream_id = run_stream_id(run_id)

    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="RunCreated",
            payload={"run_id": run_id, "loop_id": "loop_evidence_identity_boundary"},
        )
    )
    with pytest.raises(ValueError, match="requires evidence_id"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="EvidenceAccepted",
                payload={"run_id": run_id, "claim": "Anonymous proof."},
            )
        )
    with pytest.raises(ValueError, match="requires at least one verifies"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id=run_id,
                event_type="EvidenceAccepted",
                payload={"run_id": run_id, "evidence_id": "ev_identity", "claim": "Unlinked proof."},
            )
        )
    evidence_event = repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id=run_id,
            event_type="EvidenceAccepted",
            payload={
                "run_id": run_id,
                "evidence_id": "ev_identity",
                "claim": "Named proof.",
                "verifies": ["target:done_when.proof:covered"],
            },
        )
    )

    assert evidence_event.payload["evidence_id"] == "ev_identity"
    assert [event.event_type for event in repository.list_domain_events(stream_id)] == ["RunCreated", "EvidenceAccepted"]

# Merged from kernel/test_domain_event_store_run_lifecycle_invariants.py




def test_domain_event_store_rejects_run_lifecycle_events_after_terminal(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    stream_id = run_stream_id("run_terminal_boundary")

    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id="run_terminal_boundary",
            event_type="RunCreated",
            payload={"run_id": "run_terminal_boundary", "loop_id": "loop_terminal_boundary"},
        )
    )
    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id="run_terminal_boundary",
            event_type="RunStopped",
            payload={"run_id": "run_terminal_boundary", "reason": "user_requested_stop"},
        )
    )

    with pytest.raises(ValueError, match="terminal run stream"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id="run_terminal_boundary",
                event_type="RunStarted",
                payload={"run_id": "run_terminal_boundary"},
            )
        )

    assert [event.event_type for event in repository.list_domain_events(stream_id)] == ["RunCreated", "RunStopped"]


def test_non_success_terminal_run_events_require_reason(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    stream_id = run_stream_id("run_terminal_reason_boundary")

    repository.append_domain_event(
        DomainEventAppendRequest(
            stream_id=stream_id,
            aggregate_type="run",
            aggregate_id="run_terminal_reason_boundary",
            event_type="RunCreated",
            payload={"run_id": "run_terminal_reason_boundary", "loop_id": "loop_terminal_reason_boundary"},
        )
    )

    with pytest.raises(ValueError, match="RunFailed requires reason"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=stream_id,
                aggregate_type="run",
                aggregate_id="run_terminal_reason_boundary",
                event_type="RunFailed",
                payload={"run_id": "run_terminal_reason_boundary"},
            )
        )

# Merged from kernel/test_domain_event_store_stream_identity.py




def test_domain_event_store_rejects_aggregate_type_mismatches(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")

    with pytest.raises(ValueError, match="requires aggregate_type loop"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id("run_wrong_loop_event"),
                aggregate_type="run",
                aggregate_id="run_wrong_loop_event",
                event_type="LoopArchived",
                payload={"loop_id": "loop_wrong"},
            )
        )
    with pytest.raises(ValueError, match="requires aggregate_type run"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=loop_stream_id("loop_wrong_run_event"),
                aggregate_type="loop",
                aggregate_id="loop_wrong_run_event",
                event_type="RunStarted",
                payload={"run_id": "run_wrong"},
            )
        )

    assert repository.list_domain_events(run_stream_id("run_wrong_loop_event")) == []
    assert repository.list_domain_events(loop_stream_id("loop_wrong_run_event")) == []


def test_domain_event_store_rejects_stream_id_mismatches(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")

    with pytest.raises(ValueError, match="requires stream_id run:run_stream_boundary"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=loop_stream_id("loop_wrong_stream"),
                aggregate_type="run",
                aggregate_id="run_stream_boundary",
                event_type="RunStarted",
                payload={"run_id": "run_stream_boundary"},
            )
        )
    with pytest.raises(ValueError, match="requires stream_id loop:loop_stream_boundary"):
        repository.append_domain_event(
            DomainEventAppendRequest(
                stream_id=run_stream_id("run_wrong_stream"),
                aggregate_type="loop",
                aggregate_id="loop_stream_boundary",
                event_type="LoopArchived",
                payload={"loop_id": "loop_stream_boundary"},
            )
        )

    assert repository.list_domain_events(loop_stream_id("loop_wrong_stream")) == []
    assert repository.list_domain_events(run_stream_id("run_wrong_stream")) == []

# Merged from kernel/test_event_replay_projection_architecture.py
from kernel_architecture_test_support import REPO_ROOT, loopora_source


def test_event_replay_projection_modules_are_split_by_read_model() -> None:
    projection_dir = REPO_ROOT / "src" / "loopora" / "projections"

    assert (projection_dir / "evidence_ledger.py").exists()
    assert (projection_dir / "evidence_coverage.py").exists()
    assert (projection_dir / "run_snapshot.py").exists()
    assert (projection_dir / "current_step.py").exists()
    assert (projection_dir / "loop_definition.py").exists()
    assert (projection_dir / "task_verdict.py").exists()
    assert (projection_dir / "audit_timeline.py").exists()


def test_event_core_owns_projection_cache_replay_writes() -> None:
    cache_source = loopora_source("events/projection_cache.py")
    loop_records_source = loopora_source("db_loop_records.py")
    run_state_records_source = loopora_source("db_run_state_records.py")
    run_snapshot_source = loopora_source("engine/run_snapshot_source.py")
    engine_projection_cache = REPO_ROOT / "src" / "loopora" / "engine" / "run_projection_cache.py"

    assert "replay_loop_projection_bundle" in cache_source
    assert "replay_run_projection_bundle" in cache_source
    assert "current_step_projection_for_run" in cache_source
    assert "run_snapshot_projection_for_run" in cache_source
    assert not engine_projection_cache.exists()
    assert "put_projection_record_for_connection" in cache_source
    assert "SELECT * FROM event_store" not in loop_records_source
    assert "SELECT * FROM event_store" not in run_state_records_source
    assert "_put_projection_record_for_connection" not in loop_records_source
    assert "_put_projection_record_for_connection" not in run_state_records_source
    assert "replay_loop_definition_projection" not in loop_records_source
    assert "replay_run_projection_bundle" not in run_state_records_source
    assert "get_projection_record" not in run_snapshot_source
    assert "list_domain_events" not in run_snapshot_source

# Merged from kernel/test_event_replay_task_verdict_projection.py

from loopora.engine import (
    RepositoryRunEngine,
    RunEngineAcceptEvidenceRequest,
    RunEngineCoverageRecomputedRequest,
    RunEngineIssueVerdictRequest,
)

from event_replay_evidence_verdict_projection_support import create_event_projection_run


def test_run_engine_replays_rich_task_verdict_projection(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    run = create_event_projection_run(repository, tmp_path)
    engine = RepositoryRunEngine(repository)
    actor = ActorRef(kind="system", id="verdict-engine")

    engine.accept_evidence(
        RunEngineAcceptEvidenceRequest(
            run_id=run["id"],
            actor=actor,
            evidence_entry={
                "id": "ev_checks",
                "step_id": "builder",
                "role_id": "builder",
                "claim": "Automated checks passed.",
                "result": "passed",
                "verifies": ["target:done_when.proof:covered"],
            },
        )
    )
    engine.recompute_coverage(
        RunEngineCoverageRecomputedRequest(
            run_id=run["id"],
            actor=actor,
            coverage_projection={
                "status": "weak",
                "target_count": 2,
                "covered_target_count": 1,
                "weak_target_count": 1,
                "top_gaps": [{"target_id": "done_when.manual_export", "status": "weak"}],
            },
        )
    )
    engine.issue_verdict(
        RunEngineIssueVerdictRequest(
            run_id=run["id"],
            actor=actor,
            verdict={
                "status": "passed_with_residual_risk",
                "source": "gatekeeper",
                "summary": "Accepted with a named follow-up.",
                "buckets": {
                    "proven": [{"label": "Automated checks passed.", "evidence_refs": ["ev_checks"]}],
                    "residual_risk": [{"label": "Manual export remains.", "managed": True}],
                },
            },
        )
    )

    projection = replay_run_projections(repository, run["id"])["task_verdict"]
    cached = repository.get_projection_record("task_verdict", run["id"])

    assert projection["status"] == "passed_with_residual_risk"
    assert projection["buckets"]["proven"] == [{"label": "Automated checks passed.", "evidence_refs": ["ev_checks"]}]
    assert projection["buckets"]["residual_risk"] == [{"label": "Manual export remains.", "managed": True}]
    assert "next_gap" not in projection
    assert cached["payload"] == projection

# Merged from kernel/test_loop_compiler_source_dispatch.py

from loopora.compiler import LoopCompiler, LoopSource, LoopSourceKind


def test_loop_compiler_contract_covers_current_source_kinds() -> None:
    assert set(LoopSourceKind) == {
        LoopSourceKind.AGENT_MESSAGE,
        LoopSourceKind.WEB_ALIGNMENT,
        LoopSourceKind.MARKDOWN_CONTRACT,
        LoopSourceKind.LOOPFILE,
        LoopSourceKind.STRATEGY_TEMPLATE,
        LoopSourceKind.EXISTING_LOOP_RECORD,
    }


def test_loop_compiler_accepts_explicit_source_boundary() -> None:
    source = LoopSource(
        kind=LoopSourceKind.EXISTING_LOOP_RECORD,
        payload={
            "id": "loop_source",
            "name": "Source Loop",
            "compiled_spec": {"goal": "Compile through source.", "checks": []},
            "workflow": {"roles": [], "steps": []},
        },
    )

    definition = LoopCompiler().compile(source)

    assert definition.id == "loop_source"
    assert definition.metadata.source_kind == "existing_loop_record"


def test_loop_compiler_rejects_unknown_source_kinds() -> None:
    with pytest.raises(ValueError, match="unsupported Loop source kind"):
        LoopCompiler().compile(LoopSource(kind="unknown", payload={}))

# Merged from kernel/test_loop_creation_domain_events.py


from loop_event_core_test_support import create_loop, gatekeeper_loop_spec


def test_loop_creation_emits_compiler_and_activation_domain_events(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    create_loop(
        repository,
        tmp_path,
        gatekeeper_loop_spec(
            loop_id="loop_event_stream",
            name="Loop Event Stream",
            task="Prove loop events.",
        ),
    )

    events = repository.list_domain_events(loop_stream_id("loop_event_stream"))

    assert [event.event_type for event in events] == ["LoopContractCompiled", "LoopStrategyCompiled", "LoopActivated"]
    assert [event.sequence for event in events] == [1, 2, 3]
    assert events[0].payload == {
        "loop_id": "loop_event_stream",
        "name": "Loop Event Stream",
        "task": "Prove loop events.",
        "completion_mode": "gatekeeper",
        "check_count": 1,
        "coverage_target_count": 2,
        "reason": "created",
    }
    assert events[1].payload["finish_step_ids"] == ["judge"]
    assert events[1].causation_id == events[0].event_id
    assert events[2].causation_id == events[1].event_id

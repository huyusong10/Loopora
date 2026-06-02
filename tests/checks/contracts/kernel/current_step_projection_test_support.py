from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.engine import (
    RepositoryRunEngine,
    RunEngineClaimStepRequest,
    RunnerStepInstructionRequest,
    runner_step_instruction,
)
from loopora.events.streams import run_stream_id
from loopora.kernel import ActorRef

from kernel_event_test_support import create_kernel_run


CURRENT_STEP_CACHE_SOURCE_SEQUENCE = 5


def create_current_step_projection_run(repository: LooporaRepository, tmp_path: Path) -> dict:
    return create_kernel_run(
        repository,
        tmp_path,
        {
            "run_id": "run_current_step_projection",
            "loop_id": "loop_current_step_projection",
            "loop_name": "Current Step Projection Loop",
            "task": "Prove current-step projection.",
        },
    )


def claim_builder_step(repository: LooporaRepository, run: dict, actor: ActorRef) -> None:
    engine = RepositoryRunEngine(repository)
    instruction = runner_step_instruction(
        RunnerStepInstructionRequest(
            run_id=run["id"],
            contract_ref="contract/run_contract.json",
            compiled_spec={"coverage_targets": [{"id": "done_when.proof"}]},
            iteration=1,
            step={"id": "builder", "role_id": "builder", "objective": "Build proof."},
            role={"id": "builder", "name": "Builder", "archetype": "builder"},
        )
    )
    engine.claim_step(RunEngineClaimStepRequest(instruction=instruction, pending_actor=actor))


def current_step_cache_payload(
    *,
    run_id: str = "run_cached",
    step_id: str = "builder",
    kind: str = "event_replayed_current_step",
    source_sequence: int = CURRENT_STEP_CACHE_SOURCE_SEQUENCE,
    iteration: int | None = None,
) -> dict:
    payload = {
        "schema_version": 1,
        "kind": kind,
        "run_id": run_id,
        "step_id": step_id,
        "claimable": True,
        "source_sequence": source_sequence,
    }
    if iteration is not None:
        payload["iteration"] = iteration
    return payload


class CurrentStepCacheRepository:
    def __init__(
        self,
        *,
        cached_payload: dict,
        cached_source_sequence: int = CURRENT_STEP_CACHE_SOURCE_SEQUENCE,
        latest_sequence: int = CURRENT_STEP_CACHE_SOURCE_SEQUENCE,
        refreshed_payload: dict | None = None,
    ) -> None:
        self.cached_payload = cached_payload
        self.cached_source_sequence = cached_source_sequence
        self.latest_sequence = latest_sequence
        self.refreshed_payload = refreshed_payload

    def latest_domain_event_sequence(self, stream_id: str) -> int:
        assert stream_id == run_stream_id("run_cached")
        return self.latest_sequence

    def get_projection_record(self, projection_name: str, projection_key: str) -> dict:
        assert projection_name == "current_step"
        assert projection_key == "run_cached"
        return {
            "source_sequence": self.cached_source_sequence,
            "payload": self.cached_payload,
        }

    def refresh_run_projection_cache(self, run_id: str) -> dict:
        assert run_id == "run_cached"
        if self.refreshed_payload is None:
            raise AssertionError(f"cache hit should not rebuild projections for {run_id}")
        return {"current_step": self.refreshed_payload}

    def list_domain_events(self, stream_id: str):  # pragma: no cover - failure path for this contract.
        raise AssertionError(f"current-step source should rebuild through projection cache for {stream_id}")

from __future__ import annotations

from loopora.compiler.loop_compiler import compile_existing_loop_record
from loopora.events.append_requests import LoopEventAppend, append_loop_event


def append_loop_definition_events_for_connection(
    event_repository,
    connection,
    payload: dict,
    *,
    reason: str,
    activate: bool,
) -> None:
    loop_id = str(payload.get("id") or "")
    definition = compile_existing_loop_record(payload)
    event_transaction = event_repository.domain_event_transaction_for_connection(connection)
    contract_event = append_loop_event(
        event_transaction,
        LoopEventAppend(
            loop_id=loop_id,
            event_type="LoopContractCompiled",
            payload=_loop_contract_compiled_payload(definition, reason=reason),
        ),
    )
    strategy_event = append_loop_event(
        event_transaction,
        LoopEventAppend(
            loop_id=loop_id,
            event_type="LoopStrategyCompiled",
            payload=_loop_strategy_compiled_payload(definition, reason=reason),
            correlation_id=contract_event.correlation_id,
            causation_id=contract_event.event_id,
        ),
    )
    if activate:
        append_loop_event(
            event_transaction,
            LoopEventAppend(
                loop_id=loop_id,
                event_type="LoopActivated",
                payload={
                    "loop_id": loop_id,
                    "workdir": str(payload.get("workdir") or ""),
                    "completion_mode": str(payload.get("completion_mode") or "gatekeeper"),
                    "reason": reason,
                },
                correlation_id=contract_event.correlation_id,
                causation_id=strategy_event.event_id,
            ),
        )


def append_loop_archived_event_for_connection(event_repository, connection, loop_id: str, *, reason: str) -> None:
    append_loop_event(
        event_repository.domain_event_transaction_for_connection(connection),
        LoopEventAppend(
            loop_id=loop_id,
            event_type="LoopArchived",
            payload={
                "loop_id": loop_id,
                "reason": reason,
            },
        ),
    )


def _loop_contract_compiled_payload(definition, *, reason: str) -> dict:
    return {
        "loop_id": definition.id,
        "name": definition.name,
        "task": definition.contract.task,
        "completion_mode": definition.runtime_defaults.completion_mode,
        "check_count": len(definition.contract.done_when),
        "coverage_target_count": len(definition.contract.evidence_targets),
        "reason": reason,
    }


def _loop_strategy_compiled_payload(definition, *, reason: str) -> dict:
    return {
        "loop_id": definition.id,
        "role_count": len(definition.strategy.roles),
        "step_count": len(definition.strategy.steps),
        "finish_step_ids": [step.id for step in definition.strategy.steps if step.can_finish_run],
        "max_iterations": definition.strategy.iteration_policy.max_iterations,
        "max_step_retries": definition.strategy.iteration_policy.max_step_retries,
        "reason": reason,
    }

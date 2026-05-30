from __future__ import annotations

import json
import logging

from loopora.db_shared import logger
from loopora.diagnostics import log_event
from loopora.compiler import compile_existing_loop_record
from loopora.events.store import DomainEventAppendRequest
from loopora.events.streams import loop_stream_id
from loopora.projections import replay_loop_definition_projection
from loopora.utils import utc_now


class RepositoryLoopRecordsMixin:
    def create_loop(self, payload: dict) -> dict:
        now = utc_now()
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO loop_definitions (
                    id, name, orchestration_id, orchestration_name, workdir, spec_path, spec_markdown, compiled_spec_json,
                    executor_kind, executor_mode, command_cli, command_args_text,
                    model, reasoning_effort, completion_mode, iteration_interval_seconds,
                    max_iters, max_role_retries, delta_threshold,
                    trigger_window, regression_window, role_models_json, workflow_json, latest_run_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    payload["id"],
                    payload["name"],
                    payload.get("orchestration_id", ""),
                    payload.get("orchestration_name", ""),
                    payload["workdir"],
                    payload["spec_path"],
                    payload["spec_markdown"],
                    json.dumps(payload["compiled_spec"], ensure_ascii=False),
                    payload.get("executor_kind", "codex"),
                    payload.get("executor_mode", "preset"),
                    payload.get("command_cli", ""),
                    payload.get("command_args_text", ""),
                    payload["model"],
                    payload["reasoning_effort"],
                    payload.get("completion_mode", "gatekeeper"),
                    payload.get("iteration_interval_seconds", 0.0),
                    payload["max_iters"],
                    payload["max_role_retries"],
                    payload["delta_threshold"],
                    payload["trigger_window"],
                    payload["regression_window"],
                    json.dumps(payload.get("role_models", {}), ensure_ascii=False),
                    json.dumps(payload.get("workflow", {}), ensure_ascii=False),
                    now,
                    now,
                ),
            )
            self._append_loop_definition_events_for_connection(
                connection,
                payload,
                reason="created",
                activate=True,
            )
            self._refresh_loop_definition_projection_for_connection(connection, payload["id"])
        loop = self.get_loop(payload["id"])
        log_event(
            logger,
            logging.INFO,
            "db.loop.created",
            "Persisted loop definition",
            loop_id=payload["id"],
            orchestration_id=payload.get("orchestration_id", ""),
            workdir=payload["workdir"],
            loop_name=payload["name"],
        )
        return loop

    def get_loop(self, loop_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM loop_definitions WHERE id = ?", (loop_id,)).fetchone()
        return self._decode_row(row) if row else None

    def update_loop_contract(self, loop_id: str, payload: dict) -> dict | None:
        now = utc_now()
        with self.transaction() as connection:
            row = connection.execute("SELECT * FROM loop_definitions WHERE id = ?", (loop_id,)).fetchone()
            if row is None:
                return None
            existing = self._decode_row(row)
            connection.execute(
                """
                UPDATE loop_definitions
                SET orchestration_id = ?, orchestration_name = ?, spec_path = ?, spec_markdown = ?,
                    compiled_spec_json = ?, workflow_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    payload.get("orchestration_id", ""),
                    payload.get("orchestration_name", ""),
                    payload["spec_path"],
                    payload["spec_markdown"],
                    json.dumps(payload["compiled_spec"], ensure_ascii=False),
                    json.dumps(payload["workflow"], ensure_ascii=False),
                    now,
                    loop_id,
                ),
            )
            self._append_loop_definition_events_for_connection(
                connection,
                {
                    **payload,
                    "id": loop_id,
                    "name": existing.get("name", ""),
                    "workdir": existing.get("workdir", ""),
                    "completion_mode": existing.get("completion_mode", "gatekeeper"),
                    "max_iters": existing.get("max_iters", 0),
                    "max_role_retries": existing.get("max_role_retries", 0),
                },
                reason="updated",
                activate=False,
            )
            self._refresh_loop_definition_projection_for_connection(connection, loop_id)
        loop = self.get_loop(loop_id)
        log_event(
            logger,
            logging.INFO,
            "db.loop.contract_updated",
            "Updated persisted loop contract snapshot",
            loop_id=loop_id,
            orchestration_id=payload.get("orchestration_id", ""),
        )
        return loop

    def list_loops(self) -> list[dict]:
        query = """
            SELECT
                l.*,
                r.status AS latest_status,
                r.current_iter AS latest_current_iter,
                r.started_at AS latest_started_at,
                r.finished_at AS latest_finished_at,
                r.updated_at AS latest_run_updated_at,
                r.summary_md AS latest_summary_md,
                r.last_verdict_json AS latest_verdict_json,
                r.task_verdict_json AS latest_task_verdict_json
            FROM loop_definitions l
            LEFT JOIN loop_runs r ON r.id = l.latest_run_id
            ORDER BY l.updated_at DESC
        """
        with self._connect() as connection:
            rows = connection.execute(query).fetchall()
        return [self._decode_row(row) for row in rows]

    def delete_loop(self, loop_id: str) -> bool:
        with self.transaction() as connection:
            row = connection.execute("SELECT 1 FROM loop_definitions WHERE id = ?", (loop_id,)).fetchone()
            if row is None:
                return False
            self._append_loop_archived_event_for_connection(connection, loop_id, reason="deleted")
            self._refresh_loop_definition_projection_for_connection(connection, loop_id)
            connection.execute(
                "DELETE FROM run_events WHERE run_id IN (SELECT id FROM loop_runs WHERE loop_id = ?)",
                (loop_id,),
            )
            connection.execute(
                "DELETE FROM workdir_locks WHERE run_id IN (SELECT id FROM loop_runs WHERE loop_id = ?)",
                (loop_id,),
            )
            connection.execute("DELETE FROM loop_runs WHERE loop_id = ?", (loop_id,))
            connection.execute("DELETE FROM loop_definitions WHERE id = ?", (loop_id,))
        log_event(
            logger,
            logging.INFO,
            "db.loop.deleted",
            "Deleted loop definition and related records",
            loop_id=loop_id,
        )
        return True

    def _append_loop_definition_events_for_connection(
        self,
        connection,
        payload: dict,
        *,
        reason: str,
        activate: bool,
    ) -> None:
        loop_id = str(payload.get("id") or "")
        definition = compile_existing_loop_record(payload)
        contract_event = self._append_domain_event_for_connection(
            connection,
            DomainEventAppendRequest(
                stream_id=loop_stream_id(loop_id),
                aggregate_type="loop",
                aggregate_id=loop_id,
                event_type="LoopContractCompiled",
                payload=_loop_contract_compiled_payload(definition, reason=reason),
            ),
        )
        strategy_event = self._append_domain_event_for_connection(
            connection,
            DomainEventAppendRequest(
                stream_id=loop_stream_id(loop_id),
                aggregate_type="loop",
                aggregate_id=loop_id,
                event_type="LoopStrategyCompiled",
                payload=_loop_strategy_compiled_payload(definition, reason=reason),
                correlation_id=contract_event.correlation_id,
                causation_id=contract_event.event_id,
            ),
        )
        if activate:
            self._append_domain_event_for_connection(
                connection,
                DomainEventAppendRequest(
                    stream_id=loop_stream_id(loop_id),
                    aggregate_type="loop",
                    aggregate_id=loop_id,
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

    def _append_loop_archived_event_for_connection(self, connection, loop_id: str, *, reason: str) -> None:
        self._append_domain_event_for_connection(
            connection,
            DomainEventAppendRequest(
                stream_id=loop_stream_id(loop_id),
                aggregate_type="loop",
                aggregate_id=loop_id,
                event_type="LoopArchived",
                payload={
                    "loop_id": loop_id,
                    "reason": reason,
                },
            ),
        )

    def _refresh_loop_definition_projection_for_connection(self, connection, loop_id: str) -> None:
        rows = connection.execute(
            """
            SELECT * FROM event_store
            WHERE stream_id = ?
            ORDER BY sequence ASC
            """,
            (loop_stream_id(loop_id),),
        ).fetchall()
        projection = replay_loop_definition_projection([self._domain_event_from_row(row) for row in rows])
        self._put_projection_record_for_connection(
            connection,
            "loop_definition",
            loop_id,
            source_sequence=int(projection.get("source_sequence") or 0),
            payload=projection,
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

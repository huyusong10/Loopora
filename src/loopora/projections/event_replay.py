from __future__ import annotations

from loopora.events.envelope import EventEnvelope
from loopora.projections.audit_timeline import replay_audit_timeline_projection
from loopora.projections.current_step import replay_current_step_projection
from loopora.projections.evidence_coverage import replay_coverage_projection
from loopora.projections.evidence_ledger import replay_evidence_ledger_projection
from loopora.projections.loop_definition import replay_loop_definition_projection
from loopora.projections.run_snapshot import replay_run_snapshot_projection
from loopora.projections.step_instruction import replay_step_surfaces_projection
from loopora.projections.task_verdict import replay_task_verdict_projection


def replay_run_projection_bundle(events: list[EventEnvelope]) -> dict:
    return {
        "run_snapshot": replay_run_snapshot_projection(events),
        "current_step": replay_current_step_projection(events),
        "evidence_ledger": replay_evidence_ledger_projection(events),
        "coverage": replay_coverage_projection(events),
        "task_verdict": replay_task_verdict_projection(events),
        "step_surfaces": replay_step_surfaces_projection(events),
        "audit_timeline": replay_audit_timeline_projection(events),
    }


def replay_loop_projection_bundle(events: list[EventEnvelope]) -> dict:
    return {
        "loop_definition": replay_loop_definition_projection(events),
        "audit_timeline": replay_audit_timeline_projection(events),
    }

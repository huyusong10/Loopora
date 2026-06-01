from __future__ import annotations

import sqlite3

from loopora.events.invariants.causation import (
    require_evidence_linked_to_target_causation,
    require_passable_coverage_has_evidence_causation,
    require_next_gap_selected_causation,
    require_residual_risk_accepted_causation,
    require_run_closed_causation_references_passing_verdict,
    require_step_result_event_causation,
    require_strategy_advanced_causation,
    require_verdict_closure_causation,
    require_verdict_has_coverage_causation,
)
from loopora.events.invariants.coverage import (
    require_coverage_payload_status_consistency,
    require_coverage_top_gaps_shape,
)
from loopora.events.invariants.evidence import (
    require_evidence_accepted_identity,
    require_evidence_linked_to_target_identity,
    require_evidence_verified_evidence_refs_are_accepted,
)
from loopora.events.invariants.lifecycle import require_run_lifecycle_append_allowed
from loopora.events.invariants.step import require_step_claim_event_identity, require_step_result_event_identity
from loopora.events.invariants.verdict import (
    require_blocked_coverage_has_blocked_verdict,
    require_next_gap_selected_shape,
    require_passed_with_residual_risk_has_managed_risk,
    require_passing_verdict_has_no_next_gap,
    require_passing_verdict_has_passable_coverage,
    require_residual_risk_accepted_shape,
    require_verdict_evidence_refs_are_accepted,
    require_verdict_next_gap_shape,
    require_verdict_status_known,
)
from loopora.events.store import DomainEventAppendRequest


def require_run_event_append_invariants(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    require_run_lifecycle_append_allowed(connection, request)
    require_run_closed_causation_references_passing_verdict(connection, request)
    require_step_claim_event_identity(request)
    require_step_result_event_identity(request)
    require_step_result_event_causation(connection, request)
    require_evidence_accepted_identity(request)
    require_evidence_linked_to_target_identity(request)
    require_evidence_verified_evidence_refs_are_accepted(connection, request)
    require_evidence_linked_to_target_causation(connection, request)
    require_coverage_payload_status_consistency(request)
    require_coverage_top_gaps_shape(request)
    require_passable_coverage_has_evidence_causation(connection, request)
    require_verdict_has_coverage_causation(connection, request)
    require_verdict_closure_causation(connection, request)
    require_next_gap_selected_causation(connection, request)
    require_residual_risk_accepted_causation(connection, request)
    require_strategy_advanced_causation(connection, request)
    require_verdict_status_known(request)
    require_verdict_evidence_refs_are_accepted(connection, request)
    require_verdict_next_gap_shape(request)
    require_next_gap_selected_shape(request)
    require_residual_risk_accepted_shape(request)
    require_passing_verdict_has_no_next_gap(request)
    require_blocked_coverage_has_blocked_verdict(connection, request)
    require_passing_verdict_has_passable_coverage(connection, request)
    require_passed_with_residual_risk_has_managed_risk(request)

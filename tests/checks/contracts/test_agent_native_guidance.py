from __future__ import annotations

from loopora.agent_native_guidance import actionable_blocking_item
from loopora.service_agent_native_contracts import agent_native_actionable_blocking_item


def test_agent_native_blocking_summaries_explain_contract_target_tokens() -> None:
    expected = "check_001: required check id; see required_coverage.missing_check_ids and top_coverage_gaps for the contract text"

    assert actionable_blocking_item("check_001") == expected
    assert agent_native_actionable_blocking_item("check_001") == expected
    assert actionable_blocking_item("done_when.check_001").startswith("done_when.check_001: coverage target id")
    assert agent_native_actionable_blocking_item("gatekeeper.finish").startswith("gatekeeper.finish: GateKeeper finish target")

from __future__ import annotations

import json
from types import SimpleNamespace

from loopora.agent_native_parallel_groups import agent_native_parallel_group_snapshot
from loopora.run_artifacts import RunArtifactLayout


def test_parallel_group_snapshot_rebuilds_when_cached_numeric_identity_is_bool(tmp_path) -> None:
    layout = RunArtifactLayout(tmp_path / "run")
    layout.evidence_ledger_path.parent.mkdir(parents=True)
    layout.evidence_ledger_path.write_text(
        "\n".join(
            json.dumps(item)
            for item in [
                {"id": "malformed_bool_iter", "iter": True, "step_id": "peer_a"},
                {"id": "current_peer", "iter": 1, "step_id": "peer_b"},
                {"id": "builder", "iter": 1, "step_id": "builder_step"},
            ]
        ),
        encoding="utf-8",
    )
    state = {
        "parallel_group_snapshot": {
            "iter_id": True,
            "parallel_group": "inspection_pack",
            "group_start": 0,
            "group_end": 2,
            "current_outputs_by_step": {"stale": {"from": "bool-cache"}},
        }
    }
    context = SimpleNamespace(
        layout=layout,
        strategy_steps=[
            {"id": "peer_a", "role_id": "inspector_a", "parallel_group": "inspection_pack"},
            {"id": "peer_b", "role_id": "inspector_b", "parallel_group": "inspection_pack"},
        ],
        role_by_id={
            "inspector_a": {"id": "inspector_a", "archetype": "inspector"},
            "inspector_b": {"id": "inspector_b", "archetype": "inspector"},
        },
    )
    iteration = SimpleNamespace(
        iter_id=1,
        current_outputs_by_step={"builder_step": {"ok": True}, "peer_a": {"peer": True}},
        current_outputs_by_role={},
        current_outputs_by_archetype={},
        current_handoffs=[],
    )

    snapshot = agent_native_parallel_group_snapshot(
        state,
        context,
        iteration,
        0,
        "inspection_pack",
        runtime_role_key=lambda role: str(role["id"]),
    )

    assert snapshot["iter_id"] == 1
    assert snapshot["current_outputs_by_step"] == {"builder_step": {"ok": True}}
    assert [item["id"] for item in snapshot["evidence_items"]] == ["malformed_bool_iter", "builder"]

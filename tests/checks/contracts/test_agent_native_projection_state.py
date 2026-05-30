from __future__ import annotations

from loopora.agent_native_projection_state import agent_native_active_step_is_stale


def test_agent_native_active_step_cache_matches_current_step_projection() -> None:
    active = {
        "step": {"id": "builder"},
        "iter_id": 1,
        "capsule": {"step_id": "builder", "adapter": "codex"},
    }
    projection = {
        "source_sequence": 4,
        "claimable": True,
        "step_id": "builder",
        "iteration": 1,
        "pending_actor": {"kind": "agent", "id": "codex", "adapter": "codex"},
    }

    assert agent_native_active_step_is_stale(active, projection) is False


def test_agent_native_active_step_cache_preserves_zero_iteration() -> None:
    active = {
        "step": {"id": "builder"},
        "iter_id": 0,
        "capsule": {"step_id": "builder", "adapter": "codex"},
    }
    projection = {
        "source_sequence": 4,
        "claimable": True,
        "step_id": "builder",
        "iteration": 0,
        "pending_actor": {"kind": "agent", "id": "codex", "adapter": "codex"},
    }

    assert agent_native_active_step_is_stale(active, projection) is False


def test_agent_native_active_step_cache_is_stale_when_projection_moves_on() -> None:
    active = {
        "step": {"id": "builder"},
        "iter_id": 1,
        "capsule": {"step_id": "builder"},
    }
    projection = {
        "source_sequence": 5,
        "claimable": True,
        "step_id": "gatekeeper",
        "iteration": 1,
    }

    assert agent_native_active_step_is_stale(active, projection) is True


def test_agent_native_active_step_cache_is_stale_when_pending_actor_changes() -> None:
    active = {
        "step": {"id": "builder"},
        "iter_id": 1,
        "capsule": {"step_id": "builder", "adapter": "codex"},
    }
    projection = {
        "source_sequence": 5,
        "claimable": True,
        "step_id": "builder",
        "iteration": 1,
        "pending_actor": {"kind": "agent", "id": "claude", "adapter": "claude"},
    }

    assert agent_native_active_step_is_stale(active, projection) is True


def test_agent_native_active_step_cache_is_stale_when_iteration_values_are_malformed() -> None:
    active = {
        "step": {"id": "builder"},
        "iter_id": "not-an-int",
        "capsule": {"step_id": "builder", "adapter": "codex"},
    }
    projection = {
        "source_sequence": 5,
        "claimable": True,
        "step_id": "builder",
        "iteration": 1,
        "pending_actor": {"kind": "agent", "id": "codex", "adapter": "codex"},
    }

    assert agent_native_active_step_is_stale(active, projection) is True


def test_agent_native_active_step_cache_is_stale_when_projection_has_no_claimable_step() -> None:
    active = {
        "step": {"id": "builder"},
        "iter_id": 1,
        "capsule": {"step_id": "builder"},
    }
    projection = {
        "source_sequence": 6,
        "claimable": False,
        "step_id": None,
        "iteration": 1,
    }

    assert agent_native_active_step_is_stale(active, projection) is True


def test_agent_native_active_step_cache_ignores_missing_projection_during_legacy_transition() -> None:
    active = {
        "step": {"id": "builder"},
        "iter_id": 1,
        "capsule": {"step_id": "builder"},
    }

    assert agent_native_active_step_is_stale(active, {}) is False

from __future__ import annotations

from runner_agent_native_architecture_support import (
    REPO_ROOT,
    SRC_ROOT,
    agent_native_claim_source,
    source,
)


def test_headless_and_agent_share_runner_step_runtime_request_boundary() -> None:
    runner_source = source("service_runner_step_execution.py")
    agent_source = agent_native_claim_source()
    agent_runtime_step_source = source("agent_native_claim_runtime_step.py")
    request_source = source("runner_step_runtime_requests.py")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.runner_step_runtime_requests import" in runner_source
    assert "from loopora.agent_native_claim_runtime_step import" in agent_source
    assert "from loopora.runner_step_runtime_requests import" in agent_runtime_step_source
    assert "def build_runner_step_runtime_request" in request_source
    assert "class RunnerStepRuntimeInputSnapshot" in request_source
    assert "class RunnerStepRuntimeRequestBuildRequest" in request_source
    assert "structured_non_negative_int" in request_source
    for source_text in (runner_source, agent_runtime_step_source):
        assert "RunnerStepRuntimeRequest(" not in source_text
        assert "build_runner_step_runtime_request(" in source_text
        assert "structured_non_negative_int" not in source_text
    assert "runner_step_runtime_requests.py" in contracts_source


def test_agent_native_treats_active_step_state_as_projection_checked_cache() -> None:
    agent_source = agent_native_claim_source()
    active_step_source = source("agent_native_claim_active_step.py")
    projection_cache_source = source("events", "projection_cache.py")
    forbidden = (".current_step_projection(", "AgentNativeCapsuleRequest", "submit_context.context_packet")
    legacy_capsule_paths = [SRC_ROOT / name for name in ("agent_native_capsule.py", "agent_native_capsule_context.py")]

    assert all(item in active_step_source for item in ["agent_native_active_step_is_stale", "agent_native_step_view"])
    assert all(item not in agent_source for item in forbidden)
    assert all(not path.exists() for path in legacy_capsule_paths)
    assert "refresh_agent_native_capsule_with" not in agent_source
    assert "def _agent_native_capsule(" not in agent_source
    assert all(item in agent_source for item in ["current_step_projection_for_run", "AgentNativeStepViewRequest"])
    assert 'kind="event_replayed_current_step"' in projection_cache_source
    assert "get_projection_record(projection_name, run_id)" in projection_cache_source

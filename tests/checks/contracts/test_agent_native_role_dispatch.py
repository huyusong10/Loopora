from __future__ import annotations

from loopora.agent_native_role_dispatch import (
    agent_native_role_dispatch,
    agent_native_target_agent,
    agent_native_target_agent_config_path,
    agent_native_template_role_dispatch,
    agent_native_trace_contract,
)


def test_agent_native_role_dispatch_maps_role_archetypes_to_host_agent_entries(tmp_path) -> None:
    assert agent_native_target_agent("builder") == "loopora-builder"
    assert agent_native_target_agent("gatekeeper") == "loopora-gatekeeper"
    assert agent_native_target_agent("guide") == "loopora-guide"
    assert agent_native_target_agent("inspector") == "loopora-inspector"
    assert agent_native_target_agent("custom-review") == "loopora-inspector"

    assert agent_native_target_agent_config_path("codex", "loopora-builder") == ".codex/agents/loopora-builder.toml"
    assert agent_native_target_agent_config_path("claude", "loopora-builder") == ".claude/agents/loopora-builder.md"
    assert agent_native_target_agent_config_path("opencode", "loopora-builder") == ".opencode/agents/loopora-builder.md"
    assert agent_native_target_agent_config_path("unknown", "loopora-builder") == ""
    assert agent_native_target_agent_config_path("codex", "") == ""

    dispatch = agent_native_role_dispatch(adapter="codex", role_archetype="builder", workdir_path=tmp_path)

    assert dispatch["required"] is True
    assert dispatch["dispatch_contract"] == "host_native_subagent"
    assert dispatch["target_agent"] == "loopora-builder"
    assert dispatch["target_agent_config_path"] == ".codex/agents/loopora-builder.toml"
    assert dispatch["target_agent_config_absolute_path"].endswith(".codex/agents/loopora-builder.toml")
    assert dispatch["target_agent_config_exists"] is False
    assert dispatch["target_role_archetype"] == "builder"
    assert dispatch["inline_allowed"] is False
    assert dispatch["proof_field"] == "loopora_host_dispatch"
    assert dispatch["result_field"] == "result"
    assert dispatch["accepted_dispatch_modes"] == ["host_subagent", "host_task", "host_agent"]
    assert dispatch["host_mechanism"] == "Codex spawn_agent with agent_type=<role_dispatch.target_agent>"
    assert dispatch["accepted_native_tools"] == ["spawn_agent"]
    assert dispatch["native_trace_contract"] == agent_native_trace_contract()


def test_agent_native_role_dispatch_reports_config_availability(tmp_path) -> None:
    config_path = tmp_path / ".opencode" / "agents" / "loopora-gatekeeper.md"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("name: loopora-gatekeeper\n", encoding="utf-8")

    dispatch = agent_native_role_dispatch(adapter="opencode", role_archetype="gatekeeper", workdir_path=tmp_path)

    assert dispatch["target_agent"] == "loopora-gatekeeper"
    assert dispatch["target_agent_config_path"] == ".opencode/agents/loopora-gatekeeper.md"
    assert dispatch["target_agent_config_absolute_path"] == str(config_path.resolve())
    assert dispatch["target_agent_config_exists"] is True
    assert dispatch["host_mechanism"].startswith("OpenCode project command")
    assert dispatch["accepted_native_tools"] == ["task"]


def test_agent_native_template_role_dispatch_keeps_only_local_fill_guide_fields(tmp_path) -> None:
    dispatch = agent_native_role_dispatch(adapter="claude", role_archetype="guide", workdir_path=tmp_path)

    template_dispatch = agent_native_template_role_dispatch(dispatch)

    assert template_dispatch == {
        "dispatch_contract": "host_native_subagent",
        "target_agent": "loopora-guide",
        "target_role_archetype": "guide",
        "inline_allowed": False,
        "proof_field": "loopora_host_dispatch",
        "result_field": "result",
        "accepted_dispatch_modes": ["host_subagent", "host_task", "host_agent"],
        "host_mechanism": "Claude Code Agent/Task with the named Loopora role agent",
        "accepted_native_tools": ["Agent", "Task"],
    }
    assert "target_agent_config_path" not in template_dispatch
    assert "target_agent_config_absolute_path" not in template_dispatch
    assert "target_agent_config_exists" not in template_dispatch
    assert "native_trace_contract" not in template_dispatch

from __future__ import annotations

from loopora import agent_adapter_command_prefix
from loopora.agent_adapter_run_contract import agent_native_run_entry_contract
from loopora.system_prompt_assets import render_system_prompt_asset


def _render_entry_template(asset_ref: str, *, marker: str, version: int) -> str:
    return render_system_prompt_asset(
        asset_ref,
        {
            "marker": marker,
            "version": version,
            "loopora_cli_entry": agent_adapter_command_prefix.current_project_file_loopora_cli_entry(),
            "run_entry_contract": agent_native_run_entry_contract().rstrip(),
        },
    )


def codex_loopora_gen_skill(*, marker: str, version: int) -> str:
    return _render_entry_template("agent_native/entry-codex-plan.md", marker=marker, version=version)


def codex_loopora_loop_skill(*, marker: str, version: int) -> str:
    return _render_entry_template("agent_native/entry-codex-run.md", marker=marker, version=version)


def claude_loopora_gen_skill(*, marker: str, version: int) -> str:
    return _render_entry_template("agent_native/entry-claude-plan.md", marker=marker, version=version)


def claude_loopora_loop_skill(*, marker: str, version: int) -> str:
    return _render_entry_template("agent_native/entry-claude-run.md", marker=marker, version=version)


def opencode_loopora_gen_command(*, marker: str, version: int) -> str:
    return _render_entry_template("agent_native/entry-opencode-plan.md", marker=marker, version=version)


def opencode_loopora_loop_command(*, marker: str, version: int) -> str:
    return _render_entry_template("agent_native/entry-opencode-run.md", marker=marker, version=version)

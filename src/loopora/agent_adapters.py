from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

import loopora.agent_native_adapter_contracts as _agent_native_adapter_contracts
from loopora import agent_native_task_proof
from loopora import agent_adapter_context_binding as _agent_context_binding
from loopora.agent_adapter_context_binding import (
    agent_context_binding_path as agent_context_binding_path,
    agent_context_key as agent_context_key,
    agent_context_source as agent_context_source,
    read_agent_binding as read_agent_binding,
    resolved_agent_context_id as resolved_agent_context_id,
    resolve_adapter_project_root as resolve_adapter_project_root,
)
from loopora.agent_adapter_command_prefix import (
    copyable_loopora_command as copyable_loopora_command,
    loopora_command_env_prefix as loopora_command_env_prefix,
    prefix_loopora_command as prefix_loopora_command,
)
from loopora.agent_adapter_lifecycle import (
    FIRST_TASK_MESSAGE_EXAMPLE as FIRST_TASK_MESSAGE_EXAMPLE,
    IMPLEMENTED_AGENT_ADAPTERS as IMPLEMENTED_AGENT_ADAPTERS,
    _adapter_check_recovery as _adapter_check_recovery,
    adapter_first_task_handoff_policy as adapter_first_task_handoff_policy,
    _managed_templates as _managed_templates,
    adapter_first_task_message_example as adapter_first_task_message_example,
    adapter_first_task_message_example_state as adapter_first_task_message_example_state,
    agent_adapter_status as agent_adapter_status,
    check_agent_adapter as check_agent_adapter,
    install_agent_adapter as install_agent_adapter,
    list_agent_adapter_statuses as list_agent_adapter_statuses,
    preview_agent_adapter_uninstall as preview_agent_adapter_uninstall,
    uninstall_agent_adapter as uninstall_agent_adapter,
)
from loopora.agent_adapter_manifest import (
    CLAUDE_MANIFEST_RELATIVE_PATH as CLAUDE_MANIFEST_RELATIVE_PATH,
    CODEX_MANIFEST_RELATIVE_PATH as CODEX_MANIFEST_RELATIVE_PATH,
    MANIFEST_RELATIVE_PATH as MANIFEST_RELATIVE_PATH,
    MANIFEST_RELATIVE_PATHS as MANIFEST_RELATIVE_PATHS,
    OBSOLETE_MANAGED_PATHS as OBSOLETE_MANAGED_PATHS,
    OPENCODE_MANIFEST_RELATIVE_PATH as OPENCODE_MANIFEST_RELATIVE_PATH,
)
import loopora.agent_adapter_static_checks as _agent_adapter_static_checks
from loopora.agent_adapter_templates import (
    ADAPTER_MANAGED_SCHEMA_VERSION as ADAPTER_MANAGED_SCHEMA_VERSION,
    ADAPTER_VERSION as ADAPTER_VERSION,
    CLAUDE_ADAPTER_VERSION as CLAUDE_ADAPTER_VERSION,
    CLAUDE_MANAGED_MARKER as CLAUDE_MANAGED_MARKER,
    CODEX_ADAPTER_VERSION as CODEX_ADAPTER_VERSION,
    CODEX_MANAGED_MARKER as CODEX_MANAGED_MARKER,
    MANAGED_MARKER as MANAGED_MARKER,
    MANAGED_MARKERS as MANAGED_MARKERS,
    OPENCODE_ADAPTER_VERSION as OPENCODE_ADAPTER_VERSION,
    OPENCODE_MANAGED_MARKER as OPENCODE_MANAGED_MARKER,
)
from loopora.agent_native_adapter_contracts import normalize_agent_adapter_kind

AGENT_ADAPTER_KINDS = _agent_native_adapter_contracts.AGENT_ADAPTER_KINDS
AGENT_TASK_PROOF_SOURCE = agent_native_task_proof.AGENT_TASK_PROOF_SOURCE
AGENT_RUN_LIFECYCLE_SOURCE = agent_native_task_proof.AGENT_RUN_LIFECYCLE_SOURCE
NATIVE_RUN_ENTRY_CONTRACT_TITLE = _agent_native_adapter_contracts.NATIVE_RUN_ENTRY_CONTRACT_TITLE
NATIVE_RUN_ENTRY_CONTRACT_BULLETS = _agent_native_adapter_contracts.NATIVE_RUN_ENTRY_CONTRACT_BULLETS
_adapter_install_next_commands = _agent_adapter_static_checks.adapter_install_next_commands


def write_agent_binding(
    adapter: str,
    workdir: Path | str,
    payload: dict[str, Any],
    *,
    context_id: str = "",
) -> dict[str, Any]:
    return _agent_context_binding.write_agent_binding(
        adapter,
        workdir,
        payload,
        context_id=context_id,
        entry_version=ADAPTER_VERSION,
    )


def agent_loop_command(
    adapter: str,
    workdir: Path | str,
    *,
    entry_source: str = "",
    context_id: str = "",
    source_option_id: str = "",
) -> str:
    normalized_adapter = normalize_agent_adapter_kind(adapter)
    command_bits = [
        "loopora",
        "agent",
        normalized_adapter,
        "run",
        "--workdir",
        shlex.quote(str(workdir)),
    ]
    normalized_context_id = str(context_id or "").strip()
    if normalized_context_id:
        command_bits.extend(["--context-id", shlex.quote(normalized_context_id)])
    normalized_source_option_id = str(source_option_id or "").strip()
    if normalized_source_option_id:
        command_bits.extend(["--source-option-id", shlex.quote(normalized_source_option_id)])
    normalized_entry_source = str(entry_source or "").strip()
    if normalized_entry_source:
        command_bits.extend(["--entry-source", shlex.quote(normalized_entry_source)])
    command = " ".join(command_bits)
    return copyable_loopora_command(command, entry_source=normalized_entry_source)


def agent_loop_json_command(
    adapter: str,
    workdir: Path | str,
    *,
    entry_source: str = "",
    context_id: str = "",
    source_option_id: str = "",
) -> str:
    return (
        agent_loop_command(
            adapter,
            workdir,
            entry_source=entry_source,
            context_id=context_id,
            source_option_id=source_option_id,
        )
        + " --json --compact-json"
    )

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any

import loopora.agent_native_task_proof as agent_native_task_proof
import loopora.agent_native_adapter_contracts as _agent_native_adapter_contracts
import loopora.agent_adapter_static_checks as _agent_adapter_static_checks
from loopora import agent_adapter_context_binding as _agent_context_binding
from loopora.agent_adapter_context_binding import (
    agent_context_binding_path as agent_context_binding_path,
    agent_context_key as agent_context_key,
    agent_context_source as agent_context_source,
    read_agent_binding as read_agent_binding,
    resolved_agent_context_id as resolved_agent_context_id,
    resolve_adapter_project_root as resolve_adapter_project_root,
)
from loopora.agent_adapter_check_utils import (
    adapter_label as _adapter_label,
    read_text_or_empty as _read_text_or_empty,
)
from loopora.agent_adapter_command_prefix import (
    loopora_command_env_prefix as loopora_command_env_prefix,
    prefix_loopora_command as prefix_loopora_command,
)
from loopora.agent_adapter_host_config import (
    assert_host_config_is_replaceable as _assert_host_config_is_replaceable,
    host_config_status as _host_config_status,
    install_host_config as _install_host_config,
    uninstall_host_config as _uninstall_host_config,
)
from loopora.agent_adapter_managed_files import (
    CLAUDE_MANIFEST_RELATIVE_PATH as CLAUDE_MANIFEST_RELATIVE_PATH,
    CODEX_MANIFEST_RELATIVE_PATH as CODEX_MANIFEST_RELATIVE_PATH,
    MANIFEST_RELATIVE_PATH as MANIFEST_RELATIVE_PATH,
    MANIFEST_RELATIVE_PATHS as MANIFEST_RELATIVE_PATHS,
    OBSOLETE_MANAGED_PATHS as OBSOLETE_MANAGED_PATHS,
    OPENCODE_MANIFEST_RELATIVE_PATH as OPENCODE_MANIFEST_RELATIVE_PATH,
    assert_targets_are_replaceable as _assert_targets_are_replaceable,
    atomic_write_text as _atomic_write_text,
    managed_file_status as _managed_file_status,
    managed_marker as _managed_marker,
    managed_status_paths as _managed_status_paths,
    manifest_hash_for_path as _manifest_hash_for_path,
    manifest_paths as _manifest_paths,
    manifest_payload as _manifest_payload,
    manifest_relative_path as _manifest_relative_path,
    read_manifest as _read_manifest,
    remove_empty_parents as _remove_empty_parents,
    remove_obsolete_managed_files as _remove_obsolete_managed_files,
    sha256_text as _sha256_text,
)
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
    managed_templates as _adapter_managed_templates,
)
from loopora.agent_native_adapter_contracts import (
    AGENT_ADAPTER_KINDS,
    normalize_agent_adapter_kind,
)
from loopora.service_types import LooporaError

IMPLEMENTED_AGENT_ADAPTERS = {"codex", "claude", "opencode"}
FIRST_TASK_MESSAGE_EXAMPLE = (
    "After /loopora-plan, send: Goal: ship a support-ops incident dashboard that preserves audit trails; "
    "Fake-done risks: happy-path UI with no replay/error proof, missing permission checks, or unclear rollback; "
    "Required evidence: project tests, one browser journey, and a GateKeeper-readable evidence summary; "
    "Judgment tradeoffs: keep scope narrow, fail closed on unproven data safety."
)
AGENT_TASK_PROOF_SOURCE = agent_native_task_proof.AGENT_TASK_PROOF_SOURCE
AGENT_RUN_LIFECYCLE_SOURCE = agent_native_task_proof.AGENT_RUN_LIFECYCLE_SOURCE
NATIVE_RUN_ENTRY_CONTRACT_TITLE = _agent_native_adapter_contracts.NATIVE_RUN_ENTRY_CONTRACT_TITLE
NATIVE_RUN_ENTRY_CONTRACT_BULLETS = _agent_native_adapter_contracts.NATIVE_RUN_ENTRY_CONTRACT_BULLETS
_adapter_static_checks = _agent_adapter_static_checks.adapter_static_checks
_adapter_install_next_steps = _agent_adapter_static_checks.adapter_install_next_steps
_adapter_install_next_commands = _agent_adapter_static_checks.adapter_install_next_commands
_adapter_native_surface = _agent_adapter_static_checks.adapter_native_surface
_adapter_entry_reference_map = _agent_adapter_static_checks.adapter_entry_reference_map
_adapter_entry_shape_checks = _agent_adapter_static_checks.adapter_entry_shape_checks
_adapter_entry_visibility_hint = _agent_adapter_static_checks.adapter_entry_visibility_hint
_adapter_missing_role_agent_message = _agent_adapter_static_checks.adapter_missing_role_agent_message
_adapter_no_model_defaults_check = _agent_adapter_static_checks.adapter_no_model_defaults_check
_adapter_reference_paths = _agent_adapter_static_checks.adapter_reference_paths
_adapter_role_agent_checks = _agent_adapter_static_checks.adapter_role_agent_checks
_adapter_supporting_files_checks = _agent_adapter_static_checks.adapter_supporting_files_checks
_entry_has_native_run_contract = _agent_adapter_static_checks.entry_has_native_run_contract
_entry_mentions_reference = _agent_adapter_static_checks.entry_mentions_reference
_entry_path_is_run_entry = _agent_adapter_static_checks.entry_path_is_run_entry
_opencode_run_command_check_passes = _agent_adapter_static_checks.opencode_run_command_check_passes


def list_agent_adapter_statuses(workdir: Path | str | None) -> list[dict[str, Any]]:
    root = resolve_adapter_project_root(workdir)
    return [agent_adapter_status(kind, root) for kind in AGENT_ADAPTER_KINDS]


def agent_adapter_status(adapter: str, workdir: Path | str | None) -> dict[str, Any]:
    kind = normalize_agent_adapter_kind(adapter)
    root = resolve_adapter_project_root(workdir)
    if kind not in IMPLEMENTED_AGENT_ADAPTERS:
        return _not_implemented_status(kind, root)
    return _managed_adapter_status(kind, root)


def check_agent_adapter(adapter: str, workdir: Path | str | None) -> dict[str, Any]:
    kind = normalize_agent_adapter_kind(adapter)
    root = resolve_adapter_project_root(workdir)
    status = agent_adapter_status(kind, root)
    checks = _adapter_static_checks(kind, root, status) if kind in IMPLEMENTED_AGENT_ADAPTERS else []
    failed = [item for item in checks if item.get("status") != "pass"]
    check_status = "pass" if not failed and status.get("status") == "installed" else "fail"
    result = {
        **status,
        "check_status": check_status,
        "check_recovery": _adapter_check_recovery(kind, root, status=status, check_status=check_status),
        "checks": checks,
        "native_surface": _adapter_native_surface(kind, root),
    }
    if check_status == "pass":
        result["next_steps"] = _adapter_install_next_steps(kind)
        result["next_commands"] = _adapter_install_next_commands(kind, root)
        result["first_task_message_example"] = adapter_first_task_message_example()
    return result


def install_agent_adapter(adapter: str, workdir: Path | str | None) -> dict[str, Any]:
    kind = normalize_agent_adapter_kind(adapter)
    root = resolve_adapter_project_root(workdir)
    if kind not in IMPLEMENTED_AGENT_ADAPTERS:
        raise LooporaError(f"{_adapter_label(kind)} adapter is not implemented yet")
    templates = _managed_templates(kind)
    marker = _managed_marker(kind)
    _assert_targets_are_replaceable(kind, root, templates)
    removed_obsolete_files = _remove_obsolete_managed_files(kind, root, templates)
    _assert_host_config_is_replaceable(kind, root)
    written: list[dict[str, str]] = []
    for relative_path, content in templates.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        current = _read_text_or_empty(target)
        if current != content:
            _atomic_write_text(target, content)
        written.append(
            {
                "path": relative_path,
                "sha256": _sha256_text(content),
            }
        )
    _install_host_config(kind, root)
    manifest = _manifest_payload(kind, root, written)
    manifest_path = root / _manifest_relative_path(kind)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    existing_manifest, _ = _read_manifest(kind, root)
    if existing_manifest != manifest:
        _atomic_write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    status = _managed_adapter_status(kind, root)
    return {
        "adapter": kind,
        "label": _adapter_label(kind),
        "workdir": str(root),
        "status": status["status"],
        "next_steps": _adapter_install_next_steps(kind),
        "next_commands": _adapter_install_next_commands(kind, root),
        "first_task_message_example": adapter_first_task_message_example(),
        "native_surface": _adapter_native_surface(kind, root),
        "manifest_path": str(manifest_path),
        "managed_files": status["managed_files"],
        "managed_marker": marker,
        "removed_obsolete_files": removed_obsolete_files,
    }


def uninstall_agent_adapter(adapter: str, workdir: Path | str | None) -> dict[str, Any]:
    kind = normalize_agent_adapter_kind(adapter)
    root = resolve_adapter_project_root(workdir)
    if kind not in IMPLEMENTED_AGENT_ADAPTERS:
        raise LooporaError(f"{_adapter_label(kind)} adapter is not implemented yet")

    templates = _managed_templates(kind)
    marker = _managed_marker(kind)
    manifest_payload, manifest_error = _read_manifest(kind, root)
    manifest_paths = _manifest_paths(manifest_payload) if isinstance(manifest_payload, dict) else []
    managed_paths = sorted(set(manifest_paths) | set(templates))

    removed: list[str] = []
    kept: list[dict[str, str]] = []
    for relative_path in managed_paths:
        target = root / relative_path
        if not target.exists():
            continue
        try:
            content = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            kept.append({"path": relative_path, "reason": "unreadable"})
            continue
        manifest_hash = _manifest_hash_for_path(manifest_payload, relative_path) if isinstance(manifest_payload, dict) else ""
        template_hash = _sha256_text(templates.get(relative_path, ""))
        content_hash = _sha256_text(content)
        if marker in content or content_hash in {manifest_hash, template_hash}:
            target.unlink()
            removed.append(relative_path)
            _remove_empty_parents(root, target.parent)
        else:
            kept.append({"path": relative_path, "reason": "not_loopora_managed"})

    removed.extend(_uninstall_host_config(kind, root))

    manifest_path = root / _manifest_relative_path(kind)
    if manifest_path.exists():
        try:
            manifest_path.unlink()
            _remove_empty_parents(root, manifest_path.parent)
        except OSError as exc:
            kept.append({"path": _manifest_relative_path(kind), "reason": f"remove_failed: {exc}"})

    return {
        "adapter": kind,
        "label": _adapter_label(kind),
        "workdir": str(root),
        "status": _managed_adapter_status(kind, root)["status"],
        "removed_files": removed,
        "kept_files": kept,
        "manifest_error": manifest_error,
    }


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
    return prefix_loopora_command(command, entry_source=normalized_entry_source)


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
        + " --json"
    )


def _not_implemented_status(kind: str, root: Path) -> dict[str, Any]:
    return {
        "adapter": kind,
        "label": _adapter_label(kind),
        "workdir": str(root),
        "implemented": False,
        "status": "not_implemented",
        "summary": "Coming soon",
        "managed_files": [],
        "manifest_path": "",
        "error": "",
    }


def _managed_adapter_status(kind: str, root: Path) -> dict[str, Any]:
    templates = _managed_templates(kind)
    manifest_payload, manifest_error = _read_manifest(kind, root)
    manifest_path = root / _manifest_relative_path(kind)
    managed_files = []
    if manifest_error:
        return {
            "adapter": kind,
            "label": _adapter_label(kind),
            "workdir": str(root),
            "implemented": True,
            "status": "error",
            "summary": f"Cannot read Loopora {_adapter_label(kind)} adapter manifest",
            "managed_files": [],
            "manifest_path": str(manifest_path),
            "error": manifest_error,
        }

    manifest_exists = isinstance(manifest_payload, dict)
    unmanaged_conflicts = []
    needs_update = False
    installed_count = 0
    paths = _managed_status_paths(kind, root, manifest_payload, manifest_exists=manifest_exists, templates=templates)
    managed_marker_found = False
    for relative_path in paths:
        expected = templates.get(relative_path, "")
        file_state = _managed_file_status(kind, root, relative_path, expected, manifest_context=(manifest_payload, manifest_exists))
        file_payload = file_state["payload"]
        installed_count += int(file_state["current"])
        needs_update = needs_update or bool(file_state["needs_update"])
        managed_marker_found = managed_marker_found or bool(file_state["managed_marker"])
        if file_state["unmanaged_conflict"]:
            unmanaged_conflicts.append(relative_path)
        managed_files.append(file_payload)

    host_config_state = _host_config_status(kind, root, manifest_exists=manifest_exists)
    if host_config_state:
        managed_files.append(host_config_state["payload"])
        needs_update = needs_update or bool(host_config_state["needs_update"])
        if host_config_state["unmanaged_conflict"]:
            unmanaged_conflicts.append(host_config_state["payload"]["path"])

    if unmanaged_conflicts:
        status = "error"
        summary = f"{_adapter_label(kind)} adapter files exist but ownership is unclear"
        error = "unmanaged files: " + ", ".join(unmanaged_conflicts)
    elif manifest_exists and needs_update:
        status = "needs_update"
        summary = f"{_adapter_label(kind)} adapter is installed but needs update"
        error = ""
    elif manifest_exists and installed_count == len(templates):
        status = "installed"
        summary = f"{_adapter_label(kind)} adapter is installed"
        error = ""
    elif not manifest_exists and (installed_count == len(templates) or managed_marker_found):
        status = "needs_update"
        summary = f"{_adapter_label(kind)} adapter files exist but manifest is missing"
        error = ""
    else:
        status = "not_installed"
        summary = f"{_adapter_label(kind)} adapter is not installed"
        error = ""
    return {
        "adapter": kind,
        "label": _adapter_label(kind),
        "workdir": str(root),
        "implemented": True,
        "status": status,
        "summary": summary,
        "managed_files": managed_files,
        "manifest_path": str(manifest_path),
        "error": error,
    }


def _adapter_check_recovery(kind: str, root: Path, *, status: dict[str, Any], check_status: str) -> dict[str, Any]:
    install_command = prefix_loopora_command(f"loopora init {kind} --workdir {shlex.quote(str(root))}")
    check_command = prefix_loopora_command(f"loopora init {kind} --workdir {shlex.quote(str(root))} --check")
    adapter_status = str(status.get("status") or "")
    if check_status == "pass":
        return {
            "state": "installed",
            "summary": f"{_adapter_label(kind)} Loopora entry is installed and passes static checks.",
            "install_command": "",
            "check_command": check_command,
            "details_are_expected": False,
        }
    if adapter_status == "not_installed":
        return {
            "state": "not_installed",
            "summary": (
                f"{_adapter_label(kind)} Loopora entry is not installed yet; missing managed files are expected before install."
            ),
            "install_command": install_command,
            "check_command": check_command,
            "details_are_expected": True,
        }
    return {
        "state": adapter_status or "needs_attention",
        "summary": f"{_adapter_label(kind)} Loopora entry needs attention; inspect failed checks before reinstalling.",
        "install_command": install_command,
        "check_command": check_command,
        "details_are_expected": False,
    }


def adapter_first_task_message_example() -> str:
    return FIRST_TASK_MESSAGE_EXAMPLE


def _managed_templates(kind: str) -> dict[str, str]:
    return _adapter_managed_templates(kind)

from __future__ import annotations

import errno
from pathlib import Path
import shlex

from loopora import web_bind_preflight
from loopora.agent_adapter_check_utils import adapter_label
from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.agent_adapter_current_host import current_agent_host_detection
from loopora.agent_adapter_workdir_recovery import adapter_workdir_state
from loopora.agent_native_adapter_contracts import AGENT_ADAPTER_KINDS
from loopora.first_use_route_readiness import first_use_web_readiness_blockers


INIT_PREVIEW_WEB_HOST = "127.0.0.1"
INIT_PREVIEW_WEB_PORT = web_bind_preflight.DEFAULT_WEB_PORT


def init_adapter_choice_preview(workdir: Path) -> str:
    lines, state, workdir_arg = _preview_header(workdir, include_supported_adapters=True)
    ready_lines = [
        f"- Check fit first: {copyable_loopora_command(f'loopora fit --workdir {workdir_arg}')}",
        *_current_host_install_lines(workdir_arg),
        "- Explicit adapter fallback when current-host detection is unavailable or ambiguous:",
        *[
            _adapter_action_line(
                adapter=adapter,
                command=f"loopora init {adapter} --workdir {workdir_arg}",
            )
            for adapter in AGENT_ADAPTER_KINDS
        ],
        f"- Confirm readiness after an explicit adapter install: {copyable_loopora_command(f'loopora doctor --workdir {workdir_arg}')}",
        *_init_web_creation_lines(workdir_arg, state),
        f"- Usage/setup help: {copyable_loopora_command(f'loopora support --workdir {workdir_arg}')}",
    ]
    lines.extend(
        _workdir_gate_or_ready_lines(
            state,
            ready_lines,
            choose_text="choose an existing project directory before choosing an Agent adapter",
        )
    )
    return "\n".join(lines)


def uninstall_adapter_choice_preview(workdir: Path) -> str:
    lines, state, workdir_arg = _preview_header(workdir, include_supported_adapters=True)
    ready_lines = [
        "- Choose the managed same-Agent project entry to uninstall:",
        *[
            _adapter_action_line(
                adapter=adapter,
                command=f"loopora uninstall {adapter} --workdir {workdir_arg}",
            )
            for adapter in AGENT_ADAPTER_KINDS
        ],
        f"- Review remaining readiness: {copyable_loopora_command(f'loopora doctor --workdir {workdir_arg}')}",
        f"- Usage/setup help: {copyable_loopora_command(f'loopora support --workdir {workdir_arg}')}",
    ]
    lines.extend(
        _workdir_gate_or_ready_lines(
            state,
            ready_lines,
            choose_text="choose an existing project directory before choosing an Agent adapter",
        )
    )
    return "\n".join(lines)


def agent_runtime_choice_preview(workdir: Path) -> str:
    lines, state, workdir_arg = _preview_header(workdir, include_supported_adapters=True)
    ready_lines = [
        "- Choose the same-Agent project entry matching your current host, then check it:",
        *[
            _adapter_action_line(
                adapter=adapter,
                command=f"loopora agent {adapter} check --workdir {workdir_arg}",
                noun="entry",
            )
            for adapter in AGENT_ADAPTER_KINDS
        ],
        f"- Confirm readiness: {copyable_loopora_command(f'loopora doctor --workdir {workdir_arg}')}",
        "- Use /loopora-plan and /loopora-run inside the selected Agent after readiness.",
        f"- Usage/setup help: {copyable_loopora_command(f'loopora support --workdir {workdir_arg}')}",
    ]
    lines.extend(
        _workdir_gate_or_ready_lines(
            state,
            ready_lines,
            choose_text="choose an existing project directory before choosing an Agent adapter",
        )
    )
    return "\n".join(lines)


def agent_runtime_adapter_preview(adapter: str, workdir: Path) -> str:
    lines, state, workdir_arg = _preview_header(workdir, include_supported_adapters=False)
    ready_lines = [
        f"- Check this Agent entry: {copyable_loopora_command(f'loopora agent {adapter} check --workdir {workdir_arg}')}",
        f"- Confirm readiness: {copyable_loopora_command(f'loopora doctor --workdir {workdir_arg}')}",
        "- Use /loopora-plan and /loopora-run inside this Agent after readiness.",
        f"- Usage/setup help: {copyable_loopora_command(f'loopora support --workdir {workdir_arg}')}",
    ]
    lines.extend(
        _workdir_gate_or_ready_lines(
            state,
            ready_lines,
            choose_text="choose an existing project directory before checking this Agent entry",
        )
    )
    return "\n".join(lines)


def _preview_header(workdir: Path, *, include_supported_adapters: bool) -> tuple[list[str], dict[str, object], str]:
    state = adapter_workdir_state(workdir)
    status = str(state.get("status") or "unavailable")
    root = str(state.get("workdir") or "")
    lines = [
        "Target project preview:",
        f"project directory: {root}",
        f"preview state: {'ready for adapter choice' if status == 'ready' else 'blocked by project directory'}",
        f"project directory state: {status}",
    ]
    summary = str(state.get("summary") or "").strip()
    if summary:
        lines.append(f"note: {summary}")
    if include_supported_adapters:
        lines.append("supported Agent adapters: " + ", ".join(AGENT_ADAPTER_KINDS))
    lines.append("next:")
    return lines, state, shlex.quote(root)


def _workdir_gate_or_ready_lines(state: dict[str, object], ready_lines: list[str], *, choose_text: str) -> list[str]:
    if state.get("status") == "ready":
        return ready_lines
    commands = state.get("commands") if isinstance(state.get("commands"), dict) else {}
    create_command = str(commands.get("create") or "")
    if create_command:
        return [f"- Create target project directory: {create_command}", *ready_lines]
    return [f"- Choose project directory: {choose_text}."]


def _init_web_creation_lines(workdir_arg: str, state: dict[str, object]) -> list[str]:
    port = INIT_PREVIEW_WEB_PORT
    notes: list[str] = []
    label = "Fit Guide/Web choices after readiness"
    if state.get("status") != "ready":
        return [_web_creation_line(label=label, workdir_arg=workdir_arg, port=port)]

    readiness_blockers = first_use_web_readiness_blockers(state)
    if readiness_blockers:
        notes.append("- App/Web readiness needs attention; run doctor before starting Web.")
        label = "Fit Guide/Web choices after App/Web readiness"

    try:
        web_bind_preflight.probe_web_bind(INIT_PREVIEW_WEB_HOST, INIT_PREVIEW_WEB_PORT)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            suggested_port = web_bind_preflight.next_available_web_port(
                host=INIT_PREVIEW_WEB_HOST,
                port=INIT_PREVIEW_WEB_PORT,
            )
            if suggested_port is None:
                notes.append(f"- Default Web port {INIT_PREVIEW_WEB_PORT} is already in use; run doctor before starting Web.")
                label = "Fit Guide/Web choices after a Web port is available"
            else:
                port = suggested_port
                notes.append(
                    f"- Default Web port {INIT_PREVIEW_WEB_PORT} is already in use; "
                    f"this preview uses available port {suggested_port}."
                )
        else:
            notes.append(
                f"- Web bind preflight cannot use {INIT_PREVIEW_WEB_HOST}:{INIT_PREVIEW_WEB_PORT}; "
                "run doctor before starting Web."
            )
            label = "Fit Guide/Web choices after Web bind readiness"

    return [*notes, _web_creation_line(label=label, workdir_arg=workdir_arg, port=port)]


def _web_creation_line(*, label: str, workdir_arg: str, port: int) -> str:
    command = copyable_loopora_command(
        f"loopora serve --open --workdir {workdir_arg} --host {INIT_PREVIEW_WEB_HOST} --port {port}"
    )
    return f"- {label}: {command}"


def _adapter_action_line(*, adapter: str, command: str, noun: str = "") -> str:
    label = adapter_label(adapter)
    suffix = f" {noun}" if noun else ""
    return f"  - {label}{suffix}: {copyable_loopora_command(command)}"


def _current_host_install_lines(workdir_arg: str) -> list[str]:
    detection = current_agent_host_detection()
    command = copyable_loopora_command(f"loopora init current --workdir {workdir_arg}")
    if detection["state"] == "detected":
        label = adapter_label(str(detection["adapter"]))
        return [f"- Current Agent host detected: {label}", f"- Install the detected current host: {command}"]
    if detection["state"] == "ambiguous":
        labels = ", ".join(adapter_label(str(item)) for item in list(detection["detected_adapters"]))
        return [f"- Current Agent host detection is ambiguous ({labels}); use an explicit adapter below."]
    return [f"- Inside a supported Agent session, detect and install its current host: {command}"]

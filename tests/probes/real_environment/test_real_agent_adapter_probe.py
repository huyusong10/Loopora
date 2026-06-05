from __future__ import annotations

import json
import os
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

import pytest

from loopora.branding import state_dir_for_workdir
from loopora.db import LooporaRepository
from loopora.event_redaction import redact_sensitive_value
from loopora.service import LooporaService
from loopora.service_types import TERMINAL_RUN_STATUSES
from loopora.settings import AppSettings

pytestmark = pytest.mark.real_agent

ENABLE_ENV = "LOOPORA_ENABLE_REAL_AGENT_PROBE"
COMMAND_TEMPLATE_ENV = "LOOPORA_REAL_AGENT_COMMAND_TEMPLATE"
CLAUDE_COMMAND_TEMPLATE_ENV = "LOOPORA_REAL_CLAUDE_AGENT_COMMAND_TEMPLATE"
OPENCODE_COMMAND_TEMPLATE_ENV = "LOOPORA_REAL_OPENCODE_AGENT_COMMAND_TEMPLATE"
TARGETS_ENV = "LOOPORA_REAL_AGENT_TARGETS"
TIMEOUT_ENV = "LOOPORA_REAL_AGENT_TIMEOUT_SECONDS"
TERMINAL_PROOF_GRACE_ENV = "LOOPORA_REAL_AGENT_TERMINAL_PROOF_GRACE_SECONDS"
REAL_PROBE_MODEL_OVERRIDE_ENV = "LOOPORA_REAL_PROBE_ALLOW_MODEL_OVERRIDE"
AGENT_TARGETS = ("codex", "claude", "opencode")
REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"


@dataclass(frozen=True, slots=True)
class HostCommandMonitorRequest:
    command: str
    adapter: str
    workdir: Path
    env: dict[str, str]
    timeout: float
    agent_web_url: str
    sentinel_log: Path


@dataclass(frozen=True, slots=True)
class HostCommandMonitorResult:
    completed: subprocess.CompletedProcess[str]
    binding: dict
    activity_snapshots: list[dict]
    phase_report: dict
    phase_report_path: Path


@dataclass(frozen=True, slots=True)
class PhaseStatusInput:
    adapter: str
    workdir: Path
    binding: dict
    activity_snapshots: list[dict]
    events: list[dict]
    validation_summaries: list[dict]


@dataclass(frozen=True, slots=True)
class PhaseReportHostSignals:
    command: str
    stdout: str = ""
    stderr: str = ""


def _selected_real_agent_targets() -> set[str]:
    raw = str(os.environ.get(TARGETS_ENV, "") or "").strip()
    if not raw:
        return set(AGENT_TARGETS)
    selected = {item.strip().lower().replace("_", "-") for item in raw.split(",") if item.strip()}
    aliases = {"claude-code": "claude", "claudecode": "claude", "open-code": "opencode"}
    normalized = {aliases.get(item, item) for item in selected}
    invalid = sorted(normalized - set(AGENT_TARGETS))
    if invalid:
        raise AssertionError(f"unsupported {TARGETS_ENV} entries: {', '.join(invalid)}")
    return normalized


def _template_env_for_adapter(adapter: str) -> str:
    return {
        "claude": CLAUDE_COMMAND_TEMPLATE_ENV,
        "opencode": OPENCODE_COMMAND_TEMPLATE_ENV,
    }.get(adapter, COMMAND_TEMPLATE_ENV)


def _command_has_external_config_arg(command: str) -> bool:
    try:
        args = shlex.split(command)
    except ValueError:
        args = command.split()
    pinned_flags = {"--model", "--effort", "--variant"}
    return any(
        arg in pinned_flags
        or any(arg.startswith(f"{flag}=") for flag in pinned_flags)
        or "model_reasoning_effort" in arg
        for arg in args
    )


def _model_override_allowed() -> bool:
    return os.environ.get(REAL_PROBE_MODEL_OVERRIDE_ENV) == "1"


def _model_policy_summary(adapter: str, command: str) -> dict:
    external_config_arg_present = _command_has_external_config_arg(command)
    return {
        "adapter": adapter,
        "expected_default_model": "",
        "model_override_allowed": _model_override_allowed(),
        "delegates_to_host_default": not external_config_arg_present,
        "external_config_arg_present": external_config_arg_present,
    }


def _assert_real_agent_command_model_policy(adapter: str, command: str) -> None:
    if not _command_has_external_config_arg(command):
        return
    assert _model_override_allowed(), (
        f"{adapter} real-agent probe should delegate model and reasoning configuration to the host Agent on the release path. "
        f"Set {REAL_PROBE_MODEL_OVERRIDE_ENV}=1 only for an intentional override validation."
    )


def _assert_real_agent_command_monitorability(adapter: str, command: str) -> None:
    if adapter != "claude":
        return
    try:
        args = shlex.split(command)
    except ValueError:
        args = command.split()
    has_stream_json = "--output-format=stream-json" in args or any(
        arg == "--output-format" and index + 1 < len(args) and args[index + 1] == "stream-json"
        for index, arg in enumerate(args)
    )
    has_partial_messages = "--include-partial-messages" in args
    message = (
        "Claude Code real-agent release probe must use `--output-format stream-json --include-partial-messages` "
        "so the harness can monitor Agent/Task start, work-panel exposure, and repair signals before final stdout."
    )
    assert has_stream_json, message
    assert has_partial_messages, message


def _require_real_agent_template(adapter: str) -> str:
    if os.environ.get(ENABLE_ENV) != "1":
        pytest.skip(f"set {ENABLE_ENV}=1 to run the real Agent adapter release-profile probe")
    if adapter not in _selected_real_agent_targets():
        pytest.skip(f"{adapter} is not enabled by {TARGETS_ENV}")
    env_name = _template_env_for_adapter(adapter)
    template = os.environ.get(env_name, "").strip()
    if not template:
        pytest.skip(
            f"set {env_name} to a shell command template for the real {adapter} Agent host; "
            "available placeholders: {workdir}, {prompt_file}, {bundle_file}"
        )
    return template


def _write_nested_agent_sentinels(tmp_path: Path) -> tuple[Path, Path]:
    sentinel_dir = tmp_path / "nested-agent-sentinels"
    sentinel_dir.mkdir()
    log_path = tmp_path / "nested-agent-sentinel.log"
    for name in AGENT_TARGETS:
        script = sentinel_dir / name
        script.write_text(
            "#!/bin/sh\n"
            f'echo "$0 $@" >> {shlex.quote(str(log_path))}\n'
            "exit 86\n",
            encoding="utf-8",
        )
        script.chmod(0o755)
    return sentinel_dir, log_path


def _write_loopora_wrapper(tmp_path: Path, *, sentinel_dir: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    wrapper = bin_dir / "loopora"
    wrapper.write_text(
        "#!/bin/sh\n"
        f'PATH="{sentinel_dir}:$PATH" PYTHONPATH="{SRC_ROOT}${{PYTHONPATH:+:$PYTHONPATH}}" exec "{sys.executable}" -m loopora "$@"\n',
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    return bin_dir


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_agent_web(base_url: str, *, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/api/runtime/activity", timeout=1) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if {"running_count", "queued_count", "runs"} <= set(payload):
                return
        except Exception as exc:  # noqa: BLE001 - readiness probe should tolerate transient startup failures.
            last_error = str(exc)
        time.sleep(0.2)
    raise AssertionError(f"Timed out waiting for Agent-started Loopora Web at {base_url}: {last_error}")


def _fetch_runtime_activity(base_url: str) -> dict:
    with urllib.request.urlopen(f"{base_url}/api/runtime/activity", timeout=1) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or not {"running_count", "queued_count", "runs"} <= set(payload):
        raise AssertionError(f"invalid runtime activity payload: {payload!r}")
    return payload


def _fetch_returned_run_url(base_url: str, run_id: str) -> dict:
    with urllib.request.urlopen(f"{base_url}/api/runs/{run_id}", timeout=1) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or str(payload.get("id") or "") != run_id:
        raise AssertionError(f"invalid run URL payload for {run_id}: {payload!r}")
    return payload


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _safe_read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _truncate_text(value: object, *, limit: int = 600) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[:limit] + "...[truncated]"


def _tail_text(value: object, *, limit: int = 4000) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return "...[truncated]\n" + text[-limit:]


def _read_tail_text(path: Path, *, limit: int = 4000) -> str:
    try:
        return _tail_text(path.read_text(encoding="utf-8", errors="replace"), limit=limit)
    except OSError:
        return ""


def _terminate_pid_file(pid_file: Path) -> None:
    if not pid_file.exists():
        return
    raw_pid = pid_file.read_text(encoding="utf-8").strip()
    if not raw_pid:
        return
    try:
        pid = int(raw_pid)
    except ValueError:
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.1)
    os.kill(pid, signal.SIGKILL)


def _binding_payloads(adapter: str, workdir: Path) -> list[dict]:
    bindings_dir = state_dir_for_workdir(workdir) / "agent_adapters" / adapter / "bindings"
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(bindings_dir.glob("*.json"))]


def _wait_for_run_binding(adapter: str, workdir: Path, *, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    last_payloads: list[dict] = []
    while time.monotonic() < deadline:
        last_payloads = _binding_payloads(adapter, workdir)
        for payload in last_payloads:
            if str(payload.get("linked_run_id") or "").strip():
                return payload
        time.sleep(0.5)
    raise AssertionError(f"Timed out waiting for a {adapter} adapter run binding; last payloads={last_payloads!r}")


def _linked_run_binding(adapter: str, workdir: Path) -> dict | None:
    for payload in _binding_payloads(adapter, workdir):
        if str(payload.get("linked_run_id") or "").strip():
            return payload
    return None


def _latest_binding(adapter: str, workdir: Path) -> dict:
    payloads = _binding_payloads(adapter, workdir)
    if not payloads:
        return {}
    linked = [payload for payload in payloads if str(payload.get("linked_run_id") or "").strip()]
    return linked[-1] if linked else payloads[-1]


def _phase_report_path(workdir: Path) -> Path:
    return state_dir_for_workdir(workdir) / "real-probes" / "real-agent-phase-report.json"


def _candidate_file(adapter: str, workdir: Path) -> Path:
    return state_dir_for_workdir(workdir) / "agent_inbox" / adapter / "conversation-candidate.yml"


def _run_dir(workdir: Path, run_id: str) -> Path:
    return state_dir_for_workdir(workdir) / "runs" / run_id


def _alignment_validation_summaries(workdir: Path) -> list[dict]:
    rows: list[dict] = []
    sessions_dir = state_dir_for_workdir(workdir) / "alignment_sessions"
    for path in sorted(sessions_dir.glob("*/artifacts/validation.json"))[-8:]:
        payload = _safe_read_json(path)
        rows.append(
            {
                "session_id": path.parent.parent.name,
                "ok": payload.get("ok"),
                "error": _truncate_text(payload.get("error"), limit=240),
                "issues": list((payload.get("semantic_lint") or {}).get("issues") or [])[:5]
                if isinstance(payload.get("semantic_lint"), dict)
                else [],
                "path": str(path),
            }
        )
    return rows


def _binding_summary(binding: dict) -> dict:
    invocations = list(binding.get("entry_invocations") or []) if isinstance(binding.get("entry_invocations"), list) else []
    return {
        "adapter": binding.get("adapter"),
        "alignment_status": binding.get("alignment_status"),
        "alignment_session_id": binding.get("alignment_session_id"),
        "linked_bundle_id": binding.get("linked_bundle_id"),
        "linked_loop_id": binding.get("linked_loop_id"),
        "linked_run_id": binding.get("linked_run_id"),
        "run_path": binding.get("run_path"),
        "execution_plane": binding.get("execution_plane"),
        "entry_invocations": [
            {"action": item.get("action"), "entry_source": item.get("entry_source"), "at": item.get("at")}
            for item in invocations
            if isinstance(item, dict)
        ],
        "path": binding.get("path"),
    }


def _activity_summaries(activity_snapshots: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for snapshot in activity_snapshots[-5:]:
        runs = snapshot.get("runs") if isinstance(snapshot.get("runs"), list) else []
        rows.append(
            {
                "runtime_visibility_source": snapshot.get("runtime_visibility_source") or "runtime_activity",
                "returned_run_url_phase": snapshot.get("returned_run_url_phase"),
                "running_count": snapshot.get("running_count"),
                "queued_count": snapshot.get("queued_count"),
                "runs": [
                    {"id": item.get("id"), "status": item.get("status"), "run_path": item.get("run_path")}
                    for item in runs[:6]
                    if isinstance(item, dict)
                ],
            }
        )
    return rows


def _event_summaries(events: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for event in events[-12:]:
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        rows.append(
            {
                "id": event.get("id"),
                "event_type": event.get("event_type"),
                "role": event.get("role"),
                "step_id": payload.get("step_id"),
                "status": payload.get("status"),
                "reason": payload.get("reason"),
                "task_verdict_status": payload.get("task_verdict_status"),
            }
        )
    return rows


def _state_summary(path: Path) -> dict:
    state = _safe_read_json(path)
    active = state.get("active_step") if isinstance(state.get("active_step"), dict) else {}
    step_view = active.get("agent_step_view") if isinstance(active.get("agent_step_view"), dict) else {}
    return {
        "status": state.get("status"),
        "iter_id": state.get("iter_id"),
        "step_index": state.get("step_index"),
        "active_step_id": step_view.get("step_id"),
        "active_role": (step_view.get("role") or {}).get("archetype") if isinstance(step_view.get("role"), dict) else None,
        "host_dispatches": [
            {
                "step_id": item.get("step_id"),
                "target_agent": item.get("target_agent"),
                "actual_agent": item.get("actual_agent"),
                "dispatch_mode": item.get("dispatch_mode"),
                "inline": item.get("inline"),
                "native_trace": item.get("native_trace"),
            }
            for item in list(state.get("host_dispatches") or [])[-6:]
            if isinstance(item, dict)
        ],
    }


def _projection_summary(path: Path, *, keys: tuple[str, ...]) -> dict:
    payload = _safe_read_json(path)
    return {key: payload.get(key) for key in keys if key in payload}


def _role_output_summary(path: Path) -> dict:
    payload = _safe_read_json(path)
    result = payload.get("result") if isinstance(payload.get("result"), dict) else payload
    if not isinstance(result, dict):
        result = {}
    return {
        "exists": path.exists(),
        "keys": sorted(result.keys())[:16],
        "passed": result.get("passed"),
        "evidence_gate_status": result.get("evidence_gate_status"),
        "blocking_issues": list(result.get("blocking_issues") or [])[:6] if isinstance(result.get("blocking_issues"), list) else [],
        "hard_constraint_violations": list(result.get("hard_constraint_violations") or [])[:6]
        if isinstance(result.get("hard_constraint_violations"), list)
        else [],
        "evidence_refs": list(result.get("evidence_refs") or [])[:6] if isinstance(result.get("evidence_refs"), list) else [],
    }


def _role_outputs_summary(run_path: Path) -> dict:
    rows: dict[str, dict] = {}
    for step_dir in sorted((run_path / "iterations" / "iter_000" / "steps").glob("*__*")):
        rows[step_dir.name] = {
            "raw": _role_output_summary(step_dir / "output.raw.json"),
            "normalized": _role_output_summary(step_dir / "output.normalized.json"),
        }
    return rows


def _experience_health_summary(
    *,
    workdir: Path,
    run_path: Path,
    host_stdout: str = "",
    host_stderr: str = "",
) -> dict:
    stdout_text = str(host_stdout or "")
    stderr_text = str(host_stderr or "")
    stdout_tail = _tail_text(host_stdout)
    stderr_tail = _tail_text(host_stderr)
    host_text = "\n".join(item for item in (stdout_text, stderr_text) if item).lower()
    host_tail_text = "\n".join(item for item in (stdout_tail, stderr_tail) if item).lower()
    artifact_contracts = _experience_artifact_contracts(workdir, run_path)
    native_trace_observed = _experience_native_trace_observed(run_path)
    auto_repair_events = _experience_auto_repair_events(stdout_tail, stderr_tail)
    stream_task_events = _claude_stream_task_events(stdout_text, stderr_text)
    role_dispatch_prompt_contract = _claude_role_dispatch_prompt_contract(stdout_text, stderr_text)
    agent_work_panel_sources = _experience_marker_sources(
        "agent_work_panel",
        host_stdout=stdout_text,
        host_stderr=stderr_text,
        host_stdout_tail=stdout_tail,
        host_stderr_tail=stderr_tail,
    )
    notes = ["experience_health_is_review_signal_not_task_proof"]
    if host_tail_text:
        notes.append("host_stdout_stderr_tail_scanned")
    if artifact_contracts["agent_work_panel_exposed"]:
        notes.append("agent_work_panel_exposed_in_loopora_artifact")
    if artifact_contracts["native_todo_seen"]:
        notes.append("native_todo_contract_seen")
    if native_trace_observed:
        notes.append("native_trace_seen_in_agent_native_state")
    if stream_task_events["stream_json_seen"]:
        notes.append("host_stream_json_seen")
    if stream_task_events["task_started_count"]:
        notes.append("host_native_role_task_started_seen")
    elif stream_task_events["stream_json_seen"]:
        notes.append("host_native_role_task_started_not_seen")
    role_dispatch_prompt_note = _role_dispatch_prompt_contract_note(role_dispatch_prompt_contract)
    if role_dispatch_prompt_note:
        notes.append(role_dispatch_prompt_note)
    if not any(
        (
            agent_work_panel_sources,
            artifact_contracts["native_todo_seen"],
            native_trace_observed,
            auto_repair_events,
            stream_task_events["task_started_count"],
        )
    ):
        notes.append("no_experience_markers_seen_in_available_sources")
    return {
        "agent_work_panel_seen": bool(agent_work_panel_sources),
        "agent_work_panel_sources": agent_work_panel_sources,
        "agent_work_panel_artifact_exposed": artifact_contracts["agent_work_panel_exposed"],
        "agent_work_panel_artifact_sources": artifact_contracts["agent_work_panel_sources"],
        "todo_guidance_seen": _any_marker(host_text, "native_todo", "todo_items", "todo guidance")
        or artifact_contracts["native_todo_seen"],
        "todo_not_evidence_confirmed": _todo_not_evidence_seen(host_text) or artifact_contracts["native_todo_not_evidence"],
        "user_question_guidance_available": _any_marker(
            host_text,
            "question_action",
            "recommended_reply_shape",
            "loop-shaping",
            "main_agent_session",
        ),
        "role_dispatch_guidance_seen": _any_marker(
            host_text,
            "role_dispatch",
            "dispatch_next",
            "host-native role",
            "native dispatch guidance",
        )
        or artifact_contracts["role_dispatch_seen"],
        "native_trace_observed": native_trace_observed,
        "host_stream_json_seen": stream_task_events["stream_json_seen"],
        "native_role_task_started_count": stream_task_events["task_started_count"],
        "native_role_task_completed_count": stream_task_events["task_completed_count"],
        "native_role_task_started": stream_task_events["task_started"],
        "native_role_task_completed": stream_task_events["task_completed"],
        "role_dispatch_prompt_contract": role_dispatch_prompt_contract,
        "auto_repair_events": auto_repair_events,
        "experience_notes": notes,
    }


def _role_dispatch_prompt_contract_note(contract: dict[str, object]) -> str:
    if contract["violation_count"]:
        return "role_dispatch_prompt_contract_violation"
    if contract["agent_task_prompt_count"]:
        return "role_dispatch_prompt_contract_ok"
    return ""


def _experience_marker_sources(
    marker: str,
    *,
    host_stdout: str,
    host_stderr: str,
    host_stdout_tail: str,
    host_stderr_tail: str,
) -> list[str]:
    sources: list[str] = []
    if marker in host_stdout_tail.lower():
        sources.append("host_stdout_tail")
    elif marker in host_stdout.lower():
        sources.append("host_stdout")
    if marker in host_stderr_tail.lower():
        sources.append("host_stderr_tail")
    elif marker in host_stderr.lower():
        sources.append("host_stderr")
    return sources


def _any_marker(text: str, *markers: str) -> bool:
    return any(marker.lower() in text for marker in markers)


def _todo_not_evidence_seen(text: str) -> bool:
    return "not_evidence" in text or "not evidence" in text


def _host_stream_json_events(*texts: str) -> list[dict]:
    events: list[dict] = []
    for text in texts:
        for line in str(text or "").splitlines():
            stripped = line.strip()
            if not stripped.startswith("{"):
                continue
            try:
                payload = json.loads(stripped)
            except ValueError:
                continue
            if isinstance(payload, dict):
                events.append(payload)
    return events


def _claude_stream_task_events(*texts: str) -> dict[str, object]:
    started: list[dict[str, str]] = []
    completed: list[dict[str, str]] = []
    for event in _host_stream_json_events(*texts):
        if event.get("type") != "system":
            continue
        subtype = str(event.get("subtype") or "")
        if subtype == "task_started":
            started.append(
                {
                    "task_id": _truncate_text(event.get("task_id"), limit=120),
                    "tool_use_id": _truncate_text(event.get("tool_use_id"), limit=120),
                    "subagent_type": _truncate_text(event.get("subagent_type"), limit=120),
                    "description": _truncate_text(event.get("description"), limit=180),
                }
            )
        elif subtype == "task_notification" and str(event.get("status") or "") == "completed":
            completed.append(
                {
                    "task_id": _truncate_text(event.get("task_id"), limit=120),
                    "tool_use_id": _truncate_text(event.get("tool_use_id"), limit=120),
                    "status": "completed",
                    "summary": _truncate_text(event.get("summary"), limit=180),
                }
            )
    return {
        "stream_json_seen": bool(_host_stream_json_events(*texts)),
        "task_started_count": len(started),
        "task_completed_count": len(completed),
        "task_started": started[-8:],
        "task_completed": completed[-8:],
    }


def _claude_role_dispatch_prompt_contract(*texts: str) -> dict[str, object]:
    prompts: list[dict[str, object]] = []
    for event in _host_stream_json_events(*texts):
        if event.get("type") != "assistant":
            continue
        message = event.get("message") if isinstance(event.get("message"), dict) else {}
        for item in list(message.get("content") or []):
            if not isinstance(item, dict) or item.get("type") != "tool_use":
                continue
            tool_name = str(item.get("name") or "").strip()
            if tool_name not in {"Agent", "Task"}:
                continue
            tool_input = item.get("input") if isinstance(item.get("input"), dict) else {}
            prompt = str(tool_input.get("prompt") or "").strip()
            reasons = _role_dispatch_prompt_violation_reasons(prompt)
            prompts.append(
                {
                    "tool_name": tool_name,
                    "subagent_type": _truncate_text(tool_input.get("subagent_type"), limit=120),
                    "description": _truncate_text(tool_input.get("description"), limit=180),
                    "copied_compact_prompt": not reasons,
                    "violation_reasons": reasons,
                    "prompt_preview": _truncate_text(prompt, limit=260),
                }
            )
    violations = [item for item in prompts if item["violation_reasons"]]
    return {
        "agent_task_prompt_count": len(prompts),
        "copied_compact_prompt_count": len(prompts) - len(violations),
        "violation_count": len(violations),
        "violations": violations[:6],
    }


def _role_dispatch_prompt_violation_reasons(prompt: str) -> list[str]:
    if not prompt:
        return ["missing_prompt"]
    reasons: list[str] = []
    if not prompt.startswith("Use this exact string as the whole Agent/Task prompt"):
        reasons.append("not_compact_dispatch_message")
    if prompt.startswith("You are running as"):
        reasons.append("custom_role_preamble")
    if "Do the following:" in prompt:
        reasons.append("appended_task_instructions")
    if "target_agent:" in prompt:
        reasons.append("colon_anchor_rewrite")
    return reasons


def _experience_auto_repair_events(host_stdout: str, host_stderr: str) -> list[dict]:
    rows: list[dict] = []
    for source, text in (("host_stdout_tail", host_stdout), ("host_stderr_tail", host_stderr)):
        for line in text.splitlines():
            line_lower = line.lower()
            if "auto_repair" in line_lower or "auto repair" in line_lower:
                rows.append({"source": source, "line": _truncate_text(line.strip(), limit=240)})
    return rows[:8]


def _experience_artifact_contracts(workdir: Path, run_path: Path) -> dict[str, object]:
    contracts: dict[str, object] = {
        "agent_work_panel_exposed": False,
        "agent_work_panel_sources": [],
        "native_todo_seen": False,
        "native_todo_not_evidence": False,
        "role_dispatch_seen": False,
    }
    work_panel_sources: list[str] = []
    for path, payload in _experience_contract_payloads(workdir, run_path):
        work_panels = [item for item in _iter_nested_key(payload, "agent_work_panel") if isinstance(item, dict)]
        if work_panels:
            contracts["agent_work_panel_exposed"] = True
            work_panel_sources.append(_experience_artifact_source(path, workdir=workdir, run_path=run_path))
        native_todos = [item for item in _iter_nested_key(payload, "native_todo") if isinstance(item, dict)]
        if native_todos:
            contracts["native_todo_seen"] = True
        if any(item.get("not_evidence") is True for item in native_todos):
            contracts["native_todo_not_evidence"] = True
        if any(isinstance(item, dict) and item for item in _iter_nested_key(payload, "role_dispatch")):
            contracts["role_dispatch_seen"] = True
    contracts["agent_work_panel_sources"] = list(dict.fromkeys(work_panel_sources))[:8]
    return contracts


def _experience_contract_payloads(workdir: Path, run_path: Path) -> list[tuple[Path, dict]]:
    paths: list[Path] = []
    if run_path != Path():
        paths.extend(sorted(run_path.glob("agent_native/**/*.json"))[-12:])
        paths.extend(sorted(run_path.glob("iterations/**/agent_step_view.json"))[-12:])
    paths.extend(sorted((state_dir_for_workdir(workdir) / "agent_outbox").glob("**/*.result.template.json"))[-12:])
    return [(path, payload) for path in paths if (payload := _safe_read_json(path))]


def _experience_artifact_source(path: Path, *, workdir: Path, run_path: Path) -> str:
    if run_path != Path():
        with suppress(ValueError):
            relative = path.relative_to(run_path)
            if relative.parts[:1] == ("agent_native",):
                return "run_agent_native_artifact"
            if "agent_step_view.json" in relative.parts:
                return "agent_step_view"
    with suppress(ValueError):
        relative = path.relative_to(state_dir_for_workdir(workdir))
        if relative.parts[:1] == ("agent_outbox",):
            return "result_template"
    return "loopora_artifact"


def _iter_nested_key(value: object, key: str):
    if isinstance(value, dict):
        if key in value:
            yield value[key]
        for child in value.values():
            yield from _iter_nested_key(child, key)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_nested_key(child, key)


def _experience_native_trace_observed(run_path: Path) -> bool:
    if run_path == Path():
        return False
    state = _safe_read_json(run_path / "agent_native" / "state.json")
    dispatches = state.get("host_dispatches") if isinstance(state.get("host_dispatches"), list) else []
    for item in dispatches:
        if not isinstance(item, dict):
            continue
        native_trace = item.get("native_trace")
        native_trace_ref = str(item.get("native_trace_ref") or "").strip()
        if native_trace_ref:
            return True
        if isinstance(native_trace, dict) and native_trace:
            return True
        if isinstance(native_trace, str) and native_trace.strip():
            return True
    return False


def _phase_statuses(inputs: PhaseStatusInput) -> dict[str, dict]:
    run_id = str(inputs.binding.get("linked_run_id") or "").strip()
    invocations = list(inputs.binding.get("entry_invocations") or []) if isinstance(inputs.binding.get("entry_invocations"), list) else []
    actions = [str(item.get("action") or "") for item in invocations if isinstance(item, dict)]
    plan_seen = any(action in {"plan", "gen"} for action in actions)
    run_seen = any(action in {"run", "loop"} for action in actions)

    def event_seen(event_type: str, step_id: str | None = None) -> bool:
        return any(
            event.get("event_type") == event_type and (step_id is None or (event.get("payload") or {}).get("step_id") == step_id)
            for event in inputs.events
            if isinstance(event.get("payload") or {}, dict)
        )

    return {
        "host_process_started": {"ok": True, "detail": "host command was started by the harness"},
        "candidate_file_created": {
            "ok": _candidate_file(inputs.adapter, inputs.workdir).exists(),
            "path": str(_candidate_file(inputs.adapter, inputs.workdir)),
        },
        "plan_invocation_observed": {"ok": plan_seen},
        "gen_invocation_observed": {"ok": plan_seen},
        "ready_validation_observed": {"ok": any(item.get("ok") is True for item in inputs.validation_summaries)},
        "run_invocation_observed": {"ok": run_seen},
        "loop_invocation_observed": {"ok": run_seen},
        "linked_run_created": {"ok": bool(run_id), "run_id": run_id},
        "runtime_activity_observed_run": {"ok": bool(run_id) and _runtime_activity_observed_run(inputs.activity_snapshots, run_id)},
        "returned_run_url_observed": _returned_run_url_status(inputs.activity_snapshots, run_id),
        "builder_claimed": {"ok": event_seen("agent_native_step_claimed", "builder_step")},
        "builder_submitted": {"ok": event_seen("agent_native_step_submitted", "builder_step")},
        "gatekeeper_claimed": {"ok": event_seen("agent_native_step_claimed", "gatekeeper_step")},
        "gatekeeper_submitted": {"ok": event_seen("agent_native_step_submitted", "gatekeeper_step")},
        "terminal_run_finished": {"ok": any(event.get("event_type") == "run_finished" for event in inputs.events)},
        "task_verdict_passed": {
            "ok": any(
                event.get("event_type") == "run_finished"
                and (event.get("payload") or {}).get("task_verdict_status") == "passed"
                for event in inputs.events
                if isinstance(event.get("payload") or {}, dict)
            )
        },
    }


def _runtime_activity_observed_run(activity_snapshots: list[dict], run_id: str) -> bool:
    return any(
        item.get("id") == run_id
        and item.get("status") in {"queued", "running", "awaiting_agent"}
        and (snapshot.get("runtime_visibility_source") or "runtime_activity") == "runtime_activity"
        for snapshot in activity_snapshots
        for item in list(snapshot.get("runs") or [])
        if isinstance(item, dict)
    )


def _returned_run_url_status(activity_snapshots: list[dict], run_id: str) -> dict[str, object]:
    phases: list[str] = []
    statuses: list[str] = []
    for snapshot in activity_snapshots:
        if snapshot.get("runtime_visibility_source") != "returned_run_url":
            continue
        for item in list(snapshot.get("runs") or []):
            if not isinstance(item, dict) or item.get("id") != run_id:
                continue
            status = str(item.get("status") or "").strip()
            if status:
                statuses.append(status)
            phase = str(snapshot.get("returned_run_url_phase") or "during_process").strip()
            if phase:
                phases.append(phase)
    return {
        "ok": bool(statuses),
        "phase": phases[-1] if phases else "",
        "phases": list(dict.fromkeys(phases)),
        "statuses": list(dict.fromkeys(statuses)),
        "diagnostic_only": bool(phases) and all(phase == "post_exit_diagnostic_only" for phase in phases),
    }


def _runtime_visibility_sources(activity_snapshots: list[dict], run_id: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for snapshot in activity_snapshots:
        source = str(snapshot.get("runtime_visibility_source") or "runtime_activity").strip() or "runtime_activity"
        phase = str(snapshot.get("returned_run_url_phase") or "").strip()
        for item in list(snapshot.get("runs") or []):
            if not isinstance(item, dict) or item.get("id") != run_id:
                continue
            rows.append(
                {
                    "source": source,
                    "phase": phase,
                    "status": str(item.get("status") or "").strip(),
                    "active_runtime_activity": source == "runtime_activity" and item.get("status") in {"queued", "running", "awaiting_agent"},
                }
            )
    return rows[-12:]


def _build_real_probe_phase_report(
    *,
    adapter: str,
    workdir: Path,
    activity_snapshots: list[dict],
    sentinel_log: Path,
    host_signals: PhaseReportHostSignals,
) -> dict:
    binding = _latest_binding(adapter, workdir)
    run_id = str(binding.get("linked_run_id") or "").strip()
    run_path = _run_dir(workdir, run_id) if run_id else Path()
    events = _read_jsonl(run_path / "events.jsonl") if run_id else []
    validation_summaries = _alignment_validation_summaries(workdir)
    candidate = _candidate_file(adapter, workdir)
    proof_file = workdir / "loopora-agent-release-proof.json"
    return {
        "schema_version": 1,
        "adapter": adapter,
        "workdir": str(workdir),
        "command_preview": _truncate_text(host_signals.command, limit=500),
        "model_policy": _model_policy_summary(adapter, host_signals.command),
        "phase_statuses": _phase_statuses(
            PhaseStatusInput(
                adapter=adapter,
                workdir=workdir,
                binding=binding,
                activity_snapshots=activity_snapshots,
                events=events,
                validation_summaries=validation_summaries,
            )
        ),
        "diagnostics": {
            "candidate": {
                "path": str(candidate),
                "exists": candidate.exists(),
                "size_bytes": candidate.stat().st_size if candidate.exists() else 0,
                "first_lines": candidate.read_text(encoding="utf-8").splitlines()[:8] if candidate.exists() else [],
            },
            "alignment_validations": validation_summaries,
            "binding": _binding_summary(binding),
            "runtime_activity": _activity_summaries(activity_snapshots),
            "runtime_visibility_sources": _runtime_visibility_sources(activity_snapshots, run_id) if run_id else [],
            "events_tail": _event_summaries(events),
            "agent_native_state": _state_summary(run_path / "agent_native" / "state.json") if run_id else {},
            "experience_health": _experience_health_summary(
                workdir=workdir,
                run_path=run_path,
                host_stdout=host_signals.stdout,
                host_stderr=host_signals.stderr,
            ),
            "coverage": _projection_summary(
                run_path / "evidence" / "coverage.json",
                keys=("status", "covered_check_count", "missing_check_count", "missing_check_ids", "latest_gatekeeper", "top_gaps"),
            )
            if run_id
            else {},
            "task_verdict": _projection_summary(run_path / "evidence" / "task_verdict.json", keys=("status", "source", "summary", "buckets"))
            if run_id
            else {},
            "role_outputs": _role_outputs_summary(run_path) if run_id else {},
            "proof_file": {"path": str(proof_file), "exists": proof_file.exists()},
            "sentinel_log": {
                "path": str(sentinel_log),
                "exists": sentinel_log.exists(),
                "preview": _truncate_text(sentinel_log.read_text(encoding="utf-8") if sentinel_log.exists() else "", limit=500),
            },
        },
    }


def _write_real_probe_phase_report(
    *,
    adapter: str,
    workdir: Path,
    activity_snapshots: list[dict],
    sentinel_log: Path,
    host_signals: PhaseReportHostSignals,
) -> tuple[dict, Path]:
    raw_report = _build_real_probe_phase_report(
        adapter=adapter,
        workdir=workdir,
        activity_snapshots=activity_snapshots,
        sentinel_log=sentinel_log,
        host_signals=host_signals,
    )
    report = redact_sensitive_value("", raw_report)
    if not isinstance(report, dict):
        report = {}
    path = _phase_report_path(workdir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report, path


def _compact_phase_report(report: dict) -> dict:
    diagnostics = report.get("diagnostics") if isinstance(report.get("diagnostics"), dict) else {}
    return {
        "adapter": report.get("adapter"),
        "workdir": report.get("workdir"),
        "model_policy": report.get("model_policy"),
        "phase_statuses": report.get("phase_statuses"),
        "binding": diagnostics.get("binding"),
        "alignment_validations": diagnostics.get("alignment_validations"),
        "runtime_visibility_sources": diagnostics.get("runtime_visibility_sources"),
        "experience_health": diagnostics.get("experience_health"),
        "coverage": diagnostics.get("coverage"),
        "task_verdict": diagnostics.get("task_verdict"),
        "events_tail": diagnostics.get("events_tail"),
        "sentinel_log": diagnostics.get("sentinel_log"),
    }


def _format_real_probe_diagnostic_failure(message: object, *, report: dict, report_path: Path) -> str:
    compact = json.dumps(_compact_phase_report(report), ensure_ascii=False, indent=2)
    return f"{message}\n\nReal probe phase report: {report_path}\n{compact}"


def _loopora_service(loopora_home: Path) -> LooporaService:
    return LooporaService(
        repository=LooporaRepository(loopora_home / "app.db"),
        settings=AppSettings(max_concurrent_runs=1, polling_interval_seconds=0.1, stop_grace_period_seconds=0.5),
    )


def _wait_for_terminal_run(loopora_home: Path, run_id: str, *, timeout: float) -> dict:
    service = _loopora_service(loopora_home)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        run = service.get_run(run_id)
        if run["status"] in TERMINAL_RUN_STATUSES:
            return run
        time.sleep(0.5)
    run = service.get_run(run_id)
    if run["status"] in {"queued", "running", "awaiting_agent"}:
        service.stop_run(run_id)
    raise AssertionError(f"Timed out waiting for Agent-started run {run_id} to finish; last status={run['status']}")


def _write_custom_executor(workdir: Path) -> Path:
    script = workdir / "loopora_agent_release_executor.py"
    script.write_text(
        """from __future__ import annotations

import json
from pathlib import Path
import sys

role = sys.argv[1]
output_path = Path(sys.argv[2])
_prompt = sys.argv[3]
if role == "gatekeeper":
    payload = {
        "passed": True,
        "decision_summary": "Agent adapter release-profile probe passed with supporting upstream Builder evidence.",
        "feedback_to_builder": "",
        "feedback_to_generator": "",
        "blocking_issues": [],
        "hard_constraint_violations": [],
        "metrics": [{"name": "quality_score", "value": 1.0, "threshold": 0.9, "passed": True}],
        "metric_scores": {
            "check_pass_rate": {"value": 1.0, "threshold": 1.0, "passed": True},
            "quality_score": {"value": 1.0, "threshold": 0.9, "passed": True},
        },
        "failed_check_ids": [],
        "priority_failures": [],
        "composite_score": 1.0,
        "evidence_refs": ["ev_000_00_builder_step"],
        "evidence_claims": ["The upstream Builder evidence confirms the managed run binding, structured result, and evidence-backed verdict path."],
        "residual_risks": [],
        "coverage_results": [
            {
                "target_id": "done_when.check_001",
                "status": "covered",
                "evidence_refs": ["ev_000_00_builder_step"],
                "note": "The managed binding and run URL were present before GateKeeper closed the run.",
            },
            {
                "target_id": "done_when.check_002",
                "status": "covered",
                "evidence_refs": ["ev_000_00_builder_step"],
                "note": "Builder returned the structured probe result with a concrete proof file.",
            },
            {
                "target_id": "done_when.check_003",
                "status": "covered",
                "evidence_refs": ["ev_000_00_builder_step"],
                "note": "GateKeeper inspected and cited the exact upstream Builder evidence id.",
            },
            {
                "target_id": "fake_done.risk_001",
                "status": "covered",
                "evidence_refs": ["ev_000_00_builder_step"],
                "note": "The verdict relies on Builder evidence, not only run visibility.",
            },
            {
                "target_id": "fake_done.risk_002",
                "status": "covered",
                "evidence_refs": ["ev_000_00_builder_step"],
                "note": "The pass cites upstream evidence rather than an unsupported GateKeeper assertion.",
            },
            {
                "target_id": "evidence_preference.pref_001",
                "status": "covered",
                "evidence_refs": ["ev_000_00_builder_step"],
                "note": "The verdict is projected through the task verdict buckets.",
            },
            {
                "target_id": "evidence_preference.pref_002",
                "status": "covered",
                "evidence_refs": ["ev_000_00_builder_step"],
                "note": "Evidence references use exact known evidence ids.",
            },
        ],
    }
else:
    proof_path = Path("loopora-agent-release-proof.json")
    proof_path.write_text(
        json.dumps(
            {
                "candidate_bundle": "conversation-generated",
                "managed_entry": "loopora-plan before loopora-run",
                "runtime_activity": "observed by the host release-profile probe",
                "agent_native_submission": "builder handoff is available for GateKeeper",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\\n",
        encoding="utf-8",
    )
    payload = {
        "attempted": "Verified the Loopora Agent adapter can start a managed run and wrote a release proof file.",
        "abandoned": "No product changes were needed for this release-profile probe.",
        "assumption": "The release proof file is sufficient upstream evidence for this deterministic adapter gate.",
        "summary": "Custom executor wrote a structured Builder result and proof file for the Agent adapter release-profile probe.",
        "changed_files": [],
        "proof_files": [str(proof_path)],
        "proof_artifacts": [],
        "artifact_paths": [],
    }
output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
print(json.dumps({"type": "stdout", "message": f"loopora-agent-release-executor complete: {role}"}))
""",
        encoding="utf-8",
    )
    return script


def _stop_host_process(process: subprocess.Popen[str], *, graceful: bool = False) -> None:
    if process.poll() is not None:
        return
    if graceful:
        process.terminate()
    else:
        process.kill()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _write_monitor_phase_report(
    request: HostCommandMonitorRequest,
    activity_snapshots: list[dict],
    *,
    host_stdout: str = "",
    host_stderr: str = "",
) -> tuple[dict, Path]:
    return _write_real_probe_phase_report(
        adapter=request.adapter,
        workdir=request.workdir,
        activity_snapshots=activity_snapshots,
        sentinel_log=request.sentinel_log,
        host_signals=PhaseReportHostSignals(command=request.command, stdout=host_stdout, stderr=host_stderr),
    )


def _record_runtime_activity(request: HostCommandMonitorRequest, activity_snapshots: list[dict]) -> None:
    try:
        activity = _fetch_runtime_activity(request.agent_web_url)
        activity_snapshots.append(activity)
    except (AssertionError, json.JSONDecodeError, OSError, TimeoutError):
        pass


def _record_returned_run_url_visibility(
    request: HostCommandMonitorRequest,
    activity_snapshots: list[dict],
    *,
    phase: str = "during_process",
) -> None:
    binding = _linked_run_binding(request.adapter, request.workdir)
    run_id = str((binding or {}).get("linked_run_id") or "").strip()
    if not run_id:
        return
    try:
        run = _fetch_returned_run_url(request.agent_web_url, run_id)
    except (AssertionError, json.JSONDecodeError, OSError, TimeoutError):
        return
    status = str(run.get("status") or "").strip()
    activity_snapshots.append(
        {
            "runtime_visibility_source": "returned_run_url",
            "returned_run_url_phase": phase,
            "running_count": 1 if status == "running" else 0,
            "queued_count": 1 if status == "queued" else 0,
            "awaiting_agent_count": 1 if status == "awaiting_agent" else 0,
            "runs": [{"id": run_id, "status": status, "run_path": f"/runs/{run_id}"}],
        }
    )


def _raise_host_command_timeout(
    request: HostCommandMonitorRequest,
    process: subprocess.Popen[str],
    stdout_file,
    stderr_file,
    activity_snapshots: list[dict],
) -> None:
    _stop_host_process(process)
    stdout_file.flush()
    stderr_file.flush()
    stdout = Path(stdout_file.name).read_text(encoding="utf-8", errors="replace")
    stderr = Path(stderr_file.name).read_text(encoding="utf-8", errors="replace")
    phase_report, phase_report_path = _write_monitor_phase_report(
        request,
        activity_snapshots,
        host_stdout=stdout,
        host_stderr=stderr,
    )
    raise AssertionError(
        _format_real_probe_diagnostic_failure(
            f"timed out waiting for real {request.adapter} Agent host command\nstdout:\n{stdout}\nstderr:\n{stderr}",
            report=phase_report,
            report_path=phase_report_path,
        )
    ) from None


def _raise_host_command_failure(
    request: HostCommandMonitorRequest,
    completed: subprocess.CompletedProcess[str],
    activity_snapshots: list[dict],
) -> None:
    phase_report, phase_report_path = _write_monitor_phase_report(
        request,
        activity_snapshots,
        host_stdout=completed.stdout,
        host_stderr=completed.stderr,
    )
    raise AssertionError(
        _format_real_probe_diagnostic_failure(
            f"real {request.adapter} Agent host command exited {completed.returncode}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
            report=phase_report,
            report_path=phase_report_path,
        )
    ) from None


def _phase_report_has_terminal_proof_and_work_panel(phase_report: dict) -> bool:
    statuses = phase_report.get("phase_statuses", {})
    health = phase_report.get("diagnostics", {}).get("experience_health", {})
    return (
        bool(statuses.get("task_verdict_passed", {}).get("ok"))
        and bool(statuses.get("runtime_activity_observed_run", {}).get("ok"))
        and (bool(health.get("agent_work_panel_seen")) or bool(health.get("agent_work_panel_artifact_exposed")))
    )


def _read_and_remove_temp_text(path: str) -> str:
    temp_path = Path(path)
    text = temp_path.read_text(encoding="utf-8", errors="replace")
    temp_path.unlink(missing_ok=True)
    return text


def _wait_for_host_command_with_runtime_monitoring(request: HostCommandMonitorRequest) -> HostCommandMonitorResult:
    deadline = time.monotonic() + request.timeout
    terminal_proof_grace = float(os.environ.get(TERMINAL_PROOF_GRACE_ENV, "30"))
    terminal_proof_seen_at: float | None = None
    returncode_override: int | None = None
    activity_snapshots: list[dict] = []
    with tempfile.NamedTemporaryFile(
        "w+", prefix="loopora-real-agent-stdout-", suffix=".log", encoding="utf-8", delete=False
    ) as stdout_file, tempfile.NamedTemporaryFile(
        "w+", prefix="loopora-real-agent-stderr-", suffix=".log", encoding="utf-8", delete=False
    ) as stderr_file:
        process = subprocess.Popen(request.command, cwd=request.workdir, env=request.env, shell=True, text=True, stdout=stdout_file, stderr=stderr_file)
        last_report_at = 0.0
        try:
            while process.poll() is None:
                now = time.monotonic()
                if now >= deadline:
                    _raise_host_command_timeout(request, process, stdout_file, stderr_file, activity_snapshots)
                _record_runtime_activity(request, activity_snapshots)
                if now - last_report_at >= 2:
                    _record_returned_run_url_visibility(request, activity_snapshots)
                    stdout_file.flush()
                    stderr_file.flush()
                    phase_report, _ = _write_monitor_phase_report(
                        request,
                        activity_snapshots,
                        host_stdout=_read_tail_text(Path(stdout_file.name)),
                        host_stderr=_read_tail_text(Path(stderr_file.name)),
                    )
                    last_report_at = now
                    if _phase_report_has_terminal_proof_and_work_panel(phase_report):
                        terminal_proof_seen_at = terminal_proof_seen_at or now
                        if now - terminal_proof_seen_at >= terminal_proof_grace:
                            _stop_host_process(process, graceful=True)
                            returncode_override = 0
                            break
                    else:
                        terminal_proof_seen_at = None
                time.sleep(0.5)
        finally:
            _stop_host_process(process)
    stdout = _read_and_remove_temp_text(stdout_file.name)
    stderr = _read_and_remove_temp_text(stderr_file.name)
    _record_returned_run_url_visibility(request, activity_snapshots, phase="post_exit_diagnostic_only")
    completed = subprocess.CompletedProcess(request.command, returncode_override if returncode_override is not None else int(process.returncode or 0), stdout, stderr)
    if completed.returncode != 0:
        _raise_host_command_failure(request, completed, activity_snapshots)
    binding = _linked_run_binding(request.adapter, request.workdir)
    if binding is None:
        try:
            binding = _wait_for_run_binding(request.adapter, request.workdir, timeout=30)
        except AssertionError as exc:
            phase_report, phase_report_path = _write_monitor_phase_report(
                request,
                activity_snapshots,
                host_stdout=completed.stdout,
                host_stderr=completed.stderr,
            )
            message = (
                f"{exc}\n"
                f"host returncode: {completed.returncode}\n"
                f"host stdout:\n{completed.stdout}\n"
                f"host stderr:\n{completed.stderr}"
            )
            raise AssertionError(_format_real_probe_diagnostic_failure(message, report=phase_report, report_path=phase_report_path)) from None
    phase_report, phase_report_path = _write_monitor_phase_report(
        request,
        activity_snapshots,
        host_stdout=completed.stdout,
        host_stderr=completed.stderr,
    )
    return HostCommandMonitorResult(
        completed=completed,
        binding=binding,
        activity_snapshots=activity_snapshots,
        phase_report=phase_report,
        phase_report_path=phase_report_path,
    )


def _assert_runtime_activity_observed_run(activity_snapshots: list[dict], run_id: str) -> None:
    assert activity_snapshots, "runtime activity endpoint was not observed while the host command was running"
    assert _runtime_activity_observed_run(activity_snapshots, run_id), activity_snapshots[-3:]


def _assert_alignment_session_came_from_conversation(workdir: Path, run_id: str) -> None:
    manifests = sorted((workdir / ".loopora" / "alignment_sessions").glob("*/manifest.json"))
    assert manifests
    manifest = json.loads(manifests[-1].read_text(encoding="utf-8"))
    assert manifest["linked_run_id"] == run_id
    assert manifest["linked_bundle_id"]
    assert manifest["message_count"] >= 2
    assert manifest["paths"]["transcript"] == "conversation/transcript.jsonl"
    assert (Path(manifest["bundle_path"])).exists()


def _assert_run_observation_chain(workdir: Path, run_id: str, adapter: str) -> None:
    events = _read_jsonl(workdir / ".loopora" / "runs" / run_id / "events.jsonl")
    assert events
    event_types = [str(event.get("event_type") or "") for event in events]
    for step_id in ("builder_step", "gatekeeper_step"):
        for event_type in (
            "step_instruction_context_prepared",
            "role_request_prepared",
            "agent_native_step_claimed",
            "agent_native_step_submitted",
        ):
            assert any(event.get("event_type") == event_type and (event.get("payload") or {}).get("step_id") == step_id for event in events)
    run_finished = [event for event in events if event.get("event_type") == "run_finished"]
    assert run_finished
    assert run_finished[-1]["payload"]["status"] == "succeeded"
    assert run_finished[-1]["payload"]["task_verdict_status"] == "passed"
    submitted = [event for event in events if event.get("event_type") == "agent_native_step_submitted"]
    assert len(submitted) >= 2
    for event in submitted:
        dispatch = (event.get("payload") or {}).get("host_dispatch") or {}
        assert dispatch.get("adapter") == adapter
        assert dispatch.get("actual_agent") == dispatch.get("target_agent")
        assert dispatch.get("inline") is False
    assert event_types.index("step_instruction_context_prepared") < event_types.index("run_finished")


def _assert_experience_visible_work_panel(phase_report: dict, phase_report_path: Path) -> None:
    health = phase_report.get("diagnostics", {}).get("experience_health", {})
    if health.get("agent_work_panel_seen") is True:
        return
    if health.get("agent_work_panel_artifact_exposed") is True:
        return
    raise AssertionError(
        _format_real_probe_diagnostic_failure(
            "real Agent host did not expose the required agent_work_panel block in stdout/stderr or Loopora experience artifacts",
            report=phase_report,
            report_path=phase_report_path,
        )
    ) from None


def _assert_claude_role_dispatch_prompt_contract(phase_report: dict, phase_report_path: Path) -> None:
    health = phase_report.get("diagnostics", {}).get("experience_health", {})
    contract = health.get("role_dispatch_prompt_contract") if isinstance(health.get("role_dispatch_prompt_contract"), dict) else {}
    violation_count = int(contract.get("violation_count") or 0)
    copied_count = int(contract.get("copied_compact_prompt_count") or 0)
    if violation_count:
        raise AssertionError(
            _format_real_probe_diagnostic_failure(
                "Claude Agent/Task role prompts must copy summary.next_role_dispatch_message as the whole prompt; "
                "custom role preambles, appended task instructions, or colon-anchor rewrites were observed",
                report=phase_report,
                report_path=phase_report_path,
            )
        ) from None
    if copied_count < 2:
        raise AssertionError(
            _format_real_probe_diagnostic_failure(
                "Claude Agent/Task stream did not expose compact role-dispatch prompts for both Builder and GateKeeper",
                report=phase_report,
                report_path=phase_report_path,
            )
        ) from None


def _assert_no_release_prompt_polluted_validation(phase_report: dict, phase_report_path: Path) -> None:
    validations = phase_report.get("diagnostics", {}).get("alignment_validations")
    polluted = []
    workdir_placeholder = []
    unsafe_prompt_ref = []
    for item in list(validations or []):
        if not isinstance(item, dict):
            continue
        text = " ".join([str(item.get("error") or ""), *[str(issue) for issue in list(item.get("issues") or [])]])
        if "observed workdir stack" in text:
            polluted.append(item)
        if "loop.workdir must be" in text and "$PWD" in text:
            workdir_placeholder.append(item)
        if "prompt_ref must be a safe relative path" in text:
            unsafe_prompt_ref.append(item)
    if polluted:
        raise AssertionError(
            _format_real_probe_diagnostic_failure(
                "real Agent release prompt polluted the candidate bundle with a semantic-lint trigger phrase; "
                "rewrite the probe prompt so negative environment/stack guidance is not copied into spec.markdown",
                report=phase_report,
                report_path=phase_report_path,
            )
        ) from None
    if workdir_placeholder:
        raise AssertionError(
            _format_real_probe_diagnostic_failure(
                "real Agent release prompt allowed loop.workdir to be authored as a shell placeholder; "
                "the candidate must use the exact absolute workdir path before the first /loopora-plan call",
                report=phase_report,
                report_path=phase_report_path,
            )
        ) from None
    if unsafe_prompt_ref:
        raise AssertionError(
            _format_real_probe_diagnostic_failure(
                "real Agent release prompt allowed unsafe or URI-style prompt_ref values; "
                "role prompt_ref values must be safe relative paths before the first /loopora-plan call",
                report=phase_report,
                report_path=phase_report_path,
            )
        ) from None


def _assert_release_probe_candidate_validated_without_repair(phase_report: dict, phase_report_path: Path) -> None:
    validations = [item for item in list(phase_report.get("diagnostics", {}).get("alignment_validations") or []) if isinstance(item, dict)]
    failed_validations = [item for item in validations if item.get("ok") is not True]
    if not validations or failed_validations:
        raise AssertionError(
            _format_real_probe_diagnostic_failure(
                "real Agent release probe should produce a READY candidate on the first managed /loopora-plan call; "
                "failed validation followed by repair hides an intermediate experience regression",
                report=phase_report,
                report_path=phase_report_path,
            )
        ) from None
    binding = phase_report.get("diagnostics", {}).get("binding") if isinstance(phase_report.get("diagnostics"), dict) else {}
    entry_invocations = list(binding.get("entry_invocations") or []) if isinstance(binding, dict) else []
    plan_invocations = [
        item
        for item in entry_invocations
        if isinstance(item, dict) and _canonical_entry_action(item.get("action")) == "plan" and item.get("entry_source") == "claude_project_skill"
    ]
    run_invocations = [
        item
        for item in entry_invocations
        if isinstance(item, dict) and _canonical_entry_action(item.get("action")) == "run" and item.get("entry_source") == "claude_project_skill"
    ]
    if len(plan_invocations) != 1 or len(run_invocations) != 1:
        raise AssertionError(
            _format_real_probe_diagnostic_failure(
                "real Agent release probe should invoke the managed plan entry once, then the managed run entry once; "
                "extra plan retries indicate the candidate was not cleanly authored on the first pass",
                report=phase_report,
                report_path=phase_report_path,
            )
        ) from None


def _agent_label(adapter: str) -> str:
    return {
        "codex": "Codex",
        "claude": "Claude Code",
        "opencode": "OpenCode",
    }.get(adapter, adapter)


def _entry_source(adapter: str) -> str:
    if adapter == "opencode":
        return "opencode_project_command"
    return f"{adapter}_project_skill"


def _entry_file_hint(adapter: str) -> str:
    if adapter == "claude":
        return ".claude/skills/loopora-plan/SKILL.md and .claude/skills/loopora-run/SKILL.md"
    if adapter == "opencode":
        return ".opencode/commands/loopora-plan.md and .opencode/commands/loopora-run.md"
    return ".agents/skills/loopora-plan/SKILL.md and .agents/skills/loopora-run/SKILL.md"


def _release_probe_workdir_for_bundle(bundle_file: Path) -> Path:
    if len(bundle_file.parents) >= 4 and bundle_file.parents[1].name == "agent_inbox" and bundle_file.parents[2].name == ".loopora":
        return bundle_file.parents[3]
    return bundle_file.parent


def _release_probe_prompt(adapter: str, bundle_file: Path, executor_script: Path) -> str:
    workdir = _release_probe_workdir_for_bundle(bundle_file)
    return f"""# Loopora Agent Adapter Release Gate

Use the Loopora {_agent_label(adapter)} project entry installed in this workdir. If this non-interactive host does not expose native slash commands directly, inspect the installed project entry files and follow their instructions.

Current task: prove the installed Loopora Agent entry can guide a short task conversation into a READY bundle, start a managed run, expose runtime activity, and finish through Agent-native step submission.

This is an execution task, not a planning task. You may think through a checklist, but do not return a todo-only response or stop after creating a plan. Because this host is non-interactive, do not end a response after preparatory commands such as `ls`, `test -f`, `mkdir -p`, or reading files. After creating the candidate directory, immediately continue in the same uninterrupted execution sequence to write the candidate file and invoke the installed entries. Your final response is only valid after the candidate file exists, `/loopora-plan` has returned READY, `/loopora-run` has returned `complete: true`, the Builder and GateKeeper wrapper submissions have been accepted, a run binding exists, the terminal run status and task verdict have been observed, and the final main-session answer visibly includes a literal `agent_work_panel:` block.

Before any final success sentence, print this user-visible block in the main host session, using values copied from the latest `agent_v3_envelope.summary.agent_work_panel` when available:

```text
agent_work_panel:
state: <latest state>
next_action: <latest next_action>
evidence_focus: <latest evidence_focus>
todo_items: <latest todo items or []>
```

The `agent_work_panel:` block is an experience-health signal for the real probe, not Loopora task proof.

Author the candidate bundle from the conversation brief below and save it to `{bundle_file}`. Create the parent directory if needed. The pytest harness deliberately does not pre-create, prewrite, or embed a complete candidate YAML; this real probe must prove the host can turn conversation guidance into a bundle before invoking `/loopora-plan`.

Before invoking anything, read these installed project entry files: `{_entry_file_hint(adapter)}`. Use them as the only source for shell command syntax, and preserve their provenance markers exactly.

Use these requirements to author, not copy, the candidate:

- Produce one raw `version: 1` Loopora bundle file, with no Markdown fences or prose outside YAML.
- The first non-whitespace characters in the file must be exactly `version: 1`; do not add a heading, explanation, code fence, or document separator before it.
- Use metadata name `agent-adapter-release-profile-probe` and describe it as a release-profile probe for Loopora Agent managed entry and Agent-native submission.
- Explain in `collaboration_summary` that one Agent pass cannot prove the whole managed-entry contract, so Loopora must govern candidate validation, managed run binding, runtime visibility, native role dispatch, exact evidence refs, and evidence-backed verdict buckets.
- Use `completion_mode: gatekeeper`, `executor_kind: custom`, `executor_mode: command`, `command_cli: {sys.executable}`, and this executor script for both the loop defaults and the role definitions: `{executor_script}`.
- Set `loop.workdir` exactly to `{workdir}`. Do not use `$PWD`, `${{PWD}}`, `.`, relative paths, or any shell placeholder in `loop.workdir`.
- Keep `model` and `reasoning_effort` blank everywhere so the probe delegates model and reasoning configuration to the current host/provider defaults.
- The Builder command args must pass the executor script, the literal role `builder`, `{{output_path}}`, and `{{prompt}}`; the GateKeeper command args must pass the executor script, the literal role `gatekeeper`, `{{output_path}}`, and `{{prompt}}`.
- Keep the workflow minimal and explicit: `builder_step` runs first; `gatekeeper_step` reads `handoffs_from: [builder_step]`, queries Builder evidence, and uses `on_pass: finish_run`.
- The Builder role must create `loopora-agent-release-proof.json` and return it in `proof_files`.
- The GateKeeper role must cite only exact upstream Builder evidence ids from `known_evidence_ids`, use `covered` as the coverage status for satisfied targets, and keep Proven, Weak, Unproven, Blocking, and Residual risk as verdict bucket prose.
- The GateKeeper result for this release gate must keep `residual_risks: []`. If any residual risk remains, set `passed: false`; do not submit a residual-risk pass.
- The spec must include Task, Done When, Success Surface, Guardrails, Fake Done, Evidence Preferences, and Residual Risk sections covering managed entry provenance, runtime visibility, Builder proof evidence, GateKeeper exact evidence refs, task verdict buckets, no nested host CLI, and the limited residual risk of non-interactive host-native role dispatch.
- Set Builder `prompt_ref` exactly to `roles/release-proof-builder.md` and GateKeeper `prompt_ref` exactly to `roles/release-gatekeeper.md`. Do not leave `prompt_ref` blank, use `local://`, use an absolute path, or use any URI-style value.
- Set Builder role `description` exactly to `Release proof Builder role for the Loopora Agent release-profile probe.` and GateKeeper role `description` exactly to `Release GateKeeper role for the Loopora Agent release-profile probe.` Keep both descriptions as quoted YAML strings. Do not place literal result-schema snippets such as `residual_risks: []`, `proof_files: [...]`, or `coverage_results: ...` inside any `description`; put result-shape guidance in `prompt_markdown` or `posture_notes`, where block scalars make punctuation safe.
- `# Done When` becomes the required coverage contract for this deterministic probe. It must contain exactly three top-level bullet items, no more and no fewer: candidate validation plus managed run binding/runtime visibility; Builder proof file plus `proof_files`; GateKeeper exact upstream evidence refs plus `covered` coverage status before `finish_run`.
- Do not put terminal run status, task verdict, fake-done risks, guardrails, or evidence preferences in `# Done When`; those belong in `# Success Surface`, `# Guardrails`, `# Fake Done`, or `# Evidence Preferences`. Extra Done When bullets create uncovered required targets and fail this release gate.
- `# Success Surface` must contain exactly one top-level bullet item requiring terminal run status `succeeded` with task verdict `passed`; do not author a residual-risk pass for this release gate.
- `# Fake Done` must contain exactly two top-level bullet items: run visibility alone is not enough without Builder proof; GateKeeper cannot pass without citing exact upstream Builder evidence ids.
- `# Evidence Preferences` must contain exactly two top-level bullet items: task verdict buckets are Proven, Weak, Unproven, Blocking, and Residual risk; evidence references must use exact ids from `known_evidence_ids`.
- `collaboration_summary` must explicitly describe GateKeeper / final judgment posture, not just setup or execution mechanics.
- Residual Risk must say the limited non-interactive native-dispatch risk is accepted only for this probe when wrapper JSON, dispatch metadata, role outputs, exact evidence refs, and terminal verdict buckets are present; otherwise fail closed.
- Do not describe stack, framework, language, product architecture, test-suite, or build-capability details. This fixture only gives you the installed Loopora entries, a README, and the executor script path, so omit environment/architecture claims entirely.
- The user-facing bundle prose should say this is a release-profile probe for conversation-guided bundle generation, managed run binding, runtime activity, and Agent-native submission. Do not reduce it to a generic smoke test.

Required bundle structure checklist:

- Top-level keys include `version`, `metadata`, `collaboration_summary`, `loop`, `spec`, `role_definitions`, and `workflow`.
- Use quoted strings or YAML block scalars for all prose or punctuation-rich scalar values, including `metadata.description` and every `role_definitions[].description`. Prefer block scalars for `collaboration_summary`, `spec.markdown`, `posture_notes`, and `command_args_text` so colons and punctuation cannot break YAML parsing.
- For each role `prompt_markdown`, use a literal block scalar `|`, not folded `>-`; folded scalars collapse YAML front matter lines into one line and fail validation.
- `metadata` contains only identity fields such as `name` and `description`; do not place `collaboration_summary`, `completion_mode`, executor settings, roles, or steps inside `metadata`.
- `loop` is the run configuration object and must include `name`, `workdir`, `completion_mode`, `executor_kind`, `executor_mode`, `command_cli`, `command_args_text`, `model`, and `reasoning_effort`.
- Every custom `command_args_text` block must preserve the literal placeholders `{{output_path}}` and `{{prompt}}`; do not replace them with concrete paths while authoring the bundle.
- The only placeholders allowed in custom command args are `{{output_path}}` and `{{prompt}}`; never use `{{role}}`, `{{step}}`, or any other placeholder.
- Write the loop and Builder `command_args_text` as one block containing exactly this shape: `{executor_script} builder {{output_path}} {{prompt}}`.
- Write the GateKeeper `command_args_text` as one block containing exactly this shape: `{executor_script} gatekeeper {{output_path}} {{prompt}}`.
- `spec` is an object with `markdown` containing the Task, Done When, Success Surface, Guardrails, Fake Done, Evidence Preferences, and Residual Risk sections.
- `spec.markdown` must use these exact top-level Markdown headings: `# Task`, `# Done When`, `# Success Surface`, `# Guardrails`, `# Fake Done`, `# Evidence Preferences`, and `# Residual Risk`.
- `role_definitions` is a list containing one Builder role definition with key `release-proof-builder` and one GateKeeper role definition with key `release-gatekeeper`; each role has `key`, `name`, `description`, `archetype`, `prompt_ref`, `prompt_markdown`, `posture_notes`, repeats the custom command executor settings, and keeps `model` / `reasoning_effort` blank.
- Each role `prompt_markdown` must use `prompt_markdown: |` and start with these exact YAML front matter lines, with no blank line before `version: 1`: `---`, then `version: 1`, then the matching `archetype: builder` or `archetype: gatekeeper`, then `---`, followed by role guidance.
- `workflow` is the workflow object, not the `loop` object. It should define `roles` as objects such as `{{id, role_definition_key}}`; use role id `builder` with `role_definition_key: release-proof-builder` and role id `gatekeeper` with `role_definition_key: release-gatekeeper`.
- `workflow.collaboration_intent` is required and must explain evidence flow, GateKeeper closure, and weak-evidence or fake-done exposure: Builder creates durable proof first, then GateKeeper queries exact Builder evidence before `finish_run`.
- `workflow.steps` must be a list. Each step object must use an explicit `id`; do not use `key`, generated names, or omitted ids. The exact step id `builder_step` uses `role_id: builder` and runs first. The exact step id `gatekeeper_step` uses `role_id: gatekeeper`, has `inputs.handoffs_from: [builder_step]`, has `inputs.evidence_query.archetypes: [builder]`, has `inputs.evidence_query.limit` set to a small integer, and sets `on_pass: finish_run`. Do not use unsupported evidence query keys such as `from_steps`.

Required order:

0. After reading the installed entry files, create the candidate bundle on disk and verify that `{bundle_file}` exists before moving on.
1. Invoke `/loopora-plan` or the installed `loopora-plan` project entry semantics.
2. Only after the candidate is READY, invoke `/loopora-run` or the installed `loopora-run` project entry semantics.
3. Continue the installed Agent-native loop path until Loopora returns `complete: true`. For each returned Agent Step View, use the host's official native role/subagent or task mechanism named by `role_dispatch.target_agent`; in short, use the host's native role/subagent mechanism named by `role_dispatch.target_agent` whenever that is the host's official spelling. Mirror `native_todo` through the host's todo/progress-list capability when available, write one wrapper JSON result with `loopora_host_dispatch` and `result`, follow any `evidence_rules`, `evidence_ref_contract`, and `role_dispatch`, and submit it as instructed by the installed entry.
4. While the run is active, observe the local Loopora runtime activity endpoint or the returned run URL enough to confirm the run is visible before terminal completion.
5. Return a short summary with the candidate URL, run URL, runtime activity observation, and terminal run status.

Keep each role dispatch small and deterministic for this release-profile probe. Builder must create `loopora-agent-release-proof.json` in the workdir and return `proof_files: ["loopora-agent-release-proof.json"]`; it may still return empty `changed_files`, `proof_artifacts`, and `artifact_paths`. GateKeeper should cite only the exact Builder evidence id returned in `known_evidence_ids`. For every satisfied `coverage_results` target, set `status` to `covered`; do not use verdict bucket words such as `proven` or `unproven` as coverage status values. GateKeeper must return `residual_risks: []` when passing; place the fact that this is a bounded release probe in `decision_summary` or `evidence_claims`, not in `residual_risks`. For Codex, if you use `spawn_agent`, set `agent_type` to the exact target agent, omit `fork_context`, and wait with a bounded timeout shorter than this harness timeout. For Claude Code, use the official Agent tool when available and accept Task as the compatibility spelling; for OpenCode, use the configured task/subagent mechanism.

For every result file, use the installed entry's wrapper format: top-level `loopora_host_dispatch` plus top-level `result`. The `result` object must use the exact top-level keys required by the Agent Step View's `output_schema`. For GateKeeper, write `passed`, `decision_summary`, `metrics`, `metric_scores`, `evidence_refs`, `evidence_claims`, and the other schema fields inside `result`; do not use a `verdict` or `task_verdict` envelope. In `loopora_host_dispatch`, set both `target_agent` and `actual_agent` to the exact `role_dispatch.target_agent`, set `dispatch_mode` to `host_subagent`, `host_task`, or `host_agent`, and set `inline` to false. If the host exposes an official subagent/task trace id or tool-call id, copy it into `native_trace` or `native_trace_ref`; if not, leave those optional trace fields empty. Every `evidence_refs` list, including inside `coverage_results`, must contain only exact strings copied from `known_evidence_ids`. If `known_evidence_ids` contains only `ev_000_00_builder_step`, use only `ev_000_00_builder_step`; do not invent suffixes such as `_binding`, `_output`, `_preference`, or `_fake_done_risk`. Artifact labels and file names belong in evidence_claims or notes.

Do not edit user-owned config files.
Do not invent a direct Loopora CLI command from this prompt; follow the installed project entry instructions when a shell command is needed.
Do not invoke codex, claude, or opencode from inside this Agent session; this release-profile probe must prove the host Agent itself performs the role work.

Final response format:

- Your final stdout must include the literal line `agent_work_panel:`. The real probe treats the run as experience-incomplete if that line is missing.
- Print the block before any summary:

```text
agent_work_panel:
state: <copy latest state, or task_proven after the terminal verdict passed>
next_action: <copy latest next_action, or no new evidence pass unless scope changes>
evidence_focus: <copy latest evidence_focus, or task verdict passed>
todo_items: <copy latest todo_items, or []>
```

- Then print candidate URL/path, run URL, runtime activity observation, terminal run status, and task verdict.
- Do not omit the block even when the task verdict passed.
"""


def _canonical_entry_action(action: object) -> str:
    raw = str(action or "")
    if raw == "gen":
        return "plan"
    if raw == "loop":
        return "run"
    return raw


def _assert_managed_plan_before_run(adapter: str, entry_invocations: list[dict]) -> None:
    expected_source = _entry_source(adapter)
    normalized = [
        (_canonical_entry_action(item.get("action")), item.get("entry_source"))
        for item in entry_invocations
        if isinstance(item, dict)
    ]
    managed_plan_indexes = [index for index, item in enumerate(normalized) if item == ("plan", expected_source)]
    assert managed_plan_indexes, normalized
    assert any(item == ("run", expected_source) for item in normalized[managed_plan_indexes[0] + 1 :]), normalized
    assert normalized[-1] == ("run", expected_source)


@pytest.mark.parametrize("adapter", AGENT_TARGETS)
def test_real_agent_host_can_guide_bundle_then_monitor_loop(adapter: str, tmp_path: Path, monkeypatch) -> None:  # noqa: PLR0915 - release-profile probe keeps the full host journey in one scenario.
    template = _require_real_agent_template(adapter)
    timeout = float(os.environ.get(TIMEOUT_ENV, "1200"))
    loopora_home = tmp_path / "loopora-home"
    monkeypatch.setenv("LOOPORA_HOME", str(loopora_home))
    sentinel_dir, sentinel_log = _write_nested_agent_sentinels(tmp_path)
    bin_dir = _write_loopora_wrapper(tmp_path, sentinel_dir=sentinel_dir)
    env = os.environ.copy()
    env["LOOPORA_HOME"] = str(loopora_home)
    env["PYTHONPATH"] = f"{SRC_ROOT}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    agent_web_port = _free_port()
    agent_web_pid_file = tmp_path / "agent-web.pid"
    agent_web_url = f"http://127.0.0.1:{agent_web_port}"
    env["LOOPORA_AGENT_WEB_PORT"] = str(agent_web_port)
    env["LOOPORA_AGENT_WEB_PID_FILE"] = str(agent_web_pid_file)

    workdir = tmp_path / f"real-{adapter}-agent-workdir"
    workdir.mkdir()
    (workdir / "README.md").write_text("# Real Agent adapter release fixture\n", encoding="utf-8")
    executor_script = _write_custom_executor(workdir)
    bundle_file = workdir / ".loopora" / "agent_inbox" / adapter / "conversation-candidate.yml"
    prompt_file = workdir / "loopora-agent-release-prompt.md"
    command = ""
    activity_snapshots: list[dict] = []
    monitor_result: HostCommandMonitorResult | None = None
    prompt_file.write_text(_release_probe_prompt(adapter, bundle_file, executor_script), encoding="utf-8")

    try:
        install = subprocess.run(
            ["loopora", "init", adapter, "--workdir", str(workdir)],
            cwd=workdir,
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        assert install.returncode == 0, install.stderr or install.stdout
        assert not bundle_file.exists()

        command = template.format(
            workdir=shlex.quote(str(workdir)),
            prompt_file=shlex.quote(str(prompt_file)),
            bundle_file=shlex.quote(str(bundle_file)),
        )
        _assert_real_agent_command_model_policy(adapter, command)
        _assert_real_agent_command_monitorability(adapter, command)
        monitor_result = _wait_for_host_command_with_runtime_monitoring(
            HostCommandMonitorRequest(
                command=command,
                adapter=adapter,
                workdir=workdir,
                env=env,
                timeout=timeout,
                agent_web_url=agent_web_url,
                sentinel_log=sentinel_log,
            )
        )
        completed = monitor_result.completed
        binding = monitor_result.binding
        activity_snapshots = monitor_result.activity_snapshots
        assert completed.returncode == 0, completed.stderr or completed.stdout
        _assert_experience_visible_work_panel(monitor_result.phase_report, monitor_result.phase_report_path)
        _assert_no_release_prompt_polluted_validation(monitor_result.phase_report, monitor_result.phase_report_path)
        if adapter == "claude":
            _assert_release_probe_candidate_validated_without_repair(monitor_result.phase_report, monitor_result.phase_report_path)
        if adapter == "claude":
            _assert_claude_role_dispatch_prompt_contract(monitor_result.phase_report, monitor_result.phase_report_path)
        assert bundle_file.exists()
        preview = _loopora_service(loopora_home).preview_bundle_text(bundle_file.read_text(encoding="utf-8"))
        assert preview["ok"] is True, preview.get("error")
        assert binding["adapter"] == adapter
        assert binding["linked_run_id"]
        assert str(binding["run_path"]).startswith("/runs/")
        entry_invocations = binding.get("entry_invocations")
        assert isinstance(entry_invocations, list)
        _assert_managed_plan_before_run(adapter, entry_invocations)
        _assert_runtime_activity_observed_run(activity_snapshots, str(binding["linked_run_id"]))
        _assert_alignment_session_came_from_conversation(workdir, str(binding["linked_run_id"]))
        _assert_run_observation_chain(workdir, str(binding["linked_run_id"]), adapter)
        final_run = _wait_for_terminal_run(loopora_home, str(binding["linked_run_id"]), timeout=30)
        assert final_run["status"] == "succeeded"
        assert not sentinel_log.exists(), sentinel_log.read_text(encoding="utf-8") if sentinel_log.exists() else ""
    except AssertionError as exc:
        if "Real probe phase report:" in str(exc):
            raise
        if monitor_result is not None:
            raise AssertionError(
                _format_real_probe_diagnostic_failure(
                    exc,
                    report=monitor_result.phase_report,
                    report_path=monitor_result.phase_report_path,
                )
            ) from None
        report, report_path = _write_real_probe_phase_report(
            adapter=adapter,
            workdir=workdir,
            activity_snapshots=activity_snapshots,
            sentinel_log=sentinel_log,
            host_signals=PhaseReportHostSignals(command=command),
        )
        raise AssertionError(_format_real_probe_diagnostic_failure(exc, report=report, report_path=report_path)) from None
    finally:
        _terminate_pid_file(agent_web_pid_file)

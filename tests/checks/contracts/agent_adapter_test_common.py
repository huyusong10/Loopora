from __future__ import annotations

import hashlib
import shlex
import time
from pathlib import Path


from loopora.bundles import bundle_to_yaml, load_bundle_text
from agent_adapter_expected import (
    EXPECTED_NATIVE_CONTEXT_LOADING,
)


def _assert_expected_mapping_values(actual: dict, expected: dict, *, keys: tuple[str, ...] | None = None) -> None:
    for key in keys or tuple(expected):
        assert actual[key] == expected[key]

def _error_text(result) -> str:
    try:
        return result.stderr
    except ValueError:
        return result.output

def _labeled_value(output: str, label: str) -> str:
    prefix = f"{label}: "
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped.removeprefix(prefix)
    raise AssertionError(f"missing {label}: line in output")

def _assert_loopora_agent_command(
    command: str,
    action: str,
    *,
    adapter: str = "codex",
    entry_source: str = "codex_project_skill",
    json_mode: bool = True,
) -> None:
    assert f"loopora agent {adapter} {action}" in command
    assert f"LOOPORA_AGENT_ENTRY_SOURCE={entry_source}" in command
    assert f"--entry-source {entry_source}" in command
    if json_mode:
        assert "--json" in command

def _assert_labeled_loopora_agent_command(output: str, label: str, action: str, **kwargs) -> str:
    command = _labeled_value(output, label)
    _assert_loopora_agent_command(command, action, **kwargs)
    return command

def _assert_loopora_cli_command(command: str, command_body: str, *, loopora_home: Path | str | None = None) -> None:
    assert command_body in command
    if loopora_home is not None:
        assert command.startswith(f"LOOPORA_HOME={shlex.quote(str(loopora_home))} ")

def _assert_loopora_serve_command(
    command: str,
    *,
    workdir: Path | str | None = None,
    host: str = "127.0.0.1",
    port: int = 8742,
    loopora_home: Path | str | None = None,
) -> None:
    if loopora_home is not None:
        assert command.startswith(f"LOOPORA_HOME={shlex.quote(str(loopora_home))} ")
    tokens = shlex.split(command)
    while tokens and "=" in tokens[0] and not tokens[0].startswith("--"):
        tokens = tokens[1:]
    if tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    elif len(tokens) >= 5 and tokens[:2] == ["uv", "--directory"] and tokens[3] == "run":
        tokens = tokens[4:]
    assert tokens[:2] == ["loopora", "serve"]
    assert tokens[tokens.index("--host") + 1] == host
    assert tokens[tokens.index("--port") + 1] == str(port)
    if workdir is None:
        return
    assert Path(tokens[tokens.index("--workdir") + 1]).resolve() == Path(workdir).resolve()

def _assert_recovery_choice_has_copyable_commands(choice: dict) -> None:
    option_id = str(choice.get("option_id") or "")
    assert option_id.startswith("agent_run:")
    assert choice.get("runnable") is True
    assert str(choice.get("next_command") or "").startswith("/loopora-run option:agent_run:")
    assert str(choice.get("next_slash_command") or "").startswith("/loopora-run option:agent_run:")
    assert "--source-option-id" in str(choice.get("next_cli_command") or "")
    assert option_id in str(choice.get("next_cli_command") or "")

def _assert_not_ready_recovery_choice_routes_to_plan(choice: dict) -> None:
    _assert_non_runnable_recovery_choice_routes_to_plan(choice, expected_status="not_ready")

def _assert_non_runnable_recovery_choice_routes_to_plan(choice: dict, *, expected_status: str) -> None:
    assert choice.get("choice_status") == expected_status
    assert choice.get("runnable") is False
    assert choice.get("next_plan_command") == "/loopora-plan"
    assert choice.get("next_command") == ""
    assert choice.get("next_slash_command") == ""
    assert choice.get("next_cli_command") == ""
    assert choice.get("agent_cli_command") == ""

def _assert_recovery_choice_has_status_hint(choice: dict, *, expected_status: str) -> None:
    assert choice.get("choice_status") == expected_status
    assert choice.get("choice_hint_en")
    assert choice.get("choice_hint_zh")
    assert isinstance(choice.get("runnable"), bool)

def _candidate_digest(bundle_text: str) -> tuple[str, int]:
    normalized = bundle_text.rstrip() + "\n" if bundle_text.strip() else ""
    data = normalized.encode("utf-8")
    return (hashlib.sha256(data).hexdigest(), len(data)) if data else ("", 0)

def _ready_candidate_digest(bundle_text: str) -> tuple[str, int]:
    return _candidate_digest(bundle_to_yaml(load_bundle_text(bundle_text)))

def _wait_for_alignment_status(service, session_id: str, *statuses: str, timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    expected = set(statuses)
    while True:
        session = service.get_alignment_session(session_id)
        if session["status"] in expected:
            return session
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(0.05, remaining))
    raise AssertionError(f"alignment session stayed in {session['status']}, expected {sorted(expected)}")

def _assert_cli_handoff_contract_paths(
    stdout: str,
    *,
    step_contract_fragment: str,
    template_fragment: str,
    outbox_fragment: str,
) -> None:
    assert "next_step_contract_path:" in stdout
    assert step_contract_fragment in stdout
    assert "result_template_path:" in stdout
    assert template_fragment in stdout
    assert "result_outbox_dir:" in stdout
    assert outbox_fragment in stdout

def _assert_cli_list(output: str, key: str, *items: str) -> None:
    assert f"{key}:\n" in output
    assert f"{key}: [" not in output
    for item in items:
        assert f"- {item}" in output

def _assert_output_contains(output: str, *snippets: str) -> None:
    missing = [snippet for snippet in snippets if snippet not in output]

    assert not missing, f"missing output snippets: {missing[:5]}"

def _assert_native_context_loading(surface: dict) -> None:
    context_loading = surface["context_loading"]
    assert context_loading["summary_first"] == ["summary"]
    _assert_expected_mapping_values(
        context_loading,
        EXPECTED_NATIVE_CONTEXT_LOADING,
        keys=(
            "entry_prompt",
            "reference_loading",
            "host_memory",
            "memory_store",
            "template_context",
            "workflow_kits",
            "role_catalogs",
            "compaction_context",
            "host_context",
            "catalog_context",
        ),
    )

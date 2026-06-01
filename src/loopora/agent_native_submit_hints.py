from __future__ import annotations

from pathlib import Path
import shlex
from typing import Any

from loopora.agent_adapters import prefix_loopora_command
from loopora.structured_numbers import structured_non_negative_int


def agent_native_submit_command(
    *,
    adapter: str,
    run_id: str,
    step_id: str,
    entry_source: str = "",
    result_file: str = "RESULT_JSON_PATH",
) -> str:
    bits = [
        "loopora",
        "agent",
        adapter,
        "submit",
        "--workdir",
        _agent_native_command_workdir_arg(result_file),
        "--run-id",
        shlex.quote(run_id),
        "--step-id",
        shlex.quote(step_id),
        "--result-file",
        shlex.quote(str(result_file or "RESULT_JSON_PATH")),
        "--json",
    ]
    normalized_entry_source = str(entry_source or "").strip()
    if normalized_entry_source:
        bits.extend(["--entry-source", shlex.quote(normalized_entry_source)])
    command = " ".join(bits)
    return prefix_loopora_command(command, entry_source=normalized_entry_source)


def agent_native_result_artifact_stem(*, run_id: str, iter_id: int, step_order: int, step_id: str) -> str:
    return f"{run_id}__iter{iter_id:03d}__step{step_order:02d}__{step_id}"


def agent_native_submit_hint_with_scoped_result_paths(
    submit_hint: dict[str, Any],
    step_view: dict[str, Any],
    *,
    run_id: str,
    step_id: str,
) -> dict[str, Any]:
    if not _agent_native_step_view_has_step_position(step_view):
        return submit_hint
    scoped_hint = dict(submit_hint)
    result_stem = agent_native_result_artifact_stem(
        run_id=run_id,
        iter_id=structured_non_negative_int(step_view.get("iter")),
        step_order=structured_non_negative_int(step_view.get("step_order")),
        step_id=step_id,
    )
    _agent_native_set_scoped_result_paths(
        scoped_hint,
        dir_key="result_outbox_absolute_dir",
        template_key="result_template_absolute_path",
        result_key="result_file_absolute_path",
        result_stem=result_stem,
    )
    _agent_native_set_scoped_result_paths(
        scoped_hint,
        dir_key="result_outbox_dir",
        template_key="result_template_path",
        result_key="result_file_path",
        result_stem=result_stem,
    )
    return scoped_hint


def _agent_native_command_workdir_arg(result_file: str) -> str:
    text = str(result_file or "").strip()
    if not text or text == "RESULT_JSON_PATH":
        return '"$PWD"'
    try:
        path = Path(text).expanduser()
        if not path.is_absolute():
            return '"$PWD"'
        parts = path.parts
        if ".loopora" in parts:
            loopora_index = parts.index(".loopora")
            if loopora_index > 0:
                return shlex.quote(str(Path(*parts[:loopora_index]).resolve()))
    except OSError:
        return '"$PWD"'
    return '"$PWD"'


def _agent_native_step_view_has_step_position(step_view: dict[str, Any]) -> bool:
    return (
        isinstance(step_view.get("iter"), int)
        and not isinstance(step_view.get("iter"), bool)
        and isinstance(step_view.get("step_order"), int)
        and not isinstance(step_view.get("step_order"), bool)
    )


def _agent_native_path_parent(path_value: object) -> str:
    text = str(path_value or "").strip()
    if not text:
        return ""
    return str(Path(text).parent)


def _agent_native_set_scoped_result_paths(
    submit_hint: dict[str, Any],
    *,
    dir_key: str,
    template_key: str,
    result_key: str,
    result_stem: str,
) -> None:
    outbox_dir = str(submit_hint.get(dir_key) or "").strip()
    if not outbox_dir:
        outbox_dir = _agent_native_path_parent(submit_hint.get(template_key) or submit_hint.get(result_key))
    if not outbox_dir:
        return
    outbox = Path(outbox_dir)
    submit_hint[dir_key] = str(outbox)
    submit_hint[result_key] = str(outbox / f"{result_stem}.result.json")
    submit_hint[template_key] = str(outbox / f"{result_stem}.result.template.json")

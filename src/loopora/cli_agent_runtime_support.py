from __future__ import annotations

import json
import os
import shlex
from pathlib import Path

import typer

from loopora.agent_adapters import prefix_loopora_command
from loopora.agent_web import ensure_local_web_service, web_url_for_path
from loopora.cli_shared import call_spawn_background_worker
from loopora.service import LooporaError


def attach_web_url(result: dict, *, path_key: str, url_key: str, no_web: bool) -> None:
    path = str(result.get(path_key) or "")
    if not path:
        return
    if no_web:
        _attach_relative_web_url(result, path=path, url_key=url_key, status="relative_path_web_not_started")
        return
    web = ensure_local_web_service()
    result["web"] = web
    if _web_url_available(web):
        result[url_key] = web_url_for_path(path, web=web)
        return
    _attach_relative_web_url(
        result,
        path=path,
        url_key=url_key,
        status=_relative_web_status(web),
        web=web,
    )


def _attach_relative_web_url(
    target: dict,
    *,
    path: str,
    url_key: str,
    status: str,
    web: dict[str, object] | None = None,
) -> None:
    target[url_key] = path
    target[f"{url_key}_status"] = status
    target[f"{url_key}_web_start_command"] = _web_start_command(web)


def _web_url_available(web: dict[str, object]) -> bool:
    return web.get("reused") is True and not str(web.get("warning") or "").strip()


def _relative_web_status(web: dict[str, object]) -> str:
    return "relative_path_web_not_running" if web.get("start_available") is True else "relative_path_web_unavailable"


def _web_start_command(web: dict[str, object] | None = None) -> str:
    port = 8742
    if isinstance(web, dict):
        try:
            port = int(web.get("port") or port)
        except (TypeError, ValueError):
            port = 8742
    return prefix_loopora_command(f"loopora serve --host 127.0.0.1 --port {port}")


def attach_recoverable_context_preview_urls(result: dict, *, no_web: bool) -> None:
    resolution = result.get("context_resolution") if isinstance(result.get("context_resolution"), dict) else {}
    choices = [choice for choice in resolution.get("choices") or [] if isinstance(choice, dict)]
    preview_choices = [choice for choice in choices if str(choice.get("preview_path") or "").strip()]
    if not preview_choices:
        return
    web = None if no_web else ensure_local_web_service()
    if web:
        result["web"] = web
    for choice in preview_choices:
        path = str(choice.get("preview_path") or "").strip()
        if no_web:
            _attach_relative_web_url(
                choice,
                path=path,
                url_key="preview_url",
                status="relative_path_web_not_started",
            )
        elif web and _web_url_available(web):
            choice["preview_url"] = web_url_for_path(path, web=web)
        else:
            _attach_relative_web_url(
                choice,
                path=path,
                url_key="preview_url",
                status=_relative_web_status(web or {}),
                web=web,
            )


def resolved_entry_source(entry_source: str) -> str:
    return str(entry_source or "").strip() or os.environ.get("LOOPORA_AGENT_ENTRY_SOURCE", "").strip()


def agent_plan_cli_command(  # noqa: PLR0913 - preserves the existing command-helper call contract.
    *,
    adapter: str,
    workdir: Path | str,
    message: str,
    context_id: str = "",
    entry_source: str = "",
    bundle_file: str = "",
) -> str:
    command_bits = [
        "loopora",
        "agent",
        str(adapter).strip(),
        "plan",
        "--workdir",
        shlex.quote(str(workdir)),
    ]
    normalized_context_id = str(context_id or "").strip()
    if normalized_context_id:
        command_bits.extend(["--context-id", shlex.quote(normalized_context_id)])
    command_bits.extend(["--message", shlex.quote(message)])
    normalized_bundle_file = str(bundle_file or "").strip()
    if normalized_bundle_file:
        command_bits.extend(["--bundle-file", shlex.quote(normalized_bundle_file)])
    normalized_entry_source = str(entry_source or "").strip()
    if normalized_entry_source:
        command_bits.extend(["--entry-source", shlex.quote(normalized_entry_source)])
    command = " ".join(command_bits)
    return prefix_loopora_command(command, entry_source=normalized_entry_source)


def agent_next_command_hint(*, adapter: str, context_id: str, run_id: str, entry_source: str = "", workdir: Path | None = None) -> str:
    bits = [f"loopora agent {adapter} next", "--workdir", agent_command_workdir_arg(workdir)]
    if run_id:
        bits.append(f"--run-id {run_id}")
    elif context_id:
        bits.append(f"--context-id {context_id}")
    bits.extend(["--json", "--compact-json"])
    normalized_entry_source = str(entry_source or "").strip()
    if normalized_entry_source:
        bits.extend(["--entry-source", shlex.quote(normalized_entry_source)])
    command = " ".join(bits)
    return prefix_loopora_command(command, entry_source=normalized_entry_source)


def agent_command_workdir_arg(workdir: Path | None) -> str:
    if workdir is None or str(workdir).strip() in ("", "."):
        return '"$PWD"'
    try:
        return shlex.quote(str(Path(workdir).expanduser().resolve()))
    except OSError:
        return shlex.quote(str(workdir))


def spawn_agent_loop_worker_if_needed(service, result: dict) -> None:
    if result.get("execution_plane") == "agent_native":
        return
    if not result.get("started_new_run"):
        return
    run = result.get("run")
    if not isinstance(run, dict):
        return
    result["run"] = call_spawn_background_worker(service, run)


def print_web_status(result: dict) -> None:
    web = result.get("web")
    if not isinstance(web, dict):
        return
    base_url = str(web.get("base_url") or "").strip()
    if not base_url:
        return
    if web.get("started"):
        typer.echo(f"web: started {base_url}")
    elif web.get("reused"):
        typer.echo(f"web: reused {base_url}")
    else:
        typer.echo(f"web: {base_url}")
    warning = str(web.get("warning") or "").strip()
    if warning:
        typer.echo(f"web_warning: {warning}")


def read_result_json(path: Path) -> tuple[dict, dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LooporaError(f"result file is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise LooporaError("result file must contain one JSON object")
    if "loopora_host_dispatch" in payload or "result" in payload:
        host_dispatch = payload.get("loopora_host_dispatch")
        result = payload.get("result")
        if not isinstance(host_dispatch, dict):
            raise LooporaError("result wrapper must contain loopora_host_dispatch object")
        if not isinstance(result, dict):
            raise LooporaError("result wrapper must contain result object")
        return result, host_dispatch
    return payload, {}

from __future__ import annotations

import os
import shlex
from pathlib import Path

import typer

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.agent_web import discover_local_web_service, web_url_for_path
from loopora.cli_agent_result_files import read_result_file_object
from loopora.cli_shared import call_spawn_background_worker
from loopora.service import LooporaError


def attach_web_url(
    result: dict,
    *,
    path_key: str,
    url_key: str,
    no_web: bool,
    workdir: Path | str | None = None,
) -> None:
    path = str(result.get(path_key) or "")
    if not path:
        return
    web_start_workdir = _result_workdir(result, workdir)
    if no_web:
        _attach_relative_web_url(
            result,
            path=path,
            url_key=url_key,
            status="relative_path_web_not_started",
            workdir=web_start_workdir,
        )
        return
    web = discover_local_web_service()
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
        workdir=web_start_workdir,
    )


def _attach_relative_web_url(  # noqa: PLR0913 - URL fallback fields stay explicit at each recovery call site.
    target: dict,
    *,
    path: str,
    url_key: str,
    status: str,
    web: dict[str, object] | None = None,
    workdir: Path | str | None = None,
) -> None:
    target[url_key] = path
    target[f"{url_key}_status"] = status
    target[f"{url_key}_web_start_command"] = _web_start_command(web=web, workdir=workdir)


def _web_url_available(web: dict[str, object]) -> bool:
    return web.get("reused") is True and not str(web.get("warning") or "").strip()


def _relative_web_status(web: dict[str, object]) -> str:
    return "relative_path_web_not_running" if web.get("start_available") is True else "relative_path_web_unavailable"


def _web_start_command(web: dict[str, object] | None = None, *, workdir: Path | str | None = None) -> str:
    port = 8742
    if isinstance(web, dict):
        try:
            port = int(web.get("port") or port)
        except (TypeError, ValueError):
            port = 8742
    workdir_arg = f" --workdir {agent_command_workdir_arg(Path(workdir))}" if workdir not in (None, "") else ""
    return copyable_loopora_command(f"loopora serve --open{workdir_arg} --host 127.0.0.1 --port {port}")


def attach_recoverable_context_preview_urls(result: dict, *, no_web: bool, workdir: Path | str | None = None) -> None:
    resolution = result.get("context_resolution") if isinstance(result.get("context_resolution"), dict) else {}
    choices = [choice for choice in resolution.get("choices") or [] if isinstance(choice, dict)]
    preview_choices = [choice for choice in choices if str(choice.get("preview_path") or "").strip()]
    if not preview_choices:
        return
    web_start_workdir = _result_workdir(result, workdir)
    web = None if no_web else discover_local_web_service()
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
                workdir=web_start_workdir,
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
                workdir=web_start_workdir,
            )


def _result_workdir(result: dict, explicit_workdir: Path | str | None) -> Path | str | None:
    if explicit_workdir not in (None, ""):
        return explicit_workdir
    workdir = str(result.get("workdir") or "").strip()
    if workdir:
        return workdir
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    run_workdir = str(run.get("workdir") or "").strip()
    return run_workdir or None


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
        shlex.quote(str(adapter).strip()),
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
    return copyable_loopora_command(command, entry_source=normalized_entry_source)


def agent_next_command_hint(*, adapter: str, context_id: str, run_id: str, entry_source: str = "", workdir: Path | None = None) -> str:
    bits = ["loopora", "agent", shlex.quote(str(adapter)), "next", "--workdir", agent_command_workdir_arg(workdir)]
    if run_id:
        bits.extend(["--run-id", shlex.quote(str(run_id))])
    elif context_id:
        bits.extend(["--context-id", shlex.quote(str(context_id))])
    bits.extend(["--json", "--compact-json"])
    normalized_entry_source = str(entry_source or "").strip()
    if normalized_entry_source:
        bits.extend(["--entry-source", shlex.quote(normalized_entry_source)])
    command = " ".join(bits)
    return copyable_loopora_command(command, entry_source=normalized_entry_source)


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
    if web.get("reused"):
        typer.echo(f"web: reused {base_url}")
    elif web.get("start_available"):
        typer.echo(f"web: not running {base_url}")
    else:
        typer.echo(f"web: unavailable {base_url}")
    warning = str(web.get("warning") or "").strip()
    if warning:
        typer.echo(f"web_warning: {warning}")


def print_web_url(result: dict, *, path_key: str, url_key: str) -> None:
    url = str(result.get(url_key) or result.get(path_key) or "").strip()
    if url:
        typer.echo(f"{url_key}: {url}")
    url_status = str(result.get(f"{url_key}_status") or "").strip()
    if url_status:
        typer.echo(f"{url_key}_status: {url_status}")
    web_start_command = str(result.get(f"{url_key}_web_start_command") or "").strip()
    if web_start_command:
        typer.echo(f"{url_key}_web_start_command: {web_start_command}")


def print_preview_url(result: dict, *, path_key: str = "preview_path", url_key: str = "preview_url") -> None:
    print_web_url(result, path_key=path_key, url_key=url_key)


def read_result_json(path: Path) -> tuple[dict, dict]:
    payload = read_result_file_object(path)
    if "loopora_host_dispatch" in payload or "result" in payload:
        host_dispatch = payload.get("loopora_host_dispatch")
        result = payload.get("result")
        if not isinstance(host_dispatch, dict):
            raise LooporaError("result wrapper must contain loopora_host_dispatch object")
        if not isinstance(result, dict):
            raise LooporaError("result wrapper must contain result object")
        return result, host_dispatch
    return payload, {}

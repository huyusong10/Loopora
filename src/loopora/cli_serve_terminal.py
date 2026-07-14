from __future__ import annotations

import typer

from loopora.cli_recovery_language import localized_recovery_command
from loopora.cli_serve_language import localized_serve_command, serve_text
from loopora.web_origins import (
    http_origin,
    is_wildcard_bind_host,
    loopback_origin_for_wildcard,
    open_origin_for_bind_host,
    remote_origin_hint_for_wildcard,
)
from loopora.web_request_context import _is_loopback_host


def print_serve_startup_summary(  # noqa: PLR0913 - startup summary mirrors the public serve context.
    *,
    host: str,
    port: int,
    auth_token: str,
    startup_workdir: str,
    browser_url: str = "",
    language: str = "en",
) -> None:
    origin = http_origin(host, port)
    if _is_loopback_host(host):
        typer.echo(f"Loopora Web: {origin}")
        typer.echo(serve_text(language, f"home: {origin}", f"首页：{origin}"))
        typer.echo(serve_text(language, f"fit guide: {_serve_url_path(origin, '/fit-guide')}", f"适用性判断：{_serve_url_path(origin, '/fit-guide')}"))
        typer.echo(serve_text(language, f"create: {_serve_url_path(origin, '/loops/new')}", f"创建入口：{_serve_url_path(origin, '/loops/new')}"))
        typer.echo(serve_text(language, f"support: {_serve_url_path(origin, '/support')}", f"支持：{_serve_url_path(origin, '/support')}"))
        if auth_token:
            typer.echo(
                serve_text(
                    language,
                    "auth: enabled (open the token form; automation may use Authorization: Bearer)",
                    "认证：已启用（请打开 token 表单；自动化可使用 Authorization: Bearer）",
                )
            )
        else:
            typer.echo(serve_text(language, "auth: disabled (loopback local default)", "认证：未启用（loopback 本地默认）"))
        typer.echo(serve_text(language, "paths: local file dialogs enabled", "路径：已启用本地文件选择器"))
        if startup_workdir:
            typer.echo(serve_text(language, f"workdir: {startup_workdir}", f"目标项目：{startup_workdir}"))
        _print_browser_open_summary(browser_url, language=language)
        _print_serve_creation_choices_summary(language=language)
        return
    typer.echo("Loopora Web:")
    if is_wildcard_bind_host(host):
        local_origin = loopback_origin_for_wildcard(host, port)
        remote_origin = remote_origin_hint_for_wildcard(port)
        _print_wildcard_origins(local_origin, remote_origin, bind_origin=origin, language=language)
    else:
        typer.echo(serve_text(language, f"- open: {origin}", f"- 打开：{origin}"))
        typer.echo(serve_text(language, f"- fit guide: {_serve_url_path(origin, '/fit-guide')}", f"- 适用性判断：{_serve_url_path(origin, '/fit-guide')}"))
        typer.echo(serve_text(language, f"- create: {_serve_url_path(origin, '/loops/new')}", f"- 创建入口：{_serve_url_path(origin, '/loops/new')}"))
        typer.echo(serve_text(language, f"- support: {_serve_url_path(origin, '/support')}", f"- 支持：{_serve_url_path(origin, '/support')}"))
        typer.echo(serve_text(language, f"- bind: {origin}", f"- 绑定地址：{origin}"))
    if auth_token:
        typer.echo(
            serve_text(
                language,
                "auth: enabled (open the token form; automation may use Authorization: Bearer)",
                "认证：已启用（请打开 token 表单；自动化可使用 Authorization: Bearer）",
            )
        )
    else:
        typer.echo(serve_text(language, "auth: disabled by explicit --allow-unsafe-open", "认证：通过显式 --allow-unsafe-open 禁用"))
    typer.echo(
        serve_text(
            language,
            "paths: network mode uses server-side absolute paths; native file dialogs disabled",
            "路径：网络模式使用服务器端绝对路径；原生文件选择器已禁用",
        )
    )
    if startup_workdir:
        typer.echo(serve_text(language, f"workdir: {startup_workdir}", f"目标项目：{startup_workdir}"))
    _print_browser_open_summary(browser_url, language=language)
    _print_serve_creation_choices_summary(language=language)


def print_serve_existing_web_summary(  # noqa: PLR0913 - reused-service summary mirrors public serve context.
    *,
    host: str,
    port: int,
    auth_token: str,
    startup_workdir: str,
    browser_url: str,
    language: str = "en",
) -> None:
    origin = open_origin_for_bind_host(host, port)
    typer.echo(serve_text(language, f"Loopora Web: reused {origin}", f"Loopora Web：已复用 {origin}"))
    if startup_workdir:
        typer.echo(serve_text(language, f"target project: {startup_workdir}", f"目标项目：{startup_workdir}"))
    if auth_token:
        typer.echo(serve_text(language, "auth: existing service accepted the configured token", "认证：现有服务已接受配置的 token"))
    typer.echo(serve_text(language, f"browser: opening {browser_url}", f"浏览器：正在打开 {browser_url}"))
    typer.echo(
        serve_text(
            language,
            "lifecycle: the existing service remains owned by its original terminal; this command exits after opening",
            "生命周期：现有服务仍由原终端持有；此命令打开页面后退出",
        )
    )


def _print_browser_open_summary(browser_url: str, *, language: str) -> None:
    url = str(browser_url or "").strip()
    if not url:
        return
    typer.echo(serve_text(language, f"browser: opening {url}", f"浏览器：正在打开 {url}"))
    typer.echo(serve_text(language, "lifecycle: keep this command running; press Ctrl-C to stop Web", "生命周期：保持此命令运行；按 Ctrl-C 停止 Web"))


def print_serve_startup_recovery(payload: dict[str, object], *, language: str = "en") -> None:
    typer.echo(serve_text(language, "Loopora Web start is blocked", "Loopora Web 启动受阻"), err=True)
    reason = str(payload.get("start_blocked_reason") or "").strip()
    if reason:
        reason_text = _serve_blocked_reason_text(reason, language=language)
        typer.echo(serve_text(language, f"reason: {reason_text}", f"原因：{reason_text}"), err=True)
    origin = str(payload.get("origin") or "").strip()
    if origin:
        typer.echo(serve_text(language, f"origin: {origin}", f"访问地址：{origin}"), err=True)
    workdir = str(payload.get("workdir") or "").strip()
    if workdir:
        typer.echo(serve_text(language, f"target project: {workdir}", f"目标项目：{workdir}"), err=True)
    error = str(payload.get("error") or "").strip()
    if error:
        summary = _serve_recovery_summary_text(reason, error=error, language=language)
        typer.echo(serve_text(language, f"summary: {summary}", f"说明：{summary}"), err=True)
    typer.echo(serve_text(language, "next:", "下一步："), err=True)
    for item in payload.get("next_actions") or []:
        if isinstance(item, dict):
            _print_serve_startup_recovery_action(item, language=language)


def print_serve_workdir_recovery(payload: dict[str, object], *, language: str = "en") -> None:
    workdir_state = payload.get("workdir_state") if isinstance(payload.get("workdir_state"), dict) else {}
    typer.echo(serve_text(language, "Loopora Web start is blocked", "Loopora Web 启动受阻"))
    typer.echo(serve_text(language, f"target project: {payload.get('workdir')}", f"目标项目：{payload.get('workdir')}"))
    state = str(workdir_state.get("status") or "unknown")
    state_text = _serve_workdir_state_text(state, language=language)
    typer.echo(serve_text(language, f"project directory state: {state_text}", f"项目目录状态：{state_text}"))
    summary = str(payload.get("summary") or "").strip()
    if summary:
        summary = _serve_workdir_summary_text(state, summary=summary, language=language)
        typer.echo(serve_text(language, f"summary: {summary}", f"说明：{summary}"))
    typer.echo(serve_text(language, "next:", "下一步："))
    for item in payload.get("next_actions") or []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "")
        command = str(item.get("command") or "").strip()
        labels = {
            "create_workdir": "Create the target project directory",
            "choose_workdir": "Choose an existing project directory",
            "confirm_readiness": "Confirm readiness after the target is usable",
            "retry_web_start": "Retry Web start",
        }
        zh_labels = {
            "create_workdir": "创建目标项目目录",
            "choose_workdir": "选择现有项目目录",
            "confirm_readiness": "目标可用后确认就绪",
            "retry_web_start": "重试 Web 启动",
        }
        label = (zh_labels if language == "zh" else labels).get(kind, kind)
        command = localized_recovery_command(command, language=language)
        command = localized_serve_command(command, language=language)
        separator = "：" if language == "zh" else ": "
        typer.echo(f"- {label}{separator}{command}" if command else f"- {label}")
    network_note = str(payload.get("network_auth_note") or "").strip()
    if network_note:
        note = "网络模式仍需要 auth token 或显式 unsafe opt-in。" if language == "zh" else network_note
        typer.echo(serve_text(language, f"network auth: {note}", f"网络认证：{note}"))


def _print_serve_startup_recovery_action(item: dict[str, object], *, language: str) -> None:
    kind = str(item.get("kind") or "").strip()
    command = str(item.get("command") or "").strip()
    note = str(item.get("note") or "").strip()
    blocked_until = [str(value) for value in list(item.get("blocked_until") or [])]
    labels = {
        "configure_auth_token": "Configure an auth token",
        "use_loopback_web": "Use loopback Web",
        "allow_unsafe_open": "Unsafe opt-in",
        "create_recovery_archive": "Create private recovery archive",
        "preview_app_database_reset": "Preview App database reset",
        "use_matching_loopora_version_or_reset": "Use matching Loopora version or preview reset",
        "inspect_or_reset_app_state": "Inspect or reset App state",
        "retry_web_start": "Retry Web start",
        "retry_web_start_on_alternate_port": "Retry Web start on an alternate port",
        "use_temporary_app_home": "temporary Web preview",
        "stop_existing_service": "Stop the existing service",
        "choose_web_port": "Choose another Web port",
        "resolve_web_bind": "Choose a usable bind target",
    }
    zh_labels = {
        "configure_auth_token": "配置 auth token",
        "use_loopback_web": "使用 loopback Web",
        "allow_unsafe_open": "显式 unsafe opt-in",
        "create_recovery_archive": "创建私有恢复归档",
        "preview_app_database_reset": "预览 App 数据库重置",
        "use_matching_loopora_version_or_reset": "使用匹配的 Loopora 版本，或预览重置",
        "inspect_or_reset_app_state": "检查或重置 App 状态",
        "retry_web_start": "重试 Web 启动",
        "retry_web_start_on_alternate_port": "使用其他端口重试 Web 启动",
        "use_temporary_app_home": "临时 Web 预览",
        "stop_existing_service": "停止现有服务",
        "choose_web_port": "选择其他 Web 端口",
        "resolve_web_bind": "选择可用绑定目标",
    }
    label = (zh_labels if language == "zh" else labels).get(kind, kind or serve_text(language, "next action", "下一步动作"))
    if "app_state_ready" in blocked_until:
        label = serve_text(language, f"{label} after App state is ready", f"App 状态就绪后{label}")
    command = localized_recovery_command(command, language=language)
    command = localized_serve_command(command, language=language)
    suffix = ("：" if language == "zh" else ": ") + command if command else ""
    typer.echo(f"- {label}{suffix}", err=True)
    if note:
        note = _serve_action_note_text(kind, note=note, language=language)
        typer.echo(serve_text(language, f"  note: {note}", f"  说明：{note}"), err=True)


def _serve_url_path(origin: str, path: str) -> str:
    return f"{origin.rstrip('/')}/{path.lstrip('/')}"


def _print_serve_creation_choices_summary(*, language: str) -> None:
    lines = (
        ("next: start from Fit Guide, then choose a Web path", "下一步：先从适用性判断开始，再选择 Web 路径"),
        ("- Fit Guide: decide whether Loopora fits before setup or creation", "- 适用性判断：在设置或创建前判断 Loopora 是否适合"),
        ("- Web conversation: browser-first planning when outside an Agent session", "- Web 对话：不在 Agent 会话中时使用浏览器优先的规划路径"),
        ("- Same-Agent setup: handoff back to Codex, Claude Code, or OpenCode", "- 同一 Agent 设置：交接回 Codex、Claude Code 或 OpenCode"),
        ("- Import/manual expert: preview an existing plan file or exact contract before creating or running", "- 导入/手动专家：创建或运行前预览现有方案文件或精确契约"),
        ("- Existing work: inspect evidence, verdict state, residual risk, and next action", "- 现有工作：检查证据、裁决状态、残余风险和下一步动作"),
    )
    for english, chinese in lines:
        typer.echo(serve_text(language, english, chinese))


def _print_wildcard_origins(local_origin: str, remote_origin: str, *, bind_origin: str, language: str) -> None:
    lines = (
        (f"- open on this machine: {local_origin}", f"- 在本机打开：{local_origin}"),
        (f"- fit guide on this machine: {_serve_url_path(local_origin, '/fit-guide')}", f"- 本机适用性判断：{_serve_url_path(local_origin, '/fit-guide')}"),
        (f"- create on this machine: {_serve_url_path(local_origin, '/loops/new')}", f"- 本机创建入口：{_serve_url_path(local_origin, '/loops/new')}"),
        (f"- support on this machine: {_serve_url_path(local_origin, '/support')}", f"- 本机支持：{_serve_url_path(local_origin, '/support')}"),
        (f"- open from another machine: {remote_origin}", f"- 从其他机器打开：{remote_origin}"),
        (f"- fit guide from another machine: {_serve_url_path(remote_origin, '/fit-guide')}", f"- 其他机器适用性判断：{_serve_url_path(remote_origin, '/fit-guide')}"),
        (f"- create from another machine: {_serve_url_path(remote_origin, '/loops/new')}", f"- 其他机器创建入口：{_serve_url_path(remote_origin, '/loops/new')}"),
        (f"- support from another machine: {_serve_url_path(remote_origin, '/support')}", f"- 其他机器支持：{_serve_url_path(remote_origin, '/support')}"),
        (f"- bind: {bind_origin}", f"- 绑定地址：{bind_origin}"),
    )
    for english, chinese in lines:
        typer.echo(serve_text(language, english, chinese))


def _serve_blocked_reason_text(reason: str, *, language: str) -> str:
    if language != "zh":
        return reason
    return {
        "auth_token_required": "需要 auth token",
        "network_auth_required": "网络访问需要认证",
        "app_state_not_ready": "App 状态未就绪",
        "port_in_use": "端口已被占用",
        "bind_unavailable": "绑定目标不可用",
        "workdir_unavailable": "目标项目目录不可用",
    }.get(reason, reason)


def _serve_recovery_summary_text(reason: str, *, error: str, language: str) -> str:
    if language != "zh":
        return error
    return {
        "auth_token_required": "网络 Web 启动需要配置 auth token，或明确选择本地 loopback。",
        "network_auth_required": "网络 Web 启动需要配置 auth token，或明确选择本地 loopback。",
        "app_state_not_ready": "本地 App 状态阻止 Web 启动；请先完成安全恢复。",
        "port_in_use": "请求的端口已被占用；请选择可用端口或停止现有服务。",
        "bind_unavailable": "无法绑定请求的 host/port；请选择可用绑定目标。",
    }.get(reason, error)


def _serve_workdir_state_text(state: str, *, language: str) -> str:
    if language != "zh":
        return state
    return {
        "missing": "不存在",
        "not_directory": "不是目录",
        "uninspectable": "无法检查",
        "ready": "就绪",
    }.get(state, state)


def _serve_workdir_summary_text(state: str, *, summary: str, language: str) -> str:
    if language != "zh":
        return summary
    return {
        "missing": "目标项目目录尚不存在；创建或选择目录后再启动 Web。",
        "not_directory": "目标项目路径不是目录；请选择现有项目目录。",
        "uninspectable": "无法检查目标项目目录；请选择可访问的目录。",
    }.get(state, summary)


def _serve_action_note_text(kind: str, *, note: str, language: str) -> str:
    if language != "zh":
        return note
    return {
        "configure_auth_token": "使用 auth token 重试；永不打印 token 值。",
        "create_recovery_archive": "删除有价值的本地历史前，先创建并检查私有精确路径恢复归档。",
        "preview_app_database_reset": "重试 Web 启动前，先审查本地 App 数据库重置范围。",
        "use_matching_loopora_version_or_reset": "优先使用匹配或更新的 Loopora 版本；若选择 reset，先审查 App 数据库重置范围。",
        "inspect_or_reset_app_state": "先检查本地 App 状态；若选择 reset，先审查 App 数据库重置范围。",
        "use_temporary_app_home": "使用新的空 App home 做预览或排障；不会删除、迁移或修复被阻止的 App 数据库。",
        "allow_unsafe_open": "仅在理解共享网络风险后使用此显式不安全选项。",
    }.get(kind, note)

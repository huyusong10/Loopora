from __future__ import annotations

import typer

from loopora.cli_diagnose_doctor_language import doctor_text
from loopora.cli_serve_language import localized_serve_command


def print_doctor_web(report: dict, *, language: str = "en") -> None:
    web = report.get("web") if isinstance(report.get("web"), dict) else {}
    if web:
        app_state = report.get("app_state") if isinstance(report.get("app_state"), dict) else {}
        web_ready = app_state.get("web_ready") is not False
        token_note = _doctor_web_auth_note(web, language=language)
        if web.get("already_running") is True:
            state_note = doctor_text(
                language,
                "running; " if web_ready else "running; local App state needs attention; ",
                "正在运行；" if web_ready else "正在运行；本地 App 状态需要处理；",
            )
            typer.echo(f"web: {web.get('origin')} ({state_note}{token_note})")
            _print_doctor_web_bind_details(web, language=language)
            _print_doctor_web_auth_details(web, language=language)
            command = _doctor_serve_command(web.get("start_command"), language=language)
            typer.echo(doctor_text(language, f"web open: {command}", f"打开 Web：{command}"))
            return
        if web.get("start_available") is False:
            _print_doctor_web_unavailable(web, web_ready=web_ready, token_note=token_note, language=language)
            return
        if web_ready:
            typer.echo(f"web: {web.get('origin')} ({token_note})")
            _print_doctor_web_bind_details(web, language=language)
            _print_doctor_web_auth_details(web, language=language)
            command = _doctor_serve_command(web.get("start_command"), language=language)
            typer.echo(doctor_text(language, f"web start: {command}", f"启动 Web：{command}"))
            return
        blocked_note = doctor_text(language, "blocked until App state is ready", "等待 App 状态就绪")
        typer.echo(f"web: {web.get('origin')} ({blocked_note}; {token_note})")
        _print_doctor_web_bind_details(web, language=language)
        _print_doctor_web_auth_details(web, language=language)
        command = _doctor_serve_command(web.get("start_command"), language=language)
        typer.echo(doctor_text(language, f"web start after readiness: {command}", f"就绪后启动 Web：{command}"))


def _doctor_web_auth_note(web: dict, *, language: str) -> str:
    if web.get("auth_enabled") is True:
        return doctor_text(language, "auth token configured", "已配置认证 token")
    if web.get("loopback"):
        return doctor_text(language, "loopback local default", "本地 loopback 默认模式")
    return doctor_text(language, "non-loopback requires token or explicit unsafe opt-in", "非 loopback 需要 token 或显式 unsafe opt-in")


def _print_doctor_web_auth_details(web: dict, *, language: str) -> None:
    if web.get("auth_enabled") is not True and (web.get("auth_required") is not True or web.get("auth_token_configured") is not True):
        return
    env_var = str(web.get("auth_token_env_var") or "LOOPORA_AUTH_TOKEN").strip() or "LOOPORA_AUTH_TOKEN"
    typer.echo(
        doctor_text(
            language,
            f"web auth: {env_var} is configured in this shell; keep it set when running web start. Token value is not printed.",
            f"Web 认证：当前 shell 已配置 {env_var}；启动 Web 时保持该变量。不会打印 token 值。",
        )
    )


def _print_doctor_web_unavailable(web: dict, *, web_ready: bool, token_note: str, language: str) -> None:
    requested_origin = str(web.get("requested_origin") or web.get("origin") or "").strip()
    reason_key = str(web.get("start_blocked_reason") or "unavailable")
    reason = _doctor_web_reason_zh(reason_key) if language == "zh" else reason_key.replace("_", " ")
    blocked_note = doctor_text(language, "blocked until App state is ready; ", "等待 App 状态就绪；") if not web_ready else ""
    separator = "；" if language == "zh" else "; "
    typer.echo(f"web: {requested_origin} ({blocked_note}{reason}{separator}{token_note})")
    _print_doctor_web_bind_details(
        {
            "origin": requested_origin,
            "bind_origin": web.get("requested_bind_origin"),
            "remote_origin_hint": web.get("requested_remote_origin_hint"),
        },
        language=language,
    )
    label = "web_start" if web_ready else "web_start_after_readiness"
    if web.get("start_blocked_reason") == "auth_required":
        auth_command = str(web.get("auth_start_command") or "").strip()
        unsafe_command = str(web.get("unsafe_start_command") or "").strip()
        if auth_command:
            auth_command = _doctor_serve_command(auth_command, language=language)
            typer.echo(doctor_text(language, f"{_doctor_web_start_label(label)} requires auth: {auth_command}", f"{_doctor_web_start_label_zh(label)}需要认证：{auth_command}"))
        if unsafe_command:
            unsafe_command = _doctor_serve_command(unsafe_command, language=language)
            typer.echo(doctor_text(language, f"{_doctor_web_start_label(label)} unsafe opt-in: {unsafe_command}", f"{_doctor_web_start_label_zh(label)} unsafe opt-in：{unsafe_command}"))
        return
    requested_command = str(web.get("requested_start_command") or "").strip()
    suggested_command = str(web.get("suggested_start_command") or "").strip()
    suggested_origin = str(web.get("suggested_origin") or "").strip()
    if requested_command:
        requested_command = _doctor_serve_command(requested_command, language=language)
        typer.echo(doctor_text(language, f"{_doctor_web_start_unavailable_label(label)}: {requested_command}", f"{_doctor_web_start_unavailable_label_zh(label)}：{requested_command}"))
    if suggested_origin:
        typer.echo(doctor_text(language, f"suggested Web: {suggested_origin}", f"建议 Web 地址：{suggested_origin}"))
    if suggested_command:
        suggested_command = _doctor_serve_command(suggested_command, language=language)
        typer.echo(doctor_text(language, f"{_doctor_web_start_label(label)}: {suggested_command}", f"{_doctor_web_start_label_zh(label)}：{suggested_command}"))
    elif web.get("start_blocked_reason") == "bind_failed":
        typer.echo(doctor_text(language, f"{_doctor_web_start_label(label)}: choose a different --web-host / --web-port or check whether this address can be used on this machine", f"{_doctor_web_start_label_zh(label)}：选择其他 --web-host / --web-port，或检查本机是否可使用该地址"))
    else:
        typer.echo(doctor_text(language, f"{_doctor_web_start_label(label)}: stop the existing service or choose another --web-port / serve --port value", f"{_doctor_web_start_label_zh(label)}：停止现有服务，或选择其他 --web-port / serve --port"))


def _doctor_web_start_label(label: str) -> str:
    return "web start after readiness" if label == "web_start_after_readiness" else "web start"


def _doctor_serve_command(command: object, *, language: str) -> str:
    return localized_serve_command(str(command or "").strip(), language=language)


def _doctor_web_start_unavailable_label(label: str) -> str:
    if label == "web_start_after_readiness":
        return "requested web start blocked until App readiness"
    return "web start unavailable"


def _doctor_web_start_label_zh(label: str) -> str:
    return "就绪后启动 Web" if label == "web_start_after_readiness" else "启动 Web"


def _doctor_web_start_unavailable_label_zh(label: str) -> str:
    return "请求的 Web 启动等待 App 就绪" if label == "web_start_after_readiness" else "Web 启动不可用"


def _doctor_web_reason_zh(reason: str) -> str:
    return {
        "port_in_use": "端口已占用",
        "auth_required": "需要认证",
        "bind_failed": "绑定失败",
        "unavailable": "不可用",
    }.get(reason, reason.replace("_", " "))


def _print_doctor_web_bind_details(web: dict, *, language: str) -> None:
    origin = str(web.get("origin") or "").strip()
    bind_origin = str(web.get("bind_origin") or "").strip()
    remote_hint = str(web.get("remote_origin_hint") or "").strip()
    if bind_origin and bind_origin != origin:
        typer.echo(doctor_text(language, f"web bind: {bind_origin}", f"Web 绑定：{bind_origin}"))
    if remote_hint:
        typer.echo(doctor_text(language, f"remote access hint: {remote_hint}", f"远程访问提示：{remote_hint}"))

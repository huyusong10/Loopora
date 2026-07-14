from __future__ import annotations

from collections.abc import Mapping
import errno
import shlex

from loopora import web_bind_preflight
from loopora.agent_adapter_command_prefix import rewrite_loopora_command_entry
from loopora.cli_serve_language import localized_serve_command
from loopora.first_use_route_readiness import first_use_web_readiness_blockers, first_use_web_recovery_actions
from loopora.local_web_service import matching_configured_web_service

FIT_WORKDIR_PLACEHOLDER = "<project-dir>"
FIT_WORKDIR_ARG = shlex.quote(FIT_WORKDIR_PLACEHOLDER)
FIT_WEB_HOST = "127.0.0.1"
FIT_WEB_PORT = 8742


def fit_command_with_web_target(
    command: str,
    *,
    kind: str,
    web_route: Mapping[str, object] | None,
) -> str:
    if kind not in {"confirm_readiness", "support"}:
        return command
    route = fit_default_web_route_context() if web_route is None else web_route
    if str(route.get("preflight_status") or "") != "default_port_in_use_with_suggestion":
        return command
    web_host = str(route.get("host") or FIT_WEB_HOST)
    web_port = int(route.get("port") or FIT_WEB_PORT)
    return f"{command} --web-host {web_host} --web-port {web_port}"


def fit_web_route_action(
    action: dict[str, object],
    *,
    workdir_arg: str,
    cli_entry: str,
    language: str,
    web_route: Mapping[str, object] | None,
) -> dict[str, object]:
    route = fit_default_web_route_context() if web_route is None else web_route
    web_host = str(route.get("host") or FIT_WEB_HOST)
    web_port = int(route.get("port") or FIT_WEB_PORT)
    action["command"] = localized_serve_command(
        rewrite_loopora_command_entry(
            f"loopora serve --open --workdir {workdir_arg} --host {web_host} --port {web_port}",
            cli_entry=cli_entry,
        ),
        language=language,
    )
    action.update(
        {
            "host": web_host,
            "port": web_port,
            "requested_host": str(route.get("requested_host") or FIT_WEB_HOST),
            "requested_port": int(route.get("requested_port") or FIT_WEB_PORT),
            "suggested_port": route.get("suggested_port"),
            "preflight_checked": bool(route.get("preflight_checked")),
            "preflight_status": str(route.get("preflight_status") or "not_checked"),
            "start_blocked_reason": str(route.get("start_blocked_reason") or ""),
            "readiness_blockers": list(route.get("readiness_blockers") or []),
            "opens_browser": True,
        }
    )
    recovery_actions = first_use_web_recovery_actions(
        action,
        workdir_arg=workdir_arg,
        cli_entry=cli_entry,
        language=language,
    )
    if recovery_actions:
        action["recovery_actions"] = recovery_actions
    return action


def fit_default_web_route_context() -> dict[str, object]:
    return {
        "requested_host": FIT_WEB_HOST,
        "requested_port": FIT_WEB_PORT,
        "host": FIT_WEB_HOST,
        "port": FIT_WEB_PORT,
        "suggested_port": None,
        "preflight_checked": False,
        "preflight_status": "not_checked",
        "start_blocked_reason": "",
        "readiness_blockers": [],
    }


def fit_web_route_context(
    workdir_state: Mapping[str, object],
    *,
    workdir_arg: str,
    enabled: bool,
) -> dict[str, object]:
    context = fit_default_web_route_context()
    if (
        not enabled
        or workdir_arg == FIT_WORKDIR_ARG
        or not workdir_state
        or str(workdir_state.get("status") or "") != "ready"
    ):
        return context
    context["preflight_checked"] = True
    context["readiness_blockers"] = first_use_web_readiness_blockers(workdir_state)
    try:
        web_bind_preflight.probe_web_bind(FIT_WEB_HOST, FIT_WEB_PORT)
    except OSError as exc:
        if exc.errno != errno.EADDRINUSE:
            context.update({"preflight_status": "bind_unavailable", "start_blocked_reason": "bind_failed"})
            return context
        if matching_configured_web_service(FIT_WEB_HOST, FIT_WEB_PORT):
            context["preflight_status"] = "matching_service_reusable"
            return context
        suggested_port = web_bind_preflight.next_available_web_port(host=FIT_WEB_HOST, port=FIT_WEB_PORT)
        if suggested_port is None:
            context.update(
                {
                    "preflight_status": "default_port_in_use_no_suggestion",
                    "start_blocked_reason": "port_in_use",
                }
            )
            return context
        context.update(
            {
                "port": suggested_port,
                "suggested_port": suggested_port,
                "preflight_status": "default_port_in_use_with_suggestion",
                "start_blocked_reason": "port_in_use",
            }
        )
        return context
    context["preflight_status"] = "available"
    return context

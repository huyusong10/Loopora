from __future__ import annotations

import os
import socket

from loopora.settings import app_home
from loopora.web_bind_preflight import next_available_web_port
from loopora.web_service_probe import loopora_web_responds

DEFAULT_AGENT_WEB_HOST = "127.0.0.1"
DEFAULT_AGENT_WEB_PORT = 8742
AGENT_WEB_HOST_ENV = "LOOPORA_AGENT_WEB_HOST"
AGENT_WEB_PORT_ENV = "LOOPORA_AGENT_WEB_PORT"
AGENT_WEB_DISCOVERY_PORT_WINDOW = 25


def discover_local_web_service(
    *,
    host: str = DEFAULT_AGENT_WEB_HOST,
    preferred_port: int = DEFAULT_AGENT_WEB_PORT,
) -> dict[str, object]:
    selected_host = str(os.environ.get(AGENT_WEB_HOST_ENV) or host)
    selected_port = _agent_web_port_from_env(preferred_port)
    expected_app_home = str(app_home().resolve())
    first_available_port: int | None = None
    for port in range(selected_port, min(selected_port + AGENT_WEB_DISCOVERY_PORT_WINDOW, 65536)):
        base_url = f"http://{selected_host}:{port}"
        if _loopora_web_responds(base_url, expected_app_home=expected_app_home):
            return {
                "status": "reused",
                "base_url": base_url,
                "reused": True,
                "started": False,
                "start_required": False,
                "start_available": True,
                "port": port,
            }
        if first_available_port is None and _port_is_available(selected_host, port):
            first_available_port = port
    if first_available_port is None:
        first_available_port = next_available_web_port(host=selected_host, port=selected_port)
    if first_available_port is not None:
        return {
            "status": "not_running",
            "base_url": f"http://{selected_host}:{first_available_port}",
            "reused": False,
            "started": False,
            "start_required": True,
            "start_available": True,
            "port": first_available_port,
            "warning": "Loopora Web is not running; start it explicitly with the provided foreground command",
        }
    return {
        "status": "unavailable",
        "base_url": f"http://{selected_host}:{selected_port}",
        "reused": False,
        "started": False,
        "start_required": True,
        "start_available": False,
        "port": selected_port,
        "warning": "no available Loopora Web port was found",
    }

def web_url_for_path(path: str, *, web: dict[str, object]) -> str:
    base_url = str(web.get("base_url") or f"http://{DEFAULT_AGENT_WEB_HOST}:{DEFAULT_AGENT_WEB_PORT}").rstrip("/")
    normalized_path = "/" + str(path or "/").lstrip("/")
    return base_url + normalized_path


def _loopora_web_responds(base_url: str, *, expected_app_home: str = "") -> bool:
    return loopora_web_responds(base_url, expected_app_home=expected_app_home)


def _port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) != 0


def _agent_web_port_from_env(default: int) -> int:
    raw = str(os.environ.get(AGENT_WEB_PORT_ENV) or "").strip()
    if not raw:
        return default
    try:
        port = int(raw)
    except ValueError:
        return default
    if 1 <= port <= 65535:
        return port
    return default

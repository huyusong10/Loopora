from __future__ import annotations

from collections.abc import Callable
import socket
import threading
import time
from urllib.parse import urlencode, urlsplit
import webbrowser

from loopora.web_origins import open_origin_for_bind_host

DEFAULT_BROWSER_OPEN_TIMEOUT_SECONDS = 8.0


def serve_browser_url(*, host: str, port: int, open_path: str = "", workdir: str = "") -> str:
    path = _validated_relative_open_path(open_path)
    if not path:
        query = urlencode({"workdir": str(workdir).strip()}) if str(workdir).strip() else ""
        path = f"/?{query}" if query else "/"
    return open_origin_for_bind_host(host, port).rstrip("/") + path


def schedule_browser_open(
    url: str,
    *,
    timeout_seconds: float = DEFAULT_BROWSER_OPEN_TIMEOUT_SECONDS,
    ready_probe: Callable[[str, int], bool] | None = None,
    opener: Callable[[str], object] | None = None,
) -> threading.Thread:
    parsed = urlsplit(url)
    host = str(parsed.hostname or "")
    port = int(parsed.port or 80)
    probe = ready_probe or _port_accepts_connections
    open_url = opener or _open_system_browser

    def wait_and_open() -> None:
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        while time.monotonic() < deadline:
            if probe(host, port):
                open_url(url)
                return
            time.sleep(0.1)

    thread = threading.Thread(target=wait_and_open, name="loopora-browser-open", daemon=True)
    thread.start()
    return thread


def schedule_browser_open_if_requested(url: str) -> threading.Thread | None:
    return schedule_browser_open(url) if str(url or "").strip() else None


def open_browser_now(url: str, *, opener: Callable[[str], object] | None = None) -> object:
    return (opener or _open_system_browser)(url)


def _validated_relative_open_path(value: str) -> str:
    path = str(value or "").strip()
    if not path:
        return ""
    parsed = urlsplit(path)
    if parsed.scheme or parsed.netloc or not path.startswith("/") or path.startswith("//"):
        raise ValueError("expected a relative Web path beginning with one '/' and no scheme or host")
    return path


def _port_accepts_connections(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.25):
            return True
    except OSError:
        return False


def _open_system_browser(url: str) -> object:
    return webbrowser.open(url, new=2, autoraise=True)


__all__ = ["open_browser_now", "schedule_browser_open", "schedule_browser_open_if_requested", "serve_browser_url"]

from __future__ import annotations

import socket


WEB_BIND_UNAVAILABLE_SUMMARY = "bind target is unavailable"
WEB_BIND_UNAVAILABLE_RECOVERY = (
    "Choose a different --host / --port or check whether this address can be used on this machine."
)
DEFAULT_WEB_PORT = 8742
WEB_PORT_SUGGESTION_WINDOW = 200


def probe_web_bind(host: str, port: int) -> None:
    bind_host = socket_bind_host(host)
    family = socket.AF_INET6 if ":" in bind_host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        sock.bind((bind_host, port))


def next_available_web_port(*, host: str, port: int) -> int | None:
    for candidate in _candidate_web_ports(port):
        try:
            probe_web_bind(host, candidate)
        except OSError:
            continue
        return candidate
    return None


def _candidate_web_ports(port: int) -> tuple[int, ...]:
    candidates: list[int] = []
    max_candidate = min(65535, port + WEB_PORT_SUGGESTION_WINDOW)
    candidates.extend(range(port + 1, max_candidate + 1))
    candidates.extend(range(DEFAULT_WEB_PORT, DEFAULT_WEB_PORT + WEB_PORT_SUGGESTION_WINDOW + 1))
    return tuple(dict.fromkeys(candidate for candidate in candidates if 1 <= candidate <= 65535 and candidate != port))


def socket_bind_host(host: str) -> str:
    normalized = str(host or "").strip()
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1]
    return normalized or "127.0.0.1"

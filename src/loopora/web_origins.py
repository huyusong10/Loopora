from __future__ import annotations


def http_origin(host: str, port: int) -> str:
    normalized = str(host or "").strip()
    if ":" in normalized and not normalized.startswith("["):
        normalized = f"[{normalized}]"
    return f"http://{normalized}:{port}"


def is_wildcard_bind_host(host: str) -> bool:
    return str(host or "").strip().lower() in {"0.0.0.0", "::", "[::]"}


def loopback_origin_for_wildcard(host: str, port: int) -> str:
    if ":" in str(host or ""):
        return http_origin("::1", port)
    return http_origin("127.0.0.1", port)


def remote_origin_hint_for_wildcard(port: int) -> str:
    return f"http://<server-host>:{port}"


def open_origin_for_bind_host(host: str, port: int) -> str:
    if is_wildcard_bind_host(host):
        return loopback_origin_for_wildcard(host, port)
    return http_origin(host, port)

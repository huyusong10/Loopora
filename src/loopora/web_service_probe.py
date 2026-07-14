from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen


def loopora_web_responds(
    base_url: str,
    *,
    expected_app_home: str = "",
    auth_token: str = "",
) -> bool:
    request = Request(
        f"{base_url.rstrip('/')}/api/runtime/activity",
        headers=_probe_headers(auth_token),
    )
    try:
        with urlopen(request, timeout=0.35) as response:
            if int(response.status) != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError, URLError, TimeoutError):
        return False
    if not isinstance(payload, dict) or not {"running_count", "queued_count", "runs"}.issubset(payload):
        return False
    return not (expected_app_home and str(payload.get("app_home") or "") != expected_app_home)


def _probe_headers(auth_token: str) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    token = str(auth_token or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


__all__ = ["loopora_web_responds"]

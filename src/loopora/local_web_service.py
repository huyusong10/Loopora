from __future__ import annotations

import os

from loopora.branding import APP_AUTH_ENV
from loopora.settings import app_home
from loopora.web_origins import open_origin_for_bind_host
from loopora.web_service_probe import loopora_web_responds


def matching_configured_web_service(host: str, port: int) -> bool:
    return loopora_web_responds(
        open_origin_for_bind_host(host, port),
        expected_app_home=str(app_home().resolve()),
        auth_token=str(os.environ.get(APP_AUTH_ENV) or "").strip(),
    )


__all__ = ["matching_configured_web_service"]

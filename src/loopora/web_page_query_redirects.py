from __future__ import annotations

from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import RedirectResponse

from loopora.web_url_utils import is_sensitive_redirect_query_key


def new_loop_redirect(request: Request) -> RedirectResponse | None:
    if _looks_like_bundle_import_query(request):
        return RedirectResponse(url=_forward_create_query(request, "/loops/new/manual", "bundle-import-form"), status_code=303)
    if _looks_like_manual_loop_query(request):
        return RedirectResponse(url=_forward_create_query(request, "/loops/new/manual", "manual-loop-form"), status_code=303)
    return clean_create_query_redirect(request)


def new_loop_bundle_redirect(request: Request) -> RedirectResponse | None:
    if _looks_like_bundle_import_query(request):
        return RedirectResponse(url=_forward_create_query(request, "/loops/new/manual", "bundle-import-form"), status_code=303)
    return clean_create_query_redirect(request)


def clean_create_query_redirect(request: Request) -> RedirectResponse | None:
    if not any(is_sensitive_redirect_query_key(key) for key in request.query_params):
        return None
    query = urlencode([(key, value) for key, value in request.query_params.multi_items() if not is_sensitive_redirect_query_key(key)])
    return RedirectResponse(url=f"{request.url.path}{'?' + query if query else ''}", status_code=303)


def clean_bundles_query_redirect(request: Request) -> RedirectResponse | None:
    if not any(is_sensitive_redirect_query_key(key) for key in request.query_params):
        return None
    query = urlencode([(key, value) for key, value in request.query_params.multi_items() if not is_sensitive_redirect_query_key(key)])
    fragment = "bundle-import-panel" if _looks_like_bundle_import_query(request) else ""
    return RedirectResponse(
        url=f"/bundles{'?' + query if query else ''}{'#' + fragment if fragment else ''}",
        status_code=303,
    )


def _forward_create_query(request: Request, path: str, fragment: str) -> str:
    query = urlencode([(key, value) for key, value in request.query_params.multi_items() if not is_sensitive_redirect_query_key(key)])
    return f"{path}{'?' + query if query else ''}#{fragment}"


def _looks_like_bundle_import_query(request: Request) -> bool:
    keys = set(request.query_params.keys())
    return bool(keys & {"replace_bundle_id", "bundle_path", "bundle_yaml"})


def _looks_like_manual_loop_query(request: Request) -> bool:
    keys = {key for key in request.query_params if not is_sensitive_redirect_query_key(key)}
    return bool(
        keys
        & {
            "name",
            "spec_path",
            "orchestration_id",
            "completion_mode",
            "max_iters",
            "max_role_retries",
            "delta_threshold",
            "trigger_window",
            "regression_window",
            "iteration_interval_seconds",
        }
    )

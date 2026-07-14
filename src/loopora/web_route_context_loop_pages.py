from __future__ import annotations

from fastapi import Request
from fastapi.responses import HTMLResponse

from loopora.providers import list_executor_profiles
from loopora.settings import load_recent_workdirs
from loopora.web_bundle_inputs import _normalize_bundle_import_form
from loopora.web_loop_create_context import NewLoopPageState
from loopora.web_loop_create_context import loop_create_page_context
from loopora.web_loop_create_context import new_loop_page_state_from_args
from loopora.web_loop_inputs import (
    _loop_form_is_pristine,
    _normalize_loop_form,
)
from loopora.web_url_utils import with_query_params


class WebRouteLoopPagesMixin:
    def render_new_loop(
        self,
        request: Request,
        state: NewLoopPageState | None = None,
        **raw_state: object,
    ) -> HTMLResponse:
        state = new_loop_page_state_from_args(state, raw_state)
        form_values = _normalize_loop_form(state.values)
        service = self.svc()
        create_context = loop_create_page_context(request, service, page_mode=state.page_mode)
        workdir_context = str(create_context["workdir_context"])
        asset_return_to = str(create_context["asset_return_to"])
        return self.templates.TemplateResponse(
            request,
            "new_loop.html",
            {
                "request": request,
                "create_page_mode": state.page_mode,
                "form_values": form_values,
                "pristine_loop_form": _normalize_loop_form(None),
                "form_error": state.form_error,
                "form_recovery": dict(state.form_recovery or {}),
                "import_values": _normalize_bundle_import_form(state.import_values),
                "import_error": state.import_error,
                "import_recovery": dict(state.import_recovery or {}),
                "workdir_context": workdir_context,
                "create_choice_links": create_context["create_choice_links"],
                "create_choice_existing_work": create_context["create_choice_existing_work"],
                "loop_import_form_action": with_query_params(
                    "/loops/new/manual/import-bundle",
                    workdir=workdir_context or None,
                ),
                "loop_manual_form_action": with_query_params(
                    "/loops/new/manual",
                    workdir=workdir_context or None,
                ),
                "composer_orchestrations_href": with_query_params(
                    "/orchestrations",
                    workdir=workdir_context or None,
                    return_to=asset_return_to,
                ),
                "composer_roles_href": with_query_params(
                    "/roles",
                    workdir=workdir_context or None,
                    return_to=asset_return_to,
                ),
                "executor_profiles": list_executor_profiles(),
                "orchestrations": self.svc().list_orchestrations(),
                "recent_workdirs": load_recent_workdirs(),
                "allow_draft_restore": (state.form_error is None and _loop_form_is_pristine(form_values) and not workdir_context),
                "access_state": self.access_state,
            },
        )

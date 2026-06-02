from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from web_static_projection_support import REPO_ROOT, STATIC_ROOT


def test_run_detail_page_loads_projection_renderer_before_api_and_controller() -> None:
    scripts = repo_text("src", "loopora", "templates", "partials", "run_detail_scripts.html")

    assert "initialProjection" in scripts
    assert scripts.index("pages/run_detail_projection.js") < scripts.index("pages/run_detail_api.js")
    assert scripts.index("pages/run_detail_projection.js") < scripts.index("pages/run_detail.js")


def test_run_detail_client_normalizes_run_payloads_through_web_projection() -> None:
    api_js = static_text("pages", "run_detail_api.js")
    page_js = static_text("pages", "run_detail.js")
    projection_js = static_text("pages", "run_detail_projection.js")

    assert "normalizeRunPayload(payload)" in api_js
    assert "normalizeInitialRun(runDetailData)" in page_js
    assert "web_projection" in projection_js
    assert "summary.run_status" in projection_js


def test_run_detail_progress_uses_strategy_step_projection_name() -> None:
    progress_js = static_text("pages", "run_detail_progress.js")
    projection_js = static_text("pages", "run_detail_projection.js")
    sources = "\n".join(
        [
            static_text("pages", "run_detail_render.js"),
            static_text("pages", "run_detail.css"),
            repo_text("src", "loopora", "templates", "run_detail.html"),
        ]
    )

    assert "strategy_step" in f"{progress_js}\n{sources}"
    assert "stage-chip--strategy" in sources
    assert "workflow_json" not in progress_js
    assert "workflow_json" in projection_js
    old_markers = (
        "workflow" + "_step",
        "workflow" + "LoopSummary",
        "stage-chip--" + "workflow",
        "data-" + "workflow-empty",
    )
    for old_marker in old_markers:
        assert old_marker not in f"{progress_js}\n{sources}"


def test_run_detail_projection_normalizer_can_render_projection_only_payload() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for JS projection normalizer coverage")
    projection = {
        "status": "succeeded",
        "strategy_source": {
            "roles": [{"id": "builder", "archetype": "builder", "name": "Builder"}],
            "steps": [{"id": "builder_step", "role_id": "builder"}],
        },
        "summary": {
            "run_id": "run_projection_only",
            "loop_id": "loop_projection_only",
            "run_status": "succeeded",
        },
        "task_verdict": {"status": "passed", "summary": "Evidence-backed verdict passed."},
        "display": {"summary_md": "Run summary from projection."},
        "timing": {"started_at": "2026-05-28T00:00:01Z"},
    }
    script = f"""
const fs = require("fs");
const vm = require("vm");
const context = {{window: {{}}}};
[
  {json.dumps(str(STATIC_ROOT / "pages" / "run_detail_projection.js"))},
  {json.dumps(str(STATIC_ROOT / "pages" / "run_detail_progress_time.js"))},
  {json.dumps(str(STATIC_ROOT / "pages" / "run_detail_progress_activity.js"))},
  {json.dumps(str(STATIC_ROOT / "pages" / "run_detail_progress.js"))},
].forEach((sourcePath) => vm.runInNewContext(fs.readFileSync(sourcePath, "utf8"), context));
const normalized = context.window.LooporaRunDetailProjection.normalizeRunPayload({{web_projection: {json.dumps(projection)}}});
if (normalized.id !== "run_projection_only") throw new Error("id not projected");
if (normalized.status !== "succeeded") throw new Error("status not projected");
if (normalized.task_verdict.status !== "passed") throw new Error("task verdict not projected");
if (normalized.strategy_source.steps[0].id !== "builder_step") throw new Error("strategy source not projected");
if (normalized.summary_md !== "Run summary from projection.") throw new Error("summary not projected");
if (normalized.started_at !== "2026-05-28T00:00:01Z") throw new Error("timing not projected");
if (Object.prototype.hasOwnProperty.call(normalized, "raw_only_field")) throw new Error("raw fields leaked");
const projector = context.window.LooporaRunDetailProgress.createProgressProjector({{
  localeText: (zh, en) => en || zh || "",
  getCurrentRun: () => normalized,
  getProgressEvents: () => [],
  getConsoleEvents: () => [],
}});
const stepStage = projector.getProgressStages(normalized).find((stage) => stage.stepId === "builder_step");
if (!stepStage || stepStage.title !== "Builder") throw new Error("projection strategy source did not drive progress stages");
if (stepStage.kind !== "strategy_step") throw new Error("strategy step kind not projected");
const rawNormalized = context.window.LooporaRunDetailProjection.normalizeRunPayload({{
  id: "run_raw_compat",
  status: "running",
  workflow_json: {{
    roles: [{{id: "inspector", archetype: "inspector", name: "Inspector"}}],
    steps: [{{id: "inspector_step", role_id: "inspector"}}],
  }},
}});
if (rawNormalized.strategy_source.steps[0].id !== "inspector_step") throw new Error("raw compatibility strategy source not normalized");
"""

    subprocess.run([node, "-e", script], cwd=REPO_ROOT, check=True, text=True, capture_output=True)


def test_run_detail_routes_use_projection_service_as_primary_boundary() -> None:
    pages = repo_text("src", "loopora", "web_route_loop_run_pages.py")
    api = repo_text("src", "loopora", "web_route_run_api.py")

    assert "app_services.projection.web_run_detail(run)" in pages
    assert "app_services.projection.web_run_detail(run)" in api
    assert "from loopora.web_projection import web_run_detail_projection" not in pages
    assert "from loopora.web_projection import web_run_detail_projection" not in api


def static_text(*parts: str) -> str:
    return STATIC_ROOT.joinpath(*parts).read_text(encoding="utf-8")


def repo_text(*parts: str) -> str:
    return REPO_ROOT.joinpath(*parts).read_text(encoding="utf-8")

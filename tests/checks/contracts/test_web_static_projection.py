from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
STATIC_ROOT = REPO_ROOT / "src" / "loopora" / "static"


def test_app_css_is_layer_manifest_with_legacy_backstop() -> None:
    app_css = (STATIC_ROOT / "app.css").read_text(encoding="utf-8")

    for layer in ("theme", "base", "layout", "components", "pages", "legacy"):
        assert f'@import url("./styles/{layer}.css");' in app_css
        assert (STATIC_ROOT / "styles" / f"{layer}.css").exists()
    assert "Deep Visual Polish" in (STATIC_ROOT / "styles" / "legacy.css").read_text(encoding="utf-8")


def test_run_detail_page_loads_projection_renderer_before_api_and_controller() -> None:
    scripts = (REPO_ROOT / "src" / "loopora" / "templates" / "partials" / "run_detail_scripts.html").read_text(encoding="utf-8")

    assert "initialProjection" in scripts
    assert scripts.index("pages/run_detail_projection.js") < scripts.index("pages/run_detail_api.js")
    assert scripts.index("pages/run_detail_projection.js") < scripts.index("pages/run_detail.js")


def test_run_detail_client_normalizes_run_payloads_through_web_projection() -> None:
    api_js = (STATIC_ROOT / "pages" / "run_detail_api.js").read_text(encoding="utf-8")
    page_js = (STATIC_ROOT / "pages" / "run_detail.js").read_text(encoding="utf-8")
    projection_js = (STATIC_ROOT / "pages" / "run_detail_projection.js").read_text(encoding="utf-8")

    assert "normalizeRunPayload(payload)" in api_js
    assert "normalizeInitialRun(runDetailData)" in page_js
    assert "web_projection" in projection_js
    assert "summary.run_status" in projection_js


def test_run_detail_projection_normalizer_can_render_projection_only_payload() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for JS projection normalizer coverage")
    projection = {
        "schema_version": 3,
        "kind": "web_run_detail",
        "status": "succeeded",
        "summary": {
            "run_id": "run_projection_only",
            "loop_id": "loop_projection_only",
            "run_status": "succeeded",
            "task_verdict_status": "passed",
            "current_iter": 2,
            "active_role": "gatekeeper",
            "workdir": "/tmp/loopora-projection",
        },
        "lifecycle": {
            "run_id": "run_projection_only",
            "loop_id": "loop_projection_only",
            "run_status": "succeeded",
            "current_iter": 2,
            "active_role": "gatekeeper",
            "workdir": "/tmp/loopora-projection",
        },
        "task_verdict": {"status": "passed", "summary": "Evidence-backed verdict passed."},
        "display": {"summary_md": "Run summary from projection."},
        "timing": {
            "queued_at": "2026-05-28T00:00:00Z",
            "started_at": "2026-05-28T00:00:01Z",
            "finished_at": "2026-05-28T00:00:05Z",
            "updated_at": "2026-05-28T00:00:05Z",
            "created_at": "2026-05-28T00:00:00Z",
        },
        "technical_handoff": {"run_url": "/runs/run_projection_only"},
        "diagnostics": {"raw_shape": "run_record"},
    }
    script = f"""
const fs = require("fs");
const vm = require("vm");
const context = {{window: {{}}}};
vm.runInNewContext(fs.readFileSync({json.dumps(str(STATIC_ROOT / "pages" / "run_detail_projection.js"))}, "utf8"), context);
const normalized = context.window.LooporaRunDetailProjection.normalizeRunPayload({{web_projection: {json.dumps(projection)}}});
if (normalized.id !== "run_projection_only") throw new Error("id not projected");
if (normalized.status !== "succeeded") throw new Error("status not projected");
if (normalized.task_verdict.status !== "passed") throw new Error("task verdict not projected");
if (normalized.summary_md !== "Run summary from projection.") throw new Error("summary not projected");
if (normalized.started_at !== "2026-05-28T00:00:01Z") throw new Error("timing not projected");
if (Object.prototype.hasOwnProperty.call(normalized, "raw_only_field")) throw new Error("raw fields leaked");
"""

    subprocess.run([node, "-e", script], cwd=REPO_ROOT, check=True, text=True, capture_output=True)


def test_run_detail_routes_use_projection_service_as_primary_boundary() -> None:
    pages = (REPO_ROOT / "src" / "loopora" / "web_route_pages.py").read_text(encoding="utf-8")
    api = (REPO_ROOT / "src" / "loopora" / "web_route_run_api.py").read_text(encoding="utf-8")

    assert "app_services.projection.web_run_detail(run)" in pages
    assert "app_services.projection.web_run_detail(run)" in api
    assert "from loopora.web_projection import web_run_detail_projection" not in pages
    assert "from loopora.web_projection import web_run_detail_projection" not in api

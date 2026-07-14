from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
STATIC_ROOT = REPO_ROOT / "src" / "loopora" / "static"

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
    assert "error.payload = payload" in api_js
    assert "error.status = response.status" in api_js
    assert "normalizeInitialRun(runDetailData)" in page_js
    assert "web_projection" in projection_js
    assert "summary.run_status" in projection_js


def test_run_detail_api_errors_preserve_structured_recovery_payload() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for JS API helper coverage")
    script = """
const fs = require("fs");
const vm = require("vm");
const context = {
  window: {},
  fetch: async () => ({
    ok: false,
    status: 503,
    json: async () => ({
      error: "background worker could not be started",
      run_recovery: "retry_run_start",
      next_actions: [{kind: "retry_web_run_start", target: "web_loop_start"}],
    }),
  }),
};
vm.createContext(context);
vm.runInContext(fs.readFileSync("src/loopora/static/pages/run_detail_api.js", "utf8"), context);
(async () => {
  try {
    await context.window.LooporaRunDetailApi.stopRun("run_1");
    throw new Error("expected stopRun to reject");
  } catch (error) {
    if (error.status !== 503) throw new Error("status was not preserved");
    if (!error.payload || error.payload.run_recovery !== "retry_run_start") {
      throw new Error("structured recovery payload was not preserved");
    }
    if (error.payload.next_actions?.[0]?.kind !== "retry_web_run_start") {
      throw new Error("next action was not preserved");
    }
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
"""

    subprocess.run([node, "-e", script], cwd=REPO_ROOT, check=True, text=True, capture_output=True)


def test_run_detail_client_actions_can_render_structured_recovery() -> None:
    template = repo_text("src", "loopora", "templates", "run_detail.html")
    page_js = static_text("pages", "run_detail.js")
    app_js = repo_text("src", "loopora", "static", "app.js")

    assert 'data-testid="run-stop-recovery"' in template
    assert 'data-recovery-panel' in template
    assert "function renderRunActionRecovery(payload" in page_js
    assert "function renderRunActionRecoveryFromError(error" in page_js
    assert "renderRunActionRecoveryFromError(error, {testid: \"run-stop-recovery\"})" in page_js
    assert "window.LooporaUI.recoveryPanelHtml(payload" in page_js
    assert "runActionRecoveryLink: true" in page_js
    assert "String(action?.note" not in page_js
    assert 'data-recovery-action-kind="${escapeHtml(kind)}"' in app_js
    assert "action?.redirect_url" in app_js
    assert 'data-recovery-action-link' in app_js
    assert 'data-run-action-recovery-link' in app_js
    assert "recoveryActionLinkLabel(action)" in app_js
    assert "function recoveryPanelHtml(payload" in app_js
    assert "window.LooporaUI?.bindRecoveryCommandCopy?.()" in page_js


def test_run_detail_active_phase_prioritizes_progress_without_premature_verdict_actions() -> None:
    template = repo_text("src", "loopora", "templates", "run_detail.html")
    page_js = static_text("pages", "run_detail.js")
    takeaway_js = static_text("pages", "run_detail_takeaways.js")
    render_js = static_text("pages", "run_detail_render.js")
    stylesheet = static_text("pages", "run_detail.css")

    assert all(
        fragment in template
        for fragment in (
            "show_run_revision_action = terminal_run",
            'data-run-phase="{{ \'terminal\' if terminal_run else \'active\' }}"',
            'id="run-phase-intro"',
            'id="takeaway-phase-title"',
            'id="takeaway-outcome-label"',
            'data-run-action-availability="active"',
            'data-run-action-handoff="terminal-results"',
            "Evidence underway",
            "without treating missing evidence as a final verdict before the run ends",
            'data-testid="run-progress-panel"{% if not terminal_run %} open{% endif %}',
        )
    )
    assert all(
        fragment in page_js
        for fragment in (
            "function syncRunPhaseLayout(run)",
            "function syncRunActionHandoff(run)",
            "syncRunActionHandoff(run);",
            'document.querySelectorAll(\'[data-run-action-availability="active"]\')',
            "control.hidden = true",
            'control.setAttribute("aria-disabled", "true")',
            'grid.dataset.runPhase = active ? "active" : "terminal"',
            "grid.insertBefore(progress, takeaways)",
            "grid.insertBefore(takeaways, progress)",
            'progress.classList.toggle("trace-material-panel", !active)',
        )
    )
    assert all(
            fragment in takeaway_js
            for fragment in (
                "function runIsActive(run)",
                'active ? "Required evidence" : "Required basis"',
                '"Advisory follow-up"',
                'title: localeText("等待证据收束", "Evidence pending")',
            "current gaps are not classified as failure yet",
        )
    )
    assert "takeawayProjector.evidenceCoverageHtml(snapshot, runId, getRun())" in render_js
    assert '.run-judgment-grid[data-run-phase="active"] .progress-panel' in stylesheet
    assert ".hero-run-detail .hero-actions > .run-action-refresh-notice" in stylesheet
    progress_js = static_text("pages", "run_detail_progress.js")
    assert all(
        fragment in progress_js
        for fragment in (
            'localeText("等待收束", "Pending closure")',
            'localeText("等待前序阶段", "Waiting")',
            "After the preceding stages finish, this closes the run",
        )
    )


def test_run_detail_terminal_decisions_follow_evidence_and_exports_stay_secondary() -> None:
    template = repo_text("src", "loopora", "templates", "run_detail.html")
    stylesheet = static_text("pages", "run_detail.css")

    assert all(
        fragment in template
        for fragment in (
            'data-testid="run-export-menu"',
            'class="run-export-menu-actions"',
            'data-testid="run-result-decision"',
            'data-testid="run-result-decision-actions"',
            'data-result-decision-state=',
            "recording changes attention state, not proof",
        )
    )
    assert template.index('data-testid="takeaway-evidence-strip"') < template.index(
        'data-testid="run-result-decision"'
    )
    assert 'data-testid="run-evidence-improve-button"' not in template
    assert all(
        fragment in stylesheet
        for fragment in (
            ".run-export-menu-actions",
            ".run-result-decision",
            ".run-result-decision-actions",
        )
    )


def test_run_detail_terminal_verdict_explains_required_basis_and_advisory_follow_up() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for terminal verdict projector coverage")
    script = r'''
const fs = require("fs");
const vm = require("vm");
const context = {window: {}};
vm.createContext(context);
vm.runInContext(fs.readFileSync("src/loopora/static/pages/run_detail_takeaways.js", "utf8"), context);
const projector = context.window.LooporaRunDetailTakeaways.createTakeawayProjector({
  localeText: (_zh, en) => en,
});
const passed = {
  task_verdict: {
    status: "passed",
    summary: "GateKeeper accepted required evidence.",
    buckets: {
      proven: [
        {id: "done_when.primary", required: true},
        {id: "gatekeeper.finish", required: true},
        {id: "advisory.docs", required: false},
      ],
      weak: [],
      unproven: [{id: "advisory.polish", required: false}],
      blocking: [],
      residual_risk: [],
    },
  },
  evidence_coverage: {
    status: "weak",
    required_target_count: 2,
    covered_required_target_count: 2,
    advisory_target_count: 2,
    covered_advisory_target_count: 1,
    missing_advisory_target_count: 1,
  },
  evidence_manifest: {
    manifest_path: "evidence/manifest.json",
    claim_count: 2,
    artifact_backed_claim_count: 2,
    direct_proof_claim_count: 0,
    run_artifact_claim_count: 2,
  },
};
const outcome = projector.evidenceOutcome(passed, {status: "succeeded"});
const html = projector.evidenceCoverageHtml(passed, "run_passed", {status: "succeeded"});
if (outcome.title !== "Required evidence passed") throw new Error(outcome.title);
if (!outcome.detail.includes("Required basis 2/2 proven")) throw new Error(outcome.detail);
if (!outcome.detail.includes("1 advisory follow-up remains")) throw new Error(outcome.detail);
for (const marker of ["Required basis", "Advisory follow-up", "Evidence sources", "2/2 artifact-backed"]) {
  if (!html.includes(marker)) throw new Error(`missing ${marker}: ${html}`);
}
if (html.includes("Proof strength")) throw new Error("direct-proof ratio must not pose as overall proof strength");
const insufficient = {
  task_verdict: {status: "insufficient_evidence", summary: "Required target is still missing.", buckets: {}},
  evidence_coverage: {status: "partial", required_target_count: 1, missing_required_target_count: 1},
};
const insufficientOutcome = projector.evidenceOutcome(insufficient, {status: "succeeded"});
if (insufficientOutcome.title !== "Insufficient evidence") throw new Error(insufficientOutcome.title);
''';
    subprocess.run([node, "-e", script], cwd=REPO_ROOT, check=True, text=True, capture_output=True)


def test_run_detail_trace_path_actions_are_copy_safe_in_network_mode() -> None:
    template = repo_text("src", "loopora", "templates", "run_detail.html")
    page_js = static_text("pages", "run_detail.js")

    assert 'data-path-action-mode="{{ \'open\' if access_state.native_dialogs_enabled else \'copy\' }}"' in template
    assert "Copy workdir path" in template
    assert "Copy .loopora logs path" in template
    assert "takeaway-open-build" in template
    assert "takeaway-open-logs" in template
    assert all(fragment in template for fragment in ('id="run-progress-panel" data-testid="run-progress-panel"', 'id="run-console-panel" data-testid="run-console-panel"', 'id="run-timeline-panel" data-testid="run-timeline-panel"', 'data-testid="takeaway-empty-progress-link"', 'href="#run-progress-panel"', 'data-testid="takeaway-empty-console-link"', 'data-testid="timeline-empty-console-link"', 'href="#run-console-panel"'))
    build_button = template.split('id="takeaway-open-build"', 1)[1].split("</button>", 1)[0]
    log_button = template.split('id="takeaway-open-logs"', 1)[1].split("</button>", 1)[0]
    assert 'disabled aria-disabled="true"' not in build_button + log_button
    assert "function copyTracePath(path)" in page_js
    assert "window.LooporaUI.writeTextToClipboard(path)" in page_js
    assert all(fragment in page_js for fragment in ("window.LooporaUI?.renderGlobalManualCopy?.(path", "run-trace-path-manual-copy-textarea", "The browser blocked automatic copy; copy the path at the bottom of the page manually."))
    assert "window.LooporaUI.writeTextToClipboard(value)" in page_js
    assert all(fragment in f"{template}\n{page_js}" for fragment in ("data-agent-entry-manual-copy", "run-agent-entry-manual-copy", "data-agent-handoff-manual-copy", "function renderAgentHandoffManualCopy", "window.LooporaUI?.renderManualCopy?.(container, value", "agent-handoff-manual-copy-textarea", "Unable to copy automatically. Copy the handoff value below manually."))
    assert "navigator.clipboard.writeText" not in page_js
    assert 'button?.dataset?.pathActionMode === "copy"' in page_js
    assert "handleTracePathAction(buildPathButton, takeawaySnapshot?.build_dir)" in page_js
    assert "handleTracePathAction(logPathButton, takeawaySnapshot?.log_dir)" in page_js


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


def test_run_detail_same_agent_handoff_labels_are_explicit() -> None:
    template = repo_text("src", "loopora", "templates", "run_detail.html")
    progress_js = static_text("pages", "run_detail_progress.js")

    assert all(fragment in template for fragment in ("Next same-Agent handoff", "下一步同一 Agent 交接", "Target role Agent", "目标角色 Agent", "Copy target role Agent", "复制目标角色 Agent"))
    assert all(fragment in progress_js for fragment in ("Awaiting same Agent", "等待同一 Agent"))
    assert all(fragment not in f"{template}\n{progress_js}" for fragment in ("Next Agent handoff", "下一步 Agent 交接", "Awaiting Agent", "等待 Agent", "Target Agent", "目标 Agent", "Copy target Agent", "复制目标 Agent"))


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
    run_pages = repo_text("src", "loopora", "web_route_context_run_pages.py")
    api = repo_text("src", "loopora", "web_route_run_api.py")

    assert "return ctx.render_run_detail(request, run_id)" in pages
    assert "app_services.projection.web_run_detail(run)" in run_pages
    assert "app_services.projection.web_run_detail(run)" in api
    assert "from loopora.web_projection import web_run_detail_projection" not in pages
    assert "from loopora.web_projection import web_run_detail_projection" not in run_pages
    assert "from loopora.web_projection import web_run_detail_projection" not in api


def static_text(*parts: str) -> str:
    return STATIC_ROOT.joinpath(*parts).read_text(encoding="utf-8")


def repo_text(*parts: str) -> str:
    return REPO_ROOT.joinpath(*parts).read_text(encoding="utf-8")

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from loopora.web_start_context import workdir_context_preserving_href
from loopora.web_url_utils import safe_local_return_path, with_query_params


ROOT = Path(__file__).resolve().parents[3]


def _run_node(script: str) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for static JS module checks")
    subprocess.run([node, "-e", script], cwd=ROOT, text=True, check=True)


def _assert_recovery_action_labels(recovery_macro: str) -> None:
    for fragment in (
        "{% macro recovery_action_label(kind)",
        '{% macro recovery_action_hint(kind, note="")',
        "{% macro recovery_action_link_label(kind)",
        'kind == "retry_web_compose"',
        'kind == "retry_web_run_start"',
        'kind == "review_alignment_bundle"',
        'kind == "retry_alignment_import"',
        "recovery_action_label(action.kind)",
        "recovery_action_hint(action.kind, action.note)",
        "action.form_id",
        "action.form_action",
        "data-recovery-action-form",
        "action.redirect_url",
        "data-recovery-action-link",
        "data-run-action-recovery-link",
    ):
        assert fragment in recovery_macro
    assert recovery_macro.index("<span>{{ recovery_action_hint(action.kind, action.note) }}</span>") < recovery_macro.index("{% if action.command %}")
    assert recovery_macro.index("{% elif action.form_id %}") < recovery_macro.index("{% elif action.form_action %}")
    assert recovery_macro.index("{% elif action.form_action %}") < recovery_macro.index("{% elif action.redirect_url %}")


def test_run_detail_static_assets_keep_semantic_hooks_without_layout_contracts() -> None:
    template = (ROOT / "src" / "loopora" / "templates" / "run_detail.html").read_text(encoding="utf-8")
    console_template = (ROOT / "src" / "loopora" / "templates" / "run_console.html").read_text(encoding="utf-8")
    web_source = (ROOT / "src" / "loopora" / "web.py").read_text(encoding="utf-8")
    design_source = (ROOT / "design" / "contracts.md").read_text(encoding="utf-8")
    renderer = (ROOT / "src" / "loopora" / "static" / "pages" / "run_detail_render.js").read_text(encoding="utf-8")
    console = (ROOT / "src" / "loopora" / "static" / "pages" / "run_detail_console.js").read_text(encoding="utf-8")
    page_script = (ROOT / "src" / "loopora" / "static" / "pages" / "run_detail.js").read_text(encoding="utf-8")

    for kind in ("target", "context", "step-contract", "template", "outbox", "submit"):
        assert f'data-agent-handoff-copy="{kind}"' in template
        assert f'data-testid="agent-handoff-copy-{kind}"' in template

    for stable_marker in (
        'data-testid="agent-handoff-contract"',
        'data-testid="agent-handoff-continuation"',
        "result_file_contract",
        "known_evidence_count",
        "replace null placeholders",
        "window.LooporaUI.writeTextToClipboard(value)",
        "data-agent-handoff-manual-copy",
        "function renderAgentHandoffManualCopy",
        "window.LooporaUI?.renderManualCopy?.(container, value",
        "agent-handoff-manual-copy-textarea",
        "Unable to copy automatically. Copy the handoff value below manually.",
        "Same-Agent execution boundary",
        "同一 Agent 执行边界",
    ):
        assert stable_marker in template + renderer + page_script

    for verdict_marker in (
        "Task verdict",
        "not_evaluated",
        "insufficient_evidence",
        "Unproven evidence verdict recorded",
    ):
        assert verdict_marker in template + renderer + console

    assert 'data-testid="run-stop-button"' in template
    assert 'data-testid="run-stop-status"' in template
    assert 'data-run-action-availability="active"' in template
    assert 'data-testid="run-action-refresh-notice"' in template
    assert 'data-run-action-handoff="terminal-results"' in template
    assert 'data-testid="run-action-refresh-button"' in template
    assert 'data-testid="run-observation-refresh-button"' in template
    assert 'data-testid="run-action-error" data-return-feedback-param="run_action_error" aria-live="polite"' in template
    assert "href=\"{{ workdir_context_href('/runs/' ~ run.id ~ '/console', workdir_context) }}\"" in template
    assert 'data-testid="console-popout-link"' in template
    assert (
        'href="{{ workdir_context_href(\'/runs/\' ~ run.id, workdir_context) }}" data-testid="console-back-link" data-workdir-context-link="workdir"'
        in console_template
    )
    assert 'templates.env.globals["workdir_context_href"] = workdir_context_href' in web_source
    assert all(
        fragment in design_source
        for fragment in (
            "Run detail and fullscreen Console navigation preserve the current Web target-project context",
            "Empty or failed observation states keep diagnostics and retry reachable",
        )
    )
    assert all(
        fragment in page_script
        for fragment in (
            "setStopRunStatus",
            '[data-run-action-availability="active"]',
            "window.location.reload()",
            '"snapshot-failed"',
            "function loadInitialObservation()",
            "function retryObservationLoad()",
        )
    )
    assert "Agent-first execution boundary" not in template
    assert "alert(" not in page_script


def test_run_detail_console_projector_preserves_core_event_semantics() -> None:
    _run_node(
        r"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync("src/loopora/static/pages/run_detail_console.js", "utf8");
const context = {window: {LooporaUI: {translateStatus: (status) => `status:${status}`}}};
vm.createContext(context);
vm.runInContext(source, context);
const projector = context.window.LooporaRunDetailConsole.createConsoleEventProjector({
  buildConsoleEntry: (event, options) => ({eventType: event.event_type, ...options}),
  localeText: (_zh, en) => en,
  prettyConsoleJson: (value) => JSON.stringify(value, null, 2),
  resolvedPayloadRoleName: () => "Builder",
  buildContextDetail: (payload) => `step=${payload.step_id || "-"}`,
  displayIter: (value) => Number(value) + 1,
  formatDurationMs: (value) => `${value}ms`,
  translateStatus: (status) => `status:${status}`,
});

function assert(condition, message, value) {
  if (!condition) throw new Error(`${message}: ${JSON.stringify(value)}`);
}

const commandLines = projector.buildConsoleLines({
  event_type: "codex_event",
  created_at: "2026-04-30T00:00:00Z",
  role: "builder",
  payload: {type: "command", message: "uv run pytest -q"},
});
assert(commandLines.length === 1 && commandLines[0].channel === "command", "command projection failed", commandLines);

const fileLines = projector.buildConsoleLines({
  event_type: "codex_event",
  created_at: "2026-04-30T00:00:00Z",
  role: "builder",
  payload: {type: "item.completed", item: {type: "file_change", changes: [{path: "src/app.py"}]}},
});
assert(fileLines.length === 1 && fileLines[0].channel === "file", "file projection failed", fileLines);

const terminalLines = projector.buildConsoleLines({
  event_type: "run_finished",
  created_at: "2026-04-30T00:00:00Z",
  payload: {status: "succeeded", task_verdict_status: "insufficient_evidence", task_verdict_summary: "Required coverage still lacks direct evidence."},
});
assert(
  terminalLines.length === 1 &&
  terminalLines[0].tone === "warning" &&
  terminalLines[0].summary.includes("Task verdict insufficient_evidence"),
  "terminal verdict projection failed",
  terminalLines
);

const acceptedLines = projector.buildConsoleLines({
  event_type: "run_result_accepted",
  created_at: "2026-04-30T00:00:01Z",
  payload: {status: "succeeded", task_verdict_status: "insufficient_evidence"},
});
assert(
  acceptedLines.length === 1 &&
  acceptedLines[0].tone === "warning" &&
  acceptedLines[0].summary.includes("Unproven evidence verdict recorded") &&
  !acceptedLines[0].summary.includes("accepted"),
  "accepted insufficient evidence projection failed",
  acceptedLines
);

const reopenedLines = projector.buildConsoleLines({
  event_type: "run_result_acceptance_reopened",
  created_at: "2026-04-30T00:00:02Z",
  payload: {status: "succeeded", task_verdict_status: "insufficient_evidence"},
});
assert(
  reopenedLines.length === 1 &&
  reopenedLines[0].tone === "neutral" &&
  reopenedLines[0].summary.includes("Recorded evidence verdict reopened"),
  "reopened recorded verdict projection failed",
  reopenedLines
);
"""
    )


def test_global_status_translation_covers_ready_alignment_candidates() -> None:
    _run_node(
        r"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync("src/loopora/static/app.js", "utf8");

function assert(condition, message, value) {
  if (!condition) throw new Error(`${message}: ${JSON.stringify(value)}`);
}

const storedLocale = {value: "en"};
const context = {
  window: {
    location: {href: "http://loopora.local/"},
    history: {replaceState() {}},
    localStorage: {
      getItem() { return storedLocale.value; },
      setItem(_key, value) { storedLocale.value = value; },
    },
    setTimeout() { return 0; },
    clearTimeout() {},
  },
  document: {
    documentElement: {dataset: {locale: "en"}, lang: "en"},
    addEventListener() {},
    dispatchEvent() {},
    getElementById() { return null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
  },
  navigator: {},
  Intl,
  URL,
  CustomEvent: function () {},
  console,
};
vm.createContext(context);
vm.runInContext(source, context);

const ui = context.window.LooporaUI;
assert(ui.translateStatus("ready") === "ready for review", "ready status should be localized in English", ui.translateStatus("ready"));
ui.setLocale("zh", {persist: false});
assert(ui.translateStatus("ready") === "方案待审阅", "ready status should be localized in Chinese", ui.translateStatus("ready"));
assert(ui.translateStatus("running") !== "running", "existing active status remains localized in Chinese", ui.translateStatus("running"));
"""
    )


def test_web_orchestration_editor_keeps_parallel_review_advanced_entry() -> None:
    template = (ROOT / "src" / "loopora" / "templates" / "new_orchestration.html").read_text(encoding="utf-8")
    page_script = (ROOT / "src" / "loopora" / "static" / "pages" / "new_orchestration.js").read_text(encoding="utf-8")

    assert 'data-testid="workflow-settings-step-parallel-group"' in template
    assert 'data-step-field="parallel_group"' in template
    assert "canStepUseParallelGroup" in page_script
    assert 'field === "parallel_group"' in page_script
    assert "window.confirm" not in page_script
    assert "pendingStarterBundleId" in page_script
    assert "requestStarterReplacementConfirmation" in page_script
    assert 'data-confirming-starter", "1"' in page_script


def test_manual_loop_form_preserves_structured_recovery_actions() -> None:
    template = (ROOT / "src" / "loopora" / "templates" / "new_loop.html").read_text(encoding="utf-8")
    bundles_template = (ROOT / "src" / "loopora" / "templates" / "bundles.html").read_text(encoding="utf-8")
    bundle_detail_template = (ROOT / "src" / "loopora" / "templates" / "bundle_detail.html").read_text(encoding="utf-8")
    loop_detail_template = (ROOT / "src" / "loopora" / "templates" / "loop_detail.html").read_text(encoding="utf-8")
    run_detail_template = (ROOT / "src" / "loopora" / "templates" / "run_detail.html").read_text(encoding="utf-8")
    recovery_macro = (ROOT / "src" / "loopora" / "templates" / "partials" / "recovery_actions.html").read_text(encoding="utf-8")
    page_script = (ROOT / "src" / "loopora" / "static" / "pages" / "new_loop.js").read_text(encoding="utf-8")
    alignment_script = (ROOT / "src" / "loopora" / "static" / "pages" / "alignment.js").read_text(encoding="utf-8")
    app_script = (ROOT / "src" / "loopora" / "static" / "app.js").read_text(encoding="utf-8")

    assert "recovery_panel(\n    manual_loop_recovery," in template
    assert 'data-testid="alignment-workdir-recovery"' in template
    assert 'actions_testid="manual-loop-recovery-actions"' in template
    assert 'data-testid="{{ testid }}"' in recovery_macro
    assert "workdir_context_preserving_href" in recovery_macro
    assert 'data-workdir-context-formaction="workdir"' in recovery_macro
    assert 'data-workdir-context-form="workdir"' in recovery_macro
    _assert_recovery_action_labels(recovery_macro)
    assert 'recovery_panel(import_recovery, "loop-bundle-import-recovery", render_empty=true, workdir_context=workdir_context, return_to=current_return_to)' in template
    assert 'recovery_panel(import_recovery, "bundle-import-recovery", render_empty=true, workdir_context=workdir_context, return_to=current_return_to)' in bundles_template
    assert 'recovery_panel(derive_recovery, "bundle-derive-recovery", workdir_context=workdir_context, return_to=current_return_to)' in bundles_template

    assert 'recovery_panel(run_start_recovery, "loop-start-run-recovery", workdir_context=workdir_context, return_to=current_return_to)' in loop_detail_template
    assert 'recovery_panel(bundle_action_recovery, "bundle-action-recovery", workdir_context=workdir_context, return_to=current_return_to)' in bundle_detail_template
    assert 'recovery_panel(run_action_recovery, "run-action-recovery", workdir_context=workdir_context, return_to=current_return_to)' in run_detail_template
    assert "import_recovery" in template + bundles_template
    assert "form_recovery" in template
    assert all(
        fragment in loop_detail_template
        for fragment in (
            'data-testid="loop-start-run-error" data-return-feedback-param="run_start_error" aria-live="polite"',
            "run_start_recovery",
            'id="loop-agent-entry-start-guide"',
            'data-testid="loop-agent-entry-manual-copy"',
            'data-testid="loop-history-empty-agent-guide-link"',
            'data-testid="loop-history-empty-start-run-form"',
            'data-testid="loop-history-empty-start-run-button"',
        )
    )
    assert "derive_recovery" in bundles_template
    assert "bundle_action_recovery" in bundle_detail_template
    assert "run_action_recovery" in run_detail_template
    assert "data-recovery-command-copy" in recovery_macro
    assert "data-recovery-command-manual-copy" in recovery_macro
    assert "render_empty=true" in template
    assert "data-recovery-panel" in template
    assert 'status_id="manual-recovery-copy-status"' in template
    assert "function isManualRecoveryPayload(payload)" in page_script
    assert all(fragment in page_script for fragment in ("payload.loop_recovery", "Array.isArray(payload.next_actions)"))
    assert "function renderManualLoopRecovery(payload)" in page_script
    assert "renderManualLoopRecovery(responsePayload)" in page_script
    assert all(fragment not in page_script for fragment in ("function manualRecoveryActionHint(action)", "function renderManualRecoveryAction(action)"))
    assert all(
        fragment in page_script
        for fragment in (
            "window.LooporaUI.recoveryPanelHtml(recoveryPayload",
            "function manualLoopRecoveryPayload(payload)",
            "const recoveryPayload = manualLoopRecoveryPayload(payload);",
            'form_id: "new-loop-form"',
            'form_method: "POST"',
        )
    )
    assert 'itemsTestid: "manual-loop-recovery-actions"' in page_script
    assert "dataset.manualRecoveryCopy" not in page_script
    assert all(
        fragment in f"{template}\n{page_script}\n{app_script}"
        for fragment in (
            "window.LooporaUI.bindRecoveryCommandCopy()",
            "window.LooporaUI.clearRecoveryCommandCopyStatus(manualRecoveryPanel)",
            'const value = workdirInput?.value.trim() || "";',
            'window.LooporaUI.syncWorkdirContext(value, {syncUrl: true, urlParam: "workdir"})',
            'data-workdir-context-form="workdir"',
            "function syncWorkdirFormAction(targetForm",
            'document.querySelectorAll("form[data-workdir-context-form]")',
            "targetForm.action = `${url.pathname}${url.search}${url.hash}`",
            'id="spec-editor-recovery-panel"',
            'data-testid="spec-editor-recovery"',
            "function renderSpecEditorRecovery(payload)",
            'payload.resource_recovery === "invalid_spec_output_target"',
            "window.LooporaUI.recoveryPanelHtml(payload",
            'data-spec-editor-recovery-action="${escapeHtml(kind)}"',
            "await chooseSpecOutputFileFromRecovery();",
            "await saveSpecDocument({silent: false});",
            "await createSpecTemplate();",
            "await validateSpec();",
            "await loadSpecTemplateDraft();",
        )
    )
    assert all(
        fragment in alignment_script
        for fragment in (
            "function renderAlignmentRecovery(payload",
            "error.payload = payload",
            'renderRecoveryFromError(error, {testid: "alignment-session-start-recovery"})',
            'renderRecoveryFromError(error, {testid: "alignment-workdir-context-recovery"})',
            'testid: "alignment-import-recovery"',
            "Fix the Plan File before retrying",
            "window.LooporaUI.recoveryPanelHtml(payload",
            "return window.LooporaUI.writeTextToClipboard(value)",
        )
    )
    assert all(fragment not in alignment_script for fragment in ("function recoveryActionHint(action)", "function writeClipboardTextWithSelectionFallback"))
    assert all(fragment in alignment_script for fragment in ("testid,", "window.LooporaUI?.bindRecoveryCommandCopy?.()"))
    assert "<span></span>" not in alignment_script
    assert all(
        fragment in app_script
        for fragment in (
            "writeTextToClipboard,",
            "renderManualCopy,",
            "renderGlobalManualCopy,",
            "function renderGlobalManualCopy(value",
            "function renderManualCopy(container, value, options = {})",
            "function renderAgentEntryCommandManualCopy",
            "data-agent-entry-manual-copy",
            "agent-entry-command-manual-copy-textarea",
            "The browser blocked automatic copy; copy the /loopora-run command below manually.",
            "textarea.focus({preventScroll: true});",
            "recoveryActionLabel,",
            "recoveryActionHint,",
            "recoveryActionLinkLabel,",
            "recoveryActionHtml,",
            "recoveryPanelHtml,",
            "recoveryActionOptionValue(options.actionControlHtml, action)",
            "const control = customControl || recoveryActionControlHtml(action, options);",
            "function contextPreservingRecoveryUrl(value)",
            "clearRecoveryCommandCopyStatus,",
            "renderRecoveryCommandManualCopy",
            "data-recovery-command-manual-copy",
            "recovery-command-manual-copy-textarea",
            "The browser blocked automatic copy; copy the recovery command below manually.",
            "createRecoveryActionControlFragment,",
            "action?.form_id",
            "data-recovery-action-form",
            "data-workdir-context-formaction",
            "function syncWorkdirFormActionControl(",
            'document.querySelectorAll("[data-workdir-context-formaction]")',
            "formmethod=\"post\"",
            "data-recovery-action-link",
            'data-recovery-copy-status aria-live="polite"',
            "String(action?.note",
            "After fixing the directory, run the read-only readiness check.",
            "Submit this form again after fixing the setup.",
            "review_alignment_bundle",
            "Retry Loop creation",
            "After repairing the candidate source file, reload and validate it.",
        )
    )
    assert "function bindRecoveryCommandCopy()" in app_script
    assert 'document.querySelectorAll("[data-recovery-command-copy]")' in app_script


def test_support_recovery_actions_preserve_return_to() -> None:
    _run_node(
        r"""
const fs = require("fs"), vm = require("vm");
const source = fs.readFileSync("src/loopora/static/app.js", "utf8");
const context = {
  window: {
    location: {href: "http://loopora.local/tools?workdir=/tmp/demo", origin: "http://loopora.local"},
    localStorage: {getItem() { return null; }, setItem() {}},
    setTimeout() { return 0; }, clearTimeout() {}, matchMedia() { return {addEventListener() {}}; },
  },
  document: {documentElement: {dataset: {locale: "en"}, lang: "en"}, addEventListener() {}, dispatchEvent() {}, getElementById() { return null; }, querySelector() { return null; }, querySelectorAll() { return []; }},
  navigator: {}, Intl, URL, URLSearchParams, CustomEvent: function () {}, console,
};
vm.createContext(context); vm.runInContext(source, context);
const html = context.window.LooporaUI.recoveryActionHtml({kind: "open_support", redirect_url: "/support?token=secret"});
if (!html.includes('href="/support?workdir=%2Ftmp%2Fdemo&amp;return_to=%2Ftools%3Fworkdir%3D%252Ftmp%252Fdemo"') || html.includes("token=secret")) throw new Error(html);
const explicit = context.window.LooporaUI.recoveryActionHtml({kind: "open_support", redirect_url: "/support?return_to=/runs/run-1&workdir=/target"});
if (!explicit.includes('href="/support?return_to=%2Fruns%2Frun-1&amp;workdir=%2Ftarget"')) throw new Error(explicit);
"""
    )
    env = Environment(loader=FileSystemLoader(ROOT / "src" / "loopora" / "templates"), autoescape=select_autoescape(("html",)))
    env.globals.update(
        safe_local_return_path=safe_local_return_path,
        workdir_context_preserving_href=workdir_context_preserving_href,
        with_query_params=with_query_params,
    )
    html = str(env.get_template("partials/recovery_actions.html").module.recovery_panel(
        {"summary": "Recover safely", "next_actions": [{"kind": "open_support", "redirect_url": "/support?token=secret"}]},
        "safe-support-recovery",
        workdir_context="/tmp/demo",
        return_to="/runs/run-1?token=secret&tab=result",
    ))
    assert 'href="/support?return_to=%2Fruns%2Frun-1%3Ftab%3Dresult&amp;workdir=%2Ftmp%2Fdemo"' in html
    assert "token=secret" not in html


def test_plan_file_source_path_actions_are_scoped_and_copy_safe() -> None:
    template = (ROOT / "src" / "loopora" / "templates" / "new_loop.html").read_text(encoding="utf-8")
    bundles_template = (ROOT / "src" / "loopora" / "templates" / "bundles.html").read_text(encoding="utf-8")
    import_script = (ROOT / "src" / "loopora" / "static" / "pages" / "bundle_import.js").read_text(encoding="utf-8")
    alignment_script = (ROOT / "src" / "loopora" / "static" / "pages" / "alignment.js").read_text(encoding="utf-8")
    contracts = (ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    path_mode_contract = "data-path-action-mode=\"{{ 'open' if access_state.native_dialogs_enabled else 'copy' }}\""
    assert path_mode_contract in bundles_template
    assert template.count(path_mode_contract) >= 2
    assert "Copy source path" in bundles_template
    assert "Copy source path" in template
    assert 'form.closest("#bundle-import-form") || form.closest("#bundle-import-panel")' in import_script
    assert "const byId = (id) => importSurface.querySelector(`#${id}`);" in import_script
    assert 'document.getElementById("alignment-ready-preview")' not in import_script
    assert 'importSurface.querySelectorAll("[data-preview-tab]")' in import_script
    assert 'copyOnly: sourceOpenButton.dataset.pathActionMode === "copy"' in import_script
    assert all(
        fragment in import_script
        for fragment in (
            'const recoveryPanel = form.querySelector("[data-recovery-panel]");',
            "function browserBundleImportRecoveryPayload(payload)",
            "function renderBundleImportRecovery(payload)",
            "window.LooporaUI.recoveryPanelHtml(projected",
            'form_id: "bundle-import-form-fields"',
            'form_action: action.form_action || currentFormAction()',
            'throw bundleImportErrorFromPayload(',
            "renderBundleImportRecovery(error?.payload || {})",
        )
    )
    assert all(
        fragment in import_script
        for fragment in (
            "window.LooporaUI.writeTextToClipboard(path)",
            "window.LooporaUI?.renderGlobalManualCopy?.(path",
            "bundle-source-path-manual-copy-textarea",
            "The browser blocked automatic copy; copy the source path at the bottom of the page manually.",
        )
    )
    assert all(
        fragment in alignment_script
        for fragment in (
            'copyOnly: sourceOpenButton.dataset.pathActionMode === "copy"',
            "window.LooporaUI?.renderGlobalManualCopy?.(path",
            "alignment-source-path-manual-copy-textarea",
            "The browser blocked automatic copy; copy the source path at the bottom of the page manually.",
        )
    )
    assert "Plan File import/managed source" in contracts


def test_tools_adapter_mutation_preserves_structured_recovery_actions() -> None:
    tools_template = (ROOT / "src" / "loopora" / "templates" / "tools.html").read_text(encoding="utf-8")
    tools_script = (ROOT / "src" / "loopora" / "static" / "pages" / "tools.js").read_text(encoding="utf-8")
    app_styles = (ROOT / "src" / "loopora" / "static" / "app.css").read_text(encoding="utf-8")

    assert 'data-testid="agent-adapter-workdir-recovery"' in tools_template
    assert "function renderAgentAdapterRecovery(payload" in tools_script
    assert "mutationError.payload = payload" in tools_script
    assert "renderAgentAdapterRecoveryFromError(error, {testid: `agent-adapter-${action}-workdir-recovery`})" in tools_script
    assert "clearAgentAdapterRecoveryPanel()" in tools_script
    assert all(
        fragment in tools_script
        for fragment in (
            "function canonicalizeSameAgentAlias()",
            'window.location?.pathname !== "/tools"',
            'const nextUrl = `/same-agent${window.location.search || ""}${window.location.hash || ""}`',
            'window.history.replaceState(window.history.state, "", nextUrl)',
            "canonicalizeSameAgentAlias();",
        )
    )
    assert all(
        fragment in tools_script
        for fragment in (
            'window.LooporaUI.syncWorkdirContext(resolved, {syncUrl: true, urlParam: "workdir"})',
            'window.LooporaUI.syncWorkdirContext(workdir, {syncUrl: true, urlParam: "workdir"})',
            'window.LooporaUI.syncWorkdirContext("", {syncUrl: true, urlParam: "workdir"})',
        )
    )
    assert all(
        fragment in tools_script
        for fragment in (
            "window.LooporaUI.recoveryPanelHtml(payload",
            "actionLabel: (action) => agentAdapterRecoveryActionLabel(action, label)",
            "actionHint: (action) => agentAdapterRecoveryActionHint(action, label)",
            "actionControlHtml: (action) => agentAdapterRecoveryActionControlHtml(action, payload, label)",
            "function bindAgentAdapterRecoveryActionButtons()",
            'data-agent-adapter-recovery-action="${escapeHtml(actionName)}"',
            "requestAgentAdapterUninstall(adapter, button);",
            "mutateAgentAdapter(adapter, action, button);",
            "Retry installing ${label}",
            "Retry uninstalling ${label}",
            "window.LooporaUI?.bindRecoveryCommandCopy?.()",
        )
    )
    assert all(
        fragment in tools_script
        for fragment in ("uninstall-preview", "renderAgentAdapterUninstallPreview", "data-agent-adapter-confirm-uninstall", "agentAdapterUninstallIsPending")
    )
    assert all(
        fragment in tools_script
        for fragment in (
            "function renderAgentReadiness(payload)",
            "const hasExplicitTarget = Boolean(agentAdapterWorkdir())",
            "function syncAgentHostSelection(adapters)",
            "function agentAdapterTargetRequiredMessage()",
            'function agentHostSelectionRequiredMessage(adapter = "")',
            "function agentHostSelectionBlocksMutation(adapter)",
            "agentAdapterCanHandoff(item)",
            "agentAdapterTargetRequiredMessage()",
            "agentHostSelectionRequiredMessage(adapter)",
        )
    )
    assert all(
        fragment not in tools_script
        for fragment in (
            "Confirm the Agent target project",
            "project directory where the Agent will run",
            "Install one Agent entry.",
            "No Agent entry is ready yet",
            "recommended starting point",
            "Not implemented",
            "未实现",
            'payload?.recommended_adapter || "codex"',
            'entry?.adapter || payload?.recommended_adapter || "codex"',
            "return entries[0] || null",
            "`${label} entry is installed or updated",
            "`${label} entry is uninstalled",
            "`${label} entry was not installed",
            "Installing ${label} entry",
            "Uninstalling ${label} entry",
            "接入已安装",
            "接入已卸载",
            "接入未安装",
            "正在安装 ${label} 接入",
            "正在卸载 ${label} 接入",
        )
    )
    assert ".manual-recovery-panel" in app_styles
    assert ".manual-recovery-action code" in app_styles


def test_manual_loop_create_browser_enhancement_opens_failed_run_recovery() -> None:
    page_script = (ROOT / "src" / "loopora" / "static" / "pages" / "new_loop.js").read_text(encoding="utf-8")

    assert "function runStartFailureRedirect(payload)" in page_script
    assert 'payload?.run_recovery !== "retry_run_start"' in page_script
    assert "payload?.redirect_url" in page_script
    assert "payload?.run?.id" in page_script
    assert "window.location.href = redirectUrl" in page_script


def test_asset_catalog_templates_use_return_aware_editor_links() -> None:
    base_template = (ROOT / "src" / "loopora" / "templates" / "base.html").read_text(encoding="utf-8")
    role_definitions_template = (ROOT / "src" / "loopora" / "templates" / "role_definitions.html").read_text(encoding="utf-8")
    orchestrations_template = (ROOT / "src" / "loopora" / "templates" / "orchestrations.html").read_text(encoding="utf-8")
    role_editor_template = (ROOT / "src" / "loopora" / "templates" / "new_role_definition.html").read_text(encoding="utf-8")
    orchestration_editor_template = (ROOT / "src" / "loopora" / "templates" / "new_orchestration.html").read_text(encoding="utf-8")
    bundle_detail_template = (ROOT / "src" / "loopora" / "templates" / "bundle_detail.html").read_text(encoding="utf-8")
    app_script = (ROOT / "src" / "loopora" / "static" / "app.js").read_text(encoding="utf-8")

    assert all(
        fragment in role_definitions_template
        for fragment in (
            'href="{{ create_role_definition_href }}" data-testid="create-role-definition-link" data-workdir-context-link="workdir"',
            'href="{{ nav_compose_href }}" data-testid="role-definitions-compose-link" data-workdir-context-link="workdir"',
            'href="{{ nav_compose_href }}" data-testid="role-definitions-empty-compose-link" data-workdir-context-link="workdir"',
            'data-open-card="{{ role_definition.editor_href }}" data-workdir-context-open-card="workdir"',
            'href="{{ role_definition.editor_href }}" data-workdir-context-link="workdir" tabindex="-1" aria-hidden="true"',
            'data-delete-role-definition="{{ role_definition.id }}"',
            'data-testid="role-definitions-empty-create-link" data-workdir-context-link="workdir"',
            'data-testid="role-definitions-empty-template-link" data-workdir-context-link="workdir"',
            'href="{{ builtin_role_templates[0].editor_href }}" data-testid="role-definitions-empty-template-link" data-workdir-context-link="workdir"',
            "stable reuse across Loops",
            "Choose Creation Path",
        )
    )
    assert 'action="/api/role-definitions/' not in role_definitions_template
    assert 'href="{{ cancel_href }}" data-testid="role-definition-cancel-link" data-workdir-context-link="workdir"' in role_editor_template
    assert 'data-workdir-context-form="workdir"' in role_editor_template
    assert 'class="field-status is-success" data-return-feedback-param="saved" aria-live="polite"' in role_editor_template
    assert all(
        fragment in orchestrations_template
        for fragment in (
            'href="{{ create_orchestration_href }}" data-testid="create-orchestration-link" data-workdir-context-link="workdir"',
            'href="{{ nav_compose_href }}" data-testid="orchestrations-compose-link" data-workdir-context-link="workdir"',
            'href="{{ nav_compose_href }}" data-testid="orchestrations-empty-compose-link" data-workdir-context-link="workdir"',
            'data-open-card="{{ orchestration.editor_href }}" data-workdir-context-open-card="workdir"',
            'href="{{ orchestration.editor_href }}" data-workdir-context-link="workdir" tabindex="-1" aria-hidden="true"',
            'data-delete-orchestration="{{ orchestration.id }}"',
            'data-testid="orchestrations-empty-create-link" data-workdir-context-link="workdir"',
            'data-testid="orchestrations-empty-template-link" data-workdir-context-link="workdir"',
            'href="{{ builtin_orchestrations[0].editor_href }}" data-testid="orchestrations-empty-template-link" data-workdir-context-link="workdir"',
            "reusable team flow",
            "Choose Creation Path",
        )
    )
    assert 'action="/api/orchestrations/' not in orchestrations_template
    assert all(
        fragment in orchestration_editor_template
        for fragment in (
            'href="{{ role_definitions_href }}" data-testid="orchestration-manage-roles-link" data-workdir-context-link="workdir"',
            'href="{{ orchestration_create_from_preset_href }}" data-testid="orchestration-create-from-preset-link" data-workdir-context-link="workdir"',
            'href="{{ cancel_href }}" data-testid="orchestration-cancel-link" data-workdir-context-link="workdir"',
            'data-workdir-context-form="workdir"',
            'class="field-status is-success" data-return-feedback-param="saved" aria-live="polite"',
        )
    )
    assert (
        'href="{{ bundle_orchestration_edit_href }}" data-testid="bundle-orchestration-edit-link" '
        'data-workdir-context-link="workdir"'
    ) in bundle_detail_template
    assert (
        'href="{{ bundle_role_edit_hrefs.get(role_definition.id, \'\') }}" '
        'data-testid="bundle-role-edit-link-{{ role_definition.id }}" data-workdir-context-link="workdir"'
    ) in bundle_detail_template
    assert 'href="{{ workdir_context_href(\'/bundles/\' ~ bundle.id ~ \'/export\', workdir_context) }}"' in bundle_detail_template
    assert 'edit?return_to=/bundles/{{ bundle.id }}"' not in bundle_detail_template
    assert 'href="/bundles/{{ bundle.id }}/export"' not in bundle_detail_template
    assert all(
        fragment in base_template
        for fragment in (
            'data-testid="confirm-modal-status"',
            'data-testid="confirm-modal-preview"',
            'aria-describedby="confirm-modal-detail confirm-modal-preview confirm-modal-status"',
            'tabindex="-1"',
        )
    )
    assert 'selector: "[data-delete-role-definition]"' in app_script
    assert 'selector: "[data-delete-orchestration]"' in app_script
    assert all(
        fragment in app_script
        for fragment in (
            'previewEndpointPrefix: "/api/loops/"',
            'previewEndpointPrefix: "/api/bundles/"',
            'previewEndpointPrefix: "/api/role-definitions/"',
            'previewEndpointPrefix: "/api/orchestrations/"',
            'previewKind: "roleDefinition"',
            'previewKind: "orchestration"',
            "referenced_by_orchestrations",
            "referenced_by_loops",
            "/delete-preview",
            "modalConfirm.disabled = !deleteRequest.deleteAllowed",
            "function trapDeleteModalFocus(event)",
            "DELETE_MODAL_FOCUS_SELECTOR",
            "focusDeleteModalTarget(first)",
            "function openCardTargetUrl(card)",
            "const openUrl = openCardTargetUrl(card)",
            "window.location.href = openUrl",
            "function enhanceOpenCardAccessibility(card)",
            'card.setAttribute("role", "link")',
            "function openCardAccessibleName(card)",
        )
    )
    assert "window.alert(payload.error || config.failure())" not in app_script


def test_returned_asset_surface_feedback_is_visible_and_one_shot() -> None:
    _run_node(
        r"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync("src/loopora/static/app.js", "utf8");

function assert(condition, message, value) {
  if (!condition) throw new Error(`${message}: ${JSON.stringify(value)}`);
}

function runCase(path, {inlineFeedback = false, returnParams = []} = {}) {
  const feedback = {textContent: "", hidden: true, className: "app-feedback"};
  const replacements = [];
  const context = {
    window: {
      location: {href: `http://loopora.local${path}`},
      history: {replaceState: (_state, _title, nextUrl) => replacements.push(nextUrl)},
      localStorage: {getItem() { return null; }, setItem() {}},
      setTimeout() { return 0; },
      clearTimeout() {},
    },
    document: {
      documentElement: {dataset: {locale: "en"}, lang: "en"},
      addEventListener() {},
      dispatchEvent() {},
      getElementById(id) { return id === "app-feedback" ? feedback : null; },
      querySelector(selector) {
        return inlineFeedback && selector === "[data-surface-update-feedback]" ? {} : null;
      },
      querySelectorAll(selector) { return selector === "[data-return-feedback-param]" ? returnParams.map((value) => ({dataset: {returnFeedbackParam: value}})) : []; },
    },
    navigator: {},
    Intl,
    URL,
    CustomEvent: function () {},
    console,
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  context.window.LooporaUI.handleReturnedSurfaceUpdateFeedback();
  return {feedback, replacements, ui: context.window.LooporaUI};
}

const composerReturn = runCase("/loops/new/manual?workdir=/tmp/demo&surface_updated=role%3Abuilder#manual-loop-form");
assert(!composerReturn.feedback.hidden, "composer returns should show global feedback", composerReturn.feedback);
assert(composerReturn.feedback.className.includes("is-success"), "composer feedback should be success state", composerReturn.feedback);
assert(
  composerReturn.replacements[0].startsWith("/loops/new/manual?") &&
    composerReturn.replacements[0].includes("workdir=%2Ftmp%2Fdemo") &&
    !composerReturn.replacements[0].includes("surface_updated") &&
    composerReturn.replacements[0].endsWith("#manual-loop-form"),
  "composer return marker should be removed without losing context or fragment",
  composerReturn.replacements
);
assert(
  composerReturn.ui.returnedSurfaceUpdateMessage("workflow").length > 0 &&
    composerReturn.ui.returnedSurfaceUpdateMessage("role:any").length > 0,
  "known asset surfaces should have visible feedback messages"
);

const inlineReturn = runCase("/bundles/bundle-1?tab=workflow&surface_updated=workflow&saved=1&created_from_loop=1#surface", {inlineFeedback: true, returnParams: ["surface_updated", "saved", "created_from_loop"]});
assert(inlineReturn.feedback.hidden && inlineReturn.feedback.textContent === "", "inline feedback should suppress duplicate toast", inlineReturn.feedback);
assert(
  inlineReturn.replacements[0] === "/bundles/bundle-1?tab=workflow#surface",
  "inline return marker should still be removed",
  inlineReturn.replacements
);
const actionErrorReturn = runCase("/runs/run-1?tab=events&run_action_error=failed&run_start_error=old#actions", {returnParams: ["run_action_error", "run_start_error"]});
assert(actionErrorReturn.replacements[0] === "/runs/run-1?tab=events#actions", "action error markers should be removed without losing context", actionErrorReturn.replacements);

const unknownReturn = runCase("/loops/new/manual?surface_updated=other");
assert(unknownReturn.feedback.hidden, "unknown return markers should not invent success feedback", unknownReturn.feedback);
assert(unknownReturn.replacements.length === 0, "unknown return markers should not be consumed", unknownReturn.replacements);
"""
    )

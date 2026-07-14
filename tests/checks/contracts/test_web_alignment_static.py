from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]


def _run_node(script: str) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is required for static JS module checks")
    subprocess.run([node, "-e", script], cwd=ROOT, text=True, check=True)


def test_alignment_console_projector_labels_judgment_events_without_locking_layout() -> None:
    _run_node(
        r"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync("src/loopora/static/pages/alignment.js", "utf8");
const context = {window: {}, document: {addEventListener: () => {}}};
vm.createContext(context);
vm.runInContext(source, context);
const projector = context.window.LooporaAlignmentConsole.createAlignmentConsoleProjector({
  localeText: (_zh, en) => en,
});

function assert(condition, message, value) {
  if (!condition) throw new Error(`${message}: ${JSON.stringify(value)}`);
}

const userSummary = projector.eventSummary({
  event_type: "alignment_user_message",
  payload: {role: "user", content: "Create a robust import flow."},
});
assert(
  /task/i.test(userSummary) && userSummary.includes("Create a robust import flow."),
  "user task event should stay visible as task judgment evidence",
  userSummary
);

const sourceSummary = projector.eventSummary({
  event_type: "alignment_source_context_selected",
  payload: {source_type: "bundle", source_bundle_id: "bundle_1"},
});
assert(
  /context/i.test(sourceSummary) && !sourceSummary.includes("alignment_source_context_selected"),
  "source event should be projected as a readable context choice",
  sourceSummary
);

const sessionSummary = projector.eventSummary({
  event_type: "alignment_session_created",
  payload: {status: "idle", workdir: "/tmp/project"},
});
assert(
  /session/i.test(sessionSummary) && sessionSummary.includes("idle"),
  "session-created summary should preserve lifecycle status",
  sessionSummary
);

const runStartFailureSummary = projector.eventSummary({
  event_type: "alignment_run_start_failed",
  payload: {
    error: "background worker could not be started",
    run_recovery: "retry_run_start",
  },
});
assert(
  /run start/i.test(runStartFailureSummary) &&
    /retry/i.test(runStartFailureSummary) &&
    !runStartFailureSummary.includes("alignment_run_start_failed"),
  "run-start failures should be projected as recoverable lifecycle state",
  runStartFailureSummary
);

const interruptedSummary = projector.eventSummary({
  event_type: "alignment_interrupted",
  payload: {status: "failed", reason: "local_worker_interrupted"},
});
assert(
  /interrupted/i.test(interruptedSummary) && !interruptedSummary.includes("alignment_interrupted"),
  "local worker interruption should be a readable recovery event",
  interruptedSummary
);

assert(
  projector.eventKind({event_type: "alignment_validation_failed", payload: {error: "invalid yaml"}}) === "error",
  "failed events should render in the error lane"
);
assert(
  projector.eventKind({event_type: "alignment_ready", payload: {status: "ready"}}) === "success",
  "ready events should render in the success lane"
);
assert(
  projector.eventKind({event_type: "codex_event", payload: {type: "command", message: "loopora dev check"}}) === "command",
  "agent command events should keep the command lane"
);
"""
    )


def test_alignment_history_sidebar_uses_shared_renderer_across_create_modes() -> None:
    template = (ROOT / "src" / "loopora" / "templates" / "new_loop.html").read_text(encoding="utf-8")
    manual_script = (ROOT / "src" / "loopora" / "static" / "pages" / "new_loop.js").read_text(encoding="utf-8")
    alignment_script = (ROOT / "src" / "loopora" / "static" / "pages" / "alignment.js").read_text(encoding="utf-8")
    history_script = (ROOT / "src" / "loopora" / "static" / "pages" / "alignment_history.js").read_text(encoding="utf-8")

    assert template.count("pages/alignment_history.js") == 2
    assert "window.LooporaAlignmentHistory" in history_script
    assert "createAlignmentHistory" in manual_script
    assert "createAlignmentHistory" in alignment_script
    assert 'data-history-empty-start-href="{{ create_choice_links.bundle }}"' in template
    assert 'data-workdir-context-dataset-urls="historyEmptyStartHref:alignment_workdir"' in template
    assert all(
        fragment in f"{template}\n{manual_script}"
        for fragment in (
            'data-testid="manual-direct-handoff-bridge"',
            'const FIT_HANDOFF_STORAGE_KEY = "loopora:tutorial-fit-handoff:v1"',
            "function readTutorialDirectHandoff()",
            "directTask: compactText(inputs.task)",
            "directReason: compactText(inputs.direct_path_check)",
            "function directHandoffBlocksManualCreation",
            "function manualDirectHandoffMatchesTarget(handoff)",
            "allowEmptyLeft: !targetWorkdir",
            "const hasWorkdirMismatch = Boolean(handoff && !manualDirectHandoffMatchesTarget(handoff));",
            "const blocksManualCreation = Boolean(handoff && !hasWorkdirMismatch);",
            "setManualCreationBlocked(blocksManualCreation);",
            "data-manual-direct-handoff-use-source",
            "function useManualDirectHandoffSource(sourceWorkdir)",
            'document.addEventListener("loopora:workdirchange", syncManualDraftFromGlobalWorkdir)',
            "function syncManualDraftFromGlobalWorkdir(event)",
            'bundleImportForm?.addEventListener("submit"',
            "dataset.directPathBlocked",
            "manual-direct-handoff-copy",
            "manual-direct-handoff-manual-copy",
            "function renderManualDirectHandoffCommand",
            "window.LooporaUI?.renderManualCopy?.(container, command",
            "manual-direct-handoff-command-textarea",
            "The browser blocked automatic copy; copy the direct-path command below manually.",
            "Direct path is selected, so importing or manually creating a Loop is disabled",
            'document.querySelectorAll("[data-compose-mode-link]")',
            "document.querySelectorAll('[data-compose-action-kind=\"new_web_conversation\"]')",
            "function setManualDirectPathLinkEnabled",
            "window.LooporaUI.setNavigationControlBlocked(link, !enabled",
            'markerDataset: "directPathBlocked"',
            'disabledHrefDataset: "directPathDisabledHref"',
            "workdirInput?.focus?.()",
            "alignment-new-session-button",
        )
    )
    assert "openHref: (session)" in manual_script
    assert all(
        fragment in alignment_script
        for fragment in (
            "openSession: (session) => openHistorySession(session.id)",
            "function openHistorySession(sessionId)",
            "function currentUrlSessionId()",
            "fetchUrlSessionForNavigationGuard",
            "activeSessionBlocksNavigation(localeText(",
            "stop the current conversation before opening another chat",
            "function bindActiveSessionLinkGuard(selector, messageFactory)",
            'bindActiveSessionLinkGuard("[data-compose-mode-link]"',
            "bindActiveSessionLinkGuard('[data-testid=\"nav-compose-link\"]'",
            "stop the current conversation before switching composition paths",
            "stop the current conversation before returning to the composer start",
            'const hasAnyInput = [...FIT_HANDOFF_REQUIRED_INPUT_IDS, "direct_path_check"]',
            'String(payload?.review_completion_command || payload?.direct_decision_command || "").trim()',
            "missingInputIds = blocksWebConversation ? []",
            "function tutorialFitHandoffBlocksCurrentWebConversation(handoff)",
            "handoff?.blocksWebConversation && tutorialHandoffMatchesCurrentWorkdir(handoff)",
            "const directPathBlocksWebConversation = tutorialFitHandoffBlocksCurrentWebConversation(handoff)",
            "setTutorialFitHandoffBlocksWebConversation(!currentSession && directPathBlocksWebConversation)",
            "function directPathBlocksWebStart()",
            "function bindDirectPathWebStartGuard(selector)",
            'bindDirectPathWebStartGuard("[data-compose-mode-link]")',
            "window.LooporaUI.setNavigationControlBlocked(control, !enabled",
            'markerDataset: "directPathBlocked"',
            'baseDisabledDataset: "directPathBaseDisabled"',
            "function syncAlignmentDraftFromGlobalWorkdir(event)",
            "if (currentSession || !workdirInput)",
            'const nextWorkdir = String(event?.detail?.workdir || "").trim();',
            "workdirContextState = {",
            "scheduleWorkdirContextLoad();",
            'document.addEventListener("loopora:workdirchange", syncAlignmentDraftFromGlobalWorkdir)',
            "alignment-tutorial-handoff-manual-copy",
            "function renderTutorialHandoffManualCopy",
            "window.LooporaUI?.renderManualCopy?.(container, value",
            "alignment-tutorial-handoff-manual-copy-textarea",
            "The browser blocked automatic copy; copy the command below manually.",
            "The browser blocked automatic copy; copy the Fit Guide draft below manually.",
            "directPathWebStartBlockedMessage()",
            "taskGoalInput?.focus?.()",
            'fetchJson("/api/system/executor-readiness"',
            "function executorReadinessBlocksSubmission()",
            "executorReadinessState.blocking === true",
            'openTools("advanced")',
        )
    )
    assert 'data-testid="alignment-executor-readiness"' in template
    assert all(
        fragment in history_script
        for fragment in (
            'data-testid="alignment-history-delete"',
            "pendingDeleteId",
            'aria-pressed="${pendingDelete ? "true" : "false"}"',
            "render();",
            "deleteSession(session);",
            "empty.dataset.testid = testid",
            'testid: "alignment-history-empty"',
            "emptyStartHref",
            "emptyStartAction",
            'data-testid="alignment-history-empty-start-link"',
            'data-testid="alignment-history-empty-start-button"',
            "loadError",
            'testid: "alignment-history-load-error"',
            'data-testid="alignment-history-retry-button"',
            "Recent chats could not be loaded.",
            "load().catch(() => {})",
        )
    )
    assert "emptyStartHref: () => alignmentHistoryList?.dataset.historyEmptyStartHref" in manual_script
    assert "emptyStartAction: () => newSessionButton?.click()" in alignment_script
    assert "const statusLabel = (status" not in template
    assert 'fetch("/api/alignments/sessions?limit=30"' not in template


def test_alignment_session_restore_loads_event_history_to_tail_before_streaming() -> None:
    page_script = (ROOT / "src" / "loopora" / "static" / "pages" / "alignment.js").read_text(encoding="utf-8")

    assert "const ALIGNMENT_EVENT_PAGE_LIMIT = 5000;" in page_script
    assert "await loadSeedEvents(payload.session.id);" in page_script
    assert "openStream(payload.session.id);" in page_script
    assert 'params.set("after_id", String(afterId));' in page_script
    assert 'params.set("limit", String(ALIGNMENT_EVENT_PAGE_LIMIT));' in page_script
    assert "`/api/alignments/sessions/${encodeURIComponent(sessionId)}/events?${params}`" in page_script
    assert "if (!Array.isArray(events) || events.length === 0)" in page_script
    assert "if (events.length < ALIGNMENT_EVENT_PAGE_LIMIT || latestEventId <= afterId)" in page_script
    assert "afterId = latestEventId;" in page_script
    assert "let interruptedRecoveryCard = null;" in page_script
    assert "const ownedRecoveryCard = cancelledRecoveryCard || interruptedRecoveryCard;" in page_script
    assert 'classList.toggle("is-interrupted-recovery", status === "interrupted")' in page_script


def test_alignment_history_projector_preserves_session_status_semantics() -> None:
    _run_node(
        r"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync("src/loopora/static/pages/alignment_history.js", "utf8");
const context = {window: {}};
vm.createContext(context);
vm.runInContext(source, context);
const history = context.window.LooporaAlignmentHistory.createAlignmentHistory({
  localeText: (_zh, en) => en,
});

function assert(condition, message, value) {
  if (!condition) throw new Error(`${message}: ${JSON.stringify(value)}`);
}

assert(
  /agreement/i.test(history.statusLabel("waiting_user", "agreement_ready")),
  "agreement-ready waiting sessions should remain distinguishable",
  history.statusLabel("waiting_user", "agreement_ready")
);
assert(
  /review/i.test(history.statusLabel("waiting_user", "ready_review")),
  "ready-review waiting sessions should remain distinguishable",
  history.statusLabel("waiting_user", "ready_review")
);
assert(
  /repair/i.test(history.statusLabel("repairing")),
  "repairing sessions should retain repair semantics",
  history.statusLabel("repairing")
);
assert(
  /stopped/i.test(history.statusLabel("cancelled")) && /stopped/i.test(history.statusLabel("stopped")),
  "user cancellation and stopped runs should not render as failures",
  [history.statusLabel("cancelled"), history.statusLabel("stopped")]
);
assert(
  /interrupted/i.test(history.statusLabel("interrupted")),
  "orphaned planning workers should not remain visibly active or collapse into generic failure",
  history.statusLabel("interrupted")
);
"""
    )


def test_alignment_sync_failure_renders_structured_recovery_panel() -> None:
    page_script = (ROOT / "src" / "loopora" / "static" / "pages" / "alignment.js").read_text(encoding="utf-8")

    assert all(
        fragment in page_script
        for fragment in (
            'testid: "alignment-sync-recovery"',
            "Fix the Plan File before syncing again",
            "renderAlignmentRecovery(payload, {",
            "if (!payload.ok) {",
            "clearRecoveryPanel();",
        )
    )


def test_alignment_preview_failure_renders_structured_recovery_panel() -> None:
    page_script = (ROOT / "src" / "loopora" / "static" / "pages" / "alignment.js").read_text(encoding="utf-8")

    assert all(
        fragment in page_script
        for fragment in (
            'testid: "alignment-preview-recovery"',
            "Fix the Plan File before previewing again",
            "renderAlignmentRecovery(payload, {",
            "renderBundleLoadError(payload.error",
        )
    )


def test_alignment_endpoint_recovery_actions_are_executable_from_browser() -> None:
    page_script = (ROOT / "src" / "loopora" / "static" / "pages" / "alignment.js").read_text(encoding="utf-8")

    assert all(
        fragment in page_script
        for fragment in (
            "actionControlHtml: alignmentRecoveryActionControlHtml",
            "function alignmentRecoveryActionControlHtml(action)",
            '"review_alignment_source_context"',
            '"retry_alignment_session_create"',
            '"sync_alignment_bundle"',
            '"retry_alignment_bundle_preview"',
            '"retry_alignment_import"',
            'data-alignment-recovery-action="${escapeHtml(actionKind)}"',
            "function bindAlignmentRecoveryActions()",
            'if (actionKind === "review_alignment_source_context")',
            "await reviewAlignmentSourceContextFromRecovery();",
            'else if (actionKind === "retry_alignment_session_create")',
            "retryAlignmentSessionCreateFromRecovery();",
            'else if (actionKind === "sync_alignment_bundle")',
            "await syncReadyBundle();",
            'else if (actionKind === "retry_alignment_bundle_preview")',
            "await loadReadyBundle({reveal: true});",
            'else if (actionKind === "retry_alignment_import")',
            "await importReadyBundle({startImmediately: true});",
            "function alignmentRecoveryActionErrorOptions(actionKind)",
            'testid: "alignment-session-start-recovery"',
            "function reviewAlignmentSourceContextFromRecovery()",
            "await loadWorkdirContext({force: true});",
            "function retryAlignmentSessionCreateFromRecovery()",
            "startForm.requestSubmit();",
            "function importReadyBundle({startImmediately})",
            "body: JSON.stringify({start_immediately: startImmediately})",
        )
    )


def test_alignment_stale_session_links_degrade_to_startable_chat() -> None:
    page_script = (ROOT / "src" / "loopora" / "static" / "pages" / "alignment.js").read_text(encoding="utf-8")

    assert all(
        fragment in page_script
        for fragment in (
            "function setSessionIdInUrl(sessionId)",
            'url.searchParams.set("alignment_session_id", sessionId)',
            'url.searchParams.delete("alignment_workdir")',
            'url.searchParams.delete("workdir")',
            'const value = workdirInput?.value.trim() || "";',
            "window.LooporaUI.syncWorkdirContext(value, {syncUrl})",
            "function clearSessionIdFromUrl({preserveCurrentWorkdir = false} = {})",
            'url.searchParams.delete("alignment_session_id")',
            'newSessionButton.addEventListener("click", async ()',
            "function activeSessionBlocksNavigation(message)",
            "await refreshSession().catch(() => currentSession)",
            "stop the current conversation before starting a new one",
            "clearSessionIdFromUrl({preserveCurrentWorkdir: true})",
            'window.history.replaceState(null, "", nextUrl)',
            'const hasUrlSession = query.has("alignment_session_id")',
            'const hasExplicitWorkdirContext = query.has("workdir") || query.has("alignment_workdir")',
            "if (!sessionId && !hasExplicitWorkdirContext)",
            "resetToEmptyConversation();",
            "forgetSession();",
            "{autoHide: false}",
            "Same-Agent run",
            "same-Agent handoff",
            "同一 Agent 运行",
            "同一 Agent 交接",
            "data-alignment-agent-command-manual-copy",
            "function renderAgentLaunchManualCopy",
            "alignment-agent-command-manual-copy-textarea",
            "alignment-run-command-manual-copy-textarea",
            "The browser blocked automatic copy; copy the Agent command below manually.",
            "The browser blocked automatic copy; copy the /loopora-run command at the bottom of the page manually.",
        )
    )
    assert all(fragment not in page_script for fragment in ("Agent-first run", "Agent-first handoff", "Agent-first 运行", "Agent-first 交接"))


def test_agreement_ready_uses_structured_review_and_review_start_scroll_anchor() -> None:
    page_script = (ROOT / "src" / "loopora" / "static" / "pages" / "alignment.js").read_text(encoding="utf-8")

    assert all(
        fragment in page_script
        for fragment in (
            "function renderWorkingAgreementReview",
            "function workingAgreementSurfaceMode",
            "function workingAgreementPhaseCopy",
            "function entryCarriesAgreementDecision",
            'data-testid="alignment-agreement-summary"',
            'data-testid="alignment-agreement-key-judgments"',
            'data-testid="alignment-agreement-details"',
            '"alignment-agreement-handoff"',
            'data-agreement-field="${escapeHtml(key)}"',
            "if (canChoose)",
            "agreementSurfaceMode !== \"compiling\"",
            "scrollRegion.scrollTop + reviewRect.top - scrollRect.top - 8",
        )
    )
    for judgment in (
        "success_surface",
        "fake_done_risks",
        "evidence_preferences",
        "judgment_tradeoffs",
        "task_scope",
        "execution_strategy",
        "local_governance",
        "workflow_shape",
    ):
        assert f'"{judgment}"' in page_script


def test_agreement_review_keeps_primary_judgments_and_choices_responsive() -> None:
    stylesheet = (ROOT / "src" / "loopora" / "static" / "pages" / "alignment.css").read_text(encoding="utf-8")

    assert all(
        fragment in stylesheet
        for fragment in (
            ".bundle-chat-main .alignment-message--agreement",
            ".alignment-agreement-primary",
            ".alignment-agreement-review .alignment-decision-options",
            ".alignment-agreement-review.is-compiling",
            ".alignment-agreement-review.is-repair",
            ".alignment-agreement-details > dl",
            "grid-template-columns: repeat(2, minmax(0, 1fr));",
        )
    )


def test_ready_review_separates_saving_from_starting_a_web_run() -> None:
    template = (ROOT / "src" / "loopora" / "templates" / "new_loop.html").read_text(encoding="utf-8")
    page_script = (ROOT / "src" / "loopora" / "static" / "pages" / "alignment.js").read_text(encoding="utf-8")
    stylesheet = (ROOT / "src" / "loopora" / "static" / "pages" / "alignment.css").read_text(encoding="utf-8")

    assert all(
        fragment in template
        for fragment in (
            'data-testid="alignment-import-save-button"',
            'data-testid="alignment-import-run-button"',
            'data-testid="alignment-ready-actions"',
            'data-testid="alignment-ready-save-action"',
            'data-testid="alignment-ready-run-action"',
            'data-preview-tab="review"',
            'data-preview-panel="review"',
            'data-preview-panel="workflow"',
            "READY review",
            "before committing",
            "Does not start a Run",
            "Starts the first Web Run immediately",
        )
    )
    assert all(
        fragment in page_script
        for fragment in (
            'const importSaveButton = document.getElementById("alignment-import-save-button")',
            "function updateReadyReviewGateActions()",
            "function judgmentReviewStatus",
            "const allowSaveOnly = allowReadyRun && !agentLaunch",
            "await importReadyBundle({startImmediately: false})",
            "await importReadyBundle({startImmediately: true})",
            "body: JSON.stringify({start_immediately: startImmediately})",
            "review and choose the next step",
            "Save the Loop or run it now.",
            "function preparePreviewNavigation",
            "function revealReadyPreviewStart",
            'defaultTab: "review"',
            'setBilingualText(readyRunTitle, "回到同一 Agent", "Continue in the same Agent")',
            'shell?.classList.toggle("is-ready-review", reviewingReady)',
            'selectPreviewTab(previewTabs[nextIndex].dataset.previewTab || "review", {focus: true})',
        )
    )
    assert 'readyPreview.scrollIntoView({block: "nearest"' not in page_script
    assert all(
        fragment in stylesheet
        for fragment in (
            ".alignment-ready-actions",
            ".alignment-ready-action",
            '.bundle-chat-shell.is-ready-review:not(.is-ready-revision) .alignment-composer-box',
            '.bundle-chat-shell.is-ready-review:not(.is-ready-revision) .bundle-chat-sidebar',
            "grid-template-columns: repeat(2, minmax(0, 1fr));",
        )
    )

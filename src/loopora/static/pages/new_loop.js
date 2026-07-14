document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("new-loop-form");
  if (!form || !window.LooporaUI) {
    return;
  }

  const workdirInput = document.getElementById("workdir-input");
  const bundleImportForm = document.getElementById("bundle-import-form-fields");
  const specPathInput = document.getElementById("spec-path-input");
  const orchestrationInput = document.getElementById("orchestration-id-input");
  const orchestrationSummary = document.getElementById("orchestration-summary");
  const completionModeInput = document.getElementById("completion-mode-input");
  const completionModeField = document.getElementById("completion-mode-field");
  const completionModeNote = document.getElementById("completion-mode-note");
  const manualExecutorKindInput = document.getElementById("manual-executor-kind-input");
  const manualExecutorModeInputs = Array.from(form.querySelectorAll("input[name='executor_mode']"));
  const manualModeChips = Array.from(form.querySelectorAll("[data-manual-mode-choice]"));
  const manualModeNote = document.getElementById("manual-executor-mode-note");
  const manualPresetCard = document.getElementById("manual-preset-card");
  const manualCommandCard = document.getElementById("manual-command-card");
  const manualPresetState = document.getElementById("manual-preset-state");
  const manualCommandState = document.getElementById("manual-command-state");
  const manualPresetBody = document.getElementById("manual-preset-body");
  const manualPresetEmpty = document.getElementById("manual-preset-empty");
  const manualModelInput = document.getElementById("manual-model-input");
  const manualModelNote = document.getElementById("manual-model-note");
  const manualReasoningField = document.getElementById("manual-reasoning-field");
  const manualReasoningInput = document.getElementById("manual-reasoning-effort-input");
  const manualReasoningNote = document.getElementById("manual-reasoning-note");
  const manualCommandCliInput = document.getElementById("manual-command-cli-input");
  const manualCommandCliNote = document.getElementById("manual-command-cli-note");
  const manualCommandArgsInput = document.getElementById("manual-command-args-input");
  const triggerWindowField = document.getElementById("trigger-window-field");
  const regressionWindowField = document.getElementById("regression-window-field");
  const manualDirectHandoffBridge = document.getElementById("manual-direct-handoff-bridge");
  const browseWorkdirButton = document.getElementById("browse-workdir");
  const browseSpecButton = document.getElementById("browse-spec");
  const editSpecButton = document.getElementById("edit-spec");
  const createSpecTemplateButton = document.getElementById("create-spec-template");
  const saveLoopButton = document.getElementById("save-loop-button");
  const bundleImportSubmitButton = document.getElementById("bundle-import-submit-button");
  const bundlePreviewImportButton = document.getElementById("bundle-preview-import-button");
  const formError = document.getElementById("form-error");
  const bundleImportError = document.getElementById("bundle-import-error");
  const manualRecoveryPanel = document.getElementById("manual-recovery-panel");
  const draftStatus = document.getElementById("draft-status");
  const draftActions = document.getElementById("draft-actions");
  const clearDraftButton = document.getElementById("clear-draft-button");
  const specValidation = document.getElementById("spec-validation");
  const specPreviewModal = document.getElementById("spec-preview-modal");
  const specPreviewStatus = document.getElementById("spec-preview-status");
  const specPreviewPath = document.getElementById("spec-preview-path");
  const specPreviewContent = document.getElementById("spec-preview-content");
  const specPreviewToggleButton = document.getElementById("toggle-spec-preview");
  const specEditorInput = document.getElementById("spec-editor-input");
  const specEditorWorkbenchShell = document.querySelector(".spec-preview-workbench");
  const specEditorSourcePanel = document.getElementById("spec-editor-source-panel");
  const specEditorPreviewPanel = document.getElementById("spec-editor-preview-panel");
  const specEditorRecoveryPanel = document.getElementById("spec-editor-recovery-panel");
  const specEditorSaveButton = document.getElementById("save-spec-document");
  const specEditorValidationPill = document.getElementById("spec-editor-validation-pill");
  const specEditorSaveState = document.getElementById("spec-editor-save-state");
  const executorProfiles = JSON.parse(document.getElementById("executor-profiles-json")?.textContent || "[]");
  const orchestrations = JSON.parse(document.getElementById("orchestrations-json")?.textContent || "[]");
  const pristineLoopForm = JSON.parse(document.getElementById("pristine-loop-form-json")?.textContent || "{}");
  const workdirQuickPickButtons = Array.from(document.querySelectorAll("[data-fill-workdir]"));
  const alignmentHistoryList = document.getElementById("alignment-history-list");
  const composeModeLinks = Array.from(document.querySelectorAll("[data-compose-mode-link]"));
  const newConversationControls = Array.from(document.querySelectorAll('[data-compose-action-kind="new_web_conversation"]'));

  const DRAFT_STORAGE_KEY = "loopora:new-loop-draft:v2";
  const FIT_HANDOFF_STORAGE_KEY = "loopora:tutorial-fit-handoff:v1";
  let latestSpecValidationRequest = 0;
  let lastSpecPreviewTrigger = null;
  let specEditorWorkbench = null;
  let specEditorLoadedPath = "";
  let specEditorSavedText = "";
  let specEditorLastValidation = null;
  let specPreviewVisible = false;
  const manualCommandDrafts = new Map();
  let lastManualExecutorKind = manualExecutorKindInput?.value || "codex";

  function localeText(zh, en) {
    return window.LooporaUI.pickText({zh, en});
  }

  function syncManualWorkdirContext() {
    const value = workdirInput?.value.trim() || "";
    if (!window.LooporaUI.syncWorkdirContext) {
      return;
    }
    window.LooporaUI.syncWorkdirContext(value, {syncUrl: true, urlParam: "workdir"});
  }

  function syncManualDraftFromGlobalWorkdir(event) {
    if (!workdirInput) {
      return;
    }
    const nextWorkdir = String(event?.detail?.workdir || "").trim();
    if (workdirInput.value.trim() !== nextWorkdir) {
      workdirInput.value = nextWorkdir;
      saveDraft();
    }
    renderManualDirectHandoffGate();
  }

  function manualRunWorkdir(payload = {}) {
    return String(workdirInput?.value || payload?.loop?.workdir || payload?.run?.workdir || "").trim();
  }

  const alignmentHistoryController = window.LooporaAlignmentHistory?.createAlignmentHistory({
    historyList: alignmentHistoryList,
    localeText,
    fetchSessions: async () => {
      const response = await fetch("/api/alignments/sessions?limit=30", {headers: {Accept: "application/json"}});
      return response.ok ? response.json() : {sessions: []};
    },
    emptyStartHref: () => alignmentHistoryList?.dataset.historyEmptyStartHref || "/loops/new/bundle",
    openHref: (session) => `/loops/new/bundle?alignment_session_id=${encodeURIComponent(session.id)}`,
  });

  function showStatus(element, message, kind = "") {
    if (element === formError) {
      clearManualRecovery();
    }
    if (!message) {
      element.hidden = true;
      element.textContent = "";
      element.className = "field-status";
      return;
    }
    element.hidden = false;
    element.textContent = message;
    element.className = `field-status${kind ? ` is-${kind}` : ""}`;
  }

  function errorMessage(error, fallbackMessage) {
    if (error && typeof error === "object" && "message" in error && error.message) {
      return String(error.message);
    }
    return fallbackMessage;
  }

  function isManualRecoveryPayload(payload) {
    return Boolean(
      payload &&
      typeof payload === "object" &&
      payload.loop_recovery &&
      Array.isArray(payload.next_actions),
    );
  }

  function runStartFailureRedirect(payload) {
    if (payload?.run_recovery !== "retry_run_start") {
      return "";
    }
    const workdir = manualRunWorkdir(payload);
    const directRedirect = window.LooporaUI.safeLocalRecoveryUrl(payload?.redirect_url);
    if (directRedirect) {
      return window.LooporaUI.workdirContextHref(directRedirect, workdir);
    }
    const runId = String(payload?.run?.id || "").trim();
    if (!runId) {
      return "";
    }
    const url = new URL(
      window.LooporaUI.workdirContextHref(`/runs/${encodeURIComponent(runId)}`, workdir),
      window.location.origin,
    );
    const error = String(payload?.run_start_error || payload?.error || "").trim();
    if (error) {
      url.searchParams.set("run_action_error", error);
    }
    return `${url.pathname}${url.search}${url.hash}`;
  }

  function clearManualRecovery() {
    if (manualRecoveryPanel) {
      manualRecoveryPanel.hidden = true;
      manualRecoveryPanel.innerHTML = "";
    }
    window.LooporaUI.clearRecoveryCommandCopyStatus(manualRecoveryPanel);
  }

  function manualLoopRecoveryPayload(payload) {
    const actions = Array.isArray(payload?.next_actions) ? payload.next_actions : [];
    return {
      ...payload,
      next_actions: actions.map((action) => {
        const kind = String(action?.kind || "").trim();
        if (kind !== "retry_web_compose") {
          return action;
        }
        return {
          ...action,
          form_id: "new-loop-form",
          form_method: "POST",
        };
      }),
    };
  }

  function renderManualLoopRecovery(payload) {
    const message = String(payload.error || payload.summary || localeText("创建 Loop 前需要先修复输入。", "Fix the inputs before creating the loop."));
    formError.hidden = false;
    formError.textContent = message;
    formError.className = "field-status is-error";

    if (!manualRecoveryPanel || !Array.isArray(payload.next_actions) || !payload.next_actions.length) {
      clearManualRecovery();
      return;
    }
    const recoveryPayload = manualLoopRecoveryPayload(payload);
    manualRecoveryPanel.hidden = false;
    manualRecoveryPanel.innerHTML = window.LooporaUI.recoveryPanelHtml(recoveryPayload, {
      testid: "manual-loop-recovery",
      itemsTestid: "manual-loop-recovery-actions",
      title: localeText("创建被可恢复条件阻塞", "Creation is blocked by recoverable setup"),
      summary: payload.summary || message,
    });
    window.LooporaUI.bindRecoveryCommandCopy();
  }

  function specValidationFeedback(validation) {
    if (!validation || typeof validation !== "object") {
      return {
        message: localeText("Loop 契约状态未知。", "Spec status is unknown."),
        kind: "warning",
        pill: localeText("待检查", "Pending"),
      };
    }
    if (validation.state === "dirty") {
      return {
        message: validation.error || localeText("编辑器里有未保存的改动。", "There are unsaved editor changes."),
        kind: "warning",
        pill: localeText("未保存", "Unsaved"),
      };
    }
    if (validation.state === "detached") {
      return {
        message: validation.error || localeText("当前编辑器还没有绑定新的契约文件。", "The editor is not bound to the new spec file yet."),
        kind: "warning",
        pill: localeText("需重载", "Reload"),
      };
    }
    if (validation.ok) {
      const detail = validation.check_mode === "auto_generated"
        ? localeText(
          "当前内容还没有固定完成条件，运行开始时会自动生成并冻结检查项。",
          "This spec does not lock Done When yet. Loopora will generate and freeze checks at run start.",
        )
        : localeText(
          `当前内容识别到 ${validation.check_count} 条完成条件。`,
          `This spec contains ${validation.check_count} Done When outcome(s).`,
        );
      return {
        message: `${localeText("Loop 契约校验通过。", "Spec is valid.")} ${detail}`,
        kind: "success",
        pill: validation.check_mode === "auto_generated"
          ? localeText("自动生成", "Auto-generated")
          : localeText("校验通过", "Valid"),
      };
    }
    return {
      message: validation.error || localeText("Loop 契约还没有满足最小结构。", "The spec does not satisfy the minimum structure yet."),
      kind: "error",
      pill: localeText("需修正", "Needs fixes"),
    };
  }

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function compactText(value) {
    return String(value || "").trim().replace(/\s+/g, " ");
  }

  function readTutorialDirectHandoff() {
    try {
      const raw = window.sessionStorage?.getItem(FIT_HANDOFF_STORAGE_KEY) || "";
      if (!raw) {
        return null;
      }
      const payload = JSON.parse(raw);
      if (payload?.source !== "tutorial_fit_review") {
        return null;
      }
      if (!window.LooporaUI.tutorialFitPrefersDirectPath(payload)) {
        return null;
      }
      const inputs = payload?.inputs && typeof payload.inputs === "object" ? payload.inputs : {};
      return {
        command: compactText(payload?.direct_decision_command || payload?.review_completion_command),
        sourceWorkdir: compactText(payload?.source_workdir || payload?.workdir),
        directTask: compactText(inputs.task),
        directReason: compactText(inputs.direct_path_check),
      };
    } catch (_) {
      return null;
    }
  }

  function manualDirectHandoffMatchesTarget(handoff) {
    const targetWorkdir = workdirInput?.value.trim() || "";
    return window.LooporaUI.sameWorkdir(handoff?.sourceWorkdir, targetWorkdir, {
      allowEmptyLeft: !targetWorkdir,
    });
  }

  function setManualDirectPathLinkEnabled(link, enabled) {
    window.LooporaUI.setNavigationControlBlocked(link, !enabled, {
      markerDataset: "directPathBlocked",
      baseHrefDataset: "directPathBaseHref",
      disabledHrefDataset: "directPathDisabledHref",
    });
  }

  function setManualCreationBlocked(blocked) {
    [saveLoopButton, bundleImportSubmitButton, bundlePreviewImportButton].forEach((button) => {
      if (!button) {
        return;
      }
      if (blocked) {
        button.dataset.directPathDisabled = "true";
        button.disabled = Boolean(blocked);
        button.setAttribute("aria-disabled", blocked ? "true" : "false");
      } else if (button.dataset.directPathDisabled === "true") {
        button.disabled = false;
        button.setAttribute("aria-disabled", "false");
        delete button.dataset.directPathDisabled;
      }
    });
    [form, bundleImportForm].forEach((targetForm) => {
      if (targetForm) {
        targetForm.dataset.directPathBlocked = blocked ? "true" : "false";
      }
    });
    [...composeModeLinks, ...newConversationControls].forEach((link) => {
      setManualDirectPathLinkEnabled(link, !blocked);
    });
  }

  function clearTutorialDirectHandoff() {
    try {
      window.sessionStorage?.removeItem(FIT_HANDOFF_STORAGE_KEY);
    } catch (_) {
      // Best effort only.
    }
    renderManualDirectHandoffGate();
    showStatus(formError, "");
    if (bundleImportError) {
      showStatus(bundleImportError, "");
    }
    workdirInput?.focus?.();
  }

  function useManualDirectHandoffSource(sourceWorkdir) {
    const value = compactText(sourceWorkdir);
    if (!value || !workdirInput) {
      return;
    }
    workdirInput.value = value;
    syncManualWorkdirContext();
    saveDraft();
    renderManualDirectHandoffGate();
    showStatus(formError, localeText("已切回直接路径决定的来源项目。", "Switched to the direct-path decision source project."), "success");
  }

  function renderManualDirectHandoffGate() {
    const handoff = readTutorialDirectHandoff();
    const hasWorkdirMismatch = Boolean(handoff && !manualDirectHandoffMatchesTarget(handoff));
    const blocksManualCreation = Boolean(handoff && !hasWorkdirMismatch);
    setManualCreationBlocked(blocksManualCreation);
    if (!manualDirectHandoffBridge) {
      return blocksManualCreation;
    }
    if (!handoff) {
      manualDirectHandoffBridge.hidden = true;
      manualDirectHandoffBridge.innerHTML = "";
      return false;
    }
    const currentWorkdir = workdirInput?.value.trim() || "";
    const sourceLine = handoff.sourceWorkdir
      ? `<span>${escapeHtml(localeText("来源目录", "Source"))}: ${escapeHtml(handoff.sourceWorkdir)}</span>`
      : "";
    const currentLine = hasWorkdirMismatch && currentWorkdir
      ? `<span>${escapeHtml(localeText("当前目录", "Current"))}: ${escapeHtml(currentWorkdir)}</span>`
      : "";
    const taskLine = handoff.directTask
      ? `<span>${escapeHtml(localeText("任务目标", "Goal"))}: ${escapeHtml(handoff.directTask)}</span>`
      : "";
    const reasonLine = handoff.directReason
      ? `<span>${escapeHtml(localeText("直接路径理由", "Direct-path reason"))}: ${escapeHtml(handoff.directReason)}</span>`
      : "";
    const useSourceButton = hasWorkdirMismatch && handoff.sourceWorkdir
      ? `
        <button class="secondary-button" type="button" data-manual-direct-handoff-use-source data-testid="manual-direct-handoff-use-source">
          <span>${escapeHtml(localeText("使用来源项目", "Use source project"))}</span>
        </button>
      `
      : "";
    const copyButton = handoff.command
      ? `
        <button class="secondary-button" type="button" data-manual-direct-handoff-copy data-testid="manual-direct-handoff-copy">
          <span>${escapeHtml(localeText("复制直接路径命令", "Copy direct-path command"))}</span>
        </button>
      `
      : "";
    manualDirectHandoffBridge.hidden = false;
    manualDirectHandoffBridge.innerHTML = `
      <div class="alignment-source-context-copy">
        <span class="alignment-source-context-kicker">${escapeHtml(localeText("Fit Guide 判断", "Fit Guide judgment"))}</span>
        <h3>${escapeHtml(hasWorkdirMismatch ? localeText("直接路径决定属于另一个项目", "Direct-path decision belongs to another project") : localeText("已选择直接路径", "Direct path selected"))}</h3>
        <p>${escapeHtml(localeText(
          hasWorkdirMismatch
            ? "这份直接路径决定来自另一个目标项目；当前项目的导入和手动创建不会被停用。你可以切回来源项目、复制直接路径命令，或清除决定后重新判断。"
            : "这份浏览器会话记录的是不用 Loopora 的决定。导入 Plan File 和手动创建已停用；请走直接 Agent、硬性检查，或清除这份决定后重新判断。",
          hasWorkdirMismatch
            ? "This direct-path decision belongs to another target project; import and manual creation for the current project are not disabled. Use the source project, copy the direct-path command, or clear the decision and review again."
            : "This browser session records that Loopora is not needed. Plan File import and manual creation are disabled; use the direct Agent or hard-check path, or clear this decision and review again.",
        ))}</p>
        <div class="alignment-source-context-metrics" data-testid="manual-direct-handoff-meta">
          ${sourceLine}
          ${currentLine}
          ${taskLine}
          ${reasonLine}
        </div>
      </div>
      <div class="alignment-agent-review-actions">
        ${useSourceButton}
        ${copyButton}
        <button class="ghost-button" type="button" data-manual-direct-handoff-clear data-testid="manual-direct-handoff-clear">
          <span>${escapeHtml(localeText("清除决定", "Clear decision"))}</span>
        </button>
      </div>
      <div class="agent-readiness-public-report" data-manual-direct-handoff-manual-copy data-testid="manual-direct-handoff-manual-copy" hidden></div>
    `;
    manualDirectHandoffBridge.querySelector("[data-manual-direct-handoff-copy]")?.addEventListener("click", async () => {
      renderManualDirectHandoffCommand("");
      try {
        await window.LooporaUI.writeTextToClipboard(handoff.command);
        showStatus(formError, localeText("直接路径命令已复制。", "Direct-path command copied."), "success");
      } catch (_) {
        renderManualDirectHandoffCommand(handoff.command);
        showStatus(
          formError,
          localeText("浏览器未允许自动复制；请手动复制下面的直接路径命令。", "The browser blocked automatic copy; copy the direct-path command below manually."),
          "warning",
        );
      }
    });
    manualDirectHandoffBridge.querySelector("[data-manual-direct-handoff-clear]")?.addEventListener("click", clearTutorialDirectHandoff);
    manualDirectHandoffBridge.querySelector("[data-manual-direct-handoff-use-source]")?.addEventListener("click", () => {
      useManualDirectHandoffSource(handoff.sourceWorkdir);
    });
    return blocksManualCreation;
  }

  function renderManualDirectHandoffCommand(command) {
    const container = manualDirectHandoffBridge?.querySelector?.("[data-manual-direct-handoff-manual-copy]");
    window.LooporaUI?.renderManualCopy?.(container, command, {
      label: localeText("手动复制直接路径命令", "Manual direct-path command copy"),
      textareaId: "manual-direct-handoff-command-textarea",
    });
  }

  function directHandoffBlocksManualCreation(errorTarget) {
    if (!renderManualDirectHandoffGate()) {
      return false;
    }
    showStatus(
      errorTarget || formError,
      localeText(
        "已选择直接路径，不能导入或手动创建 Loop。请复制直接路径命令，或清除这份决定后重新判断。",
        "Direct path is selected, so importing or manually creating a Loop is disabled. Copy the direct-path command, or clear this decision and review again.",
      ),
      "error",
    );
    manualDirectHandoffBridge?.scrollIntoView({block: "start", behavior: "smooth"});
    return true;
  }

  function setButtonBusy(button, isBusy) {
    if (!button) {
      return;
    }
    button.disabled = isBusy;
    button.setAttribute("aria-busy", String(isBusy));
  }

  function loadDraft() {
    try {
      const raw = window.localStorage.getItem(DRAFT_STORAGE_KEY);
      if (!raw) {
        return null;
      }
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : null;
    } catch (_) {
      return null;
    }
  }

  function normalizeDraftValue(key, value) {
    if (key === "start_immediately") {
      if (typeof value === "boolean") {
        return value ? "1" : "";
      }
      const normalized = String(value || "").trim().toLowerCase();
      return normalized === "1" || normalized === "true" ? "1" : "";
    }
    return String(value ?? "");
  }

  function pruneDraft(rawDraft) {
    if (!rawDraft || typeof rawDraft !== "object") {
      return {};
    }
    const draft = {};
    Object.entries(rawDraft).forEach(([key, value]) => {
      const normalizedValue = normalizeDraftValue(key, value);
      const pristineValue = normalizeDraftValue(key, pristineLoopForm[key]);
      if (normalizedValue !== pristineValue) {
        draft[key] = normalizedValue;
      }
    });
    return draft;
  }

  function updateDraftUI() {
    const draft = loadDraft();
    const visible = Object.keys(pruneDraft(draft)).length > 0;
    if (draftActions) {
      draftActions.hidden = !visible;
    }
  }

  function collectDraft() {
    const formData = new FormData(form);
    const draft = Object.fromEntries(
      Array.from(formData.entries()).map(([key, value]) => [key, typeof value === "string" ? value : String(value)]),
    );
    draft.start_immediately = form.querySelector('input[name="start_immediately"]')?.checked ? "1" : "";
    draft.executor_mode = manualCommandMode() ? "command" : "preset";
    if (draft.executor_mode !== "command") {
      draft.command_cli = "";
      draft.command_args_text = "";
    }
    return draft;
  }

  function saveDraft() {
    const draft = pruneDraft(collectDraft());
    try {
      if (Object.keys(draft).length === 0) {
        window.localStorage.removeItem(DRAFT_STORAGE_KEY);
      } else {
        window.localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
      }
    } catch (_) {
      return;
    }
    updateDraftUI();
  }

  function clearDraft(options = {}) {
    try {
      window.localStorage.removeItem(DRAFT_STORAGE_KEY);
    } catch (_) {
      // Ignore storage cleanup issues.
    }
    updateDraftUI();
    if (options.announce) {
      showStatus(
        draftStatus,
        localeText("本地草稿已清空，当前表单内容保持不变。", "Saved browser draft cleared. The current form stays as-is."),
        "success",
      );
    } else {
      showStatus(draftStatus, "");
    }
  }

  function applyDraft(draft) {
    const normalizedDraft = pruneDraft(draft);
    if (!Object.keys(normalizedDraft).length) {
      return false;
    }
    Array.from(form.elements).forEach((element) => {
      if (!(element instanceof HTMLElement)) {
        return;
      }
      const name = element.getAttribute("name");
      if (!name || !(name in normalizedDraft)) {
        return;
      }
      if (element instanceof HTMLInputElement) {
        if (element.type === "checkbox") {
          element.checked = String(normalizedDraft[name] || "").trim().toLowerCase() === "1";
          return;
        }
        if (element.type === "radio") {
          element.checked = element.value === String(normalizedDraft[name] || "");
          return;
        }
      }
      if ("value" in element) {
        element.value = String(normalizedDraft[name] ?? "");
      }
    });
    return true;
  }

  function restoreDraftIfAllowed() {
    updateDraftUI();
    if (form.dataset.restoreDraft !== "true") {
      return false;
    }
    const draft = loadDraft();
    if (!applyDraft(draft)) {
      return false;
    }
    showStatus(
      draftStatus,
      localeText("已恢复这台浏览器里上次没提交完的 Loop 草稿。", "Restored the unfinished loop draft saved in this browser."),
      "success",
    );
    return true;
  }

  async function fetchJson(url, options = {}) {
    try {
      const response = await fetch(url, options);
      const payload = await response.json().catch(() => ({}));
      return {response, payload, error: null};
    } catch (error) {
      return {response: null, payload: {}, error};
    }
  }

  async function runAction(button, action, options) {
    const {errorTarget, fallbackMessage} = options;
    setButtonBusy(button, true);
    try {
      await action();
    } catch (error) {
      showStatus(errorTarget, errorMessage(error, fallbackMessage), "error");
    } finally {
      setButtonBusy(button, false);
    }
  }

  function currentOrchestration() {
    return orchestrations.find((item) => item.id === orchestrationInput.value) || orchestrations[0] || null;
  }

  function strategySource(orchestration) {
    const source = orchestration?.strategy_source || orchestration?.workflow_json || {};
    return source && typeof source === "object" ? source : {};
  }

  function strategyRoles(orchestration) {
    const source = strategySource(orchestration);
    return Array.isArray(source.roles) ? source.roles : [];
  }

  function strategySteps(orchestration) {
    const source = strategySource(orchestration);
    return Array.isArray(source.steps) ? source.steps : [];
  }

  function strategyParallelGroupCount(orchestration) {
    const groups = new Map();
    strategySteps(orchestration).forEach((step) => {
      const group = String(step?.parallel_group || "").trim();
      if (!group) {
        return;
      }
      groups.set(group, (groups.get(group) || 0) + 1);
    });
    return Array.from(groups.values()).filter((count) => count >= 2).length;
  }

  function strategyHasRole(orchestration, archetype) {
    return strategyRoles(orchestration).some((role) => String(role?.archetype || "") === archetype);
  }

  function executorLabel(kind) {
    return executorProfiles.find((profile) => profile.key === kind)?.label || kind || "-";
  }

  function executorProfile(kind) {
    return executorProfiles.find((profile) => profile.key === kind) || executorProfiles[0] || {};
  }

  function defaultManualCommandArgsText(profile) {
    return Array.isArray(profile?.command_args_template) ? profile.command_args_template.join("\n") : "";
  }

  function selectedManualExecutorMode() {
    const selected = manualExecutorModeInputs.find((input) => input.checked);
    return String(selected?.value || "preset") === "command" ? "command" : "preset";
  }

  function setManualExecutorMode(nextMode) {
    const resolvedMode = String(nextMode || "preset") === "command" ? "command" : "preset";
    manualExecutorModeInputs.forEach((input) => {
      input.checked = input.value === resolvedMode;
    });
  }

  function manualExecutionProfile() {
    return executorProfile(manualExecutorKindInput?.value || "codex");
  }

  function manualCommandMode() {
    const profile = manualExecutionProfile();
    return selectedManualExecutorMode() === "command" || Boolean(profile.command_only);
  }

  function saveManualCommandDraft(profileKey = lastManualExecutorKind) {
    if (!profileKey || !manualCommandCliInput || !manualCommandArgsInput) {
      return;
    }
    manualCommandDrafts.set(profileKey, {
      cli: manualCommandCliInput.value || "",
      args: manualCommandArgsInput.value || "",
    });
  }

  function loadManualCommandDraft(profile) {
    if (!profile || !manualCommandCliInput || !manualCommandArgsInput) {
      return;
    }
    const saved = manualCommandDrafts.get(profile.key);
    if (saved) {
      manualCommandCliInput.value = saved.cli || profile.cli_name || "";
      manualCommandArgsInput.value = saved.args || defaultManualCommandArgsText(profile);
      return;
    }
    if (!manualCommandCliInput.value.trim() || manualCommandCliInput.dataset.autofilled === "true") {
      manualCommandCliInput.value = profile.cli_name || "";
      manualCommandCliInput.dataset.autofilled = "true";
    }
    if (!manualCommandArgsInput.value.trim() || manualCommandArgsInput.dataset.autofilled === "true") {
      manualCommandArgsInput.value = defaultManualCommandArgsText(profile);
      manualCommandArgsInput.dataset.autofilled = "true";
    }
  }

  function syncManualModeChips(profile, commandMode) {
    manualModeChips.forEach((chip) => {
      const mode = chip.dataset.manualModeChoice || "";
      const input = chip.querySelector("input[name='executor_mode']");
      const active = commandMode ? mode === "command" : mode === "preset";
      chip.classList.toggle("is-active", active);
      if (mode === "preset") {
        const disabled = Boolean(profile.command_only);
        if (input) {
          input.disabled = disabled;
        }
        chip.classList.toggle("is-disabled", disabled);
        chip.setAttribute("aria-disabled", String(disabled));
      } else {
        chip.classList.remove("is-disabled");
        chip.removeAttribute("aria-disabled");
      }
    });
  }

  function syncManualExecutionControls(options = {}) {
    if (!manualExecutorKindInput) {
      return;
    }
    const profile = manualExecutionProfile();
    if (profile.command_only && selectedManualExecutorMode() !== "command") {
      setManualExecutorMode("command");
    }
    const commandMode = manualCommandMode();
    const preserveUserModel = options.preserveUserModel !== false;
    const preserveUserReasoning = options.preserveUserReasoning !== false;
    const modelWasDefault = !manualModelInput?.value.trim() || manualModelInput?.value.trim() === (manualModelInput?.dataset.defaultModel || "");
    const reasoningWasDefault = !manualReasoningInput?.value.trim() || manualReasoningInput?.value.trim() === (manualReasoningInput?.dataset.defaultReasoning || "");

    if (manualModelInput) {
      if ((!preserveUserModel || modelWasDefault) && profile.default_model !== undefined) {
        manualModelInput.value = profile.default_model || "";
      }
      manualModelInput.dataset.defaultModel = profile.default_model || "";
      manualModelInput.placeholder = profile.model_placeholder_zh || profile.model_placeholder_en || profile.default_model || "";
      manualModelInput.readOnly = commandMode;
    }
    if (manualReasoningInput) {
      if ((!preserveUserReasoning || reasoningWasDefault) && profile.effort_default !== undefined) {
        manualReasoningInput.value = profile.effort_default || "";
      }
      manualReasoningInput.dataset.defaultReasoning = profile.effort_default || "";
      manualReasoningInput.placeholder = Array.isArray(profile.effort_options)
        ? profile.effort_options.filter(Boolean).join(", ")
        : "";
      manualReasoningInput.readOnly = commandMode || Boolean(profile.command_only);
    }
    if (manualModelNote) {
      manualModelNote.textContent = window.LooporaUI.currentLocale() === "zh"
        ? (profile.model_help_zh || "")
        : (profile.model_help_en || "");
    }
    if (manualReasoningNote) {
      manualReasoningNote.textContent = window.LooporaUI.currentLocale() === "zh"
        ? (profile.effort_help_zh || "")
        : (profile.effort_help_en || "");
    }

    syncManualModeChips(profile, commandMode);
    manualPresetCard?.classList.toggle("is-active", !commandMode && !profile.command_only);
    manualPresetCard?.classList.toggle("is-inactive", commandMode || profile.command_only);
    manualCommandCard?.classList.toggle("is-active", commandMode);
    manualCommandCard?.classList.toggle("is-inactive", !commandMode);
    if (manualPresetState) {
      manualPresetState.hidden = commandMode || Boolean(profile.command_only);
    }
    if (manualCommandState) {
      manualCommandState.hidden = !commandMode;
    }
    if (manualPresetBody) {
      manualPresetBody.hidden = Boolean(profile.command_only);
    }
    if (manualPresetEmpty) {
      manualPresetEmpty.hidden = !profile.command_only;
    }
    if (manualReasoningField) {
      manualReasoningField.hidden = Boolean(profile.command_only);
    }

    if (commandMode) {
      loadManualCommandDraft(profile);
      if (manualCommandCliInput) {
        manualCommandCliInput.readOnly = false;
      }
      if (manualCommandArgsInput) {
        manualCommandArgsInput.readOnly = false;
      }
    } else {
      if (manualCommandCliInput) {
        manualCommandCliInput.value = profile.cli_name || "";
        manualCommandCliInput.dataset.autofilled = "true";
        manualCommandCliInput.readOnly = true;
      }
      if (manualCommandArgsInput) {
        manualCommandArgsInput.value = defaultManualCommandArgsText(profile);
        manualCommandArgsInput.dataset.autofilled = "true";
        manualCommandArgsInput.readOnly = true;
      }
    }

    if (manualModeNote) {
      manualModeNote.textContent = profile.command_only
        ? localeText(
          "自定义执行工具只支持直接命令；命令必须把最终 JSON 写到 `{output_path}`。",
          "Custom execution tools only support direct command; the command must write final JSON to `{output_path}`.",
        )
        : (commandMode
          ? localeText(
            "直接命令会接管 Loop 层级回退执行器；模型和推理强度只作为参考。",
            "Direct command owns the loop-level fallback executor; model and reasoning become references.",
          )
          : localeText(
            "预设模式会按所选工具自动生成 Loop 层级回退命令。",
            "Preset mode assembles the loop-level fallback command for the selected tool.",
          ));
    }
    if (manualCommandCliNote) {
      manualCommandCliNote.textContent = profile.command_only
        ? localeText("这里填你自己的命令入口。", "Put your own command executable here.")
        : localeText("切到直接命令后，这里就是最终会执行的可执行文件。", "Once direct command mode is active, this executable is used.");
    }
  }

  function setManualExecutionMode(nextMode) {
    const profile = manualExecutionProfile();
    setManualExecutorMode(profile.command_only ? "command" : nextMode);
    syncManualExecutionControls({preserveUserModel: true, preserveUserReasoning: true});
  }

  function strategyHasFinishGate(orchestration) {
    const roleById = Object.fromEntries(strategyRoles(orchestration).map((role) => [role.id, role]));
    return strategySteps(orchestration).some((step) => {
      const role = roleById[step.role_id];
      return role?.archetype === "gatekeeper" && String(step.on_pass || "continue") === "finish_run";
    });
  }

  function strategyPolicy(orchestration) {
    return {
      hasGuide: strategyHasRole(orchestration, "guide"),
      supportsGatekeeperCompletion: strategyHasFinishGate(orchestration),
    };
  }

  function roleRuntimeSummary(orchestration) {
    const roles = strategyRoles(orchestration);
    const counts = new Map();
    roles.forEach((role) => {
      const label = executorLabel(String(role.executor_kind || "codex"));
      counts.set(label, (counts.get(label) || 0) + 1);
    });
    if (!counts.size) {
      return localeText("沿用旧 Loop 层级回退", "Legacy loop-level fallback");
    }
    return Array.from(counts.entries()).map(([label, count]) => (count > 1 ? `${label} x${count}` : label)).join(" · ");
  }

  function syncCompletionModeLabels() {
    if (!completionModeInput) {
      return;
    }
    Array.from(completionModeInput.querySelectorAll("option[data-label-zh]")).forEach((option) => {
      option.textContent = localeText(option.dataset.labelZh || "", option.dataset.labelEn || "");
    });
  }

  function syncCompletionModeState(policy) {
    if (!completionModeInput) {
      return;
    }
    const gatekeeperOption = completionModeInput.querySelector('option[value="gatekeeper"]');
    if (gatekeeperOption) {
      gatekeeperOption.hidden = !policy.supportsGatekeeperCompletion;
      gatekeeperOption.disabled = !policy.supportsGatekeeperCompletion;
    }
    if (!policy.supportsGatekeeperCompletion) {
      completionModeInput.value = "rounds";
    }
    if (completionModeField) {
      completionModeField.dataset.modeLocked = String(!policy.supportsGatekeeperCompletion);
    }
    if (completionModeNote) {
      if (policy.supportsGatekeeperCompletion) {
        completionModeNote.hidden = true;
        completionModeNote.textContent = "";
      } else {
        completionModeNote.hidden = false;
        completionModeNote.textContent = localeText(
          "当前编排没有“通过即结束”的 GateKeeper 步骤，所以这里只能使用轮次推进。",
          "This flow has no finish-on-pass GateKeeper step, so rounds is the only completion mode available here.",
        );
      }
    }
  }

  function applyOrchestrationPolicy() {
    const selected = currentOrchestration();
    const policy = strategyPolicy(selected);
    syncCompletionModeLabels();
    syncCompletionModeState(policy);
    if (triggerWindowField) {
      triggerWindowField.hidden = !policy.hasGuide;
    }
    if (regressionWindowField) {
      regressionWindowField.hidden = !policy.hasGuide;
    }
    return policy;
  }

  function renderOrchestrationSummary() {
    const selected = currentOrchestration();
    if (!selected) {
      applyOrchestrationPolicy();
      showStatus(
        orchestrationSummary,
        localeText(
          "还没有可用的运行流程。新任务先回创建路径选择 Web 对话或同一 Agent 设置；如果你在修复专家资产，再去“流程编排”恢复或派生流程。",
          "No runnable flow is available. For a new task, return to creation choices for Web conversation or Same-Agent Setup; if you are repairing expert assets, open Flows to recover or derive a workflow.",
        ),
        "error",
      );
      return;
    }
    const selectedStrategySource = strategySource(selected);
    const roles = Array.isArray(selectedStrategySource.roles) ? selectedStrategySource.roles.length : 0;
    const steps = Array.isArray(selectedStrategySource.steps) ? selectedStrategySource.steps.length : 0;
    const policy = applyOrchestrationPolicy();
    const source = selected.source === "builtin"
      ? localeText("内置方案", "Built-in")
      : localeText("自定义方案", "Custom");
    const runtimeSummary = roleRuntimeSummary(selected);
    const notes = [];
    if (!policy.supportsGatekeeperCompletion) {
      notes.push(localeText("仅支持轮次推进", "Rounds only"));
    }
    if (!policy.hasGuide) {
      notes.push(localeText("无引导者，已隐藏触发/回退窗口", "No Guide, trigger/regression windows hidden"));
    }
    const parallelGroupCount = strategyParallelGroupCount(selected);
    if (parallelGroupCount) {
      notes.push(localeText(`并行检视 ${parallelGroupCount} 组`, `${parallelGroupCount} parallel review group${parallelGroupCount === 1 ? "" : "s"}`));
    }
    if (!policy.supportsGatekeeperCompletion) {
      showStatus(
        orchestrationSummary,
        localeText(
          `当前方案是 ${selected.name} · ${source} · 角色 ${roles} · 步骤 ${steps} · 执行 ${runtimeSummary}${notes.length ? ` · ${notes.join(" · ")}` : ""}。如果你想用守门裁决收束，请先去编排页补一个“通过即结束”的守门者步骤。`,
          `The selected flow is ${selected.name} · ${source} · Roles ${roles} · Steps ${steps} · Runtime ${runtimeSummary}${notes.length ? ` · ${notes.join(" · ")}` : ""}. Add a finish-on-pass GateKeeper step in Flows if you want gate-based completion.`,
        ),
        "warning",
      );
      return;
    }
    showStatus(
      orchestrationSummary,
      `${selected.name} · ${source} · ${localeText("角色", "Roles")} ${roles} · ${localeText("步骤", "Steps")} ${steps} · ${localeText("执行", "Runtime")} ${runtimeSummary}${notes.length ? ` · ${notes.join(" · ")}` : ""}${selected.description ? ` · ${selected.description}` : ""}`,
      "success",
    );
  }

  async function validateSpec(options = {}) {
    const quiet = options.quiet ?? false;
    const path = specPathInput.value.trim();
    const requestId = ++latestSpecValidationRequest;
    if (!path) {
      if (quiet) {
        showStatus(specValidation, "");
      } else {
        showStatus(specValidation, localeText("请先提供契约路径。", "Please provide a spec path first."), "error");
      }
      return false;
    }
    if (!quiet) {
      showStatus(specValidation, localeText("正在校验 Loop 契约…", "Validating spec..."));
    }
    const {response, payload, error} = await fetchJson(`/api/specs/validate?path=${encodeURIComponent(path)}`);
    if (requestId !== latestSpecValidationRequest) {
      return false;
    }
    if (error || !response) {
      if (!quiet) {
        showStatus(specValidation, errorMessage(error, localeText("Loop 契约校验暂时不可用。", "Spec validation is temporarily unavailable.")), "error");
      }
      return false;
    }
    if (payload.ok) {
      const feedback = specValidationFeedback({
        ok: true,
        check_mode: payload.check_mode,
        check_count: payload.check_count,
      });
      showStatus(specValidation, feedback.message, feedback.kind);
      specPathInput.value = payload.path;
      saveDraft();
      return true;
    }
    if (!quiet) {
      showStatus(specValidation, payload.error || localeText("Loop 契约校验失败。", "Spec validation failed."), "error");
    }
    return false;
  }

  async function browseWorkdir() {
    const {response, payload, error} = await fetchJson("/api/system/pick-directory", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({start_path: workdirInput.value.trim()}),
    });
    if (error || !response?.ok) {
      throw new Error(payload.error || errorMessage(error, localeText("无法打开目录选择器。", "Unable to open the directory picker.")));
    }
    if (payload.path) {
      workdirInput.value = payload.path;
      syncManualWorkdirContext();
      saveDraft();
    }
  }

  async function browseSpec() {
    const startPath = specPathInput.value.trim() || workdirInput.value.trim();
    const {response, payload, error} = await fetchJson("/api/system/pick-spec-file", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({start_path: startPath}),
    });
    if (error || !response?.ok) {
      throw new Error(payload.error || errorMessage(error, localeText("无法打开契约选择器。", "Unable to open the spec picker.")));
    }
    if (payload.path) {
      specPathInput.value = payload.path;
      await validateSpec();
    }
  }

  async function createSpecTemplate() {
    let targetPath = specPathInput.value.trim();
    if (!targetPath) {
      if (createSpecTemplateButton.dataset.nativeDialogsEnabled === "false") {
        showStatus(specValidation, localeText("网络模式下请先手动填好服务端上的契约路径，再创建模板。", "In network mode, enter a server-side spec path first and then create the template."), "error");
        return;
      }
      const startPath = workdirInput.value.trim();
      const selection = await fetchJson("/api/system/pick-spec-save-path", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({start_path: startPath}),
      });
      if (selection.error || !selection.response?.ok) {
        throw new Error(selection.payload.error || errorMessage(selection.error, localeText("无法选择契约保存路径。", "Unable to choose a spec save path.")));
      }
      if (!selection.payload.path) {
        return;
      }
      targetPath = selection.payload.path;
    }

    const selected = currentOrchestration();
    const selectedStrategySource = selected ? strategySource(selected) : null;
    const {response, payload, error} = await fetchJson("/api/specs/init", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        path: targetPath,
        locale: window.LooporaUI.currentLocale(),
        strategy_json: selectedStrategySource,
      }),
    });
    if (error || !response) {
      throw new Error(errorMessage(error, localeText("无法创建契约模板。", "Unable to create the spec template.")));
    }
    if (!response.ok) {
      renderSpecEditorRecovery(payload);
      showStatus(specValidation, payload.error || localeText("无法创建契约模板。", "Unable to create the spec template."), "error");
      return;
    }
    clearSpecEditorRecovery();
    specPathInput.value = payload.path;
    await validateSpec();
  }

  function isSpecOutputRecoveryPayload(payload) {
    return Boolean(payload && typeof payload === "object" && payload.resource_recovery === "invalid_spec_output_target" && Array.isArray(payload.next_actions));
  }

  function clearSpecEditorRecovery() {
    if (!specEditorRecoveryPanel) {
      return;
    }
    specEditorRecoveryPanel.hidden = true;
    specEditorRecoveryPanel.innerHTML = "";
  }

  function specOutputRecoveryActionLabel(action) {
    const kind = String(action?.kind || "").trim();
    if (kind === "choose_spec_output_file") {
      return localeText("选择契约输出文件", "Choose spec output file");
    }
    if (kind === "retry_web_spec_save") {
      return localeText("重试保存契约", "Retry spec save");
    }
    if (kind === "retry_web_spec_init") {
      return localeText("重试生成模板", "Retry template creation");
    }
    if (kind === "validate_spec_content") {
      return localeText("校验当前契约", "Validate current spec");
    }
    if (kind === "render_spec_template") {
      return localeText("载入模板草稿", "Load template draft");
    }
    return window.LooporaUI.recoveryActionLabel(action);
  }

  function specOutputRecoveryActionHint(action) {
    const kind = String(action?.kind || "").trim();
    if (kind === "choose_spec_output_file") {
      return localeText("换成一个可写的 Markdown 契约路径。", "Switch to a writable Markdown spec path.");
    }
    if (kind === "retry_web_spec_save") {
      return localeText("路径修复后，把当前编辑器内容再次写回磁盘。", "After fixing the path, write the current editor content to disk again.");
    }
    if (kind === "retry_web_spec_init") {
      return localeText("路径修复后，重新按当前流程生成契约模板。", "After fixing the path, generate the spec template for the current flow again.");
    }
    if (kind === "validate_spec_content") {
      return localeText("检查当前路径上的契约是否满足 Loop 最小结构。", "Check whether the spec at the current path satisfies the minimum Loop structure.");
    }
    if (kind === "render_spec_template") {
      return localeText("不写磁盘，只把当前流程的模板载入编辑器作为草稿。", "Load the current flow template into the editor as a draft without writing to disk.");
    }
    return window.LooporaUI.recoveryActionHint(action);
  }

  function specOutputRecoveryActionControlHtml(action) {
    const kind = String(action?.kind || "").trim();
    if (!["choose_spec_output_file", "retry_web_spec_save", "retry_web_spec_init", "validate_spec_content", "render_spec_template"].includes(kind)) {
      return "";
    }
    return `<button class="ghost-button" type="button" data-spec-editor-recovery-action="${escapeHtml(kind)}">${escapeHtml(specOutputRecoveryActionLabel(action))}</button>`;
  }

  function renderSpecEditorRecovery(payload) {
    if (!specEditorRecoveryPanel || !isSpecOutputRecoveryPayload(payload)) {
      clearSpecEditorRecovery();
      return;
    }
    if (specPreviewModal?.hidden) {
      openSpecPreview(createSpecTemplateButton || editSpecButton);
    }
    specEditorRecoveryPanel.innerHTML = window.LooporaUI.recoveryPanelHtml(payload, {
      testid: "spec-editor-recovery",
      title: localeText("契约输出位置需要修复", "Spec output location needs attention"),
      summary: payload.error || payload.summary || "",
      actionLabel: specOutputRecoveryActionLabel,
      actionHint: specOutputRecoveryActionHint,
      actionControlHtml: specOutputRecoveryActionControlHtml,
    });
    specEditorRecoveryPanel.hidden = false;
    bindSpecEditorRecoveryActionButtons();
    window.LooporaUI?.bindRecoveryCommandCopy?.();
  }

  function bindSpecEditorRecoveryActionButtons() {
    specEditorRecoveryPanel?.querySelectorAll("[data-spec-editor-recovery-action]").forEach((button) => {
      if (!(button instanceof HTMLButtonElement) || button.dataset.boundSpecEditorRecoveryAction === "1") {
        return;
      }
      button.dataset.boundSpecEditorRecoveryAction = "1";
      button.addEventListener("click", () => runSpecEditorRecoveryAction(button));
    });
  }

  async function runSpecEditorRecoveryAction(button) {
    const action = String(button.dataset.specEditorRecoveryAction || "").trim();
    button.disabled = true;
    try {
      if (action === "choose_spec_output_file") {
        await chooseSpecOutputFileFromRecovery();
      } else if (action === "retry_web_spec_save") {
        await saveSpecDocument({silent: false});
      } else if (action === "retry_web_spec_init") {
        await createSpecTemplate();
      } else if (action === "validate_spec_content") {
        await validateSpec();
      } else if (action === "render_spec_template") {
        await loadSpecTemplateDraft();
      }
    } finally {
      button.disabled = false;
    }
  }

  async function chooseSpecOutputFileFromRecovery() {
    if (createSpecTemplateButton?.dataset.nativeDialogsEnabled === "false") {
      closeSpecPreview();
      specPathInput.focus();
      showStatus(specValidation, localeText("请先把契约路径改成服务端可写的 Markdown 文件。", "Change the spec path to a writable server-side Markdown file."), "warning");
      return;
    }
    const startPath = specPathInput.value.trim() || workdirInput.value.trim();
    const selection = await fetchJson("/api/system/pick-spec-save-path", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({start_path: startPath}),
    });
    if (selection.error || !selection.response?.ok) {
      setSpecEditorSaveState(selection.payload?.error || errorMessage(selection.error, localeText("无法选择契约保存路径。", "Unable to choose a spec save path.")), "error");
      return;
    }
    if (!selection.payload.path) {
      return;
    }
    specPathInput.value = selection.payload.path;
    specPreviewPath.textContent = selection.payload.path;
    setSpecEditorSaveState(localeText("已选择新的契约输出路径，可以重试保存。", "A new spec output path is selected; retry saving."), "warning");
    saveDraft();
  }

  async function loadSpecTemplateDraft() {
    const selected = currentOrchestration();
    const selectedStrategySource = selected ? strategySource(selected) : null;
    const {response, payload, error} = await fetchJson("/api/specs/template", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        locale: window.LooporaUI.currentLocale(),
        strategy_json: selectedStrategySource,
      }),
    });
    if (error || !response?.ok || !payload?.ok) {
      setSpecEditorSaveState(payload?.error || errorMessage(error, localeText("无法载入契约模板草稿。", "Unable to load the spec template draft.")), "error");
      return;
    }
    if (!specEditorInput) {
      return;
    }
    if (specEditorWorkbench) {
      specEditorWorkbench.setValue(payload.content || "", {render: false});
    } else {
      specEditorInput.value = payload.content || "";
    }
    specEditorSavedText = "";
    specEditorLastValidation = {state: "dirty", error: localeText("模板草稿尚未保存。", "The template draft is not saved yet."), check_count: 0, check_mode: ""};
    setSpecEditorValidation(specEditorLastValidation);
    setSpecEditorSaveState(localeText("模板草稿已载入编辑器；请选择可写路径后保存。", "Template draft loaded; choose a writable path and save it."), "warning");
    syncSpecPreviewStatusForCurrentMode();
  }

  function setSpecPreviewStatus(message, kind = "") {
    if (!specPreviewStatus) {
      return;
    }
    specPreviewStatus.textContent = message || "";
    specPreviewStatus.className = `spec-preview-status${kind ? ` is-${kind}` : ""}`;
  }

  function setSpecEditorSaveState(message, kind = "") {
    if (!specEditorSaveState) {
      return;
    }
    specEditorSaveState.textContent = message || "";
    specEditorSaveState.className = `field-note markdown-workbench-save-state${kind ? ` is-${kind}` : ""}`;
  }

  function setSpecEditorValidation(validation) {
    if (!specEditorValidationPill) {
      return;
    }
    const feedback = specValidationFeedback(validation);
    specEditorValidationPill.textContent = feedback.pill;
    specEditorValidationPill.className = `status-pill spec-preview-readonly${feedback.kind ? ` is-${feedback.kind}` : ""}`;
  }

  function specEditorIsDirty() {
    return Boolean(specEditorInput) && specEditorInput.value !== specEditorSavedText;
  }

  function specPreviewPlaceholderHtml() {
    return `<p>${escapeHtml(localeText(
      "这里只在你手动点击“预览”后显示渲染结果。",
      "The rendered result appears here only after you click Preview.",
    ))}</p>`;
  }

  function syncSpecPreviewToggleButton() {
    if (!specPreviewToggleButton) {
      return;
    }
    specPreviewToggleButton.textContent = specPreviewVisible
      ? localeText("返回编辑", "Back to editor")
      : localeText("预览", "Preview");
    specPreviewToggleButton.setAttribute("aria-pressed", String(specPreviewVisible));
  }

  function syncSpecPreviewMode() {
    specEditorWorkbenchShell?.classList.toggle("is-previewing", specPreviewVisible);
    if (specEditorSourcePanel) {
      specEditorSourcePanel.hidden = specPreviewVisible;
    }
    if (specEditorPreviewPanel) {
      specEditorPreviewPanel.hidden = !specPreviewVisible;
    }
    syncSpecPreviewToggleButton();
  }

  function syncSpecPreviewStatusForCurrentMode() {
    if (specPreviewVisible) {
      setSpecPreviewStatus(
        localeText("这是当前文本的渲染结果。要继续修改，请返回编辑。", "This is the rendered result for the current text. Go back to the editor to keep changing it."),
        "success",
      );
      return;
    }
    if (specEditorIsDirty()) {
      setSpecPreviewStatus(
        localeText("当前先保持在源码编辑态；准备好后再手动点“预览”。", "Stay in source-editing mode for now, then click Preview manually when you are ready."),
        "warning",
      );
      return;
    }
    setSpecPreviewStatus(
      localeText("先专心修改源码，准备好后再手动打开预览。", "Focus on editing first, then open the preview manually when you are ready."),
      "",
    );
  }

  function openSpecPreview(trigger = editSpecButton) {
    if (!specPreviewModal) {
      return;
    }
    lastSpecPreviewTrigger = trigger instanceof HTMLElement ? trigger : document.activeElement;
    specPreviewModal.hidden = false;
    specPreviewModal.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");
    specPreviewModal.querySelector(".spec-preview-dialog")?.scrollTo({top: 0});
    syncSpecPreviewMode();
  }

  function closeSpecPreview() {
    if (!specPreviewModal) {
      return;
    }
    specPreviewModal.hidden = true;
    specPreviewModal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("modal-open");
    if (lastSpecPreviewTrigger instanceof HTMLElement) {
      lastSpecPreviewTrigger.focus();
    }
  }

  function applyLoadedSpecDocument(payload) {
    if (!payload || !payload.ok || !specEditorInput) {
      return;
    }
    clearSpecEditorRecovery();
    specEditorLoadedPath = payload.path;
    specEditorSavedText = String(payload.content || "");
    specEditorLastValidation = payload.validation || null;
    specPathInput.value = payload.path;
    specPreviewPath.textContent = payload.path;
    specEditorWorkbench?.setValue(payload.content || "", {render: false});
    specEditorWorkbench?.setPreviewHtml(specPreviewPlaceholderHtml());
    setSpecEditorValidation(payload.validation);
    showStatus(
      specValidation,
      specValidationFeedback(payload.validation).message,
      specValidationFeedback(payload.validation).kind,
    );
    setSpecEditorSaveState(
      payload.validation?.ok
        ? localeText("磁盘内容已载入，可以继续修改。", "Disk content loaded. You can keep editing.")
        : localeText("磁盘内容已载入，但当前契约还需要修正。", "Disk content loaded, but the current spec still needs fixes."),
      payload.validation?.ok ? "success" : "warning",
    );
    syncSpecPreviewStatusForCurrentMode();
    saveDraft();
  }

  async function loadSpecDocument(options = {}) {
    const path = specPathInput.value.trim();
    if (!path) {
      showStatus(specValidation, localeText("请先提供契约路径，再打开编辑器。", "Provide a spec path before opening the editor."), "error");
      return;
    }
    if (!options.force && specEditorLoadedPath === path && specEditorInput?.value) {
      specPreviewPath.textContent = path;
      if (!specEditorIsDirty() && specEditorLastValidation) {
        setSpecEditorValidation(specEditorLastValidation);
      }
      syncSpecPreviewStatusForCurrentMode();
      return;
    }

    specPreviewPath.textContent = path;
    setSpecPreviewStatus(localeText("正在读取 Loop 契约…", "Loading spec..."));
    setSpecEditorSaveState(localeText("正在把磁盘内容载入编辑器。", "Loading the file from disk into the editor."));

    const {response, payload, error} = await fetchJson(`/api/specs/document?path=${encodeURIComponent(path)}`);
    if (error || !response) {
      specPreviewPath.textContent = path;
      setSpecPreviewStatus(errorMessage(error, localeText("Loop 契约编辑器暂时不可用。", "The spec editor is temporarily unavailable.")), "error");
      setSpecEditorSaveState(errorMessage(error, localeText("暂时无法读取这份契约。", "This spec cannot be read right now.")), "error");
      return;
    }
    if (!payload.ok) {
      specPreviewPath.textContent = path;
      renderSpecEditorRecovery(payload);
      setSpecPreviewStatus(payload.error || localeText("Loop 契约编辑器加载失败。", "The spec editor could not be loaded."), "error");
      setSpecEditorSaveState(payload.error || localeText("请检查路径和文件内容。", "Check the path and file contents."), "error");
      return;
    }
    applyLoadedSpecDocument(payload);
  }

  async function saveSpecDocument(options = {}) {
    const path = specPathInput.value.trim();
    if (!path) {
      showStatus(specValidation, localeText("请先提供契约路径，再保存编辑器内容。", "Provide a spec path before saving the editor contents."), "error");
      return false;
    }
    if (!specEditorInput) {
      return false;
    }
    setSpecEditorSaveState(localeText("正在把改动写回磁盘。", "Writing your changes back to disk."));
    const {response, payload, error} = await fetchJson("/api/specs/document", {
      method: "PUT",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({path, content: specEditorInput.value}),
    });
    if (error || !response) {
      const message = errorMessage(error, localeText("保存契约失败。", "Unable to save the spec."));
      setSpecEditorSaveState(message, "error");
      if (!options.silent) {
        showStatus(specValidation, message, "error");
      }
      return false;
    }
    if (!payload.ok) {
      const message = payload.error || localeText("保存契约失败。", "Unable to save the spec.");
      renderSpecEditorRecovery(payload);
      setSpecEditorSaveState(message, "error");
      if (!options.silent) {
        showStatus(specValidation, message, "error");
      }
      return false;
    }
    applyLoadedSpecDocument(payload);
    if (payload.validation?.ok) {
      setSpecEditorSaveState(localeText("已保存到磁盘，当前契约已通过校验。", "Saved to disk. The current spec is valid."), "success");
    } else {
      setSpecEditorSaveState(localeText("已保存到磁盘，但当前契约还需要修正。", "Saved to disk, but the current spec still needs fixes."), "warning");
    }
    if (!options.silent) {
      showStatus(
        specValidation,
        specValidationFeedback(payload.validation).message,
        specValidationFeedback(payload.validation).kind,
      );
    }
    return true;
  }

  async function editSpec() {
    specPreviewVisible = false;
    openSpecPreview(editSpecButton);
    syncSpecPreviewMode();
    if (!specEditorWorkbench && window.LooporaMarkdownWorkbench && specPreviewContent && specEditorInput) {
      specEditorWorkbench = window.LooporaMarkdownWorkbench.create({
        textarea: specEditorInput,
        preview: specPreviewContent,
        autoRenderOnInput: false,
        onStatus(kind, message) {
          if (kind === "loading") {
            setSpecPreviewStatus(message || localeText("正在生成 Markdown 预览…", "Generating the Markdown preview..."));
            return;
          }
          if (kind === "error") {
            setSpecPreviewStatus(message || localeText("Markdown 预览失败。", "Markdown preview failed."), "error");
            return;
          }
          syncSpecPreviewStatusForCurrentMode();
        },
        emptyMessage: {
          zh: "这份契约目前还是空的。",
          en: "This spec is currently empty.",
        },
        loadingMessage: {
          zh: "正在渲染 Markdown 预览…",
          en: "Rendering the Markdown preview...",
        },
      });
      specEditorInput.addEventListener("input", () => {
        setSpecEditorSaveState(localeText("有未保存的改动。提交 Loop 前会先尝试自动保存。", "There are unsaved changes. Loop submission will try to save them first."), "warning");
        setSpecEditorValidation({
          state: "dirty",
          error: localeText("编辑器里有未保存的改动。", "There are unsaved editor changes."),
          check_count: 0,
          check_mode: "",
        });
        syncSpecPreviewStatusForCurrentMode();
      });
    }
    await loadSpecDocument();
    syncSpecPreviewMode();
    syncSpecPreviewStatusForCurrentMode();
    specEditorInput?.focus();
  }

  async function toggleSpecPreview() {
    if (specPreviewVisible) {
      specPreviewVisible = false;
      syncSpecPreviewMode();
      syncSpecPreviewStatusForCurrentMode();
      specEditorInput?.focus();
      return;
    }
    specPreviewVisible = true;
    syncSpecPreviewMode();
    await specEditorWorkbench?.renderNow();
  }

  function parseNumber(value, fallback) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  async function submitForm(event) {
    event.preventDefault();
    if (directHandoffBlocksManualCreation(formError)) {
      return;
    }
    if (!form.reportValidity()) {
      return;
    }
    showStatus(formError, "");
    if (!currentOrchestration()) {
      showStatus(formError, localeText("请先选择一个流程编排。", "Choose a flow first."), "error");
      return;
    }
    if (specEditorIsDirty()) {
      if (specPathInput.value.trim() !== specEditorLoadedPath) {
        showStatus(
          formError,
          localeText("契约路径已经变了，请重新打开编辑器确认要保存哪份文件。", "The spec path changed. Reopen the editor to confirm which file should be saved."),
          "error",
        );
        return;
      }
      const saved = await saveSpecDocument({silent: false});
      if (!saved) {
        showStatus(formError, localeText("Loop 契约编辑器里的改动还没有成功保存，请先修复后再提交。", "The editor changes were not saved successfully. Fix that first before submitting."), "error");
        return;
      }
    }
    const specValid = await validateSpec();
    if (!specValid) {
      showStatus(formError, localeText("Loop 契约不满足要求，请先修复后再提交。", "The spec does not satisfy the required structure yet."), "error");
      return;
    }

    const formData = new FormData(form);
    const executionCommandMode = manualCommandMode();
    if (executionCommandMode) {
      setManualExecutorMode("command");
    }
    const payload = {
      name: String(formData.get("name") || "").trim(),
      workdir: String(formData.get("workdir") || "").trim(),
      spec_path: String(formData.get("spec_path") || "").trim(),
      orchestration_id: String(formData.get("orchestration_id") || "").trim(),
      completion_mode: String(formData.get("completion_mode") || "gatekeeper").trim(),
      executor_kind: String(formData.get("executor_kind") || "codex").trim(),
      executor_mode: executionCommandMode ? "command" : "preset",
      command_cli: executionCommandMode ? String(formData.get("command_cli") || "").trim() : "",
      command_args_text: executionCommandMode ? String(formData.get("command_args_text") || "") : "",
      model: String(formData.get("model") || "").trim(),
      reasoning_effort: String(formData.get("reasoning_effort") || "").trim(),
      iteration_interval_seconds: parseNumber(formData.get("iteration_interval_seconds"), 0),
      max_iters: parseNumber(formData.get("max_iters"), 8),
      max_role_retries: parseNumber(formData.get("max_role_retries"), 2),
      delta_threshold: parseNumber(formData.get("delta_threshold"), 0.005),
      trigger_window: parseNumber(formData.get("trigger_window"), 4),
      regression_window: parseNumber(formData.get("regression_window"), 2),
      start_immediately: formData.get("start_immediately") === "1",
    };

    setButtonBusy(saveLoopButton, true);
    try {
      const {response, payload: responsePayload, error} = await fetchJson("/api/loops", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      });
      if (error || !response) {
        showStatus(formError, errorMessage(error, localeText("保存 Loop 失败。", "Unable to save the loop.")), "error");
        return;
      }
      if (!response.ok) {
        if (isManualRecoveryPayload(responsePayload)) {
          renderManualLoopRecovery(responsePayload);
          return;
        }
        const redirectUrl = runStartFailureRedirect(responsePayload);
        if (redirectUrl) {
          clearDraft();
          window.location.href = redirectUrl;
          return;
        }
        showStatus(formError, responsePayload.error || localeText("保存 Loop 失败。", "Unable to save the loop."), "error");
        return;
      }
      clearDraft();
      window.location.href = window.LooporaUI.workdirContextRedirectUrl(responsePayload.redirect_url, {
        fallback: "/",
        workdir: manualRunWorkdir(responsePayload),
      });
    } finally {
      setButtonBusy(saveLoopButton, false);
    }
  }

  if (browseWorkdirButton && !browseWorkdirButton.disabled) {
    browseWorkdirButton.addEventListener("click", () => runAction(
      browseWorkdirButton,
      browseWorkdir,
      {
        errorTarget: formError,
        fallbackMessage: localeText("无法打开目录选择器。", "Unable to open the directory picker."),
      },
    ));
  }
  if (browseSpecButton && !browseSpecButton.disabled) {
    browseSpecButton.addEventListener("click", () => runAction(
      browseSpecButton,
      browseSpec,
      {
        errorTarget: specValidation,
        fallbackMessage: localeText("无法打开契约选择器。", "Unable to open the spec picker."),
      },
    ));
  }
  if (editSpecButton) {
    editSpecButton.addEventListener("click", () => runAction(
      editSpecButton,
      editSpec,
      {
        errorTarget: specValidation,
        fallbackMessage: localeText("无法打开契约编辑器。", "Unable to open the spec editor."),
      },
    ));
  }
  if (specEditorSaveButton) {
    specEditorSaveButton.addEventListener("click", () => runAction(
      specEditorSaveButton,
      () => saveSpecDocument({silent: false}),
      {
        errorTarget: specValidation,
        fallbackMessage: localeText("无法保存契约。", "Unable to save the spec."),
      },
    ));
  }
  if (specPreviewToggleButton) {
    specPreviewToggleButton.addEventListener("click", () => runAction(
      specPreviewToggleButton,
      toggleSpecPreview,
      {
        errorTarget: specValidation,
        fallbackMessage: localeText("无法切换契约预览。", "Unable to toggle the spec preview."),
      },
    ));
  }
  if (createSpecTemplateButton) {
    createSpecTemplateButton.addEventListener("click", () => runAction(
      createSpecTemplateButton,
      createSpecTemplate,
      {
        errorTarget: specValidation,
        fallbackMessage: localeText("无法创建契约模板。", "Unable to create the spec template."),
      },
    ));
  }
  if (clearDraftButton) {
    clearDraftButton.addEventListener("click", () => clearDraft({announce: true}));
  }
  workdirQuickPickButtons.forEach((button) => {
    button.addEventListener("click", () => {
      workdirInput.value = button.dataset.fillWorkdir || "";
      syncManualWorkdirContext();
      saveDraft();
      showStatus(formError, "");
    });
  });

  workdirInput.addEventListener("change", () => {
    syncManualWorkdirContext();
    showStatus(formError, "");
  });
  workdirInput.addEventListener("input", () => {
    syncManualWorkdirContext();
    showStatus(formError, "");
  });
  orchestrationInput?.addEventListener("change", renderOrchestrationSummary);
  completionModeInput?.addEventListener("change", renderOrchestrationSummary);
  manualExecutorKindInput?.addEventListener("change", () => {
    if (manualCommandMode()) {
      saveManualCommandDraft(lastManualExecutorKind);
    }
    lastManualExecutorKind = manualExecutorKindInput.value;
    if (manualCommandCliInput) {
      manualCommandCliInput.dataset.autofilled = "true";
    }
    if (manualCommandArgsInput) {
      manualCommandArgsInput.dataset.autofilled = "true";
    }
    syncManualExecutionControls({preserveUserModel: true, preserveUserReasoning: true});
    saveDraft();
  });
  manualModeChips.forEach((chip) => {
    const input = chip.querySelector("input[name='executor_mode']");
    chip.addEventListener("click", (event) => {
      if (input?.disabled) {
        event.preventDefault();
      }
    });
    input?.addEventListener("change", () => {
      if (!input.checked) {
        return;
      }
      const nextMode = input.value || chip.dataset.manualModeChoice || "preset";
      if (nextMode === "preset") {
        saveManualCommandDraft(manualExecutorKindInput?.value || lastManualExecutorKind);
      }
      setManualExecutionMode(nextMode);
      saveDraft();
    });
  });
  [manualCommandCliInput, manualCommandArgsInput].forEach((input) => {
    input?.addEventListener("input", () => {
      input.dataset.autofilled = "false";
    });
  });
  specPathInput.addEventListener("change", () => {
    if (specPathInput.value.trim() !== specEditorLoadedPath) {
      specEditorLoadedPath = "";
      specEditorSavedText = "";
      specEditorLastValidation = null;
      setSpecEditorSaveState(localeText("路径已经变化，重新打开编辑器后会读取新的契约文件。", "The path changed. Reopen the editor to load the new spec file."));
      setSpecEditorValidation({
        state: "detached",
        error: localeText("当前编辑器还没有绑定新的契约文件。", "The editor is not bound to the new spec file yet."),
        check_count: 0,
        check_mode: "",
      });
    }
    validateSpec({quiet: false});
  });
  specPathInput.addEventListener("blur", () => validateSpec({quiet: true}));
  form.addEventListener("input", saveDraft);
  form.addEventListener("change", saveDraft);
  form.addEventListener("submit", submitForm);
  bundleImportForm?.addEventListener("submit", (event) => {
    if (directHandoffBlocksManualCreation(bundleImportError || formError)) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, {capture: true});
  [...composeModeLinks, ...newConversationControls].forEach((link) => {
    link?.addEventListener("click", (event) => {
      if (!directHandoffBlocksManualCreation(formError)) {
        return;
      }
      event.preventDefault();
      event.stopImmediatePropagation();
    }, {capture: true});
  });
  document.addEventListener("loopora:localechange", () => {
    renderManualDirectHandoffGate();
    renderOrchestrationSummary();
    syncManualExecutionControls({preserveUserModel: true, preserveUserReasoning: true});
    syncSpecPreviewToggleButton();
    syncSpecPreviewStatusForCurrentMode();
    alignmentHistoryController?.render();
    if (!specPreviewVisible) {
      specEditorWorkbench?.setPreviewHtml(specPreviewPlaceholderHtml());
    }
  });
  document.addEventListener("loopora:workdirchange", syncManualDraftFromGlobalWorkdir);
  document.querySelectorAll("[data-close-spec-preview]").forEach((element) => {
    element.addEventListener("click", closeSpecPreview);
  });
  specPreviewModal?.addEventListener("click", (event) => {
    if (event.target === specPreviewModal) {
      closeSpecPreview();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && specPreviewModal && !specPreviewModal.hidden) {
      closeSpecPreview();
    }
  });

  const restoredDraft = restoreDraftIfAllowed();
  specEditorWorkbench?.setPreviewHtml(specPreviewPlaceholderHtml());
  syncSpecPreviewMode();
  renderManualDirectHandoffGate();
  syncManualExecutionControls({preserveUserModel: true, preserveUserReasoning: true});
  renderOrchestrationSummary();
  if (specPathInput.value.trim()) {
    validateSpec({quiet: true});
  }
  if (restoredDraft) {
    syncManualWorkdirContext();
    saveDraft();
  } else {
    updateDraftUI();
  }
  alignmentHistoryController?.load().catch(() => {});
});

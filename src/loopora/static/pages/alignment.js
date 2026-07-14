(function () {
  function createAlignmentConsoleProjector({localeText} = {}) {
    const pickText = localeText || ((_zh, en) => en);

    function textValue(value) {
      return String(value || "").trim();
    }

    function summaryWithPayload(label, payload, key) {
      const value = textValue(payload[key]);
      return value ? `${label} · ${value}` : label;
    }

    function sourceContextSummary(payload) {
      const sourceType = textValue(payload.source_type);
      const sourceLabels = {
        alignment_session: pickText("已选择对齐对话上下文", "Alignment session context selected"),
        bundle: pickText("已选择 Loop 计划上下文", "Loop plan context selected"),
        loop: pickText("已选择 Loop 上下文", "Loop context selected"),
        run: pickText("已选择运行上下文", "Run context selected"),
        spec_file: pickText("已选择规格文件上下文", "Spec file context selected"),
      };
      return sourceLabels[sourceType] || pickText("已选择来源上下文", "Source context selected");
    }

    function statusSummary(label, payload) {
      const parts = [label];
      const status = textValue(payload.status);
      if (status) {
        parts.push(status);
      }
      const error = textValue(payload.error);
      if (error) {
        parts.push(error);
      }
      return parts.join(" · ");
    }

    function runStartFailedSummary(payload) {
      const parts = [pickText("运行启动失败", "Run start failed")];
      if (textValue(payload.run_recovery) === "retry_run_start") {
        parts.push(pickText("可重试启动", "Retry start available"));
      }
      const error = textValue(payload.run_start_error) || textValue(payload.error);
      if (error) {
        parts.push(error);
      }
      return parts.join(" · ");
    }

    const eventSummaries = {
      alignment_session_created: (payload) =>
        statusSummary(pickText("对齐对话已创建", "Alignment session created"), payload),
      alignment_source_context_selected: sourceContextSummary,
      alignment_started: (payload) => statusSummary(pickText("对齐执行已开始", "Alignment run started"), payload),
      alignment_user_message: (payload) =>
        summaryWithPayload(pickText("用户任务输入", "User task input"), payload, "content"),
      alignment_message: (payload) =>
        summaryWithPayload(
          payload.role === "assistant"
            ? pickText("助手回复", "Assistant reply")
            : pickText("对齐消息", "Alignment message"),
          payload,
          "content",
        ),
      alignment_agreement_ready: () => pickText("工作协议待确认", "Working agreement ready"),
      alignment_agreement_confirmed: () => pickText("工作协议已确认", "Working agreement confirmed"),
      alignment_agreement_reopened: () => pickText("工作协议已重新打开", "Working agreement reopened"),
      alignment_ready_review_started: () => pickText("READY 复核已开始", "READY review started"),
      alignment_stage_blocked: (payload) => statusSummary(pickText("阶段被阻塞", "Stage blocked"), payload),
      alignment_waiting_user: (payload) => statusSummary(pickText("等待用户判断", "Waiting for user judgment"), payload),
      alignment_bundle_written: (payload) =>
        summaryWithPayload(pickText("候选 Loop 计划已写入", "Candidate Loop plan written"), payload, "bundle_path"),
      alignment_validation_passed: () => pickText("Loop 计划校验通过", "Loop plan validation passed"),
      alignment_validation_failed: (payload) => statusSummary(pickText("Loop 计划校验失败", "Loop plan validation failed"), payload),
      alignment_repair_started: (payload) => statusSummary(pickText("修复已开始", "Repair started"), payload),
      alignment_generation_retry_requested: (payload) =>
        statusSummary(pickText("重新生成已请求", "Plan generation retry requested"), payload),
      alignment_ready: (payload) => statusSummary(pickText("Loop 计划已准备好", "Loop plan ready"), payload),
      alignment_failed: (payload) => statusSummary(pickText("对齐失败", "Alignment failed"), payload),
      alignment_interrupted: (payload) => statusSummary(pickText("本地规划已中断", "Local planning interrupted"), payload),
      alignment_cancel_requested: () => pickText("取消请求已发送", "Cancel requested"),
      alignment_cancelled: () => pickText("对齐已取消", "Alignment cancelled"),
      alignment_imported: () => pickText("Loop 已创建", "Loop created"),
      alignment_import_failed: (payload) => statusSummary(pickText("Loop 创建失败", "Loop creation failed"), payload),
      alignment_run_started: () => pickText("运行已启动", "Run started"),
      alignment_run_start_failed: runStartFailedSummary,
      alignment_bundle_synced: () => pickText("Loop 计划预览已同步", "Loop plan preview synced"),
      alignment_bundle_sync_failed: (payload) => statusSummary(pickText("Loop 计划同步失败", "Loop plan sync failed"), payload),
      stream_error: (payload) => statusSummary(pickText("事件流错误", "Event stream error"), payload),
    };

    function eventKind(event) {
      if (event.event_type === "codex_event") {
        const type = String(event.payload?.type || "");
        if (type === "command") {
          return "command";
        }
        if (type.includes("complete")) {
          return "success";
        }
        return "stdout";
      }
      if (event.event_type.includes("failed") || event.event_type.includes("cancel") || event.event_type === "stream_error") {
        return "error";
      }
      if (event.event_type.includes("ready") || event.event_type.includes("passed") || event.event_type.includes("imported")) {
        return "success";
      }
      if (event.event_type.includes("repair") || event.event_type.includes("validat") || event.event_type.includes("started")) {
        return "progress";
      }
      return "system";
    }

    function eventSummary(event) {
      const payload = event.payload || {};
      if (event.event_type === "codex_event") {
        return payload.message || payload.type || "agent event";
      }
      const projector = eventSummaries[event.event_type];
      if (projector) {
        return projector(payload);
      }
      if (payload.error) {
        return payload.error;
      }
      if (payload.content) {
        return payload.content;
      }
      if (payload.bundle_path) {
        return payload.bundle_path;
      }
      return String(event.event_type || "").replaceAll("_", " ");
    }

    return {eventKind, eventSummary};
  }

  window.LooporaAlignmentConsole = {createAlignmentConsoleProjector};
})();

document.addEventListener("DOMContentLoaded", () => {
  const panel = document.querySelector("[data-testid='loop-alignment-panel']");
  if (!panel || !window.LooporaUI) {
    return;
  }

  const scrollRegion = document.getElementById("alignment-scroll-region");
  const profiles = JSON.parse(document.getElementById("executor-profiles-json")?.textContent || "[]");
  const shell = document.querySelector("[data-testid='loop-compose-shell']");
  const startForm = document.getElementById("alignment-start-form");
  const emptyState = document.getElementById("alignment-empty-state");
  const toolsMenu = document.getElementById("alignment-tools-menu");
  const toolsCloseButton = document.getElementById("alignment-tools-close");
  const toolPanels = Array.from(document.querySelectorAll("[data-tool-panel]"));
  const executorInput = document.getElementById("alignment-executor-kind");
  const workdirInput = document.getElementById("alignment-workdir");
  const messageInput = document.getElementById("alignment-message");
  const taskGoalInput = document.getElementById("alignment-task-goal");
  const judgmentDetails = document.getElementById("alignment-judgment-details");
  const alignmentEntryCopyNodes = Array.from(panel.querySelectorAll("[data-alignment-entry-copy]"));
  const alignmentEntryTaskOnlyNodes = Array.from(panel.querySelectorAll("[data-alignment-entry-task-only]"));
  const alignmentEntryHandoffSummary = panel.querySelector("[data-alignment-entry-handoff-summary]");
  const looporaFitReasonInput = document.getElementById("alignment-loopora-fit-reason");
  const directPathCheckInput = document.getElementById("alignment-direct-path-check");
  const fakeDoneRiskInput = document.getElementById("alignment-fake-done-risk");
  const requiredEvidenceInput = document.getElementById("alignment-required-evidence");
  const judgmentTradeoffsInput = document.getElementById("alignment-judgment-tradeoffs");
  const modelInput = document.getElementById("alignment-model");
  const effortInput = document.getElementById("alignment-reasoning-effort");
  const executorModeInputs = Array.from(panel.querySelectorAll("input[name='alignment_executor_mode']"));
  const modeButtons = Array.from(document.querySelectorAll("[data-alignment-mode-choice]"));
  const modeNote = document.getElementById("alignment-executor-mode-note");
  const presetCard = document.getElementById("alignment-preset-card");
  const commandCard = document.getElementById("alignment-command-card");
  const presetState = document.getElementById("alignment-preset-state");
  const commandState = document.getElementById("alignment-command-state");
  const presetBody = document.getElementById("alignment-preset-body");
  const presetEmpty = document.getElementById("alignment-preset-empty");
  const reasoningField = document.getElementById("alignment-reasoning-field");
  const reasoningNote = document.getElementById("alignment-reasoning-note");
  const commandCliInput = document.getElementById("alignment-command-cli");
  const commandCliNote = document.getElementById("alignment-command-cli-note");
  const commandArgsInput = document.getElementById("alignment-command-args");
  const sendButton = document.getElementById("alignment-send-button");
  const newSessionButton = document.getElementById("alignment-new-session-button");
  const composeModeLinks = Array.from(document.querySelectorAll("[data-compose-mode-link]"));
  const errorBox = document.getElementById("alignment-error");
  const recoveryPanel = document.getElementById("alignment-recovery-panel");
  const statusPill = document.getElementById("alignment-status-pill");
  const agentChip = document.getElementById("alignment-agent-chip");
  const executorReadinessNode = document.getElementById("alignment-executor-readiness");
  const workdirChip = document.getElementById("alignment-workdir-chip");
  const chat = document.getElementById("alignment-chat");
  const sessionMeta = document.getElementById("alignment-session-meta");
  const thinkingStatus = document.getElementById("alignment-thinking-status");
  const historyList = document.getElementById("alignment-history-list");
  const tutorialHandoffBridge = document.getElementById("alignment-tutorial-handoff-bridge");
  const agentReviewBridge = document.getElementById("alignment-agent-review-bridge");
  const sourceContextBridge = document.getElementById("alignment-source-context-bridge");
  const agentLaunchGuide = document.getElementById("alignment-agent-launch-guide");
  const transcriptEl = document.getElementById("alignment-transcript");
  const consoleOutput = document.getElementById("alignment-console-output");
  const liveDetails = document.getElementById("alignment-live-details");
  const liveToggle = document.getElementById("alignment-live-toggle");
  const liveSummaryLabel = document.getElementById("alignment-live-summary-label");
  const liveSummaryMeta = document.getElementById("alignment-live-summary-meta");
  const liveBody = document.getElementById("alignment-live-body");
  const cancelButton = document.getElementById("alignment-cancel-button");
  const readyPreview = document.getElementById("alignment-ready-preview");
  const repairGuide = document.getElementById("alignment-repair-guide");
  const reviewGate = document.getElementById("alignment-review-gate");
  const reviewGateCheckbox = document.getElementById("alignment-review-confirm");
  const reviewGateEvidence = document.getElementById("alignment-review-gate-evidence");
  const reviewGateJudgment = document.getElementById("alignment-review-gate-judgment");
  const reviewGateClosure = document.getElementById("alignment-review-gate-closure");
  const reviewGateStatus = document.getElementById("alignment-review-gate-status");
  const readyActions = document.getElementById("alignment-ready-actions");
  const readySaveAction = panel.querySelector('[data-ready-action="save"]');
  const readyRunAction = panel.querySelector('[data-ready-action="run"]');
  const readySaveDescription = document.getElementById("alignment-ready-save-description");
  const readyRunTitle = document.getElementById("alignment-ready-run-title");
  const readyRunDescription = document.getElementById("alignment-ready-run-description");
  const previewTitle = document.getElementById("bundle-preview-title");
  const artifactName = document.getElementById("alignment-artifact-name");
  const readyNote = document.getElementById("alignment-ready-note");
  const artifactRisk = document.getElementById("alignment-artifact-risk");
  const artifactEvidence = document.getElementById("alignment-artifact-evidence");
  const artifactJudgment = document.getElementById("alignment-artifact-judgment");
  const artifactVerdict = document.getElementById("alignment-artifact-verdict");
  const artifactWorkdir = document.getElementById("alignment-artifact-workdir");
  const controlSummary = document.getElementById("alignment-control-summary");
  const judgmentMap = document.getElementById("alignment-judgment-map");
  const diagnosticsStrip = document.getElementById("alignment-diagnostics-strip");
  const artifactSource = document.getElementById("alignment-artifact-source");
  const sourcePathLabel = document.getElementById("alignment-source-path");
  const specPreview = document.getElementById("alignment-spec-preview");
  const roleList = document.getElementById("alignment-role-list");
  const workflowDiagram = document.getElementById("alignment-workflow-diagram");
  const importSaveButton = document.getElementById("alignment-import-save-button");
  const importRunButton = document.getElementById("alignment-import-run-button");
  const revisePreviewButton = document.getElementById("alignment-revise-preview-button");
  const sourceOpenButton = document.getElementById("alignment-source-open-button");
  const sourceSyncButton = document.getElementById("alignment-source-sync-button");
  const workdirContext = document.getElementById("alignment-workdir-context");
  const workdirContextStatus = document.getElementById("alignment-workdir-context-status");
  const workdirContextOptions = document.getElementById("alignment-workdir-context-options");

  const ACTIVE_STATUSES = new Set(["running", "validating", "repairing"]);
  const MISSING_ITEM_LABELS_ZH = {
    loop_fit: "Loopora 适配",
    task_scope: "任务边界",
    success_surface: "完成标准",
    fake_done_risks: "伪完成风险",
    evidence_preferences: "必需证据",
    execution_strategy: "执行策略",
    judgment_tradeoffs: "判断取舍",
    residual_risk_policy: "残余风险",
    local_governance: "本地治理责任",
    role_posture: "角色姿态",
    workflow_shape: "运行流程",
    workdir_facts: "运行目录事实",
  };
  const MISSING_ITEM_LABELS_EN = {
    loop_fit: "Loopora fit",
    task_scope: "Task scope",
    success_surface: "Success criteria",
    fake_done_risks: "Fake-done risks",
    evidence_preferences: "Evidence expectations",
    execution_strategy: "Execution strategy",
    judgment_tradeoffs: "Judgment tradeoffs",
    residual_risk_policy: "Residual risk policy",
    local_governance: "Local governance",
    role_posture: "Role posture",
    workflow_shape: "Workflow shape",
    workdir_facts: "Run directory facts",
  };
  const SESSION_STORAGE_KEY = "loopora:alignment-session:v1";
  const FIT_HANDOFF_STORAGE_KEY = "loopora:tutorial-fit-handoff:v1";
  const FIT_HANDOFF_REQUIRED_INPUT_IDS = ["task", "loopora_fit_reason", "fake_done_risks", "required_evidence", "judgment_tradeoffs"];
  const tutorialFitHref = shell?.dataset.tutorialFitHref || "/tutorial#tutorial-decision-tree-panel";
  const EVENT_TYPES = [
    "alignment_session_created",
    "alignment_source_context_selected",
    "alignment_started",
    "alignment_user_message",
    "alignment_message",
    "alignment_agreement_ready",
    "alignment_agreement_confirmed",
    "alignment_agreement_reopened",
    "alignment_ready_review_started",
    "alignment_stage_blocked",
    "alignment_waiting_user",
    "alignment_bundle_written",
    "alignment_validation_passed",
    "alignment_validation_failed",
    "alignment_repair_started",
    "alignment_ready",
    "alignment_failed",
    "alignment_interrupted",
    "alignment_cancel_requested",
    "alignment_cancelled",
    "alignment_imported",
    "alignment_import_failed",
    "alignment_run_started",
    "alignment_run_start_failed",
    "alignment_bundle_synced",
    "alignment_bundle_sync_failed",
    "codex_event",
    "stream_error",
  ];
  const ALIGNMENT_EVENT_PAGE_LIMIT = 5000;
  let currentSession = null;
  let eventSource = null;
  let latestEventId = 0;
  let submitPending = false;
  let cancelPending = false;
  let tutorialFitHandoffBlocksWebConversation = false;
  let alignmentEntryPhaseState = {phase: "task", knownCount: 0, missingCount: 0};
  let selectedPreviewTab = "review";
  let previewTabSessionId = "";
  let previewSurfaceState = "";
  let readyRevisionOpen = false;
  let errorTimer = null;
  let agentLaunchCopyTimer = null;
  let executorReadinessState = {
    status: "checking",
    blocking: false,
    readiness_kind: "checking",
  };
  let executorReadinessRequestId = 0;
  let executorReadinessTimer = 0;
  const commandDrafts = new Map();
  let lastExecutorKind = executorInput?.value || "codex";
  let workdirContextState = {
    workdir: "",
    options: [],
    requiresChoice: false,
    selectedOptionId: "",
    loaded: false,
  };
  let workdirContextTimer = null;

  function localeText(zh, en) {
    return window.LooporaUI.pickText({zh, en});
  }
  const alignmentConsoleProjector = window.LooporaAlignmentConsole.createAlignmentConsoleProjector({localeText});
  const alignmentHistoryLabels = window.LooporaAlignmentHistory.createAlignmentHistory({localeText});
  const alignmentHistoryController = window.LooporaAlignmentHistory.createAlignmentHistory({
    historyList,
    localeText,
    fetchSessions: () => fetchJson("/api/alignments/sessions?limit=30"),
    emptyStartAction: () => newSessionButton?.click(),
    openSession: (session) => openHistorySession(session.id),
    deleteSession: (session) => deleteHistorySession(session.id),
    currentSessionId: () => currentSession?.id || "",
  });

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function basename(path) {
    const cleaned = String(path || "").replace(/\/+$/, "");
    if (!cleaned) {
      return "";
    }
    return cleaned.split("/").filter(Boolean).pop() || cleaned;
  }

  function profileFor(kind) {
    return profiles.find((profile) => profile.key === kind) || profiles[0] || {};
  }

  function failureRecovery(session = currentSession) {
    return session?.failure_recovery && typeof session.failure_recovery === "object"
      ? session.failure_recovery
      : {};
  }

  function failedSessionHasCandidatePlan(session = currentSession) {
    return failureRecovery(session).kind === "repair_candidate_plan";
  }

  function defaultCommandArgsText(profile) {
    return Array.isArray(profile?.command_args_template) ? profile.command_args_template.join("\n") : "";
  }

  function selectedExecutorMode() {
    const selected = executorModeInputs.find((input) => input.checked);
    return String(selected?.value || "preset") === "command" ? "command" : "preset";
  }

  function setExecutorMode(nextMode) {
    const resolvedMode = String(nextMode || "preset") === "command" ? "command" : "preset";
    executorModeInputs.forEach((input) => {
      input.checked = input.value === resolvedMode;
    });
  }

  function isCommandMode() {
    const profile = profileFor(executorInput.value);
    return selectedExecutorMode() === "command" || Boolean(profile.command_only);
  }

  function setBilingualText(element, zh, en) {
    if (!element) {
      return;
    }
    const zhNode = document.createElement("span");
    zhNode.dataset.lang = "zh";
    zhNode.textContent = String(zh || "");
    const enNode = document.createElement("span");
    enNode.dataset.lang = "en";
    enNode.textContent = String(en || "");
    element.replaceChildren(zhNode, enNode);
  }

  function writeClipboardText(value) {
    return window.LooporaUI.writeTextToClipboard(value);
  }

  function textLooksChinese(value) {
    return /[\u3400-\u9fff]/.test(String(value || ""));
  }

  function compactHandoffText(value) {
    return String(value || "").trim().replace(/\s+/g, " ");
  }

  function renderAlignmentEntryPhase() {
    const {phase, knownCount, missingCount} = alignmentEntryPhaseState;
    panel.dataset.alignmentEntryPhase = phase;
    alignmentEntryCopyNodes.forEach((node) => {
      node.hidden = node.dataset.alignmentEntryCopy !== phase;
    });
    alignmentEntryTaskOnlyNodes.forEach((node) => {
      node.hidden = phase !== "task";
    });
    if (!alignmentEntryHandoffSummary) {
      return;
    }
    alignmentEntryHandoffSummary.hidden = phase === "task";
    alignmentEntryHandoffSummary.dataset.entryPhase = phase;
    alignmentEntryHandoffSummary.dataset.knownCount = String(knownCount);
    alignmentEntryHandoffSummary.dataset.missingCount = String(missingCount);
    if (phase === "task") {
      alignmentEntryHandoffSummary.textContent = "";
      return;
    }
    alignmentEntryHandoffSummary.textContent = phase === "reviewed"
      ? localeText(`${knownCount} 项 Fit Review 判断已带入`, `Fit Review applied · ${knownCount} judgment${knownCount === 1 ? "" : "s"}`)
      : localeText(`已带入 ${knownCount} 项，${missingCount} 项由对话补齐`, `${knownCount} carried · ${missingCount} to clarify`);
  }

  function setAlignmentEntryPhase(phase = "task", {knownCount = 0, missingCount = 0} = {}) {
    alignmentEntryPhaseState = {phase, knownCount, missingCount};
    renderAlignmentEntryPhase();
  }

  function tutorialFitReviewHref(workdir = "") {
    const url = new URL(tutorialFitHref, window.location.origin);
    const targetWorkdir = compactHandoffText(workdir);
    if (targetWorkdir) {
      url.searchParams.set("workdir", targetWorkdir);
    }
    if (!url.hash) {
      url.hash = "tutorial-decision-tree-panel";
    }
    return `${url.pathname}${url.search}${url.hash}`;
  }

  function tutorialHandoffInputLabel(inputId, prefersDirect = false) {
    const labels = {
      task: localeText("任务目标", "Task goal"),
      loopora_fit_reason: localeText("Loopora 适配理由", "Loopora fit reason"),
      direct_path_check: prefersDirect ? localeText("直接路径决策", "Direct-path decision") : localeText("直接路径检查", "Direct-path check"),
      fake_done_risks: localeText("伪完成风险", "Fake-done risk"),
      required_evidence: localeText("必需证据", "Required evidence"),
      judgment_tradeoffs: localeText("判断取舍", "Judgment tradeoffs"),
    };
    return labels[inputId] || String(inputId || "").replaceAll("_", " ");
  }

  function readTutorialFitHandoff() {
    try {
      const raw = window.sessionStorage?.getItem(FIT_HANDOFF_STORAGE_KEY) || "";
      if (!raw) {
        return null;
      }
      const payload = JSON.parse(raw);
      if (payload?.source !== "tutorial_fit_review") {
        return null;
      }
      const inputs = payload?.inputs && typeof payload.inputs === "object" ? payload.inputs : {};
      const hasAnyInput = [...FIT_HANDOFF_REQUIRED_INPUT_IDS, "direct_path_check"]
        .some((inputId) => compactHandoffText(inputs[inputId]));
      const reviewCompletionCommand = String(payload?.review_completion_command || payload?.direct_decision_command || "").trim();
      if (!hasAnyInput && !reviewCompletionCommand) {
        return null;
      }
      const blocksWebConversation = window.LooporaUI.tutorialFitPrefersDirectPath(payload);
      const payloadMissingIds = Array.isArray(payload?.missing_first_task_input_ids)
        ? payload.missing_first_task_input_ids.map((inputId) => String(inputId || "").trim()).filter(Boolean)
        : [];
      const derivedMissingIds = FIT_HANDOFF_REQUIRED_INPUT_IDS.filter((inputId) => !compactHandoffText(inputs[inputId]));
      const missingInputIds = blocksWebConversation ? [] : Array.from(new Set([...payloadMissingIds, ...derivedMissingIds]));
      const setupAllowed = !blocksWebConversation && payload?.setup_allowed !== false && payload?.ready_for_loopora_plan_message !== false;
      const sourceWorkdir = String(payload?.source_workdir || payload?.workdir || "").trim();
      const setupCommandState = window.LooporaUI.tutorialFitSetupCommandState(payload, {missingInputIds, setupAllowed, sourceWorkdir});
      return {
        inputs,
        missingInputIds,
        setupAllowed,
        blocksWebConversation,
        readyForPlan: missingInputIds.length === 0 && setupAllowed,
        setupGateReady: setupCommandState.setupGateReady,
        setupGateBlockers: setupCommandState.setupGateBlockers,
        setupCommandsReady: setupCommandState.setupCommandsReady,
        setupCommandBlockers: setupCommandState.setupCommandBlockers,
        routePreviewExecutable: setupCommandState.routePreviewExecutable,
        routePreviewBlockers: setupCommandState.routePreviewBlockers,
        reviewCompletionCommand,
        draft: String(payload?.draft_first_task_message || "").trim(),
        sourceWorkdir,
      };
    } catch (_) {
      return null;
    }
  }

  function judgmentBriefInputsAreEmpty() {
    return ![
      taskGoalInput,
      looporaFitReasonInput,
      directPathCheckInput,
      fakeDoneRiskInput,
      requiredEvidenceInput,
      judgmentTradeoffsInput,
      messageInput,
    ].some((input) => input?.value.trim());
  }

  function tutorialHandoffMatchesCurrentWorkdir(handoff) {
    const targetWorkdir = workdirInput.value.trim();
    return window.LooporaUI.sameWorkdir(handoff?.sourceWorkdir, targetWorkdir, {
      allowEmptyLeft: !targetWorkdir,
    });
  }

  function tutorialFitHandoffBlocksCurrentWebConversation(handoff) {
    return Boolean(handoff?.blocksWebConversation && tutorialHandoffMatchesCurrentWorkdir(handoff));
  }

  function currentJudgmentBriefMatchesHandoff(handoff) {
    const inputs = handoff?.inputs || {};
    return compactHandoffText(taskGoalInput?.value) === compactHandoffText(inputs.task)
      && compactHandoffText(looporaFitReasonInput?.value) === compactHandoffText(inputs.loopora_fit_reason)
      && compactHandoffText(directPathCheckInput?.value) === compactHandoffText(inputs.direct_path_check)
      && compactHandoffText(fakeDoneRiskInput?.value) === compactHandoffText(inputs.fake_done_risks)
      && compactHandoffText(requiredEvidenceInput?.value) === compactHandoffText(inputs.required_evidence)
      && compactHandoffText(judgmentTradeoffsInput?.value) === compactHandoffText(inputs.judgment_tradeoffs);
  }

  function applyTutorialFitHandoff() {
    if (!taskGoalInput || !looporaFitReasonInput || !directPathCheckInput || !fakeDoneRiskInput || !requiredEvidenceInput || !judgmentTradeoffsInput || !messageInput) {
      return false;
    }
    if (currentSession || !judgmentBriefInputsAreEmpty()) {
      return false;
    }
    const handoff = readTutorialFitHandoff();
    if (!handoff) {
      return false;
    }
    if (handoff.blocksWebConversation || !tutorialHandoffMatchesCurrentWorkdir(handoff)) {
      return false;
    }
    if (handoff.sourceWorkdir && !workdirInput.value.trim()) {
      setDraftWorkdirContext(handoff.sourceWorkdir, {syncUrl: true, renderHandoff: false});
    }
    taskGoalInput.value = compactHandoffText(handoff.inputs.task);
    looporaFitReasonInput.value = compactHandoffText(handoff.inputs.loopora_fit_reason);
    directPathCheckInput.value = compactHandoffText(handoff.inputs.direct_path_check);
    fakeDoneRiskInput.value = compactHandoffText(handoff.inputs.fake_done_risks);
    requiredEvidenceInput.value = compactHandoffText(handoff.inputs.required_evidence);
    judgmentTradeoffsInput.value = compactHandoffText(handoff.inputs.judgment_tradeoffs);
    [taskGoalInput, looporaFitReasonInput, directPathCheckInput, fakeDoneRiskInput, requiredEvidenceInput, judgmentTradeoffsInput].forEach((input) => {
      input.dispatchEvent(new Event("input", {bubbles: true}));
    });
    const knownCount = [...FIT_HANDOFF_REQUIRED_INPUT_IDS, "direct_path_check"]
      .filter((inputId) => compactHandoffText(handoff.inputs[inputId])).length;
    setAlignmentEntryPhase(
      handoff.missingInputIds.length === 0 && handoff.setupAllowed ? "reviewed" : "partial",
      {knownCount, missingCount: handoff.missingInputIds.length},
    );
    if (judgmentDetails) {
      judgmentDetails.open = false;
    }
    return true;
  }

  function clearTutorialFitHandoff() {
    try {
      window.sessionStorage?.removeItem(FIT_HANDOFF_STORAGE_KEY);
    } catch (_) {
      // Best effort only.
    }
    if (tutorialHandoffBridge) {
      tutorialHandoffBridge.hidden = true;
      tutorialHandoffBridge.innerHTML = "";
      tutorialHandoffBridge.classList.remove("is-warning");
    }
    setTutorialFitHandoffBlocksWebConversation(false);
    clearTransientError();
    taskGoalInput?.focus?.();
  }

  function renderTutorialFitHandoffBridge() {
    if (!tutorialHandoffBridge) {
      return false;
    }
    const handoff = readTutorialFitHandoff();
    if (
      !handoff
      || currentSession
      || (
        !handoff.blocksWebConversation
        && currentJudgmentBriefMatchesHandoff(handoff)
        && tutorialHandoffMatchesCurrentWorkdir(handoff)
      )
    ) {
      setTutorialFitHandoffBlocksWebConversation(false);
      tutorialHandoffBridge.hidden = true;
      tutorialHandoffBridge.innerHTML = "";
      tutorialHandoffBridge.classList.remove("is-warning");
      return false;
    }
    const sourceWorkdir = String(handoff.sourceWorkdir || "").trim();
    const currentWorkdir = workdirInput.value.trim();
    const hasWorkdirMismatch = !window.LooporaUI.sameWorkdir(sourceWorkdir, currentWorkdir, {
      allowEmptyLeft: !currentWorkdir,
    });
    const directPathBlocksWebConversation = tutorialFitHandoffBlocksCurrentWebConversation(handoff);
    setTutorialFitHandoffBlocksWebConversation(!currentSession && directPathBlocksWebConversation);
    const hasMissingInputs = !handoff.blocksWebConversation && (handoff.missingInputIds.length > 0 || !handoff.setupAllowed);
    const fieldsAreEmpty = judgmentBriefInputsAreEmpty();
    const canPrefill = !handoff.blocksWebConversation && fieldsAreEmpty && !hasWorkdirMismatch;
    const needsAttention = hasWorkdirMismatch || (!handoff.blocksWebConversation && (hasMissingInputs || !fieldsAreEmpty));
    const title = hasWorkdirMismatch
      ? localeText("Fit Guide 判断属于另一个项目", "Fit Guide judgment belongs to another project")
      : directPathBlocksWebConversation
      ? localeText("已选择直接路径", "Direct path selected")
      : hasMissingInputs
      ? localeText("Fit Guide 草稿可在对话中补齐", "Fit Guide draft can be completed in conversation")
      : localeText("Fit Guide 判断可用于 Web 对话", "Fit Guide judgment is ready for Web conversation");
    const description = hasWorkdirMismatch
      ? localeText(
        "为了避免把任务判断写进错误项目，Loopora 没有自动预填。你可以切回来源项目后再使用这份判断。",
        "Loopora did not prefill because the target project differs. Switch back to the source project before using this review."
      )
      : directPathBlocksWebConversation
      ? localeText(
        "这份 Fit Guide 判断记录的是不用 Loopora 的决定。Web 对话已停用；请走直接 Agent、硬性检查或清除这份决定后重新判断。",
        "This Fit Guide judgment records that Loopora is not needed. Web conversation is disabled; use the direct Agent or hard-check path, or clear this decision and review again."
      )
      : hasMissingInputs
      ? localeText(
        "这份草稿仍有空白项。可以带入已有内容并开始对话，Loopora 会逐项追问；也可以先回 Fit Guide 补齐。",
        "This draft still has blank items. Carry what is known into Web conversation and let Loopora clarify the rest, or finish it in Fit Guide first."
      )
      : localeText(
          "这份判断保存在浏览器会话里，可以预填首轮任务和已有验收判断。",
          "This judgment is stored in this browser session and can prefill the first task plus known acceptance judgment."
        );
    const chips = [...FIT_HANDOFF_REQUIRED_INPUT_IDS, "direct_path_check"]
      .map((inputId) => [inputId, compactHandoffText(handoff.inputs[inputId])])
      .filter(([, value]) => value)
      .map(([inputId, value]) => `
        <span>
          <strong>${escapeHtml(tutorialHandoffInputLabel(inputId, handoff.blocksWebConversation))}</strong>
          ${escapeHtml(value)}
        </span>
      `)
      .join("");
    const missingLine = hasMissingInputs
      ? `<span>${escapeHtml(localeText("缺少", "Missing"))}: ${escapeHtml(handoff.missingInputIds.map(tutorialHandoffInputLabel).join(", ") || "-")}</span>`
      : "";
    const setupCommandLine = handoff.setupGateReady
      ? `<span>${escapeHtml(localeText("设置命令", "Setup commands"))}: ${escapeHtml(localeText("同一 Agent 设置命令可复制", "Same-Agent setup commands are copyable"))}</span>`
      : handoff.setupGateBlockers.includes("prefer_direct_path")
        ? directPathBlocksWebConversation
          ? `<span>${escapeHtml(localeText("设置命令", "Setup commands"))}: ${escapeHtml(localeText("直接路径决策已阻止 Loopora 设置", "Direct-path decision blocks Loopora setup"))}</span>`
          : `<span>${escapeHtml(localeText("设置命令", "Setup commands"))}: ${escapeHtml(localeText("直接路径决策属于来源项目", "Direct-path decision belongs to the source project"))}</span>`
      : handoff.setupGateBlockers.includes("target_project_required")
        ? `<span>${escapeHtml(localeText("设置命令", "Setup commands"))}: ${escapeHtml(localeText("先选择目标项目", "choose a target project first"))}</span>`
        : "";
    const sourceLine = sourceWorkdir
      ? `<span>${escapeHtml(localeText("来源目录", "Source"))}: ${escapeHtml(sourceWorkdir)}</span>`
      : "";
    const currentLine = currentWorkdir
      ? `<span>${escapeHtml(localeText("当前目录", "Current"))}: ${escapeHtml(currentWorkdir)}</span>`
      : "";
    const useSourceButton = sourceWorkdir && hasWorkdirMismatch
      ? `
        <button class="secondary-button" type="button" data-tutorial-handoff-use-source data-testid="alignment-tutorial-handoff-use-source">
          <span>${escapeHtml(localeText("切回来源项目", "Use source project"))}</span>
        </button>
      `
      : "";
    const finishReviewLink = hasMissingInputs
      ? `
        <a class="secondary-button is-primary-recovery" href="${escapeHtml(tutorialFitReviewHref(sourceWorkdir))}" data-tutorial-handoff-finish data-testid="alignment-tutorial-handoff-finish-link">
          <span>${escapeHtml(localeText("补齐适配性判断", "Finish Fit Review"))}</span>
        </a>
      `
      : "";
    const prefillButton = canPrefill
      ? `
        <button class="primary-button" type="button" data-tutorial-handoff-prefill data-testid="alignment-tutorial-handoff-prefill">
          <span>${escapeHtml(localeText("预填 Web 对话", "Prefill Web conversation"))}</span>
        </button>
      `
      : "";
    const completionButton = handoff.reviewCompletionCommand
      ? `
        <button class="ghost-button" type="button" data-tutorial-handoff-copy-completion="${escapeHtml(handoff.reviewCompletionCommand)}" data-testid="alignment-tutorial-handoff-copy-completion">
          <span>${escapeHtml(handoff.blocksWebConversation ? localeText("复制直接路径命令", "Copy direct-path command") : localeText("复制补完命令", "Copy completion command"))}</span>
        </button>
      `
      : "";
    const draftButton = handoff.draft
      ? `
        <button class="ghost-button" type="button" data-tutorial-handoff-copy-draft="${escapeHtml(handoff.draft)}" data-testid="alignment-tutorial-handoff-copy-draft">
          <span>${escapeHtml(localeText("复制 Fit Guide 草稿", "Copy Fit Guide draft"))}</span>
        </button>
      `
      : "";
    tutorialHandoffBridge.hidden = false;
    tutorialHandoffBridge.classList.toggle("is-warning", needsAttention);
    tutorialHandoffBridge.innerHTML = `
      <div class="alignment-source-context-copy">
        <span class="alignment-source-context-kicker">${escapeHtml(localeText("Fit Guide 判断草稿", "Fit Guide review draft"))}</span>
        <h3>${escapeHtml(title)}</h3>
        <p>${escapeHtml(description)}</p>
        <div class="alignment-source-context-metrics" data-testid="alignment-tutorial-handoff-meta">
          ${sourceLine}
          ${currentLine}
          ${missingLine}
          ${setupCommandLine}
        </div>
      </div>
      <div class="alignment-tutorial-handoff-summary" data-testid="alignment-tutorial-handoff-inputs">${chips}</div>
      <div class="alignment-agent-review-actions">
        ${prefillButton}
        ${finishReviewLink}
        ${useSourceButton}
        ${draftButton}
        ${completionButton}
        <button class="ghost-button" type="button" data-tutorial-handoff-clear data-testid="alignment-tutorial-handoff-clear">
          <span>${escapeHtml(localeText("清除草稿", "Clear draft"))}</span>
        </button>
      </div>
      <div class="agent-readiness-public-report" data-tutorial-handoff-manual-copy data-testid="alignment-tutorial-handoff-manual-copy" hidden></div>
    `;
    tutorialHandoffBridge.querySelector("[data-tutorial-handoff-use-source]")?.addEventListener("click", () => {
      if (sourceWorkdir) {
        setDraftWorkdirContext(sourceWorkdir, {syncUrl: true});
      }
    });
    tutorialHandoffBridge.querySelector("[data-tutorial-handoff-prefill]")?.addEventListener("click", () => {
      if (sourceWorkdir) {
        setDraftWorkdirContext(sourceWorkdir, {syncUrl: true, renderHandoff: false});
      }
      if (applyTutorialFitHandoff()) {
        tutorialHandoffBridge.hidden = true;
        tutorialHandoffBridge.innerHTML = "";
        taskGoalInput.focus();
      } else {
        renderTutorialFitHandoffBridge();
      }
    });
    tutorialHandoffBridge.querySelector("[data-tutorial-handoff-copy-completion]")?.addEventListener("click", async (event) => {
      const command = event.currentTarget?.dataset.tutorialHandoffCopyCompletion || "";
      if (!command) {
        return;
      }
      renderTutorialHandoffManualCopy("");
      try {
        await writeClipboardText(command);
        showTutorialHandoffCopyFeedback(localeText("命令已复制。", "Command copied."), "success");
      } catch (_) {
        renderTutorialHandoffManualCopy(
          command,
          handoff.blocksWebConversation
            ? localeText("手动复制直接路径命令", "Manual direct-path command copy")
            : localeText("手动复制补完命令", "Manual completion command copy"),
        );
        showTutorialHandoffCopyFeedback(
          localeText("浏览器未允许自动复制；请手动复制下面的命令。", "The browser blocked automatic copy; copy the command below manually."),
          "warning",
        );
      }
    });
    tutorialHandoffBridge.querySelector("[data-tutorial-handoff-copy-draft]")?.addEventListener("click", async (event) => {
      const draft = event.currentTarget?.dataset.tutorialHandoffCopyDraft || "";
      if (!draft) {
        return;
      }
      renderTutorialHandoffManualCopy("");
      try {
        await writeClipboardText(draft);
        showTutorialHandoffCopyFeedback(localeText("Fit Guide 草稿已复制。", "Fit Guide draft copied."), "success");
      } catch (_) {
        renderTutorialHandoffManualCopy(draft, localeText("手动复制 Fit Guide 草稿", "Manual Fit Guide draft copy"));
        showTutorialHandoffCopyFeedback(
          localeText("浏览器未允许自动复制；请手动复制下面的 Fit Guide 草稿。", "The browser blocked automatic copy; copy the Fit Guide draft below manually."),
          "warning",
        );
      }
    });
    tutorialHandoffBridge.querySelector("[data-tutorial-handoff-clear]")?.addEventListener("click", clearTutorialFitHandoff);
    return true;
  }

  function showTutorialHandoffCopyFeedback(message, kind = "warning") {
    if (typeof window.LooporaUI?.showAppFeedback === "function") {
      window.LooporaUI.showAppFeedback(message, kind);
      return;
    }
    showError(message);
  }

  function renderTutorialHandoffManualCopy(value, label = "") {
    const container = tutorialHandoffBridge?.querySelector?.("[data-tutorial-handoff-manual-copy]");
    window.LooporaUI?.renderManualCopy?.(container, value, {
      label: label || localeText("手动复制 Fit Guide 交接内容", "Manual Fit Guide handoff copy"),
      textareaId: "alignment-tutorial-handoff-manual-copy-textarea",
    });
  }

  function collectJudgmentBrief() {
    return {
      taskGoal: taskGoalInput?.value.trim() || "",
      looporaFitReason: looporaFitReasonInput?.value.trim() || "",
      directPathCheck: directPathCheckInput?.value.trim() || "",
      fakeDoneRisk: fakeDoneRiskInput?.value.trim() || "",
      requiredEvidence: requiredEvidenceInput?.value.trim() || "",
      judgmentTradeoffs: judgmentTradeoffsInput?.value.trim() || "",
    };
  }

  function requiredJudgmentInputs() {
    return [taskGoalInput].filter(Boolean);
  }

  function missingJudgmentFields(brief = collectJudgmentBrief()) {
    const candidates = [[taskGoalInput, brief.taskGoal]];
    return candidates.filter(([input, value]) => input && !value).map(([input]) => input);
  }

  function setJudgmentValidationState(missingInputs = []) {
    const missing = new Set(missingInputs.filter(Boolean));
    requiredJudgmentInputs().forEach((input) => {
      if (missing.has(input)) {
        input.setAttribute("aria-invalid", "true");
        return;
      }
      input.removeAttribute("aria-invalid");
    });
  }

  function judgmentBriefHasAnyValue(brief = collectJudgmentBrief()) {
    return Boolean(
      brief.taskGoal || brief.looporaFitReason || brief.directPathCheck || brief.fakeDoneRisk || brief.requiredEvidence || brief.judgmentTradeoffs
    );
  }

  function composeJudgmentMessage(additionalMessage = messageInput.value.trim()) {
    const brief = collectJudgmentBrief();
    const joined = [
      brief.taskGoal,
      brief.looporaFitReason,
      brief.directPathCheck,
      brief.fakeDoneRisk,
      brief.requiredEvidence,
      brief.judgmentTradeoffs,
      additionalMessage,
    ].join("\n");
    const labels = textLooksChinese(joined) || window.LooporaUI.currentLocale() === "zh"
      ? {
          taskGoal: "任务目标",
          looporaFitReason: "Loopora 适配",
          directPathCheck: "直接路径检查",
          fakeDoneRisk: "伪完成风险",
          requiredEvidence: "必需证据",
          judgmentTradeoffs: "判断取舍",
          additionalContext: "补充上下文",
        }
      : {
          taskGoal: "Task goal",
          looporaFitReason: "Loopora fit",
          directPathCheck: "Direct-path check",
          fakeDoneRisk: "Fake-done risk",
          requiredEvidence: "Required evidence",
          judgmentTradeoffs: "Judgment tradeoffs",
          additionalContext: "Additional context",
        };
    const fields = [
      [labels.taskGoal, brief.taskGoal],
      [labels.looporaFitReason, brief.looporaFitReason],
      [labels.directPathCheck, brief.directPathCheck],
      [labels.fakeDoneRisk, brief.fakeDoneRisk],
      [labels.requiredEvidence, brief.requiredEvidence],
      [labels.judgmentTradeoffs, brief.judgmentTradeoffs],
    ];
    const populatedFields = fields.filter(([, value]) => value);
    if (populatedFields.length === 1 && populatedFields[0][0] === labels.taskGoal && !additionalMessage) {
      return brief.taskGoal;
    }
    const parts = populatedFields.map(([label, value]) => `${label}:\n${value}`);
    if (additionalMessage) {
      parts.push(`${labels.additionalContext}:\n${additionalMessage}`);
    }
    return parts.join("\n\n");
  }

  function clearJudgmentBriefInputs() {
    [taskGoalInput, looporaFitReasonInput, directPathCheckInput, fakeDoneRiskInput, requiredEvidenceInput, judgmentTradeoffsInput].forEach((input) => {
      if (input) {
        input.value = "";
      }
    });
  }

  function showError(message, options = {}) {
    const autoHide = options.autoHide !== false;
    if (errorTimer) {
      clearTimeout(errorTimer);
      errorTimer = null;
    }
    if (!message) {
      errorBox.hidden = true;
      errorBox.textContent = "";
      setJudgmentValidationState();
      return;
    }
    errorBox.hidden = false;
    errorBox.textContent = message;
    if (autoHide) {
      errorTimer = window.setTimeout(() => showError(""), 7000);
    }
  }

  function clearRecoveryPanel() {
    if (!recoveryPanel) {
      return;
    }
    recoveryPanel.hidden = true;
    recoveryPanel.innerHTML = "";
  }

  function clearTransientError() {
    showError("");
    clearRecoveryPanel();
  }

  function directPathWebStartBlockedMessage() {
    return localeText(
      "已选择直接路径，不能启动 Web 对话。请复制直接路径命令，或清除这份决定后重新判断。",
      "Direct path is selected, so Web conversation cannot start. Copy the direct-path command, or clear this decision and review again.",
    );
  }

  function setDirectPathWebStartControlEnabled(control, enabled) {
    window.LooporaUI.setNavigationControlBlocked(control, !enabled, {
      markerDataset: "directPathBlocked",
      baseHrefDataset: "directPathBaseHref",
      disabledHrefDataset: "directPathDisabledHref",
      baseDisabledDataset: "directPathBaseDisabled",
    });
  }

  function syncDirectPathWebStartControls() {
    const enabled = !tutorialFitHandoffBlocksWebConversation;
    for (const control of [...composeModeLinks, newSessionButton].filter(Boolean)) {
      setDirectPathWebStartControlEnabled(control, enabled);
    }
  }

  function setTutorialFitHandoffBlocksWebConversation(blocked) {
    tutorialFitHandoffBlocksWebConversation = Boolean(blocked);
    syncDirectPathWebStartControls();
    setSendButtonState();
  }

  function renderAlignmentRecovery(payload, {testid = "alignment-workdir-recovery", title = ""} = {}) {
    if (!recoveryPanel || !payload || !Array.isArray(payload.next_actions) || !payload.next_actions.length) {
      clearRecoveryPanel();
      return;
    }
    recoveryPanel.setAttribute("data-testid", testid);
    recoveryPanel.innerHTML = window.LooporaUI.recoveryPanelHtml(payload, {
      testid,
      title: title || localeText("需要先修复运行目录", "Fix the run directory first"),
      actionControlHtml: alignmentRecoveryActionControlHtml,
    });
    recoveryPanel.hidden = false;
    window.LooporaUI?.bindRecoveryCommandCopy?.();
    bindAlignmentRecoveryActions();
  }

  function alignmentRecoveryActionKind(action) {
    return String(action?.kind || "").trim();
  }

  function alignmentRecoveryActionControlHtml(action) {
    const actionKind = alignmentRecoveryActionKind(action);
    if (![
      "review_alignment_source_context",
      "retry_alignment_session_create",
      "sync_alignment_bundle",
      "retry_alignment_bundle_preview",
      "retry_alignment_import",
    ].includes(actionKind)) {
      return "";
    }
    const label = window.LooporaUI?.recoveryActionLabel?.(action) || actionKind.replaceAll("_", " ");
    return `<button class="ghost-button" type="button" data-alignment-recovery-action="${escapeHtml(actionKind)}">${escapeHtml(label)}</button>`;
  }

  function setAlignmentRecoveryActionButtonsDisabled(disabled) {
    recoveryPanel?.querySelectorAll("[data-alignment-recovery-action]")?.forEach((button) => {
      button.disabled = disabled;
    });
  }

  function bindAlignmentRecoveryActions() {
    recoveryPanel?.querySelectorAll("[data-alignment-recovery-action]")?.forEach((button) => {
      if (button.dataset.boundAlignmentRecoveryAction === "1") {
        return;
      }
      button.dataset.boundAlignmentRecoveryAction = "1";
      button.addEventListener("click", async () => {
        const actionKind = String(button.dataset.alignmentRecoveryAction || "").trim();
        setAlignmentRecoveryActionButtonsDisabled(true);
        try {
          if (actionKind === "review_alignment_source_context") {
            await reviewAlignmentSourceContextFromRecovery();
          } else if (actionKind === "retry_alignment_session_create") {
            retryAlignmentSessionCreateFromRecovery();
          } else if (actionKind === "sync_alignment_bundle") {
            await syncReadyBundle();
          } else if (actionKind === "retry_alignment_bundle_preview") {
            await loadReadyBundle({reveal: true});
          } else if (actionKind === "retry_alignment_import") {
            await importReadyBundle({startImmediately: true});
          }
        } catch (error) {
          renderRecoveryFromError(error, alignmentRecoveryActionErrorOptions(actionKind));
          showError(error.message || localeText("修复动作失败。", "Recovery action failed."));
        } finally {
          setAlignmentRecoveryActionButtonsDisabled(false);
        }
      });
    });
  }

  function alignmentRecoveryActionErrorOptions(actionKind) {
    if (actionKind === "review_alignment_source_context") {
      return {testid: "alignment-workdir-context-recovery"};
    }
    if (actionKind === "retry_alignment_session_create") {
      return {testid: "alignment-session-start-recovery"};
    }
    if (actionKind === "sync_alignment_bundle") {
      return {
        testid: "alignment-sync-recovery",
        title: localeText("先修复 Plan File 后再同步", "Fix the Plan File before syncing again"),
      };
    }
    if (actionKind === "retry_alignment_bundle_preview") {
      return {
        testid: "alignment-preview-recovery",
        title: localeText("先修复 Plan File 后再预览", "Fix the Plan File before previewing again"),
      };
    }
    return {
      testid: "alignment-import-recovery",
      title: localeText("先修复 Plan File 后再重试", "Fix the Plan File before retrying"),
    };
  }

  async function reviewAlignmentSourceContextFromRecovery() {
    openTools("workdir");
    await loadWorkdirContext({force: true});
    workdirContext?.scrollIntoView?.({block: "nearest", behavior: "smooth"});
  }

  function retryAlignmentSessionCreateFromRecovery() {
    clearTransientError();
    if (typeof startForm.requestSubmit === "function") {
      startForm.requestSubmit();
      return;
    }
    startForm.dispatchEvent(new Event("submit", {bubbles: true, cancelable: true}));
  }

  function renderRecoveryFromError(error, options = {}) {
    const payload = error?.payload || {};
    if (payload && Array.isArray(payload.next_actions)) {
      renderAlignmentRecovery(payload, options);
      return true;
    }
    clearRecoveryPanel();
    return false;
  }

  function statusLabel(status, stage = "") {
    return alignmentHistoryLabels.statusLabel(status, stage);
  }

  function projectedSessionStatus(session = currentSession) {
    return String(session?.status_label || session?.status || "idle");
  }

  function renderSessionStatus(session = currentSession) {
    const status = projectedSessionStatus(session);
    const kind = ["ready", "failed", "cancelled", "interrupted"].includes(status) ? status : "";
    shell?.classList.toggle("is-cancelled-recovery", status === "cancelled");
    shell?.classList.toggle("is-interrupted-recovery", status === "interrupted");
    if (status !== "cancelled") {
      shell?.classList.remove("is-cancelled-reply");
    }
    setStatus(statusLabel(status, session?.alignment_stage), kind, status);
    return status;
  }

  function isActiveStatus(status) {
    return ACTIVE_STATUSES.has(String(status || ""));
  }

  function activeStatusCopy(status) {
    const labels = {
      running: {
        label: localeText("Agent 正在执行", "Agent running"),
        meta: localeText(`${executorLabel()} 正在处理`, `${executorLabel()} is working`),
      },
      validating: {
        label: localeText("正在校验 Loop", "Validating Loop"),
        meta: localeText("检查方案契约与运行面", "Checking plan contract and runtime surface"),
      },
      repairing: {
        label: localeText("正在自动修复", "Repairing plan"),
        meta: localeText("根据校验结果修复", "Repairing from validation results"),
      },
    };
    return labels[String(status || "")] || {
      label: statusLabel(status),
      meta: "",
    };
  }

  function setSendButtonState(status = currentSession?.status || "idle") {
    const active = isActiveStatus(status);
    const starting = !active && !currentSession;
    sendButton.disabled = submitPending
      || cancelPending
      || (!active && tutorialFitHandoffBlocksWebConversation)
      || (!active && executorReadinessState.blocking === true);
    sendButton.classList.toggle("is-stop", active);
    sendButton.dataset.action = active ? "cancel" : "send";
    sendButton.textContent = active ? "■" : (starting ? localeText("开始对话", "Start conversation") : "↑");
    sendButton.setAttribute("aria-label", active
      ? localeText("停止执行", "Stop execution")
      : starting
      ? localeText("开始对话", "Start conversation")
      : localeText("发送", "Send"));
    sendButton.setAttribute("aria-busy", String(submitPending || cancelPending || active));
  }

  function setLiveSummaryStatus(status = currentSession?.status || "idle") {
    if (!liveToggle || !liveSummaryLabel || !liveSummaryMeta) {
      return;
    }
    const active = isActiveStatus(status);
    liveToggle.classList.toggle("is-active", active);
    liveToggle.dataset.status = status;
    liveSummaryLabel.textContent = localeText("执行详情", "Execution details");
    liveSummaryMeta.textContent = active
      ? localeText("实时事件流", "Live event stream")
      : (latestEventId ? localeText(`最近事件 #${latestEventId}`, `Latest event #${latestEventId}`) : "");
  }

  function setExecutionState(status = currentSession?.status || "idle") {
    const normalized = String(status || "idle");
    [panel, shell, startForm, chat, liveDetails].forEach((element) => {
      if (!element) {
        return;
      }
      element.dataset.alignmentExecutionState = normalized;
      element.classList.toggle("is-executing", isActiveStatus(normalized));
    });
    cancelButton.hidden = !isActiveStatus(normalized);
    cancelButton.disabled = cancelPending;
    setSendButtonState(normalized);
    setLiveSummaryStatus(normalized);
  }

  function setBusy(isBusy) {
    submitPending = Boolean(isBusy) && !isActiveStatus(currentSession?.status || "");
    setExecutionState();
  }

  function setStatus(message, kind = "", status = "") {
    statusPill.textContent = message;
    const normalized = String(status || kind || currentSession?.status || "");
    statusPill.className = `alignment-status-pill${kind ? ` is-${kind}` : ""}`;
    statusPill.classList.toggle("is-active", isActiveStatus(normalized));
    statusPill.dataset.status = normalized || "idle";
    statusPill.disabled = false;
    statusPill.setAttribute("aria-disabled", String(kind !== "ready"));
    statusPill.setAttribute("aria-pressed", "false");
  }

  function executorLabel(session = currentSession) {
    const profile = profileFor(session?.executor_kind || executorInput.value || "codex");
    return localeText(profile.label_zh || profile.label || "Agent", profile.label || profile.label_zh || "Agent");
  }

  function updateChips() {
    const profile = profileFor(executorInput.value || "codex");
    agentChip.textContent = executorLabel();
    const currentWorkdir = currentSession?.workdir || workdirInput.value.trim();
    workdirChip.textContent = currentWorkdir
      ? basename(currentWorkdir)
      : localeText("选择运行目录", "Choose run directory");
    workdirChip.title = currentWorkdir || "";
    if (profile.command_only || isCommandMode()) {
      agentChip.textContent = `${agentChip.textContent} · ${localeText("自定义命令", "Custom")}`;
    }
    applyExecutorReadinessToChip();
  }

  function syncWorkdirInputFromSession() {
    const sessionWorkdir = String(currentSession?.workdir || "").trim();
    if (!sessionWorkdir) {
      return;
    }
    workdirInput.value = sessionWorkdir;
    updateChips();
    syncAlignmentWorkdirContext();
  }

  function syncAlignmentWorkdirContext({syncUrl = false} = {}) {
    const value = workdirInput?.value.trim() || "";
    if (!window.LooporaUI.syncWorkdirContext) {
      return;
    }
    window.LooporaUI.syncWorkdirContext(value, {syncUrl});
  }

  function setDraftWorkdirContext(workdir, {syncUrl = false, renderHandoff = true} = {}) {
    const value = String(workdir || "").trim();
    if (!value || !workdirInput) {
      return;
    }
    workdirInput.value = value;
    workdirContextState = {
      workdir: value,
      options: [],
      requiresChoice: false,
      selectedOptionId: "",
      loaded: false,
    };
    updateChips();
    renderWorkdirContext();
    scheduleWorkdirContextLoad();
    syncAlignmentWorkdirContext({syncUrl});
    if (renderHandoff) {
      renderTutorialFitHandoffBridge();
    }
  }

  function syncAlignmentDraftFromGlobalWorkdir(event) {
    if (currentSession || !workdirInput) {
      return;
    }
    const nextWorkdir = String(event?.detail?.workdir || "").trim();
    if (workdirInput.value.trim() === nextWorkdir) {
      return;
    }
    workdirInput.value = nextWorkdir;
    workdirContextState = {
      workdir: nextWorkdir,
      options: [],
      requiresChoice: false,
      selectedOptionId: "",
      loaded: false,
    };
    updateChips();
    renderWorkdirContext();
    scheduleWorkdirContextLoad();
    renderTutorialFitHandoffBridge();
  }

  function setToolControlsExpanded(panelName = "") {
    document.querySelectorAll("[data-open-panel][aria-expanded]").forEach((button) => {
      button.setAttribute("aria-expanded", String(!toolsMenu.hidden && button.dataset.openPanel === panelName));
    });
    document.querySelectorAll(".alignment-tool-tabs [data-open-panel]").forEach((button) => {
      const active = button.dataset.openPanel === panelName;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
  }

  function openTools(panelName = "workdir") {
    if (panelName === "workdir") {
      syncWorkdirInputFromSession();
      loadWorkdirContext().catch(() => {});
    }
    toolsMenu.hidden = false;
    toolsMenu.dataset.activePanel = panelName;
    toolPanels.forEach((section) => {
      section.hidden = section.dataset.toolPanel !== panelName;
    });
    setToolControlsExpanded(panelName);
    const firstFocusable = toolsMenu.querySelector(`[data-tool-panel="${panelName}"] input, [data-tool-panel="${panelName}"] textarea, [data-tool-panel="${panelName}"] select, [data-tool-panel="${panelName}"] button`);
    firstFocusable?.focus();
  }

  function closeTools() {
    toolsMenu.hidden = true;
    toolsMenu.dataset.activePanel = "";
    setToolControlsExpanded("");
  }

  function setLiveDetailsOpen(open) {
    if (!liveDetails || !liveToggle || !liveBody) {
      return;
    }
    liveDetails.classList.toggle("is-open", open);
    liveToggle.setAttribute("aria-expanded", String(open));
    liveBody.hidden = !open;
  }

  function resetToEmptyConversation() {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    currentSession = null;
    latestEventId = 0;
    submitPending = false;
    cancelPending = false;
    selectedPreviewTab = "review";
    previewTabSessionId = "";
    previewSurfaceState = "";
    readyRevisionOpen = false;
    workdirContextState = {workdir: "", options: [], requiresChoice: false, selectedOptionId: "", loaded: false};
    forgetSession();
    closeTools();
    renderWorkdirContext();
    setLiveDetailsOpen(false);
    consoleOutput.innerHTML = "";
    if (agentReviewBridge) {
      agentReviewBridge.hidden = true;
      agentReviewBridge.innerHTML = "";
    }
    if (sourceContextBridge) {
      sourceContextBridge.hidden = true;
      sourceContextBridge.innerHTML = "";
    }
    if (tutorialHandoffBridge) {
      tutorialHandoffBridge.hidden = true;
      tutorialHandoffBridge.innerHTML = "";
      tutorialHandoffBridge.classList.remove("is-warning");
    }
    transcriptEl.innerHTML = "";
    readyPreview.hidden = true;
    if (readyActions) {
      readyActions.hidden = true;
    }
    resetReadyReviewGate();
    chat.hidden = true;
    scrollRegion?.scrollTo({top: 0});
    if (liveDetails) {
      liveDetails.hidden = true;
    }
    if (sourceOpenButton) {
      sourceOpenButton.hidden = true;
      sourceOpenButton.dataset.sourcePath = "";
    }
    if (sourceSyncButton) {
      sourceSyncButton.hidden = true;
    }
    if (artifactSource) {
      artifactSource.hidden = true;
    }
    if (sourcePathLabel) {
      sourcePathLabel.textContent = "";
    }
    renderJudgmentMap({}, []);
    emptyState.hidden = false;
    shell?.classList.remove("has-session", "has-artifact");
    shell?.classList.remove("is-ready-review", "is-ready-revision");
    setStatus(localeText("未开始", "Idle"));
    syncActiveExecutionCopy("");
    updateChips();
    setBusy(false);
    clearTransientError();
    messageInput.value = "";
    clearJudgmentBriefInputs();
    if (judgmentDetails) {
      judgmentDetails.open = false;
    }
    setAlignmentEntryPhase("task");
  }

  function renderEffortOptions(profile, currentValue = "") {
    effortInput.innerHTML = "";
    const options = Array.isArray(profile.effort_options) && profile.effort_options.length
      ? profile.effort_options
      : [""];
    options.forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value || localeText("默认", "Default");
      effortInput.append(option);
    });
    const fallback = profile.effort_default || "";
    effortInput.value = options.includes(currentValue) ? currentValue : fallback;
  }

  function saveCommandDraft(profileKey = lastExecutorKind) {
    if (!profileKey || !commandCliInput || !commandArgsInput) {
      return;
    }
    commandDrafts.set(profileKey, {
      cli: commandCliInput.value || "",
      args: commandArgsInput.value || "",
    });
  }

  function loadCommandDraft(profile) {
    if (!profile || !commandCliInput || !commandArgsInput) {
      return;
    }
    const saved = commandDrafts.get(profile.key);
    if (saved) {
      commandCliInput.value = saved.cli || profile.cli_name || "";
      commandArgsInput.value = saved.args || defaultCommandArgsText(profile);
      return;
    }
    commandCliInput.value = commandCliInput.value.trim() && commandCliInput.dataset.autofilled !== "true"
      ? commandCliInput.value
      : profile.cli_name || "";
    commandCliInput.dataset.autofilled = "true";
    commandArgsInput.value = commandArgsInput.value.trim() && commandArgsInput.dataset.autofilled !== "true"
      ? commandArgsInput.value
      : defaultCommandArgsText(profile);
    commandArgsInput.dataset.autofilled = "true";
  }

  function updateModeButtons(profile, commandMode) {
    modeButtons.forEach((chip) => {
      const mode = chip.dataset.alignmentModeChoice || "";
      const input = chip.querySelector("input[name='alignment_executor_mode']");
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

  function updateCommandInputs(profile, commandMode) {
    if (commandMode) {
      loadCommandDraft(profile);
      commandCliInput.readOnly = false;
      commandArgsInput.readOnly = false;
      return;
    }
    commandCliInput.value = profile.cli_name || "";
    commandArgsInput.value = defaultCommandArgsText(profile);
    commandCliInput.readOnly = true;
    commandArgsInput.readOnly = true;
  }

  function updateExecutorControls(options = {}) {
    const profile = profileFor(executorInput.value);
    if (profile.command_only && selectedExecutorMode() !== "command") {
      setExecutorMode("command");
    }
    const commandMode = isCommandMode();
    const preserveUserModel = options.preserveUserModel !== false;
    const preserveUserEffort = options.preserveUserEffort !== false;
    const previousModelDefault = modelInput.dataset.defaultModel || "";
    const previousEffortDefault = effortInput.dataset.defaultEffort || "";
    const currentModel = modelInput.value.trim();
    const currentEffort = effortInput.value.trim();
    const modelWasDefault = !currentModel || currentModel === previousModelDefault;
    const effortWasDefault = !currentEffort || currentEffort === previousEffortDefault;

    modelInput.placeholder = profile.model_placeholder_zh || profile.model_placeholder_en || profile.default_model || "";
    if ((!preserveUserModel || modelWasDefault) && profile.default_model !== undefined) {
      modelInput.value = profile.default_model || "";
    }
    modelInput.dataset.defaultModel = profile.default_model || "";
    renderEffortOptions(profile, (!preserveUserEffort || effortWasDefault) ? (profile.effort_default || "") : currentEffort);
    effortInput.dataset.defaultEffort = profile.effort_default || "";

    presetCard?.classList.toggle("is-active", !commandMode && !profile.command_only);
    presetCard?.classList.toggle("is-inactive", commandMode || profile.command_only);
    commandCard?.classList.toggle("is-active", commandMode);
    commandCard?.classList.toggle("is-inactive", !commandMode);
    if (presetState) {
      presetState.hidden = commandMode || profile.command_only;
    }
    if (commandState) {
      commandState.hidden = !commandMode;
    }
    if (presetBody) {
      presetBody.hidden = Boolean(profile.command_only);
    }
    if (presetEmpty) {
      presetEmpty.hidden = !profile.command_only;
    }
    if (reasoningField) {
      reasoningField.hidden = Boolean(profile.command_only);
    }
    modelInput.readOnly = commandMode;
    effortInput.disabled = commandMode || Boolean(profile.command_only);

    updateModeButtons(profile, commandMode);
    updateCommandInputs(profile, commandMode);
    setBilingualText(
      modeNote,
      profile.command_only
        ? "自定义命令完全由 CLI 模板决定，不会额外套模型或推理强度。"
        : (commandMode
          ? "现在由自定义命令接管。模型和推理强度只作为灰掉的参考，不会单独传入。"
          : "现在由预设模式接管。Loopora 会按所选工具自动拼出 Agent 调用。"),
      profile.command_only
        ? "Custom command is governed entirely by the CLI template; no separate model or reasoning setting is applied."
        : (commandMode
          ? "Custom command now owns the run. Model and reasoning are disabled references and are not submitted separately."
          : "Preset mode now owns the run. Loopora assembles the Agent invocation for the selected tool."),
    );
    setBilingualText(
      commandCliNote,
      profile.command_only
        ? "这里填你自己的命令入口。"
        : "切到自定义命令后，这里就是最终会执行的可执行文件。",
      profile.command_only
        ? "Put your own command executable here."
        : "Once custom command mode is active, this is the executable Loopora will run.",
    );
    setBilingualText(
      reasoningNote,
      profile.key === "opencode"
        ? "OpenCode 默认不填推理强度；需要变体时再选择。"
        : "留空时使用该工具的默认推理设置。",
      profile.key === "opencode"
        ? "OpenCode defaults to blank reasoning effort; choose a variant only when needed."
        : "Leave blank to use the tool's default reasoning setting.",
    );
    updateChips();
    window.LooporaUI.applyLocalizedAttributes(document);
  }

  function syncExecutorControlsFromSession(session) {
    const sessionKind = String(session?.executor_kind || "").trim();
    if (!sessionKind || !profiles.some((profile) => profile.key === sessionKind)) {
      return;
    }
    executorInput.value = sessionKind;
    lastExecutorKind = sessionKind;
    const mode = String(session?.executor_mode || "preset") === "command" ? "command" : "preset";
    setExecutorMode(mode);
    if (mode === "command") {
      commandDrafts.set(sessionKind, {
        cli: String(session?.command_cli || ""),
        args: String(session?.command_args_text || ""),
      });
    }
    updateExecutorControls({preserveUserModel: false, preserveUserEffort: false});
    if (mode === "command") {
      commandCliInput.value = String(session?.command_cli || "");
      commandArgsInput.value = String(session?.command_args_text || "");
    } else {
      modelInput.value = String(session?.model || "");
      renderEffortOptions(profileFor(sessionKind), String(session?.reasoning_effort || ""));
    }
    updateChips();
    scheduleExecutorReadiness();
  }

  function setAlignmentMode(nextMode) {
    const profile = profileFor(executorInput.value);
    setExecutorMode(profile.command_only ? "command" : nextMode);
    updateExecutorControls({preserveUserModel: true, preserveUserEffort: true});
    scheduleExecutorReadiness();
  }

  function setSessionIdInUrl(sessionId) {
    const url = new URL(window.location.href);
    url.searchParams.set("alignment_session_id", sessionId);
    url.searchParams.delete("alignment_workdir");
    url.searchParams.delete("workdir");
    const nextUrl = `${url.pathname}${url.search}${url.hash}`;
    window.history.replaceState(null, "", nextUrl);
  }

  function clearSessionIdFromUrl({preserveCurrentWorkdir = false} = {}) {
    const url = new URL(window.location.href);
    const hadSessionId = url.searchParams.has("alignment_session_id");
    if (!hadSessionId && !preserveCurrentWorkdir) {
      return;
    }
    url.searchParams.delete("alignment_session_id");
    if (preserveCurrentWorkdir && !url.searchParams.has("workdir") && !url.searchParams.has("alignment_workdir")) {
      const workdir = workdirInput?.value.trim() || "";
      if (workdir) {
        url.searchParams.set("alignment_workdir", workdir);
      }
    }
    const nextUrl = `${url.pathname}${url.search}${url.hash}`;
    window.history.replaceState(null, "", nextUrl);
  }

  function currentAlignmentWorkdir() {
    return String(currentSession?.workdir || workdirInput?.value || "").trim();
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        "content-type": "application/json",
        ...(options.headers || {}),
      },
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(payload.error || payload.detail || response.statusText);
      error.payload = payload;
      throw error;
    }
    return payload;
  }

  function selectedWorkdirContextOption() {
    return (workdirContextState.options || []).find((option) => option.option_id === workdirContextState.selectedOptionId) || null;
  }

  function shouldRequireWorkdirContextChoice() {
    const currentWorkdir = workdirInput.value.trim();
    return Boolean(
      currentWorkdir
      && workdirContextState.loaded
      && workdirContextState.workdir === currentWorkdir
      && workdirContextState.requiresChoice
      && !workdirContextState.selectedOptionId
    );
  }

  function renderWorkdirContext() {
    if (!workdirContext || !workdirContextOptions || !workdirContextStatus) {
      return;
    }
    const options = workdirContextState.options || [];
    const visibleOptions = options.filter((option) => option.action !== "regenerate");
    if (!workdirContextState.workdir || (!workdirContextState.requiresChoice && visibleOptions.length === 0)) {
      workdirContext.hidden = true;
      workdirContextOptions.innerHTML = "";
      workdirContextStatus.textContent = "";
      return;
    }
    workdirContext.hidden = false;
    workdirContextStatus.textContent = workdirContextState.requiresChoice
      ? localeText("请选择启动方式", "Choose how to start")
      : localeText("未发现可继承产物", "No reusable artifacts found");
    const renderedOptions = options.filter((option) => option.action !== "regenerate" || workdirContextState.requiresChoice);
    workdirContextOptions.innerHTML = renderedOptions.map((option) => {
      const optionId = escapeHtml(option.option_id || "");
      const checked = option.option_id === workdirContextState.selectedOptionId ? " checked" : "";
      const label = escapeHtml(localeText(option.label_zh || "", option.label_en || option.label_zh || ""));
      const description = escapeHtml(localeText(option.description_zh || "", option.description_en || option.description_zh || ""));
      return `
        <label class="alignment-workdir-context-option" data-testid="alignment-workdir-context-option">
          <input type="radio" name="alignment_source_option" value="${optionId}"${checked} />
          <span>
            <strong>${label}</strong>
            <small>${description}</small>
          </span>
        </label>
      `;
    }).join("");
    workdirContextOptions.querySelectorAll("input[name='alignment_source_option']").forEach((input) => {
      input.addEventListener("change", () => {
        workdirContextState.selectedOptionId = input.value;
        renderWorkdirContext();
        clearTransientError();
      });
    });
  }

  async function loadWorkdirContext({force = false} = {}) {
    const workdir = workdirInput.value.trim();
    if (!workdir) {
      workdirContextState = {workdir: "", options: [], requiresChoice: false, selectedOptionId: "", loaded: false};
      renderWorkdirContext();
      return;
    }
    if (!force && workdirContextState.loaded && workdirContextState.workdir === workdir) {
      renderWorkdirContext();
      return;
    }
    if (workdirContext && workdirContextStatus) {
      workdirContext.hidden = false;
      workdirContextStatus.textContent = localeText("正在检查…", "Checking...");
    }
    try {
      const payload = await fetchJson("/api/alignments/workdir-context", {
        method: "POST",
        body: JSON.stringify({workdir}),
      });
      clearRecoveryPanel();
      const nextOptions = Array.isArray(payload.options) ? payload.options : [];
      const keepSelection = workdirContextState.workdir === workdir
        && nextOptions.some((option) => option.option_id === workdirContextState.selectedOptionId);
      workdirContextState = {
        workdir,
        options: nextOptions,
        requiresChoice: Boolean(payload.requires_choice),
        selectedOptionId: keepSelection ? workdirContextState.selectedOptionId : "",
        loaded: true,
      };
      if (!workdirContextState.requiresChoice) {
        workdirContextState.selectedOptionId = payload.recommended_option_id || "";
      }
      renderWorkdirContext();
    } catch (error) {
      workdirContextState = {workdir, options: [], requiresChoice: false, selectedOptionId: "", loaded: false};
      if (workdirContext && workdirContextStatus) {
        workdirContext.hidden = false;
        workdirContextStatus.textContent = error.message || localeText("检查失败", "Check failed");
      }
      renderRecoveryFromError(error, {testid: "alignment-workdir-context-recovery"});
      if (workdirContextOptions) {
        workdirContextOptions.innerHTML = "";
      }
    }
  }

  function scheduleWorkdirContextLoad() {
    clearTimeout(workdirContextTimer);
    workdirContextTimer = window.setTimeout(() => {
      loadWorkdirContext().catch(() => {});
    }, 300);
  }

  function collectExecutorSettingsPayload() {
    const commandMode = isCommandMode();
    return {
      executor_kind: executorInput.value,
      executor_mode: commandMode ? "command" : "preset",
      model: commandMode ? "" : modelInput.value.trim(),
      reasoning_effort: commandMode ? "" : effortInput.value.trim(),
      command_cli: commandMode ? commandCliInput.value.trim() : "",
      command_args_text: commandMode ? commandArgsInput.value : "",
    };
  }

  function executorReadinessCopy(readiness = executorReadinessState) {
    const label = executorLabel();
    const availableKinds = Array.isArray(readiness?.available_executor_kinds)
      ? readiness.available_executor_kinds.map((kind) => executorLabel({executor_kind: kind}))
      : [];
    const alternatives = availableKinds.length
      ? localeText(` 可用替代：${availableKinds.join("、")}。`, ` Available alternatives: ${availableKinds.join(", ")}.`)
      : "";
    const copies = {
      checking: localeText(`正在检查 ${label} 命令…`, `Checking the ${label} command…`),
      managed_runtime: localeText(
        `${label} 由当前 Loopora 宿主提供，可以开始对话。`,
        `${label} is provided by this Loopora host; the conversation can start.`,
      ),
      executable_available: localeText(
        `${label} CLI 可用；这里只确认命令可解析，认证和模型调用会在运行时验证。`,
        `${label} CLI is available. This checks command resolution only; authentication and model access are verified at runtime.`,
      ),
      command_required: localeText(
        "先在智能体设置里填写命令可执行文件和参数模板。",
        "Enter a command executable and argument template in Agent settings first.",
      ),
      invalid_configuration: localeText(
        "智能体配置还不能运行；请检查配置方式、命令和参数模板。",
        "The Agent configuration is not runnable yet; review its mode, command, and argument template.",
      ),
      runtime_unavailable: localeText(
        "Loopora 无法初始化所选智能体运行时；请检查智能体设置。",
        "Loopora could not initialize the selected Agent runtime; review Agent settings.",
      ),
      executable_not_found: localeText(
        `${label} CLI 在当前服务环境中不可用。请选择已安装的智能体或配置自定义命令。${alternatives}`,
        `${label} CLI is not available in this server environment. Choose an installed Agent or configure a custom command.${alternatives}`,
      ),
      check_failed: localeText(
        "暂时无法确认智能体命令；仍可尝试开始，运行失败时任务会保留供修复重试。",
        "The Agent command could not be checked. You may still start; a runtime failure preserves the task for repair and retry.",
      ),
    };
    return copies[String(readiness?.readiness_kind || "")] || copies.check_failed;
  }

  function applyExecutorReadinessToChip() {
    if (!agentChip) {
      return;
    }
    const blocked = executorReadinessState.blocking === true;
    agentChip.classList.toggle("is-readiness-blocked", blocked);
    agentChip.dataset.readinessStatus = String(executorReadinessState.status || "unknown");
    agentChip.dataset.readinessKind = String(executorReadinessState.readiness_kind || "unknown");
    if (blocked) {
      agentChip.textContent = `${agentChip.textContent} · ${localeText("不可用", "Unavailable")}`;
    }
    agentChip.title = executorReadinessCopy();
  }

  function renderExecutorReadiness(readiness) {
    executorReadinessState = readiness && typeof readiness === "object"
      ? readiness
      : {status: "unknown", blocking: false, readiness_kind: "check_failed"};
    if (executorReadinessNode) {
      executorReadinessNode.dataset.status = String(executorReadinessState.status || "unknown");
      executorReadinessNode.dataset.readinessKind = String(executorReadinessState.readiness_kind || "unknown");
      executorReadinessNode.textContent = executorReadinessCopy();
    }
    updateChips();
    setSendButtonState();
  }

  async function refreshExecutorReadiness({showChecking = false} = {}) {
    const requestId = ++executorReadinessRequestId;
    if (showChecking) {
      renderExecutorReadiness({status: "checking", blocking: false, readiness_kind: "checking"});
    }
    try {
      const readiness = await fetchJson("/api/system/executor-readiness", {
        method: "POST",
        body: JSON.stringify(collectExecutorSettingsPayload()),
      });
      if (requestId !== executorReadinessRequestId) {
        return executorReadinessState;
      }
      renderExecutorReadiness(readiness);
      return readiness;
    } catch (_) {
      if (requestId !== executorReadinessRequestId) {
        return executorReadinessState;
      }
      const unknown = {status: "unknown", blocking: false, readiness_kind: "check_failed"};
      renderExecutorReadiness(unknown);
      return unknown;
    }
  }

  function scheduleExecutorReadiness() {
    window.clearTimeout(executorReadinessTimer);
    executorReadinessTimer = window.setTimeout(() => {
      refreshExecutorReadiness({showChecking: true}).catch(() => {});
    }, 250);
  }

  async function executorReadinessBlocksSubmission() {
    const readiness = await refreshExecutorReadiness();
    if (readiness?.blocking !== true) {
      return false;
    }
    showError(executorReadinessCopy(readiness), {autoHide: false});
    openTools("advanced");
    return true;
  }

  function collectStartPayload() {
    const payload = {
      ...collectExecutorSettingsPayload(),
      workdir: workdirInput.value.trim(),
      message: composeJudgmentMessage(),
    };
    const selectedOption = selectedWorkdirContextOption();
    if (selectedOption && selectedOption.action !== "regenerate" && selectedOption.action !== "continue_session") {
      payload.source_option_id = selectedOption.option_id;
    }
    return payload;
  }

  function syncActiveExecutionCopy(status) {
    if (thinkingStatus) {
      thinkingStatus.hidden = true;
      thinkingStatus.textContent = "";
    }
    const statusText = String(currentSession?.status || status);
    setLiveSummaryStatus(statusText);
    if (!isActiveStatus(statusText)) {
      return;
    }
    const copy = activeStatusCopy(statusText);
    const workingTitle = transcriptEl.querySelector("[data-working-title]");
    const workingMeta = transcriptEl.querySelector("[data-working-meta]");
    if (workingTitle) {
      workingTitle.textContent = copy.label;
    }
    if (workingMeta) {
      workingMeta.textContent = copy.meta;
    }
  }

  function renderSession(session, options = {}) {
    const sessionChanged = currentSession?.id !== session?.id;
    const previousStatus = String(currentSession?.status || "");
    currentSession = session;
    if (sessionChanged) {
      syncExecutorControlsFromSession(session);
      selectedPreviewTab = "review";
      previewTabSessionId = String(session?.id || "");
      previewSurfaceState = "";
      readyRevisionOpen = false;
    }
    rememberSession(session.id);
    setSessionIdInUrl(session.id);
    syncWorkdirInputFromSession();
    shell?.classList.add("has-session");
    emptyState.hidden = true;
    chat.hidden = false;
    if (liveDetails) {
      liveDetails.hidden = false;
    }
    const status = String(session.status || "idle");
    const stage = String(session.alignment_stage || "");
    const statusChanged = previousStatus !== status;
    const revealReady = options.revealReady === true
      || (options.revealReady !== false && (sessionChanged || statusChanged || readyPreview.hidden));
    const revealRepair = options.revealRepair === true
      || (options.revealRepair !== false && (sessionChanged || statusChanged || readyPreview.hidden));
    const projectedStatus = renderSessionStatus(session);
    sessionMeta.textContent = `${statusLabel(projectedStatus, stage)} · ${basename(session.workdir)} · ${session.id}`;
    setBusy(isActiveStatus(status));
    renderReadyRevisionComposer(status);
    if (!isActiveStatus(status) && status !== "failed") {
      setLiveDetailsOpen(false);
    }
    updateChips();
    const shouldRevealAgentReview = renderAgentReviewBridge(session);
    const shouldRevealSourceContext = renderSourceContextBridge(session);
    renderTranscript(session.transcript || [], session);
    syncActiveExecutionCopy(status);
    if (shouldRevealAgentReview || shouldRevealSourceContext) {
      scrollRegion?.scrollTo({top: 0});
    }
    if (status === "ready") {
      loadReadyBundle({reveal: revealReady}).catch((error) => {
        renderBundleLoadError(error.message || localeText("无法加载 Loop 方案。", "Unable to load the loop plan."));
      });
    } else if (status === "running_loop" && String(session.linked_run_id || "").trim() && String(session.bundle_path || "").trim()) {
      loadReadyBundle({reveal: revealReady}).catch((error) => {
        renderBundleLoadError(error.message || localeText("无法加载已启动的 Loop 方案。", "Unable to load the launched loop plan."));
      });
    } else if (status === "failed" && failedSessionHasCandidatePlan(session)) {
      loadReadyBundle({
        reveal: revealRepair,
        allowImport: false,
        repairNote: session.error_message || localeText(
          "方案文件未通过校验；可以打开源文件修复，然后重新同步。",
          "The plan file did not pass validation; open the source, repair it, then reload."
        ),
      }).catch((error) => {
        renderBundleLoadError(error.message || localeText("无法加载待修复的方案文件。", "Unable to load the plan file that needs repair."));
      });
    } else {
      readyPreview.hidden = true;
      resetReadyReviewGate();
      shell?.classList.remove("has-artifact");
    }
    loadHistory().catch(() => {});
  }

  function rememberSession(sessionId) {
    try {
      if (sessionId) {
        window.localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
      }
    } catch (_) {
      return;
    }
  }

  function forgetSession() {
    try {
      window.localStorage.removeItem(SESSION_STORAGE_KEY);
    } catch (_) {
      return;
    }
  }

  function fillStarterPrompt(button) {
    if (!taskGoalInput || !button) {
      return;
    }
    const locale = window.LooporaUI.currentLocale();
    if (taskGoalInput) {
      taskGoalInput.value = locale === "zh" ? (button.dataset.goalZh || "") : (button.dataset.goalEn || "");
    }
    if (looporaFitReasonInput) {
      looporaFitReasonInput.value = locale === "zh" ? (button.dataset.fitZh || "") : (button.dataset.fitEn || "");
    }
    if (fakeDoneRiskInput) {
      fakeDoneRiskInput.value = locale === "zh" ? (button.dataset.fakeDoneZh || "") : (button.dataset.fakeDoneEn || "");
    }
    if (requiredEvidenceInput) {
      requiredEvidenceInput.value = locale === "zh" ? (button.dataset.evidenceZh || "") : (button.dataset.evidenceEn || "");
    }
    if (judgmentTradeoffsInput) {
      judgmentTradeoffsInput.value = locale === "zh" ? (button.dataset.tradeoffsZh || "") : (button.dataset.tradeoffsEn || "");
    }
    if (judgmentDetails) {
      judgmentDetails.open = true;
    }
    showError("");
    taskGoalInput.focus();
    taskGoalInput.dispatchEvent(new Event("input", {bubbles: true}));
    if (typeof taskGoalInput.setSelectionRange === "function") {
      taskGoalInput.setSelectionRange(taskGoalInput.value.length, taskGoalInput.value.length);
    }
  }

  function renderWorkingCard(session = currentSession) {
    const status = String(session?.status || "");
    if (!isActiveStatus(status)) {
      return;
    }
    const copy = activeStatusCopy(status);
    const card = document.createElement("article");
    card.className = "alignment-working-card";
    card.dataset.testid = "alignment-working-card";
    card.setAttribute("aria-live", "polite");
    card.innerHTML = `
      <span class="alignment-working-beacon" aria-hidden="true"></span>
      <span class="alignment-working-copy">
        <strong data-working-title>${escapeHtml(copy.label)}</strong>
        <span data-working-meta>${escapeHtml(copy.meta)}</span>
      </span>
      <span class="alignment-working-dots" aria-hidden="true"><i></i><i></i><i></i></span>
    `;
    transcriptEl.append(card);
  }

  function normalizeDecisionOptions(options) {
    if (!Array.isArray(options)) {
      return [];
    }
    return options
      .filter((option) => option && typeof option === "object")
      .map((option, index) => ({
        id: String(option.id || `option_${index + 1}`),
        label: String(option.label || "").trim(),
        description: String(option.description || "").trim(),
        recommended: option.recommended === true,
        userReply: String(option.user_reply || option.userReply || option.label || "").trim(),
      }))
      .filter((option) => option.label && option.userReply)
      .slice(0, 4);
  }

  function renderDecisionOptions(container, entry, {canChoose = false} = {}) {
    const options = normalizeDecisionOptions(entry?.decision_options);
    if (!options.length) {
      return;
    }
    const group = document.createElement("div");
    group.className = "alignment-decision-options";
    group.dataset.testid = "alignment-decision-options";
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", localeText("推荐选择", "Recommended choices"));
    options.forEach((option) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `alignment-decision-option${option.recommended ? " is-recommended" : ""}`;
      button.dataset.testid = "alignment-decision-option";
      button.dataset.optionId = option.id;
      button.disabled = !canChoose;
      const badge = option.recommended
        ? `<span class="alignment-decision-badge">${escapeHtml(localeText("推荐", "Recommended"))}</span>`
        : "";
      button.innerHTML = `
        <span class="alignment-decision-option-title">
          <strong>${escapeHtml(option.label)}</strong>
          ${badge}
        </span>
        <small>${escapeHtml(option.description)}</small>
      `;
      button.addEventListener("click", async () => {
        if (!canChoose || !currentSession?.id || isActiveStatus(currentSession.status || "")) {
          return;
        }
        showError("");
        setBusy(true);
        try {
          await appendMessage(option.userReply);
        } catch (error) {
          showError(error.message || localeText("发送选择失败。", "Failed to send choice."));
          setBusy(false);
        }
      });
      group.append(button);
    });
    container.append(group);
  }

  function agreementReviewFieldMarkup(evidence, key, label, {primary = false} = {}) {
    const value = String(evidence?.[key] || "").trim();
    return `
      <div class="alignment-agreement-field${primary ? " is-primary" : ""}" data-agreement-field="${escapeHtml(key)}">
        <dt>${escapeHtml(label)}</dt>
        <dd>${escapeHtml(value || localeText("尚未记录", "Not captured"))}</dd>
      </div>
    `;
  }

  function entryCarriesAgreementDecision(entry) {
    return normalizeDecisionOptions(entry?.decision_options).some((option) => option.id === "confirm_agreement");
  }

  function workingAgreementSurfaceMode(session, agreement) {
    const stage = String(session?.alignment_stage || "");
    const status = String(session?.status || "");
    const checklist = agreement?.readiness_checklist && typeof agreement.readiness_checklist === "object"
      ? agreement.readiness_checklist
      : {};
    const confirmed = checklist.explicit_confirmation === true || Boolean(String(agreement?.confirmed_at || "").trim());
    if (stage === "agreement_ready" && !confirmed) {
      return "review";
    }
    if (!confirmed) {
      return "";
    }
    if (isActiveStatus(status)) {
      return "compiling";
    }
    if (status === "failed") {
      const recoveryKind = failureRecovery(session).kind;
      if (recoveryKind === "user_cancelled") {
        return "cancelled";
      }
      if (recoveryKind === "resume_interrupted_planning") {
        return "interrupted";
      }
      return failedSessionHasCandidatePlan(session) ? "repair" : "execution_recovery";
    }
    return "compiled";
  }

  function workingAgreementPhaseCopy(session, mode) {
    const status = String(session?.status || "");
    if (mode === "review") {
      return {
        kicker: localeText("生成方案前的判断边界", "Judgment boundary before plan generation"),
        title: localeText("确认这些判断，再生成 Loop", "Confirm these judgments, then generate the Loop"),
      };
    }
    if (mode === "repair") {
      return {
        kicker: localeText("工作协议已保留", "Working agreement preserved"),
        title: localeText("方案需要修复，确认过的判断不会丢失", "The plan needs repair; confirmed judgments remain intact"),
      };
    }
    if (mode === "execution_recovery") {
      return {
        kicker: localeText("工作协议已保留", "Working agreement preserved"),
        title: localeText("智能体未生成方案；修复执行环境后重试", "No plan was generated; fix the Agent runtime and retry"),
      };
    }
    if (mode === "interrupted") {
      return {
        kicker: localeText("工作协议已保留", "Working agreement preserved"),
        title: localeText("本地规划已中断；可以从原判断继续", "Local planning was interrupted; continue from the same judgments"),
      };
    }
    if (mode === "cancelled") {
      return {
        kicker: localeText("工作协议已保留", "Working agreement preserved"),
        title: localeText("对话已停止；需要时可继续回复", "The conversation stopped; reply when you want to continue"),
      };
    }
    if (mode === "compiled") {
      return {
        kicker: localeText("工作协议已编译", "Working agreement compiled"),
        title: localeText("READY 方案来自这些已确认判断", "The READY plan comes from these confirmed judgments"),
      };
    }
    if (status === "validating") {
      return {
        kicker: localeText("正在校验判断投影", "Validating judgment projection"),
        title: localeText("检查 Loop 是否完整保留工作协议", "Checking that the Loop preserves the working agreement"),
      };
    }
    if (status === "repairing") {
      return {
        kicker: localeText("正在修复判断缺口", "Repairing judgment gaps"),
        title: localeText("按工作协议修复未投影或弱证据部分", "Repairing missing projection or weak evidence against the agreement"),
      };
    }
    return {
      kicker: localeText("工作协议已确认", "Working agreement confirmed"),
      title: localeText("正在把确认过的判断编译成 Loop", "Turning confirmed judgments into a Loop"),
    };
  }

  function renderWorkingAgreementReview(container, session = currentSession) {
    const agreement = session?.working_agreement && typeof session.working_agreement === "object"
      ? session.working_agreement
      : {};
    const evidence = agreement.readiness_evidence && typeof agreement.readiness_evidence === "object"
      ? agreement.readiness_evidence
      : {};
    const mode = workingAgreementSurfaceMode(session, agreement);
    if (!mode || !Object.keys(agreement).length) {
      return null;
    }

    const phase = workingAgreementPhaseCopy(session, mode);
    const agreementStepClass = mode === "review" ? "is-current" : "is-complete";
    const planStepClass = mode === "compiling" ? "is-current" : (mode === "repair" ? "is-blocked" : (mode === "compiled" ? "is-complete" : ""));
    const reviewPrimaryFields = `
      ${agreementReviewFieldMarkup(evidence, "success_surface", localeText("成功面", "Success surface"), {primary: true})}
      ${agreementReviewFieldMarkup(evidence, "fake_done_risks", localeText("假完成风险", "Fake-done risks"), {primary: true})}
    `;

    container.classList.add("alignment-message--agreement");
    container.dataset.testid = mode === "review" ? "alignment-agreement-review" : "alignment-agreement-handoff";
    container.dataset.agreementMode = mode;
    container.innerHTML = `
      <section class="alignment-agreement-review is-${escapeHtml(mode)}" aria-labelledby="alignment-agreement-review-title">
        <ol class="alignment-agreement-progress" aria-label="${escapeHtml(localeText("方案准备进度", "Plan preparation progress"))}">
          <li class="is-complete">${escapeHtml(localeText("任务", "Task"))}</li>
          <li class="${agreementStepClass}"${mode === "review" ? ' aria-current="step"' : ""}>${escapeHtml(localeText("工作协议", "Working agreement"))}</li>
          <li class="${planStepClass}"${mode === "compiling" ? ' aria-current="step"' : ""}>${escapeHtml(localeText("Loop 方案", "Loop plan"))}</li>
        </ol>
        <header class="alignment-agreement-header">
          <span data-testid="alignment-agreement-phase">${escapeHtml(phase.kicker)}</span>
          <h2 id="alignment-agreement-review-title">${escapeHtml(phase.title)}</h2>
          <p data-testid="alignment-agreement-summary">${escapeHtml(String(agreement.summary || "").trim())}</p>
        </header>
        <dl class="alignment-agreement-primary" data-testid="alignment-agreement-key-judgments">
          ${reviewPrimaryFields}
        </dl>
        ${mode === "review" ? '<div data-agreement-decision-mount></div>' : ""}
        <details class="alignment-agreement-details" data-testid="alignment-agreement-details">
          <summary>${escapeHtml(localeText("查看完整协议", "Review the full agreement"))}</summary>
          <dl>
            ${agreementReviewFieldMarkup({summary: agreement.summary}, "summary", localeText("协议摘要", "Agreement summary"))}
            ${agreementReviewFieldMarkup(evidence, "success_surface", localeText("成功面", "Success surface"))}
            ${agreementReviewFieldMarkup(evidence, "fake_done_risks", localeText("假完成风险", "Fake-done risks"))}
            ${agreementReviewFieldMarkup(evidence, "evidence_preferences", localeText("证据偏好", "Evidence preferences"))}
            ${agreementReviewFieldMarkup(evidence, "judgment_tradeoffs", localeText("关键取舍", "Key tradeoffs"))}
            ${agreementReviewFieldMarkup(evidence, "loop_fit", localeText("为什么使用 Loopora", "Why Loopora"))}
            ${agreementReviewFieldMarkup(evidence, "task_scope", localeText("任务范围", "Task scope"))}
            ${agreementReviewFieldMarkup(evidence, "execution_strategy", localeText("执行策略", "Execution strategy"))}
            ${agreementReviewFieldMarkup(evidence, "residual_risk_policy", localeText("残余风险", "Residual risk"))}
            ${agreementReviewFieldMarkup(evidence, "local_governance", localeText("本地治理", "Local governance"))}
            ${agreementReviewFieldMarkup(evidence, "role_posture", localeText("角色姿态", "Role posture"))}
            ${agreementReviewFieldMarkup(evidence, "workflow_shape", localeText("运行流程", "Run flow"))}
            ${agreementReviewFieldMarkup(evidence, "workdir_facts", localeText("项目事实", "Project facts"))}
          </dl>
        </details>
      </section>
    `;
    return {
      decisionMount: container.querySelector("[data-agreement-decision-mount]"),
      mode,
    };
  }

  function agentReviewItemLabel(itemId) {
    const labels = {
      success_surface: localeText("完成标准", "Success criteria"),
      fake_done_risks: localeText("伪完成风险", "Fake-done risks"),
      evidence_preferences: localeText("必需证据", "Evidence expectations"),
      loop_fit: localeText("Loopora fit", "Loopora fit"),
      execution_strategy: localeText("执行策略", "Execution strategy"),
      judgment_tradeoffs: localeText("判断取舍", "Judgment tradeoffs"),
      residual_risk_policy: localeText("残余风险", "Residual risk policy"),
      local_governance: localeText("本地治理责任", "Local governance"),
    };
    return labels[String(itemId || "")] || String(itemId || "").replaceAll("_", " ");
  }

  function agentReviewSuggestedReply(review) {
    const projectedReply = String(review?.suggested_reply || "").trim();
    if (projectedReply) {
      return projectedReply;
    }
    if (review?.loopora_fit_contradiction === true || review?.review_mode === "not_fit") {
      return localeText(
        "请先重新判断这个任务是否适合 Loopora：如果仍要继续，请说明后续轮次会新增哪些证据、handoff 或 GateKeeper 裁决价值；如果不适合，请明确建议不要生成可运行 Loop。",
        "First re-check whether this task fits Loopora. If we should continue, explain what later evidence, handoffs, or GateKeeper judgment would add. If it does not fit, clearly recommend not generating a runnable Loop."
      );
    }
    return localeText(
      "请基于上面的任务与判断，先确认 Loopora fit，并把完成标准、伪完成风险、证据预期、执行策略、判断取舍、残余风险和本地治理责任整理成可审查的 Loop 预览。",
      "Based on the task and judgment above, first confirm Loopora fit, then organize the success criteria, fake-done risks, evidence expectations, execution strategy, judgment tradeoffs, residual-risk policy, and local governance into a reviewable Loop preview."
    );
  }

  function fillAgentReviewReply(review) {
    const suggestedReply = agentReviewSuggestedReply(review);
    messageInput.value = suggestedReply;
    showError("");
    taskGoalInput.focus();
    messageInput.dispatchEvent(new Event("input", {bubbles: true}));
    if (typeof messageInput.setSelectionRange === "function") {
      messageInput.setSelectionRange(messageInput.value.length, messageInput.value.length);
    }
  }

  function renderAgentReviewBridge(session = currentSession) {
    if (!agentReviewBridge) {
      return false;
    }
    const review = session?.agent_entry_review || {};
    const status = String(session?.status || "");
    const shouldShow = review?.source === "agent_entry"
      && review.requires_web_alignment === true
      && status !== "ready";
    if (!shouldShow) {
      agentReviewBridge.hidden = true;
      agentReviewBridge.innerHTML = "";
      return false;
    }
    const reviewMode = review.loopora_fit_contradiction === true || review.review_mode === "not_fit" ? "not_fit" : "missing_candidate_plan";
    const itemIds = Array.isArray(review.missing_judgment_item_ids) && review.missing_judgment_item_ids.length
      ? review.missing_judgment_item_ids
      : ["success_surface", "fake_done_risks", "evidence_preferences", "loop_fit", "execution_strategy", "judgment_tradeoffs", "residual_risk_policy", "local_governance"];
    const itemMarkup = itemIds.map((itemId) => `
      <li>
        <span aria-hidden="true"></span>
        <strong>${escapeHtml(agentReviewItemLabel(itemId))}</strong>
      </li>
    `).join("");
    const active = isActiveStatus(status);
    const title = reviewMode === "not_fit"
      ? localeText("先重新定义为什么需要 Loop", "First redefine why a Loop is needed")
      : localeText("这还不是可运行 Loop", "This is not a runnable Loop yet");
    const body = reviewMode === "not_fit"
      ? localeText(
        "这次 /loopora-plan 没有提交候选方案文件，而且任务摘要像一次性处理或无需后续新证据的工作。继续前，先证明后续证据、handoff 或 GateKeeper 裁决会带来真实价值。",
        "This /loopora-plan did not submit a candidate plan file, and the task summary looks like one-off work or work with no later evidence. Before continuing, prove that later evidence, handoffs, or GateKeeper judgment add real value."
      )
      : localeText(
        "这次 /loopora-plan 来自宿主 Agent，但没有候选方案文件。Loopora 已保留任务和来源，只能先做 Web review，补齐关键判断后才会生成可审查预览。",
        "This /loopora-plan came from the host Agent but did not include a candidate plan file. Loopora preserved the task and provenance, and must stay in Web review until the missing judgment is filled in."
      );
    const taskMessage = String(review.task_message || "").trim();
    const taskAnchorMarkup = taskMessage
      ? `
        <section class="alignment-agent-review-source" data-testid="alignment-agent-review-source">
          <span>${escapeHtml(localeText("任务锚点", "Task anchor"))}</span>
          <p>${escapeHtml(taskMessage)}</p>
        </section>
      `
      : "";
    agentReviewBridge.hidden = false;
    agentReviewBridge.dataset.reviewMode = reviewMode;
    const reviewStage = String(session?.alignment_stage || "");
    agentReviewBridge.innerHTML = `
      <div class="alignment-agent-review-copy">
        <span class="alignment-agent-review-kicker">/loopora-plan Web review</span>
        <h3>${escapeHtml(title)}</h3>
        <p>${escapeHtml(body)}</p>
        ${taskAnchorMarkup}
        <div class="alignment-agent-review-meta">
          <span>${escapeHtml(localeText("来源", "Source"))}: ${escapeHtml(review.adapter || executorLabel(session))}</span>
          <span>${escapeHtml(localeText("当前状态", "Current state"))}: ${escapeHtml(statusLabel(projectedSessionStatus(session), reviewStage))}</span>
          <span>${escapeHtml(localeText("候选方案文件", "Candidate plan file"))}: ${escapeHtml(review.has_candidate_yaml ? localeText("已提供", "provided") : localeText("缺失", "missing"))}</span>
        </div>
      </div>
      <ul class="alignment-agent-review-checklist" data-testid="alignment-agent-review-checklist">
        ${itemMarkup}
      </ul>
      <div class="alignment-agent-review-options" data-testid="alignment-agent-review-options"></div>
      <div class="alignment-agent-review-actions">
        <button class="primary-button" type="button" data-agent-review-send data-testid="alignment-agent-review-send" ${active ? "disabled" : ""}>
          ${escapeHtml(localeText("提交审查并继续", "Send review and continue"))}
        </button>
        <button class="secondary-button" type="button" data-agent-review-fill data-testid="alignment-agent-review-fill">
          ${escapeHtml(localeText("填入审查回复", "Fill review reply"))}
        </button>
      </div>
    `;
    const reviewOptions = agentReviewBridge.querySelector("[data-testid='alignment-agent-review-options']");
    renderDecisionOptions(reviewOptions, {decision_options: review.decision_options || []}, {canChoose: !active});
    if (reviewOptions && !reviewOptions.childElementCount) {
      reviewOptions.hidden = true;
    }
    agentReviewBridge.querySelector("[data-agent-review-fill]")?.addEventListener("click", () => fillAgentReviewReply(review));
    agentReviewBridge.querySelector("[data-agent-review-send]")?.addEventListener("click", async () => {
      if (!currentSession?.id || isActiveStatus(currentSession.status || "")) {
        return;
      }
      showError("");
      setBusy(true);
      try {
        await appendMessage(agentReviewSuggestedReply(review));
      } catch (error) {
        showError(error.message || localeText("提交审查失败。", "Failed to send review."));
        setBusy(false);
      }
    });
    return true;
  }

  function normalizedStringList(value, limit = 6) {
    if (!Array.isArray(value)) {
      return [];
    }
    const items = [];
    value.forEach((item) => {
      const text = String(item || "").trim();
      if (text && !items.includes(text)) {
        items.push(text);
      }
    });
    return items.slice(0, limit);
  }

  function normalizedCount(value) {
    const number = Number(value);
    return Number.isFinite(number) && number >= 0 ? number : 0;
  }

  function sourceTopGapTexts(coverage) {
    if (!Array.isArray(coverage?.top_gaps)) {
      return [];
    }
    const items = [];
    coverage.top_gaps.forEach((gap) => {
      if (!gap || typeof gap !== "object") {
        return;
      }
      const text = String(gap.text || gap.summary || gap.target_id || gap.id || "").trim();
      if (text && !items.includes(text)) {
        items.push(text);
      }
    });
    return items.slice(0, 5);
  }

  function sourceEvidenceClaims(source) {
    if (!Array.isArray(source?.evidence_summary)) {
      return [];
    }
    const items = [];
    source.evidence_summary.forEach((item) => {
      if (!item || typeof item !== "object") {
        return;
      }
      const claim = String(item.claim || item.result || item.id || "").trim();
      if (claim && !items.includes(claim)) {
        items.push(claim);
      }
    });
    return items.slice(0, 3);
  }

  function sourceArtifactLabel(key) {
    const labels = {
      run_contract: localeText("运行判断契约", "Run contract"),
      task_verdict: localeText("任务裁决", "Task verdict"),
      evidence_ledger: localeText("证据账本", "Evidence ledger"),
      evidence_coverage: localeText("覆盖投影", "Coverage projection"),
      evidence_manifest: localeText("证据清单", "Evidence manifest"),
    };
    return labels[String(key || "")] || String(key || "").replaceAll("_", " ");
  }

  function sourceArtifactItems(source) {
    const paths = source?.artifact_paths && typeof source.artifact_paths === "object" ? source.artifact_paths : {};
    return Object.entries(paths)
      .map(([key, value]) => ({
        label: sourceArtifactLabel(key),
        path: String(value || "").trim(),
      }))
      .filter((item) => item.path)
      .slice(0, 5);
  }

  function sourceListMarkup(items, fallback) {
    const visibleItems = normalizedStringList(items, 6);
    if (!visibleItems.length) {
      return `<p class="alignment-source-context-empty">${escapeHtml(fallback)}</p>`;
    }
    return `<ul>${visibleItems.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
  }

  function renderSourceContextBridge(session = currentSession) {
    if (!sourceContextBridge) {
      return false;
    }
    const agreement = session?.working_agreement && typeof session.working_agreement === "object" ? session.working_agreement : {};
    const source = agreement.source && typeof agreement.source === "object" ? agreement.source : {};
    if (String(source.source_type || "") !== "run") {
      sourceContextBridge.hidden = true;
      sourceContextBridge.innerHTML = "";
      return false;
    }
    const coverage = source.coverage_summary && typeof source.coverage_summary === "object" ? source.coverage_summary : {};
    const verdict = source.task_verdict && typeof source.task_verdict === "object" ? source.task_verdict : {};
    const rawMissingCheckIds = normalizedStringList(coverage.missing_check_ids, 20);
    const missingIds = rawMissingCheckIds.slice(0, 6).map((id) => localeText(`缺失检查：${id}`, `Missing check: ${id}`));
    const topGaps = sourceTopGapTexts(coverage);
    const gapItems = [...topGaps, ...missingIds].slice(0, 6);
    const riskItems = normalizedStringList(coverage.risk_signals, 5);
    const evidenceClaims = sourceEvidenceClaims(source);
    const artifactItems = sourceArtifactItems(source);
    const runId = String(source.source_run_id || "").trim();
    const runStatus = String(source.run_status || "").trim();
    const verdictStatus = String(verdict.status || "").trim();
    const missingCount = normalizedCount(coverage.missing_check_count) || rawMissingCheckIds.length;
    const blockedCount = normalizedCount(coverage.blocked_target_count);
    const weakCount = normalizedCount(coverage.weak_target_count);
    const reason = String(coverage.reason || "").trim();

    sourceContextBridge.hidden = false;
    sourceContextBridge.innerHTML = `
      <div class="alignment-source-context-copy">
        <span class="alignment-source-context-kicker">${escapeHtml(localeText("上一轮证据", "Previous run evidence"))}</span>
        <h3>${escapeHtml(localeText("这次改进从具体缺口开始。", "This revision starts from concrete gaps."))}</h3>
        <p>${escapeHtml(reason || localeText(
          "Loopora 已把上一轮的裁决、覆盖缺口和证据文件带入这次对话；下一版 Loop 应先回应这些缺口。",
          "Loopora carried the previous verdict, coverage gaps, and evidence files into this chat; the next Loop should answer these gaps first."
        ))}</p>
      </div>
      <div class="alignment-source-context-metrics">
        ${runId ? `<span data-testid="alignment-source-run-id">${escapeHtml(localeText("运行", "Run"))}: ${escapeHtml(runId)}</span>` : ""}
        ${runStatus ? `<span>${escapeHtml(localeText("生命周期", "Lifecycle"))}: ${escapeHtml(statusLabel(runStatus))}</span>` : ""}
        ${verdictStatus ? `<span data-testid="alignment-source-task-verdict">${escapeHtml(localeText("任务裁决", "Task verdict"))}: ${escapeHtml(verdictStatus)}</span>` : ""}
        <span data-testid="alignment-source-missing-count">${escapeHtml(localeText("缺失检查", "Missing checks"))}: ${escapeHtml(String(missingCount))}</span>
        <span>${escapeHtml(localeText("弱证据", "Weak targets"))}: ${escapeHtml(String(weakCount))}</span>
        <span>${escapeHtml(localeText("阻断项", "Blocking targets"))}: ${escapeHtml(String(blockedCount))}</span>
      </div>
      <div class="alignment-source-context-grid">
        <article>
          <strong>${escapeHtml(localeText("先修这些缺口", "Gaps to fix first"))}</strong>
          <div data-testid="alignment-source-gap-list">
            ${sourceListMarkup(gapItems, localeText("没有可展示的覆盖缺口；继续检查 GateKeeper 裁决和证据账本。", "No visible coverage gaps; inspect the GateKeeper verdict and evidence ledger."))}
          </div>
        </article>
        <article>
          <strong>${escapeHtml(localeText("风险信号", "Risk signals"))}</strong>
          <div data-testid="alignment-source-risk-list">
            ${sourceListMarkup(riskItems, localeText("没有额外风险信号。", "No additional risk signals."))}
          </div>
        </article>
        <article>
          <strong>${escapeHtml(localeText("最近证据", "Recent evidence"))}</strong>
          <div data-testid="alignment-source-evidence-list">
            ${sourceListMarkup(evidenceClaims, localeText("没有可展示的最近证据摘要。", "No recent evidence summary is available."))}
          </div>
        </article>
        <article>
          <strong>${escapeHtml(localeText("白盒文件", "White-box files"))}</strong>
          <ul data-testid="alignment-source-artifact-list">
            ${artifactItems.length
              ? artifactItems.map((item) => `<li><span>${escapeHtml(item.label)}</span><code>${escapeHtml(item.path)}</code></li>`).join("")
              : `<li>${escapeHtml(localeText("没有可展示的证据文件路径。", "No evidence file paths are available."))}</li>`
            }
          </ul>
        </article>
      </div>
    `;
    return true;
  }

  function renderTranscript(transcript, session = currentSession) {
    transcriptEl.innerHTML = "";
    let agreementSurfaceBubble = null;
    let agreementSurfaceMode = "";
    let cancelledRecoveryCard = null;
    let interruptedRecoveryCard = null;
    const latestAssistantIndex = [...transcript].map((entry, index) => ({entry, index})).reverse()
      .find((item) => item.entry?.role === "assistant")?.index ?? -1;
    const latestAgreementIndex = [...transcript].map((entry, index) => ({entry, index})).reverse()
      .find((item) => item.entry?.role === "assistant" && entryCarriesAgreementDecision(item.entry))?.index ?? -1;
    transcript.forEach((entry, index) => {
      const bubble = document.createElement("article");
      bubble.className = `alignment-message alignment-message--${entry.role === "user" ? "user" : "assistant"}`;
      const isCurrentAgreement = entry.role === "assistant" && index === latestAgreementIndex;
      const agreementSurface = isCurrentAgreement ? renderWorkingAgreementReview(bubble, session) : null;
      let missingHtml = "";
      if (entry.role === "assistant" && Array.isArray(entry.missing_items) && entry.missing_items.length) {
        const missingLabels = entry.missing_items.map((id) => {
          const labelZh = MISSING_ITEM_LABELS_ZH[id] || id;
          const labelEn = MISSING_ITEM_LABELS_EN[id] || id;
          return `<li><span aria-hidden="true">⚠</span><span>${escapeHtml(localeText(labelZh, labelEn))}</span></li>`;
        });
        missingHtml = `<ul class="alignment-missing-items" data-testid="alignment-missing-items">${missingLabels.join("")}</ul>`;
      }
      if (!agreementSurface) {
        bubble.innerHTML = `
          <p>${escapeHtml(entry.content || "")}</p>
          ${missingHtml}
        `;
      } else {
        agreementSurfaceMode = agreementSurface.mode;
        if (["review", "compiling"].includes(agreementSurface.mode)) {
          agreementSurfaceBubble = bubble;
        }
      }
      if (entry.role === "assistant") {
        const canChoose = index === latestAssistantIndex
          && !isActiveStatus(session?.status || "")
          && String(session?.status || "") !== "ready";
        if (canChoose) {
          renderDecisionOptions(agreementSurface?.decisionMount || bubble, entry, {canChoose: true});
        }
      }
      transcriptEl.append(bubble);
    });
    if (agreementSurfaceMode !== "compiling") {
      renderWorkingCard(session);
    }
    if (String(session?.status || "") === "failed") {
      const recoveryKind = failureRecovery(session).kind;
      const workerInterrupted = recoveryKind === "resume_interrupted_planning";
      const generationRetry = recoveryKind === "retry_alignment_generation" || workerInterrupted;
      const userCancelled = recoveryKind === "user_cancelled";
      const failure = document.createElement("article");
      failure.className = `alignment-failure-card${userCancelled ? " is-cancelled" : ""}${workerInterrupted ? " is-interrupted" : ""}`;
      if (userCancelled) {
        cancelledRecoveryCard = failure;
      }
      if (workerInterrupted) {
        interruptedRecoveryCard = failure;
      }
      failure.innerHTML = `
        <strong>${escapeHtml(userCancelled
          ? localeText("对话已停止", "The conversation was stopped")
          : (workerInterrupted
            ? localeText("本地规划已中断", "Local planning was interrupted")
            : (generationRetry
            ? localeText("智能体未生成 Plan File", "The Agent did not produce a Plan File")
            : localeText("候选 Plan File 需要修复", "The candidate Plan File needs repair"))))}</strong>
        <p>${escapeHtml(userCancelled
          ? localeText("原任务和判断仍保留在这段对话中；需要继续时直接补充一条回复。", "The original task and judgment remain in this conversation; add a reply when you want to continue.")
          : (workerInterrupted
            ? localeText("原任务和工作协议仍在；继续后会从这段对话恢复规划。", "The task and working agreement remain; resume to continue planning in this conversation.")
            : (session?.error_message || (generationRetry
            ? localeText("原任务已保留；修复智能体设置或本地运行环境后可直接重试生成。", "The original task is preserved; fix the Agent settings or local runtime, then retry generation.")
            : localeText("可以查看执行详情，或让智能体按这个错误继续修复。", "Check execution details, or ask the Agent to repair from this error.")))))}</p>
        <div class="card-actions card-actions-compact">
          ${userCancelled
            ? `<button class="primary-button" type="button" data-focus-reply data-testid="alignment-cancelled-focus-reply-button">${escapeHtml(localeText("继续回复", "Continue with a reply"))}</button>`
            : (generationRetry
            ? `<button class="primary-button" type="button" data-retry-generation data-testid="alignment-retry-generation-button">${escapeHtml(workerInterrupted ? localeText("继续规划", "Resume planning") : localeText("重试生成", "Retry generation"))}</button>`
            : `<button class="primary-button" type="button" data-repair-failure data-testid="alignment-repair-failure-button">${escapeHtml(localeText("继续修复", "Continue repair"))}</button>`)}
          ${userCancelled ? "" : `<button class="secondary-button" type="button" data-open-panel="advanced">${escapeHtml(localeText("智能体设置", "Agent settings"))}</button>`}
          <button class="ghost-button" type="button" data-open-live-details>${escapeHtml(localeText("查看详情", "View details"))}</button>
        </div>
      `;
      failure.querySelector("[data-focus-reply]")?.addEventListener("click", () => {
        shell?.classList.add("is-cancelled-reply");
        messageInput?.focus?.();
        scrollRegion?.scrollTo({top: scrollRegion.scrollHeight, behavior: "smooth"});
      });
      failure.querySelector("[data-retry-generation]")?.addEventListener("click", async () => {
        setBusy(true);
        try {
          await retryAlignmentGeneration();
        } catch (error) {
          showError(error.message || localeText("重新生成失败。", "Failed to retry plan generation."));
          setBusy(false);
        }
      });
      failure.querySelector("[data-repair-failure]")?.addEventListener("click", async () => {
        if (!currentSession?.id) {
          return;
        }
        setBusy(true);
        try {
          await appendMessage(localeText("请根据上面的校验错误继续修复这个 Loop 方案。", "Please repair this loop plan using the validation error above."));
        } catch (error) {
          showError(error.message || localeText("继续修复失败。", "Failed to continue repair."));
          setBusy(false);
        }
      });
      failure.querySelector("[data-open-live-details]")?.addEventListener("click", () => {
        if (liveDetails) {
          liveDetails.hidden = false;
        }
        setLiveDetailsOpen(true);
      });
      failure.querySelector("[data-open-panel]")?.addEventListener("click", () => openTools("advanced"));
      transcriptEl.append(failure);
    }
    const sessionStatus = String(session?.status || "");
    const artifactOwnsScroll = sessionStatus === "ready"
      || sessionStatus === "running_loop"
      || (sessionStatus === "failed" && failedSessionHasCandidatePlan(session));
    const ownedRecoveryCard = cancelledRecoveryCard || interruptedRecoveryCard;
    if (ownedRecoveryCard && scrollRegion) {
      const scrollRect = scrollRegion.getBoundingClientRect();
      const recoveryRect = ownedRecoveryCard.getBoundingClientRect();
      scrollRegion.scrollTo({top: Math.max(0, scrollRegion.scrollTop + recoveryRect.top - scrollRect.top - 8)});
    } else if (agreementSurfaceBubble && scrollRegion) {
      const scrollRect = scrollRegion.getBoundingClientRect();
      const reviewRect = agreementSurfaceBubble.getBoundingClientRect();
      scrollRegion.scrollTo({top: Math.max(0, scrollRegion.scrollTop + reviewRect.top - scrollRect.top - 8)});
    } else if (!artifactOwnsScroll) {
      scrollRegion?.scrollTo({top: scrollRegion.scrollHeight});
    }
  }

  function appendEvent(event) {
    if (!event || !event.id || event.id <= latestEventId) {
      return;
    }
    latestEventId = event.id;
    const kind = alignmentConsoleProjector.eventKind(event);
    const line = document.createElement("article");
    line.className = `console-line console-line-${kind} is-collapsed`;
    line.innerHTML = `
      <button class="console-line-toggle" type="button">
        <span class="console-line-meta">
          <span class="console-line-stamp">#${event.id}</span>
          <span class="console-line-badge">${escapeHtml(kind)}</span>
        </span>
        <span class="console-line-summary">${escapeHtml(alignmentConsoleProjector.eventSummary(event))}</span>
        <span class="console-line-expander">view</span>
      </button>
      <pre class="console-line-body">${escapeHtml(JSON.stringify(event.payload || {}, null, 2))}</pre>
    `;
    line.querySelector(".console-line-toggle")?.addEventListener("click", () => {
      line.classList.toggle("is-collapsed");
    });
    consoleOutput.append(line);
    if (liveDetails) {
      liveDetails.hidden = false;
    }
    setLiveSummaryStatus(currentSession?.status || "idle");
    consoleOutput.parentElement.scrollTop = consoleOutput.parentElement.scrollHeight;
  }

  async function deleteHistorySession(sessionId) {
    if (!sessionId) {
      return;
    }
    showError("");
    try {
      await fetchJson(`/api/alignments/sessions/${encodeURIComponent(sessionId)}`, {
        method: "DELETE",
      });
      if (currentSession?.id === sessionId) {
        const preservedWorkdir = currentSession?.workdir || workdirInput?.value.trim() || "";
        resetToEmptyConversation();
        if (preservedWorkdir) {
          workdirInput.value = preservedWorkdir;
          syncAlignmentWorkdirContext();
        }
        forgetSession();
        clearSessionIdFromUrl({preserveCurrentWorkdir: true});
      }
      await loadHistory();
    } catch (error) {
      showError(error.message || localeText("删除历史对话失败。", "Failed to delete chat history."));
    }
  }

  async function loadHistory() {
    await alignmentHistoryController.load();
  }

  async function restoreSession(sessionId) {
    if (!sessionId) {
      return;
    }
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    latestEventId = 0;
    consoleOutput.innerHTML = "";
    closeTools();
    const payload = await fetchJson(`/api/alignments/sessions/${encodeURIComponent(sessionId)}`);
    renderSession(payload.session, {revealReady: true});
    await loadSeedEvents(payload.session.id);
    if (ACTIVE_STATUSES.has(String(payload.session.status || ""))) {
      openStream(payload.session.id);
    }
  }

  function currentUrlSessionId() {
    return new URL(window.location.href).searchParams.get("alignment_session_id") || "";
  }

  async function fetchUrlSessionForNavigationGuard() {
    const sessionId = currentUrlSessionId();
    if (!sessionId) {
      return null;
    }
    const payload = await fetchJson(`/api/alignments/sessions/${encodeURIComponent(sessionId)}`).catch(() => null);
    return payload?.session || null;
  }

  async function activeSessionBlocksNavigation(message) {
    if (!isActiveStatus(currentSession?.status || "") && !currentUrlSessionId()) {
      return false;
    }
    const latestSession = currentSession?.id
      ? await refreshSession().catch(() => currentSession)
      : await fetchUrlSessionForNavigationGuard();
    if (!isActiveStatus(latestSession?.status || "")) {
      return false;
    }
    showError(message, {autoHide: false});
    return true;
  }

  function directPathBlocksWebStart() {
    if (currentSession) {
      return false;
    }
    const handoff = readTutorialFitHandoff();
    if (!tutorialFitHandoffBlocksCurrentWebConversation(handoff)) {
      setTutorialFitHandoffBlocksWebConversation(false);
      return false;
    }
    setTutorialFitHandoffBlocksWebConversation(true);
    renderTutorialFitHandoffBridge();
    showError(directPathWebStartBlockedMessage(), {autoHide: false});
    return true;
  }

  async function openHistorySession(sessionId) {
    const targetSessionId = String(sessionId || "").trim();
    if (!targetSessionId) {
      return;
    }
    if (
      currentSession?.id
      && currentSession.id !== targetSessionId
      && await activeSessionBlocksNavigation(localeText(
        "Agent 正在执行；请先停止当前对话，再打开其他历史对话。",
        "The Agent is running; stop the current conversation before opening another chat.",
      ))
    ) {
      return;
    }
    try {
      await restoreSession(targetSessionId);
    } catch (error) {
      showError(error.message || localeText("打开历史对话失败。", "Failed to open chat history."));
    }
  }

  function bindActiveSessionLinkGuard(selector, messageFactory) {
    document.querySelectorAll(selector).forEach((link) => {
      link.addEventListener("click", async (event) => {
        if (!isActiveStatus(currentSession?.status || "") && !currentUrlSessionId()) {
          return;
        }
        event.preventDefault();
        if (await activeSessionBlocksNavigation(messageFactory())) {
          return;
        }
        window.location.href = link.href;
      });
    });
  }

  function bindActiveSessionFormGuard(selector, messageFactory) {
    document.querySelectorAll(selector).forEach((form) => {
      form.addEventListener("submit", async (event) => {
        if (form.dataset.activeSessionGuardBypass === "1") {
          delete form.dataset.activeSessionGuardBypass;
          return;
        }
        if (!isActiveStatus(currentSession?.status || "") && !currentUrlSessionId()) {
          return;
        }
        event.preventDefault();
        if (await activeSessionBlocksNavigation(messageFactory())) {
          return;
        }
        form.dataset.activeSessionGuardBypass = "1";
        if (typeof form.requestSubmit === "function") {
          if (event.submitter) {
            form.requestSubmit(event.submitter);
          } else {
            form.requestSubmit();
          }
          return;
        }
        form.submit();
      });
    });
  }

  function bindDirectPathWebStartGuard(selector) {
    document.querySelectorAll(selector).forEach((control) => {
      control.addEventListener("click", (event) => {
        if (!directPathBlocksWebStart()) {
          return;
        }
        event.preventDefault();
        event.stopImmediatePropagation();
      });
    });
  }

  bindDirectPathWebStartGuard("[data-compose-mode-link]");
  bindActiveSessionLinkGuard("[data-compose-mode-link]", () => localeText(
    "Agent 正在执行；请先停止当前对话，再切换编排入口。",
    "The Agent is running; stop the current conversation before switching composition paths.",
  ));
  bindActiveSessionLinkGuard('[data-testid="nav-compose-link"]', () => localeText(
    "Agent 正在执行；请先停止当前对话，再返回创建入口。",
    "The Agent is running; stop the current conversation before returning to the composer start.",
  ));
  bindActiveSessionFormGuard("[data-global-project-scope-form]", () => localeText(
    "Agent 正在执行；请先停止当前对话，再切换目标项目。",
    "The Agent is running; stop the current conversation before switching target projects.",
  ));

  async function refreshSession() {
    if (!currentSession?.id) {
      return null;
    }
    const payload = await fetchJson(`/api/alignments/sessions/${encodeURIComponent(currentSession.id)}`);
    renderSession(payload.session);
    return payload.session;
  }

  function openStream(sessionId) {
    if (eventSource) {
      eventSource.close();
    }
    eventSource = new EventSource(`/api/alignments/sessions/${encodeURIComponent(sessionId)}/stream?after_id=${latestEventId}`);
    EVENT_TYPES.forEach((eventType) => {
      eventSource.addEventListener(eventType, (message) => {
        try {
          appendEvent(JSON.parse(message.data));
        } catch (_) {
          return;
        }
        refreshSession().catch(() => {});
      });
    });
    eventSource.onerror = () => {
      eventSource?.close();
      eventSource = null;
      refreshSession().catch(() => {});
    };
  }

  async function loadSeedEvents(sessionId) {
    let afterId = latestEventId;
    while (true) {
      const params = new URLSearchParams();
      params.set("after_id", String(afterId));
      params.set("limit", String(ALIGNMENT_EVENT_PAGE_LIMIT));
      const events = await fetchJson(`/api/alignments/sessions/${encodeURIComponent(sessionId)}/events?${params}`);
      if (!Array.isArray(events) || events.length === 0) {
        return;
      }
      events.forEach(appendEvent);
      if (events.length < ALIGNMENT_EVENT_PAGE_LIMIT || latestEventId <= afterId) {
        return;
      }
      afterId = latestEventId;
    }
  }

  async function loadReadyBundle(options = {}) {
    if (!currentSession?.id) {
      return;
    }
    const payload = await fetchJson(`/api/alignments/sessions/${encodeURIComponent(currentSession.id)}/bundle`);
    if (!payload.ok) {
      renderAlignmentRecovery(payload, {
        testid: "alignment-preview-recovery",
        title: localeText("先修复 Plan File 后再预览", "Fix the Plan File before previewing again"),
      });
      renderBundleLoadError(payload.error || localeText("方案暂时无法读取。", "The plan cannot be read right now."));
      return;
    }
    clearRecoveryPanel();
    renderBundlePreview(payload, options);
  }

  function renderBundleLoadError(message) {
    shell?.classList.add("has-artifact");
    readyPreview.hidden = false;
    readyPreview.dataset.previewState = "error";
    if (readyActions) {
      readyActions.hidden = true;
    }
    if (readySaveAction) {
      readySaveAction.hidden = true;
    }
    if (readyRunAction) {
      readyRunAction.hidden = true;
    }
    resetReadyReviewGate();
    const agentEntryLaunch = agentEntryProjectionFor({session: currentSession});
    readyPreview.dataset.launchMode = agentEntryLaunch ? "agent-entry" : "web-run";
    if (importSaveButton) {
      importSaveButton.hidden = true;
      importSaveButton.disabled = true;
    }
    if (importRunButton) {
      importRunButton.hidden = true;
      delete importRunButton.dataset.runId;
      delete importRunButton.dataset.copyValue;
      delete importRunButton.dataset.launchAction;
      setBilingualText(importRunButton, agentEntryLaunch ? "修复后回到 Agent" : "修复后运行", agentEntryLaunch ? "Repair before Agent run" : "Repair before running");
    }
    artifactName.textContent = localeText("无法加载 Loop 方案", "Unable to load loop plan");
    previewTitle.textContent = agentEntryLaunch
      ? localeText("候选方案需要重新加载后再回到 Agent", "Candidate plan needs reload before returning to the Agent")
      : localeText("方案需要重新加载", "Plan needs reload");
    readyNote.textContent = agentEntryLaunch
      ? localeText(
        "这份候选来自 /loopora-plan；Web 只负责展示修复面。修好源文件并重新运行 /loopora-plan，READY 后再回到同一个 Agent 执行 /loopora-run。",
        "This candidate came from /loopora-plan; Web only shows the repair surface. Repair the source file, rerun /loopora-plan, then return to the same Agent for /loopora-run after READY."
      )
      : localeText(
        "源文件当前不可作为可运行 Loop 预览。先按修复焦点处理，再重新同步。",
        "The source file cannot be used as a runnable Loop preview yet. Repair the focus items, then reload."
      );
    if (artifactRisk) {
      artifactRisk.textContent = localeText("风险：-", "Risk: -");
    }
    if (artifactEvidence) {
      artifactEvidence.textContent = localeText("证据：-", "Evidence: -");
    }
    if (artifactJudgment) {
      artifactJudgment.textContent = localeText("判断：-", "Judgment: -");
    }
    if (artifactVerdict) {
      artifactVerdict.textContent = localeText("裁决：-", "Verdict: -");
    }
    artifactWorkdir.textContent = localeText(
      `运行目录：${basename(currentSession?.workdir || "") || "-"}`,
      `Run directory: ${basename(currentSession?.workdir || "") || "-"}`
    );
    renderControlSummary(null);
    renderJudgmentMap({}, []);
    roleList.innerHTML = "";
    workflowDiagram.innerHTML = "";
    if (sourceOpenButton) {
      const path = currentSession?.bundle_path || "";
      sourceOpenButton.hidden = !path;
      sourceOpenButton.dataset.sourcePath = path;
    }
    if (sourceSyncButton) {
      sourceSyncButton.hidden = false;
    }
    if (artifactSource) {
      artifactSource.hidden = false;
    }
    renderRepairGuide({
      visible: true,
      error: message || "",
      sourcePath: currentSession?.bundle_path || "",
      sessionId: currentSession?.id || "",
      agentEntry: agentEntryLaunch,
    });
    if (sourcePathLabel) {
      const path = currentSession?.bundle_path || "";
      sourcePathLabel.textContent = path ? `${localeText("源文件", "Source")}: ${path}` : "";
      sourcePathLabel.title = path;
    }
    specPreview.innerHTML = `
      <div class="field-status is-error">
        ${escapeHtml(message || localeText("无法加载 Loop 方案。", "Unable to load the loop plan."))}
      </div>
      <div class="card-actions">
        <button class="secondary-button" type="button" data-reload-ready-bundle>${escapeHtml(localeText("重新同步源文件", "Reload source file"))}</button>
      </div>
    `;
    specPreview.querySelector("[data-reload-ready-bundle]")?.addEventListener("click", () => {
      syncReadyBundle().catch((error) => renderBundleLoadError(error.message));
    });
    preparePreviewNavigation({
      sessionId: currentSession?.id || "",
      surfaceState: "error",
      defaultTab: "spec",
    });
    revealReadyPreviewStart();
  }

  function taskSummary(bundle) {
    const markdown = String(bundle?.spec?.markdown || "");
    const taskMatch = markdown.match(/# Task\s+([\s\S]*?)(?:\n# |\s*$)/);
    const text = (taskMatch ? taskMatch[1] : markdown)
      .replace(/```[\s\S]*?```/g, "")
      .replace(/[#*_`>-]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
    return text.slice(0, 180) || localeText("Loop 目标已生成。", "Task goal generated.");
  }

  function workflowSummary(preview) {
    const roleById = new Map((preview?.roles || []).map((role) => [role.id, role.name || role.id]));
    return (preview?.steps || [])
      .map((step) => roleById.get(step.role_id) || step.role_id)
      .filter(Boolean)
      .join(" -> ");
  }

  function labeledSummary(labelZh, labelEn, value) {
    return localeText(`${labelZh}：${value || "-"}`, `${labelEn}: ${value || "-"}`);
  }

  function mainRiskSummary(summary) {
    return listSnippet(summary?.risks) || localeText("按方案中的假完成风险收束。", "Controlled from the plan's fake-done risks.");
  }

  function primaryRiskSummary(summary) {
    return (summary?.risks || [])
      .map((value) => String(value || "").trim())
      .filter(Boolean)[0] || localeText("按方案中的假完成风险收束。", "Controlled from the plan's fake-done risks.");
  }

  function evidencePathSummary(summary) {
    const evidence = listSnippet(summary?.evidence) || localeText("运行时写入证据账本。", "Recorded into the run evidence ledger.");
    const coverage = coverageSummary(summary);
    const evidenceText = coverage ? `${evidence}; ${coverage}` : evidence;
    const traceability = summary?.traceability || {};
    if (Number(traceability.mapped_count || 0) > 0) {
      return localeText(
        `${evidenceText}；${traceability.mapped_count}/${traceability.required_count || traceability.mapped_count} 项判断已投影。`,
        `${evidenceText}; ${traceability.mapped_count}/${traceability.required_count || traceability.mapped_count} judgments projected.`
      );
    }
    return evidenceText;
  }

  function coverageSummary(summary) {
    const coverage = summary?.coverage || {};
    const checkCount = Number(coverage.check_count || 0);
    const targetCount = Number(coverage.target_count || 0);
    const requiredCount = Number(coverage.required_target_count || 0);
    const summaryText = localeText(coverage.summary_zh || "", coverage.summary_en || coverage.summary || "");
    if (summaryText && !checkCount && !targetCount) {
      return summaryText;
    }
    if (checkCount && targetCount) {
      return localeText(
        `${checkCount} 项检查 · ${targetCount} 个覆盖目标（${requiredCount} 必需）`,
        `${checkCount} checks · ${targetCount} coverage targets (${requiredCount} required)`
      );
    }
    if (checkCount) {
      return localeText(`${checkCount} 项检查`, `${checkCount} checks`);
    }
    if (targetCount) {
      return localeText(
        `${targetCount} 个覆盖目标（${requiredCount} 必需）`,
        `${targetCount} coverage targets (${requiredCount} required)`
      );
    }
    return "";
  }

  function evidenceStatus(summary) {
    const count = (summary?.evidence || []).filter((value) => String(value || "").trim()).length;
    const coverage = summary?.coverage || {};
    const targetCount = Number(coverage.target_count || 0);
    const traceabilityCount = Number(summary?.traceability?.mapped_count || 0);
    if (targetCount) {
      const checkCount = Number(coverage.check_count || count || 0);
      return localeText(`${checkCount} 检查 · ${targetCount} 目标`, `${checkCount} checks · ${targetCount} targets`);
    }
    if (count) {
      if (traceabilityCount) {
        return localeText(`${count} 项 · ${traceabilityCount} 映射`, `${count} checks · ${traceabilityCount} mapped`);
      }
      return localeText(`${count} 项`, `${count} checks`);
    }
    if (traceabilityCount) {
      return localeText(`${traceabilityCount} 映射`, `${traceabilityCount} mapped`);
    }
    return localeText("已配置", "configured");
  }

  function judgmentStatus(summary) {
    const traceability = summary?.traceability || {};
    const mapped = Number(traceability.mapped_count || 0);
    const required = Number(traceability.required_count || mapped);
    const diagnostics = (summary?.diagnostics || []).filter((item) => String(item?.severity || "") !== "info");
    const base = mapped
      ? localeText(`${mapped}/${required || mapped} 已投影`, `${mapped}/${required || mapped} projected`)
      : localeText("未投影", "not projected");
    if (diagnostics.length) {
      return localeText(`${base} · ${diagnostics.length} 提醒`, `${base} · ${diagnostics.length} warnings`);
    }
    return base;
  }

  function judgmentReviewStatus(summary, diagnostics = []) {
    const traceability = summary?.traceability || {};
    const mapped = Number(traceability.mapped_count || 0);
    const required = Number(traceability.required_count || mapped);
    const warnings = diagnostics.filter((item) => String(item?.severity || "") !== "info").length;
    const base = mapped ? `${mapped}/${required || mapped}` : localeText("未投影", "not projected");
    return warnings
      ? localeText(`${base} · ${warnings} 提醒`, `${base} · ${warnings} warnings`)
      : base;
  }

  function verdictSummary(summary) {
    const gatekeeper = summary?.gatekeeper || {};
    if (gatekeeper.enabled === true) {
      return localeText("守门者依据证据裁决。", "GateKeeper judges from evidence.");
    }
    return localeText("按轮次预算收束。", "Ends by round budget.");
  }

  function listSnippet(values) {
    return (values || [])
      .map((value) => String(value || "").trim())
      .filter(Boolean)
      .slice(0, 2)
      .join(" / ");
  }

  function readyReviewGateRequired() {
    return Boolean(reviewGate && reviewGate.dataset.required === "true" && !reviewGate.hidden);
  }

  function resetReadyReviewGate() {
    if (reviewGate) {
      reviewGate.hidden = true;
      reviewGate.dataset.required = "false";
    }
    if (reviewGateCheckbox) {
      reviewGateCheckbox.checked = false;
      reviewGateCheckbox.disabled = true;
    }
    if (reviewGateStatus) {
      reviewGateStatus.textContent = "";
    }
    if (importRunButton) {
      importRunButton.removeAttribute("aria-describedby");
    }
    if (importSaveButton) {
      importSaveButton.removeAttribute("aria-describedby");
    }
  }

  function renderReadyRevisionComposer(status = currentSession?.status || "") {
    const reviewingReady = String(status || "") === "ready";
    if (!reviewingReady) {
      readyRevisionOpen = false;
    }
    shell?.classList.toggle("is-ready-review", reviewingReady);
    shell?.classList.toggle("is-ready-revision", reviewingReady && readyRevisionOpen);
    revisePreviewButton?.setAttribute("aria-expanded", String(reviewingReady && readyRevisionOpen));
  }

  function updateReadyReviewGateActions() {
    const required = readyReviewGateRequired() && importRunButton?.dataset.launchAction === "web-run";
    if (!required) {
      [importSaveButton, importRunButton].forEach((button) => button?.removeAttribute("aria-describedby"));
      if (reviewGateStatus) {
        reviewGateStatus.textContent = "";
      }
      return;
    }
    [importSaveButton, importRunButton].forEach((button) => {
      button?.setAttribute("aria-describedby", "alignment-review-gate-status");
      if (button && button.dataset.busy !== "true") {
        button.disabled = reviewGateCheckbox?.checked !== true;
      }
    });
    if (reviewGateStatus) {
      reviewGateStatus.textContent = reviewGateCheckbox?.checked === true
        ? localeText("复核完成，可以保存 Loop 或立即运行。", "Review confirmed. Save the Loop or run it now.")
        : localeText("确认复核后，再选择保存 Loop 或立即运行。", "Confirm the review, then save the Loop or run it now.");
    }
  }

  function renderReadyReviewGate({required, summary, diagnostics = []}) {
    if (!reviewGate) {
      return;
    }
    if (!required) {
      resetReadyReviewGate();
      return;
    }
    reviewGate.hidden = false;
    reviewGate.dataset.required = "true";
    if (reviewGateCheckbox) {
      reviewGateCheckbox.checked = false;
      reviewGateCheckbox.disabled = false;
    }
    if (reviewGateEvidence) {
      reviewGateEvidence.textContent = labeledSummary("证据", "Evidence", evidenceStatus(summary));
      reviewGateEvidence.title = evidencePathSummary(summary);
    }
    if (reviewGateJudgment) {
      reviewGateJudgment.textContent = labeledSummary("判断", "Judgment", judgmentReviewStatus(summary, diagnostics));
      reviewGateJudgment.title = evidencePathSummary(summary);
    }
    if (reviewGateClosure) {
      reviewGateClosure.textContent = labeledSummary(
        "收口",
        "Closure",
        summary?.gatekeeper?.enabled === true ? "GateKeeper" : verdictSummary(summary)
      );
      reviewGateClosure.title = verdictSummary(summary);
    }
    updateReadyReviewGateActions();
  }

  function renderControlSummary(summary) {
    if (!controlSummary) {
      return;
    }
    if (!summary) {
      controlSummary.innerHTML = "";
      return;
    }
    const workflow = summary.workflow || {};
    const gatekeeper = summary.gatekeeper || {};
    const controls = Array.isArray(summary.controls) ? summary.controls : [];
    const controlSnippet = controls
      .slice(0, 2)
      .map((control) => {
        const after = control.after && control.after !== "0s" ? `${control.after} · ` : "";
        return `${after}${control.signal || "control"} -> ${control.role_name || control.role_id || "role"}`;
      })
      .join(" / ");
    const cards = [
      {
        label: localeText("Loopora 适配", "Loopora fit"),
        value: listSnippet(summary.loop_fit_reasons)
          || localeText("长期治理理由未声明。", "Long-running governance reason not declared."),
      },
      {
        label: localeText("成功面", "Success"),
        value: listSnippet(summary.success_surface)
          || localeText("按 Done When 与任务成功面裁决。", "Judged by Done When and the success surface."),
      },
      {
        label: localeText("假完成", "Fake done"),
        value: listSnippet(summary.fake_done_risks)
          || localeText("未声明额外假完成风险。", "No extra fake-done risks declared."),
      },
      {
        label: localeText("证据偏好", "Evidence preferences"),
        value: listSnippet(summary.evidence_preferences)
          || localeText("按任务契约选择证据。", "Evidence follows the task contract."),
      },
      {
        label: localeText("覆盖目标", "Coverage targets"),
        value: coverageSummary(summary)
          || localeText("由 Done When 和裁决面派生。", "Derived from Done When and verdict surfaces."),
      },
      {
        label: localeText("主要风险", "Main risk"),
        value: listSnippet(summary.risks) || localeText("从 Loop 契约中读取。", "Read from the task contract."),
      },
      {
        label: localeText("残余风险", "Residual risk"),
        value: listSnippet(summary.residual_risk_policy)
          || localeText("按任务契约失败关闭。", "Fail closed by the task contract."),
      },
      {
        label: localeText("执行策略", "Execution strategy"),
        value: listSnippet(summary.execution_strategy)
          || localeText("下一轮优先级未声明。", "Next-round priority not declared."),
      },
      {
        label: localeText("判断取舍", "Tradeoffs"),
        value: listSnippet(summary.judgment_tradeoffs)
          || localeText("按任务契约裁决。", "Judged by the task contract."),
      },
      {
        label: localeText("角色姿态", "Role posture"),
        value: listSnippet(summary.role_postures)
          || localeText("角色执行姿态未声明。", "Role posture not declared."),
      },
      {
        label: localeText("证据路径", "Evidence path"),
        value: listSnippet(summary.evidence) || localeText("运行时写入证据账本。", "Recorded into the run evidence ledger."),
      },
      {
        label: localeText("执行顺序", "Execution path"),
        value: workflow.summary || localeText(`${workflow.step_count || 0} 个步骤`, `${workflow.step_count || 0} steps`),
      },
      ...(Array.isArray(summary.local_governance) && summary.local_governance.length ? [{
        label: localeText("本地治理", "Local governance"),
        value: listSnippet(summary.local_governance),
      }] : []),
      {
        label: localeText("守门者", "GateKeeper"),
        value: gatekeeper.enabled === true
          ? localeText("需要证据引用才能结束。", "Requires evidence refs to finish.")
          : localeText("未配置守门者。", "No GateKeeper configured."),
      },
      ...(controls.length ? [{
        label: localeText("运行控制", "Runtime controls"),
        value: controlSnippet || localeText("按误差风险触发检查。", "Triggered by error-control risk."),
      }] : []),
    ];
    controlSummary.innerHTML = cards.map((card) => `
      <div class="alignment-control-card">
        <strong>${escapeHtml(card.label)}</strong>
        <span>${escapeHtml(card.value)}</span>
      </div>
    `).join("");
  }

  function traceItemLabel(item) {
    const labels = {
      loop_fit: localeText("Loopora 适配", "Loopora fit"),
      collaboration_story: localeText("协作判断", "Collaboration"),
      task_scope: localeText("任务边界", "Task scope"),
      success_surface: localeText("成功面", "Success"),
      fake_done_risks: localeText("假完成", "Fake done"),
      evidence_preferences: localeText("证据偏好", "Evidence"),
      coverage_targets: localeText("覆盖目标", "Coverage"),
      execution_strategy: localeText("执行策略", "Execution strategy"),
      residual_risk_policy: localeText("残余风险", "Risk policy"),
      judgment_tradeoffs: localeText("判断取舍", "Tradeoffs"),
      local_governance: localeText("本地治理", "Local governance"),
      role_posture: localeText("角色姿态", "Role posture"),
      workflow_judgment: localeText("运行流程", "Run flow"),
      gatekeeper_closure: localeText("裁决收口", "Closure"),
      runtime_controls: localeText("运行控制", "Controls"),
    };
    return labels[item?.key] || item?.label || item?.key || "-";
  }

  function traceSurfaceLabel(value) {
    const surface = String(value || "").trim();
    const labels = {
      collaboration_summary: [ "治理摘要", "Governance summary" ],
      "spec.markdown": [ "Loop 契约", "Loop contract" ],
      "spec.markdown#Task": [ "任务契约", "Task contract" ],
      "spec.markdown#Done When": [ "完成标准", "Completion criteria" ],
      "spec.markdown#Success Surface": [ "成功面", "Success surface" ],
      "spec.markdown#Fake Done": [ "假完成护栏", "Fake-done guardrails" ],
      "spec.markdown#Evidence Preferences": [ "证据偏好", "Evidence expectations" ],
      "spec.markdown#Residual Risk": [ "残余风险策略", "Residual-risk policy" ],
      "spec.markdown#Role Notes": [ "本地治理说明", "Local governance notes" ],
      "role_definitions[].prompt_markdown": [ "角色工作姿态", "Role operating posture" ],
      "role_definitions[].posture_notes": [ "角色姿态说明", "Role posture notes" ],
      "workflow.collaboration_intent": [ "运行意图", "Run-flow intent" ],
      "workflow.steps[].inputs": [ "步骤交接输入", "Step handoff inputs" ],
      "workflow.steps[].on_pass": [ "收口动作", "Closure action" ],
      "workflow.steps[].inputs.evidence_query": [ "GateKeeper 证据查询", "GateKeeper evidence query" ],
      "workflow.controls[]": [ "运行控制钩子", "Runtime control hooks" ],
    };
    if (labels[surface]) {
      return localeText(labels[surface][0], labels[surface][1]);
    }
    if (surface.startsWith("spec.markdown#")) {
      return localeText("Loop 契约章节", "Loop contract section");
    }
    if (surface.startsWith("role_definitions[]")) {
      return localeText("角色运行契约", "Role runtime contract");
    }
    if (surface.startsWith("workflow.")) {
      return localeText("运行流程契约", "Run-flow contract");
    }
    return localeText("可运行合同面", "Runnable contract surface");
  }

  function humanSurfaceSummary(surfaces) {
    const seen = new Set();
    const values = (surfaces || [])
      .map((value) => traceSurfaceLabel(value))
      .filter(Boolean)
      .filter((value) => {
        if (seen.has(value)) {
          return false;
        }
        seen.add(value);
        return true;
      });
    return values.slice(0, 2).join(" / ") || localeText("可运行合同面", "Runnable contract surface");
  }

  function traceEvidencePreview(item) {
    const evidence = (item?.evidence || []).map((value) => String(value || "").trim()).filter(Boolean)[0] || "";
    if (evidence.length <= 180) {
      return evidence;
    }
    return `${evidence.slice(0, 177).trimEnd()}...`;
  }

  function localizedDiagnosticText(item, field) {
    const zh = item?.[`${field}_zh`] || item?.[field];
    const en = item?.[`${field}_en`] || item?.[field];
    return localeText(zh || "", en || "");
  }

  function renderJudgmentMap(traceability, diagnostics = []) {
    if (!judgmentMap || !diagnosticsStrip) {
      return;
    }
    const items = Array.isArray(traceability?.items) ? traceability.items : [];
    const visibleItems = items.slice(0, 12);
    if (!visibleItems.length) {
      judgmentMap.hidden = true;
      judgmentMap.innerHTML = "";
    } else {
      judgmentMap.hidden = false;
      judgmentMap.innerHTML = visibleItems.map((item) => {
        const evidence = traceEvidencePreview(item);
        const surface = humanSurfaceSummary(item.surfaces);
        const mapped = item.mapped === true;
        const mapping = mapped
          ? localeText(`已投影到：${surface}`, `Mapped into: ${surface}`)
          : localeText("缺少可运行映射", "Missing runnable mapping");
        return `
          <div class="alignment-judgment-row" data-mapped="${mapped}">
            <strong>${escapeHtml(traceItemLabel(item))}</strong>
            <span>${escapeHtml(mapping)}</span>
            ${evidence ? `<span class="alignment-judgment-evidence">${escapeHtml(evidence)}</span>` : ""}
          </div>
        `;
      }).join("");
    }

    const visibleDiagnostics = (diagnostics || [])
      .filter((item) => item && String(item.severity || "") !== "info")
      .slice(0, 3);
    if (!visibleDiagnostics.length) {
      diagnosticsStrip.hidden = true;
      diagnosticsStrip.innerHTML = "";
      return;
    }
    diagnosticsStrip.hidden = false;
    diagnosticsStrip.innerHTML = visibleDiagnostics.map((item) => `
      <div class="alignment-diagnostic-row">
        <strong>${escapeHtml(localizedDiagnosticText(item, "title"))}</strong>
        <span>${escapeHtml(localizedDiagnosticText(item, "message"))}</span>
      </div>
    `).join("");
  }

  function compactRoleSummary(role) {
    const description = String(role.description || "").trim();
    const posture = String(role.posture_notes || "").trim();
    return description || posture || localeText("点击查看完整角色信息。", "Open to inspect the full role definition.");
  }

  function roleDetailRow(label, value, options = {}) {
    const text = String(value || "").trim();
    if (!text) {
      return "";
    }
    const body = options.pre
      ? `<pre>${escapeHtml(text)}</pre>`
      : `<dd>${escapeHtml(text)}</dd>`;
    return `<div><dt>${escapeHtml(label)}</dt>${body}</div>`;
  }

  function renderRoleCard(role) {
    const item = document.createElement("details");
    item.className = "alignment-role-card";
    item.dataset.testid = "alignment-role-card";
    const name = role.name || role.key || "role";
    const archetype = role.archetype || "";
    const executor = [
      role.executor_kind,
      role.model,
      role.reasoning_effort,
    ].filter(Boolean).join(" · ");
    item.innerHTML = `
      <summary class="alignment-role-summary" data-testid="alignment-role-toggle">
        <span class="alignment-role-title">
          <strong>${escapeHtml(name)}</strong>
          <em>${escapeHtml(archetype)}</em>
        </span>
        <span class="alignment-role-brief">${escapeHtml(compactRoleSummary(role))}</span>
      </summary>
      <dl class="alignment-role-details">
        ${roleDetailRow("key", role.key)}
        ${roleDetailRow("archetype", archetype)}
        ${roleDetailRow("description", role.description)}
        ${roleDetailRow("posture_notes", role.posture_notes)}
        ${roleDetailRow("executor", executor)}
        ${roleDetailRow("executor_mode", role.executor_mode)}
        ${roleDetailRow("command_cli", role.command_cli)}
        ${roleDetailRow("command_args_text", role.command_args_text, {pre: true})}
        ${roleDetailRow("prompt_ref", role.prompt_ref)}
        ${roleDetailRow("prompt_markdown", role.prompt_markdown, {pre: true})}
      </dl>
    `;
    return item;
  }

  function selectPreviewTab(tabName, {remember = true, focus = false} = {}) {
    const buttons = Array.from(readyPreview.querySelectorAll("[data-preview-tab]"));
    const requested = String(tabName || "").trim();
    const resolved = buttons.some((button) => button.dataset.previewTab === requested)
      ? requested
      : (buttons.some((button) => button.dataset.previewTab === "review") ? "review" : (buttons[0]?.dataset.previewTab || "spec"));
    if (remember) {
      selectedPreviewTab = resolved;
    }
    let activeButton = null;
    buttons.forEach((button) => {
      const active = button.dataset.previewTab === resolved;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
      if (active) {
        activeButton = button;
      }
    });
    readyPreview.querySelectorAll("[data-preview-panel]").forEach((section) => {
      section.hidden = section.dataset.previewPanel !== resolved;
    });
    if (focus) {
      activeButton?.focus();
    }
  }

  function preparePreviewNavigation({sessionId = "", surfaceState = "", defaultTab = "review"} = {}) {
    const normalizedSessionId = String(sessionId || "");
    const normalizedState = String(surfaceState || "");
    if (previewTabSessionId !== normalizedSessionId || previewSurfaceState !== normalizedState) {
      selectedPreviewTab = defaultTab;
    }
    previewTabSessionId = normalizedSessionId;
    previewSurfaceState = normalizedState;
    selectPreviewTab(selectedPreviewTab, {remember: false});
  }

  function revealReadyPreviewStart() {
    const anchor = readyPreview.querySelector(".alignment-artifact-head") || readyPreview;
    anchor.scrollIntoView({block: "start", behavior: "auto"});
  }

  function renderBundlePreview(payload, options = {}) {
    shell?.classList.add("has-artifact");
    readyPreview.hidden = false;
    const sessionStatus = String(payload.session?.status || currentSession?.status || "");
    const linkedRunId = String(payload.session?.linked_run_id || currentSession?.linked_run_id || "").trim();
    const allowReadyRun = options.allowImport !== false && sessionStatus === "ready";
    const allowLinkedRun = options.allowImport !== false && sessionStatus === "running_loop" && Boolean(linkedRunId);
    const allowAction = allowReadyRun || allowLinkedRun;
    const agentEntryLaunch = agentEntryProjectionFor(payload);
    const agentLaunch = agentEntryLaunchFor(payload, allowAction);
    const surfaceState = allowLinkedRun ? "linked-run" : (allowReadyRun ? "ready" : "repair");
    const allowSaveOnly = allowReadyRun && !agentLaunch;
    readyPreview.dataset.previewState = surfaceState;
    readyPreview.dataset.launchMode = agentEntryLaunch ? "agent-entry" : "web-run";
    if (readyActions) {
      readyActions.hidden = !allowAction;
    }
    if (readySaveAction) {
      readySaveAction.hidden = !allowSaveOnly;
    }
    if (readyRunAction) {
      readyRunAction.hidden = !allowAction;
    }
    setBilingualText(
      readySaveDescription,
      "不启动 Run；之后从 Loop 详情继续。",
      "Does not start a Run; continue later from Loop detail.",
    );
    if (importSaveButton) {
      importSaveButton.hidden = !allowSaveOnly;
      importSaveButton.disabled = !allowSaveOnly;
    }
    if (importRunButton) {
      importRunButton.hidden = !allowAction;
      importRunButton.disabled = !allowAction;
      importRunButton.dataset.launchAction = agentLaunch?.linked_run_id ? "open-linked-run" : (agentLaunch ? "copy-agent-loop" : "web-run");
      if (agentLaunch?.linked_run_id) {
        importRunButton.dataset.runId = agentLaunch.linked_run_id;
        delete importRunButton.dataset.copyValue;
        setBilingualText(importRunButton, "打开运行", "Open run");
        setBilingualText(readyRunTitle, "查看运行", "View run");
        setBilingualText(
          readyRunDescription,
          "打开已由同一 Agent 启动的 Run；Web 不会再次启动运行。",
          "Open the Run already started by the same Agent; Web will not start it again.",
        );
      } else if (agentLaunch) {
        delete importRunButton.dataset.runId;
        importRunButton.dataset.copyValue = agentLaunch.slash_command || "/loopora-run";
        setBilingualText(importRunButton, "复制 /loopora-run", "Copy /loopora-run");
        setBilingualText(readyRunTitle, "回到同一 Agent", "Continue in the same Agent");
        setBilingualText(
          readyRunDescription,
          "复制命令并回到生成方案的 Agent；Web 不会替你启动 Run。",
          "Copy the command and return to the Agent that created the plan; Web will not start a Run.",
        );
      } else if (allowAction) {
        delete importRunButton.dataset.runId;
        delete importRunButton.dataset.copyValue;
        setBilingualText(importRunButton, "创建并运行", "Create and run");
        setBilingualText(readyRunTitle, "立即运行", "Run now");
        setBilingualText(
          readyRunDescription,
          "立即启动第一个 Web Run。",
          "Starts the first Web Run immediately.",
        );
      } else {
        delete importRunButton.dataset.runId;
        delete importRunButton.dataset.copyValue;
        setBilingualText(importRunButton, agentEntryLaunch ? "修复后回到 Agent" : "修复后运行", agentEntryLaunch ? "Repair before Agent run" : "Repair before running");
      }
    }
    if (revisePreviewButton) {
      const canRevisePreview = Boolean(currentSession?.id) && sessionStatus === "ready";
      revisePreviewButton.hidden = !canRevisePreview;
      revisePreviewButton.disabled = !canRevisePreview;
    }
    const metadata = payload.metadata || payload.bundle?.metadata || {};
    artifactName.textContent = metadata.name || localeText("Loop 方案", "Loop plan");
    previewTitle.textContent = agentLaunch?.linked_run_id
      ? localeText("Loop 已在 Agent 中运行", "Loop is running in the Agent")
      : agentLaunch
      ? localeText("Loop 已准备好，回到 Agent 运行", "Plan is ready for the Agent")
      : allowReadyRun
      ? localeText("Loop 已准备好，复核后选择下一步", "Plan is ready; review and choose the next step")
      : agentEntryLaunch
      ? localeText("候选方案需要修复后再回到 Agent", "Candidate plan needs repair before returning to the Agent")
      : localeText("方案文件需要修复后才能运行", "Plan file needs repair before running");
    const repairError = String(options.repairNote || payload.validation?.error || "").trim();
    readyNote.textContent = allowAction
      ? agentLaunch?.linked_run_id
        ? localeText(
          "这份预览已通过 /loopora-run 启动；Web 负责呈现证据与运行状态，继续执行仍回到同一个 Agent。",
          "This preview has been launched through /loopora-run; Web keeps evidence and run state visible, while execution still returns to the same Agent."
        )
        : agentLaunch
        ? localeText(
          "这份预览来自 /loopora-plan；用同一个 Agent 执行 /loopora-run，才能保留宿主交接。",
          "This preview came from /loopora-plan; run /loopora-run in the same Agent to preserve the host handoff."
        )
        : localeText(
          "READY 只表示方案通过硬校验；确认判断地图、证据路径和运行目录后，再保存 Loop 或立即运行。",
          "READY only means the plan passed hard validation; confirm the judgment map, evidence path, and run directory, then save the Loop or run it now."
        )
      : agentEntryLaunch
      ? localeText(
        "候选方案尚未通过校验。先修源候选文件，再重新运行 /loopora-plan；只有预览 READY 后，才回到同一个 Agent 执行 /loopora-run。",
        "The candidate plan has not passed validation. Repair the source candidate file, then rerun /loopora-plan; return to the same Agent for /loopora-run only after the preview is READY."
      )
      : localeText(
        "候选方案尚未通过校验。按下面的修复焦点改源文件，重新同步后再运行。",
        "The candidate plan has not passed validation. Repair the source file using the focus list below, then reload before running."
      );
    renderAgentLaunchGuide(agentLaunch);
    renderRepairGuide({
      visible: !allowAction,
      error: repairError,
      sourcePath: payload.source_path || currentSession?.bundle_path || "",
      sessionId: currentSession?.id || payload.session?.id || "",
      agentEntry: agentEntryLaunch,
    });
    const summary = payload.control_summary || {};
    const diagnostics = payload.diagnostics || summary.diagnostics || [];
    if (artifactRisk) {
      const risk = primaryRiskSummary(summary);
      artifactRisk.textContent = labeledSummary("最大风险", "Risk", risk);
      artifactRisk.title = risk;
    }
    if (artifactEvidence) {
      const evidenceText = evidencePathSummary(summary);
      artifactEvidence.textContent = labeledSummary("证据", "Evidence", evidenceStatus(summary));
      artifactEvidence.title = evidenceText;
    }
    if (artifactJudgment) {
      artifactJudgment.textContent = labeledSummary("判断", "Judgment", judgmentStatus({...summary, diagnostics}));
      artifactJudgment.title = evidencePathSummary(summary);
    }
    if (artifactVerdict) {
      artifactVerdict.textContent = labeledSummary("裁决", "Verdict", summary?.gatekeeper?.enabled === true ? "GateKeeper" : verdictSummary(summary));
      artifactVerdict.title = verdictSummary(summary);
    }
    artifactWorkdir.textContent = labeledSummary("运行目录", "Run directory", basename(payload.bundle?.loop?.workdir || ""));
    artifactWorkdir.title = payload.bundle?.loop?.workdir || "";
    renderReadyReviewGate({required: allowReadyRun && !agentLaunch, summary, diagnostics});
    renderControlSummary(summary);
    renderJudgmentMap(payload.traceability || summary.traceability || {}, diagnostics);
    specPreview.innerHTML = payload.spec_rendered_html || "";
    if (sourceOpenButton) {
      sourceOpenButton.hidden = !payload.source_path;
      sourceOpenButton.dataset.sourcePath = payload.source_path || "";
      sourceOpenButton.title = payload.source_path || "";
    }
    if (sourceSyncButton) {
      sourceSyncButton.hidden = !payload.source_path;
    }
    if (artifactSource) {
      artifactSource.hidden = !payload.source_path;
    }
    if (sourcePathLabel) {
      sourcePathLabel.textContent = "";
      sourcePathLabel.title = payload.source_path || "";
    }
    roleList.innerHTML = "";
    (payload.roles || []).forEach((role) => {
      roleList.append(renderRoleCard(role));
    });
    if (window.LooporaWorkflowDiagram) {
      window.LooporaWorkflowDiagram.renderInto(workflowDiagram, payload.workflow_preview || {}, {variant: "editor"});
    }
    preparePreviewNavigation({
      sessionId: payload.session?.id || currentSession?.id || "",
      surfaceState,
      defaultTab: "review",
    });
    if (options.reveal !== false) {
      revealReadyPreviewStart();
    }
  }

  function agentEntryProjectionFor(payload) {
    const session = payload?.session || currentSession || {};
    const launch = session.agent_entry_launch || {};
    if (launch.source !== "agent_entry") {
      return null;
    }
    return launch;
  }

  function agentEntryLaunchFor(payload, allowAction) {
    if (!allowAction) {
      return null;
    }
    const session = payload?.session || currentSession || {};
    const launch = agentEntryProjectionFor(payload);
    if (!launch) {
      return null;
    }
    const linkedRunId = String(session.linked_run_id || "").trim();
    return linkedRunId ? {...launch, linked_run_id: linkedRunId} : launch;
  }

  function renderAgentLaunchGuide(launch) {
    if (!agentLaunchGuide) {
      return;
    }
    if (!launch) {
      agentLaunchGuide.hidden = true;
      agentLaunchGuide.innerHTML = "";
      return;
    }
    const adapter = adapterDisplayName(String(launch.adapter || "agent").trim());
    const slashCommand = String(launch.slash_command || "/loopora-run").trim();
    const loopCommand = String(launch.loop_command || "").trim();
    const workdir = String(launch.workdir || "").trim();
    const linkedRunId = String(launch.linked_run_id || "").trim();
    const linkedRunHref = linkedRunId ? window.LooporaUI.workdirContextHref(`/runs/${encodeURIComponent(linkedRunId)}`, workdir) : "";
    const slashCopyButton = renderAgentLaunchCopyButton(
      slashCommand,
      "alignment-agent-launch-copy-slash",
      "复制同一 Agent slash 命令",
      "Copy same-Agent slash command"
    );
    const cliCopyButton = renderAgentLaunchCopyButton(
      loopCommand,
      "alignment-agent-launch-copy-cli",
      "复制 CLI fallback 命令",
      "Copy CLI fallback command"
    );
    agentLaunchGuide.hidden = false;
    agentLaunchGuide.innerHTML = `
      <div class="alignment-agent-launch-copy">
        <span class="alignment-agent-launch-kicker">${escapeHtml(localeText("同一 Agent 运行", "Same-Agent run"))}</span>
        <strong>${escapeHtml(linkedRunId
          ? localeText(`当前运行已绑定 ${adapter}`, `Current run is bound to ${adapter}`)
          : localeText(`回到 ${adapter} 执行 /loopora-run`, `Return to ${adapter} and run /loopora-run`))}</strong>
        <p>${escapeHtml(localeText(
          linkedRunId
            ? "Web 只负责查看运行证据和当前交接；下一步执行仍回到宿主 Agent，避免改走后台 worker。"
            : "Web 已完成审查面；运行必须回到宿主 Agent，让 Builder、Inspector 和 GateKeeper 通过原生交接执行。",
          linkedRunId
            ? "Web only shows run evidence and the current handoff; the next execution step still returns to the host Agent instead of a background worker."
            : "Web has finished the review surface; execution must return to the host Agent so Builder, Inspector, and GateKeeper run through native handoff."
        ))}</p>
      </div>
      <div class="alignment-agent-launch-commands">
        <div class="alignment-agent-launch-command-block">
          <span>${escapeHtml(localeText("Slash command", "Slash command"))}</span>
          <div class="alignment-agent-launch-command-row">
            <code data-testid="alignment-agent-launch-slash" data-agent-entry-slash-command-value>${escapeHtml(slashCommand)}</code>
            ${slashCopyButton}
          </div>
        </div>
        ${loopCommand ? `
          <div class="alignment-agent-launch-command-block">
            <span>${escapeHtml(localeText("CLI fallback", "CLI fallback"))}</span>
            <div class="alignment-agent-launch-command-row">
              <code data-testid="alignment-agent-launch-cli" data-agent-entry-command-value>${escapeHtml(loopCommand)}</code>
              ${cliCopyButton}
            </div>
          </div>
        ` : ""}
        ${workdir ? `
          <div class="alignment-agent-launch-command-block">
            <span>${escapeHtml(localeText("Workdir", "Workdir"))}</span>
            <code title="${escapeHtml(workdir)}">${escapeHtml(workdir)}</code>
          </div>
        ` : ""}
        ${linkedRunHref ? `<a class="secondary-button alignment-agent-launch-run-link" href="${escapeHtml(linkedRunHref)}" data-testid="alignment-agent-launch-run-link">${escapeHtml(localeText("打开当前运行", "Open current run"))}</a>` : ""}
        <p class="alignment-agent-launch-copy-status" data-alignment-agent-copy-status aria-live="polite"></p>
        <div class="alignment-agent-launch-manual-copy" data-alignment-agent-command-manual-copy data-testid="alignment-agent-command-manual-copy" hidden></div>
      </div>
    `;
    bindAgentLaunchGuideCopyButtons();
  }

  function renderAgentLaunchCopyButton(value, testId, zhLabel, enLabel) {
    const command = String(value || "").trim();
    if (!command) {
      return "";
    }
    return `
      <button
        class="ghost-button alignment-agent-launch-copy-button"
        type="button"
        data-alignment-agent-command-copy
        data-agent-entry-command-copy
        data-copy-value="${escapeHtml(command)}"
        data-testid="${escapeHtml(testId)}"
        aria-label="${escapeHtml(localeText(zhLabel, enLabel))}"
      >
        <span aria-hidden="true">⧉</span>
        <span class="sr-only">
          <span data-lang="zh">${escapeHtml(zhLabel)}</span>
          <span data-lang="en">${escapeHtml(enLabel)}</span>
        </span>
      </button>
    `;
  }

  function setAgentLaunchCopyStatus(button, message) {
    const status = agentLaunchGuide?.querySelector("[data-alignment-agent-copy-status]");
    button?.classList.add("is-copied");
    if (status) {
      status.textContent = message || "";
    }
    if (agentLaunchCopyTimer) {
      window.clearTimeout(agentLaunchCopyTimer);
    }
    agentLaunchCopyTimer = window.setTimeout(() => {
      button?.classList.remove("is-copied");
      if (status && status.textContent === message) {
        status.textContent = "";
      }
    }, 1800);
  }

  function renderAgentLaunchManualCopy(command) {
    const container = agentLaunchGuide?.querySelector?.("[data-alignment-agent-command-manual-copy]");
    window.LooporaUI?.renderManualCopy?.(container, command, {
      label: localeText("手动复制 Agent 命令", "Manual Agent command copy"),
      textareaId: "alignment-agent-command-manual-copy-textarea",
      rows: 4,
    });
  }

  function bindAgentLaunchGuideCopyButtons() {
    agentLaunchGuide?.querySelectorAll("[data-alignment-agent-command-copy]").forEach((button) => {
      button.addEventListener("click", async () => {
        const command = String(button.dataset.copyValue || "").trim();
        if (!command) {
          setAgentLaunchCopyStatus(button, localeText("没有可复制的 Agent 命令。", "No Agent command is available to copy."));
          return;
        }
        renderAgentLaunchManualCopy("");
        try {
          await writeClipboardText(command);
          setAgentLaunchCopyStatus(button, localeText("命令已复制。回到同一 Agent 会话粘贴运行。", "Command copied. Paste it in the same Agent session."));
        } catch (_) {
          renderAgentLaunchManualCopy(command);
          setAgentLaunchCopyStatus(button, localeText("浏览器未允许自动复制；请手动复制下面的 Agent 命令。", "The browser blocked automatic copy; copy the Agent command below manually."));
        }
      });
    });
  }

  function adapterDisplayName(adapter) {
    const normalized = String(adapter || "").toLowerCase();
    if (normalized === "codex") {
      return "Codex";
    }
    if (normalized === "claude") {
      return "Claude Code";
    }
    if (normalized === "opencode") {
      return "OpenCode";
    }
    return adapter || "Agent";
  }

  function renderRepairGuide({visible, error, sourcePath, sessionId, agentEntry}) {
    if (!repairGuide) {
      return;
    }
    if (!visible) {
      repairGuide.hidden = true;
      repairGuide.innerHTML = "";
      return;
    }
    const isAgentEntryRepair = (agentEntry?.source || currentSession?.agent_entry_launch?.source) === "agent_entry";
    const hints = repairHints(error, {agentEntry: isAgentEntryRepair});
    const source = String(sourcePath || "").trim();
    const rawError = String(error || "").trim();
    const repairMessage = isAgentEntryRepair
      ? localeText(
        "这不是运行失败，也不是 Web 创建运行入口。候选方案还没有把宿主 Agent 的任务判断编译成可运行 Loop；先修源候选文件，重新运行 /loopora-plan，READY 后回到同一个 Agent 执行 /loopora-run。",
        "This is not a run failure and not a Web create-run entry. The candidate plan has not compiled the host Agent task judgment into a runnable Loop yet; repair the source candidate file, rerun /loopora-plan, then return to the same Agent for /loopora-run after READY."
      )
      : localeText(
        "这不是运行失败，而是候选方案还没有把任务判断编译成可运行 Loop。先修方案文件，再重新同步；通过校验前不会允许创建运行。",
        "This is not a run failure. The candidate plan has not yet compiled task judgment into a runnable Loop. Repair the plan file, then reload; creation stays disabled until validation passes."
      );
    repairGuide.hidden = false;
    repairGuide.innerHTML = `
      <div class="alignment-repair-guide-copy">
        <span class="alignment-repair-guide-kicker">${escapeHtml(localeText("下一步修复", "Repair next"))}</span>
        <strong>${escapeHtml(isAgentEntryRepair
          ? localeText("修复候选方案，再回到同一个 Agent。", "Repair the candidate plan, then return to the same Agent.")
          : localeText("把校验错误转成方案修复，而不是继续运行。", "Turn validation errors into plan repair before running."))}</strong>
        <p>${escapeHtml(repairMessage)}</p>
      </div>
      <ol class="alignment-repair-steps">
        ${hints.map((hint) => `<li>${escapeHtml(hint)}</li>`).join("")}
      </ol>
      <div class="alignment-repair-meta">
        ${source ? `<code title="${escapeHtml(source)}">${escapeHtml(source)}</code>` : ""}
        ${sessionId ? `<span>${escapeHtml(localeText(`对话 ${sessionId}`, `Session ${sessionId}`))}</span>` : ""}
      </div>
      ${rawError ? `
        <details class="alignment-repair-raw">
          <summary>${escapeHtml(localeText("查看原始校验错误", "Show raw validation error"))}</summary>
          <p>${escapeHtml(rawError)}</p>
        </details>
      ` : ""}
    `;
  }

  function repairHints(error, options = {}) {
    const text = String(error || "");
    const hints = [];
    if (text.includes("spec Task must describe the concrete user-facing task")) {
      hints.push(localeText(
        "在 # Task 里写清真实用户结果和业务对象，例如谁在什么页面完成什么退款动作；不要只写治理或内部流程。",
        "Make # Task state the real user outcome and domain object, not only governance or internal process."
      ));
    }
    if (text.includes("must follow the user-facing task language")) {
      hints.push(localeText(
        "可见名称、任务契约、角色名称和角色姿态都要使用用户面对的任务语言；Loopora 专有词可以保留。",
        "Keep visible names, task contract, role names, and role posture in the user's language; Loopora terms may remain."
      ));
    }
    if (
      text.includes("host Agent task context") ||
      text.includes("project the host Agent task context") ||
      text.includes("host Agent task summary") ||
      text.includes("project the host Agent task summary")
    ) {
      hints.push(localeText(
        "把 /loopora-plan 任务上下文里的高信号对象写进 spec、角色责任、运行意图和证据规则。",
        "Project high-signal objects from the /loopora-plan task context into spec, role responsibilities, run intent, and evidence rules."
      ));
    }
    if (text.includes("evidence preferences") || text.includes("explicit host Agent evidence")) {
      hints.push(localeText(
        "把必需证据模式落到可运行 surface：测试、命令、浏览器 journey、日志、审计或权限/支付证明，而不是只放在摘要里。",
        "Compile required evidence modes into runnable surfaces: tests, commands, browser journeys, logs, audit, or permission/payment proof."
      ));
    }
    if (text.includes("Loopora fit") || text.includes("one-off") || text.includes("no-new-evidence")) {
      hints.push(localeText(
        "说明后续轮次会新增什么证据、handoff、GateKeeper 裁决或残余风险跟踪；否则这件事可能不适合开 Loop。",
        "Explain what later rounds add: new evidence, handoffs, GateKeeper verdict, or residual-risk tracking; otherwise this may not need a Loop."
      ));
    }
    if (!hints.length) {
      hints.push(localeText(
        "先修复最上面的结构或语义错误，再重新同步；如果错误仍然抽象，打开源文件检查 task、证据、角色责任和裁决规则是否一致。",
        "Fix the top structural or semantic error first, then reload; if the error is still abstract, inspect whether task, evidence, role duties, and verdict rules agree."
      ));
    }
    if (options.agentEntry) {
      hints.push(localeText(
        "修完候选文件后重新执行 /loopora-plan；只有看到“Loop 已准备好，回到 Agent 运行”后，才在同一个 Agent 会话执行 /loopora-run。",
        "After editing the candidate file, rerun /loopora-plan; run /loopora-run in the same Agent session only after the preview says the plan is ready for the Agent."
      ));
    } else {
      hints.push(localeText(
        "修完后点击“重新同步”；只有看到“Loop 已准备好，先复核再运行”并确认运行前复核后，才使用页面里的创建 / 运行入口。",
        "After editing, click Reload; use the page's create/run action only after the preview says the Loop is ready for review and the pre-run review is confirmed."
      ));
    }
    return hints.slice(0, 5);
  }

  async function copySourcePath(path) {
    if (!path) {
      return;
    }
    window.LooporaUI?.renderGlobalManualCopy?.("");
    try {
      await writeClipboardText(path);
      showError(localeText("源文件路径已复制。", "Source path copied."));
    } catch (_) {
      window.LooporaUI?.renderGlobalManualCopy?.(path, {
        label: localeText("手动复制源文件路径", "Manual source path copy"),
        textareaId: "alignment-source-path-manual-copy-textarea",
      });
      showError(localeText("浏览器未允许自动复制；请手动复制页面底部的源文件路径。", "The browser blocked automatic copy; copy the source path at the bottom of the page manually."));
    }
  }

  async function revealSourcePath(path, options = {}) {
    if (!path) {
      return;
    }
    if (options.copyOnly) {
      await copySourcePath(path);
      return;
    }
    try {
      await fetchJson("/api/system/reveal-path", {
        method: "POST",
        body: JSON.stringify({path}),
      });
    } catch (error) {
      try {
        await writeClipboardText(path);
        window.LooporaUI?.renderGlobalManualCopy?.("");
        showError(localeText("无法自动打开，路径已复制到剪贴板。", "Could not open automatically. The path was copied to your clipboard."));
      } catch (_) {
        window.LooporaUI?.renderGlobalManualCopy?.(path, {
          label: localeText("手动复制源文件路径", "Manual source path copy"),
          textareaId: "alignment-source-path-manual-copy-textarea",
        });
        showError(error.message || localeText("无法自动打开或复制源文件路径；请手动复制页面底部的路径。", "Unable to open or copy the source path automatically; copy the path at the bottom of the page manually."));
      }
    }
  }

  async function syncReadyBundle() {
    if (!currentSession?.id) {
      return;
    }
    if (sourceSyncButton) {
      sourceSyncButton.disabled = true;
    }
    try {
      const payload = await fetchJson(`/api/alignments/sessions/${encodeURIComponent(currentSession.id)}/bundle/sync`, {
        method: "POST",
        body: "{}",
      });
      if (payload.session) {
        currentSession = payload.session;
        renderTranscript(currentSession.transcript || [], currentSession);
        renderSessionStatus(currentSession);
        setExecutionState(currentSession.status);
      }
      if (!payload.ok) {
        renderAlignmentRecovery(payload, {
          testid: "alignment-sync-recovery",
          title: localeText("先修复 Plan File 后再同步", "Fix the Plan File before syncing again"),
        });
        renderBundleLoadError(payload.validation?.error || localeText("源文件校验失败。", "Source validation failed."));
        await loadHistory();
        return;
      }
      clearRecoveryPanel();
      renderBundlePreview(payload, {reveal: true});
      await loadHistory();
    } finally {
      if (sourceSyncButton) {
        sourceSyncButton.disabled = false;
      }
    }
  }

  async function importReadyBundle({startImmediately}) {
    if (!currentSession?.id) {
      return false;
    }
    if (readyReviewGateRequired() && reviewGateCheckbox?.checked !== true) {
      showError(localeText("先确认 READY 复核，再选择保存或运行。", "Confirm the READY review before saving or running."));
      reviewGate?.scrollIntoView({block: "nearest", behavior: "smooth"});
      reviewGateCheckbox?.focus();
      updateReadyReviewGateActions();
      return false;
    }
    [importSaveButton, importRunButton].forEach((button) => {
      if (button) {
        button.dataset.busy = "true";
        button.disabled = true;
      }
    });
    setAlignmentRecoveryActionButtonsDisabled(true);
    let redirecting = false;
    try {
      const response = await fetchJson(`/api/alignments/sessions/${encodeURIComponent(currentSession.id)}/import`, {
        method: "POST",
        body: JSON.stringify({start_immediately: startImmediately}),
      });
      redirecting = true;
      window.location.assign(window.LooporaUI.workdirContextRedirectUrl(response.redirect_url, {
        fallback: "/",
        workdir: currentAlignmentWorkdir(),
      }));
      return true;
    } catch (error) {
      renderRecoveryFromError(error, {
        testid: "alignment-import-recovery",
        title: localeText("先修复 Plan File 后再重试", "Fix the Plan File before retrying"),
      });
      showError(error.message || (startImmediately
        ? localeText("创建或运行失败，方案源文件已保留。", "Creation or run failed; the plan source file is preserved.")
        : localeText("保存失败，方案源文件已保留。", "Save failed; the plan source file is preserved.")));
      return false;
    } finally {
      if (!redirecting) {
        [importSaveButton, importRunButton].forEach((button) => {
          if (button) {
            delete button.dataset.busy;
          }
        });
        updateReadyReviewGateActions();
        setAlignmentRecoveryActionButtonsDisabled(false);
      }
    }
  }

  async function createSession(payload) {
    const response = await fetchJson("/api/alignments/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    latestEventId = 0;
    consoleOutput.innerHTML = "";
    renderSession(response.session);
    await loadSeedEvents(response.session.id);
    openStream(response.session.id);
    await loadHistory();
  }

  async function appendMessage(message) {
    const response = await fetchJson(`/api/alignments/sessions/${encodeURIComponent(currentSession.id)}/messages`, {
      method: "POST",
      body: JSON.stringify({message}),
    });
    renderSession(response.session);
    openStream(response.session.id);
    await loadHistory();
  }

  async function retryAlignmentGeneration() {
    if (!currentSession?.id || !["retry_alignment_generation", "resume_interrupted_planning"].includes(failureRecovery(currentSession).kind)) {
      return;
    }
    if (await executorReadinessBlocksSubmission()) {
      return;
    }
    const response = await fetchJson(
      `/api/alignments/sessions/${encodeURIComponent(currentSession.id)}/retry-generation`,
      {
        method: "POST",
        body: JSON.stringify(collectExecutorSettingsPayload()),
      },
    );
    renderSession(response.session);
    await loadSeedEvents(response.session.id);
    openStream(response.session.id);
    await loadHistory();
  }

  async function cancelCurrentSession() {
    if (!currentSession?.id || !isActiveStatus(currentSession.status)) {
      return;
    }
    cancelPending = true;
    setExecutionState(currentSession.status);
    try {
      const response = await fetchJson(`/api/alignments/sessions/${encodeURIComponent(currentSession.id)}/cancel`, {
        method: "POST",
        body: "{}",
      });
      renderSession(response.session);
      await loadHistory();
    } catch (error) {
      showError(error.message || localeText("取消失败。", "Failed to cancel."));
    } finally {
      cancelPending = false;
      setExecutionState(currentSession?.status || "idle");
    }
  }

  startForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearTransientError();
    if (isActiveStatus(currentSession?.status || "")) {
      const latestSession = await refreshSession().catch(() => currentSession);
      if (isActiveStatus(latestSession?.status || "")) {
        await cancelCurrentSession();
        return;
      }
    }
    if (directPathBlocksWebStart()) {
      return;
    }
    const additionalMessage = messageInput.value.trim();
    const judgmentBrief = collectJudgmentBrief();
    const hasJudgmentBrief = judgmentBriefHasAnyValue(judgmentBrief);
    const missingJudgmentInputs = missingJudgmentFields(judgmentBrief);
    if (!additionalMessage && !hasJudgmentBrief) {
      if (currentSession?.id) {
        showError(localeText("先写一条回复。", "Write a reply first."));
        messageInput.focus();
      } else {
        setJudgmentValidationState(missingJudgmentInputs);
        showError(localeText("先用一句话说明要完成的任务。", "Describe the task in one sentence first."));
        taskGoalInput.focus();
      }
      return;
    }
    const composedMessage = hasJudgmentBrief ? composeJudgmentMessage(additionalMessage) : additionalMessage;
    if (await executorReadinessBlocksSubmission()) {
      return;
    }
    if (currentSession?.id && !ACTIVE_STATUSES.has(String(currentSession.status || ""))) {
      setBusy(true);
      try {
        await appendMessage(composedMessage);
        clearJudgmentBriefInputs();
        messageInput.value = "";
      } catch (error) {
        showError(error.message || localeText("发送回复失败。", "Failed to send reply."));
        setBusy(false);
      }
      return;
    }
    const payload = collectStartPayload();
    if (!payload.workdir) {
      showError(localeText("先选择这次 Loop 的运行目录。", "Choose the run directory for this Loop first."));
      openTools("workdir");
      return;
    }
    await loadWorkdirContext();
    if (shouldRequireWorkdirContextChoice()) {
      showError(localeText("这个运行目录已有 Loopora 产物，请先选择继续、改进或重新生成。", "This run directory has Loopora artifacts. Choose continue, improve, or start fresh first."));
      openTools("workdir");
      return;
    }
    const selectedOption = selectedWorkdirContextOption();
    if (selectedOption?.action === "continue_session" && selectedOption.session_id) {
      setBusy(true);
      try {
        await restoreSession(selectedOption.session_id);
        if (!isActiveStatus(currentSession?.status || "")) {
          await appendMessage(composedMessage);
          clearJudgmentBriefInputs();
          messageInput.value = "";
        }
        closeTools();
      } catch (error) {
        showError(error.message || localeText("继续已有对话失败。", "Failed to continue the existing chat."));
        setBusy(false);
      }
      return;
    }
    const missingJudgmentField = missingJudgmentInputs[0] || null;
    if (missingJudgmentField) {
      setJudgmentValidationState(missingJudgmentInputs);
      showError(localeText("先用一句话说明要完成的任务；其他判断可以留给对话逐步补齐。", "Describe the task first; the conversation can clarify the remaining judgment."));
      missingJudgmentField.focus();
      return;
    }
    setJudgmentValidationState();
    setBusy(true);
    try {
      await createSession(payload);
      clearRecoveryPanel();
      clearJudgmentBriefInputs();
      messageInput.value = "";
      closeTools();
    } catch (error) {
      renderRecoveryFromError(error, {testid: "alignment-session-start-recovery"});
      showError(error.message || localeText("启动对话失败。", "Failed to start conversation."));
      setBusy(false);
    }
  });

  messageInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || event.shiftKey || event.isComposing) {
      return;
    }
    event.preventDefault();
    if (isActiveStatus(currentSession?.status || "")) {
      showError(localeText("Agent 正在执行；当前输入会保留，需停止后再发送。", "The Agent is running; your draft is preserved and can be sent after stopping."));
      return;
    }
    startForm.requestSubmit();
  });

  [messageInput, taskGoalInput, looporaFitReasonInput, fakeDoneRiskInput, requiredEvidenceInput, judgmentTradeoffsInput].forEach((input) => {
    input?.addEventListener("input", () => clearTransientError());
  });
  document.addEventListener("loopora:localechange", () => {
    alignmentHistoryController.render();
    renderExecutorReadiness(executorReadinessState);
    renderAlignmentEntryPhase();
  });
  document.addEventListener("loopora:workdirchange", syncAlignmentDraftFromGlobalWorkdir);
  panel.querySelectorAll("[data-goal-zh][data-goal-en]").forEach((button) => {
    button.addEventListener("click", () => fillStarterPrompt(button));
  });
  workdirInput.addEventListener("input", () => {
    clearTransientError();
    workdirContextState = {
      workdir: workdirInput.value.trim(),
      options: [],
      requiresChoice: false,
      selectedOptionId: "",
      loaded: false,
    };
    renderWorkdirContext();
    scheduleWorkdirContextLoad();
    syncAlignmentWorkdirContext({syncUrl: true});
  });
  cancelButton.addEventListener("click", () => {
    cancelCurrentSession().catch(() => {});
  });

  newSessionButton.addEventListener("click", async () => {
    if (directPathBlocksWebStart()) {
      return;
    }
    if (await activeSessionBlocksNavigation(localeText(
      "Agent 正在执行；请先停止当前对话，再开始新对话。",
      "The Agent is running; stop the current conversation before starting a new one.",
    ))) {
      return;
    }
    const preservedWorkdir = currentSession?.workdir || workdirInput.value.trim();
    resetToEmptyConversation();
    if (preservedWorkdir) {
      workdirInput.value = preservedWorkdir;
      syncAlignmentWorkdirContext();
    }
    forgetSession();
    clearSessionIdFromUrl({preserveCurrentWorkdir: true});
    messageInput.focus();
    loadHistory().catch(() => {});
  });

  reviewGateCheckbox?.addEventListener("change", () => {
    updateReadyReviewGateActions();
  });

  importSaveButton?.addEventListener("click", async () => {
    await importReadyBundle({startImmediately: false});
  });

  importRunButton.addEventListener("click", async () => {
    if (!currentSession?.id) {
      return;
    }
    if (importRunButton.dataset.launchAction === "open-linked-run") {
      const runId = String(importRunButton.dataset.runId || "").trim();
      if (runId) {
        window.location.assign(window.LooporaUI.workdirContextHref(
          `/runs/${encodeURIComponent(runId)}`,
          currentAlignmentWorkdir(),
        ));
      }
      return;
    }
    if (importRunButton.dataset.launchAction === "copy-agent-loop") {
      const value = importRunButton.dataset.copyValue || "/loopora-run";
      window.LooporaUI?.renderGlobalManualCopy?.("");
      try {
        await writeClipboardText(value);
        importRunButton.classList.add("is-copied");
        setBilingualText(importRunButton, "已复制", "Copied");
        window.setTimeout(() => {
          importRunButton.classList.remove("is-copied");
          setBilingualText(importRunButton, "复制 /loopora-run", "Copy /loopora-run");
        }, 1400);
      } catch (_) {
        window.LooporaUI?.renderGlobalManualCopy?.(value, {
          label: localeText("手动复制 /loopora-run 命令", "Manual /loopora-run command copy"),
          textareaId: "alignment-run-command-manual-copy-textarea",
        });
        showError(localeText("浏览器未允许自动复制；请手动复制页面底部的 /loopora-run 命令。", "The browser blocked automatic copy; copy the /loopora-run command at the bottom of the page manually."));
      }
      return;
    }
    await importReadyBundle({startImmediately: true});
  });
  revisePreviewButton?.addEventListener("click", () => {
    const launch = currentSession?.agent_entry_launch || {};
    const agentEntryLaunch = launch?.source === "agent_entry";
    const draft = agentEntryLaunch
      ? localeText(
        "我想调整这份 Loop 预览，但保持同一 Agent 交接：审查后仍回到同一个 Agent 运行 /loopora-run。请改进：",
        "I want to revise this Loop preview while keeping the same-Agent handoff: after review, return to the same Agent and run /loopora-run. Please adjust:"
      )
      : localeText(
        "我想调整这份 Loop 预览：",
        "I want to revise this Loop preview:"
      );
    if (!messageInput.value.trim()) {
      messageInput.value = draft;
      messageInput.dispatchEvent(new Event("input", {bubbles: true}));
    }
    readyRevisionOpen = true;
    renderReadyRevisionComposer("ready");
    messageInput.focus();
    messageInput.setSelectionRange(messageInput.value.length, messageInput.value.length);
    scrollRegion?.scrollTo({top: scrollRegion.scrollHeight, behavior: "smooth"});
  });

  document.querySelectorAll("[data-open-panel]").forEach((button) => {
    button.addEventListener("click", () => {
      const panelName = button.dataset.openPanel || "workdir";
      if (!toolsMenu.hidden && toolsMenu.dataset.activePanel === panelName) {
        closeTools();
        return;
      }
      openTools(panelName);
    });
  });
  toolsCloseButton?.addEventListener("click", closeTools);
  liveToggle?.addEventListener("click", () => {
    setLiveDetailsOpen(!liveDetails?.classList.contains("is-open"));
  });
  sourceOpenButton?.addEventListener("click", () => {
    revealSourcePath(sourceOpenButton.dataset.sourcePath || currentSession?.bundle_path || "", {
      copyOnly: sourceOpenButton.dataset.pathActionMode === "copy",
    }).catch((error) => {
      showError(error.message || localeText("无法打开源文件。", "Unable to open the source file."));
    });
  });
  sourceSyncButton?.addEventListener("click", () => {
    syncReadyBundle().catch((error) => {
      renderBundleLoadError(error.message || localeText("无法重新同步源文件。", "Unable to reload the source file."));
    });
  });
  statusPill?.addEventListener("click", () => {
    if (String(currentSession?.status || "") !== "ready") {
      return;
    }
    loadReadyBundle({reveal: true}).catch((error) => {
      renderBundleLoadError(error.message || localeText("无法加载 Loop 方案。", "Unable to load the loop plan."));
    });
  });
  document.addEventListener("click", (event) => {
    if (toolsMenu.hidden) {
      return;
    }
    const target = event.target;
    if (!(target instanceof Element)) {
      return;
    }
    if (toolsMenu.contains(target) || target.closest("[data-open-panel]")) {
      return;
    }
    closeTools();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeTools();
      setLiveDetailsOpen(false);
    }
  });
  const previewTabs = Array.from(readyPreview.querySelectorAll("[data-preview-tab]"));
  previewTabs.forEach((button, index) => {
    button.addEventListener("click", () => selectPreviewTab(button.dataset.previewTab || "review"));
    button.addEventListener("keydown", (event) => {
      let nextIndex = null;
      if (event.key === "ArrowRight") {
        nextIndex = (index + 1) % previewTabs.length;
      } else if (event.key === "ArrowLeft") {
        nextIndex = (index - 1 + previewTabs.length) % previewTabs.length;
      } else if (event.key === "Home") {
        nextIndex = 0;
      } else if (event.key === "End") {
        nextIndex = previewTabs.length - 1;
      }
      if (nextIndex === null) {
        return;
      }
      event.preventDefault();
      selectPreviewTab(previewTabs[nextIndex].dataset.previewTab || "review", {focus: true});
    });
  });

  panel.querySelectorAll("[data-pick-directory][data-target-input]").forEach((button) => {
    button.addEventListener("click", async () => {
      const target = document.getElementById(button.dataset.targetInput || "");
      if (!target) {
        return;
      }
      const endpoint = button.dataset.pickEndpoint || "/api/system/pick-directory";
      try {
        const payload = await fetchJson(endpoint, {
          method: "POST",
          body: JSON.stringify({start_path: target.value.trim()}),
        });
        if (payload.path) {
          if (target === workdirInput) {
            setDraftWorkdirContext(payload.path, {syncUrl: true});
          } else {
            target.value = payload.path;
            updateChips();
          }
        }
      } catch (error) {
        showError(error.message || localeText("无法打开目录选择器。", "Could not open the directory picker."));
      }
    });
  });

  workdirInput.addEventListener("input", () => {
    updateChips();
    renderTutorialFitHandoffBridge();
  });
  workdirInput.addEventListener("change", () => {
    syncAlignmentWorkdirContext({syncUrl: true});
  });
  executorInput.addEventListener("change", () => {
    if (isCommandMode()) {
      saveCommandDraft(lastExecutorKind);
    }
    lastExecutorKind = executorInput.value;
    commandCliInput.dataset.autofilled = "true";
    commandArgsInput.dataset.autofilled = "true";
    updateExecutorControls({preserveUserModel: true, preserveUserEffort: true});
    scheduleExecutorReadiness();
  });
  modeButtons.forEach((chip) => {
    const input = chip.querySelector("input[name='alignment_executor_mode']");
    chip.addEventListener("click", (event) => {
      if (!input || input.disabled) {
        event.preventDefault();
        return;
      }
      event.preventDefault();
      setAlignmentMode(input.value || chip.dataset.alignmentModeChoice || "preset");
      try {
        input.focus({preventScroll: true});
      } catch {
        input.focus();
      }
    });
    input?.addEventListener("change", () => {
      if (!input.checked) {
        return;
      }
      const nextMode = input.value || chip.dataset.alignmentModeChoice || "preset";
      setAlignmentMode(nextMode);
    });
  });
  [modelInput, effortInput, commandCliInput, commandArgsInput].forEach((input) => {
    input?.addEventListener("input", () => {
      if (input === commandCliInput || input === commandArgsInput) {
        input.dataset.autofilled = "false";
      }
      scheduleExecutorReadiness();
    });
  });

  async function restoreSessionIfPresent() {
    const query = new URLSearchParams(window.location.search);
    const hasUrlSession = query.has("alignment_session_id");
    const hasExplicitWorkdirContext = query.has("workdir") || query.has("alignment_workdir");
    let sessionId = query.get("alignment_session_id") || "";
    if (!sessionId && !hasExplicitWorkdirContext) {
      try {
        sessionId = window.localStorage.getItem(SESSION_STORAGE_KEY) || "";
      } catch (_) {
        sessionId = "";
      }
    }
    if (!sessionId) {
      return;
    }
    try {
      await restoreSession(sessionId);
    } catch (_) {
      forgetSession();
      if (hasUrlSession) {
        resetToEmptyConversation();
        clearSessionIdFromUrl();
        showError(
          localeText(
            "这个对话链接已失效或已被删除。已回到新对话，你可以继续使用当前运行目录重新开始。",
            "This chat link is no longer available or was deleted. Start a new chat from the current run directory.",
          ),
          {autoHide: false},
        );
      }
    }
  }

  if (window.location.hash === "#bundle-import-form") {
    window.location.replace(window.LooporaUI.safeLocalRedirectUrl(
      shell?.dataset.composeImportHref,
      "/loops/new/manual#bundle-import-form",
    ));
    return;
  }
  updateExecutorControls();
  setExecutionState("idle");
  refreshExecutorReadiness({showChecking: true}).catch(() => {});
  loadHistory().catch(() => {});
  restoreSessionIfPresent().finally(() => {
    applyTutorialFitHandoff();
    renderTutorialFitHandoffBridge();
  });
});

document.addEventListener("DOMContentLoaded", () => {
  function canonicalizeSameAgentAlias() {
    if (window.location?.pathname !== "/tools" || typeof window.history?.replaceState !== "function") {
      return;
    }
    const nextUrl = `/same-agent${window.location.search || ""}${window.location.hash || ""}`;
    window.history.replaceState(window.history.state, "", nextUrl);
  }

  canonicalizeSameAgentAlias();

  if (!window.LooporaUI) {
    return;
  }

  const wakeLockToggle = document.getElementById("wake-lock-toggle");
  const wakeLockStatusBox = document.getElementById("wake-lock-status");
  const wakeLockRuntimePill = document.getElementById("wake-lock-runtime-pill");
  const wakeLockHoldPill = document.getElementById("wake-lock-hold-pill");
  const wakeLockRuns = document.getElementById("wake-lock-runs");
  const localAssetsPanel = document.querySelector("[data-testid='local-assets-diagnostics-panel']");
  const toolsSupportPanel = document.querySelector("[data-testid='tools-support-panel']");
  const toolsSupportStatusBox = document.getElementById("tools-support-status");
  const localAssetsStatusBox = document.getElementById("local-assets-status");
  const localAssetsCountNodes = Array.from(document.querySelectorAll("[data-local-assets-count]"));
  const localAssetsDetails = document.getElementById("local-assets-details");
  const localAssetsToggle = document.getElementById("local-assets-toggle");
  const agentAdapterStatusBox = document.getElementById("agent-adapter-status");
  const agentAdapterWorkdirInput = document.getElementById("agent-adapter-workdir");
  const agentAdapterTargetNote = document.getElementById("agent-adapter-target-note");
  const agentAdapterNextSteps = document.querySelector("[data-testid='agent-adapter-next-steps']");
  const agentReadinessSummary = document.getElementById("agent-readiness-summary");
  const agentAdapterHandoff = document.getElementById("agent-adapter-handoff");
  const agentAdapterDraftHandoff = document.getElementById("agent-adapter-draft-handoff");
  const agentAdapterRecoveryPanel = document.getElementById("agent-adapter-recovery-panel");
  const toolsFitGuideLink = document.querySelector("[data-testid='tools-fit-guide-link']");
  const agentAdapterBrowseWorkdirButton = document.querySelector("[data-testid='agent-adapter-browse-workdir']");
  const agentAdapterUseServerWorkdirButton = document.querySelector("[data-testid='agent-adapter-use-server-workdir']");
  const agentAdapterGrid = document.getElementById("agent-adapter-grid");
  const agentAdapterCards = Array.from(document.querySelectorAll("[data-agent-adapter]"));
  const agentAdapterStatusNodes = Array.from(document.querySelectorAll("[data-agent-adapter-status]"));
  const agentAdapterInstallButtons = Array.from(document.querySelectorAll("[data-agent-adapter-install]"));
  const agentAdapterUninstallButtons = Array.from(document.querySelectorAll("[data-agent-adapter-uninstall]"));
  const agentHostInputs = Array.from(document.querySelectorAll("[data-agent-host]"));
  const agentHostOptions = Array.from(document.querySelectorAll("[data-agent-host-option]"));
  const agentHostStatusNodes = Array.from(document.querySelectorAll("[data-agent-host-status]"));
  const agentHostSelectionStatus = document.getElementById("agent-host-selection-status");
  const WAKE_LOCK_PREF_KEY = "loopora:tools:wake-lock-enabled";
  const AGENT_ADAPTER_WORKDIR_PREF_KEY = "loopora:tools:agent-adapter-workdir";
  const FIT_HANDOFF_STORAGE_KEY = "loopora:tutorial-fit-handoff:v1";
  const FIT_HANDOFF_REQUIRED_INPUT_IDS = ["task", "loopora_fit_reason", "fake_done_risks", "required_evidence", "judgment_tradeoffs"];
  const SAME_AGENT_HANDOFF_BRIEF_ZH = "Loopora 适配理由、任务目标、伪完成风险、必需证据、判断取舍和可选直接路径上下文";
  const SAME_AGENT_HANDOFF_BRIEF_EN = "the Loopora fit reason, task goal, fake-done risk, required evidence, judgment tradeoffs, and optional direct-path context";
  const SUPPORT_CHOOSE_WORKDIR_ACTION_KIND = "choose_workdir_for_public_report";
  const SUPPORT_PUBLIC_ISSUE_BUNDLE_ACTION_KIND = "run_public_issue_bundle";
  const SUPPORT_PUBLIC_DOCTOR_ACTION_KIND = "run_public_doctor_report";
  const SUPPORT_TARGET_SCOPED_ACTION_KINDS = [SUPPORT_PUBLIC_ISSUE_BUNDLE_ACTION_KIND, SUPPORT_PUBLIC_DOCTOR_ACTION_KIND];
  const supportInitialNextActionKinds = supportActionKinds(toolsSupportPanel?.dataset.supportNextActionKinds);
  const supportInitialReadyNextActionKinds = supportActionKinds(toolsSupportPanel?.dataset.supportReadyNextActionKinds);
  const supportInitialBlockedNextActionKinds = supportActionKinds(toolsSupportPanel?.dataset.supportBlockedNextActionKinds);
  let wakeLockSentinel = null;
  let runtimeActivity = {
    running_count: 0,
    queued_count: 0,
    has_running_runs: false,
    has_active_runs: false,
    runs: [],
  };
  let runtimeActivitySignature = JSON.stringify(runtimeActivity);
  let preferredAgentAdapterHandoff = "";
  let selectedAgentAdapter = "";
  let agentAdapterHandoffUsesFitDraft = false;
  let lastAgentAdapterPayload = null;
  let lastAgentAdapterItems = [];
  let lastAgentReadinessPayload = null;
  let pendingAgentAdapterUninstall = null;
  let fitHandoffRenderSignature = "";
  let fitDirectPathBlocksAgentSetup = false;
  let fitReviewBlocksAgentInstall = false;
  const agentAdapterFirstTaskExamples = new Map();
  const agentAdapterFirstTaskExampleStates = new Map();
  const agentAdapterFirstTaskHandoffPolicies = new Map();
  const agentAdapterNextCommands = new Map();
  let localAssetsDetailsExpanded = false;
  let localAssetsIssueTotal = 0;
  let agentAdapterTargetRefreshTimer = 0;
  const localAssetsNativeDialogsEnabled = localAssetsPanel?.dataset.nativeDialogsEnabled !== "false";

  function localeText(zh, en) {
    return window.LooporaUI.pickText({zh, en});
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function showStatus(box, message, kind = "") {
    if (!box) {
      return;
    }
    const nextClassName = `field-status${kind ? ` is-${kind}` : ""}`;
    if (!message) {
      if (box.hidden && box.textContent === "" && box.className === "field-status") {
        return;
      }
      box.hidden = true;
      box.textContent = "";
      box.className = "field-status";
      return;
    }
    if (!box.hidden && box.textContent === message && box.className === nextClassName) {
      return;
    }
    box.hidden = false;
    box.textContent = message;
    box.className = nextClassName;
  }

  function compactText(value) {
    return String(value || "").trim().replace(/\s+/g, " ");
  }

  function supportShellQuote(value) {
    const text = String(value ?? "");
    if (!text) {
      return "''";
    }
    if (/^[A-Za-z0-9_@%+=:,./-]+$/.test(text)) {
      return text;
    }
    return `'${text.replace(/'/g, "'\"'\"'")}'`;
  }

  function supportPublicDoctorCommandWithWorkdir(command, workdir) {
    const text = String(command || "");
    const marker = "--workdir ";
    const markerIndex = text.indexOf(marker);
    if (markerIndex < 0) {
      return text;
    }
    const valueStart = markerIndex + marker.length;
    const suffixStart = text.indexOf(" || true", valueStart);
    const valueEnd = suffixStart >= 0 ? suffixStart : text.length;
    return `${text.slice(0, valueStart)}${supportShellQuote(workdir)}${text.slice(valueEnd)}`;
  }

  function supportPublicDoctorCommandTemplate(button) {
    const cached = String(button?.dataset?.supportCommandTemplate || "").trim();
    if (cached) {
      return cached;
    }
    const current = String(button?.dataset?.supportCommandCopy || "").trim();
    const template = supportPublicDoctorCommandWithWorkdir(current, "<project-dir>");
    if (button?.dataset) {
      button.dataset.supportCommandTemplate = template;
    }
    return template;
  }

  function supportPublicReportUrlWithWorkdir(workdir) {
    const text = String(workdir || "").trim();
    if (!text) {
      return "";
    }
    const params = new URLSearchParams();
    params.set("workdir", text);
    params.set("language", String(document.documentElement?.dataset?.locale || "en"));
    return `/api/diagnostics/public-issue-bundle?${params.toString()}`;
  }

  function setSupportButtonDisabled(button, disabled) {
    button.disabled = disabled;
    if (disabled) {
      button.setAttribute("aria-disabled", "true");
    } else {
      button.removeAttribute("aria-disabled");
    }
  }

  function setSupportButtonText(button, labelZh, labelEn) {
    button.innerHTML = `
      <span data-lang="zh">${escapeHtml(labelZh)}</span>
      <span data-lang="en">${escapeHtml(labelEn)}</span>
    `;
  }

  function supportActionKinds(value) {
    return String(value || "")
      .split(",")
      .map((kind) => kind.trim())
      .filter(Boolean);
  }

  function supportTargetProjectStatus() {
    if (!agentAdapterWorkdir()) {
      return "required";
    }
    const status = String(toolsSupportPanel?.dataset.supportTargetProjectStatus || "").trim();
    return status && status !== "required" ? status : "pending";
  }

  function supportTargetProjectStatusLabel(status) {
    const labels = {
      required: localeText("尚未提供", "not supplied"),
      pending: localeText("等待刷新", "pending refresh"),
      missing: localeText("不存在", "missing"),
      not_directory: localeText("不是目录", "not a directory"),
      unavailable: localeText("无法检查", "unavailable"),
      ready: localeText("已就绪", "ready"),
    };
    return labels[status] || String(status || "").replaceAll("_", " ");
  }

  function supportReportCommandReady(hasTarget, status) {
    return Boolean(hasTarget) && !["required", "pending"].includes(status);
  }

  function setToolsSupportTargetDataset(status, hasTarget) {
    if (!toolsSupportPanel) {
      return;
    }
    const normalized = String(status || "").trim() || (hasTarget ? "pending" : "required");
    const setupReady = normalized === "ready";
    const reportOnly = supportReportCommandReady(hasTarget, normalized) && !setupReady;
    toolsSupportPanel.dataset.supportTargetProjectStatus = normalized;
    toolsSupportPanel.dataset.supportTargetProjectSetupReady = setupReady ? "true" : "false";
    toolsSupportPanel.dataset.supportTargetProjectReportOnly = reportOnly ? "true" : "false";
  }

  function syncToolsSupportTargetStateNote(hasTarget, status, reportOnly) {
    const stateNote = toolsSupportPanel?.querySelector("[data-support-target-state-note]");
    if (!(stateNote instanceof HTMLElement)) {
      return;
    }
    if (!hasTarget) {
      stateNote.hidden = true;
      return;
    }
    if (status === "pending") {
      stateNote.hidden = false;
      stateNote.textContent = localeText(
        "目标项目状态：等待刷新；刷新完成前不要复制公开 issue 支持包或兜底报告命令。",
        "Target project state: pending refresh; do not copy the public issue bundle or fallback report command until refresh finishes.",
      );
      return;
    }
    if (reportOnly) {
      const statusLabel = supportTargetProjectStatusLabel(status);
      stateNote.hidden = false;
      stateNote.textContent = localeText(
        `目标项目状态：${statusLabel}；优先支持包/兜底报告命令可以生成脱敏证据，但设置仍需要可用的目标项目。`,
        `Target project state: ${statusLabel}; the preferred bundle/fallback report commands can produce redacted evidence, but setup still needs a usable target project.`,
      );
      return;
    }
    stateNote.hidden = true;
  }

  function uniqueSupportActionKinds(kinds) {
    return Array.from(new Set(kinds.filter(Boolean)));
  }

  function orderedSupportActionKinds(kinds, order) {
    const remaining = new Set(kinds);
    const ordered = [];
    for (const kind of order) {
      if (remaining.has(kind)) {
        ordered.push(kind);
        remaining.delete(kind);
      }
    }
    return ordered.concat(Array.from(remaining));
  }

  function setToolsSupportActionGroups(hasTarget, reportCommandReady = hasTarget) {
    if (!toolsSupportPanel) {
      return;
    }
    const targetRequiredNote = toolsSupportPanel.querySelector("[data-support-target-required-note]");
    const hasTargetPrompt = targetRequiredNote instanceof HTMLElement;
    if (hasTargetPrompt) {
      targetRequiredNote.hidden = hasTarget;
    }
    const next = supportInitialNextActionKinds.filter((kind) => kind !== SUPPORT_CHOOSE_WORKDIR_ACTION_KIND);
    const ready = supportInitialReadyNextActionKinds.filter((kind) => (
      kind !== SUPPORT_CHOOSE_WORKDIR_ACTION_KIND && !SUPPORT_TARGET_SCOPED_ACTION_KINDS.includes(kind)
    ));
    const blocked = supportInitialBlockedNextActionKinds.filter((kind) => (
      kind !== SUPPORT_CHOOSE_WORKDIR_ACTION_KIND && !SUPPORT_TARGET_SCOPED_ACTION_KINDS.includes(kind)
    ));
    if (!hasTarget && hasTargetPrompt) {
      next.unshift(SUPPORT_CHOOSE_WORKDIR_ACTION_KIND);
      ready.unshift(SUPPORT_CHOOSE_WORKDIR_ACTION_KIND);
    }
    for (const actionKind of SUPPORT_TARGET_SCOPED_ACTION_KINDS) {
      next.push(actionKind);
      if (reportCommandReady) {
        ready.push(actionKind);
      } else {
        blocked.push(actionKind);
      }
    }
    const orderedNext = uniqueSupportActionKinds(next);
    toolsSupportPanel.dataset.supportNextActionKinds = orderedNext.join(",");
    toolsSupportPanel.dataset.supportReadyNextActionKinds = orderedSupportActionKinds(
      uniqueSupportActionKinds(ready),
      orderedNext,
    ).join(",");
    toolsSupportPanel.dataset.supportBlockedNextActionKinds = orderedSupportActionKinds(
      uniqueSupportActionKinds(blocked),
      orderedNext,
    ).join(",");
  }

  function syncTargetScopedSupportCommandButton(actionKind, workdir, hasTarget, status, commandReady, labels) {
    const commandButton = toolsSupportPanel?.querySelector(`[data-support-command-copy][data-support-next-action-kind="${actionKind}"]`);
    if (!(commandButton instanceof HTMLButtonElement)) {
      return;
    }
    const template = supportPublicDoctorCommandTemplate(commandButton);
    commandButton.dataset.supportCommandCopy = hasTarget
      ? supportPublicDoctorCommandWithWorkdir(template, workdir)
      : template;
    commandButton.dataset.supportCommandRequiresTarget = hasTarget ? "false" : "true";
    commandButton.dataset.supportCommandReady = commandReady ? "true" : "false";
    setSupportButtonDisabled(commandButton, !commandReady);
    setSupportButtonText(
      commandButton,
      !hasTarget
        ? labels.noTargetZh
        : status === "pending"
          ? labels.pendingZh
          : status !== "ready"
            ? labels.reportOnlyZh
            : labels.readyZh,
      !hasTarget
        ? labels.noTargetEn
        : status === "pending"
          ? labels.pendingEn
          : status !== "ready"
            ? labels.reportOnlyEn
            : labels.readyEn,
    );
  }

  function syncToolsSupportTargetState() {
    if (!toolsSupportPanel) {
      return;
    }
    const workdir = agentAdapterWorkdir();
    const hasTarget = Boolean(workdir);
    const status = supportTargetProjectStatus();
    const reportCommandReady = supportReportCommandReady(hasTarget, status);
    const reportOnly = reportCommandReady && status !== "ready";
    setToolsSupportTargetDataset(status, hasTarget);
    toolsSupportPanel.dataset.supportPublicReportUrl = reportCommandReady ? supportPublicReportUrlWithWorkdir(workdir) : "";
    syncToolsSupportTargetStateNote(hasTarget, status, reportOnly);
    const reportButton = toolsSupportPanel.querySelector("[data-support-copy-public-report]");
    if (reportButton instanceof HTMLButtonElement) {
      setSupportButtonDisabled(reportButton, !reportCommandReady);
      setSupportButtonText(
        reportButton,
        !hasTarget
          ? "选择目标后复制当前公开 issue 支持包"
          : status === "pending"
            ? "刷新目标后复制当前公开 issue 支持包"
            : reportOnly
              ? "复制不可用目标的公开 issue 支持包"
              : "复制当前公开 issue 支持包",
        !hasTarget
          ? "Choose target before copying current public issue bundle"
          : status === "pending"
            ? "Refresh target before copying current public issue bundle"
            : reportOnly
              ? "Copy public issue bundle for unusable target"
              : "Copy current public issue bundle",
      );
    }
    syncTargetScopedSupportCommandButton(SUPPORT_PUBLIC_ISSUE_BUNDLE_ACTION_KIND, workdir, hasTarget, status, reportCommandReady, {
      noTargetZh: "选择目标后复制优先支持包命令",
      noTargetEn: "Choose target before copying preferred bundle command",
      pendingZh: "刷新目标后复制优先支持包命令",
      pendingEn: "Refresh target before copying preferred bundle command",
      reportOnlyZh: "复制优先支持包命令",
      reportOnlyEn: "Copy preferred bundle command",
      readyZh: "复制优先支持包命令",
      readyEn: "Copy preferred bundle command",
    });
    syncTargetScopedSupportCommandButton(SUPPORT_PUBLIC_DOCTOR_ACTION_KIND, workdir, hasTarget, status, reportCommandReady, {
      noTargetZh: "选择目标后复制兜底报告命令",
      noTargetEn: "Choose target before copying fallback report command",
      pendingZh: "刷新目标后复制兜底报告命令",
      pendingEn: "Refresh target before copying fallback report command",
      reportOnlyZh: "复制兜底报告命令",
      reportOnlyEn: "Copy fallback report command",
      readyZh: "复制兜底报告命令",
      readyEn: "Copy fallback report command",
    });
    setToolsSupportActionGroups(hasTarget, reportCommandReady);
  }

  function fitHandoffInputLabel(inputId, prefersDirect = false) {
    const labels = {
      task: localeText("目标", "Goal"),
      loopora_fit_reason: localeText("适配理由", "Fit reason"),
      direct_path_check: prefersDirect ? localeText("直接路径决策", "Direct-path decision") : localeText("直接路径", "Direct path"),
      fake_done_risks: localeText("伪完成", "Fake done"),
      required_evidence: localeText("证据", "Evidence"),
      judgment_tradeoffs: localeText("取舍", "Tradeoffs"),
    };
    return labels[inputId] || inputId;
  }

  function fitHandoffChipLabel(inputId, prefersDirect = false) {
    const labels = {
      task: localeText("目标", "Goal"),
      loopora_fit_reason: localeText("Loopora 适配理由", "Loopora fit reason"),
      direct_path_check: prefersDirect ? localeText("直接路径决策", "Direct-path decision") : localeText("直接路径检查", "Direct-path check"),
      fake_done_risks: localeText("伪完成风险", "Fake-done risks"),
      required_evidence: localeText("必需证据", "Required evidence"),
      judgment_tradeoffs: localeText("判断取舍", "Judgment tradeoffs"),
    };
    return labels[inputId] || inputId;
  }

  function readFitHandoff() {
    try {
      const raw = window.sessionStorage?.getItem(FIT_HANDOFF_STORAGE_KEY) || "";
      if (!raw) {
        return null;
      }
      const payload = JSON.parse(raw);
      if (payload?.source !== "tutorial_fit_review") {
        return null;
      }
      const prefersDirect = window.LooporaUI.tutorialFitPrefersDirectPath(payload);
      const draft = String(payload?.primary_first_task_message || payload?.draft_first_task_message || "").trim();
      if (!draft && !prefersDirect) {
        return null;
      }
      const inputs = payload?.inputs && typeof payload.inputs === "object" ? payload.inputs : {};
      const payloadMissingIds = Array.isArray(payload?.missing_first_task_input_ids)
        ? payload.missing_first_task_input_ids.map((inputId) => String(inputId || "").trim()).filter(Boolean)
        : [];
      const derivedMissingIds = FIT_HANDOFF_REQUIRED_INPUT_IDS.filter((inputId) => !compactText(inputs[inputId]));
      const missingInputIds = prefersDirect ? [] : Array.from(new Set([...payloadMissingIds, ...derivedMissingIds]));
      const setupGate = String(payload?.setup_gate || "").trim();
      const setupAllowed = !prefersDirect && payload?.setup_allowed !== false && setupGate !== "blocked_until_review_inputs_complete";
      const sourceWorkdir = String(payload?.source_workdir || payload?.workdir || "").trim();
      const setupCommandState = window.LooporaUI.tutorialFitSetupCommandState(payload, {missingInputIds, setupAllowed, sourceWorkdir});
      const firstTaskState = fitHandoffPrimaryFirstTaskState(payload, {missingInputIds, setupAllowed});
      return {
        prefersDirect,
        draft,
        firstTaskState,
        inputs,
        missingInputIds,
        setupAllowed,
        setupGateReady: setupCommandState.setupGateReady,
        setupGateBlockers: setupCommandState.setupGateBlockers,
        setupCommandsReady: setupCommandState.setupCommandsReady,
        setupCommandBlockers: setupCommandState.setupCommandBlockers,
        routePreviewExecutable: setupCommandState.routePreviewExecutable,
        routePreviewBlockers: setupCommandState.routePreviewBlockers,
        setupGate,
        setupBlocker: String(payload?.setup_blocker || "").trim(),
        readyForPlan: firstTaskState.copyAllowed,
        reviewCompletionCommand: String(payload?.review_completion_command || payload?.direct_decision_command || "").trim(),
        language: String(payload?.language || "").trim(),
        savedAt: String(payload?.saved_at || "").trim(),
        sourceWorkdir,
      };
    } catch (_) {
      return null;
    }
  }

  function fitHandoffPrimaryFirstTaskState(payload, {missingInputIds, setupAllowed}) {
    const state = payload?.primary_first_task_message_state && typeof payload.primary_first_task_message_state === "object"
      ? payload.primary_first_task_message_state
      : {};
    const fallbackReady = missingInputIds.length === 0 && payload?.ready_for_loopora_plan_message !== false && setupAllowed;
    const copyAllowed = typeof state.copy_allowed === "boolean" ? state.copy_allowed : fallbackReady;
    const ready = typeof state.ready === "boolean" ? state.ready : copyAllowed;
    const completedReview = typeof state.completed_review === "boolean" ? state.completed_review : copyAllowed;
    return {
      source: String(state.source || payload?.primary_first_task_message_source || "task_review_draft").trim(),
      status: String(
        state.status || payload?.primary_first_task_message_status || (
          copyAllowed ? "copyable_after_review_inputs_complete" : "preview_only_until_review_inputs_complete"
        ),
      ).trim(),
      ready,
      copyAllowed,
      completedReview,
    };
  }

  function fitHandoffMatchesTarget(handoff, targetWorkdir) {
    const target = String(targetWorkdir || "").trim();
    return window.LooporaUI.sameWorkdir(handoff?.sourceWorkdir, target, {
      allowEmptyLeft: !target,
      allowEmptyRight: false,
    });
  }

  function fitHandoffReadyForAgent(handoff) {
    return Boolean(
      handoff?.setupAllowed !== false
      && handoff?.setupGateReady
      && handoff?.readyForPlan
      && handoff?.firstTaskState?.copyAllowed
      && !handoff?.missingInputIds?.length,
    );
  }

  function normalizeAgentAdapterFirstTaskExampleState(state, fallbackSource = "generic_example") {
    const value = state && typeof state === "object" ? state : {};
    const copyAllowed = value.copy_allowed === true || value.copyAllowed === true;
    const completedReview = value.completed_review === true || value.completedReview === true || copyAllowed;
    const ready = typeof value.ready === "boolean" ? value.ready : copyAllowed;
    return {
      source: String(value.source || fallbackSource || "generic_example").trim(),
      status: String(value.status || (copyAllowed ? "copyable_after_review_inputs_complete" : "orientation_only")).trim(),
      ready,
      copyAllowed,
      completedReview,
    };
  }

  function fitHandoffReviewHref(sourceWorkdir = "") {
    const baseHref = String(toolsFitGuideLink?.getAttribute("href") || "/tutorial#tutorial-decision-tree-panel").trim();
    try {
      const url = new URL(baseHref, window.location.origin);
      const workdir = String(sourceWorkdir || agentAdapterWorkdir() || "").trim();
      if (workdir && url.origin === window.location.origin) {
        url.searchParams.set("workdir", workdir);
      }
      return `${url.pathname}${url.search}${url.hash}`;
    } catch (_) {
      return baseHref || "/tutorial#tutorial-decision-tree-panel";
    }
  }

  function clearFitHandoff() {
    try {
      window.sessionStorage?.removeItem(FIT_HANDOFF_STORAGE_KEY);
    } catch (_) {
      // Best effort only.
    }
  }

  function focusAgentAdapterTargetInput() {
    agentAdapterWorkdirInput?.focus?.();
  }

  function directPathAgentAdapterBlockMessage() {
    return localeText(
      "已选择直接路径，因此同一 Agent setup 已停用。复制直接路径命令，或清除 Fit Guide 决策后再安装项目入口。",
      "Direct path is selected, so same-Agent setup is disabled. Copy the direct-path command, or clear the Fit Guide decision before installing a project entry.",
    );
  }

  function incompleteFitReviewAgentAdapterBlockMessage() {
    return localeText(
      "当前任务的 Fit Review 尚未完成；可以继续读取状态、复制补完命令或卸载旧入口，但安装或更新必须等五项判断审查完成。",
      "The current task's Fit Review is incomplete. You may still inspect status, copy the completion command, or uninstall an old entry, but install or update must wait until all five judgments are reviewed.",
    );
  }

  function fitHandoffBlocksCurrentAgentInstall(handoff, targetWorkdir = agentAdapterWorkdir()) {
    return Boolean(
      handoff
      && !handoff.prefersDirect
      && fitHandoffMatchesTarget(handoff, targetWorkdir)
      && !fitHandoffReadyForAgent(handoff),
    );
  }

  function syncAgentAdapterMutationButton(button) {
    if (!(button instanceof HTMLButtonElement)) {
      return;
    }
    if (button.dataset.agentAdapterBaseDisabled === undefined) {
      button.dataset.agentAdapterBaseDisabled = button.disabled ? "true" : "false";
      button.dataset.agentAdapterBaseTitle = button.getAttribute("title") || "";
    }
    if (fitDirectPathBlocksAgentSetup) {
      button.disabled = true;
      button.setAttribute("aria-disabled", "true");
      button.setAttribute("title", directPathAgentAdapterBlockMessage());
      button.dataset.agentAdapterDirectPathDisabled = "true";
      delete button.dataset.agentAdapterFitReviewDisabled;
      return;
    }
    if (fitReviewBlocksAgentInstall && button.dataset.agentAdapterInstall !== undefined) {
      button.disabled = true;
      button.setAttribute("aria-disabled", "true");
      button.setAttribute("title", incompleteFitReviewAgentAdapterBlockMessage());
      button.dataset.agentAdapterFitReviewDisabled = "true";
      delete button.dataset.agentAdapterDirectPathDisabled;
      return;
    }
    button.disabled = button.dataset.agentAdapterBaseDisabled === "true";
    button.removeAttribute("aria-disabled");
    const baseTitle = button.dataset.agentAdapterBaseTitle || "";
    if (baseTitle) {
      button.setAttribute("title", baseTitle);
    } else {
      button.removeAttribute("title");
    }
    delete button.dataset.agentAdapterDirectPathDisabled;
    delete button.dataset.agentAdapterFitReviewDisabled;
  }

  function setAgentAdapterMutationButtonBaseState(button, disabled, title = "") {
    if (!(button instanceof HTMLButtonElement)) {
      return;
    }
    button.dataset.agentAdapterBaseDisabled = disabled ? "true" : "false";
    button.dataset.agentAdapterBaseTitle = String(title || "");
    syncAgentAdapterMutationButton(button);
  }

  function setAgentAdapterSetupBlockedForDirectPath(blocked) {
    fitDirectPathBlocksAgentSetup = Boolean(blocked);
    for (const button of [...agentAdapterInstallButtons, ...agentAdapterUninstallButtons]) {
      syncAgentAdapterMutationButton(button);
    }
  }

  function setAgentAdapterInstallBlockedForFitReview(blocked) {
    fitReviewBlocksAgentInstall = Boolean(blocked);
    for (const button of agentAdapterInstallButtons) {
      syncAgentAdapterMutationButton(button);
    }
  }

  function syncAgentAdapterFitGates(handoff = readFitHandoff(), targetWorkdir = agentAdapterWorkdir()) {
    const matchesTarget = Boolean(handoff && fitHandoffMatchesTarget(handoff, targetWorkdir));
    const directPathBlocksAgentSetup = Boolean(handoff?.prefersDirect && matchesTarget);
    const reviewBlocksAgentInstall = fitHandoffBlocksCurrentAgentInstall(handoff, targetWorkdir);
    setAgentAdapterSetupBlockedForDirectPath(directPathBlocksAgentSetup);
    setAgentAdapterInstallBlockedForFitReview(reviewBlocksAgentInstall);
    return {directPathBlocksAgentSetup, reviewBlocksAgentInstall};
  }

  function directHandoffBlocksAgentAdapterMutation() {
    const handoff = readFitHandoff();
    const {directPathBlocksAgentSetup: directPathBlocksCurrentTarget} = syncAgentAdapterFitGates(
      handoff,
      agentAdapterWorkdir(),
    );
    if (!directPathBlocksCurrentTarget) {
      return false;
    }
    setAgentAdapterSetupBlockedForDirectPath(true);
    renderFitHandoff();
    clearAgentAdapterRecoveryPanel();
    showStatus(agentAdapterStatusBox, directPathAgentAdapterBlockMessage(), "error");
    try {
      agentAdapterDraftHandoff?.scrollIntoView({block: "nearest"});
    } catch (_) {
      // Best effort only.
    }
    return true;
  }

  function incompleteFitHandoffBlocksAgentAdapterInstall() {
    const handoff = readFitHandoff();
    const reviewBlocksAgentInstall = fitHandoffBlocksCurrentAgentInstall(handoff, agentAdapterWorkdir());
    if (!reviewBlocksAgentInstall) {
      return false;
    }
    setAgentAdapterInstallBlockedForFitReview(true);
    renderFitHandoff();
    showStatus(agentAdapterStatusBox, incompleteFitReviewAgentAdapterBlockMessage(), "warning");
    try {
      agentAdapterDraftHandoff?.scrollIntoView({block: "nearest"});
    } catch (_) {
      // Best effort only.
    }
    return true;
  }

  function renderFitHandoff() {
    if (!agentAdapterDraftHandoff) {
      setAgentAdapterSetupBlockedForDirectPath(false);
      setAgentAdapterInstallBlockedForFitReview(false);
      return;
    }
    if (agentAdapterHandoffUsesFitDraft) {
      fitHandoffRenderSignature = "";
      setAgentAdapterSetupBlockedForDirectPath(false);
      setAgentAdapterInstallBlockedForFitReview(false);
      agentAdapterDraftHandoff.hidden = true;
      agentAdapterDraftHandoff.innerHTML = "";
      agentAdapterDraftHandoff.classList.remove("is-warning");
      return;
    }
    const handoff = readFitHandoff();
    if (!handoff) {
      fitHandoffRenderSignature = "";
      setAgentAdapterSetupBlockedForDirectPath(false);
      setAgentAdapterInstallBlockedForFitReview(false);
      agentAdapterDraftHandoff.hidden = true;
      agentAdapterDraftHandoff.innerHTML = "";
      agentAdapterDraftHandoff.classList.remove("is-warning");
      return;
    }
    const inputs = handoff.inputs || {};
    const handoffLanguage = String(handoff.language || "").trim();
    const sourceWorkdir = String(handoff.sourceWorkdir || "").trim();
    const targetWorkdir = agentAdapterWorkdir();
    const missingInputIds = Array.isArray(handoff.missingInputIds) ? handoff.missingInputIds : [];
    const prefersDirect = Boolean(handoff.prefersDirect);
    const hasWorkdirMismatch = !fitHandoffMatchesTarget(handoff, targetWorkdir);
    const {directPathBlocksAgentSetup, reviewBlocksAgentInstall} = syncAgentAdapterFitGates(handoff, targetWorkdir);
    const hasMissingInputs = !prefersDirect && (missingInputIds.length > 0 || handoff.setupAllowed === false || !handoff.readyForPlan);
    const targetProjectRequired = handoff.setupGateBlockers.includes("target_project_required");
    const hasSetupCommandBlockers = !prefersDirect && !handoff.setupGateReady;
    const needsAttention = hasWorkdirMismatch || hasMissingInputs || hasSetupCommandBlockers;
    const title = hasWorkdirMismatch
      ? localeText("brief 属于另一个目标项目", "Brief belongs to another target project")
      : prefersDirect
        ? localeText("已选择直接路径", "Direct path selected")
      : hasMissingInputs
        ? localeText("brief 还缺判断输入", "Brief still needs review inputs")
        : targetProjectRequired
          ? localeText("先选择目标项目", "Choose a target project first")
        : localeText("已审查交接，先完成设置", "Reviewed handoff; finish setup first");
    const description = hasWorkdirMismatch
      ? localeText(
        "这个 Fit Guide 草稿属于另一个项目。切回来源项目后再复制 Agent brief，避免把判断带进错误目标。",
        "This Fit Guide draft belongs to another project. Switch back to the source project before copying the Agent brief into the wrong target.",
      )
      : prefersDirect
        ? localeText(
          "Fit Guide 已记录直接 Agent、/goal、硬性检查或项目流程足够。不要安装同一 Agent 项目入口或复制 /loopora-plan brief。",
          "Fit Guide recorded that direct Agent work, /goal, hard checks, or the project process is enough. Do not install a same-Agent project entry or copy a /loopora-plan brief.",
        )
      : hasMissingInputs
        ? localeText(
          "这个 Fit Guide 草稿还缺判断输入。先补齐或复制补完命令；缺项状态不会暴露为可粘贴的 Agent brief，也不会允许当前项目安装或更新入口。",
          "This Fit Guide draft still needs review inputs. Finish it or copy the completion command; incomplete drafts are not exposed as paste-ready Agent briefs and cannot install or update the current project's entry.",
        )
        : targetProjectRequired
          ? localeText(
            "这个 Fit Guide 草稿还没有绑定目标项目。先在同一 Agent 设置里选择并刷新目标项目，再复制 Agent brief。",
            "This Fit Guide draft is not bound to a target project yet. Choose and refresh a target in Same-Agent Setup before copying the Agent brief.",
          )
        : localeText(
          "这份 Fit Guide 交接已绑定当前目标。现在可以保存，但只有所选同一 Agent 项目入口报告就绪后才能粘贴；草稿不会写入服务器或 URL。",
          "This Fit Guide handoff is bound to the current target. You may save it now, but paste it only after the selected same-Agent project entry reports ready; the draft is not written to the server or URL.",
        );
    const sourceWorkdirLine = sourceWorkdir
      ? `
        <span class="agent-draft-handoff-context" data-testid="agent-draft-handoff-source-workdir">
          ${escapeHtml(localeText("来源项目", "Source project"))}: ${escapeHtml(sourceWorkdir)}
        </span>
      `
      : "";
    const targetWorkdirLine = hasWorkdirMismatch
      ? `
        <span class="agent-draft-handoff-context" data-testid="agent-draft-handoff-current-workdir">
          ${escapeHtml(localeText("当前目标", "Current target"))}: ${escapeHtml(targetWorkdir || "-")}
        </span>
      `
      : "";
    const missingInputsLine = hasMissingInputs
      ? `
        <span class="agent-draft-handoff-context" data-testid="agent-draft-handoff-missing-inputs">
          ${escapeHtml(localeText("缺少判断输入", "Missing review inputs"))}: ${escapeHtml(missingInputIds.map(fitHandoffInputLabel).join(", ") || "-")}
        </span>
      `
      : "";
    const setupCommandLine = reviewBlocksAgentInstall
      ? `
        <span class="agent-draft-handoff-context" data-testid="agent-draft-handoff-setup-commands">
          ${escapeHtml(localeText("设置与交接", "Setup and handoff"))}: ${escapeHtml(localeText("安装、更新和 plan/run 交接等待审查完成", "install, update, and plan/run handoff wait for review completion"))}
        </span>
      `
      : handoff.setupGateReady
      ? `
        <span class="agent-draft-handoff-context" data-testid="agent-draft-handoff-setup-commands">
          ${escapeHtml(localeText("设置命令", "Setup commands"))}: ${escapeHtml(localeText("同一 Agent 设置命令可复制", "Same-Agent setup commands are copyable"))}
        </span>
      `
      : handoff.setupGateBlockers.includes("prefer_direct_path")
        ? directPathBlocksAgentSetup
          ? `
          <span class="agent-draft-handoff-context" data-testid="agent-draft-handoff-setup-commands">
            ${escapeHtml(localeText("设置命令", "Setup commands"))}: ${escapeHtml(localeText("直接路径决策已阻止 Loopora 设置", "Direct-path decision blocks Loopora setup"))}
          </span>
        `
          : `
          <span class="agent-draft-handoff-context" data-testid="agent-draft-handoff-setup-commands">
            ${escapeHtml(localeText("设置命令", "Setup commands"))}: ${escapeHtml(localeText("直接路径决策属于来源项目", "Direct-path decision belongs to the source project"))}
          </span>
        `
      : handoff.setupGateBlockers.includes("target_project_required")
        ? `
          <span class="agent-draft-handoff-context" data-testid="agent-draft-handoff-setup-commands">
            ${escapeHtml(localeText("设置命令", "Setup commands"))}: ${escapeHtml(localeText("先选择目标项目", "choose a target project first"))}
          </span>
        `
        : "";
    const finishReviewHref = fitHandoffReviewHref(sourceWorkdir || targetWorkdir);
    const useSourceWorkdirButton = hasWorkdirMismatch && sourceWorkdir
      ? `
        <button
          class="ghost-button"
          type="button"
          data-agent-draft-handoff-use-source="${escapeHtml(sourceWorkdir)}"
          data-testid="agent-draft-handoff-use-source"
        >
          ${escapeHtml(localeText("使用来源项目", "Use source project"))}
        </button>
      `
      : "";
    const finishReviewLink = hasMissingInputs
      ? `
        <a
          class="secondary-button agent-draft-handoff-finish-review"
          href="${escapeHtml(finishReviewHref)}"
          data-agent-draft-handoff-finish-review="1"
          data-testid="agent-draft-handoff-finish-review"
        >
          ${escapeHtml(localeText("回 Fit Guide 补齐判断", "Finish review in Fit Guide"))}
        </a>
      `
      : "";
    const completionCommandButton = hasMissingInputs && handoff.reviewCompletionCommand
      ? `
        <button
          class="ghost-button"
          type="button"
          data-agent-draft-handoff-copy-completion="${escapeHtml(handoff.reviewCompletionCommand)}"
          data-testid="agent-draft-handoff-copy-completion"
        >
          ${escapeHtml(localeText("复制补完命令", "Copy completion command"))}
        </button>
      `
      : prefersDirect && handoff.reviewCompletionCommand
        ? `
          <button
            class="ghost-button"
            type="button"
            data-agent-draft-handoff-copy-completion="${escapeHtml(handoff.reviewCompletionCommand)}"
            data-testid="agent-draft-handoff-copy-direct-decision"
          >
            ${escapeHtml(localeText("复制直接路径命令", "Copy direct-path command"))}
          </button>
        `
      : "";
    const chips = [
      ["task", inputs.task],
      ["loopora_fit_reason", inputs.loopora_fit_reason],
      ["direct_path_check", inputs.direct_path_check],
      ["fake_done_risks", inputs.fake_done_risks],
      ["required_evidence", inputs.required_evidence],
      ["judgment_tradeoffs", inputs.judgment_tradeoffs],
    ]
      .filter(([, value]) => String(value || "").trim())
      .map(([inputId, value]) => `
        <span class="agent-draft-handoff-chip">
          <strong>${escapeHtml(fitHandoffChipLabel(inputId, prefersDirect))}</strong>
          <span>${escapeHtml(value)}</span>
        </span>
      `)
      .join("");
    const agentBriefCopyButton = !needsAttention && handoff.draft && handoff.firstTaskState?.copyAllowed
      ? `
        <button
          class="agent-adapter-command-button agent-draft-handoff-copy"
          type="button"
          data-agent-draft-handoff-copy="${escapeHtml(handoff.draft)}"
          data-testid="agent-draft-handoff-copy"
          aria-label="${escapeHtml(localeText("复制设置就绪后使用的已审查交接", "Copy the reviewed handoff for after setup is ready"))}"
        >
          <code>${escapeHtml(handoff.draft)}</code>
        </button>
      `
      : "";
    const renderSignature = JSON.stringify({
      draft: handoff.draft,
      inputs,
      sourceWorkdir,
      targetWorkdir,
      finishReviewHref,
      hasWorkdirMismatch,
      hasMissingInputs,
      prefersDirect,
      directPathBlocksAgentSetup,
      reviewBlocksAgentInstall,
      missingInputIds,
      setupGateReady: handoff.setupGateReady,
      setupGateBlockers: handoff.setupGateBlockers,
      routePreviewExecutable: handoff.routePreviewExecutable,
      routePreviewBlockers: handoff.routePreviewBlockers,
      reviewCompletionCommand: handoff.reviewCompletionCommand,
      handoffLanguage,
      locale: window.LooporaUI.currentLocale?.() || "",
    });
    if (!agentAdapterDraftHandoff.hidden && fitHandoffRenderSignature === renderSignature) {
      return;
    }
    fitHandoffRenderSignature = renderSignature;
    agentAdapterDraftHandoff.hidden = false;
    agentAdapterDraftHandoff.classList.toggle("is-warning", needsAttention);
    agentAdapterDraftHandoff.innerHTML = `
      <div class="agent-adapter-handoff-head">
        <div>
          <strong data-testid="agent-draft-handoff-title">${escapeHtml(title)}</strong>
          <span>${escapeHtml(description)}</span>
          ${sourceWorkdirLine}
          ${targetWorkdirLine}
          ${missingInputsLine}
          ${setupCommandLine}
        </div>
        <span class="wake-lock-pill ${needsAttention ? "wake-lock-pill-warning" : "wake-lock-pill-neutral"}" data-testid="agent-draft-handoff-state">
          ${escapeHtml(hasWorkdirMismatch
            ? localeText("不同目标", "Different target")
            : hasMissingInputs
              ? localeText("缺少输入", "Missing input")
              : prefersDirect
                ? localeText("直接路径", "Direct path")
              : targetProjectRequired
                ? localeText("缺少目标", "Missing target")
              : localeText("先设置", "Setup first"))}
        </span>
      </div>
      <div class="agent-draft-handoff-chips" data-testid="agent-draft-handoff-inputs">${chips}</div>
      ${agentBriefCopyButton}
      <div class="agent-draft-handoff-actions">
        ${finishReviewLink}
        ${useSourceWorkdirButton}
        ${completionCommandButton}
        <button class="ghost-button" type="button" data-agent-draft-handoff-clear="1" data-testid="agent-draft-handoff-clear">
          <span>${escapeHtml(localeText("清除草稿", "Clear draft"))}</span>
        </button>
      </div>
      <div class="agent-readiness-public-report" data-agent-draft-handoff-manual-copy data-testid="agent-draft-handoff-manual-copy" hidden></div>
    `;
  }

  function updateNodeTextAndClass(node, text, className) {
    if (!node) {
      return;
    }
    if (node.textContent === text && node.className === className) {
      return;
    }
    node.textContent = text;
    node.className = className;
  }

  function fetchJson(url, options = {}) {
    return fetch(url, options).then(async (response) => {
      const payload = await response.json().catch(() => ({}));
      return {response, payload};
    });
  }

  function parentPath(path) {
    const value = String(path || "").replace(/[\\/]+$/, "");
    if (!value) {
      return "";
    }
    const slashIndex = Math.max(value.lastIndexOf("/"), value.lastIndexOf("\\"));
    if (slashIndex <= 0) {
      return value;
    }
    return value.slice(0, slashIndex);
  }

  function renderLocalAssetDiagnostics(payload) {
    let total = 0;
    for (const node of localAssetsCountNodes) {
      const key = String(node.dataset.localAssetsCount || "");
      const count = Array.isArray(payload?.[key]) ? payload[key].length : 0;
      total += count;
      const label = key === "orphan_alignment_dirs"
        ? localeText("对话编排残留目录", "Conversation orphan dirs")
        : key === "orphan_bundle_dirs"
          ? localeText("方案文件残留目录", "Plan file orphan dirs")
          : key === "orphan_run_dirs"
            ? localeText("运行残留目录", "Run orphan dirs")
            : localeText("记录缺失目录", "Records missing dirs");
      node.textContent = `${label}: ${count}`;
      node.className = `wake-lock-pill ${count > 0 ? "wake-lock-pill-warning" : "wake-lock-pill-neutral"}`;
    }
    localAssetsIssueTotal = total;
    updateLocalAssetsToggle();
    renderLocalAssetDetails(payload, total);
  }

  function updateLocalAssetsToggle() {
    if (!localAssetsToggle) {
      return;
    }
    if (!localAssetsIssueTotal) {
      localAssetsToggle.hidden = true;
      localAssetsToggle.setAttribute("aria-expanded", "false");
      return;
    }
    localAssetsToggle.hidden = false;
    localAssetsToggle.setAttribute("aria-expanded", String(localAssetsDetailsExpanded));
    localAssetsToggle.textContent = localAssetsDetailsExpanded
      ? localeText("收起维护明细", "Hide maintenance details")
      : localeText(
        `查看 ${localAssetsIssueTotal} 项维护明细`,
        `Review ${localAssetsIssueTotal} maintenance ${localAssetsIssueTotal === 1 ? "detail" : "details"}`,
      );
  }

  function localAssetIssueConfig(key) {
    const configs = {
      orphan_alignment_dirs: {
        title: localeText("对话编排残留目录", "Conversation orphan directories"),
        idLabel: localeText("对话", "Conversation"),
        idField: "session_id",
        action: localeText("打开目录", "Open folder"),
        suggestion: localeText(
          "建议先检查 transcript、events 和 artifacts；确认这次对话已不需要后，再在文件管理器中手动清理。",
          "Inspect transcript, events, and artifacts first; once the chat is no longer needed, clean it up manually in your file manager.",
        ),
      },
      orphan_bundle_dirs: {
        title: localeText("方案文件残留目录", "Plan file orphan directories"),
        idLabel: localeText("方案文件", "Plan file"),
        idField: "bundle_id",
        action: localeText("打开目录", "Open folder"),
        suggestion: localeText(
          "建议打开目录确认里面是否还有要导出的方案文件；确认无用后手动清理。",
          "Open the folder and check whether any plan files still need to be exported; clean it manually once it is safe.",
        ),
      },
      orphan_run_dirs: {
        title: localeText("运行残留目录", "Run orphan directories"),
        idLabel: localeText("运行", "Run"),
        idField: "run_id",
        action: localeText("打开目录", "Open folder"),
        suggestion: localeText(
          "建议先检查 evidence、timeline 或输出文件；确认运行证据已迁移或不再需要后手动清理。",
          "Inspect evidence, timeline, or output files first; clean it manually after the run evidence is migrated or no longer needed.",
        ),
      },
      record_without_dir: {
        title: localeText("记录缺失目录", "Records missing directories"),
        idLabel: localeText("记录", "Record"),
        idField: "resource_id",
        action: localeText("打开上级目录", "Open parent folder"),
        suggestion: localeText(
          "这通常表示目录被外部移动或删除；建议确认记录是否仍要保留，必要时重新运行、重新导入或重新开始对话来重建目录。",
          "This usually means the folder was moved or removed externally; decide whether to keep the record, then rerun, reimport, or restart the chat if the directory must be recreated.",
        ),
      },
    };
    return configs[key] || {
      title: key,
      idLabel: "id",
      idField: "id",
      action: localeText("打开目录", "Open folder"),
      suggestion: "",
    };
  }

  function localAssetIssueMeta(key, item) {
    const config = localAssetIssueConfig(key);
    const id = String(item?.[config.idField] || item?.resource_id || item?.path || "-");
    const type = item?.resource_type ? `${item.resource_type} · ` : "";
    const source = item?.source ? ` · ${item.source}` : "";
    const workdir = item?.workdir ? ` · ${item.workdir}` : "";
    return `${config.idLabel}: ${type}${id}${source}${workdir}`;
  }

  function localAssetPrimaryActionLabel(config) {
    if (localAssetsNativeDialogsEnabled) {
      return config.action;
    }
    return localeText("复制目录路径", "Copy folder path");
  }

  function renderLocalAssetDetails(payload, total) {
    if (!localAssetsDetails) {
      return;
    }
    if (!total) {
      localAssetsDetailsExpanded = false;
      localAssetsDetails.hidden = true;
      localAssetsDetails.innerHTML = "";
      return;
    }
    const keys = ["orphan_alignment_dirs", "orphan_bundle_dirs", "orphan_run_dirs", "record_without_dir"];
    const sections = keys.map((key) => {
      const items = Array.isArray(payload?.[key]) ? payload[key] : [];
      if (!items.length) {
        return "";
      }
      const config = localAssetIssueConfig(key);
      const rows = items.map((item) => {
        const path = String(item?.path || "");
        const revealPath = key === "record_without_dir" ? parentPath(path) : path;
        const primaryCopyPath = revealPath || path;
        const primaryActionAttributes = localAssetsNativeDialogsEnabled
          ? `
                data-local-assets-reveal-path="${escapeHtml(revealPath)}"
                data-local-assets-copy-path="${escapeHtml(primaryCopyPath)}"
                ${revealPath ? "" : "disabled"}`
          : `
                data-local-assets-copy-path="${escapeHtml(primaryCopyPath)}"
                ${primaryCopyPath ? "" : "disabled"}`;
        const copyOriginalPathButton = localAssetsNativeDialogsEnabled
          ? `
              <button
                class="ghost-button"
                type="button"
                data-local-assets-copy-path="${escapeHtml(path)}"
                data-testid="local-assets-copy-button"
              >${escapeHtml(localeText("复制路径", "Copy path"))}</button>
            `
          : "";
        return `
          <article class="local-assets-issue" data-testid="local-assets-issue" data-local-assets-kind="${escapeHtml(key)}">
            <div class="local-assets-issue-copy">
              <strong>${escapeHtml(localAssetIssueMeta(key, item))}</strong>
              <code>${escapeHtml(path || "-")}</code>
              <p>${escapeHtml(config.suggestion)}</p>
            </div>
            <div class="local-assets-issue-actions">
              <button
                class="secondary-button"
                type="button"
                data-testid="local-assets-reveal-button"
                ${primaryActionAttributes}
              >${escapeHtml(localAssetPrimaryActionLabel(config))}</button>
              ${copyOriginalPathButton}
            </div>
          </article>
        `;
      }).join("");
      return `
        <section class="local-assets-issue-group" data-testid="local-assets-issue-group">
          <header>
            <strong>${escapeHtml(config.title)}</strong>
            <span>${items.length}</span>
          </header>
          <div class="local-assets-issue-list">${rows}</div>
        </section>
      `;
    }).join("");
    localAssetsDetails.hidden = !localAssetsDetailsExpanded;
    localAssetsDetails.innerHTML = `
      <div class="local-assets-guidance">
        <strong>${escapeHtml(localeText("发现本地资产不一致", "Local asset mismatch found"))}</strong>
        <span>${escapeHtml(localAssetsNativeDialogsEnabled
          ? localeText("下面的动作只会定位或复制路径，不会删除文件或修改记录。", "These actions only reveal or copy paths; they do not delete files or modify records.")
          : localeText("网络模式不能打开主机文件夹；下面的动作只会复制服务端路径，不会删除文件或修改记录。", "Network mode cannot open host folders; these actions only copy server-side paths and do not delete files or modify records.")
        )}</span>
      </div>
      ${sections}
    `;
  }

  function copyText(value) {
    const text = String(value || "");
    if (!text) {
      return Promise.reject(new Error(localeText("没有可复制的内容。", "No copyable value.")));
    }
    return window.LooporaUI.writeTextToClipboard(text);
  }

  async function revealLocalAssetPath(path, copyFallbackPath = path) {
    window.LooporaUI?.renderGlobalManualCopy?.("");
    if (!localAssetsNativeDialogsEnabled) {
      const value = copyFallbackPath || path;
      try {
        await copyText(value);
        showStatus(localAssetsStatusBox, localeText("服务端路径已复制到剪贴板。", "Server-side path copied to clipboard."), "success");
      } catch (_) {
        window.LooporaUI?.renderGlobalManualCopy?.(value, {
          label: localeText("手动复制服务端路径", "Manual server-side path copy"),
          textareaId: "local-asset-path-manual-copy-textarea",
        });
        showStatus(localAssetsStatusBox, localeText("浏览器未允许自动复制；请手动复制页面底部的服务端路径。", "The browser blocked automatic copy; copy the server-side path at the bottom of the page manually."), "warning");
      }
      return;
    }
    if (!path && copyFallbackPath) {
      try {
        await copyText(copyFallbackPath);
        showStatus(localAssetsStatusBox, localeText("路径已复制到剪贴板。", "Path copied to clipboard."), "success");
      } catch (_) {
        window.LooporaUI?.renderGlobalManualCopy?.(copyFallbackPath, {
          label: localeText("手动复制路径", "Manual path copy"),
          textareaId: "local-asset-path-manual-copy-textarea",
        });
        showStatus(localAssetsStatusBox, localeText("浏览器未允许自动复制；请手动复制页面底部的路径。", "The browser blocked automatic copy; copy the path at the bottom of the page manually."), "warning");
      }
      return;
    }
    try {
      const {response, payload} = await fetchJson("/api/system/reveal-path", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({path}),
      });
      if (!response.ok) {
        const mutationError = new Error(payload.error || payload.summary || "failed");
        mutationError.payload = payload;
        throw mutationError;
      }
      showStatus(localAssetsStatusBox, localeText("已打开对应目录。", "Opened the corresponding folder."), "success");
    } catch (error) {
      try {
        await copyText(copyFallbackPath || path);
        window.LooporaUI?.renderGlobalManualCopy?.("");
        showStatus(
          localAssetsStatusBox,
          localeText("无法自动打开，路径已复制到剪贴板。", "Could not open automatically; the path was copied to clipboard."),
          "warning",
        );
      } catch (_) {
        window.LooporaUI?.renderGlobalManualCopy?.(copyFallbackPath || path, {
          label: localeText("手动复制路径", "Manual path copy"),
          textareaId: "local-asset-path-manual-copy-textarea",
        });
        showStatus(
          localAssetsStatusBox,
          localeText("无法自动打开或复制目录；请手动复制页面底部的路径。", "Unable to open or copy the folder automatically; copy the path at the bottom of the page manually."),
          "warning",
        );
      }
    }
  }

  async function refreshLocalAssetDiagnostics(options = {}) {
    const quiet = options.quiet ?? false;
    const {response, payload} = await fetchJson("/api/diagnostics/local-assets");
    if (!response.ok) {
      if (!quiet) {
        showStatus(localAssetsStatusBox, payload.error || localeText("无法读取本地资产诊断。", "Unable to load local asset diagnostics."), "error");
      }
      return;
    }
    renderLocalAssetDiagnostics(payload);
    showStatus(localAssetsStatusBox, "");
  }

  function agentReadinessUrl() {
    const workdir = agentAdapterWorkdir();
    if (!workdir) {
      return "/api/diagnostics/doctor";
    }
    return `/api/diagnostics/doctor?workdir=${encodeURIComponent(workdir)}`;
  }

  function agentReadinessPublicUrl() {
    const workdir = agentAdapterWorkdir();
    if (!workdir) {
      throw new Error(localeText("先选择目标项目，再复制公开诊断报告。", "Choose a target project before copying a public report."));
    }
    const params = new URLSearchParams();
    params.set("public", "true");
    params.set("workdir", workdir);
    return `/api/diagnostics/doctor?${params.toString()}`;
  }

  function agentReadinessStatusLabel(payload) {
    const status = String(payload?.status || "");
    if (agentReadinessWebBlocked(payload) && payload?.ready) {
      return localeText("Agent 可用，Web 需处理", "Agent ready, Web needs attention");
    }
    if (payload?.ready && status === "ready_with_warnings") {
      return localeText("可开始，有需检查项", "Ready with warnings");
    }
    if (payload?.ready) {
      return localeText("已可开始", "Ready");
    }
    return localeText("还不能开始", "Needs entry");
  }

  function agentReadinessPillClass(payload) {
    const status = String(payload?.status || "");
    if (agentReadinessWebBlocked(payload)) {
      return "wake-lock-pill wake-lock-pill-warning";
    }
    if (payload?.ready && status === "ready_with_warnings") {
      return "wake-lock-pill wake-lock-pill-queued";
    }
    if (payload?.ready) {
      return "wake-lock-pill wake-lock-pill-held";
    }
    return "wake-lock-pill wake-lock-pill-warning";
  }

  function agentReadinessEntries(payload) {
    return Array.isArray(payload?.agent_entries) ? payload.agent_entries : [];
  }

  function agentReadinessPrimaryEntry(payload) {
    const entries = agentReadinessEntries(payload);
    if (!selectedAgentAdapter) {
      return null;
    }
    return entries.find((item) => String(item?.adapter || "") === selectedAgentAdapter) || null;
  }

  function agentReadinessCommand(entry, kind) {
    const commands = entry?.commands && typeof entry.commands === "object" ? entry.commands : {};
    return String(commands[kind] || "").trim();
  }

  function agentReadinessAppState(payload) {
    return payload?.app_state && typeof payload.app_state === "object" ? payload.app_state : {};
  }

  function agentReadinessWeb(payload) {
    return payload?.web && typeof payload.web === "object" ? payload.web : {};
  }

  function agentReadinessLegacyWebRecoveryAction(reason) {
    const actions = {
      auth_required: "configure_web_auth",
      port_in_use: "use_suggested_free_port_or_choose_another_port",
      bind_failed: "choose_different_bind_host_or_port",
    };
    return actions[String(reason || "").trim()] || "inspect_readiness";
  }

  function agentReadinessWebBlockers(payload) {
    const web = agentReadinessWeb(payload);
    const blockers = Array.isArray(web.readiness_blockers)
      ? web.readiness_blockers.filter((item) => item && typeof item === "object")
      : [];
    if (blockers.length) {
      return blockers;
    }
    const appState = agentReadinessAppState(payload);
    const legacyBlockers = [];
    if (appState?.web_ready === false) {
      legacyBlockers.push({
        kind: "app_state_not_ready",
        status: String(appState?.status || "unknown").trim() || "unknown",
        recovery_action: "preview_app_database_reset",
      });
    }
    const reason = String(web.start_blocked_reason || "").trim();
    if (reason) {
      legacyBlockers.push({kind: reason, recovery_action: agentReadinessLegacyWebRecoveryAction(reason)});
    }
    return legacyBlockers;
  }

  function agentReadinessWebAppStateBlocked(payload) {
    return agentReadinessWebBlockers(payload).some((item) => String(item?.kind || "") === "app_state_not_ready");
  }

  function agentReadinessWebBlocked(payload) {
    return agentReadinessWebBlockers(payload).length > 0;
  }

  function agentReadinessWebBlockerLabel(blocker) {
    const kind = String(blocker?.kind || "").trim();
    const labels = {
      app_state_not_ready: localeText("Web 启动等待 App 数据", "Web start waits for App state"),
      auth_required: localeText("Web 启动需要认证 token", "Web start needs an auth token"),
      port_in_use: localeText("Web 端口已被占用", "Web port is already in use"),
      bind_failed: localeText("Web 绑定失败", "Web bind failed"),
    };
    return labels[kind] || localeText("Web 就绪需要处理", "Web readiness needs attention");
  }

  function agentReadinessWebBlockerSummary(payload) {
    const labels = agentReadinessWebBlockers(payload).map(agentReadinessWebBlockerLabel);
    return labels.join(localeText("、", ", "));
  }

  function agentReadinessWebStatusLabel(payload) {
    const web = agentReadinessWeb(payload);
    const blockerSummary = agentReadinessWebBlockerSummary(payload);
    if (blockerSummary) {
      return localeText(`Web 就绪需处理：${blockerSummary}`, `Web readiness needs attention: ${blockerSummary}`);
    }
    if (web.start_available === false) {
      const reason = String(web.start_blocked_reason || "");
      const labels = {
        auth_required: localeText("Web 启动需要认证 token", "Web start needs an auth token"),
        port_in_use: localeText("Web 端口已被占用", "Web port is already in use"),
        bind_failed: localeText("Web 绑定失败", "Web bind failed"),
      };
      return labels[reason] || localeText("Web 启动需要处理", "Web start needs attention");
    }
    if (web.already_running === true) {
      return localeText("Web 服务正在运行", "Web service is running");
    }
    if (web.auth_required === true && web.auth_token_configured === true) {
      return localeText("Web 可用，需保留当前 token 环境", "Web start ready; keep the current token environment");
    }
    return localeText("Web 启动可用", "Web start ready");
  }

  function appStateStatusLabel(appState) {
    const status = String(appState?.status || "");
    const labels = {
      current: localeText("App 数据可用", "App state ready"),
      not_initialized: localeText("App 数据待初始化", "App state not initialized"),
      current_shape_unversioned: localeText("App 数据待标记版本", "App state needs version stamp"),
      development_reset_required: localeText("App 数据库需预览重置范围", "App database reset scope needs preview"),
      future_version: localeText("App 数据来自较新版本", "App state from newer version"),
      unreadable: localeText("App 数据不可读取", "App state unreadable"),
      target_required: localeText("App 数据等待目标项目", "App state waits for target project"),
    };
    return labels[status] || localeText("App 数据状态未知", "App state unknown");
  }

  function appStateCommand(appState, kind) {
    const commands = appState?.commands && typeof appState.commands === "object" ? appState.commands : {};
    return String(commands[kind] || "").trim();
  }

  function agentReadinessActionItems(payload) {
    const primary = Array.isArray(payload?.next_actions)
      ? payload.next_actions.filter((item) => item && typeof item === "object")
      : [];
    if (primary.length > 0) {
      return primary;
    }
    return Array.isArray(payload?.next_action_items)
      ? payload.next_action_items.filter((item) => item && typeof item === "object")
      : [];
  }

  function agentReadinessActionCommand(payload, kind) {
    const targetKind = String(kind || "");
    const action = agentReadinessActionItems(payload).find((item) => String(item?.kind || "") === targetKind);
    return String(action?.command || "").trim();
  }

  function agentReadinessPreservesConfiguredAppHome(payload, entry) {
    const actionCommands = agentReadinessActionItems(payload)
      .filter((item) => String(item?.kind || "") !== "use_temporary_app_home")
      .map((item) => String(item?.command || "").trim());
    const entryCommands = ["install", "install_check", "agent_check"]
      .map((kind) => agentReadinessCommand(entry, kind));
    return [...actionCommands, ...entryCommands].some((command) => command.startsWith("LOOPORA_HOME="));
  }

  function agentReadinessWebAction(payload) {
    const webActionKinds = ["configure_web_auth", "resolve_web_port", "resolve_web_bind", "start_web"];
    return agentReadinessActionItems(payload).find((item) => {
      const kind = String(item?.kind || "");
      const command = String(item?.command || item?.origin || "").trim();
      return webActionKinds.includes(kind) && Boolean(command);
    }) || null;
  }

  function agentReadinessWebActionLabel(action) {
    const kind = String(action?.kind || "");
    if (kind === "start_web" && String(action?.operation || "") === "open_existing") {
      return {
        zh: "复制 Web 打开命令",
        en: "Copy Web open",
      };
    }
    const labels = {
      configure_web_auth: {
        zh: "复制 Web 认证启动",
        en: "Copy Web auth start",
      },
      resolve_web_port: {
        zh: "复制 Web 端口恢复",
        en: "Copy Web port recovery",
      },
      resolve_web_bind: {
        zh: "复制 Web 绑定恢复",
        en: "Copy Web bind recovery",
      },
      start_web: {
        zh: "复制 Web 启动",
        en: "Copy Web start",
      },
    };
    return labels[kind] || {
      zh: "复制 Web 命令",
      en: "Copy Web command",
    };
  }

  function agentReadinessWebActionCopyButton(payload) {
    const action = agentReadinessWebAction(payload);
    const command = String(action?.command || action?.origin || "").trim();
    if (!command) {
      return "";
    }
    const kind = String(action?.kind || "");
    const label = agentReadinessWebActionLabel(action);
    return agentReadinessCopyButton({
      testId: "agent-readiness-copy-web",
      command,
      labelZh: label.zh,
      labelEn: label.en,
    });
  }

  function agentReadinessCommandBlockerLabels(action, language) {
    const labels = {
      target_project_required: {zh: "可用目标项目", en: "usable target project"},
      target_project_unready: {zh: "可用目标项目", en: "usable target project"},
      same_agent_entry_required: {zh: "同一 Agent 项目入口", en: "same-Agent project entry"},
      app_state_not_ready: {zh: "本地 App 状态", en: "local App state"},
      first_task_message_not_ready: {zh: "可复制 /loopora-plan 任务消息", en: "copyable /loopora-plan task message"},
    };
    const seen = new Set();
    return (Array.isArray(action?.command_blockers) ? action.command_blockers : [])
      .map((item) => String(item || "").trim())
      .filter(Boolean)
      .map((item) => labels[item]?.[language] || item.replace(/_/g, " "))
      .filter((item) => {
        if (seen.has(item)) {
          return false;
        }
        seen.add(item);
        return true;
      });
  }

  function agentReadinessJoinLabels(labels, language) {
    if (labels.length <= 1) {
      return labels[0] || "";
    }
    if (language === "zh") {
      return labels.join("和");
    }
    if (labels.length === 2) {
      return `${labels[0]} and ${labels[1]}`;
    }
    return `${labels.slice(0, -1).join(", ")}, and ${labels[labels.length - 1]}`;
  }

  function agentReadinessCommandBlockerText(action, language) {
    const labels = agentReadinessCommandBlockerLabels(action, language);
    if (!labels.length) {
      return "";
    }
    const subject = agentReadinessJoinLabels(labels, language);
    return language === "zh"
      ? `${subject}就绪`
      : `${subject} ${labels.length === 1 ? "is" : "are"} ready`;
  }

  function agentReadinessActionStep(action) {
    const kind = String(action?.kind || "");
    const label = String(action?.label || "");
    const command = String(action?.command || "").trim();
    const origin = String(action?.origin || "").trim();
    const selectionRequired = action?.selection_required === true;
    const afterAction = String(action?.after_action || "").trim();
    const planBlockerZh = agentReadinessCommandBlockerText(action, "zh");
    const planBlockerEn = agentReadinessCommandBlockerText(action, "en");
    const readyReviewBlocked = (Array.isArray(action?.command_blockers) ? action.command_blockers : [])
      .map((item) => String(item || "").trim())
      .includes("ready_review_required");
    const webOperation = String(action?.operation || "");
    const webChoiceText = localeText(
      "Web 对话、Plan File 导入或手动专家路径，然后审查证据、缺口和裁决",
      "Web conversation, Plan File import, or manual expert paths; then review evidence, gaps, and verdicts",
    );
    function confirmReadinessText() {
      if (afterAction === "install_agent_entry") {
        return command
          ? localeText(
            `安装匹配的同一 Agent 项目入口后，回到 Agent 前确认 readiness：${command}`,
            `After installing the matching same-Agent project entry, confirm readiness before returning to Agent: ${command}`,
          )
          : localeText(
            "安装匹配的同一 Agent 项目入口后，回到 Agent 前确认 readiness。",
            "After installing the matching same-Agent project entry, confirm readiness before returning to Agent.",
          );
      }
      return command
        ? localeText(`回到 Agent 前确认 readiness：${command}`, `Confirm readiness before returning to Agent: ${command}`)
        : localeText("回到 Agent 前确认 readiness。", "Confirm readiness before returning to Agent.");
    }
    const labels = {
      return_to_ready_agent: localeText(
        `回到 ${label || "Agent"}，说明 ${SAME_AGENT_HANDOFF_BRIEF_ZH}。`,
        `Return to ${label || "Agent"} with ${SAME_AGENT_HANDOFF_BRIEF_EN}.`,
      ),
      return_to_agent: localeText(
        selectionRequired
          ? `安装匹配的同一 Agent 项目入口后，回到该 Agent，说明 ${SAME_AGENT_HANDOFF_BRIEF_ZH}。`
          : `回到 ${label || "Agent"}，说明 ${SAME_AGENT_HANDOFF_BRIEF_ZH}。`,
        selectionRequired
          ? `After installing the matching same-Agent project entry, return to that Agent with ${SAME_AGENT_HANDOFF_BRIEF_EN}.`
          : `Return to ${label || "Agent"} with ${SAME_AGENT_HANDOFF_BRIEF_EN}.`,
      ),
      install_agent_entry: command
        ? localeText("选择与你当前宿主匹配的同一 Agent 项目入口并安装。", "Choose the same-Agent project entry that matches your current host, then install it.")
        : localeText("选择与你当前宿主匹配的同一 Agent 项目入口。", "Choose the same-Agent project entry that matches your current host."),
      create_workdir: command
        ? localeText(`先创建目标项目目录：${command}`, `Create the target project directory first: ${command}`)
        : localeText("先创建目标项目目录。", "Create the target project directory first."),
      choose_workdir: localeText(
        "先选择一个可用的目标项目目录。",
        "Choose a usable target project directory first.",
      ),
      confirm_readiness: confirmReadinessText(),
      refresh_agent_host: selectionRequired
        ? localeText(
          "安装匹配的同一 Agent 项目入口后，刷新或重启该 Agent，让入口可见。",
          "After installing the matching same-Agent project entry, refresh or restart that Agent so the entry is visible.",
        )
        : localeText(
          "刷新或重启 Agent，让新的同一 Agent 项目入口可见。",
          "Refresh or restart the Agent so the new same-Agent project entry is visible.",
        ),
      confirm_agent_visibility: localeText(
        `如果 ${label || "Agent"} 中看不到 /loopora-plan 或 /loopora-run，请刷新或重启 ${label || "Agent"}。`,
        `If /loopora-plan or /loopora-run is not visible in ${label || "Agent"}, refresh or restart ${label || "Agent"}.`,
      ),
      run_loopora_plan: planBlockerEn
        ? localeText(
          `${planBlockerZh}后，运行 /loopora-plan 准备 Loop 预览。`,
          `After ${planBlockerEn}, run /loopora-plan to prepare the Loop preview.`,
        )
        : localeText(
          "运行 /loopora-plan 准备 Loop 预览。",
          "Run /loopora-plan to prepare the Loop preview.",
        ),
      review_ready_loop_preview: localeText(
        "审查 READY Loop 预览是否匹配任务判断。",
        "Review whether the READY Loop preview matches the task judgment.",
      ),
      run_loopora_run: readyReviewBlocked
        ? localeText(
          "READY Loop 预览匹配任务判断后，在同一 Agent 会话运行 /loopora-run。",
          "After the READY preview matches the task judgment, run /loopora-run in the same Agent session.",
        )
        : localeText(
          "在同一 Agent 会话运行 /loopora-run。",
          "Run /loopora-run in the same Agent session.",
        ),
      start_web: webOperation === "open_existing"
        ? (origin
          ? localeText(`打开现有 Loopora Web 服务：${origin}`, `Open the existing Loopora Web service: ${origin}`)
          : localeText("打开现有 Loopora Web 服务。", "Open the existing Loopora Web service."))
        : (origin
          ? localeText(`打开适用性判断/Web 选择：先做适用性判断，再选择创建路径：${webChoiceText}：${origin}`, `Open Fit Guide/Web choices in Web: Fit Guide first, then creation choices: ${webChoiceText}: ${origin}`)
          : localeText(`打开适用性判断/Web 选择：先做适用性判断，再选择创建路径：${webChoiceText}。`, `Open Fit Guide/Web choices in Web: Fit Guide first, then creation choices: ${webChoiceText}.`)),
      configure_web_auth: command
        ? localeText(`启动网络 Web 前先设置认证 token：${command}`, `Set a Web auth token before starting network Web: ${command}`)
        : localeText("启动网络 Web 前先设置认证 token。", "Set a Web auth token before starting network Web."),
      resolve_web_port: command
        ? localeText(
          `选择空闲 Web 端口，或停止占用当前端口的服务：${command}`,
          `Choose a free Web port or stop the service using the configured port: ${command}`,
        )
        : localeText(
          "选择空闲 Web 端口，或停止占用当前端口的服务。",
          "Choose a free Web port or stop the service using the configured port.",
        ),
      resolve_web_bind: command
        ? localeText(
          `选择其他 Web 绑定 host 或端口：${command}`,
          `Choose a different Web bind host or port: ${command}`,
        )
        : localeText("选择其他 Web 绑定 host 或端口。", "Choose a different Web bind host or port."),
      preview_app_database_reset: command
        ? localeText(
          `运行 /loopora-plan 或 Web 审查前，先预览 App 数据库重置范围：${command}`,
          `Before /loopora-plan or Web review, preview the App database reset scope: ${command}`,
        )
        : localeText(
          "运行 /loopora-plan 或 Web 审查前，先预览 App 数据库重置范围。",
          "Before /loopora-plan or Web review, preview the App database reset scope.",
        ),
      use_temporary_app_home: command
        ? localeText(
          `临时预览 Web 而不修改被阻断的 App 数据库：${command}`,
          `Preview Web temporarily without changing the blocked App database: ${command}`,
        )
        : localeText(
          "临时预览 Web，而不修改被阻断的 App 数据库。",
          "Preview Web temporarily without changing the blocked App database.",
        ),
    };
    return labels[kind] || "";
  }

  function shortCommandLabel(command) {
    const value = String(command || "").trim();
    const leadingEnv = value.match(/^(?:[A-Z_][A-Z0-9_]*=(?:'[^']*'|"[^"]*"|\S+)\s+)+/)?.[0] || "";
    const envNames = [...leadingEnv.matchAll(/([A-Z_][A-Z0-9_]*)=/g)].map((match) => String(match[1] || ""));
    const envPrefix = envNames.map((name) => `${name}=${name === "LOOPORA_HOME" ? "<app-home>" : "<value>"}`).join(" ");
    const withoutEnv = value.slice(leadingEnv.length);
    const display = withoutEnv
      .replace(/(^|\s)--directory\s+(?:"[^"]*"|'[^']*'|\S+)/g, (_match, prefix) => `${prefix}--directory <Loopora checkout>`)
      .replace(/(^|\s)--workdir\s+(?:"[^"]*"|'[^']*'|\S+)/g, (_match, prefix) => `${prefix}--workdir <target>`)
      .replace(/\s+/g, " ")
      .trim();
    return [envPrefix, display].filter(Boolean).join(" ");
  }

  function agentReadinessCopyButton({testId, command, labelZh, labelEn, shortLabel}) {
    const value = String(command || "").trim();
    if (!value) {
      return "";
    }
    const label = localeText(labelZh, labelEn);
    const displayCommand = String(shortLabel || shortCommandLabel(value)).trim();
    const accessibleLabel = localeText(`${label}：${value}`, `${label}: ${value}`);
    return `
      <button
        class="agent-readiness-copy-button"
        type="button"
        data-agent-readiness-copy="${escapeHtml(value)}"
        data-testid="${escapeHtml(testId)}"
        title="${escapeHtml(value)}"
        aria-label="${escapeHtml(accessibleLabel)}"
      >
        <span class="agent-readiness-copy-label">${escapeHtml(label)}</span>
        <code>${escapeHtml(displayCommand)}</code>
      </button>
    `;
  }

  function agentReadinessSteps(payload, fallbackSteps) {
    const steps = agentReadinessActionItems(payload).map(agentReadinessActionStep).filter(Boolean);
    return steps.length ? steps : fallbackSteps;
  }

  function agentReadinessCurrentTargetCommand(payload = lastAgentReadinessPayload) {
    const commands = payload?.commands && typeof payload.commands === "object" ? payload.commands : {};
    return String(commands.confirm_readiness || "").trim();
  }

  function renderAgentReadiness(payload) {
    if (!agentReadinessSummary) {
      return;
    }
    lastAgentReadinessPayload = payload || null;
    const entry = agentReadinessPrimaryEntry(payload);
    const adapter = selectedAgentAdapter;
    const label = String(entry?.label || agentAdapterLabel(adapter));
    const hasSelectedHost = Boolean(adapter);
    const selectedReady = entry?.ready === true;
    const workdir = String(payload?.workdir || agentAdapterWorkdir() || "").trim();
    const hasExplicitTarget = Boolean(agentAdapterWorkdir());
    const {directPathBlocksAgentSetup, reviewBlocksAgentInstall} = syncAgentAdapterFitGates(
      readFitHandoff(),
      agentAdapterWorkdir(),
    );
    const webOrigin = String(payload?.web?.origin || "").trim();
    const appState = agentReadinessAppState(payload);
    const webBlocked = agentReadinessWebBlocked(payload);
    const appStateWebBlocked = agentReadinessWebAppStateBlocked(payload);
    const webBlockerSummary = agentReadinessWebBlockerSummary(payload);
    const resetCommand = agentReadinessActionCommand(payload, "preview_app_database_reset")
      || appStateCommand(appState, "preview_reset")
      || appStateCommand(appState, "reset");
    const recoveryArchiveCommand = agentReadinessActionCommand(payload, "create_recovery_archive")
      || appStateCommand(appState, "recovery_archive");
    const temporaryAppHomeCommand = agentReadinessActionCommand(payload, "use_temporary_app_home");
    const createWorkdirCommand = agentReadinessActionCommand(payload, "create_workdir");
    const projectDirectoryBlocked = agentReadinessActionItems(payload).some((item) => (
      String(item?.kind || "") === "create_workdir" || String(item?.kind || "") === "choose_workdir"
    ));
    const readinessCommand = agentReadinessCurrentTargetCommand(payload)
      || agentReadinessActionCommand(payload, "confirm_readiness");
    const checkCommand = agentReadinessCommand(entry, "install_check") || agentReadinessCommand(entry, "agent_check");
    const webActionButton = agentReadinessWebActionCopyButton(payload);
    const title = !hasExplicitTarget
      ? localeText("先确认同一 Agent 目标项目", "Confirm the same-Agent target project")
      : directPathBlocksAgentSetup
      ? localeText("当前任务已选择直接路径", "The current task uses a direct path")
      : !hasSelectedHost
      ? localeText("选择你现在使用的 Agent", "Choose the Agent you are using now")
      : reviewBlocksAgentInstall
      ? localeText("先完成当前任务的 Fit Review", "Finish the current task's Fit Review")
      : selectedReady
      ? localeText(`${label} 已经可以启动 Loopora`, `${label} can start Loopora`)
      : localeText(`${label} 还需要项目入口`, `${label} needs its project entry`);
    const detail = !hasExplicitTarget
      ? localeText(
        "尚未选择同一 Agent 目标项目。填写你正在使用 Codex、Claude Code 或 OpenCode 的项目目录，或使用服务目录作为显式目标后，再安装入口、复制命令或生成公开报告。",
        "No same-Agent target project is selected yet. Enter the project directory where you are using Codex, Claude Code, or OpenCode, or adopt the service folder as the explicit target before installing same-Agent project entries, copying commands, or generating a public report.",
      )
      : directPathBlocksAgentSetup
      ? localeText(
        "Fit Guide 已确认直接 Agent、硬性检查或现有项目流程更合适，因此这个任务不会安装或更新 Loopora 项目入口，也不会提供 /loopora-plan 或 /loopora-run 交接。可复制直接路径命令，或清除该决策后重新评审。",
        "Fit Guide confirmed that direct Agent work, hard checks, or the existing project process is a better fit, so this task will not install or update a Loopora project entry or expose /loopora-plan or /loopora-run handoff. Copy the direct-path command, or clear the decision and review again.",
      )
      : !hasSelectedHost
      ? localeText(
        "选择当前 Codex、Claude Code 或 OpenCode 宿主。Loopora 只会显示并管理这个宿主的项目入口。",
        "Choose the current Codex, Claude Code, or OpenCode host. Loopora will show and manage only that host's project entry.",
      )
      : reviewBlocksAgentInstall
      ? localeText(
        "当前任务只完成了部分 Fit Review。项目入口状态仍可检查，旧入口仍可卸载；安装或更新以及 /loopora-plan、/loopora-run 交接会等到五项判断全部审查完成。",
        "The current task has only a partial Fit Review. Project entry status remains inspectable and an old entry may still be uninstalled; install or update plus /loopora-plan and /loopora-run handoff wait until all five judgments are reviewed.",
      )
      : selectedReady
      ? localeText(
        `${label} 的项目入口可用${webBlocked ? `；Web 就绪需处理：${webBlockerSummary}` : ""}。回到 ${label} 说明 ${SAME_AGENT_HANDOFF_BRIEF_ZH}。`,
        `${label}'s project entry is ready${webBlocked ? `; Web readiness needs attention: ${webBlockerSummary}` : ""}. Return to ${label} with ${SAME_AGENT_HANDOFF_BRIEF_EN}.`,
      )
      : projectDirectoryBlocked
      ? localeText(
        "先处理目标项目目录，再重新确认 readiness；目录可用前不会显示安装同一 Agent 项目入口命令。",
        "Handle the target project directory first, then confirm readiness again; install commands stay hidden until the directory is usable.",
      )
      : localeText(
        `为目标项目安装或更新 ${label} 的同一 Agent 项目入口。安装后刷新或重启 ${label}，再回到任务里运行 /loopora-plan。${webBlocked ? `打开 Web 前还需要处理：${webBlockerSummary}。` : ""}`,
        `Install or update ${label}'s same-Agent project entry for the target project. Then refresh or restart ${label} and run /loopora-plan in the task.${webBlocked ? ` Web readiness also needs attention before opening Web: ${webBlockerSummary}.` : ""}`,
      );
    const fallbackSteps = selectedReady
      ? [
        localeText("把任务判断交给 /loopora-plan。", "Give the task judgment to /loopora-plan."),
        localeText("审查 READY Loop 预览。", "Review the READY Loop preview."),
        webBlocked
          ? localeText(`先处理 Web 就绪阻塞：${webBlockerSummary}。`, `Handle Web readiness blockers before using Web for creation or review: ${webBlockerSummary}.`)
          : localeText("在同一 Agent 会话运行 /loopora-run。", "Run /loopora-run in the same Agent session."),
      ]
      : [
        localeText("确认目标项目目录。", "Confirm the target project directory."),
        localeText("选择当前宿主 adapter 并安装同一 Agent 项目入口。", "Choose the current host adapter and install its same-Agent project entry."),
        webBlocked
          ? localeText(`打开 Web 前处理 Web 就绪阻塞：${webBlockerSummary}。`, `Handle Web readiness blockers before opening Web: ${webBlockerSummary}.`)
          : localeText("回到 Agent 运行 /loopora-plan。", "Return to the Agent and run /loopora-plan."),
      ];
    const targetRequiredSteps = [
      localeText("填写正在使用 Codex、Claude Code 或 OpenCode 的项目目录，或点击“使用服务目录”。", "Enter the project directory where you are using Codex, Claude Code, or OpenCode, or choose the service folder."),
      localeText("刷新后再复制安装、就绪检查或公开诊断报告。", "After refresh, copy install, readiness, or public diagnostic commands."),
      localeText("安装入口后再回到对应 Agent 运行 /loopora-plan。", "After installing an entry, return to that Agent and run /loopora-plan."),
    ];
    const directPathSteps = [
      localeText("按 Fit Guide 记录的直接路径处理当前任务。", "Follow the direct path recorded by Fit Guide for this task."),
      localeText("需要命令时从 Fit Guide 决策面板复制，保持该判断可追溯。", "Copy the command from the Fit Guide decision panel when needed so the judgment stays traceable."),
      localeText("任务边界变化时，清除该决策并重新完成 Fit Review。", "If the task boundary changes, clear the decision and complete Fit Review again."),
    ];
    const incompleteReviewSteps = [
      localeText("回到 Web 对话或 Fit Guide 补齐剩余判断。", "Return to Web conversation or Fit Guide to complete the remaining judgments."),
      localeText("在审查完成前，只读取入口和 readiness 状态；不要安装或更新。", "Until review is complete, inspect entry and readiness status only; do not install or update."),
      localeText("五项判断完成后，再继续项目入口和 /loopora-plan 交接。", "After all five judgments are complete, resume project entry setup and /loopora-plan handoff."),
    ];
    const steps = !hasExplicitTarget
      ? targetRequiredSteps
      : directPathBlocksAgentSetup
      ? directPathSteps
      : reviewBlocksAgentInstall && hasSelectedHost
      ? incompleteReviewSteps
      : projectDirectoryBlocked
      ? agentReadinessSteps(payload, fallbackSteps)
      : fallbackSteps;
    const resetButton = appStateWebBlocked
      ? agentReadinessCopyButton({
        testId: "agent-readiness-copy-reset",
        command: resetCommand,
        labelZh: "复制重置预览",
        labelEn: "Copy reset preview",
      })
      : "";
    const recoveryArchiveButton = appStateWebBlocked
      ? agentReadinessCopyButton({
        testId: "agent-readiness-copy-recovery-archive",
        command: recoveryArchiveCommand,
        labelZh: "复制私有恢复归档命令",
        labelEn: "Copy private recovery archive",
      })
      : "";
    const temporaryAppHomeButton = appStateWebBlocked
      ? agentReadinessCopyButton({
        testId: "agent-readiness-copy-temporary-app-home",
        command: temporaryAppHomeCommand,
        labelZh: "复制临时 Web 预览",
        labelEn: "Copy temporary Web preview",
      })
      : "";
    const createWorkdirButton = agentReadinessCopyButton({
      testId: "agent-readiness-copy-create-workdir",
      command: createWorkdirCommand,
      labelZh: "复制创建目录",
      labelEn: "Copy create directory",
    });
    const actionButtons = !hasExplicitTarget || !hasSelectedHost
      ? ""
      : directPathBlocksAgentSetup
      ? ""
      : reviewBlocksAgentInstall
      ? `
        ${agentReadinessCopyButton({testId: "agent-readiness-copy-readiness", command: checkCommand || readinessCommand, labelZh: "复制就绪检查", labelEn: "Copy readiness check"})}
        ${webActionButton}
      `
      : selectedReady
      ? `
        ${recoveryArchiveButton}
        ${resetButton}
        ${temporaryAppHomeButton}
        ${agentReadinessCopyButton({testId: "agent-readiness-copy-plan", command: "/loopora-plan", labelZh: "复制计划入口", labelEn: "Copy plan entry", shortLabel: "/loopora-plan"})}
        ${agentReadinessCopyButton({testId: "agent-readiness-copy-run", command: "/loopora-run", labelZh: "复制运行入口", labelEn: "Copy run entry", shortLabel: "/loopora-run"})}
        ${webActionButton}
      `
      : `
        ${createWorkdirButton}
        ${recoveryArchiveButton}
        ${resetButton}
        ${temporaryAppHomeButton}
        ${agentReadinessCopyButton({testId: "agent-readiness-copy-readiness", command: checkCommand || readinessCommand, labelZh: "复制就绪检查", labelEn: "Copy readiness check"})}
        ${webActionButton}
      `;
    const publicReportButton = hasExplicitTarget ? `
      <button class="agent-readiness-copy-button" type="button" data-agent-readiness-copy-public="true" data-testid="agent-readiness-copy-public">
        ${escapeHtml(localeText("复制公开诊断报告", "Copy public report"))}
      </button>
    ` : "";
    const workdirLabel = hasExplicitTarget
      ? localeText("目标项目", "Target project")
      : localeText("目标项目未选择", "No target selected");
    const appHomeNote = agentReadinessPreservesConfiguredAppHome(payload, entry)
      ? `<span data-testid="agent-readiness-app-home-note">${escapeHtml(localeText(
        "复制命令会保留当前 Web 会话的 LOOPORA_HOME。",
        "Copyable commands preserve this Web session's LOOPORA_HOME.",
      ))}</span>`
      : "";
    const scopedReadiness = {...payload, ready: selectedReady};
    const pillLabel = !hasExplicitTarget
      ? localeText("需要目标项目", "Needs target")
      : directPathBlocksAgentSetup
      ? localeText("直接路径", "Direct path")
      : !hasSelectedHost
      ? localeText("选择 Agent", "Choose Agent")
      : reviewBlocksAgentInstall
      ? localeText("审查未完成", "Review incomplete")
      : agentReadinessStatusLabel(scopedReadiness);
    const pillClass = directPathBlocksAgentSetup || !hasSelectedHost
      ? "wake-lock-pill wake-lock-pill-neutral"
      : reviewBlocksAgentInstall
      ? "wake-lock-pill wake-lock-pill-warning"
      : agentReadinessPillClass(scopedReadiness);
    agentReadinessSummary.dataset.readinessStatus = String(payload?.status || "");
    agentReadinessSummary.dataset.fitReviewGate = directPathBlocksAgentSetup
      ? "direct_path"
      : reviewBlocksAgentInstall
        ? "incomplete"
        : "ready";
    agentReadinessSummary.innerHTML = `
      <div class="agent-readiness-head">
        <div class="agent-readiness-copy">
          <strong data-testid="agent-readiness-title">${escapeHtml(title)}</strong>
          <span data-testid="agent-readiness-detail">${escapeHtml(detail)}</span>
        </div>
        <span class="${escapeHtml(pillClass)}" data-testid="agent-readiness-pill">${escapeHtml(pillLabel)}</span>
      </div>
      <div class="agent-readiness-meta">
        <span>${escapeHtml(workdirLabel)}: ${escapeHtml(workdir || "-")}</span>
        ${webOrigin ? `<span>${escapeHtml(localeText("适用性判断/Web 选择入口", "Fit Guide/Web choices entry"))}: ${escapeHtml(webOrigin)}</span>` : ""}
        <span>${escapeHtml(appStateStatusLabel(appState))}</span>
        <span>${escapeHtml(agentReadinessWebStatusLabel(payload))}</span>
        ${appHomeNote}
      </div>
      <ol class="agent-readiness-steps" data-testid="agent-readiness-steps">
        ${steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}
      </ol>
      <div class="agent-readiness-actions" data-testid="agent-readiness-actions">${actionButtons}${publicReportButton}</div>
      <div class="agent-readiness-public-report" data-agent-readiness-command-manual-copy data-testid="agent-readiness-command-manual-copy" hidden></div>
      <div class="agent-readiness-public-report" data-agent-readiness-public-report data-testid="agent-readiness-public-report" hidden></div>
    `;
  }

  function renderAgentReadinessPending(workdir) {
    if (!agentReadinessSummary) {
      return;
    }
    const target = String(workdir || "").trim();
    agentReadinessSummary.dataset.readinessStatus = "refreshing";
    agentReadinessSummary.innerHTML = `
      <div class="agent-readiness-head">
        <div class="agent-readiness-copy">
          <strong data-testid="agent-readiness-title">${escapeHtml(localeText("正在刷新目标项目", "Refreshing target project"))}</strong>
          <span data-testid="agent-readiness-detail">${escapeHtml(localeText(
            "正在重新读取这个目录的同一 Agent 项目入口和本地 App 状态，旧目标项目的命令会暂时隐藏。",
            "Reading this directory's same-Agent project entries and local App state; commands from the previous target are temporarily hidden.",
          ))}</span>
        </div>
        <span class="wake-lock-pill wake-lock-pill-neutral" data-testid="agent-readiness-pill">${escapeHtml(localeText("刷新中", "Refreshing"))}</span>
      </div>
      <div class="agent-readiness-meta">
        <span>${escapeHtml(localeText("目标项目", "Target project"))}: ${escapeHtml(target || "-")}</span>
      </div>
      <ol class="agent-readiness-steps" data-testid="agent-readiness-steps">
        <li>${escapeHtml(localeText("确认目标项目目录。", "Confirm the target project directory."))}</li>
        <li>${escapeHtml(localeText("等待就绪检查完成。", "Wait for readiness checks to finish."))}</li>
        <li>${escapeHtml(localeText("再复制安装、检查或运行命令。", "Copy install, check, or run commands after refresh."))}</li>
      </ol>
      <div class="agent-readiness-actions" data-testid="agent-readiness-actions"></div>
    `;
  }

  function clearAgentAdapterHandoff() {
    if (!agentAdapterHandoff) {
      return;
    }
    agentAdapterHandoffUsesFitDraft = false;
    agentAdapterHandoff.hidden = true;
    agentAdapterHandoff.innerHTML = "";
    renderFitHandoff();
  }

  function clearPendingAgentAdapterUninstall() {
    pendingAgentAdapterUninstall = null;
    for (const button of agentAdapterUninstallButtons) {
      button.classList.remove("danger-button");
      button.removeAttribute("data-agent-adapter-uninstall-confirm");
      button.innerHTML = `
        <span data-lang="zh">卸载</span>
        <span data-lang="en">Uninstall</span>
      `;
    }
  }

  function agentAdapterUninstallSignature(adapter) {
    return `${String(adapter || "").trim()}\n${agentAdapterWorkdir()}`;
  }

  function markAgentAdapterUninstallPending(adapter, button) {
    clearPendingAgentAdapterUninstall();
    pendingAgentAdapterUninstall = {
      adapter: String(adapter || "").trim(),
      signature: agentAdapterUninstallSignature(adapter),
    };
    if (button instanceof HTMLButtonElement) {
      button.classList.add("danger-button");
      button.setAttribute("data-agent-adapter-uninstall-confirm", "1");
      button.innerHTML = `
        <span data-lang="zh">确认卸载</span>
        <span data-lang="en">Confirm uninstall</span>
      `;
    }
  }

  function agentAdapterUninstallIsPending(adapter) {
    return pendingAgentAdapterUninstall?.signature === agentAdapterUninstallSignature(adapter);
  }

  function publicReportManualCopyContainer(trigger = null) {
    const supportContainer = trigger?.closest?.("[data-testid='tools-support-panel']")
      ?.querySelector?.("[data-support-public-report-manual-copy]");
    return supportContainer || agentReadinessSummary?.querySelector?.("[data-agent-readiness-public-report]");
  }

  function clearAgentReadinessPublicReportManualCopy() {
    clearAgentCommandManualCopy();
    [
      agentReadinessSummary?.querySelector?.("[data-agent-readiness-public-report]"),
      toolsSupportPanel?.querySelector?.("[data-support-public-report-manual-copy]"),
    ].forEach((container) => renderAgentReadinessPublicReportManualCopy("", container));
  }

  function renderManualCopyTextarea(copyText, container, options = {}) {
    window.LooporaUI?.renderManualCopy?.(container, copyText, {
      label: options.label || localeText("手动复制", "Manual copy"),
      textareaId: options.textareaId || "agent-readiness-manual-copy-textarea",
      rows: options.rows || 10,
    });
  }

  function agentCommandManualCopyContainer(button = null) {
    const handoffContainer = button?.closest?.("#agent-adapter-handoff")
      ?.querySelector?.("[data-agent-adapter-command-manual-copy]");
    return handoffContainer || agentReadinessSummary?.querySelector?.("[data-agent-readiness-command-manual-copy]");
  }

  function renderAgentCommandManualCopy(command, button = null) {
    const isHandoffCommand = Boolean(button?.closest?.("#agent-adapter-handoff"));
    renderManualCopyTextarea(command, agentCommandManualCopyContainer(button), {
      label: localeText("手动复制 Agent 命令", "Manual Agent command copy"),
      textareaId: isHandoffCommand
        ? "agent-adapter-command-manual-copy-textarea"
        : "agent-readiness-command-manual-copy-textarea",
      rows: 4,
    });
  }

  function clearAgentCommandManualCopy() {
    [
      agentReadinessSummary?.querySelector?.("[data-agent-readiness-command-manual-copy]"),
      agentAdapterHandoff?.querySelector?.("[data-agent-adapter-command-manual-copy]"),
    ].forEach((container) => renderManualCopyTextarea("", container));
  }

  function renderAgentReadinessPublicReportManualCopy(reportText, container = publicReportManualCopyContainer()) {
    const textareaId = container?.hasAttribute?.("data-support-public-report-manual-copy")
      ? "tools-support-public-report-textarea"
      : "agent-readiness-public-report-textarea";
    renderManualCopyTextarea(reportText, container, {
      label: localeText("手动复制公开诊断报告", "Manual public report copy"),
      textareaId,
    });
  }

  function draftHandoffManualCopyContainer() {
    return agentAdapterDraftHandoff?.querySelector?.("[data-agent-draft-handoff-manual-copy]");
  }

  function renderDraftHandoffManualCopy(copyText, label) {
    renderManualCopyTextarea(copyText, draftHandoffManualCopyContainer(), {
      label,
      textareaId: "agent-draft-handoff-manual-copy-textarea",
    });
  }

  function clearDraftHandoffManualCopy() {
    renderDraftHandoffManualCopy("", "");
  }

  async function copyAgentReadinessPublicReport(button, statusBox = agentAdapterStatusBox) {
    const manualCopyContainer = publicReportManualCopyContainer(button);
    clearAgentReadinessPublicReportManualCopy();
    const {response, payload} = await fetchJson(agentReadinessPublicUrl());
    if (!response.ok) {
      throw new Error(payload.error || localeText("无法读取公开诊断报告。", "Unable to load the public report."));
    }
    const reportText = JSON.stringify(payload, null, 2);
    try {
      await copyText(reportText);
      clearAgentReadinessPublicReportManualCopy();
      button.classList.add("is-copied");
      showStatus(statusBox, localeText("已复制公开诊断报告。", "Public report copied."), "success");
      window.setTimeout(() => button.classList.remove("is-copied"), 1400);
    } catch (_) {
      renderAgentReadinessPublicReportManualCopy(reportText, manualCopyContainer);
      showStatus(
        statusBox,
        localeText("浏览器未允许自动复制；请手动复制下面的公开诊断报告。", "The browser blocked automatic copy; copy the public report below manually."),
        "warning",
      );
    }
  }

  async function refreshAgentReadiness(options = {}) {
    const quiet = options.quiet ?? false;
    const expectedWorkdir = options.expectedWorkdir ?? agentAdapterWorkdir();
    const {response, payload} = await fetchJson(agentReadinessUrl());
    if (!agentAdapterResponseMatchesExpected(payload, expectedWorkdir)) {
      return;
    }
    if (!response.ok) {
      if (!quiet) {
        showStatus(agentAdapterStatusBox, payload.error || localeText("无法读取本地就绪状态。", "Unable to load local readiness."), "error");
      }
      return;
    }
    normalizeAgentAdapterTargetFromPayload(payload, expectedWorkdir);
    setToolsSupportTargetDataset(String(payload?.workdir_state?.status || "").trim(), Boolean(agentAdapterWorkdir()));
    syncToolsSupportTargetState();
    renderAgentReadiness(payload);
    rerenderAgentAdapterHandoff();
    if (!quiet) {
      showStatus(agentAdapterStatusBox, "");
    }
  }

  function agentAdapterStatusLabel(status) {
    const labels = {
      installed: localeText("已安装", "Installed"),
      not_installed: localeText("未安装", "Not installed"),
      needs_update: localeText("需要更新", "Needs update"),
      error: localeText("不可判断", "Needs attention"),
      not_implemented: localeText("当前构建不可用", "Unavailable in this build"),
      blocked_by_workdir: localeText("需要目标项目", "Needs target project"),
    };
    return labels[status] || localeText("未知状态", "Unknown");
  }

  function agentAdapterPillClass(status) {
    if (status === "installed") {
      return "wake-lock-pill wake-lock-pill-held";
    }
    if (status === "needs_update") {
      return "wake-lock-pill wake-lock-pill-queued";
    }
    if (status === "error") {
      return "wake-lock-pill wake-lock-pill-warning";
    }
    if (status === "blocked_by_workdir") {
      return "wake-lock-pill wake-lock-pill-warning";
    }
    return "wake-lock-pill wake-lock-pill-neutral";
  }

  function agentAdapterCanHandoff(item) {
    const status = String(item?.status || "");
    return item?.implemented !== false && (status === "installed" || status === "needs_update");
  }

  function ensureAgentHostSelection(adapters, payload) {
    const supported = new Set(adapters.map((item) => String(item?.adapter || "")).filter(Boolean));
    if (selectedAgentAdapter && supported.has(selectedAgentAdapter)) {
      return;
    }
    const detectedHost = payload?.current_agent_host;
    const detectedAdapter = String(detectedHost?.adapter || "");
    if (String(detectedHost?.state || "") === "detected" && supported.has(detectedAdapter)) {
      selectedAgentAdapter = detectedAdapter;
      preferredAgentAdapterHandoff = selectedAgentAdapter;
      return;
    }
    const installed = adapters.filter(agentAdapterCanHandoff);
    selectedAgentAdapter = installed.length === 1 ? String(installed[0]?.adapter || "") : "";
    preferredAgentAdapterHandoff = selectedAgentAdapter;
  }

  function syncAgentHostSelection(adapters) {
    const byKind = new Map(adapters.map((item) => [String(item?.adapter || ""), item]));
    for (const input of agentHostInputs) {
      input.checked = String(input.dataset.agentHost || "") === selectedAgentAdapter;
    }
    for (const option of agentHostOptions) {
      option.classList.toggle("is-active", String(option.dataset.agentHostOption || "") === selectedAgentAdapter);
    }
    for (const node of agentHostStatusNodes) {
      const adapter = String(node.dataset.agentHostStatus || "");
      const status = String(byKind.get(adapter)?.status || "not_installed");
      node.textContent = agentAdapterStatusLabel(status);
    }
    if (agentAdapterGrid) {
      agentAdapterGrid.hidden = !selectedAgentAdapter;
    }
    if (agentAdapterNextSteps) {
      agentAdapterNextSteps.hidden = !selectedAgentAdapter || agentAdapterCanHandoff(byKind.get(selectedAgentAdapter));
    }
    for (const card of agentAdapterCards) {
      card.hidden = String(card.dataset.agentAdapter || "") !== selectedAgentAdapter;
    }
    if (!agentHostSelectionStatus) {
      return;
    }
    const item = byKind.get(selectedAgentAdapter);
    const label = agentAdapterLabel(selectedAgentAdapter);
    const status = String(item?.status || "not_installed");
    agentHostSelectionStatus.textContent = !selectedAgentAdapter
      ? localeText(
        "先选择当前宿主，再安装或管理它的项目入口。",
        "Choose the current host before installing or managing its project entry.",
      )
      : fitDirectPathBlocksAgentSetup
      ? localeText(
        `${label} 已选中；当前任务采用直接路径，同一 Agent setup 与任务交接已停用。`,
        `${label} selected; the current task uses a direct path, so same-Agent setup and task handoff are disabled.`,
      )
      : fitReviewBlocksAgentInstall
      ? localeText(
        `${label} 已选中；当前任务审查未完成，安装或更新与 plan/run 交接暂缓。`,
        `${label} selected; the current task review is incomplete, so install or update and plan/run handoff are waiting.`,
      )
      : agentAdapterCanHandoff(item)
      ? localeText(
        `${label} 已选中；${status === "needs_update" ? "更新入口后再继续" : "项目入口可以继续使用"}。`,
        `${label} selected; ${status === "needs_update" ? "update its entry before continuing" : "its project entry is ready"}.`,
      )
      : localeText(
        `${label} 已选中；为这个目标项目安装它的入口。`,
        `${label} selected; install its entry for this target project.`,
      );
  }

  function renderAgentAdapters(payload) {
    updateAgentAdapterTargetNote(payload);
    const adapters = Array.isArray(payload?.adapters) ? payload.adapters : [payload].filter(Boolean);
    lastAgentAdapterPayload = payload || null;
    lastAgentAdapterItems = adapters;
    for (const item of adapters) {
      rememberAgentAdapterFirstTaskHandoffPolicy(String(item?.adapter || ""), item);
    }
    ensureAgentHostSelection(adapters, payload);
    const byKind = new Map(adapters.map((item) => [String(item?.adapter || ""), item]));
    const implementedFallbacks = new Set(["codex", "claude", "opencode"]);
    const hasExplicitTarget = Boolean(agentAdapterWorkdir());
    const targetRequiredMessage = agentAdapterTargetRequiredMessage();
    syncAgentAdapterFitGates(readFitHandoff(), agentAdapterWorkdir());
    for (const node of agentAdapterStatusNodes) {
      const adapter = String(node.dataset.agentAdapterStatus || "");
      const item = byKind.get(adapter);
      const status = String(item?.status || (implementedFallbacks.has(adapter) ? "not_installed" : "not_implemented"));
      node.dataset.agentAdapterState = status;
      updateNodeTextAndClass(node, agentAdapterStatusLabel(status), agentAdapterPillClass(status));
    }
    for (const card of agentAdapterCards) {
      const adapter = String(card.dataset.agentAdapter || "");
      const item = byKind.get(adapter);
      const status = String(item?.status || (implementedFallbacks.has(adapter) ? "not_installed" : "not_implemented"));
      card.dataset.agentAdapterState = status;
      card.classList.toggle("is-disabled", status === "not_implemented");
      card.classList.toggle("is-error", status === "error");
    }
    for (const button of agentAdapterInstallButtons) {
      const adapter = String(button.dataset.agentAdapterInstall || "");
      const item = byKind.get(adapter);
      setAgentAdapterMutationButtonBaseState(
        button,
        !hasExplicitTarget || adapter !== selectedAgentAdapter || item?.implemented === false,
        !hasExplicitTarget ? targetRequiredMessage : adapter !== selectedAgentAdapter ? localeText("先选择这个 Agent 作为当前宿主。", "Choose this Agent as the current host first.") : "",
      );
    }
    for (const button of agentAdapterUninstallButtons) {
      const adapter = String(button.dataset.agentAdapterUninstall || "");
      const item = byKind.get(adapter);
      setAgentAdapterMutationButtonBaseState(
        button,
        !hasExplicitTarget || adapter !== selectedAgentAdapter || item?.implemented === false || item?.status === "not_installed",
        !hasExplicitTarget ? targetRequiredMessage : adapter !== selectedAgentAdapter ? localeText("先选择这个 Agent 作为当前宿主。", "Choose this Agent as the current host first.") : "",
      );
    }
    syncAgentHostSelection(adapters);
    if (lastAgentReadinessPayload) {
      renderAgentReadiness(lastAgentReadinessPayload);
    }
    renderAgentAdapterHandoff(payload, adapters);
    renderFitHandoff();
  }

  function renderAgentAdaptersPending() {
    for (const node of agentAdapterStatusNodes) {
      node.dataset.agentAdapterState = "refreshing";
      updateNodeTextAndClass(node, localeText("刷新中", "Refreshing"), "wake-lock-pill wake-lock-pill-neutral");
    }
    for (const card of agentAdapterCards) {
      card.dataset.agentAdapterState = "refreshing";
      card.classList.remove("is-error");
      card.classList.add("is-disabled");
    }
    for (const button of [...agentAdapterInstallButtons, ...agentAdapterUninstallButtons]) {
      setAgentAdapterMutationButtonBaseState(button, true);
    }
  }

  function agentAdapterLabel(adapter) {
    const labels = {
      codex: "Codex",
      claude: "Claude Code",
      opencode: "OpenCode",
    };
    return labels[adapter] || adapter || "Agent";
  }

  function updateAgentAdapterTargetNote(payload) {
    if (!agentAdapterTargetNote) {
      return;
    }
    const explicitWorkdir = agentAdapterWorkdir();
    const resolvedWorkdir = String(payload?.workdir || "").trim();
    if (!explicitWorkdir) {
      updateAgentAdapterUseServerWorkdirButton(resolvedWorkdir);
      agentAdapterTargetNote.textContent = localeText(
        resolvedWorkdir
          ? "从上方项目切换器或输入框确认 Agent 正在使用的项目；也可以采用服务目录。确认后，Web 作用域和入口操作会使用同一项目。"
          : "从上方“切换项目”选择最近项目，或填写 Agent 将运行的绝对目录；两处目标会保持同步。",
        resolvedWorkdir
          ? "Confirm the Agent's project with the project switcher or this input; you can also adopt the service folder. Web scope and entry actions then use the same project."
          : "Choose a recent project from Switch project above, or enter the absolute directory where the Agent will run. Both target controls stay in sync.",
      );
      agentAdapterTargetNote.title = resolvedWorkdir;
      return;
    }
    updateAgentAdapterUseServerWorkdirButton("");
    const workdir = resolvedWorkdir || explicitWorkdir;
    agentAdapterTargetNote.textContent = localeText(
      `当前设置目标：${workdir}。它也是 Web 项目作用域；确认这是你正在使用 Codex、Claude Code 或 OpenCode 的项目。`,
      `Setup target: ${workdir}. This is also the Web project scope; confirm it is the project used by Codex, Claude Code, or OpenCode.`,
    );
    agentAdapterTargetNote.title = workdir;
  }

  function updateAgentAdapterUseServerWorkdirButton(workdir) {
    if (!agentAdapterUseServerWorkdirButton) {
      return;
    }
    const value = String(workdir || "").trim();
    agentAdapterUseServerWorkdirButton.hidden = !value;
    agentAdapterUseServerWorkdirButton.disabled = !value;
    agentAdapterUseServerWorkdirButton.dataset.serverWorkdir = value;
    agentAdapterUseServerWorkdirButton.title = value
      ? localeText(`使用服务当前目录：${value}`, `Use service current folder: ${value}`)
      : "";
    agentAdapterUseServerWorkdirButton.setAttribute(
      "aria-label",
      value
        ? localeText(`使用服务当前目录作为目标项目：${value}`, `Use service current folder as the target project: ${value}`)
        : localeText("使用服务当前目录作为目标项目", "Use service current folder as the target project"),
    );
  }

  function applyAgentAdapterServerWorkdir() {
    const workdir = String(agentAdapterUseServerWorkdirButton?.dataset.serverWorkdir || "").trim();
    setAgentAdapterTargetWorkdir(workdir, {
      message: localeText("已把服务目录设为目标项目。", "Service folder set as the target project."),
    });
  }

  function setAgentAdapterTargetWorkdir(workdir, options = {}) {
    const value = String(workdir || "").trim();
    if (!value || !agentAdapterWorkdirInput) {
      return;
    }
    agentAdapterWorkdirInput.value = value;
    agentAdapterWorkdirInput.focus();
    persistAgentAdapterWorkdirPreference(value);
    window.LooporaUI.syncWorkdirContext(value, {syncUrl: true, urlParam: "workdir"});
    refreshAgentAdapterTargetFromInput({delayMs: 0, preservePendingContext: true});
    if (options.message) {
      showStatus(agentAdapterStatusBox, options.message, "success");
    }
  }

  function agentAdapterResponseWorkdir(payload) {
    return String(payload?.workdir || "").trim();
  }

  function agentAdapterResponseMatchesExpected(payload, expectedWorkdir) {
    if (expectedWorkdir === undefined) {
      return true;
    }
    const current = agentAdapterWorkdir();
    if (current === expectedWorkdir) {
      return true;
    }
    const resolved = agentAdapterResponseWorkdir(payload);
    return Boolean(resolved && current === resolved);
  }

  function normalizeAgentAdapterTargetFromPayload(payload, expectedWorkdir) {
    const resolved = agentAdapterResponseWorkdir(payload);
    if (!resolved || !agentAdapterWorkdirInput) {
      return;
    }
    const current = agentAdapterWorkdir();
    if (!current) {
      return;
    }
    if (expectedWorkdir !== undefined && current !== expectedWorkdir) {
      return;
    }
    if (current !== resolved) {
      agentAdapterWorkdirInput.value = resolved;
    }
    persistAgentAdapterWorkdirPreference(resolved);
    window.LooporaUI.syncWorkdirContext(resolved, {syncUrl: true, urlParam: "workdir"});
    syncToolsSupportTargetState();
  }

  async function browseAgentAdapterWorkdir() {
    if (!agentAdapterWorkdirInput || !agentAdapterBrowseWorkdirButton) {
      return;
    }
    const startPath = agentAdapterWorkdir()
      || String(agentAdapterUseServerWorkdirButton?.dataset.serverWorkdir || "").trim();
    const wasDisabled = agentAdapterBrowseWorkdirButton.disabled;
    agentAdapterBrowseWorkdirButton.disabled = true;
    showStatus(agentAdapterStatusBox, localeText("正在打开目录选择器…", "Opening folder picker…"));
    try {
      const {response, payload} = await fetchJson("/api/system/pick-directory", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({start_path: startPath}),
      });
      if (!response.ok) {
        throw new Error(payload.error || "failed");
      }
      const selected = String(payload?.path || "").trim();
      if (!selected) {
        showStatus(agentAdapterStatusBox, "");
        return;
      }
      setAgentAdapterTargetWorkdir(selected, {
        message: localeText("已选择目标项目目录。", "Target project folder selected."),
      });
    } catch (error) {
      showStatus(
        agentAdapterStatusBox,
        error?.message || localeText("无法打开目录选择器。", "Unable to open the folder picker."),
        "error",
      );
    } finally {
      agentAdapterBrowseWorkdirButton.disabled = wasDisabled;
    }
  }

  function agentAdapterInstallSuccessMessage(label) {
    return localeText(
      `${label} 同一 Agent 项目入口已安装或更新。回到 ${label}，说明 ${SAME_AGENT_HANDOFF_BRIEF_ZH} 后运行 /loopora-plan；预览 READY 并审查后，在同一 Agent 会话运行 /loopora-run。`,
      `${label} same-Agent project entry is installed or updated. Return to ${label} with ${SAME_AGENT_HANDOFF_BRIEF_EN} before /loopora-plan; after the READY preview is reviewed, run /loopora-run in the same Agent session.`,
    );
  }

  function agentAdapterUninstallSuccessMessage(label, payload) {
    const removedCount = agentAdapterRemovedFiles(payload).length;
    const keptCount = agentAdapterKeptFiles(payload).length;
    if (keptCount > 0) {
      return localeText(
        `${label} 同一 Agent 项目入口已卸载，删除了 ${removedCount} 个 Loopora 管理文件；${keptCount} 个文件因为归属不可证明而保留，请先复核。`,
        `${label} same-Agent project entry is uninstalled. ${removedCount} Loopora-managed files were removed; ${keptCount} files were kept because ownership was not provable. Review them before assuming the entry is fully gone.`,
      );
    }
    return localeText(
      `${label} 同一 Agent 项目入口已卸载，删除了 ${removedCount} 个 Loopora 管理文件；如果 Agent 仍显示入口，请刷新或重启 ${label}。`,
      `${label} same-Agent project entry is uninstalled. ${removedCount} Loopora-managed files were removed; if the Agent still shows the entry, refresh or restart ${label}.`,
    );
  }

  function adapterConflictPaths(message) {
    const marker = "adapter files:";
    if (!message || !message.includes(marker)) {
      return [];
    }
    return message.split(marker, 2)[1].split(",").map((part) => part.trim()).filter(Boolean);
  }

  function agentAdapterFailureMessage(adapter, label, action, error) {
    const message = String(error?.message || "");
    const workdirRecovery = agentAdapterWorkdirRecoveryMessage(error?.payload);
    if (workdirRecovery) {
      return workdirRecovery;
    }
    const paths = adapterConflictPaths(message);
    if (action === "install" && paths.length) {
      return localeText(
        `${label} 同一 Agent 项目入口未安装。Loopora 发现这些入口文件不是自己管理的，因此没有覆盖：${paths.join("，")}。请先检查、移动或重命名这些文件，或换一个目标项目目录，然后重新安装。`,
        `${label} same-Agent project entry was not installed. Loopora found entry files it does not own, so it left them unchanged: ${paths.join(", ")}. Inspect, move, or rename those files, or choose another target project, then install again.`,
      );
    }
    return message || localeText("同一 Agent 项目入口操作失败。", "same-Agent project entry action failed.");
  }

  function agentAdapterWorkdirRecoveryMessage(payload) {
    if (payload?.loop_recovery !== "adapter_workdir_unavailable") {
      return "";
    }
    const state = String(payload?.workdir_state?.status || "").trim();
    const summary = String(payload?.summary || payload?.error || "").trim();
    const actions = Array.isArray(payload?.next_actions) ? payload.next_actions : [];
    const firstCommand = String(actions.find((item) => String(item?.command || "").trim())?.command || "").trim();
    if (state === "missing" && firstCommand) {
      return localeText(
        `${summary} 先执行：${firstCommand}`,
        `${summary} First run: ${firstCommand}`,
      );
    }
    if (state === "not_directory") {
      return localeText(
        `${summary} 请改填一个已有项目目录。`,
        `${summary} Enter an existing project directory.`,
      );
    }
    return summary || localeText("目标项目目录不可用。", "Target project directory is not usable.");
  }

  function clearAgentAdapterRecoveryPanel() {
    if (!agentAdapterRecoveryPanel) {
      return;
    }
    agentAdapterRecoveryPanel.hidden = true;
    agentAdapterRecoveryPanel.innerHTML = "";
    agentAdapterRecoveryPanel.setAttribute("data-testid", "agent-adapter-workdir-recovery");
  }

  function agentAdapterRecoveryActionLabel(action, label) {
    const kind = String(action?.kind || "");
    if (kind === "retry_install") {
      return localeText(`重试安装 ${label}`, `Retry installing ${label}`);
    }
    if (kind === "retry_uninstall") {
      return localeText(`重试卸载 ${label}`, `Retry uninstalling ${label}`);
    }
    return window.LooporaUI.recoveryActionLabel(action);
  }

  function agentAdapterRecoveryActionHint(action, label) {
    const kind = String(action?.kind || "");
    if (kind === "retry_install") {
      return localeText(
        `创建或选择可用目录后，再为 ${label} 安装同一 Agent 项目入口。`,
        `After creating or choosing a usable directory, install the same-Agent project entry for ${label} again.`,
      );
    }
    if (kind === "retry_uninstall") {
      return localeText(
        `创建或选择可用目录后，再卸载 ${label} 的同一 Agent 项目入口。`,
        `After creating or choosing a usable directory, uninstall the same-Agent project entry for ${label} again.`,
      );
    }
    return window.LooporaUI.recoveryActionHint(action);
  }

  function agentAdapterRecoveryActionControlHtml(action, payload, label) {
    const kind = String(action?.kind || "").trim();
    const adapter = String(payload?.adapter || "").trim();
    const actionName = kind === "retry_install" ? "install" : kind === "retry_uninstall" ? "uninstall" : "";
    if (!adapter || !actionName) {
      return "";
    }
    return `<button class="ghost-button" type="button" data-agent-adapter-recovery-action="${escapeHtml(actionName)}" data-agent-adapter-recovery-adapter="${escapeHtml(adapter)}">${escapeHtml(agentAdapterRecoveryActionLabel(action, label))}</button>`;
  }

  function bindAgentAdapterRecoveryActionButtons() {
    agentAdapterRecoveryPanel?.querySelectorAll("[data-agent-adapter-recovery-action]").forEach((button) => {
      if (!(button instanceof HTMLButtonElement) || button.dataset.boundAgentAdapterRecoveryAction === "1") {
        return;
      }
      button.dataset.boundAgentAdapterRecoveryAction = "1";
      button.addEventListener("click", () => {
        const adapter = String(button.dataset.agentAdapterRecoveryAdapter || "").trim();
        const action = String(button.dataset.agentAdapterRecoveryAction || "").trim();
        if (!adapter || !action) {
          return;
        }
        if (action === "uninstall") {
          requestAgentAdapterUninstall(adapter, button);
          return;
        }
        mutateAgentAdapter(adapter, action, button);
      });
    });
  }

  function renderAgentAdapterRecovery(payload, {testid = "agent-adapter-workdir-recovery"} = {}) {
    const actions = Array.isArray(payload?.next_actions) ? payload.next_actions : [];
    if (!agentAdapterRecoveryPanel || payload?.loop_recovery !== "adapter_workdir_unavailable" || !actions.length) {
      clearAgentAdapterRecoveryPanel();
      return;
    }
    const label = String(payload?.label || agentAdapterLabel(payload?.adapter || "")).trim() || localeText("Agent", "Agent");
    agentAdapterRecoveryPanel.setAttribute("data-testid", testid);
    agentAdapterRecoveryPanel.innerHTML = window.LooporaUI.recoveryPanelHtml(payload, {
      testid,
      title: localeText("目标项目还不能管理同一 Agent 项目入口", "Target project is not ready for same-Agent project entries"),
      actionLabel: (action) => agentAdapterRecoveryActionLabel(action, label),
      actionHint: (action) => agentAdapterRecoveryActionHint(action, label),
      actionControlHtml: (action) => agentAdapterRecoveryActionControlHtml(action, payload, label),
      emptyControlText: localeText("在上方目标项目输入框中完成。", "Complete this in the target project input above."),
    });
    agentAdapterRecoveryPanel.hidden = false;
    bindAgentAdapterRecoveryActionButtons();
    window.LooporaUI?.bindRecoveryCommandCopy?.();
  }

  function renderAgentAdapterRecoveryFromError(error, options = {}) {
    const payload = error?.payload || {};
    if (payload?.loop_recovery === "adapter_workdir_unavailable" && Array.isArray(payload.next_actions)) {
      renderAgentAdapterRecovery(payload, options);
      return true;
    }
    clearAgentAdapterRecoveryPanel();
    return false;
  }

  function handoffStatusLabel(status) {
    return status === "needs_update"
      ? localeText("需要更新", "Needs update")
      : localeText("已安装", "Installed");
  }

  function handoffTitle(label, status) {
    if (status === "needs_update") {
      return localeText(
        `${label} 入口需要更新`,
        `${label} entry needs an update`,
      );
    }
    return localeText(
      `${label} 入口已接好`,
      `${label} entry is ready`,
    );
  }

  function managedFileStateLabel(state) {
    const labels = {
      current: localeText("当前", "current"),
      needs_update: localeText("需更新", "needs update"),
      missing: localeText("缺失", "missing"),
      unmanaged_conflict: localeText("冲突", "conflict"),
      error: localeText("错误", "error"),
    };
    return labels[state] || state || localeText("未知", "unknown");
  }

  function handoffCandidate(adapters) {
    if (!selectedAgentAdapter) {
      return null;
    }
    const selected = adapters.find((item) => String(item?.adapter || "") === selectedAgentAdapter);
    return agentAdapterCanHandoff(selected) ? selected : null;
  }

  function agentAdapterFirstTaskExample(adapter, payload, item) {
    const fitHandoff = readFitHandoff();
    const targetWorkdir = String(item?.workdir || payload?.workdir || agentAdapterWorkdir() || "").trim();
    const fitDraft = fitHandoffMatchesTarget(fitHandoff, targetWorkdir) && fitHandoffReadyForAgent(fitHandoff)
      ? String(fitHandoff?.draft || "").trim()
      : "";
    if (fitDraft) {
      return {
        text: fitDraft,
        source: "tutorial_fit_review",
        state: fitHandoff.firstTaskState,
      };
    }
    const direct = String(item?.first_task_message_example || payload?.first_task_message_example || "").trim();
    if (direct) {
      const state = normalizeAgentAdapterFirstTaskExampleState(
        item?.first_task_message_example_state || payload?.first_task_message_example_state,
      );
      return {
        text: direct,
        source: "diagnostics",
        state,
      };
    }
    const remembered = String(agentAdapterFirstTaskExamples.get(adapter) || "").trim();
    const rememberedState = agentAdapterFirstTaskExampleStates.get(adapter);
    return remembered
      ? {
        text: remembered,
        source: "diagnostics",
        state: normalizeAgentAdapterFirstTaskExampleState(rememberedState),
      }
      : null;
  }

  function normalizeAgentAdapterFirstTaskHandoffPolicy(policy) {
    if (!policy || typeof policy !== "object") {
      return null;
    }
    const preferredSource = String(policy.preferred_source || "").trim();
    const fallbackSource = String(policy.fallback_source || "").trim();
    const fitCommand = String(policy.fit_command || "").trim();
    const planCommand = String(policy.plan_command || "").trim();
    const copyRule = String(policy.copy_rule || "").trim();
    if (!preferredSource && !fallbackSource && !fitCommand && !planCommand && !copyRule) {
      return null;
    }
    return {
      preferredSource,
      fallbackSource,
      fitCommand,
      planCommand,
      copyRule,
    };
  }

  function rememberAgentAdapterFirstTaskHandoffPolicy(adapter, payload) {
    const policy = normalizeAgentAdapterFirstTaskHandoffPolicy(payload?.first_task_handoff_policy);
    if (adapter && policy) {
      agentAdapterFirstTaskHandoffPolicies.set(adapter, policy);
    }
  }

  function agentAdapterFirstTaskHandoffPolicy(adapter, payload, item) {
    return normalizeAgentAdapterFirstTaskHandoffPolicy(item?.first_task_handoff_policy)
      || normalizeAgentAdapterFirstTaskHandoffPolicy(payload?.first_task_handoff_policy)
      || agentAdapterFirstTaskHandoffPolicies.get(adapter)
      || null;
  }

  function rerenderAgentAdapterHandoff() {
    syncAgentAdapterFitGates(readFitHandoff(), agentAdapterWorkdir());
    if (lastAgentAdapterPayload && lastAgentAdapterItems.length) {
      renderAgentAdapterHandoff(lastAgentAdapterPayload, lastAgentAdapterItems);
    } else {
      clearAgentAdapterHandoff();
    }
    renderFitHandoff();
  }

  function rememberAgentAdapterNextCommands(adapter, payload) {
    const commands = payload?.next_commands;
    if (!adapter || !commands || typeof commands !== "object") {
      return;
    }
    agentAdapterNextCommands.set(adapter, {...commands});
  }

  function agentAdapterNextCommand(adapter, item, kind) {
    const commands = item?.next_commands && typeof item.next_commands === "object"
      ? item.next_commands
      : agentAdapterNextCommands.get(adapter) || {};
    return String(commands[kind] || "").trim();
  }

  function agentAdapterDiagnosticButton({testId, command, labelZh, labelEn}) {
    const value = String(command || "").trim();
    if (!value) {
      return "";
    }
    return `
      <button
        class="agent-readiness-copy-button"
        type="button"
        data-agent-adapter-command-copy="${escapeHtml(value)}"
        data-copy-value="${escapeHtml(value)}"
        data-copy-label="${escapeHtml(localeText(labelZh, labelEn))}"
        data-testid="${escapeHtml(testId)}"
        title="${escapeHtml(value)}"
        aria-label="${escapeHtml(localeText(`${labelZh}：${value}`, `${labelEn}: ${value}`))}"
      >
        <span class="agent-readiness-copy-label">${escapeHtml(localeText(labelZh, labelEn))}</span>
        <code>${escapeHtml(shortCommandLabel(value))}</code>
      </button>
    `;
  }

  function renderAgentAdapterHandoff(payload, adapters) {
    if (!agentAdapterHandoff) {
      return;
    }
    const item = handoffCandidate(adapters);
    if (!item || fitReviewBlocksAgentInstall || fitDirectPathBlocksAgentSetup) {
      agentAdapterHandoffUsesFitDraft = false;
      agentAdapterHandoff.hidden = true;
      agentAdapterHandoff.innerHTML = "";
      return;
    }
    const adapter = String(item.adapter || "");
    const label = String(item.label || agentAdapterLabel(adapter));
    const status = String(item.status || "installed");
    const workdir = String(item.workdir || payload?.workdir || agentAdapterWorkdir() || "").trim();
    const managedFiles = Array.isArray(item.managed_files) ? item.managed_files : [];
    const currentCount = managedFiles.filter((file) => String(file?.state || "") === "current").length;
    const firstTaskExample = agentAdapterFirstTaskExample(adapter, payload, item);
    const firstTaskCanCopy = Boolean(firstTaskExample?.state?.copyAllowed);
    const firstTaskUsesFitReview = firstTaskExample?.source === "tutorial_fit_review" && firstTaskCanCopy;
    agentAdapterHandoffUsesFitDraft = firstTaskUsesFitReview;
    const firstTaskPolicy = agentAdapterFirstTaskHandoffPolicy(adapter, payload, item);
    const fitCommand = String(firstTaskPolicy?.fitCommand || "loopora fit").trim();
    const planCommand = String(firstTaskPolicy?.planCommand || "/loopora-plan").trim();
    const doctorCommand = agentReadinessCurrentTargetCommand()
      || agentAdapterNextCommand(adapter, item, "doctor");
    const checkCommand = agentAdapterNextCommand(adapter, item, "check");
    const diagnosticButtons = `
      ${agentAdapterDiagnosticButton({
        testId: "agent-adapter-copy-readiness",
        command: doctorCommand || checkCommand,
        labelZh: "复制就绪检查",
        labelEn: "Copy readiness check",
      })}
    `;
    const diagnosticsBlock = diagnosticButtons.trim()
      ? `
        <div class="agent-readiness-actions agent-adapter-diagnostic-actions" data-testid="agent-adapter-diagnostic-actions">
          ${diagnosticButtons}
        </div>
      `
      : "";
    const firstTaskExampleText = String(firstTaskExample?.text || "").trim();
    const firstTaskReviewedMessageText = firstTaskCanCopy ? firstTaskExampleText : "";
    const firstTaskOrientationText = firstTaskExampleText && !firstTaskCanCopy ? firstTaskExampleText : "";
    const firstTaskExampleLabel = firstTaskCanCopy && firstTaskExample?.state?.completedReview
      ? localeText("已完成 fit 评审", "Completed fit review")
      : localeText("泛用兜底示例", "Generic fallback example");
    const firstTaskExampleCopyLabel = localeText("已完成 fit 评审消息", "completed fit review message");
    const firstTaskClearButton = firstTaskUsesFitReview
      ? `
          <button class="ghost-button" type="button" data-agent-draft-handoff-clear="1" data-testid="agent-adapter-clear-first-task-example">
            ${escapeHtml(localeText("清除 Fit Guide brief", "Clear Fit Guide brief"))}
          </button>
        `
      : "";
    const firstTaskPreferredSourceNote = firstTaskExampleText && !firstTaskUsesFitReview
      ? `
          <p class="agent-adapter-first-task-source-note" data-testid="agent-adapter-first-task-preferred-source">
            ${escapeHtml(localeText(
              `首选：完成 ${fitCommand} 后，把它生成的 ${planCommand} 交接作为一条消息粘贴；下面只是没有评审草稿时的兜底示例。`,
              `Preferred: after completing ${fitCommand}, paste its generated ${planCommand} handoff as one message; the example below is only the fallback when no reviewed draft is available.`,
            ))}
          </p>
        `
      : "";
    const firstTaskOrientationAside = firstTaskOrientationText
      ? `
        <div class="agent-adapter-first-task-example agent-adapter-first-task-example--orientation" data-testid="agent-adapter-first-task-orientation-example">
          <div class="agent-adapter-first-task-example-head">
            <strong>${escapeHtml(firstTaskExampleLabel)}</strong>
          </div>
          ${firstTaskPreferredSourceNote}
          <code>${escapeHtml(firstTaskOrientationText)}</code>
        </div>
      `
      : "";
    const firstTaskReviewedHeader = firstTaskReviewedMessageText
      ? `
        <div class="agent-adapter-first-task-example" data-testid="agent-adapter-first-task-example">
          <div class="agent-adapter-first-task-example-head">
            <strong>${escapeHtml(firstTaskExampleLabel)}</strong>
            ${firstTaskClearButton}
          </div>
          ${firstTaskPreferredSourceNote}
        </div>
      `
      : "";
    const flowClass = firstTaskReviewedMessageText
      ? "agent-adapter-command-flow agent-adapter-command-flow--with-brief"
      : "agent-adapter-command-flow";
    const reviewStepLabel = firstTaskExampleText
      ? localeText("审查 READY Loop 预览", "Review READY Loop preview")
      : localeText("审查 READY Loop 预览", "Review READY Loop preview");
    const planHandoffText = firstTaskReviewedMessageText || "/loopora-plan";
    const planHandoffTestId = firstTaskReviewedMessageText ? "agent-adapter-copy-first-task-example" : "agent-adapter-copy-gen";
    const planHandoffCopyLabel = firstTaskReviewedMessageText
      ? firstTaskExampleCopyLabel
      : "/loopora-plan";
    const proofRows = managedFiles.length
      ? `
        <span class="agent-adapter-managed-file" data-testid="agent-adapter-managed-file-summary">
          <code>${escapeHtml(`${currentCount}/${managedFiles.length}`)}</code>
          <span>${escapeHtml(managedFileStateLabel(currentCount === managedFiles.length ? "current" : status))}</span>
        </span>
      `
      : "";
    const proofSummary = managedFiles.length
      ? localeText(
        `入口文件：${currentCount}/${managedFiles.length} 个为当前版本`,
        `Entry files: ${currentCount}/${managedFiles.length} current`,
      )
      : localeText("入口文件状态暂不可用", "Entry file status is not available yet");
    agentAdapterHandoff.hidden = false;
    agentAdapterHandoff.innerHTML = `
      <div class="agent-adapter-handoff-head">
        <div>
          <strong data-testid="agent-adapter-handoff-title">${escapeHtml(handoffTitle(label, status))}</strong>
          <span data-testid="agent-adapter-handoff-target">${escapeHtml(localeText("目标项目", "Target project"))}: ${escapeHtml(workdir || "-")}</span>
        </div>
        <span class="${escapeHtml(agentAdapterPillClass(status))}">${escapeHtml(handoffStatusLabel(status))}</span>
      </div>
      <div class="agent-adapter-judgment-brief" data-testid="agent-adapter-judgment-brief">
        <strong>${escapeHtml(localeText("把任务判断交给 /loopora-plan，不只是任务标题。", "Give /loopora-plan the task judgment, not just a task title."))}</strong>
        <ul>
          <li><span>${escapeHtml(localeText("目标", "Goal"))}</span>${escapeHtml(localeText("要证明的用户结果", "User result to prove"))}</li>
          <li><span>${escapeHtml(localeText("伪完成", "Fake done"))}</span>${escapeHtml(localeText("看似完成但必须阻断的状态", "Looks done but must block"))}</li>
          <li><span>${escapeHtml(localeText("证据", "Evidence"))}</span>${escapeHtml(localeText("哪些记录、测试或产物才算够硬", "Records, tests, or artifacts that count"))}</li>
        </ul>
      </div>
      <div class="${escapeHtml(flowClass)}" data-testid="agent-adapter-handoff-flow">
        ${firstTaskReviewedHeader}
        <button
          class="agent-adapter-command-button"
          type="button"
          data-agent-adapter-command-copy="${escapeHtml(planHandoffText)}"
          data-copy-value="${escapeHtml(planHandoffText)}"
          data-copy-label="${escapeHtml(planHandoffCopyLabel)}"
          data-testid="${escapeHtml(planHandoffTestId)}"
          aria-label="${escapeHtml(firstTaskReviewedMessageText ? localeText("复制单条 /loopora-plan 交接消息", "Copy one-message /loopora-plan handoff") : localeText("复制 /loopora-plan", "Copy /loopora-plan"))}"
        >
          <span>1</span>
          <code>${escapeHtml(planHandoffText)}</code>
        </button>
        <span class="agent-adapter-command-then">${escapeHtml(reviewStepLabel)}</span>
        <button
          class="agent-adapter-command-button"
          type="button"
          data-agent-adapter-command-copy="/loopora-run"
          data-copy-value="/loopora-run"
          data-testid="agent-adapter-copy-loop"
          aria-label="${escapeHtml(localeText("复制 /loopora-run", "Copy /loopora-run"))}"
        >
          <span>2</span>
          <code>/loopora-run</code>
        </button>
      </div>
      <p class="agent-adapter-handoff-note" data-testid="agent-adapter-handoff-note">
        ${escapeHtml(localeText(
          "只有预览匹配这些判断后才运行 /loopora-run；不在 Agent 会话中时，Web 对话、Plan File 导入和手动专家路径也会进入同一套证据、缺口和裁决审查。",
          "Run /loopora-run only after the preview matches those judgments; outside an Agent session, Web conversation, Plan File import, and manual expert paths enter the same evidence, gaps, and verdict review.",
        ))}
      </p>
      ${firstTaskOrientationAside}
      ${diagnosticsBlock}
      <div class="agent-readiness-public-report" data-agent-adapter-command-manual-copy data-testid="agent-adapter-command-manual-copy" hidden></div>
      <div class="agent-adapter-install-proof" data-testid="agent-adapter-install-proof">
        <strong>${escapeHtml(proofSummary)}</strong>
        <div class="agent-adapter-managed-files">
          ${proofRows}
        </div>
      </div>
    `;
  }

  function renderAgentAdapterUninstallSummary(payload, label) {
    if (!agentAdapterHandoff) {
      return;
    }
    const adapter = String(payload?.adapter || "").trim();
    const workdir = String(payload?.workdir || agentAdapterWorkdir() || "").trim();
    const removedFiles = agentAdapterRemovedFiles(payload);
    const keptFiles = agentAdapterKeptFiles(payload);
    const reinstallCommand = agentAdapterUninstallReinstallCommand(payload);
    const keptRows = keptFiles.slice(0, 5).map((item) => `
      <span class="agent-adapter-managed-file" data-testid="agent-adapter-kept-file">
        <code>${escapeHtml(item.path || "-")}</code>
        <span>${escapeHtml(item.reason || "kept")}</span>
      </span>
    `).join("");
    const keptOverflow = keptFiles.length > 5
      ? `<span class="agent-adapter-managed-file" data-testid="agent-adapter-kept-file-more"><code>+${keptFiles.length - 5}</code><span>${escapeHtml(localeText("更多", "more"))}</span></span>`
      : "";
    agentAdapterHandoff.hidden = false;
    agentAdapterHandoff.innerHTML = `
      <div class="agent-adapter-handoff-head">
        <div>
          <strong data-testid="agent-adapter-handoff-title">${escapeHtml(localeText(`${label} 同一 Agent 项目入口已卸载`, `${label} same-Agent project entry is uninstalled`))}</strong>
          <span data-testid="agent-adapter-handoff-target">${escapeHtml(localeText("目标项目", "Target project"))}: ${escapeHtml(workdir || "-")}</span>
        </div>
        <span class="wake-lock-pill wake-lock-pill-neutral">${escapeHtml(localeText("未安装", "Not installed"))}</span>
      </div>
      <div class="agent-adapter-uninstall-summary" data-testid="agent-adapter-uninstall-summary">
        <span><strong data-testid="agent-adapter-removed-count">${removedFiles.length}</strong>${escapeHtml(localeText("已删除的 Loopora 管理文件", "Loopora-managed files removed"))}</span>
        <span><strong data-testid="agent-adapter-kept-count">${keptFiles.length}</strong>${escapeHtml(localeText("需要复核的保留文件", "kept files to review"))}</span>
      </div>
      <p class="agent-adapter-handoff-note" data-testid="agent-adapter-uninstall-note">
        ${escapeHtml(localeText(
          keptFiles.length
            ? "Loopora 只删除能证明归属的同一 Agent 项目入口；先复核保留文件，再假设所有入口都已消失。"
            : `Loopora 已移除同一 Agent 项目入口；如果 ${label} 仍显示 /loopora-plan 或 /loopora-run，请刷新或重启 host。`,
          keptFiles.length
            ? "Loopora only removes same-Agent project entries with provable ownership; review kept files before assuming every entry is gone."
            : `Loopora removed the same-Agent project entry; if ${label} still shows /loopora-plan or /loopora-run, refresh or restart the host.`,
        ))}
      </p>
      ${reinstallCommand ? `
        <div class="agent-readiness-actions" data-testid="agent-adapter-uninstall-actions">
          <button
            class="agent-readiness-copy-button"
            type="button"
            data-agent-adapter-command-copy="${escapeHtml(reinstallCommand)}"
            data-copy-value="${escapeHtml(reinstallCommand)}"
            data-testid="agent-adapter-reinstall-command"
          ><code>${escapeHtml(reinstallCommand)}</code></button>
        </div>
      ` : ""}
      <div class="agent-readiness-public-report" data-agent-adapter-command-manual-copy data-testid="agent-adapter-command-manual-copy" hidden></div>
      ${keptFiles.length ? `
        <div class="agent-adapter-install-proof" data-testid="agent-adapter-kept-files">
          <strong>${escapeHtml(localeText("保留文件", "Kept files"))}</strong>
          <div class="agent-adapter-managed-files">
            ${keptRows}
            ${keptOverflow}
          </div>
        </div>
      ` : ""}
    `;
  }

  function renderAgentAdapterUninstallPreview(payload, label) {
    if (!agentAdapterHandoff) {
      return;
    }
    const adapter = String(payload?.adapter || "").trim();
    const workdir = String(payload?.workdir || agentAdapterWorkdir() || "").trim();
    const removedFiles = agentAdapterRemovedFiles(payload);
    const keptFiles = agentAdapterKeptFiles(payload);
    const removedRows = removedFiles.slice(0, 5).map((path) => `
      <span class="agent-adapter-managed-file" data-testid="agent-adapter-preview-remove-file">
        <code>${escapeHtml(path || "-")}</code>
        <span>${escapeHtml(localeText("将删除", "remove"))}</span>
      </span>
    `).join("");
    const keptRows = keptFiles.slice(0, 5).map((item) => `
      <span class="agent-adapter-managed-file" data-testid="agent-adapter-preview-kept-file">
        <code>${escapeHtml(item.path || "-")}</code>
        <span>${escapeHtml(item.reason || "kept")}</span>
      </span>
    `).join("");
    const removedOverflow = removedFiles.length > 5
      ? `<span class="agent-adapter-managed-file" data-testid="agent-adapter-preview-remove-file-more"><code>+${removedFiles.length - 5}</code><span>${escapeHtml(localeText("更多", "more"))}</span></span>`
      : "";
    const keptOverflow = keptFiles.length > 5
      ? `<span class="agent-adapter-managed-file" data-testid="agent-adapter-preview-kept-file-more"><code>+${keptFiles.length - 5}</code><span>${escapeHtml(localeText("更多", "more"))}</span></span>`
      : "";
    agentAdapterHandoff.hidden = false;
    agentAdapterHandoff.innerHTML = `
      <div class="agent-adapter-handoff-head">
        <div>
          <strong data-testid="agent-adapter-handoff-title">${escapeHtml(localeText(`${label} 卸载预览`, `${label} uninstall preview`))}</strong>
          <span data-testid="agent-adapter-handoff-target">${escapeHtml(localeText("目标项目", "Target project"))}: ${escapeHtml(workdir || "-")}</span>
        </div>
        <span class="wake-lock-pill wake-lock-pill-warning">${escapeHtml(localeText("待确认", "Confirm"))}</span>
      </div>
      <div class="agent-adapter-uninstall-summary" data-testid="agent-adapter-uninstall-preview-summary">
        <span><strong data-testid="agent-adapter-preview-removed-count">${removedFiles.length}</strong>${escapeHtml(localeText("将删除的 Loopora 管理文件", "Loopora-managed files to remove"))}</span>
        <span><strong data-testid="agent-adapter-preview-kept-count">${keptFiles.length}</strong>${escapeHtml(localeText("需要复核的保留文件", "kept files to review"))}</span>
      </div>
      <p class="agent-adapter-handoff-note" data-testid="agent-adapter-uninstall-preview-note">
        ${escapeHtml(localeText(
          keptFiles.length
            ? "确认前先复核保留文件；Loopora 只会删除能证明归属的同一 Agent 项目入口。"
            : "确认后才会删除这些同一 Agent 项目入口；如果 Agent 之后仍显示入口，请刷新或重启 host。",
          keptFiles.length
            ? "Review kept files before confirming; Loopora only removes same-Agent project entries with provable ownership."
            : "These same-Agent project entries are removed only after confirmation; if the Agent still shows them later, refresh or restart the host.",
        ))}
      </p>
      <div class="agent-readiness-actions" data-testid="agent-adapter-uninstall-preview-actions">
        <button
          class="ghost-button danger-button"
          type="button"
          data-agent-adapter-confirm-uninstall="${escapeHtml(adapter)}"
          data-testid="agent-adapter-confirm-uninstall"
        >
          ${escapeHtml(localeText("确认卸载", "Confirm uninstall"))}
        </button>
      </div>
      ${removedFiles.length ? `
        <div class="agent-adapter-install-proof" data-testid="agent-adapter-preview-remove-files">
          <strong>${escapeHtml(localeText("将删除", "Will remove"))}</strong>
          <div class="agent-adapter-managed-files">
            ${removedRows}
            ${removedOverflow}
          </div>
        </div>
      ` : ""}
      ${keptFiles.length ? `
        <div class="agent-adapter-install-proof" data-testid="agent-adapter-preview-kept-files">
          <strong>${escapeHtml(localeText("保留文件", "Kept files"))}</strong>
          <div class="agent-adapter-managed-files">
            ${keptRows}
            ${keptOverflow}
          </div>
        </div>
      ` : ""}
    `;
  }

  function agentAdapterUninstallReinstallCommand(payload) {
    return String(payload?.next_commands?.reinstall || "").trim();
  }

  function agentAdapterRemovedFiles(payload) {
    if (!Array.isArray(payload?.removed_files)) {
      return [];
    }
    return payload.removed_files.map((item) => String(item || "").trim()).filter(Boolean);
  }

  function agentAdapterKeptFiles(payload) {
    if (!Array.isArray(payload?.kept_files)) {
      return [];
    }
    return payload.kept_files.map((item) => {
      if (!item || typeof item !== "object") {
        return null;
      }
      const path = String(item.path || "").trim();
      if (!path) {
        return null;
      }
      return {
        path,
        reason: String(item.reason || "kept").trim() || "kept",
      };
    }).filter(Boolean);
  }

  function refreshAgentAdapterTargetFromInput(options = {}) {
    const delayMs = Number(options.delayMs ?? 350);
    const preservePendingContext = options.preservePendingContext === true;
    const workdir = agentAdapterWorkdir();
    const workdirCanSyncContext = !workdir || agentAdapterWorkdirLooksServerAbsolute(workdir);
    if (!workdir) {
      persistAgentAdapterWorkdirPreference("");
      window.LooporaUI.syncWorkdirContext("", {syncUrl: true, urlParam: "workdir"});
    } else if (!workdirCanSyncContext) {
      persistAgentAdapterWorkdirPreference("");
      window.LooporaUI.syncWorkdirContext("", {syncUrl: true, urlParam: "workdir"});
    } else if (!preservePendingContext) {
      persistAgentAdapterWorkdirPreference("");
      window.LooporaUI.syncWorkdirContext(workdir, {syncUrl: true, urlParam: "workdir"});
    }
    setToolsSupportTargetDataset(workdir ? "pending" : "required", Boolean(workdir));
    syncToolsSupportTargetState();
    clearAgentReadinessPublicReportManualCopy();
    preferredAgentAdapterHandoff = "";
    updateAgentAdapterTargetNote({workdir});
    clearAgentAdapterRecoveryPanel();
    clearPendingAgentAdapterUninstall();
    renderAgentReadinessPending(workdir);
    renderAgentAdaptersPending();
    clearAgentAdapterHandoff();
    if (agentAdapterTargetRefreshTimer) {
      window.clearTimeout(agentAdapterTargetRefreshTimer);
      agentAdapterTargetRefreshTimer = 0;
    }
    const refresh = () => {
      agentAdapterTargetRefreshTimer = 0;
      const expectedWorkdir = agentAdapterWorkdir();
      refreshAgentAdapters({expectedWorkdir}).catch(() => {});
      refreshAgentReadiness({expectedWorkdir}).catch(() => {});
    };
    if (delayMs <= 0) {
      refresh();
      return;
    }
    agentAdapterTargetRefreshTimer = window.setTimeout(refresh, delayMs);
  }

  function agentAdapterWorkdirLooksServerAbsolute(value) {
    const path = String(value || "").trim();
    return path.startsWith("/") || /^[A-Za-z]:[\\/]/.test(path) || path.startsWith("\\\\");
  }

  function readAgentAdapterWorkdirPreference() {
    try {
      return window.localStorage.getItem(agentAdapterWorkdirPreferenceKey()) || "";
    } catch (_) {
      return "";
    }
  }

  function readAgentAdapterWorkdirFromUrl() {
    try {
      return new URLSearchParams(window.location.search || "").get("workdir") || "";
    } catch (_) {
      return "";
    }
  }

  function readAgentAdapterWorkdirFromPageContext() {
    return String(agentAdapterWorkdirInput?.dataset.agentAdapterWorkdirContext || "").trim();
  }

  function persistAgentAdapterWorkdirPreference(value) {
    try {
      const normalized = String(value || "").trim();
      const preferenceKey = agentAdapterWorkdirPreferenceKey();
      if (normalized) {
        window.localStorage.setItem(preferenceKey, normalized);
      } else {
        window.localStorage.removeItem(preferenceKey);
      }
      if (preferenceKey !== AGENT_ADAPTER_WORKDIR_PREF_KEY) {
        window.localStorage.removeItem(AGENT_ADAPTER_WORKDIR_PREF_KEY);
      }
    } catch (_) {
      // Ignore storage failures.
    }
  }

  function agentAdapterWorkdirPreferenceKey() {
    const scope = String(agentAdapterWorkdirInput?.dataset.agentAdapterPreferenceScope || "").trim();
    if (!scope) {
      return AGENT_ADAPTER_WORKDIR_PREF_KEY;
    }
    return `${AGENT_ADAPTER_WORKDIR_PREF_KEY}:${scope}`;
  }

  function agentAdapterWorkdir() {
    return String(agentAdapterWorkdirInput?.value || "").trim();
  }

  function agentAdapterTargetRequiredMessage() {
    return localeText(
      "先填写目标项目目录，再安装或移除同一 Agent 项目入口。",
      "Enter the target project directory before installing or removing same-Agent project entries.",
    );
  }

  function agentHostSelectionRequiredMessage(adapter = "") {
    const label = agentAdapterLabel(adapter);
    return localeText(
      `先选择 ${label} 作为当前宿主，再修改它的项目入口。`,
      `Choose ${label} as the current host before changing its project entry.`,
    );
  }

  function agentHostSelectionBlocksMutation(adapter) {
    if (selectedAgentAdapter === adapter) {
      return false;
    }
    showStatus(agentAdapterStatusBox, agentHostSelectionRequiredMessage(adapter), "error");
    const input = agentHostInputs.find((item) => String(item.dataset.agentHost || "") === adapter) || agentHostInputs[0];
    input?.focus?.();
    return true;
  }

  function agentAdapterStatusUrl() {
    const workdir = agentAdapterWorkdir();
    if (!workdir) {
      return "/api/agent-adapters";
    }
    return `/api/agent-adapters?workdir=${encodeURIComponent(workdir)}`;
  }

  function agentAdapterMutationBody() {
    const workdir = agentAdapterWorkdir();
    if (!workdir) {
      throw new Error(agentAdapterTargetRequiredMessage());
    }
    return JSON.stringify({workdir});
  }

  async function refreshAgentAdapters(options = {}) {
    const quiet = options.quiet ?? false;
    const expectedWorkdir = options.expectedWorkdir ?? agentAdapterWorkdir();
    const {response, payload} = await fetchJson(agentAdapterStatusUrl());
    if (!agentAdapterResponseMatchesExpected(payload, expectedWorkdir)) {
      return;
    }
    if (!response.ok) {
      if (!quiet) {
        showStatus(agentAdapterStatusBox, payload.error || localeText("无法读取同一 Agent 项目入口状态。", "Unable to load same-Agent project entry status."), "error");
      }
      return;
    }
    normalizeAgentAdapterTargetFromPayload(payload, expectedWorkdir);
    renderAgentAdapters(payload);
    if (!quiet) {
      showStatus(agentAdapterStatusBox, "");
    }
  }

  async function previewAgentAdapterUninstall(adapter, trigger) {
    if (directHandoffBlocksAgentAdapterMutation()) {
      return;
    }
    const originalDisabled = trigger.disabled;
    trigger.disabled = true;
    const label = agentAdapterLabel(adapter);
    showStatus(
      agentAdapterStatusBox,
      localeText(`正在预览 ${label} 卸载范围…`, `Previewing ${label} uninstall scope…`),
    );
    clearAgentAdapterRecoveryPanel();
    try {
      const {response, payload} = await fetchJson(`/api/agent-adapters/${encodeURIComponent(adapter)}/uninstall-preview`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: agentAdapterMutationBody(),
      });
      if (!response.ok) {
        const previewError = new Error(payload.error || "failed");
        previewError.payload = payload;
        throw previewError;
      }
      markAgentAdapterUninstallPending(adapter, trigger);
      renderAgentAdapterUninstallPreview(payload, label);
      showStatus(
        agentAdapterStatusBox,
        localeText(
          `${label} 卸载范围已预览；确认后才会删除 Loopora 管理的同一 Agent 项目入口。`,
          `${label} uninstall scope is ready; Loopora-managed same-Agent project entries are removed only after confirmation.`,
        ),
        "warning",
      );
    } catch (error) {
      renderAgentAdapterRecoveryFromError(error, {testid: "agent-adapter-uninstall-workdir-recovery"});
      showStatus(
        agentAdapterStatusBox,
        agentAdapterFailureMessage(adapter, label, "uninstall", error),
        "error",
      );
    } finally {
      trigger.disabled = originalDisabled;
      syncAgentAdapterMutationButton(trigger);
    }
  }

  function requestAgentAdapterUninstall(adapter, trigger) {
    if (directHandoffBlocksAgentAdapterMutation()) {
      return;
    }
    if (agentHostSelectionBlocksMutation(adapter)) {
      return;
    }
    if (agentAdapterUninstallIsPending(adapter)) {
      mutateAgentAdapter(adapter, "uninstall", trigger);
      return;
    }
    previewAgentAdapterUninstall(adapter, trigger).catch(() => {});
  }

  async function mutateAgentAdapter(adapter, action, trigger) {
    if (directHandoffBlocksAgentAdapterMutation()) {
      return;
    }
    if (action === "install" && incompleteFitHandoffBlocksAgentAdapterInstall()) {
      return;
    }
    if (agentHostSelectionBlocksMutation(adapter)) {
      return;
    }
    const originalDisabled = trigger.disabled;
    let applied = false;
    trigger.disabled = true;
    const label = agentAdapterLabel(adapter);
    if (action === "install") {
      clearPendingAgentAdapterUninstall();
    }
    showStatus(
      agentAdapterStatusBox,
      action === "install"
        ? localeText(`正在安装 ${label} 同一 Agent 项目入口…`, `Installing ${label} same-Agent project entry…`)
        : localeText(`正在卸载 ${label} 同一 Agent 项目入口…`, `Uninstalling ${label} same-Agent project entry…`),
    );
    clearAgentAdapterRecoveryPanel();
    try {
      const {response, payload} = await fetchJson(`/api/agent-adapters/${encodeURIComponent(adapter)}/${action}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: agentAdapterMutationBody(),
      });
      if (!response.ok) {
        const mutationError = new Error(payload.error || "failed");
        mutationError.payload = payload;
        throw mutationError;
      }
      clearAgentAdapterRecoveryPanel();
      preferredAgentAdapterHandoff = action === "install" ? adapter : "";
      const firstTaskExample = String(payload?.first_task_message_example || "").trim();
      if (action === "install") {
        if (firstTaskExample) {
          agentAdapterFirstTaskExamples.set(adapter, firstTaskExample);
          agentAdapterFirstTaskExampleStates.set(
            adapter,
            normalizeAgentAdapterFirstTaskExampleState(payload?.first_task_message_example_state),
          );
        } else {
          agentAdapterFirstTaskExamples.delete(adapter);
          agentAdapterFirstTaskExampleStates.delete(adapter);
        }
        rememberAgentAdapterFirstTaskHandoffPolicy(adapter, payload);
        rememberAgentAdapterNextCommands(adapter, payload);
      } else {
        agentAdapterFirstTaskExamples.delete(adapter);
        agentAdapterFirstTaskExampleStates.delete(adapter);
      }
      renderAgentAdapters(payload);
      applied = true;
      showStatus(
        agentAdapterStatusBox,
        action === "install"
          ? agentAdapterInstallSuccessMessage(label)
          : agentAdapterUninstallSuccessMessage(label, payload),
        "success",
      );
      await refreshAgentAdapters({quiet: true});
      if (action === "uninstall") {
        clearPendingAgentAdapterUninstall();
        renderAgentAdapterUninstallSummary(payload, label);
      }
      await refreshAgentReadiness({quiet: true});
    } catch (error) {
      renderAgentAdapterRecoveryFromError(error, {testid: `agent-adapter-${action}-workdir-recovery`});
      showStatus(
        agentAdapterStatusBox,
        agentAdapterFailureMessage(adapter, label, action, error),
        "error",
      );
    } finally {
      if (!applied) {
        trigger.disabled = originalDisabled;
        syncAgentAdapterMutationButton(trigger);
      }
    }
  }

  function readWakeLockPreference() {
    try {
      return window.localStorage.getItem(WAKE_LOCK_PREF_KEY) === "1";
    } catch (_) {
      return false;
    }
  }

  function persistWakeLockPreference(enabled) {
    try {
      window.localStorage.setItem(WAKE_LOCK_PREF_KEY, enabled ? "1" : "0");
    } catch (_) {
      // Ignore storage failures.
    }
  }

  function supportsWakeLock() {
    return Boolean(navigator.wakeLock && typeof navigator.wakeLock.request === "function");
  }

  function displayIter(value, fallback = 1) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed < 0) {
      return fallback;
    }
    return Math.floor(parsed) + 1;
  }

  function updateWakeLockRuntimePill() {
    if (!wakeLockRuntimePill) {
      return;
    }
    const runningCount = Number(runtimeActivity.running_count || 0);
    const queuedCount = Number(runtimeActivity.queued_count || 0);
    let className = "wake-lock-pill wake-lock-pill-neutral";
    let text = localeText("当前没有活动运行", "No runs are currently executing");
    if (runningCount > 0) {
      className = "wake-lock-pill wake-lock-pill-running";
      text = localeText(
        `检测到 ${runningCount} 个活动运行${queuedCount ? `，另有 ${queuedCount} 个排队中` : ""}`,
        `${runningCount} running run(s) detected${queuedCount ? `, plus ${queuedCount} queued` : ""}`
      );
    } else if (queuedCount > 0) {
      className = "wake-lock-pill wake-lock-pill-queued";
      text = localeText(`当前有 ${queuedCount} 个运行在排队`, `${queuedCount} queued run(s) detected`);
    }
    updateNodeTextAndClass(wakeLockRuntimePill, text, className);
  }

  function updateWakeLockHoldPill() {
    if (!wakeLockHoldPill || !wakeLockToggle) {
      return;
    }
    if (!supportsWakeLock()) {
      updateNodeTextAndClass(
        wakeLockHoldPill,
        localeText("当前浏览器不支持防休眠锁", "This browser does not support the Wake Lock API"),
        "wake-lock-pill wake-lock-pill-warning",
      );
      return;
    }
    if (!wakeLockToggle.checked) {
      updateNodeTextAndClass(
        wakeLockHoldPill,
        localeText("防休眠开关处于关闭状态", "Wake lock is currently turned off"),
        "wake-lock-pill wake-lock-pill-neutral",
      );
      return;
    }
    if (wakeLockSentinel) {
      updateNodeTextAndClass(
        wakeLockHoldPill,
        localeText("已持有防休眠锁", "Wake lock is currently held"),
        "wake-lock-pill wake-lock-pill-held",
      );
      return;
    }
    if (document.visibilityState !== "visible") {
      updateNodeTextAndClass(
        wakeLockHoldPill,
        localeText("页面不可见，等待重新获取", "Waiting to reacquire once the page is visible again"),
        "wake-lock-pill wake-lock-pill-neutral",
      );
      return;
    }
    if (Number(runtimeActivity.running_count || 0) > 0) {
      updateNodeTextAndClass(
        wakeLockHoldPill,
        localeText("检测到活动运行，正在等待获取防休眠锁", "A run is active; waiting to acquire the wake lock"),
        "wake-lock-pill wake-lock-pill-neutral",
      );
      return;
    }
    updateNodeTextAndClass(
      wakeLockHoldPill,
        localeText("已开启，等有活动运行时再生效", "Enabled and standing by until a run is actively executing"),
      "wake-lock-pill wake-lock-pill-neutral",
    );
  }

  function renderRuntimeRuns() {
    if (!wakeLockRuns) {
      return;
    }
    const runs = Array.isArray(runtimeActivity.runs) ? runtimeActivity.runs : [];
    if (!runs.length) {
      wakeLockRuns.innerHTML = `
        <div class="wake-lock-empty">
          <span data-lang="zh">当前没有活动运行，这个开关会保持待命。</span>
          <span data-lang="en">There are no active runs right now, so the wake lock stays on standby.</span>
        </div>
      `;
      return;
    }
    wakeLockRuns.innerHTML = runs.map((run) => {
      const role = run.active_role ? window.LooporaUI.translateRole(run.active_role) : localeText("等待调度", "Waiting");
      const status = window.LooporaUI.translateStatus(run.status || "queued");
      const iter = localeText(`第 ${displayIter(run.current_iter)} 轮`, `Round ${displayIter(run.current_iter)}`);
      const runHref = window.LooporaUI.workdirContextHref(`/runs/${encodeURIComponent(run.id)}`, run.workdir || "");
      return `
        <a class="wake-lock-run-card" href="${escapeHtml(runHref)}">
          <div class="wake-lock-run-head">
            <strong>${escapeHtml(run.loop_name || run.id)}</strong>
            <span class="wake-lock-run-state wake-lock-run-state-${escapeHtml(run.status || "queued")}">${escapeHtml(status)}</span>
          </div>
          <p class="wake-lock-run-meta">${escapeHtml(role)} · ${escapeHtml(iter)}</p>
          <p class="wake-lock-run-path">${escapeHtml(run.workdir || "")}</p>
        </a>
      `;
    }).join("");
  }

  async function releaseWakeLock() {
    if (!wakeLockSentinel) {
      updateWakeLockHoldPill();
      return;
    }
    const current = wakeLockSentinel;
    wakeLockSentinel = null;
    try {
      await current.release();
    } catch (_) {
      // Ignore release errors; the sentinel is no longer useful either way.
    }
    updateWakeLockHoldPill();
  }

  async function syncWakeLock() {
    updateWakeLockHoldPill();
    if (!wakeLockToggle || !wakeLockToggle.checked) {
      await releaseWakeLock();
      showStatus(wakeLockStatusBox, "");
      return;
    }
    if (!supportsWakeLock()) {
      showStatus(
        wakeLockStatusBox,
        localeText("这个浏览器不支持屏幕防休眠锁，所以这里只能显示运行状态，不能真正阻止休眠。", "This browser does not support the Screen Wake Lock API, so this page can show run activity but cannot actually keep the screen awake."),
        "warning",
      );
      return;
    }
    if (document.visibilityState !== "visible") {
      await releaseWakeLock();
      showStatus(
        wakeLockStatusBox,
        localeText("页面当前不可见；回到此页面后会自动重新尝试。", "The page is not visible right now. It will automatically retry once you come back to this page."),
      );
      return;
    }
    if (Number(runtimeActivity.running_count || 0) <= 0) {
      await releaseWakeLock();
      showStatus(
        wakeLockStatusBox,
        localeText("开关已经打开，但当前没有活动运行，所以不会主动持有防休眠锁。", "The toggle is on, but there is no actively running task right now, so no wake lock is being held."),
      );
      return;
    }
    if (wakeLockSentinel) {
      showStatus(
        wakeLockStatusBox,
        localeText("已检测到活动运行，屏幕会尽量保持唤醒。", "An active run is detected, so the page is currently trying to keep the screen awake."),
        "success",
      );
      updateWakeLockHoldPill();
      return;
    }
    try {
      wakeLockSentinel = await navigator.wakeLock.request("screen");
      wakeLockSentinel.addEventListener("release", () => {
        wakeLockSentinel = null;
        updateWakeLockHoldPill();
        if (wakeLockToggle.checked && document.visibilityState === "visible" && Number(runtimeActivity.running_count || 0) > 0) {
          window.setTimeout(() => {
            syncWakeLock().catch(() => {});
          }, 200);
        }
      });
      showStatus(
        wakeLockStatusBox,
        localeText("已持有防休眠锁；只要这个页面保持可见且仍有活动运行，就会继续阻止自动休眠。", "Wake lock acquired. As long as this page remains visible and a run is still active, the browser will keep trying to prevent automatic sleep."),
        "success",
      );
    } catch (error) {
      showStatus(
        wakeLockStatusBox,
        localeText(
          `没能拿到防休眠锁：${error?.message || "未知错误"}`,
          `Unable to acquire the wake lock: ${error?.message || "unknown error"}`
        ),
        "error",
      );
    }
    updateWakeLockHoldPill();
  }

  async function refreshRuntimeActivity(options = {}) {
    const quiet = options.quiet ?? false;
    const {response, payload} = await fetchJson("/api/runtime/activity");
    if (!response.ok) {
      if (!quiet) {
        showStatus(wakeLockStatusBox, payload.error || localeText("无法读取当前运行状态。", "Unable to load the current run activity."), "error");
      }
      return;
    }
    const nextSignature = JSON.stringify(payload || {});
    const changed = nextSignature !== runtimeActivitySignature;
    runtimeActivity = payload;
    runtimeActivitySignature = nextSignature;
    if (changed) {
      updateWakeLockRuntimePill();
      renderRuntimeRuns();
    }
    if (changed) {
      await syncWakeLock();
    }
  }

  wakeLockToggle.checked = readWakeLockPreference();
  updateWakeLockRuntimePill();
  updateWakeLockHoldPill();
  renderRuntimeRuns();

  localAssetsDetails?.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLButtonElement)) {
      return;
    }
    const revealPath = target.dataset.localAssetsRevealPath || "";
    const copyPath = target.dataset.localAssetsCopyPath || "";
    if (target.dataset.localAssetsRevealPath !== undefined) {
      target.disabled = true;
      revealLocalAssetPath(revealPath, copyPath).finally(() => {
        target.disabled = false;
      });
      return;
    }
    if (target.dataset.localAssetsCopyPath !== undefined) {
      window.LooporaUI?.renderGlobalManualCopy?.("");
      copyText(copyPath)
        .then(() => showStatus(localAssetsStatusBox, localeText("路径已复制到剪贴板。", "Path copied to clipboard."), "success"))
        .catch(() => {
          window.LooporaUI?.renderGlobalManualCopy?.(copyPath, {
            label: localeText("手动复制路径", "Manual path copy"),
            textareaId: "local-asset-path-manual-copy-textarea",
          });
          showStatus(localAssetsStatusBox, localeText("浏览器未允许自动复制；请手动复制页面底部的路径。", "The browser blocked automatic copy; copy the path at the bottom of the page manually."), "warning");
        });
    }
  });

  localAssetsToggle?.addEventListener("click", () => {
    if (!localAssetsIssueTotal || !localAssetsDetails) {
      return;
    }
    localAssetsDetailsExpanded = !localAssetsDetailsExpanded;
    localAssetsDetails.hidden = !localAssetsDetailsExpanded;
    updateLocalAssetsToggle();
  });

  for (const button of agentAdapterInstallButtons) {
    button.addEventListener("click", () => {
      mutateAgentAdapter(String(button.dataset.agentAdapterInstall || ""), "install", button);
    });
  }

  for (const input of agentHostInputs) {
    input.addEventListener("change", () => {
      if (!input.checked) {
        return;
      }
      selectedAgentAdapter = String(input.dataset.agentHost || "");
      preferredAgentAdapterHandoff = selectedAgentAdapter;
      clearPendingAgentAdapterUninstall();
      clearAgentAdapterRecoveryPanel();
      if (lastAgentAdapterPayload) {
        renderAgentAdapters(lastAgentAdapterPayload);
      } else if (lastAgentReadinessPayload) {
        renderAgentReadiness(lastAgentReadinessPayload);
      }
      showStatus(agentAdapterStatusBox, "");
    });
  }

  for (const button of agentAdapterUninstallButtons) {
    button.addEventListener("click", () => {
      requestAgentAdapterUninstall(String(button.dataset.agentAdapterUninstall || ""), button);
    });
  }

  agentAdapterHandoff?.addEventListener("click", async (event) => {
    const confirmUninstallButton = event.target?.closest?.("[data-agent-adapter-confirm-uninstall]");
    if (confirmUninstallButton instanceof HTMLButtonElement) {
      const adapter = String(confirmUninstallButton.dataset.agentAdapterConfirmUninstall || "").trim();
      if (adapter) {
        mutateAgentAdapter(adapter, "uninstall", confirmUninstallButton);
      }
      return;
    }
    const clearButton = event.target?.closest?.("[data-agent-draft-handoff-clear]");
    if (clearButton instanceof HTMLButtonElement) {
      clearFitHandoff();
      agentAdapterHandoffUsesFitDraft = false;
      rerenderAgentAdapterHandoff();
      showStatus(agentAdapterStatusBox, localeText("已清除 Fit Guide brief。", "Fit Guide brief cleared."), "success");
      focusAgentAdapterTargetInput();
      return;
    }
    const button = event.target?.closest?.("[data-agent-adapter-command-copy]");
    if (!(button instanceof HTMLButtonElement)) {
      return;
    }
    const value = String(button.dataset.agentAdapterCommandCopy || button.dataset.copyValue || "").trim();
    const label = String(button.dataset.copyLabel || value).trim();
    if (!value) {
      return;
    }
    renderAgentCommandManualCopy("", button);
    try {
      await copyText(value);
      button.classList.add("is-copied");
      showStatus(
        agentAdapterStatusBox,
        localeText(`已复制 ${label}。`, `${label} copied.`),
        "success",
      );
      window.setTimeout(() => button.classList.remove("is-copied"), 1400);
    } catch (_) {
      renderAgentCommandManualCopy(value, button);
      showStatus(
        agentAdapterStatusBox,
        localeText("浏览器未允许自动复制；请手动复制下面的 Agent 命令。", "The browser blocked automatic copy; copy the Agent command below manually."),
        "warning",
      );
    }
  });

  agentAdapterDraftHandoff?.addEventListener("click", async (event) => {
    const useSourceButton = event.target?.closest?.("[data-agent-draft-handoff-use-source]");
    if (useSourceButton instanceof HTMLButtonElement) {
      const sourceWorkdir = String(useSourceButton.dataset.agentDraftHandoffUseSource || "").trim();
      if (sourceWorkdir) {
        setAgentAdapterTargetWorkdir(sourceWorkdir, {
          message: localeText("已切回 Fit Guide brief 的来源项目。", "Switched back to the Fit Guide brief source project."),
        });
      }
      return;
    }
    const clearButton = event.target?.closest?.("[data-agent-draft-handoff-clear]");
    if (clearButton instanceof HTMLButtonElement) {
      clearFitHandoff();
      rerenderAgentAdapterHandoff();
      syncAgentHostSelection(lastAgentAdapterItems);
      if (lastAgentReadinessPayload) {
        renderAgentReadiness(lastAgentReadinessPayload);
      }
      showStatus(agentAdapterStatusBox, localeText("已清除 Fit Guide 草稿。", "Fit Guide draft cleared."), "success");
      focusAgentAdapterTargetInput();
      return;
    }
    const completionCopyButton = event.target?.closest?.("[data-agent-draft-handoff-copy-completion]");
    if (completionCopyButton instanceof HTMLButtonElement) {
      const value = String(completionCopyButton.dataset.agentDraftHandoffCopyCompletion || "").trim();
      if (!value) {
        return;
      }
      clearDraftHandoffManualCopy();
      try {
        await copyText(value);
        showStatus(agentAdapterStatusBox, localeText("补完命令已复制。", "Completion command copied."), "success");
      } catch (error) {
        const directPathCommand = completionCopyButton.matches('[data-testid="agent-draft-handoff-copy-direct-decision"]');
        renderDraftHandoffManualCopy(
          value,
          directPathCommand
            ? localeText("手动复制直接路径命令", "Manual direct-path command copy")
            : localeText("手动复制补完命令", "Manual completion command copy"),
        );
        showStatus(
          agentAdapterStatusBox,
          error?.message || localeText("浏览器未允许自动复制；请手动复制下面的命令。", "The browser blocked automatic copy; copy the command below manually."),
          "warning",
        );
      }
      return;
    }
    const copyButton = event.target?.closest?.("[data-agent-draft-handoff-copy]");
    if (!(copyButton instanceof HTMLButtonElement)) {
      return;
    }
    const value = String(copyButton.dataset.agentDraftHandoffCopy || "").trim();
    if (!value) {
      return;
    }
    clearDraftHandoffManualCopy();
    try {
      await copyText(value);
      copyButton.classList.add("is-copied");
      showStatus(agentAdapterStatusBox, localeText("已复制 Fit Guide 生成的 Agent brief。", "Fit Guide Agent brief copied."), "success");
      window.setTimeout(() => copyButton.classList.remove("is-copied"), 1400);
    } catch (error) {
      renderDraftHandoffManualCopy(value, localeText("手动复制 Agent brief", "Manual Agent brief copy"));
      showStatus(
        agentAdapterStatusBox,
        error?.message || localeText("浏览器未允许自动复制；请手动复制下面的 Agent brief。", "The browser blocked automatic copy; copy the Agent brief below manually."),
        "warning",
      );
    }
  });

  agentReadinessSummary?.addEventListener("click", async (event) => {
    const button = event.target?.closest?.("[data-agent-readiness-copy], [data-agent-readiness-copy-public]");
    if (!(button instanceof HTMLButtonElement)) {
      return;
    }
    if (button.dataset.agentReadinessCopyPublic === "true") {
      try {
        await copyAgentReadinessPublicReport(button);
      } catch (error) {
        showStatus(
          agentAdapterStatusBox,
          error?.message || localeText("无法复制公开诊断报告。", "Unable to copy the public report."),
          "error",
        );
      }
      return;
    }
    const value = String(button.dataset.agentReadinessCopy || "").trim();
    if (!value) {
      return;
    }
    renderAgentCommandManualCopy("", button);
    try {
      await copyText(value);
      button.classList.add("is-copied");
      showStatus(agentAdapterStatusBox, localeText("已复制命令。", "Command copied."), "success");
      window.setTimeout(() => button.classList.remove("is-copied"), 1400);
    } catch (_) {
      renderAgentCommandManualCopy(value, button);
      showStatus(
        agentAdapterStatusBox,
        localeText("浏览器未允许自动复制；请手动复制下面的命令。", "The browser blocked automatic copy; copy the command below manually."),
        "warning",
      );
    }
  });

  if (agentAdapterWorkdirInput) {
    agentAdapterWorkdirInput.value = readAgentAdapterWorkdirFromUrl().trim()
      || readAgentAdapterWorkdirFromPageContext()
      || readAgentAdapterWorkdirPreference();
    syncToolsSupportTargetState();
    agentAdapterWorkdirInput.addEventListener("input", () => {
      refreshAgentAdapterTargetFromInput();
    });
    agentAdapterWorkdirInput.addEventListener("change", () => {
      refreshAgentAdapterTargetFromInput({delayMs: 0});
    });
    agentAdapterWorkdirInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        refreshAgentAdapterTargetFromInput({delayMs: 0});
      }
    });
  }
  renderFitHandoff();

  agentAdapterBrowseWorkdirButton?.addEventListener("click", () => {
    browseAgentAdapterWorkdir().catch((error) => {
      showStatus(
        agentAdapterStatusBox,
        error?.message || localeText("无法打开目录选择器。", "Unable to open the folder picker."),
        "error",
      );
    });
  });

  agentAdapterUseServerWorkdirButton?.addEventListener("click", () => {
    applyAgentAdapterServerWorkdir();
  });

  wakeLockToggle.addEventListener("change", async () => {
    persistWakeLockPreference(wakeLockToggle.checked);
    await syncWakeLock();
  });

  document.addEventListener("visibilitychange", () => {
    syncWakeLock().catch(() => {});
  });

  window.addEventListener("beforeunload", () => {
    releaseWakeLock().catch(() => {});
  });

  refreshRuntimeActivity({quiet: true});
  refreshAgentReadiness({quiet: true}).catch(() => {});
  refreshAgentAdapters({quiet: true}).catch(() => {});
  refreshLocalAssetDiagnostics({quiet: true}).catch(() => {});
  window.setInterval(() => {
    refreshRuntimeActivity({quiet: true}).catch(() => {});
  }, 15000);

  document.addEventListener("loopora:localechange", () => {
    updateWakeLockRuntimePill();
    updateWakeLockHoldPill();
    renderRuntimeRuns();
    refreshAgentReadiness({quiet: true}).catch(() => {});
    refreshAgentAdapters({quiet: true}).catch(() => {});
    refreshLocalAssetDiagnostics({quiet: true}).catch(() => {});
    syncWakeLock().catch(() => {});
  });
});

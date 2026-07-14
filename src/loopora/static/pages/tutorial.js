document.addEventListener("DOMContentLoaded", () => {
  function canonicalizeFitGuideAlias() {
    if (window.location?.pathname !== "/tutorial" || typeof window.history?.replaceState !== "function") {
      return;
    }
    const nextUrl = `/fit-guide${window.location.search || ""}${window.location.hash || ""}`;
    window.history.replaceState(window.history.state, "", nextUrl);
  }

  canonicalizeFitGuideAlias();

  if (!window.LooporaUI) {
    return;
  }

  const modal = document.getElementById("tutorial-spec-practice-modal");
  const title = document.getElementById("tutorial-spec-practice-title");
  const summary = document.getElementById("tutorial-spec-practice-summary");
  const preview = document.getElementById("tutorial-spec-practice-preview");
  const payload = JSON.parse(document.getElementById("tutorial-spec-practices-json")?.textContent || "{}");

  if (!modal || !title || !summary || !preview || !Object.keys(payload).length) {
    return;
  }

  let activeExampleId = "";
  let lastTrigger = null;
  const FIT_HANDOFF_STORAGE_KEY = "loopora:tutorial-fit-handoff:v1";

  function currentLocale() {
    return window.LooporaUI.currentLocale();
  }

  function localeText(zh, en) {
    return window.LooporaUI.pickText({zh, en});
  }

  function compactText(value) {
    return String(value || "").trim().replace(/\s+/g, " ");
  }

  function localizedFitPlaceholder(field) {
    const english = field?.dataset.fitCommandPlaceholderEn || field?.dataset.fitCommandPlaceholder || "";
    const chinese = field?.dataset.fitCommandPlaceholderZh || english;
    return currentLocale() === "zh" ? chinese || english : english || chinese;
  }

  function localizedDirectDecisionPlaceholder(field) {
    const english = field?.dataset.fitDirectDecisionPlaceholderEn || "";
    const chinese = field?.dataset.fitDirectDecisionPlaceholderZh || english;
    return currentLocale() === "zh" ? chinese || english : english || chinese;
  }

  function localizedInputPlaceholder(field) {
    const english = field?.dataset.fitPlaceholderEn || field?.getAttribute("placeholder") || "";
    const chinese = field?.dataset.fitPlaceholderZh || english;
    return currentLocale() === "zh" ? chinese || english : english || chinese;
  }

  function localizedDirectDecisionInputPlaceholder(field) {
    const english = field?.dataset.fitDirectDecisionInputPlaceholderEn || "";
    const chinese = field?.dataset.fitDirectDecisionInputPlaceholderZh || english;
    return currentLocale() === "zh" ? chinese || english : english || chinese;
  }

  function setFitFieldDecisionContext(fields, preferDirect) {
    fields.forEach((field) => {
      const directDecisionField = preferDirect && field.dataset.fitDraftField === "direct_path_check";
      const directPlaceholder = localizedDirectDecisionInputPlaceholder(field);
      field.placeholder = directDecisionField && directPlaceholder ? directPlaceholder : localizedInputPlaceholder(field);
      field.closest(".tutorial-fit-task-field")?.querySelectorAll("[data-fit-label]").forEach((label) => {
        const defaultLabel = label.dataset.fitLabelDefault || label.textContent || "";
        const directLabel = label.dataset.fitLabelDirectDecision || defaultLabel;
        label.textContent = directDecisionField ? directLabel : defaultLabel;
      });
    });
  }

  function fitPlaceholderForInput(inputId, fields) {
    const field = fields.find((item) => item.dataset.fitDraftField === inputId);
    return localizedFitPlaceholder(field) || `<${inputId}>`;
  }

  function draftForInputs(inputs, fields) {
    const task = inputs.task || fitPlaceholderForInput("task", fields);
    const fitReason = inputs.loopora_fit_reason || fitPlaceholderForInput("loopora_fit_reason", fields);
    const fakeDone = inputs.fake_done_risks || fitPlaceholderForInput("fake_done_risks", fields);
    const evidence = inputs.required_evidence || fitPlaceholderForInput("required_evidence", fields);
    const tradeoffs = inputs.judgment_tradeoffs || fitPlaceholderForInput("judgment_tradeoffs", fields);
    const directPath = inputs.direct_path_check || "";
    if (currentLocale() === "zh") {
      const parts = [
        `/loopora-plan\n\nLoopora 适配：${fitReason}；`,
      ];
      if (directPath) {
        parts.push(`直接路径检查：${directPath}；`);
      }
      parts.push(
        `目标：${task}；`,
        `伪完成风险：${fakeDone}；`,
        `必需证据：${evidence}；`,
        `判断取舍：${tradeoffs}。`,
      );
      return parts.join("");
    }
    const parts = [
      `/loopora-plan\n\nLoopora fit: ${fitReason};`,
    ];
    if (directPath) {
      parts.push(`Direct-path check: ${directPath};`);
    }
    parts.push(
      `Goal: ${task};`,
      `Fake-done risks: ${fakeDone};`,
      `Required evidence: ${evidence};`,
      `Judgment tradeoffs: ${tradeoffs}.`,
    );
    return parts.join(" ");
  }

  function shellQuote(value) {
    const text = String(value || "");
    return "'" + text.replace(/'/g, "'\"'\"'") + "'";
  }

  function fitCliEntry() {
    return compactText(document.querySelector("[data-testid='tutorial-fit-task-review']")?.dataset.fitCliEntry) || "loopora";
  }

  function completionCommandForInputs(inputs, fields, sourceWorkdir = "", preferDirect = false) {
    const parts = [fitCliEntry(), "fit"];
    if (currentLocale() === "zh") {
      parts.push("--language", "zh");
    }
    const workdir = compactText(sourceWorkdir);
    if (workdir) {
      parts.push("--workdir", shellQuote(workdir));
    }
    if (preferDirect) {
      parts.push("--prefer-direct");
    }
    if (preferDirect) {
      fields.forEach((field) => {
        const inputId = field.dataset.fitDraftField || "";
        const option = field.dataset.fitCommandOption || "";
        if (!["task", "direct_path_check"].includes(inputId) || !option) {
          return;
        }
        const suppliedValue = compactText(inputs[inputId]);
        if (inputId === "task" && !suppliedValue) {
          return;
        }
        const placeholder = localizedDirectDecisionPlaceholder(field) || localizedFitPlaceholder(field) || `<${inputId}>`;
        const value = suppliedValue || placeholder;
        parts.push(`--${option}`, shellQuote(value));
      });
      return parts.join(" ");
    }
    fields.forEach((field) => {
      const inputId = field.dataset.fitDraftField || "";
      const option = field.dataset.fitCommandOption || "";
      if (!inputId || !option) {
        return;
      }
      const placeholder = localizedFitPlaceholder(field) || `<${inputId}>`;
      const required = field.dataset.fitRequiredForFirstTask !== "0";
      const suppliedValue = compactText(inputs[inputId]);
      if (preferDirect && !suppliedValue) {
        return;
      }
      if (!required && !suppliedValue) {
        return;
      }
      const value = suppliedValue || placeholder;
      parts.push(`--${option}`, shellQuote(value));
    });
    return parts.join(" ");
  }

  function requiredFitInputIds(fields) {
    return fields
      .filter((field) => field.dataset.fitRequiredForFirstTask !== "0")
      .map((field) => field.dataset.fitDraftField || "")
      .filter(Boolean);
  }

  function missingFitInputIds(inputs, fields) {
    return requiredFitInputIds(fields)
      .filter((inputId) => !compactText(inputs[inputId]));
  }

  function directDecisionInputSupplied(inputs) {
    return Boolean(compactText(inputs.direct_path_check));
  }

  function fitReviewSetupGate(reviewShell, missingInputIds, preferDirect = false, directDecisionHasInput = true) {
    if (preferDirect) {
      if (!directDecisionHasInput) {
        return {
          setup_allowed: false,
          setup_gate: reviewShell?.dataset.fitSetupBlocked || "blocked_until_review_inputs_complete",
          setup_blocker: reviewShell?.dataset.fitSetupDirectInputBlocker || "missing_direct_decision_input",
        };
      }
      return {
        setup_allowed: false,
        setup_gate: reviewShell?.dataset.fitSetupDirect || "direct_path_selected",
        setup_blocker: reviewShell?.dataset.fitSetupDirectBlocker || "prefer_direct_path",
      };
    }
    const ready = missingInputIds.length === 0;
    return {
      setup_allowed: ready,
      setup_gate: ready
        ? reviewShell?.dataset.fitSetupReady || "ready_for_setup"
        : reviewShell?.dataset.fitSetupBlocked || "blocked_until_review_inputs_complete",
      setup_blocker: ready ? "none" : reviewShell?.dataset.fitSetupBlocker || "missing_review_inputs",
    };
  }

  function primaryFirstTaskMessageState(reviewShell, setupGate) {
    if (setupGate.setup_blocker === "missing_direct_decision_input") {
      return {
        source: "not_available_until_review",
        status: reviewShell?.dataset.fitFirstTaskDirectInput || "direct_path_needs_decision_input",
        ready: false,
        copy_allowed: false,
        completed_review: false,
      };
    }
    if (setupGate.setup_blocker === "prefer_direct_path") {
      return {
        source: "direct_path_decision",
        status: reviewShell?.dataset.fitFirstTaskDirect || "direct_path_selected",
        ready: false,
        copy_allowed: false,
        completed_review: false,
      };
    }
    const ready = setupGate.setup_allowed === true;
    return {
      source: "task_review_draft",
      status: ready
        ? reviewShell?.dataset.fitFirstTaskReady || "copyable_after_review_inputs_complete"
        : reviewShell?.dataset.fitFirstTaskPreview || "preview_only_until_review_inputs_complete",
      ready,
      copy_allowed: ready,
      completed_review: ready,
    };
  }

  function fitSetupCommandState(sourceWorkdir, setupGate) {
    if (["prefer_direct_path", "missing_direct_decision_input"].includes(setupGate.setup_blocker)) {
      return {
        target_project_required: false,
        route_commands_are_placeholders: false,
        setup_gate_ready: false,
        setup_gate_blockers: [setupGate.setup_blocker],
        setup_commands_ready: false,
        setup_command_blockers: [setupGate.setup_blocker],
        route_preview_executable: false,
        route_preview_blockers: [setupGate.setup_blocker],
      };
    }
    const targetProjectRequired = !compactText(sourceWorkdir);
    const blockers = [];
    if (setupGate.setup_allowed === false) {
      blockers.push("review_inputs_required");
    }
    if (targetProjectRequired) {
      blockers.push("target_project_required");
    }
    const setupCommandsReady = blockers.length === 0;
    return {
      target_project_required: targetProjectRequired,
      route_commands_are_placeholders: targetProjectRequired,
      setup_gate_ready: setupCommandsReady,
      setup_gate_blockers: setupCommandsReady ? [] : blockers,
      setup_commands_ready: setupCommandsReady,
      setup_command_blockers: blockers,
      route_preview_executable: setupCommandsReady,
      route_preview_blockers: setupCommandsReady ? [] : blockers,
    };
  }

  function writeClipboardText(value) {
    const text = String(value || "");
    return window.LooporaUI.writeTextToClipboard(text);
  }

  function selectManualCopyField(field) {
    if (!(field instanceof HTMLTextAreaElement || field instanceof HTMLInputElement)) {
      return;
    }
    try {
      field.focus({preventScroll: true});
    } catch (_) {
      field.focus();
    }
    field.select();
  }

  function writeFitHandoff(payload) {
    if (!window.sessionStorage) {
      return false;
    }
    try {
      window.sessionStorage.setItem(FIT_HANDOFF_STORAGE_KEY, JSON.stringify(payload));
      return true;
    } catch (_) {
      return false;
    }
  }

  function workdirFromUrl(value) {
    try {
      const url = new URL(value, window.location.href);
      return compactText(url.searchParams.get("workdir") || url.searchParams.get("alignment_workdir") || "");
    } catch (_) {
      return "";
    }
  }

  function fitGuidanceWorkdirContext() {
    const reviewShell = document.querySelector("[data-testid='tutorial-fit-task-review']");
    return compactText(reviewShell?.dataset.currentWorkdir || reviewShell?.dataset.fitWorkdir);
  }

  function fitReviewInputsFromUrlFragment() {
    const marker = "#fit-review=";
    if (!window.location.hash.startsWith(marker)) {
      return {};
    }
    let inputs = {};
    try {
      const parsed = JSON.parse(decodeURIComponent(window.location.hash.slice(marker.length)));
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        inputs = parsed;
      }
    } catch (_) {
      inputs = {};
    } finally {
      window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
    }
    return inputs;
  }

  function hydrateFitReviewFromUrlFragment(fields) {
    const inputs = fitReviewInputsFromUrlFragment();
    let hydrated = false;
    fields.forEach((field) => {
      const inputId = field.dataset.fitDraftField || "";
      const supplied = typeof inputs[inputId] === "string" ? inputs[inputId].trim() : "";
      if (!field.value && supplied) {
        field.value = supplied;
        hydrated = true;
      }
    });
    return hydrated;
  }

  function storedFitHandoffForCurrentTarget() {
    try {
      const raw = window.sessionStorage?.getItem(FIT_HANDOFF_STORAGE_KEY) || "";
      const handoff = raw ? JSON.parse(raw) : null;
      if (handoff?.source !== "tutorial_fit_review") {
        return null;
      }
      const sourceWorkdir = compactText(handoff?.source_workdir || handoff?.workdir);
      const currentWorkdir = fitGuidanceWorkdirContext();
      if (Boolean(sourceWorkdir) !== Boolean(currentWorkdir)) {
        return null;
      }
      if (sourceWorkdir && !window.LooporaUI.sameWorkdir(sourceWorkdir, currentWorkdir)) {
        return null;
      }
      return handoff;
    } catch (_) {
      return null;
    }
  }

  function hydrateFitReviewFromSession(fields, preferDirectInput) {
    const handoff = storedFitHandoffForCurrentTarget();
    const inputs = handoff?.inputs && typeof handoff.inputs === "object" ? handoff.inputs : {};
    if (!Object.values(inputs).some((value) => compactText(value))) {
      return false;
    }
    fields.forEach((field) => {
      const inputId = field.dataset.fitDraftField || "";
      const supplied = compactText(inputs[inputId]);
      if (!field.value && supplied) {
        field.value = supplied;
      }
    });
    if (preferDirectInput instanceof HTMLInputElement) {
      preferDirectInput.checked = window.LooporaUI.tutorialFitPrefersDirectPath(handoff);
    }
    return true;
  }

  function tutorialWorkdirContext(useToolsLink) {
    const toolsWorkdir = useToolsLink instanceof HTMLAnchorElement ? workdirFromUrl(useToolsLink.href) : "";
    const urlWorkdir = workdirFromUrl(window.location.href);
    return toolsWorkdir || urlWorkdir || fitGuidanceWorkdirContext();
  }

  function bindTaskFitReview() {
    const reviewShell = document.querySelector("[data-testid='tutorial-fit-task-review']");
    const fields = Array.from(document.querySelectorAll("[data-fit-draft-field]"))
      .filter((node) => node instanceof HTMLTextAreaElement);
    const taskInput = document.getElementById("tutorial-fit-task-input");
    const draft = document.getElementById("tutorial-fit-task-draft");
    const completionCommand = document.getElementById("tutorial-fit-completion-command");
    const copyButton = document.querySelector("[data-testid='tutorial-fit-task-copy']");
    const commandCopyButton = document.querySelector("[data-testid='tutorial-fit-completion-command-copy']");
    const preferDirectInput = document.querySelector("[data-fit-prefer-direct]");
    const draftPane = document.querySelector(".tutorial-fit-task-pane--draft");
    const reviewQuestions = document.querySelector("[data-testid='tutorial-fit-task-review-questions']");
    [
      [document.querySelector("[data-testid='nav-compose-link']"), "choice"],
      [document.querySelector("[data-testid='nav-tools-link']"), "setup"],
    ].forEach(([link, route]) => {
      if (link instanceof HTMLAnchorElement) {
        link.dataset.tutorialFitRoute = route;
        link.dataset.tutorialFitEmptyAllowed = "true";
      }
    });
    const handoffLinks = Array.from(document.querySelectorAll("[data-tutorial-fit-route]"));
    const status = document.getElementById("tutorial-fit-task-status");
    if (!(taskInput instanceof HTMLTextAreaElement) || !(draft instanceof HTMLTextAreaElement) || !copyButton || !fields.length) {
      return;
    }
    if (!hydrateFitReviewFromUrlFragment(fields)) {
      hydrateFitReviewFromSession(fields, preferDirectInput);
    }

    function setStatus(message, kind = "") {
      if (!status) {
        return;
      }
      status.textContent = message;
      status.classList.toggle("is-success", kind === "success");
      status.classList.toggle("is-warning", kind === "warning");
    }

    function setCompletionCommand(inputs, hasAnyInput, isComplete = false, preferDirect = false) {
      if (!(completionCommand instanceof HTMLTextAreaElement) || !commandCopyButton) {
        return "";
      }
      const text = preferDirect
        ? completionCommandForInputs(inputs, fields, tutorialWorkdirContext(), true)
        : hasAnyInput && !isComplete
          ? completionCommandForInputs(inputs, fields, tutorialWorkdirContext())
          : "";
      completionCommand.value = text;
      commandCopyButton.disabled = !text;
      return text;
    }

    function disabledHandoffLinkMessage() {
      return localeText(
        "已选择直接路径；不用继续 Web 创建或同一 Agent 设置。请复制直接路径命令，或取消直接路径选择后重新判断。",
        "Direct path is selected; do not continue to Fit Guide/Web choices or Same-Agent setup. Copy the direct-path command, or clear the direct-path choice and review again.",
      );
    }

    function setHandoffLinksEnabled(enabled) {
      handoffLinks.forEach((link) => {
        window.LooporaUI.setNavigationControlBlocked(link, !enabled, {
          markerDataset: "fitHandoffDisabled",
          baseHrefDataset: "handoffBaseHref",
          disabledHrefDataset: "disabledHref",
        });
      });
    }

    function collectInputs() {
      return fields.reduce((memo, field) => {
        memo[field.dataset.fitDraftField || ""] = compactText(field.value);
        return memo;
      }, {});
    }

    function renderDraft() {
      const inputs = collectInputs();
      const preferDirect = preferDirectInput instanceof HTMLInputElement && preferDirectInput.checked;
      setFitFieldDecisionContext(fields, preferDirect);
      const hasAnyInput = Object.values(inputs).some(Boolean);
      const hasTask = Boolean(inputs.task);
      const missingInputIds = preferDirect ? [] : missingFitInputIds(inputs, fields);
      const directDecisionHasInput = directDecisionInputSupplied(inputs);
      const isComplete = missingInputIds.length === 0;
      reviewShell?.classList.toggle("has-task", hasTask);
      reviewShell?.classList.toggle("has-review-input", hasAnyInput);
      reviewShell?.classList.toggle("is-direct-decision", preferDirect);
      fields.forEach((field) => {
        const inputId = field.dataset.fitDraftField || "";
        const fieldShell = field.closest(".tutorial-fit-task-field");
        if (fieldShell) {
          fieldShell.hidden = inputId === "task"
            ? false
            : preferDirect
              ? inputId !== "direct_path_check"
              : !hasTask;
        }
      });
      if (draftPane) {
        draftPane.hidden = !hasTask && !preferDirect;
      }
      if (reviewQuestions) {
        reviewQuestions.hidden = !hasTask || preferDirect;
      }
      if (preferDirect) {
        draft.value = "";
        copyButton.disabled = true;
        setHandoffLinksEnabled(false);
        setCompletionCommand(inputs, true, false, true);
        if (!directDecisionHasInput) {
          setStatus(
            localeText(
              "先写直接路径理由，再记录不用 Loopora 的决定。",
              "Add a direct-path reason before recording why Loopora is not needed.",
            ),
            "warning",
          );
          return "";
        }
        setStatus(
          localeText(
            "已选择直接路径；不会生成 /loopora-plan 草稿，也不会继续 Loopora 设置。复制命令可记录这次直接路径判断。",
            "Direct path selected; no /loopora-plan draft or Loopora setup will be generated. Copy the command to record this direct-path decision.",
          ),
          "warning",
        );
        return "";
      }
      setHandoffLinksEnabled(true);
      if (!hasAnyInput) {
        draft.value = "";
        copyButton.disabled = true;
        setCompletionCommand(inputs, false, false, false);
        setStatus(localeText("填写五项必需判断后生成草稿；直接路径检查可选，但有助于说明为什么不用普通 Agent 或硬性检查。", "Fill the five required judgment fields to generate the draft; the direct-path check is optional but helps explain why ordinary Agent work or hard checks are not enough."));
        return "";
      }
      const nextDraft = draftForInputs(inputs, fields);
      draft.value = nextDraft;
      copyButton.disabled = !isComplete;
      setCompletionCommand(inputs, true, isComplete, false);
      if (!hasTask) {
        setStatus(localeText("先补任务目标；缺项时请复制补完命令，不要把占位符草稿发给 Agent。", "Add the task goal first; while inputs are missing, copy the completion command instead of sending a placeholder draft to the Agent."), "warning");
      } else if (!isComplete) {
        setStatus(localeText("判断尚未补齐；可以在 Web 对话中继续澄清。进入同一 Agent 设置前，需先补齐并审查全部必填判断。", "The review is incomplete; continue clarifying it in Web conversation. Complete and review every required judgment before Same-Agent setup."), "warning");
      } else {
        setStatus(localeText("完整草稿已生成；适配性仍由你裁决。", "Complete draft ready; fit remains your call."), "success");
      }
      return nextDraft;
    }

    fields.forEach((field) => {
      field.addEventListener("input", renderDraft);
    });
    preferDirectInput?.addEventListener("change", renderDraft);
    copyButton.addEventListener("click", async () => {
      const text = draft.value.trim() || renderDraft();
      if (!text) {
        taskInput.focus();
        return;
      }
      try {
        await writeClipboardText(text);
        setStatus(localeText("草稿已复制。", "Draft copied."), "success");
        window.LooporaUI.showAppFeedback(localeText("草稿已复制。", "Draft copied."), "success");
      } catch (_) {
        selectManualCopyField(draft);
        setStatus(localeText("无法自动复制；已选中草稿，请手动复制。", "Unable to copy automatically; the draft is selected for manual copy."), "warning");
      }
    });

    function directDecisionHandoffPayload(inputs, sourceWorkdir) {
      const setupGate = fitReviewSetupGate(reviewShell, [], true, directDecisionInputSupplied(inputs));
      const setupCommandState = fitSetupCommandState(sourceWorkdir, setupGate);
      const firstTaskState = primaryFirstTaskMessageState(reviewShell, setupGate);
      const directDecisionCommand = completionCommandForInputs(inputs, fields, sourceWorkdir, true);
      const handoffInputs = Object.fromEntries(Object.entries(inputs).filter(([, value]) => compactText(value)));
      return {
        ...setupGate,
        ...setupCommandState,
        schema_version: 1,
        source: "tutorial_fit_review",
        language: currentLocale(),
        source_workdir: sourceWorkdir,
        inputs: handoffInputs,
        missing_first_task_input_ids: [],
        ready_for_loopora_plan_message: false,
        prefer_direct_path: true,
        fit_decision: "prefer_direct_path",
        next_review_action: "use_direct_agent_or_hard_checks",
        primary_first_task_message: "",
        primary_first_task_message_source: firstTaskState.source,
        primary_first_task_message_status: firstTaskState.status,
        primary_first_task_message_ready: false,
        primary_first_task_message_copy_allowed: false,
        primary_first_task_message_state: firstTaskState,
        review_completion_command: directDecisionCommand,
        direct_decision_command: directDecisionCommand,
        draft_first_task_message: "",
        saved_at: new Date().toISOString(),
      };
    }

    commandCopyButton?.addEventListener("click", async () => {
      renderDraft();
      const text = completionCommand instanceof HTMLTextAreaElement ? completionCommand.value.trim() : "";
      if (!text) {
        taskInput.focus();
        return;
      }
      const inputs = collectInputs();
      const preferDirect = preferDirectInput instanceof HTMLInputElement && preferDirectInput.checked;
      const storedDirectDecision = preferDirect && directDecisionInputSupplied(inputs)
        ? writeFitHandoff(directDecisionHandoffPayload(inputs, tutorialWorkdirContext()))
        : false;
      try {
        await writeClipboardText(text);
        const message = storedDirectDecision
          ? localeText("直接路径命令已复制并记录；不用继续适用性判断/Web 选择或同一 Agent 设置。", "Direct-path command copied and recorded; do not continue to Fit Guide/Web choices or Same-Agent setup.")
          : localeText("补完命令已复制。", "Completion command copied.");
        setStatus(message, "success");
        window.LooporaUI.showAppFeedback(message, "success");
      } catch (_) {
        selectManualCopyField(completionCommand);
        setStatus(localeText("无法自动复制；已选中补完命令，请手动复制。", "Unable to copy automatically; the completion command is selected for manual copy."), "warning");
      }
    });
    function storeFitHandoffForLink(event, link) {
      if (link?.dataset.fitHandoffDisabled === "true") {
        event.preventDefault();
        event.stopImmediatePropagation();
        const message = disabledHandoffLinkMessage();
        setStatus(message, "warning");
        window.LooporaUI.showAppFeedback(message, "warning");
        return;
      }
      const inputs = collectInputs();
      const preferDirect = preferDirectInput instanceof HTMLInputElement && preferDirectInput.checked;
      const routeMode = compactText(link?.dataset.tutorialFitRoute);
      const hasAnyInput = Object.values(inputs).some((value) => compactText(value));
      if (routeMode === "expert") {
        return;
      }
      if (!hasAnyInput && link?.dataset.tutorialFitEmptyAllowed === "true") {
        return;
      }
      const text = preferDirect ? "" : draft.value.trim() || renderDraft();
      const missingInputIds = preferDirect ? [] : missingFitInputIds(inputs, fields);
      const directDecisionHasInput = directDecisionInputSupplied(inputs);
      const setupGate = fitReviewSetupGate(reviewShell, missingInputIds, preferDirect, directDecisionHasInput);
      const requiredInputIds = new Set(requiredFitInputIds(fields));
      const handoffInputs = Object.fromEntries(
        Object.entries(inputs).filter(([inputId, value]) => (preferDirect ? compactText(value) : requiredInputIds.has(inputId) || compactText(value))),
      );
      if (preferDirect && !inputs.direct_path_check) {
        event.preventDefault();
        const directPathInput = fields.find((field) => field.dataset.fitDraftField === "direct_path_check");
        (directPathInput || taskInput).focus();
        setStatus(localeText("先写直接路径判断，再记录不用 Loopora 的决定。", "Add the direct-path decision before recording why Loopora is not needed."), "warning");
        return;
      }
      if (!inputs.task || !text) {
        if (preferDirect) {
          const sourceWorkdir = tutorialWorkdirContext(link);
          const stored = writeFitHandoff(directDecisionHandoffPayload(inputs, sourceWorkdir));
          event.preventDefault();
          setStatus(
            stored
              ? localeText("已记录直接路径判断；不用继续适用性判断/Web 选择或同一 Agent 设置。", "Direct-path decision recorded; do not continue to Fit Guide/Web choices or Same-Agent setup.")
              : localeText("浏览器阻止了会话暂存；请复制直接路径命令。", "The browser blocked session storage; copy the direct-path command instead."),
            stored ? "success" : "warning",
          );
          return;
        }
        event.preventDefault();
        taskInput.focus();
        setStatus(localeText("先补任务目标，再带走这份判断。", "Add the task goal before carrying this judgment forward."), "warning");
        return;
      }
      const sourceWorkdir = tutorialWorkdirContext(link);
      const setupCommandState = fitSetupCommandState(sourceWorkdir, setupGate);
      const firstTaskState = primaryFirstTaskMessageState(reviewShell, setupGate);
      const stored = writeFitHandoff({
        ...setupGate,
        ...setupCommandState,
        schema_version: 1,
        source: "tutorial_fit_review",
        language: currentLocale(),
        source_workdir: sourceWorkdir,
        inputs: handoffInputs,
        missing_first_task_input_ids: missingInputIds,
        ready_for_loopora_plan_message: setupGate.setup_allowed,
        prefer_direct_path: false,
        fit_decision: setupGate.setup_allowed ? "strong_fit_review_complete" : "needs_review_inputs",
        primary_first_task_message: text,
        primary_first_task_message_source: firstTaskState.source,
        primary_first_task_message_status: firstTaskState.status,
        primary_first_task_message_ready: firstTaskState.ready,
        primary_first_task_message_copy_allowed: firstTaskState.copy_allowed,
        primary_first_task_message_state: firstTaskState,
        review_completion_command: missingInputIds.length > 0 ? completionCommandForInputs(inputs, fields, sourceWorkdir) : "",
        draft_first_task_message: text,
        saved_at: new Date().toISOString(),
      });
      if (!stored) {
        event.preventDefault();
        setStatus(localeText("浏览器阻止了会话暂存；请先复制草稿。", "The browser blocked session handoff storage; copy the draft instead."), "warning");
      }
    }

    handoffLinks.forEach((link) => {
      link.addEventListener("click", (event) => storeFitHandoffForLink(event, link));
    });

    document.addEventListener("loopora:localechange", renderDraft);
    document.addEventListener("loopora:workdirchange", renderDraft);
    renderDraft();
  }

  function exampleById(exampleId) {
    return payload[String(exampleId || "").trim()] || null;
  }

  bindTaskFitReview();

  function renderExample(exampleId) {
    const example = exampleById(exampleId);
    if (!example) {
      return false;
    }
    const locale = currentLocale();
    title.textContent = `${example.name || ""} ${localeText("样例", "Example")}`.trim();
    summary.textContent = String(locale === "zh" ? example.summary_zh || "" : example.summary_en || "");
    preview.innerHTML = String(locale === "zh" ? example.rendered_html_zh || "" : example.rendered_html_en || "");
    activeExampleId = exampleId;
    return true;
  }

  function openModal(exampleId, trigger) {
    if (!renderExample(exampleId)) {
      return;
    }
    lastTrigger = trigger || document.activeElement;
    modal.hidden = false;
    modal.setAttribute("aria-hidden", "false");
  }

  function closeModal() {
    if (modal.hidden) {
      return;
    }
    modal.hidden = true;
    modal.setAttribute("aria-hidden", "true");
    activeExampleId = "";
    if (lastTrigger && typeof lastTrigger.focus === "function") {
      lastTrigger.focus();
    }
  }

  document.querySelectorAll("[data-open-tutorial-spec-practice]").forEach((button) => {
    button.addEventListener("click", () => {
      openModal(button.dataset.openTutorialSpecPractice, button);
    });
  });

  modal.querySelectorAll("[data-close-tutorial-spec-practice]").forEach((element) => {
    element.addEventListener("click", closeModal);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) {
      event.preventDefault();
      closeModal();
    }
  });

  document.addEventListener("loopora:localechange", () => {
    if (activeExampleId) {
      renderExample(activeExampleId);
    }
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const FIT_HANDOFF_STORAGE_KEY = "loopora:tutorial-fit-handoff:v1";
  const REQUIRED_INPUT_IDS = ["task", "loopora_fit_reason", "fake_done_risks", "required_evidence", "judgment_tradeoffs"];
  const fitPrompt = document.querySelector("[data-create-choice-fit-prompt]");
  const bridge = document.getElementById("create-choice-tutorial-handoff");
  if (!bridge) {
    return;
  }

  const title = bridge.querySelector("[data-create-choice-handoff-title]");
  const description = bridge.querySelector("[data-create-choice-handoff-description]");
  const summary = bridge.querySelector("[data-testid='loop-create-tutorial-handoff-inputs']");
  const reviewDisclosure = bridge.querySelector("[data-testid='loop-create-tutorial-handoff-review']");
  const reviewCount = bridge.querySelector("[data-testid='loop-create-tutorial-handoff-review-count']");
  const meta = bridge.querySelector("[data-testid='loop-create-tutorial-handoff-meta']");
  const webLink = bridge.querySelector("[data-create-choice-handoff-web]");
  const finishLink = bridge.querySelector("[data-create-choice-handoff-finish]");
  const useSourceLink = bridge.querySelector("[data-create-choice-handoff-use-source]");
  const toolsLink = bridge.querySelector("[data-create-choice-handoff-tools]");
  const directCopyButton = bridge.querySelector("[data-create-choice-handoff-copy-direct]");
  const directManualCopy = bridge.querySelector("[data-create-choice-handoff-direct-manual-copy]");
  const clearButton = bridge.querySelector("[data-create-choice-handoff-clear]");
  const webStartLinks = Array.from(new Set([
    webLink,
    ...document.querySelectorAll("[data-create-choice-web-start]"),
  ].filter(Boolean)));
  const setupStartLinks = Array.from(document.querySelectorAll("[data-create-choice-setup-start]"));
  const expertStartLinks = Array.from(document.querySelectorAll("[data-create-choice-expert-start]"));
  const webStartBaseHrefs = new Map(webStartLinks.map((link) => [link, link.getAttribute("href") || ""]));
  const finishBaseHref = finishLink?.getAttribute("href") || "/tutorial#tutorial-decision-tree-panel";
  const toolsBaseHref = toolsLink?.getAttribute("href") || "/same-agent";
  let currentHandoff = null;

  function activeLinkHref(link) {
    if (!link) {
      return "";
    }
    return link.getAttribute("href")
      || link.dataset.disabledHref
      || link.dataset.enabledHref
      || link.dataset.navigationDisabledHref
      || link.dataset.navigationBaseHref
      || "";
  }

  function rememberWebStartBaseHrefs() {
    webStartLinks.forEach((link) => {
      webStartBaseHrefs.set(link, activeLinkHref(link));
    });
  }

  function localeText(zh, en) {
    return window.LooporaUI?.pickText ? window.LooporaUI.pickText({zh, en}) : en;
  }

  function compactText(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function renderDirectManualCopy(command) {
    window.LooporaUI?.renderManualCopy?.(directManualCopy, compactText(command), {
      label: localeText("手动复制直接路径命令", "Manual direct-path command copy"),
      textareaId: "loop-create-tutorial-handoff-direct-manual-copy-textarea",
    });
  }

  function inputLabel(inputId, prefersDirect = false) {
    const labels = {
      task: localeText("目标", "Goal"),
      loopora_fit_reason: localeText("适配理由", "Fit reason"),
      direct_path_check: prefersDirect ? localeText("直接路径决策", "Direct-path decision") : localeText("直接路径", "Direct path"),
      fake_done_risks: localeText("伪完成", "Fake-done"),
      required_evidence: localeText("证据", "Evidence"),
      judgment_tradeoffs: localeText("取舍", "Tradeoffs"),
    };
    return labels[inputId] || inputId.replaceAll("_", " ");
  }

  function currentWorkdirContext() {
    return compactText(bridge.dataset.currentWorkdir || "");
  }

  function handoffMatchesTarget(handoff) {
    const targetWorkdir = currentWorkdirContext();
    return window.LooporaUI.sameWorkdir(handoff?.sourceWorkdir, targetWorkdir, {
      allowEmptyLeft: !targetWorkdir,
    });
  }

  function sourceWorkdirScopedHref(baseHref, sourceWorkdir, {urlParam = "workdir"} = {}) {
    const workdir = compactText(sourceWorkdir);
    if (!workdir) {
      return baseHref;
    }
    try {
      const url = new URL(baseHref, window.location.origin);
      const targetParam = urlParam === "alignment_workdir" ? "alignment_workdir" : "workdir";
      url.searchParams.set(targetParam, workdir);
      url.searchParams.delete(targetParam === "alignment_workdir" ? "workdir" : "alignment_workdir");
      return `${url.pathname}${url.search}${url.hash}`;
    } catch (_) {
      return baseHref;
    }
  }

  function setWebStartHrefs(sourceWorkdir = "") {
    const workdir = compactText(sourceWorkdir);
    webStartLinks.forEach((link) => {
      const baseHref = webStartBaseHrefs.get(link) || link.getAttribute("href") || "";
      link.href = workdir
        ? sourceWorkdirScopedHref(baseHref, workdir, {urlParam: "alignment_workdir"})
        : baseHref;
    });
  }

  function sourceWorkdirCreateChoiceHref(sourceWorkdir) {
    return sourceWorkdirScopedHref("/loops/new", sourceWorkdir);
  }

  function readTutorialHandoff() {
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
      const prefersDirect = window.LooporaUI.tutorialFitPrefersDirectPath(payload);
      const hasAnyInput = [...REQUIRED_INPUT_IDS, "direct_path_check"].some((inputId) => compactText(inputs[inputId]));
      const directDecisionReady = !prefersDirect || Boolean(compactText(inputs.direct_path_check));
      if (!hasAnyInput || !directDecisionReady) {
        return null;
      }
      const payloadMissingIds = Array.isArray(payload?.missing_first_task_input_ids)
        ? payload.missing_first_task_input_ids.map((inputId) => compactText(inputId)).filter(Boolean)
        : [];
      const derivedMissingIds = REQUIRED_INPUT_IDS.filter((inputId) => !compactText(inputs[inputId]));
      const missingInputIds = Array.from(new Set([...payloadMissingIds, ...derivedMissingIds]));
      const setupAllowed = !prefersDirect && payload?.setup_allowed !== false && payload?.ready_for_loopora_plan_message !== false;
      const sourceWorkdir = compactText(payload?.source_workdir || payload?.workdir || "");
      const setupCommandState = window.LooporaUI.tutorialFitSetupCommandState(payload, {missingInputIds, setupAllowed, sourceWorkdir});
      return {
        prefersDirect,
        inputs,
        missingInputIds: prefersDirect ? [] : missingInputIds,
        readyForWeb: !prefersDirect && missingInputIds.length === 0 && setupAllowed,
        setupGateReady: setupCommandState.setupGateReady,
        setupGateBlockers: setupCommandState.setupGateBlockers,
        setupCommandsReady: setupCommandState.setupCommandsReady,
        setupCommandBlockers: setupCommandState.setupCommandBlockers,
        routePreviewExecutable: setupCommandState.routePreviewExecutable,
        routePreviewBlockers: setupCommandState.routePreviewBlockers,
        reviewCompletionCommand: String(payload?.review_completion_command || payload?.direct_decision_command || "").trim(),
        sourceWorkdir,
      };
    } catch (_) {
      return null;
    }
  }

  function setLinkEnabled(link, enabled) {
    window.LooporaUI.setNavigationControlBlocked(link, !enabled, {
      markerDataset: "createChoiceRouteBlocked",
      baseHrefDataset: "enabledHref",
      disabledHrefDataset: "disabledHref",
    });
  }

  function setWebLinkEnabled(enabled) {
    webStartLinks.forEach((link) => {
      link.classList.toggle("is-disabled", !enabled);
      setLinkEnabled(link, enabled);
    });
  }

  function setSetupLinkEnabled(enabled) {
    setupStartLinks.forEach((link) => {
      setLinkEnabled(link, enabled);
    });
  }

  function setExpertLinkEnabled(enabled) {
    expertStartLinks.forEach((link) => {
      setLinkEnabled(link, enabled);
    });
  }

  function blockedRouteMessage() {
    if (currentHandoff?.directPathBlocksCurrentTarget) {
      return localeText(
        "已选择直接路径。复制直接路径命令，或清除 Fit Guide 决策后再创建 Loop。",
        "Direct path is selected. Copy the direct-path command, or clear the Fit Guide decision before creating a Loop.",
      );
    }
    if (currentHandoff?.hasWorkdirMismatch) {
      return localeText(
        "这份适配性判断属于另一个目标项目。先使用来源项目，或清除草稿后重新判断。",
        "This fit review belongs to another target project. Use the source project first, or clear the draft and review again.",
      );
    }
    return localeText("当前路径暂时不可用。", "This path is temporarily unavailable.");
  }

  function blockRouteStart(event) {
    event.preventDefault();
    event.stopPropagation();
    window.LooporaUI?.showAppFeedback?.(blockedRouteMessage(), "error");
  }

  function focusFirstEnabledCreateChoiceRoute() {
    const routeLinks = document.querySelectorAll("[data-create-choice-web-start], [data-create-choice-setup-start], [data-create-choice-expert-start]");
    const target = Array.from(routeLinks).find((link) => {
      if (link.closest("[hidden]") || link.getAttribute("aria-disabled") === "true") {
        return false;
      }
      return link.hasAttribute("href") && typeof link.focus === "function";
    });
    target?.focus();
  }

  function renderMetaLine(label, value) {
    const text = compactText(value);
    if (!text) {
      return "";
    }
    return `<span><strong>${escapeHtml(label)}</strong>${escapeHtml(text)}</span>`;
  }

  function renderHandoffBridge() {
    const rawHandoff = readTutorialHandoff();
    const hasWorkdirMismatch = Boolean(rawHandoff && !handoffMatchesTarget(rawHandoff));
    const directPathBlocksCurrentTarget = Boolean(rawHandoff?.prefersDirect && !hasWorkdirMismatch);
    const handoff = rawHandoff
      ? {
        ...rawHandoff,
        readyForWeb: rawHandoff.readyForWeb && !hasWorkdirMismatch,
        hasWorkdirMismatch,
        directPathBlocksCurrentTarget,
        webStartBlocked: directPathBlocksCurrentTarget,
      }
      : null;
    currentHandoff = handoff;
    if (!handoff) {
      currentHandoff = null;
      if (fitPrompt) {
        fitPrompt.hidden = false;
      }
      if (reviewDisclosure) {
        reviewDisclosure.open = false;
      }
      renderDirectManualCopy("");
      setWebLinkEnabled(true);
      setSetupLinkEnabled(true);
      setExpertLinkEnabled(true);
      setWebStartHrefs();
      if (finishLink) {
        finishLink.href = finishBaseHref;
      }
      if (toolsLink) {
        toolsLink.href = toolsBaseHref;
        toolsLink.hidden = false;
      }
      if (directCopyButton) {
        directCopyButton.hidden = true;
        delete directCopyButton.dataset.copyValue;
      }
      bridge.hidden = true;
      return;
    }
    bridge.hidden = false;
    if (fitPrompt) {
      fitPrompt.hidden = !hasWorkdirMismatch;
    }
    if (reviewDisclosure && hasWorkdirMismatch) {
      reviewDisclosure.open = true;
    }
    renderDirectManualCopy("");
    bridge.classList.toggle("is-warning", hasWorkdirMismatch);
    finishLink?.classList.remove("is-primary-recovery");
    setSetupLinkEnabled(!handoff.directPathBlocksCurrentTarget);
    setExpertLinkEnabled(!handoff.directPathBlocksCurrentTarget);
    setWebStartHrefs(handoff.sourceWorkdir && !currentWorkdirContext() ? handoff.sourceWorkdir : "");
    if (finishLink) {
      finishLink.href = sourceWorkdirScopedHref(finishBaseHref, handoff.sourceWorkdir);
    }
    if (toolsLink) {
      toolsLink.href = sourceWorkdirScopedHref(toolsBaseHref, handoff.sourceWorkdir);
      toolsLink.hidden = handoff.directPathBlocksCurrentTarget;
    }
    if (directCopyButton) {
      const directCommand = handoff.prefersDirect ? compactText(handoff.reviewCompletionCommand) : "";
      directCopyButton.hidden = !directCommand;
      if (directCommand) {
        directCopyButton.dataset.copyValue = directCommand;
      } else {
        delete directCopyButton.dataset.copyValue;
      }
    }
    if (useSourceLink) {
      useSourceLink.hidden = !hasWorkdirMismatch || !handoff.sourceWorkdir;
      useSourceLink.href = sourceWorkdirCreateChoiceHref(handoff.sourceWorkdir);
      useSourceLink.classList.toggle("is-primary-recovery", rawHandoff.readyForWeb && hasWorkdirMismatch);
    }
    if (title) {
      title.textContent = hasWorkdirMismatch
        ? localeText("适配性判断属于另一个目标项目", "Fit review belongs to another target project")
        : handoff.prefersDirect
        ? localeText("已选择直接路径", "Direct path selected")
        : handoff.readyForWeb
        ? localeText("适配性判断可继续使用", "Fit review is ready to continue")
        : localeText("适配性判断可在对话中补齐", "Fit review can continue in conversation");
    }
    if (description) {
      description.textContent = hasWorkdirMismatch
        ? localeText(
          "这份草稿来自另一个项目，不会自动带入当前目标。你仍可为当前目标开始新对话，或切回来源项目继续这份草稿。",
          "This draft came from another project and will not be applied to the current target. Start a new conversation here, or switch back to its source project.",
        )
        : handoff.prefersDirect
        ? localeText(
        "Fit Guide 已记录直接 Agent、/goal、硬性检查或项目流程足够；不要继续适用性判断/Web 选择或同一 Agent 设置。",
        "Fit Guide recorded that direct Agent work, /goal, hard checks, or the project process is enough; do not continue Fit Guide/Web choices or Same-Agent setup.",
        )
        : handoff.readyForWeb
        ? localeText(
          "选择 Web 对话会预填任务和已有验收判断；当前已经在 Agent 会话中时，也可以进入同一 Agent 设置。",
          "Choose Web conversation to prefill the task and known acceptance judgment; if you are already in an Agent session, you can use Same-Agent Setup.",
        )
        : localeText(
          "选择 Web 对话会带入已有内容，缺失判断由对话逐步追问；也可以先回 Fit Guide 补齐，或在同一 Agent 设置中继续。",
          "Choose Web conversation to carry the known context and clarify missing judgment step by step, or finish in Fit Guide or Same-Agent Setup first.",
        );
    }
    const summaryEntries = [...REQUIRED_INPUT_IDS, "direct_path_check"]
        .map((inputId) => [inputId, compactText(handoff.inputs[inputId])])
        .filter(([, value]) => value);
    if (summary) {
      summary.innerHTML = summaryEntries
        .map(([inputId, value]) => `
          <span>
            <strong>${escapeHtml(inputLabel(inputId, handoff.prefersDirect))}</strong>
            ${escapeHtml(value)}
          </span>
        `)
        .join("");
    }
    if (reviewCount) {
      reviewCount.textContent = localeText(`${summaryEntries.length} 项`, `${summaryEntries.length} item${summaryEntries.length === 1 ? "" : "s"}`);
    }
    if (reviewDisclosure) {
      reviewDisclosure.hidden = summaryEntries.length === 0;
    }
    if (meta) {
      const missing = handoff.missingInputIds.map(inputLabel).join(", ");
      const completionHint = handoff.reviewCompletionCommand
        ? handoff.prefersDirect
          ? localeText("可复制直接路径决策命令", "Direct-path decision command available")
          : localeText("可复制补完命令", "Completion command available")
        : "";
      const setupCommandHint = handoff.setupGateBlockers.includes("prefer_direct_path")
          ? handoff.directPathBlocksCurrentTarget
            ? localeText("直接路径决策阻止 Loopora 设置", "Direct-path decision blocks Loopora setup")
            : localeText("直接路径决策属于来源项目", "Direct-path decision belongs to the source project")
        : handoff.setupGateBlockers.includes("target_project_required")
          ? localeText("先选择目标项目再复制同一 Agent 设置命令", "Choose a target project before copying same-Agent setup commands")
          : "";
      const projectLines = hasWorkdirMismatch
        ? [
          renderMetaLine(localeText("来源目录", "Source project"), handoff.sourceWorkdir),
          renderMetaLine(localeText("当前目标", "Current target"), currentWorkdirContext()),
        ]
        : currentWorkdirContext()
          ? []
          : [renderMetaLine(localeText("目标项目", "Target project"), handoff.sourceWorkdir)];
      meta.innerHTML = [
        renderMetaLine(localeText("缺少", "Missing"), missing),
        ...projectLines,
        renderMetaLine(localeText("设置命令", "Setup commands"), setupCommandHint),
        renderMetaLine(localeText("恢复方式", "Recovery"), completionHint),
      ].join("");
      meta.hidden = !meta.innerHTML;
    }
    setWebLinkEnabled(!handoff.webStartBlocked);
  }

  webStartLinks.forEach((link) => link.addEventListener("click", (event) => {
    if (currentHandoff?.webStartBlocked) {
      blockRouteStart(event);
    }
  }));
  setupStartLinks.forEach((link) => link.addEventListener("click", (event) => {
    if (currentHandoff?.directPathBlocksCurrentTarget) {
      blockRouteStart(event);
    }
  }));
  expertStartLinks.forEach((link) => link.addEventListener("click", (event) => {
    if (currentHandoff?.directPathBlocksCurrentTarget) {
      blockRouteStart(event);
    }
  }));
  clearButton?.addEventListener("click", () => {
    try {
      window.sessionStorage?.removeItem(FIT_HANDOFF_STORAGE_KEY);
    } catch (_) {
      // Best effort only.
    }
    currentHandoff = null;
    setWebLinkEnabled(true);
    setSetupLinkEnabled(true);
    setExpertLinkEnabled(true);
    setWebStartHrefs();
    if (finishLink) {
      finishLink.href = finishBaseHref;
    }
    if (toolsLink) {
      toolsLink.href = toolsBaseHref;
      toolsLink.hidden = false;
    }
    if (directCopyButton) {
      directCopyButton.hidden = true;
      delete directCopyButton.dataset.copyValue;
    }
    renderDirectManualCopy("");
    if (useSourceLink) {
      useSourceLink.hidden = true;
    }
    bridge.hidden = true;
    if (fitPrompt) {
      fitPrompt.hidden = false;
    }
    if (reviewDisclosure) {
      reviewDisclosure.open = false;
    }
    window.LooporaUI?.showAppFeedback?.(localeText("Fit Guide 草稿已清除。", "Fit Guide draft cleared."), "success");
    focusFirstEnabledCreateChoiceRoute();
  });
  directCopyButton?.addEventListener("click", async () => {
    const command = compactText(directCopyButton.dataset.copyValue || "");
    if (!command) {
      return;
    }
    renderDirectManualCopy("");
    try {
      await window.LooporaUI.writeTextToClipboard(command);
      window.LooporaUI?.showAppFeedback?.(localeText("直接路径命令已复制。", "Direct-path command copied."), "success");
    } catch (_) {
      renderDirectManualCopy(command);
      window.LooporaUI?.showAppFeedback?.(
        localeText("浏览器未允许自动复制；请手动复制页面中的直接路径命令。", "The browser blocked automatic copy; copy the direct-path command from the page manually."),
        "warning",
      );
    }
  });
  document.addEventListener("loopora:localechange", renderHandoffBridge);
  document.addEventListener("loopora:workdirchange", () => {
    rememberWebStartBaseHrefs();
    renderHandoffBridge();
  });
  renderHandoffBridge();
});

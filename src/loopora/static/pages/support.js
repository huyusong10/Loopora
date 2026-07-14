(() => {
  const supportPanel = document.querySelector("[data-testid='tools-support-panel']");
  if (!supportPanel) {
    return;
  }
  const statusBox = document.getElementById("tools-support-status");
  const manualCopyContainer = supportPanel.querySelector("[data-support-manual-copy], [data-support-public-report-manual-copy]");
  const supportTargetForm = document.getElementById("support-target-form");
  const supportTargetInput = document.getElementById("support-target-workdir");
  const supportTargetStatus = document.getElementById("support-target-status");
  const supportTargetBrowseButton = document.querySelector("[data-support-browse-workdir]");
  const supportTargetRecentButtons = Array.from(document.querySelectorAll("[data-support-recent-workdir]"));
  const supportHeroContext = document.querySelector("[data-testid='support-hero-target-context']");
  const supportHeroTargetSummary = supportHeroContext?.querySelector("[data-support-target-summary]");
  const supportHeroTargetDescription = supportHeroContext?.querySelector("[data-support-target-description]");
  const supportHeroReportLink = document.querySelector("[data-testid='support-public-report-link']");
  const supportReportButtons = Array.from(document.querySelectorAll("[data-support-copy-public-report]"))
    .filter((button) => button !== supportHeroReportLink);
  const SUPPORT_PUBLIC_ISSUE_BUNDLE_ACTION_KIND = "run_public_issue_bundle";
  const SUPPORT_PUBLIC_DOCTOR_ACTION_KIND = "run_public_doctor_report";

  function localeText(zh, en) {
    return window.LooporaUI?.pickText?.({zh, en}) || zh || en || "";
  }

  function panelContext() {
    return String(supportPanel.dataset.supportPanelContext || "support");
  }

  function setStatus(message, kind = "") {
    if (!statusBox) {
      return;
    }
    const text = String(message || "");
    statusBox.textContent = text;
    statusBox.hidden = !text;
    statusBox.classList.remove("is-error", "is-success", "is-warning");
    if (kind) {
      statusBox.classList.add(`is-${kind}`);
    }
  }

  function renderManualCopy(copyText, options = {}) {
    window.LooporaUI?.renderManualCopy?.(manualCopyContainer, copyText, {
      label: options.label || localeText("手动复制公开 issue 支持包", "Manual public issue bundle copy"),
      textareaId: options.textareaId || "tools-support-public-report-textarea",
      rows: 10,
    });
  }

  function renderManualCommandCopy(command) {
    renderManualCopy(command, {
      label: localeText("手动复制本地命令", "Manual local command copy"),
      textareaId: "tools-support-command-manual-copy-textarea",
    });
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
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
    const value = String(workdir || "").trim();
    if (!value) {
      return "";
    }
    const params = new URLSearchParams();
    params.set("workdir", value);
    params.set("language", String(document.documentElement?.dataset?.locale || "en"));
    return `/api/diagnostics/public-issue-bundle?${params.toString()}`;
  }

  function setSupportControlDisabled(control, disabled) {
    if (!(control instanceof HTMLElement)) {
      return;
    }
    if (control instanceof HTMLButtonElement) {
      control.disabled = Boolean(disabled);
    }
    if (disabled) {
      control.setAttribute("aria-disabled", "true");
    } else {
      control.removeAttribute("aria-disabled");
    }
  }

  function setSupportControlText(control, labelZh, labelEn) {
    if (!(control instanceof HTMLElement)) {
      return;
    }
    control.innerHTML = `
      <span data-lang="zh">${escapeHtml(labelZh)}</span>
      <span data-lang="en">${escapeHtml(labelEn)}</span>
    `;
  }

  async function copyText(text) {
    if (typeof window.LooporaUI?.writeTextToClipboard === "function") {
      return window.LooporaUI.writeTextToClipboard(text);
    }
    throw new Error(localeText("无法复制，请手动复制。", "Unable to copy; copy manually."));
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {Accept: "application/json", ...(options.headers || {})},
    });
    let payload = {};
    try {
      payload = await response.json();
    } catch (_) {
      payload = {};
    }
    return {response, payload};
  }

  async function fetchPublicIssueBundleText(url) {
    const response = await fetch(url, {
      headers: {Accept: "text/plain, application/json"},
    });
    const contentType = String(response.headers.get("content-type") || "");
    const body = await response.text();
    if (!response.ok) {
      let payload = {};
      try {
        payload = body ? JSON.parse(body) : {};
      } catch (_) {
        payload = {};
      }
      throw new Error(payload.error || body || localeText("无法读取公开 issue 支持包。", "Unable to load the public issue support bundle."));
    }
    if (contentType.includes("application/json")) {
      const payload = body ? JSON.parse(body) : {};
      const text = String(payload.public_issue_bundle_text || payload.public_issue_bundle || "").trim();
      if (text) {
        return text;
      }
      throw new Error(payload.error || localeText("公开 issue 支持包响应缺少可复制文本。", "The public issue bundle response did not include copyable text."));
    }
    return body;
  }

  function supportTargetWorkdir() {
    return String(supportTargetInput?.value || "").trim();
  }

  function setStandaloneSupportHeroState(workdir) {
    if (panelContext() !== "support" || !supportHeroContext) {
      return;
    }
    const hasTarget = Boolean(String(workdir || "").trim());
    supportHeroContext.dataset.supportTargetProjectStatus = hasTarget ? "pending" : "required";
    supportHeroContext.dataset.supportTargetProjectReportOnly = hasTarget ? "true" : "false";
    supportHeroContext.dataset.supportTargetProjectRequired = hasTarget ? "false" : "true";
    if (supportHeroTargetSummary) {
      setSupportControlText(
        supportHeroTargetSummary,
        hasTarget ? "已选择，待刷新" : "尚未选择",
        hasTarget ? "selected, pending refresh" : "not selected",
      );
    }
    if (supportHeroTargetDescription) {
      setSupportControlText(
        supportHeroTargetDescription,
        hasTarget
          ? "目标项目来自当前 Web 上下文；可以复制公开 issue 支持包，也可以点击“使用目标”刷新设置就绪状态。"
          : "公开报告需要目标项目上下文。请在这里填写目标项目路径，或从带 workdir 的 Web 链接打开本页。",
        hasTarget
          ? "The target project comes from the current Web context; copy the public issue support bundle, or click Use Target to refresh setup readiness."
          : "A public report needs target-project context. Set the target project path here, or open this page from a Web link with workdir.",
      );
    }
  }

  function setStandaloneSupportActionGroups(hasTarget) {
    const targetRequiredNote = supportPanel.querySelector("[data-support-target-required-note]");
    if (targetRequiredNote instanceof HTMLElement) {
      targetRequiredNote.hidden = hasTarget;
    }
    const targetStateNote = supportPanel.querySelector("[data-support-target-state-note]");
    if (targetStateNote instanceof HTMLElement) {
      targetStateNote.hidden = !hasTarget;
      if (hasTarget) {
        targetStateNote.textContent = localeText(
          "目标项目来自当前 Web 上下文；公开报告可复制，设置就绪状态可通过“使用目标”刷新。",
          "Target project comes from the current Web context; public reporting is copyable, and setup readiness can be refreshed with Use Target.",
        );
      }
    }
  }

  function syncStandaloneSupportCommandButton(actionKind, workdir, hasTarget, labels) {
    const commandButton = supportPanel.querySelector(`[data-support-command-copy][data-support-next-action-kind="${actionKind}"]`);
    if (!(commandButton instanceof HTMLButtonElement)) {
      return;
    }
    const template = supportPublicDoctorCommandTemplate(commandButton);
    commandButton.dataset.supportCommandCopy = hasTarget
      ? supportPublicDoctorCommandWithWorkdir(template, workdir)
      : template;
    commandButton.dataset.supportCommandRequiresTarget = hasTarget ? "false" : "true";
    commandButton.dataset.supportCommandReady = hasTarget ? "true" : "false";
    setSupportControlDisabled(commandButton, !hasTarget);
    setSupportControlText(commandButton, hasTarget ? labels.readyZh : labels.noTargetZh, hasTarget ? labels.readyEn : labels.noTargetEn);
  }

  function syncStandaloneSupportTargetState(workdir, {showFeedback = false} = {}) {
    if (panelContext() !== "support") {
      return;
    }
    const value = String(workdir || "").trim();
    const hasTarget = Boolean(value);
    if (supportTargetInput && supportTargetInput.value !== value) {
      supportTargetInput.value = value;
    }
    supportPanel.dataset.supportTargetProjectStatus = hasTarget ? "pending" : "required";
    supportPanel.dataset.supportTargetProjectSetupReady = "false";
    supportPanel.dataset.supportTargetProjectReportOnly = hasTarget ? "true" : "false";
    supportPanel.dataset.supportPublicReportUrl = hasTarget ? supportPublicReportUrlWithWorkdir(value) : "";
    setStandaloneSupportHeroState(value);
    setStandaloneSupportActionGroups(hasTarget);
    for (const control of [supportHeroReportLink, ...supportReportButtons]) {
      if (!(control instanceof HTMLElement)) {
        continue;
      }
      if (hasTarget) {
        control.dataset.supportCopyPublicReport = "true";
      } else {
        delete control.dataset.supportCopyPublicReport;
      }
      setSupportControlDisabled(control, !hasTarget && control instanceof HTMLButtonElement);
      setSupportControlText(
        control,
        hasTarget ? "复制公开 issue 支持包" : "先选择目标项目",
        hasTarget ? "Copy Public Issue Bundle" : "Choose Target First",
      );
    }
    syncStandaloneSupportCommandButton(SUPPORT_PUBLIC_ISSUE_BUNDLE_ACTION_KIND, value, hasTarget, {
      noTargetZh: "选择目标后复制优先支持包命令",
      noTargetEn: "Choose target before copying preferred bundle command",
      readyZh: "复制优先支持包命令",
      readyEn: "Copy preferred bundle command",
    });
    syncStandaloneSupportCommandButton(SUPPORT_PUBLIC_DOCTOR_ACTION_KIND, value, hasTarget, {
      noTargetZh: "选择目标后复制兜底报告命令",
      noTargetEn: "Choose target before copying fallback report command",
      readyZh: "复制兜底报告命令",
      readyEn: "Copy fallback report command",
    });
    renderManualCopy("");
    if (showFeedback) {
      setSupportTargetStatus(
        hasTarget
          ? localeText(
            "已同步当前 Web 目标项目；可以复制公开 issue 支持包，或点击“使用目标”刷新设置状态。",
            "Current Web target synced; copy the public issue support bundle, or click Use Target to refresh setup status.",
          )
          : localeText("已清除目标项目上下文。", "Target project context cleared."),
        hasTarget ? "success" : "warning",
      );
    }
  }

  function setSupportTargetStatus(message, kind = "") {
    if (!supportTargetStatus) {
      return;
    }
    const text = String(message || "");
    supportTargetStatus.textContent = text;
    supportTargetStatus.hidden = !text;
    supportTargetStatus.classList.remove("is-error", "is-success", "is-warning");
    if (kind) {
      supportTargetStatus.classList.add(`is-${kind}`);
    }
  }

  function submitSupportTargetWorkdir(workdir) {
    const value = String(workdir || "").trim();
    if (!supportTargetForm || !supportTargetInput) {
      return;
    }
    supportTargetInput.value = value;
    if (typeof supportTargetForm.requestSubmit === "function") {
      supportTargetForm.requestSubmit();
      return;
    }
    if (typeof supportTargetForm.submit === "function") {
      supportTargetForm.submit();
      return;
    }
    const url = new URL(supportTargetForm.getAttribute("action") || "/support", window.location.href);
    if (value) {
      url.searchParams.set("workdir", value);
    } else {
      url.searchParams.delete("workdir");
      url.searchParams.set("support_target_feedback", "target_required");
      url.hash = "support-target-form";
    }
    window.location.assign(`${url.pathname}${url.search}${url.hash}`);
  }

  async function browseSupportTargetWorkdir() {
    if (!supportTargetInput || !supportTargetBrowseButton) {
      return;
    }
    const wasDisabled = supportTargetBrowseButton.disabled;
    supportTargetBrowseButton.disabled = true;
    setSupportTargetStatus(localeText("正在打开目录选择器…", "Opening folder picker…"));
    try {
      const {response, payload} = await fetchJson("/api/system/pick-directory", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({start_path: supportTargetWorkdir()}),
      });
      if (!response.ok) {
        throw new Error(payload.error || "failed");
      }
      const selected = String(payload?.path || "").trim();
      if (!selected) {
        setSupportTargetStatus("");
        return;
      }
      setSupportTargetStatus(localeText("已选择目标项目目录。", "Target project folder selected."), "success");
      submitSupportTargetWorkdir(selected);
    } catch (error) {
      setSupportTargetStatus(
        error?.message || localeText("无法打开目录选择器。", "Unable to open the folder picker."),
        "error",
      );
    } finally {
      supportTargetBrowseButton.disabled = wasDisabled;
    }
  }

  async function copyPublicReport(button) {
    renderManualCopy("");
    const url = String(supportPanel.dataset.supportPublicReportUrl || "").trim();
    if (!url) {
      throw new Error(panelContext() === "tools"
        ? localeText("先选择并刷新目标项目，再复制公开 issue 支持包。", "Choose and refresh a target project before copying a public issue support bundle.")
        : localeText("先带目标项目打开本页，再复制公开 issue 支持包。", "Open this page with a target project before copying a public issue support bundle."));
    }
    const reportText = await fetchPublicIssueBundleText(url);
    try {
      await copyText(reportText);
      button.classList.add("is-copied");
      setStatus(localeText("已复制公开 issue 支持包。", "Public issue support bundle copied."), "success");
      window.setTimeout(() => button.classList.remove("is-copied"), 1400);
    } catch (_) {
      renderManualCopy(reportText);
      setStatus(
        localeText("浏览器未允许自动复制；请手动复制下面的公开 issue 支持包。", "The browser blocked automatic copy; copy the public issue support bundle below manually."),
        "warning",
      );
    }
  }

  async function handlePublicReportButton(button) {
    const wasDisabled = button instanceof HTMLButtonElement ? button.disabled : button?.getAttribute?.("aria-disabled") === "true";
    setSupportControlDisabled(button, true);
    if (supportPanel instanceof HTMLDetailsElement) {
      supportPanel.open = true;
    }
    try {
      await copyPublicReport(button);
    } catch (error) {
      setStatus(error?.message || localeText("无法复制公开 issue 支持包。", "Unable to copy the public issue support bundle."), "error");
    } finally {
      setSupportControlDisabled(button, wasDisabled);
    }
  }

  supportTargetForm?.addEventListener("submit", (event) => {
    const workdir = supportTargetWorkdir();
    if (supportTargetInput) {
      supportTargetInput.value = workdir;
    }
    if (!workdir) {
      setSupportTargetStatus(localeText("正在清除目标项目上下文…", "Clearing target project context…"));
    }
  });

  supportTargetBrowseButton?.addEventListener("click", () => {
    browseSupportTargetWorkdir().catch((error) => {
      setSupportTargetStatus(
        error?.message || localeText("无法打开目录选择器。", "Unable to open the folder picker."),
        "error",
      );
    });
  });

  for (const button of supportTargetRecentButtons) {
    button.addEventListener("click", () => {
      submitSupportTargetWorkdir(button.dataset.supportRecentWorkdir || "");
    });
  }

  for (const button of supportReportButtons) {
    button.addEventListener("click", () => {
      handlePublicReportButton(button);
    });
  }

  supportHeroReportLink?.addEventListener("click", (event) => {
    if (supportHeroReportLink.dataset.supportCopyPublicReport !== "true" && !supportHeroReportLink.hasAttribute("data-support-copy-public-report")) {
      return;
    }
    event.preventDefault();
    handlePublicReportButton(supportHeroReportLink);
  });

  document.addEventListener("loopora:workdirchange", (event) => {
    syncStandaloneSupportTargetState(event?.detail?.workdir || "", {showFeedback: true});
  });

  supportPanel.addEventListener("click", async (event) => {
    const button = event.target?.closest?.("[data-support-command-copy]");
    if (!(button instanceof HTMLButtonElement)) {
      return;
    }
    const value = String(button.dataset.supportCommandCopy || "").trim();
    if (!value) {
      return;
    }
    renderManualCopy("");
    if (button.dataset.supportCommandRequiresTarget === "true" && value.includes("<project-dir>")) {
      setStatus(
        panelContext() === "tools"
          ? localeText(
            "先选择并刷新目标项目，再复制优先支持包或兜底报告命令；或手动替换 <project-dir>。",
            "Choose and refresh a target project before copying preferred bundle or fallback report commands, or replace <project-dir> manually.",
          )
          : localeText(
            "先带目标项目打开本页，再复制优先支持包或兜底报告命令；或手动替换 <project-dir>。",
            "Open this page with a target project before copying preferred bundle or fallback report commands, or replace <project-dir> manually.",
          ),
        "error",
      );
      return;
    }
    try {
      await copyText(value);
      button.classList.add("is-copied");
      setStatus(localeText("本地命令已复制。公开 issue 优先粘贴支持包输出。", "Local command copied. Prefer the support bundle output in public issues."), "success");
      window.setTimeout(() => button.classList.remove("is-copied"), 1400);
    } catch (_) {
      renderManualCommandCopy(value);
      setStatus(localeText("浏览器未允许自动复制；请手动复制下面的本地命令。", "The browser blocked automatic copy; copy the local command below manually."), "warning");
    }
  });
})();

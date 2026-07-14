(function () {
  const ACTIVE_STATUSES = new Set(["running", "validating", "repairing"]);

  function defaultLocaleText(_zh, en) {
    return en;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function createAlignmentHistory({
    historyList,
    localeText = defaultLocaleText,
    fetchSessions,
    openSession,
    openHref,
    emptyStartHref,
    emptyStartAction,
    deleteSession,
    currentSessionId,
  } = {}) {
    let lastSessions = [];
    let pendingDeleteId = "";
    let loadError = "";

    function statusLabel(status, stage = "") {
      if (status === "waiting_user" && stage) {
        const stageLabels = {
          clarifying: localeText("判断不足，需要补充", "Judgment incomplete"),
          agreement_ready: localeText("等待确认协议", "Waiting for agreement"),
          confirmed: localeText("已确认协议", "Agreement confirmed"),
          compiling: localeText("正在编译方案", "Compiling plan"),
          ready_review: localeText("等待复核", "Waiting for review"),
        };
        if (stageLabels[stage]) {
          return stageLabels[stage];
        }
      }
      const labels = {
        idle: localeText("未开始", "Idle"),
        running: localeText("编排中", "Composing"),
        waiting_user: localeText("等待回复", "Waiting"),
        validating: localeText("校验中", "Validating"),
        repairing: localeText("自动修复", "Repairing"),
        ready: localeText("方案已准备好", "Plan ready"),
        failed: localeText("失败", "Failed"),
        interrupted: localeText("已中断", "Interrupted"),
        cancelled: localeText("已停止", "Stopped"),
        stopped: localeText("已停止", "Stopped"),
        imported: localeText("已导入", "Imported"),
        running_loop: localeText("运行中", "Running loop"),
      };
      return labels[status] || status || "-";
    }

    function currentId() {
      return typeof currentSessionId === "function" ? currentSessionId() : currentSessionId || "";
    }

    function render(sessions = lastSessions) {
      if (!historyList) {
        return;
      }
      lastSessions = Array.isArray(sessions) ? sessions : [];
      historyList.innerHTML = "";
      if (loadError) {
        const failed = historyStateElement({
          testid: "alignment-history-load-error",
          className: "is-error",
          message: localeText("最近对话加载失败。", "Recent chats could not be loaded."),
          retry: true,
        });
        historyList.append(failed);
        if (!lastSessions.length) {
          return;
        }
      }
      if (!lastSessions.length) {
        historyList.append(historyStateElement({
          testid: "alignment-history-empty",
          message: localeText("还没有历史对话。", "No recent chats yet."),
        }));
        return;
      }
      lastSessions.forEach((session) => {
        const item = document.createElement("article");
        const sessionId = String(session.id || "");
        const sessionStatus = String(session.status || "");
        const running = ACTIVE_STATUSES.has(sessionStatus);
        const pendingDelete = Boolean(sessionId) && pendingDeleteId === sessionId;
        item.className = "alignment-history-item";
        item.dataset.testid = "alignment-history-item";
        item.dataset.sessionId = sessionId;
        item.dataset.sessionStatus = sessionStatus;
        item.classList.toggle("is-delete-pending", pendingDelete);
        item.classList.toggle("is-active", currentId() === sessionId);
        item.classList.toggle("is-running", running);

        const href = typeof openHref === "function" ? openHref(session) : "";
        const openTag = typeof openSession === "function"
          ? '<button class="alignment-history-open" type="button" data-testid="alignment-history-open">'
          : `<a class="alignment-history-open" href="${escapeHtml(href)}" data-testid="alignment-history-open">`;
        const closeTag = typeof openSession === "function" ? "</button>" : "</a>";
        const deleteMarkup = typeof deleteSession === "function"
          ? `
            <button
              class="alignment-history-delete"
              type="button"
              data-testid="alignment-history-delete"
              ${running ? "disabled aria-disabled=\"true\"" : ""}
              aria-pressed="${pendingDelete ? "true" : "false"}"
              aria-label="${escapeHtml(pendingDelete ? localeText("确认删除历史对话", "Confirm delete chat") : localeText("删除历史对话", "Delete chat"))}"
              title="${escapeHtml(pendingDelete ? localeText("再次点击确认删除", "Click again to confirm delete") : localeText("删除", "Delete"))}"
            >${pendingDelete ? escapeHtml(localeText("删除？", "Delete?")) : "×"}</button>
          `
          : "";
        item.innerHTML = `
          ${openTag}
            <strong>${escapeHtml(session.title || session.id)}</strong>
            <span class="alignment-history-status">
              <span class="alignment-history-status-dot" aria-hidden="true"></span>
              <span>${escapeHtml(statusLabel(session.status_label || session.status, session.alignment_stage))} · ${escapeHtml(session.executor_kind || "")}</span>
            </span>
          ${closeTag}
          ${deleteMarkup}
        `;
        item.querySelector(".alignment-history-open")?.addEventListener("click", () => {
          if (typeof openSession === "function") {
            openSession(session);
          }
        });
        item.querySelector(".alignment-history-delete")?.addEventListener("click", (event) => {
          event.stopPropagation();
          if (pendingDeleteId !== sessionId) {
            pendingDeleteId = sessionId;
            render();
            return;
          }
          pendingDeleteId = "";
          deleteSession(session);
        });
        historyList.append(item);
      });
    }

    function historyStateElement({testid, message, className = "", retry = false}) {
        const href = typeof emptyStartHref === "function" ? emptyStartHref() : emptyStartHref || "";
        const canStartWithButton = !href && typeof emptyStartAction === "function";
        const empty = document.createElement("div");
        empty.className = `alignment-history-empty${className ? ` ${className}` : ""}`;
        empty.dataset.testid = testid;
        empty.innerHTML = `
          <p class="field-note">${escapeHtml(message)}</p>
          ${retry ? `
            <button class="alignment-history-empty-action" type="button" data-testid="alignment-history-retry-button">
              ${escapeHtml(localeText("重试", "Retry"))}
            </button>
          ` : ""}
          ${href ? `
            <a class="alignment-history-empty-action" href="${escapeHtml(href)}" data-testid="alignment-history-empty-start-link">
              ${escapeHtml(localeText("开始 Web 对话", "Start Web conversation"))}
            </a>
          ` : ""}
          ${canStartWithButton ? `
            <button class="alignment-history-empty-action" type="button" data-testid="alignment-history-empty-start-button">
              ${escapeHtml(localeText("开始 Web 对话", "Start Web conversation"))}
            </button>
          ` : ""}
        `;
        empty.querySelector('[data-testid="alignment-history-retry-button"]')?.addEventListener("click", () => {
          load().catch(() => {});
        });
        empty.querySelector('[data-testid="alignment-history-empty-start-button"]')?.addEventListener("click", () => {
          emptyStartAction();
        });
        return empty;
    }

    async function load() {
      if (!historyList || typeof fetchSessions !== "function") {
        return;
      }
      try {
        const payload = await fetchSessions();
        loadError = "";
        render(payload.sessions || []);
      } catch (error) {
        loadError = String(error?.message || "load_failed");
        render(lastSessions);
      }
    }

    return {load, render, statusLabel};
  }

  window.LooporaAlignmentHistory = {createAlignmentHistory};
})();

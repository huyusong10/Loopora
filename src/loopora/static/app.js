(() => {
  const STATUS_LABELS = {
    zh: {
      draft: "草稿",
      queued: "排队中",
      running: "运行中",
      validating: "校验中",
      repairing: "自动修复",
      ready: "方案待审阅",
      awaiting_agent: "等待 Agent",
      succeeded: "正常结束",
      failed: "失败",
      stopped: "已停止",
    },
    en: {
      draft: "draft",
      queued: "queued",
      running: "running",
      validating: "validating",
      repairing: "repairing",
      ready: "ready for review",
      awaiting_agent: "awaiting agent",
      succeeded: "finished normally",
      failed: "failed",
      stopped: "stopped",
    },
  };

  const ROLE_LABELS = {
    zh: {
      generator: "构建者",
      builder: "构建者",
      check_planner: "检查规划者",
      tester: "巡检者",
      inspector: "巡检者",
      verifier: "守门者",
      gatekeeper: "守门者",
      challenger: "引导者",
      guide: "引导者",
      system: "系统",
    },
    en: {
      generator: "Builder",
      builder: "Builder",
      check_planner: "Check Planner",
      tester: "Inspector",
      inspector: "Inspector",
      verifier: "GateKeeper",
      gatekeeper: "GateKeeper",
      challenger: "Guide",
      guide: "Guide",
      system: "System",
    },
  };
  const ROLE_DISPLAY_BY_ARCHETYPE = {
    builder: "Builder",
    inspector: "Inspector",
    gatekeeper: "GateKeeper",
    guide: "Guide",
    custom: "Custom Role",
  };
  const ROLE_DISPLAY_LABELS = {
    zh: {
      Builder: "构建者",
      Inspector: "巡检者",
      GateKeeper: "守门者",
      Guide: "引导者",
      "Custom Role": "自定义角色",
      "Contract Inspector": "契约巡检者",
      "Evidence Inspector": "证据巡检者",
      "Benchmark Inspector": "基准巡检者",
      "Regression Inspector": "回归巡检者",
    },
    en: {},
  };
  const ROLE_NAME_ALIASES = {
    builder: ["构建者", "建造者", "generator", "builder"],
    inspector: ["巡检者", "tester", "inspector"],
    gatekeeper: ["守门者", "守门人", "verifier", "gatekeeper"],
    guide: ["引导者", "向导", "challenger", "guide"],
    custom: ["自定义角色", "custom role", "custom"],
  };
  const ROLE_NAME_LOOKUP = Object.fromEntries(
    Object.entries(ROLE_NAME_ALIASES).flatMap(([archetype, aliases]) => {
      const canonical = ROLE_DISPLAY_BY_ARCHETYPE[archetype];
      return aliases.flatMap((alias) => {
        const normalized = String(alias || "").trim();
        return normalized ? [[normalized, canonical], [normalized.toLowerCase(), canonical]] : [];
      });
    })
  );
  const ALIGNMENT_SESSION_STORAGE_KEY = "loopora:alignment-session:v1";
  const ACTIVE_ALIGNMENT_STATUSES = new Set(["running", "validating", "repairing"]);
  const PROJECT_SCOPE_QUERY_PARAM = "project_scope";
  const ALL_PROJECTS_SCOPE = "all";

  function readSavedLocale() {
    try {
      const saved = window.localStorage.getItem("loopora:locale");
      if (saved === "zh" || saved === "en") {
        return saved;
      }
    } catch (_) {
      // Ignore storage access issues and fall back to environment detection.
    }
    return null;
  }

  function readSavedTheme() {
    try {
      const saved = window.localStorage.getItem("loopora:theme");
      if (saved === "light" || saved === "dark") {
        return saved;
      }
    } catch (_) {
      // Ignore storage access issues and fall back to system preferences.
    }
    return null;
  }

  function normalizeLocale(value) {
    if (typeof value !== "string") {
      return "";
    }
    return value.trim().replace(/_/g, "-").toLowerCase();
  }

  function isChineseLocale(value) {
    const locale = normalizeLocale(value);
    return locale === "zh" || locale.startsWith("zh-") || locale.includes("-hans") || locale.includes("-hant");
  }

  function detectPreferredLocale() {
    const saved = readSavedLocale();
    if (saved) {
      return saved;
    }

    const nav = typeof navigator === "object" && navigator ? navigator : {};
    const systemCandidates = [];
    const browserCandidates = [];

    if (typeof nav.systemLanguage === "string") {
      systemCandidates.push(nav.systemLanguage);
    }

    try {
      const intlLocale = Intl.DateTimeFormat().resolvedOptions().locale;
      if (typeof intlLocale === "string") {
        systemCandidates.push(intlLocale);
      }
    } catch (_) {
      // Ignore Intl availability issues.
    }

    if (Array.isArray(nav.languages) && nav.languages.length > 0) {
      browserCandidates.push(nav.languages[0]);
    }
    browserCandidates.push(nav.language, nav.userLanguage, nav.browserLanguage);

    if (systemCandidates.some(isChineseLocale)) {
      return "zh";
    }
    if (browserCandidates.some(isChineseLocale)) {
      return "zh";
    }
    return "en";
  }

  function initialLocale() {
    return detectPreferredLocale();
  }

  function currentLocale() {
    return document.documentElement.dataset.locale || initialLocale();
  }

  function initialTheme() {
    const saved = readSavedTheme();
    if (saved) {
      return saved;
    }
    const prefersDark = typeof window.matchMedia === "function"
      && window.matchMedia("(prefers-color-scheme: dark)").matches;
    return prefersDark ? "dark" : "light";
  }

  function currentTheme() {
    return document.documentElement.dataset.theme || initialTheme();
  }

  function pickText(values) {
    return currentLocale() === "zh" ? values.zh : values.en;
  }

  let appFeedbackTimer = null;

  function showAppFeedback(message, kind = "", options = {}) {
    const node = document.getElementById("app-feedback");
    if (!node) {
      return;
    }
    if (appFeedbackTimer) {
      window.clearTimeout(appFeedbackTimer);
      appFeedbackTimer = null;
    }
    const text = String(message || "").trim();
    node.textContent = text;
    node.hidden = !text;
    const normalizedKind = ["success", "warning", "error"].includes(kind) ? kind : "";
    node.className = `app-feedback${normalizedKind ? ` is-${normalizedKind}` : ""}`;
    if (!text || options.autoHide === false) {
      return;
    }
    appFeedbackTimer = window.setTimeout(() => {
      if (node.textContent === text) {
        node.hidden = true;
        node.textContent = "";
        node.className = "app-feedback";
      }
      appFeedbackTimer = null;
    }, Number(options.durationMs || 4800));
  }

  function returnedSurfaceUpdateMessage(value) {
    const marker = String(value || "").trim();
    if (marker === "workflow") {
      return pickText({
        zh: "流程编排已保存，可以继续当前工作。",
        en: "The flow was saved. You can keep working here.",
      });
    }
    if (marker.startsWith("role:")) {
      return pickText({
        zh: "角色定义已保存，可以继续当前工作。",
        en: "The role definition was saved. You can keep working here.",
      });
    }
    return "";
  }

  function handleReturnedSurfaceUpdateFeedback() {
    if (typeof URL !== "function" || !window.location) {
      return;
    }

    let url;
    try {
      url = new URL(window.location.href);
    } catch (_) {
      return;
    }

    const message = returnedSurfaceUpdateMessage(url.searchParams.get("surface_updated"));
    const hasInlineFeedback = Boolean(document.querySelector("[data-surface-update-feedback]"));
    let changed = false;
    if (message && !hasInlineFeedback) {
      showAppFeedback(message, "success", {durationMs: 6200});
    }
    if (message) {
      url.searchParams.delete("surface_updated");
      changed = true;
    }
    document.querySelectorAll("[data-return-feedback-param]").forEach((node) => {
      const key = String(node.dataset.returnFeedbackParam || "").trim();
      if (!key || !url.searchParams.has(key)) {
        return;
      }
      url.searchParams.delete(key);
      changed = true;
    });
    if (!changed) {
      return;
    }

    if (window.history && typeof window.history.replaceState === "function") {
      try {
        window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
      } catch (_) {
        // URL cleanup is best-effort; the visible feedback is the stable behavior.
      }
    }
  }

  function currentHashTargetElement() {
    const rawHash = String(window.location?.hash || "").slice(1);
    if (!rawHash) {
      return null;
    }
    let targetId = rawHash;
    try {
      targetId = decodeURIComponent(rawHash);
    } catch (_) {
      // Keep the raw hash if it is not URI-encoded cleanly.
    }
    return document.getElementById(targetId);
  }

  function openHashLinkedDisclosure() {
    const target = currentHashTargetElement();
    if (!target) {
      return;
    }
    const disclosure = target.tagName === "DETAILS" ? target : target.closest("details");
    if (disclosure) {
      disclosure.open = true;
    }
  }

  function bindHashLinkedDisclosures() {
    openHashLinkedDisclosure();
    window.addEventListener("hashchange", openHashLinkedDisclosure);
  }

  function translateStatus(value) {
    return STATUS_LABELS[currentLocale()][value] || value || "-";
  }

  function translateRole(value) {
    if (!value || value === "-") {
      return "-";
    }
    return ROLE_LABELS[currentLocale()][value] || normalizeRoleName(value);
  }

  function normalizeRoleName(value, archetype = "") {
    if (!value || value === "-") {
      return value || "-";
    }
    const text = String(value).trim();
    if (!text) {
      return "-";
    }
    const localizedText = ROLE_DISPLAY_LABELS[currentLocale()]?.[text];
    if (localizedText) {
      return localizedText;
    }
    const canonical = ROLE_DISPLAY_BY_ARCHETYPE[String(archetype || "").trim().toLowerCase()] || "";
    if (canonical) {
      const localizedCanonical = ROLE_DISPLAY_LABELS[currentLocale()]?.[canonical] || canonical;
      const lowered = text.toLowerCase();
      if (lowered === canonical.toLowerCase()) {
        return localizedCanonical;
      }
      if (ROLE_NAME_LOOKUP[text] === canonical || ROLE_NAME_LOOKUP[lowered] === canonical) {
        return localizedCanonical;
      }
      return text;
    }
    const matchedCanonical = ROLE_NAME_LOOKUP[text] || ROLE_NAME_LOOKUP[text.toLowerCase()];
    return matchedCanonical ? (ROLE_DISPLAY_LABELS[currentLocale()]?.[matchedCanonical] || matchedCanonical) : text;
  }

  function applyLocalizedAttributes(root = document) {
    root.querySelectorAll("[data-placeholder-zh]").forEach((element) => {
      const placeholder = currentLocale() === "zh" ? element.dataset.placeholderZh : element.dataset.placeholderEn;
      if (placeholder) {
        element.setAttribute("placeholder", placeholder);
      }
    });

    root.querySelectorAll("[data-title-zh]").forEach((element) => {
      const title = currentLocale() === "zh" ? element.dataset.titleZh : element.dataset.titleEn;
      if (title) {
        element.setAttribute("data-tooltip", title);
        element.setAttribute("aria-label", title);
        element.removeAttribute("title");
      } else {
        element.removeAttribute("data-tooltip");
        element.removeAttribute("aria-label");
        element.removeAttribute("title");
      }
    });

    root.querySelectorAll("[data-status-label]").forEach((element) => {
      element.textContent = translateStatus(element.dataset.statusLabel);
    });

    root.querySelectorAll("[data-role-label]").forEach((element) => {
      element.textContent = translateRole(element.dataset.roleLabel);
    });
  }

  function syncLocaleButtons() {
    document.querySelectorAll("[data-set-locale]").forEach((button) => {
      button.classList.toggle("active", button.dataset.setLocale === currentLocale());
    });
  }

  function setLocale(locale, options = {}) {
    if (locale !== "zh" && locale !== "en") {
      return;
    }
    const persist = options.persist !== false;
    document.documentElement.dataset.locale = locale;
    document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
    if (persist) {
      try {
        window.localStorage.setItem("loopora:locale", locale);
      } catch (_) {
        // Ignore storage access issues.
      }
    }
    applyLocalizedAttributes(document);
    syncLocaleButtons();
    document.dispatchEvent(new CustomEvent("loopora:localechange", {detail: {locale}}));
  }

  function setTheme(theme, options = {}) {
    if (theme !== "light" && theme !== "dark") {
      return;
    }
    const persist = options.persist !== false;
    document.documentElement.dataset.theme = theme;
    if (persist) {
      try {
        window.localStorage.setItem("loopora:theme", theme);
      } catch (_) {
        // Ignore storage access issues.
      }
    }
    document.querySelectorAll("[data-set-theme]").forEach((button) => {
      button.classList.toggle("active", button.dataset.setTheme === theme);
    });
    document.dispatchEvent(new CustomEvent("loopora:themechange", {detail: {theme}}));
  }

  function bindDeleteLoopButtons() {
    const modal = document.getElementById("confirm-modal");
    const modalDetail = document.getElementById("confirm-modal-detail");
    const modalPreview = document.getElementById("confirm-modal-preview");
    const modalStatus = document.getElementById("confirm-modal-status");
    const modalCancel = document.getElementById("confirm-modal-cancel");
    const modalConfirm = document.getElementById("confirm-modal-confirm");
    const modalBackdrop = modal?.querySelector("[data-close-confirm-modal]");
    const modalDialog = modal?.querySelector(".confirm-modal-dialog");
    if (!modal || !modalDetail || !modalPreview || !modalCancel || !modalConfirm) {
      return;
    }

    const deleteConfigs = [
      {
        selector: "[data-delete-loop]",
        idKey: "deleteLoop",
        nameKey: "loopName",
        endpointPrefix: "/api/loops/",
        previewEndpointPrefix: "/api/loops/",
        previewKind: "loop",
        redirectUrl: "/",
        countId: "loop-count",
        gridId: "loop-grid",
        emptyStateId: "loops-empty-state",
        noteSelector: "[data-testid='loop-grid-note']",
        detail(name) {
          return pickText({
            zh: `“${name}” 和它保存下来的运行记录都会一起消失，这次就真的不回头了。`,
            en: `"${name}" and its stored run history will disappear together. This one really does not come back.`,
          });
        },
        failure() {
          return pickText({
            zh: "无法删除这个 Loop。",
            en: "Unable to delete this loop.",
          });
        },
      },
      {
        selector: "[data-delete-bundle]",
        idKey: "deleteBundle",
        nameKey: "bundleName",
        endpointPrefix: "/api/bundles/",
        previewEndpointPrefix: "/api/bundles/",
        previewKind: "bundle",
        redirectUrl: "/bundles",
        countId: "bundle-count",
        gridId: "bundle-grid",
        emptyStateId: "bundles-empty-state",
        noteSelector: "[data-testid='bundle-grid-note']",
        detail(name) {
          return pickText({
            zh: `“${name}” 和它导入的 Loop、流程、角色定义都会一起清理。手动资源不会被影响。`,
            en: `"${name}" and its imported loop, flow, and role definitions will be removed together. Unrelated manual assets stay intact.`,
          });
        },
        failure() {
          return pickText({
            zh: "无法删除这个方案。",
            en: "Unable to delete this plan.",
          });
        },
      },
      {
        selector: "[data-delete-role-definition]",
        idKey: "deleteRoleDefinition",
        nameKey: "roleDefinitionName",
        endpointPrefix: "/api/role-definitions/",
        previewEndpointPrefix: "/api/role-definitions/",
        previewKind: "roleDefinition",
        redirectUrl: "/roles",
        countId: "role-definition-count",
        gridId: "role-definition-grid",
        emptyStateId: "role-definitions-empty-state",
        noteSelector: "",
        detail(name) {
          return pickText({
            zh: `自定义角色“${name}”会从后续编排选择里移除。已保存的 Loop 不会被自动改写。`,
            en: `The custom role "${name}" will be removed from future flow choices. Saved loops are not rewritten automatically.`,
          });
        },
        failure() {
          return pickText({
            zh: "无法删除这个角色。",
            en: "Unable to delete this role.",
          });
        },
      },
      {
        selector: "[data-delete-orchestration]",
        idKey: "deleteOrchestration",
        nameKey: "orchestrationName",
        endpointPrefix: "/api/orchestrations/",
        previewEndpointPrefix: "/api/orchestrations/",
        previewKind: "orchestration",
        redirectUrl: "/orchestrations",
        countId: "orchestration-count",
        gridId: "orchestration-grid",
        emptyStateId: "orchestrations-empty-state",
        noteSelector: "",
        detail(name) {
          return pickText({
            zh: `自定义编排“${name}”会从后续创建 Loop 的选择里移除。已保存的 Loop 不会被自动改写。`,
            en: `The custom flow "${name}" will be removed from future loop creation choices. Saved loops are not rewritten automatically.`,
          });
        },
        failure() {
          return pickText({
            zh: "无法删除这个编排。",
            en: "Unable to delete this flow.",
          });
        },
      },
    ];

    let pendingDelete = null;
    let lastFocusedElement = null;
    const DELETE_MODAL_FOCUS_SELECTOR = [
      "a[href]",
      "button:not([disabled])",
      "input:not([disabled])",
      "select:not([disabled])",
      "textarea:not([disabled])",
      "[tabindex]:not([tabindex='-1'])",
    ].join(",");

    function deleteModalFocusableControls() {
      return Array.from(modal.querySelectorAll(DELETE_MODAL_FOCUS_SELECTOR)).filter((node) => {
        if (node.disabled || node.hidden) {
          return false;
        }
        return node.getAttribute("aria-hidden") !== "true";
      });
    }

    function focusDeleteModalTarget(target) {
      if (target && typeof target.focus === "function") {
        target.focus();
        return;
      }
      modalDialog?.focus?.();
    }

    function trapDeleteModalFocus(event) {
      if (event.key !== "Tab" || modal.hidden) {
        return;
      }
      const focusable = deleteModalFocusableControls();
      if (focusable.length === 0) {
        event.preventDefault();
        focusDeleteModalTarget(null);
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (typeof modal.contains === "function" && !modal.contains(document.activeElement)) {
        event.preventDefault();
        focusDeleteModalTarget(first);
        return;
      }
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        focusDeleteModalTarget(last);
        return;
      }
      if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        focusDeleteModalTarget(first);
      }
    }

    function closeDeleteModal() {
      modal.hidden = true;
      modal.setAttribute("aria-hidden", "true");
      document.body.classList.remove("modal-open");
      pendingDelete = null;
      modalConfirm.disabled = false;
      setDeleteModalPreview(null);
      setDeleteModalStatus("");
      lastFocusedElement?.focus?.();
    }

    function setDeleteModalStatus(message) {
      if (!modalStatus) {
        return;
      }
      const text = String(message || "");
      modalStatus.textContent = text;
      modalStatus.hidden = !text;
    }

    function deletePreviewLabel(key) {
      const labels = {
        target_project_workdir: {zh: "目标项目目录", en: "target project folder"},
        source_spec_file: {zh: "来源 spec 文件", en: "source spec file"},
        exported_plan_files: {zh: "已导出的 Plan File", en: "exported Plan Files"},
        original_exported_yaml_file: {zh: "原始导出 YAML", en: "original exported YAML"},
        source_project_workdir: {zh: "来源项目目录", en: "source project folder"},
        non_bundle_owned_assets: {zh: "非本 Plan File 拥有的资产", en: "non-bundle-owned assets"},
        saved_loop_snapshots: {zh: "已保存 Loop 快照", en: "saved Loop snapshots"},
        saved_orchestration_snapshots: {zh: "已保存流程快照", en: "saved flow snapshots"},
        external_provider_history: {zh: "外部 provider 历史", en: "external provider history"},
      };
      return pickText(labels[key] || {zh: String(key || "").replaceAll("_", " "), en: String(key || "").replaceAll("_", " ")});
    }

    function compactDeletePreviewValues(values) {
      const normalized = (Array.isArray(values) ? values : [])
        .map((value) => String(value || "").trim())
        .filter(Boolean);
      if (normalized.length === 0) {
        return pickText({zh: "无", en: "none"});
      }
      if (normalized.length <= 3) {
        return normalized.join(", ");
      }
      return `${normalized.slice(0, 3).join(", ")} +${normalized.length - 3}`;
    }

    function deletePreviewRows(config, payload) {
      const wouldDelete = payload?.would_delete && typeof payload.would_delete === "object" ? payload.would_delete : {};
      const rows = [];
      if (config.previewKind === "loop") {
        rows.push({
          label: pickText({zh: "将删除的运行", en: "Runs to delete"}),
          value: `${Number(wouldDelete.run_count || 0)} · ${compactDeletePreviewValues(wouldDelete.run_ids)}`,
        });
      } else if (config.previewKind === "bundle") {
        rows.push({label: "Loop", value: String(wouldDelete.linked_loop || pickText({zh: "无", en: "none"}))});
        rows.push({label: pickText({zh: "流程", en: "Flow"}), value: String(wouldDelete.linked_orchestration || pickText({zh: "无", en: "none"}))});
        rows.push({
          label: pickText({zh: "角色定义", en: "Role definitions"}),
          value: `${Number(wouldDelete.linked_role_definition_count || 0)} · ${compactDeletePreviewValues(wouldDelete.linked_role_definition_ids)}`,
        });
        rows.push({
          label: pickText({zh: "关联运行", en: "Linked runs"}),
          value: `${Number(wouldDelete.linked_run_count || 0)} · ${compactDeletePreviewValues(wouldDelete.linked_run_ids)}`,
        });
      } else if (config.previewKind === "roleDefinition") {
        rows.push({label: pickText({zh: "角色定义", en: "Role definition"}), value: String(wouldDelete.role_definition || pickText({zh: "无", en: "none"}))});
        rows.push({
          label: pickText({zh: "引用它的流程", en: "Flows using it"}),
          value: `${Number(wouldDelete.referencing_orchestration_count || 0)} · ${compactDeletePreviewValues(wouldDelete.referencing_orchestration_ids)}`,
        });
      } else if (config.previewKind === "orchestration") {
        rows.push({label: pickText({zh: "流程", en: "Flow"}), value: String(wouldDelete.orchestration || pickText({zh: "无", en: "none"}))});
        rows.push({
          label: pickText({zh: "引用它的 Loop", en: "Loops using it"}),
          value: `${Number(wouldDelete.referencing_loop_count || 0)} · ${compactDeletePreviewValues(wouldDelete.referencing_loop_ids)}`,
        });
      }
      const activeRunIds = Array.isArray(payload?.blocked_by_active_runs) ? payload.blocked_by_active_runs : [];
      if (activeRunIds.length > 0) {
        rows.push({
          label: pickText({zh: "阻塞中的运行", en: "Blocking runs"}),
          value: compactDeletePreviewValues(activeRunIds),
        });
      }
      const preserved = Array.isArray(payload?.does_not_delete) ? payload.does_not_delete.map(deletePreviewLabel) : [];
      if (preserved.length > 0) {
        rows.push({label: pickText({zh: "不会删除", en: "Will not delete"}), value: compactDeletePreviewValues(preserved)});
      }
      return rows;
    }

    function setDeleteModalPreview(payload, config = null) {
      modalPreview.replaceChildren();
      if (!payload || !config) {
        modalPreview.hidden = true;
        modalPreview.classList.remove("is-blocked");
        return;
      }
      const state = document.createElement("p");
      state.className = "delete-preview-state";
      state.textContent = payload.delete_allowed === true
        ? pickText({zh: "预览完成。请确认范围后再删除。", en: "Preview complete. Review the scope before deleting."})
        : pickText({zh: "当前不能安全删除。先处理下面的阻塞项。", en: "Deletion is not currently safe. Resolve the blockers below first."});
      const list = document.createElement("dl");
      deletePreviewRows(config, payload).forEach((row) => {
        const term = document.createElement("dt");
        term.textContent = row.label;
        const detail = document.createElement("dd");
        detail.textContent = row.value;
        list.append(term, detail);
      });
      modalPreview.append(state, list);
      modalPreview.classList.toggle("is-blocked", payload.delete_allowed !== true);
      modalPreview.hidden = false;
    }

    function deletePreviewFailureMessage() {
      return pickText({
        zh: "删除范围预览失败。为了避免误删，请刷新后再试。",
        en: "Unable to preview the delete scope. Refresh and try again before deleting.",
      });
    }

    function deletePreviewBlockedMessage(payload) {
      const activeRunIds = Array.isArray(payload?.blocked_by_active_runs) ? payload.blocked_by_active_runs : [];
      if (activeRunIds.length > 0) {
        return pickText({
          zh: `还有 ${activeRunIds.length} 个运行未结束，不能删除。`,
          en: `${activeRunIds.length} run(s) are still active, so deletion is blocked.`,
        });
      }
      const blockers = Array.isArray(payload?.blockers) ? payload.blockers : [];
      const bundleBlocker = blockers.find((item) => item && item.kind === "bundle_owned" && item.bundle_id);
      if (bundleBlocker) {
        return pickText({
          zh: `这个资产由 Plan File ${bundleBlocker.bundle_id} 管理；请删除对应 Plan File。`,
          en: `This asset is managed by Plan File ${bundleBlocker.bundle_id}; delete that Plan File instead.`,
        });
      }
      const orchestrationBlocker = blockers.find((item) => item && item.kind === "referenced_by_orchestrations" && Array.isArray(item.orchestration_ids) && item.orchestration_ids.length > 0);
      if (orchestrationBlocker) {
        return pickText({
          zh: `还有 ${orchestrationBlocker.orchestration_ids.length} 个流程引用这个角色，不能删除。`,
          en: `${orchestrationBlocker.orchestration_ids.length} flow(s) still use this role, so deletion is blocked.`,
        });
      }
      const loopBlocker = blockers.find((item) => item && item.kind === "referenced_by_loops" && Array.isArray(item.loop_ids) && item.loop_ids.length > 0);
      if (loopBlocker) {
        return pickText({
          zh: `还有 ${loopBlocker.loop_ids.length} 个 Loop 引用这个流程，不能删除。`,
          en: `${loopBlocker.loop_ids.length} Loop(s) still use this flow, so deletion is blocked.`,
        });
      }
      const preflightBlocker = blockers.find((item) => item && item.kind === "preflight" && item.message);
      if (preflightBlocker) {
        return String(preflightBlocker.message);
      }
      return pickText({
        zh: "当前不能安全删除。先处理预览里的阻塞项。",
        en: "Deletion is not currently safe. Resolve the preview blockers first.",
      });
    }

    function deletePreviewLoadingMessage() {
      return pickText({
        zh: "正在检查删除范围…",
        en: "Checking delete scope...",
      });
    }

    function openDeleteModal(config, button, resourceId, resourceName) {
      const previewRequired = Boolean(config.previewEndpointPrefix);
      pendingDelete = {config, button, resourceId, resourceName, previewRequired, deleteAllowed: !previewRequired};
      lastFocusedElement = button;
      modalDetail.textContent = config.detail(resourceName);
      setDeleteModalPreview(null);
      setDeleteModalStatus("");
      modalConfirm.disabled = previewRequired;
      modal.hidden = false;
      modal.setAttribute("aria-hidden", "false");
      document.body.classList.add("modal-open");
      if (previewRequired) {
        setDeleteModalStatus(deletePreviewLoadingMessage());
        loadDeletePreview(pendingDelete);
      }
      (previewRequired ? modalCancel : modalConfirm).focus();
    }

    async function loadDeletePreview(deleteRequest) {
      const {config, resourceId} = deleteRequest;
      let response;
      let payload;
      try {
        response = await fetch(`${config.previewEndpointPrefix}${encodeURIComponent(resourceId)}/delete-preview`);
        payload = await response.json();
      } catch (_) {
        if (pendingDelete === deleteRequest) {
          modalConfirm.disabled = true;
          setDeleteModalStatus(deletePreviewFailureMessage());
        }
        return;
      }
      if (pendingDelete !== deleteRequest) {
        return;
      }
      if (!response.ok) {
        modalConfirm.disabled = true;
        setDeleteModalStatus(payload?.error || deletePreviewFailureMessage());
        return;
      }
      deleteRequest.deleteAllowed = payload?.delete_allowed === true;
      modalConfirm.disabled = !deleteRequest.deleteAllowed;
      setDeleteModalPreview(payload, config);
      setDeleteModalStatus(deleteRequest.deleteAllowed ? "" : deletePreviewBlockedMessage(payload));
    }

    function removeResourceCard(button, config) {
      const card = button.closest(".loop-card");
      if (!card) {
        window.location.href = contextPreservingRedirectUrl(config.redirectUrl, window.location.pathname || "/");
        return;
      }
      const grid = document.getElementById(config.gridId);
      card.remove();
      const remainingCards = grid ? grid.querySelectorAll(".loop-card").length : 0;
      const countElement = document.getElementById(config.countId);
      const emptyState = document.getElementById(config.emptyStateId);
      const gridNote = config.noteSelector ? document.querySelector(config.noteSelector) : null;
      if (countElement) {
        countElement.textContent = String(remainingCards);
      }
      if (remainingCards === 0) {
        if (grid) {
          grid.hidden = true;
        }
        if (gridNote) {
          gridNote.hidden = true;
        }
        if (emptyState) {
          emptyState.hidden = false;
        } else {
          window.location.reload();
        }
      }
    }

    modalCancel.addEventListener("click", closeDeleteModal);
    modalBackdrop?.addEventListener("click", closeDeleteModal);
    modal.addEventListener("click", (event) => {
      if (event.target === modal) {
        closeDeleteModal();
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !modal.hidden) {
        closeDeleteModal();
      }
      trapDeleteModalFocus(event);
    });
    modalConfirm.addEventListener("click", async () => {
      if (!pendingDelete) {
        return;
      }
      modalConfirm.disabled = true;
      const {button, config, resourceId} = pendingDelete;
      if (pendingDelete.previewRequired && pendingDelete.deleteAllowed !== true) {
        modalConfirm.disabled = true;
        setDeleteModalStatus(config.failure());
        return;
      }
      let response;
      try {
        response = await fetch(`${config.endpointPrefix}${encodeURIComponent(resourceId)}`, {method: "DELETE"});
      } catch (_) {
        modalConfirm.disabled = false;
        setDeleteModalStatus(config.failure());
        return;
      }
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        modalConfirm.disabled = false;
        setDeleteModalStatus(payload.error || config.failure());
        return;
      }
      closeDeleteModal();
      removeResourceCard(button, config);
    });

    deleteConfigs.forEach((config) => {
      document.querySelectorAll(config.selector).forEach((button) => {
        if (button.dataset.bound === "1") {
          return;
        }
        button.dataset.bound = "1";
        button.addEventListener("click", async () => {
          const resourceId = button.dataset[config.idKey];
          const resourceName = button.dataset[config.nameKey] || resourceId;
          openDeleteModal(config, button, resourceId, resourceName);
        });
      });
    });
  }

  function bindOpenCards() {
    document.querySelectorAll("[data-open-card]").forEach((card) => {
      if (card.dataset.boundCard === "1") {
        return;
      }
      card.dataset.boundCard = "1";
      if (!openCardTargetUrl(card)) {
        return;
      }
      enhanceOpenCardAccessibility(card);

      const isInteractive = (target) => target instanceof Element
        && Boolean(target.closest("a, button, input, select, textarea, summary, [role='button']"));

      card.addEventListener("click", (event) => {
        if (isInteractive(event.target)) {
          return;
        }
        const openUrl = openCardTargetUrl(card);
        if (!openUrl) {
          return;
        }
        window.location.href = openUrl;
      });

      card.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") {
          return;
        }
        if (isInteractive(event.target)) {
          return;
        }
        event.preventDefault();
        const openUrl = openCardTargetUrl(card);
        if (!openUrl) {
          return;
        }
        window.location.href = openUrl;
      });
    });
  }

  function openCardTargetUrl(card) {
    const openUrl = safeLocalRecoveryUrl(card?.dataset?.openCard);
    return openUrl ? contextPreservingRedirectUrl(openUrl, openUrl) : "";
  }

  function compactElementText(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function openCardAccessibleName(card) {
    const title = card.querySelector("[data-open-card-label], h1, h2, h3, strong");
    return compactElementText(title?.textContent || card.getAttribute("data-open-card-label") || "");
  }

  function enhanceOpenCardAccessibility(card) {
    if (!card.hasAttribute("role")) {
      card.setAttribute("role", "link");
    }
    if (!card.hasAttribute("tabindex")) {
      card.setAttribute("tabindex", "0");
    }
    if (!card.hasAttribute("aria-label")) {
      const label = openCardAccessibleName(card);
      if (label) {
        card.setAttribute("aria-label", label);
      }
    }
  }

  function bindPrimaryNavigation() {
    document.querySelectorAll(".top-nav-link").forEach((link) => {
      if (link.dataset.boundNav === "1") {
        return;
      }
      if (link.matches("[data-toggle-nav-menu]")) {
        return;
      }
      link.dataset.boundNav = "1";
      link.addEventListener("click", () => {
        link.classList.add("is-routing");
      });
    });
  }

  function revealActiveTopNavItem() {
    const rail = document.querySelector(".top-nav-links");
    const active = rail?.querySelector(".top-nav-link.active");
    if (!(rail instanceof HTMLElement) || !(active instanceof HTMLElement)) {
      return;
    }
    if (rail.scrollWidth <= rail.clientWidth + 1) {
      rail.scrollLeft = 0;
      return;
    }
    const railBox = rail.getBoundingClientRect();
    const activeBox = active.getBoundingClientRect();
    const nextScrollLeft = rail.scrollLeft
      + activeBox.left
      - railBox.left
      - ((rail.clientWidth - activeBox.width) / 2);
    const maxScrollLeft = Math.max(0, rail.scrollWidth - rail.clientWidth);
    rail.scrollLeft = Math.max(0, Math.min(nextScrollLeft, maxScrollLeft));
  }

  function bindNavPreferences() {
    const roots = Array.from(document.querySelectorAll("[data-nav-menu]"));
    if (!roots.length) {
      return;
    }
    const NAV_MENU_ITEM_SELECTOR = "a[href], button:not([disabled])";

    const navMenuItems = (root) => {
      const panel = root.querySelector("[data-nav-menu-panel]");
      if (!panel || panel.hidden) {
        return [];
      }
      return Array.from(panel.querySelectorAll(NAV_MENU_ITEM_SELECTOR)).filter((item) => {
        if (item.hidden || item.getAttribute("aria-hidden") === "true") {
          return false;
        }
        return typeof item.focus === "function";
      });
    };

    const focusNavMenuItem = (root, index) => {
      const items = navMenuItems(root);
      if (!items.length) {
        return false;
      }
      const targetIndex = ((index % items.length) + items.length) % items.length;
      items[targetIndex].focus();
      return true;
    };

    const rootOwnsFocus = (root) => {
      return document.activeElement instanceof Node && root.contains(document.activeElement);
    };

    const closeMenu = (root, {restoreFocus = false} = {}) => {
      const toggle = root.querySelector("[data-toggle-nav-menu]");
      const panel = root.querySelector("[data-nav-menu-panel]");
      if (!toggle || !panel) {
        return;
      }
      root.classList.remove("is-open");
      panel.hidden = true;
      toggle.setAttribute("aria-expanded", "false");
      if (restoreFocus && typeof toggle.focus === "function") {
        toggle.focus();
      }
    };

    const openMenu = (root, {focusFirst = false} = {}) => {
      roots.forEach((otherRoot) => {
        if (otherRoot !== root) {
          closeMenu(otherRoot);
        }
      });
      const toggle = root.querySelector("[data-toggle-nav-menu]");
      const panel = root.querySelector("[data-nav-menu-panel]");
      if (!toggle || !panel) {
        return;
      }
      root.classList.add("is-open");
      panel.hidden = false;
      toggle.setAttribute("aria-expanded", "true");
      if (focusFirst) {
        focusNavMenuItem(root, 0);
      }
    };

    roots.forEach((root) => {
      if (root.dataset.boundPreferences === "1") {
        return;
      }
      root.dataset.boundPreferences = "1";

      const toggle = root.querySelector("[data-toggle-nav-menu]");
      const panel = root.querySelector("[data-nav-menu-panel]");
      if (!toggle || !panel) {
        return;
      }

      toggle.addEventListener("click", (event) => {
        event.preventDefault();
        if (root.classList.contains("is-open")) {
          closeMenu(root);
          return;
        }
        openMenu(root);
      });

      toggle.addEventListener("keydown", (event) => {
        if (["ArrowDown", "Enter", " "].includes(event.key)) {
          event.preventDefault();
          openMenu(root, {focusFirst: true});
          return;
        }
        if (event.key === "Escape" && root.classList.contains("is-open")) {
          event.preventDefault();
          closeMenu(root, {restoreFocus: true});
        }
      });

      panel.addEventListener("keydown", (event) => {
        const items = navMenuItems(root);
        if (!items.length) {
          return;
        }
        const currentIndex = items.indexOf(document.activeElement);
        if (event.key === "Escape") {
          event.preventDefault();
          closeMenu(root, {restoreFocus: true});
          return;
        }
        if (event.key === "ArrowDown") {
          event.preventDefault();
          focusNavMenuItem(root, currentIndex >= 0 ? currentIndex + 1 : 0);
          return;
        }
        if (event.key === "ArrowUp") {
          event.preventDefault();
          focusNavMenuItem(root, currentIndex >= 0 ? currentIndex - 1 : items.length - 1);
          return;
        }
        if (event.key === "Home") {
          event.preventDefault();
          focusNavMenuItem(root, 0);
          return;
        }
        if (event.key === "End") {
          event.preventDefault();
          focusNavMenuItem(root, items.length - 1);
        }
      });

      root.addEventListener("focusout", () => {
        window.setTimeout(() => {
          if (!rootOwnsFocus(root)) {
            closeMenu(root);
          }
        }, 0);
      });

      panel.querySelectorAll("a, [data-set-theme], [data-set-locale]").forEach((item) => {
        item.addEventListener("click", () => {
          window.setTimeout(() => closeMenu(root), 0);
        });
      });
    });

    if (document.body.dataset.boundNavMenuDismiss === "1") {
      return;
    }
    document.body.dataset.boundNavMenuDismiss = "1";

    document.addEventListener("click", (event) => {
      if (!(event.target instanceof Node)) {
        return;
      }
      roots.forEach((root) => {
        if (!root.contains(event.target)) {
          closeMenu(root);
        }
      });
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        roots.forEach((root) => closeMenu(root, {restoreFocus: rootOwnsFocus(root)}));
      }
    });
  }

  async function revealPath(path) {
    if (!path) {
      return;
    }
    renderGlobalManualCopy("");
    try {
      const response = await fetch("/api/system/reveal-path", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({path}),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.error || "failed");
      }
      showAppFeedback(pickText({
        zh: "已打开路径。",
        en: "Opened the path.",
      }), "success");
    } catch (error) {
      try {
        await writeTextToClipboard(path);
        showAppFeedback(pickText({
          zh: "无法自动打开，路径已复制到剪贴板。",
          en: "Could not open automatically. The path was copied to your clipboard.",
        }), "warning");
        return;
      } catch (_) {
        renderGlobalManualCopy(path, {
          label: pickText({zh: "手动复制路径", en: "Manual path copy"}),
          textareaId: "global-path-manual-copy-textarea",
        });
        showAppFeedback(pickText({
          zh: "无法自动打开或复制该路径；请手动复制上方路径。",
          en: "Unable to open or copy that path automatically; copy the path above manually.",
        }), "warning");
      }
    }
  }

  function writeTextWithSelectionFallback(text) {
    return new Promise((resolve, reject) => {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.setAttribute("readonly", "");
      textarea.style.position = "fixed";
      textarea.style.left = "-9999px";
      textarea.style.top = "0";
      document.body.appendChild(textarea);
      textarea.select();
      try {
        if (document.execCommand("copy")) {
          resolve();
        } else {
          reject(new Error("copy failed"));
        }
      } catch (error) {
        reject(error);
      } finally {
        document.body.removeChild(textarea);
      }
    });
  }

  function writeTextToClipboard(value) {
    const text = String(value || "");
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      return navigator.clipboard.writeText(text).catch(() => writeTextWithSelectionFallback(text));
    }
    return writeTextWithSelectionFallback(text);
  }

  function renderManualCopy(container, value, options = {}) {
    const target = typeof container === "string" ? document.querySelector(container) : container;
    if (!target) {
      return null;
    }
    const text = String(value || "").trim();
    if (!text) {
      target.hidden = true;
      target.innerHTML = "";
      return null;
    }
    const textareaId = String(options.textareaId || "loopora-manual-copy-textarea");
    const textareaTestId = String(options.textareaTestId || textareaId);
    const rows = String(options.rows || "6");
    const label = String(options.label || pickText({zh: "手动复制", en: "Manual copy"}));
    target.hidden = false;
    target.innerHTML = `
      <label for="${escapeHtml(textareaId)}">
        ${escapeHtml(label)}
      </label>
      <textarea
        id="${escapeHtml(textareaId)}"
        data-testid="${escapeHtml(textareaTestId)}"
        readonly
        rows="${escapeHtml(rows)}"
        spellcheck="false"
      >${escapeHtml(text)}</textarea>
    `;
    const textarea = target.querySelector("textarea");
    if (textarea && options.focus !== false) {
      try {
        textarea.focus({preventScroll: true});
      } catch (_) {
        textarea.focus();
      }
      textarea.select();
    }
    return textarea;
  }

  function renderGlobalManualCopy(value, options = {}) {
    const container = document.querySelector("[data-global-manual-copy]");
    return renderManualCopy(container, value, {
      label: options.label || pickText({zh: "手动复制", en: "Manual copy"}),
      textareaId: options.textareaId || "global-manual-copy-textarea",
      rows: options.rows || 4,
      focus: options.focus,
    });
  }

  function setAgentEntryCopyStatus(button, message) {
    const guide = button.closest(".agent-entry-start-guide") || document.querySelector(".agent-entry-start-guide");
    const status = guide?.querySelector("[data-agent-entry-copy-status]");
    if (status) {
      status.textContent = message;
    }
    button.classList.add("is-copied");
    window.setTimeout(() => button.classList.remove("is-copied"), 1400);
    if (status && message) {
      window.setTimeout(() => {
        if (status.textContent === message) {
          status.textContent = "";
        }
      }, 4200);
    }
  }

  function renderAgentEntryCommandManualCopy(button, command) {
    const guide = button.closest(".agent-entry-start-guide") || document.querySelector(".agent-entry-start-guide");
    const container = guide?.querySelector?.("[data-agent-entry-manual-copy]");
    return renderManualCopy(container, command, {
      label: pickText({zh: "手动复制 /loopora-run 命令", en: "Manual /loopora-run command copy"}),
      textareaId: "agent-entry-command-manual-copy-textarea",
      rows: 4,
    });
  }

  function bindAgentEntryCommandCopy() {
    document.querySelectorAll("[data-agent-entry-command-copy]").forEach((button) => {
      if (button.dataset.boundAgentEntryCopy === "1") {
        return;
      }
      button.dataset.boundAgentEntryCopy = "1";
      button.addEventListener("click", async () => {
        const command = String(button.dataset.copyValue || "").trim();
        if (!command) {
          setAgentEntryCopyStatus(button, pickText({
            zh: "没有可复制的 Agent 命令。",
            en: "No Agent command is available to copy.",
          }));
          return;
        }
        renderAgentEntryCommandManualCopy(button, "");
        try {
          await writeTextToClipboard(command);
          setAgentEntryCopyStatus(button, pickText({
            zh: "命令已复制。回到同一 Agent 会话粘贴运行。",
            en: "Command copied. Paste it in the same Agent session.",
          }));
        } catch (_) {
          renderAgentEntryCommandManualCopy(button, command);
          setAgentEntryCopyStatus(button, pickText({
            zh: "浏览器未允许自动复制；请手动复制下面的 /loopora-run 命令。",
            en: "The browser blocked automatic copy; copy the /loopora-run command below manually.",
          }));
        }
      });
    });
  }

  const RECOVERY_ACTION_LABELS = {
    create_workdir: {zh: "创建项目目录", en: "Create project directory"},
    choose_workdir: {zh: "选择项目目录", en: "Choose project directory"},
    confirm_readiness: {zh: "确认就绪状态", en: "Confirm readiness"},
    create_spec: {zh: "创建 Spec 文件", en: "Create spec file"},
    choose_spec: {zh: "选择 Spec 文件", en: "Choose spec file"},
    retry_web_compose: {zh: "重试当前表单", en: "Retry this form"},
    retry_web_run_start: {zh: "重试启动运行", en: "Retry run start"},
    retry_run_start: {zh: "重试启动运行", en: "Retry run start"},
    refresh_run_detail: {zh: "刷新运行状态", en: "Refresh run status"},
    review_source_bundle: {zh: "查看来源 Plan File", en: "Review source Plan File"},
    review_source_run: {zh: "查看来源运行", en: "Review source run"},
    retry_revision_session: {zh: "重试改进会话", en: "Retry revision session"},
    review_alignment_source_context: {zh: "重新检查来源上下文", en: "Review source context"},
    retry_alignment_session_create: {zh: "重试创建对话", en: "Retry conversation start"},
    review_alignment_bundle: {zh: "查看候选 Plan File", en: "Review candidate Plan File"},
    sync_alignment_bundle: {zh: "同步候选 Plan File", en: "Sync candidate Plan File"},
    retry_alignment_bundle_preview: {zh: "重试预览", en: "Retry preview"},
    retry_alignment_import: {zh: "重试创建 Loop", en: "Retry Loop creation"},
    open_support: {zh: "打开支持与诊断", en: "Open support and diagnostics"},
    review_plan_file: {zh: "查看 Plan File", en: "Review Plan File"},
    retry_plan_file_export: {zh: "重试导出", en: "Retry export"},
    open_plan_file_library: {zh: "打开 Plan File 列表", en: "Open Plan File library"},
    fix_asset_fields: {zh: "修复字段", en: "Fix fields"},
    retry_web_asset_save: {zh: "重试保存", en: "Retry save"},
  };

  const RECOVERY_ACTION_HINTS = {
    create_workdir: {zh: "先在服务端创建目标项目目录。", en: "Create the target project directory on the server first."},
    choose_workdir: {zh: "换成一个可读取的项目目录。", en: "Choose a readable project directory."},
    confirm_readiness: {zh: "目录修复后运行只读检查确认状态。", en: "After fixing the directory, run the read-only readiness check."},
    create_spec: {zh: "先生成一个可编辑的 Spec 草稿。", en: "Create an editable spec draft first."},
    choose_spec: {zh: "换成一个可读取的 Markdown Spec 文件。", en: "Choose a readable Markdown spec file."},
    retry_web_compose: {zh: "修复后重新提交当前表单。", en: "Submit this form again after fixing the setup."},
    retry_web_run_start: {zh: "目录就绪后，重试启动运行。", en: "After the directory is ready, retry the run start."},
    retry_run_start: {zh: "目录就绪后，重试启动运行。", en: "After the directory is ready, retry the run start."},
    refresh_run_detail: {
      zh: "当前页面的运行动作已经过期；刷新后查看最新结果和下一步。",
      en: "The run action on this page is stale; refresh to see the latest result and next step.",
    },
    review_source_bundle: {
      zh: "回到来源 Plan File，确认它仍是要改进的对象。",
      en: "Return to the source Plan File and confirm it is still the revision target.",
    },
    review_source_run: {
      zh: "回到来源运行，确认要基于这次证据继续改进。",
      en: "Return to the source run and confirm this evidence is still the revision target.",
    },
    retry_revision_session: {
      zh: "确认来源后重新发起改进会话。",
      en: "After reviewing the source, start the revision session again.",
    },
    review_alignment_source_context: {
      zh: "重新检查当前项目里可继续、可改进或可重新生成的来源。",
      en: "Review the current project's continue, improve, or regenerate source choices.",
    },
    retry_alignment_session_create: {
      zh: "确认来源后重新创建 Web 对话。",
      en: "After reviewing the source, start the Web conversation again.",
    },
    review_alignment_bundle: {
      zh: "回到 READY 候选方案，确认源文件仍是要创建的 Loop。",
      en: "Return to the READY candidate and confirm the source file is still the Loop to create.",
    },
    sync_alignment_bundle: {
      zh: "修复候选源文件后重新读取并校验它。",
      en: "After repairing the candidate source file, reload and validate it.",
    },
    retry_alignment_bundle_preview: {
      zh: "同步通过后重新打开候选方案预览。",
      en: "After the sync passes, reopen the candidate preview.",
    },
    retry_alignment_import: {
      zh: "确认候选方案后再次创建 Loop。",
      en: "After reviewing the candidate, create the Loop again.",
    },
    open_support: {
      zh: "查看本地诊断和公开求助边界。",
      en: "Review local diagnostics and public support boundaries.",
    },
    review_plan_file: {
      zh: "检查这个 Plan File 是否仍可作为导出来源。",
      en: "Check whether this Plan File is still a usable export source.",
    },
    retry_plan_file_export: {
      zh: "确认来源后重新请求导出。",
      en: "After reviewing the source, request the export again.",
    },
    open_plan_file_library: {
      zh: "回到 Plan File 列表选择其他可用方案。",
      en: "Return to the Plan File library and choose another usable plan.",
    },
    fix_asset_fields: {
      zh: "回到被标记的字段，先修正验证失败的内容。",
      en: "Return to the highlighted fields and fix the validation issue first.",
    },
    retry_web_asset_save: {
      zh: "字段修复后重新提交当前保存动作。",
      en: "After fixing the fields, submit the current save action again.",
    },
  };

  function recoveryActionKind(action) {
    return String(action?.kind || "").trim();
  }

  function recoveryActionFallback(kind, fallback) {
    return kind.replaceAll("_", " ") || fallback;
  }

  function recoveryActionLabel(action) {
    const kind = recoveryActionKind(action);
    const label = RECOVERY_ACTION_LABELS[kind];
    return label ? pickText(label) : recoveryActionFallback(kind, pickText({zh: "下一步", en: "Next action"}));
  }

  function recoveryActionHint(action) {
    const note = String(action?.note || "").trim();
    if (note) {
      return note;
    }
    const kind = recoveryActionKind(action);
    const hint = RECOVERY_ACTION_HINTS[kind];
    return hint ? pickText(hint) : pickText({zh: "完成这一步后再继续。", en: "Complete this step before continuing."});
  }

  function recoveryActionLinkLabel(action) {
    return recoveryActionKind(action) === "refresh_run_detail"
      ? pickText({zh: "刷新页面", en: "Refresh page"})
      : pickText({zh: "打开", en: "Open"});
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function recoveryActionOptionValue(option, action) {
    return typeof option === "function" ? option(action) : option;
  }

  const SENSITIVE_REDIRECT_QUERY_KEYS = new Set([
    "access_token",
    "api_key",
    "auth_token",
    "id_token",
    "refresh_token",
    "token",
    "x_loopora_token",
    "x-loopora-token",
  ]);
  const LOCAL_REDIRECT_QUERY_VALUE_KEYS = new Set(["return_to"]);

  function safeLocalRecoveryUrl(value) {
    const target = String(value || "").trim();
    if (!target || target.includes("\\") || /[\u0000-\u001f\u007f]/u.test(target)) {
      return "";
    }
    if (!target.startsWith("/") || target.startsWith("//")) {
      return "";
    }

    let parsed;
    try {
      parsed = new URL(target, window.location?.origin || "http://loopora.local");
    } catch (_) {
      return "";
    }
    if (parsed.origin !== (window.location?.origin || parsed.origin)) {
      return "";
    }

    const query = new URLSearchParams();
    parsed.searchParams.forEach((itemValue, itemKey) => {
      const normalizedKey = String(itemKey || "").trim().toLowerCase();
      if (SENSITIVE_REDIRECT_QUERY_KEYS.has(normalizedKey)) {
        return;
      }
      if (LOCAL_REDIRECT_QUERY_VALUE_KEYS.has(normalizedKey)) {
        const nestedTarget = safeLocalRecoveryUrl(itemValue);
        if (nestedTarget) {
          query.append(itemKey, nestedTarget);
        }
        return;
      }
      query.append(itemKey, itemValue);
    });
    const queryString = query.toString();
    return `${parsed.pathname || "/"}${queryString ? `?${queryString}` : ""}${safeRedirectHash(parsed.hash)}`;
  }

  function safeRedirectHash(hash) {
    const fragment = String(hash || "").replace(/^#/, "");
    if (!fragment || !fragment.includes("=")) {
      return hash || "";
    }
    const params = new URLSearchParams(fragment);
    const cleaned = new URLSearchParams();
    let removedSensitive = false;
    params.forEach((itemValue, itemKey) => {
      const normalizedKey = String(itemKey || "").trim().toLowerCase();
      if (SENSITIVE_REDIRECT_QUERY_KEYS.has(normalizedKey)) {
        removedSensitive = true;
        return;
      }
      cleaned.append(itemKey, itemValue);
    });
    if (!removedSensitive) {
      return hash || "";
    }
    const cleanedHash = cleaned.toString();
    return cleanedHash ? `#${cleanedHash}` : "";
  }

  function safeLocalRedirectUrl(value, fallback = "/") {
    return safeLocalRecoveryUrl(value) || safeLocalRecoveryUrl(fallback) || "/";
  }

  function contextPreservingRecoveryUrl(value) {
    const safeValue = safeLocalRecoveryUrl(value);
    return safeValue ? contextPreservingRedirectUrl(safeValue, safeValue) : "";
  }

  function currentLocalReturnPath() {
    let current;
    try {
      current = new URL(window.location?.href || "/", window.location?.origin || "http://loopora.local");
    } catch (_) {
      return "";
    }
    const path = `${current.pathname || "/"}${current.search || ""}${current.hash || ""}`;
    const safePath = safeLocalRecoveryUrl(path);
    if (!safePath) {
      return "";
    }
    try {
      const safeUrl = new URL(safePath, window.location?.origin || "http://loopora.local");
      if (safeUrl.pathname === "/support") {
        return "";
      }
    } catch (_) {
      return "";
    }
    return safePath;
  }

  function supportRecoveryUrlWithReturnTo(value) {
    const safeValue = safeLocalRecoveryUrl(value);
    if (!safeValue) {
      return "";
    }
    let url;
    try {
      url = new URL(safeValue, window.location?.origin || "http://loopora.local");
    } catch (_) {
      return safeValue;
    }
    if (url.pathname !== "/support" || url.searchParams.has("return_to")) {
      return safeValue;
    }
    const returnTo = currentLocalReturnPath();
    if (returnTo) {
      url.searchParams.set("return_to", returnTo);
    }
    return `${url.pathname}${url.search}${url.hash}`;
  }

  function recoveryRedirectUrl(action) {
    const redirectUrl = contextPreservingRecoveryUrl(action?.redirect_url);
    if (!redirectUrl || recoveryActionKind(action) !== "open_support") {
      return redirectUrl;
    }
    return supportRecoveryUrlWithReturnTo(redirectUrl);
  }

  function contextPreservingRedirectUrl(value, fallback = "/") {
    const redirectUrl = safeLocalRedirectUrl(value, fallback);
    let target;
    let current;
    try {
      target = new URL(redirectUrl, window.location?.origin || "http://loopora.local");
      current = new URL(window.location?.href || "/", window.location?.origin || "http://loopora.local");
    } catch (_) {
      return redirectUrl;
    }
    if (target.searchParams.has("workdir") || target.searchParams.has("alignment_workdir")) {
      return `${target.pathname}${target.search}${target.hash}`;
    }
    ["workdir", "alignment_workdir"].forEach((key) => {
      if (target.searchParams.has(key)) {
        return;
      }
      const contextValue = current.searchParams.get(key);
      if (contextValue) {
        target.searchParams.set(key, contextValue);
      }
    });
    return `${target.pathname}${target.search}${target.hash}`;
  }

  function localUrlWithQueryParam(value, key, paramValue) {
    const safeValue = safeLocalRecoveryUrl(value);
    if (!safeValue || !key || !paramValue) {
      return safeValue || "";
    }
    try {
      const url = new URL(safeValue, window.location.origin);
      url.searchParams.set(key, paramValue);
      return `${url.pathname}${url.search}${url.hash}`;
    } catch (_) {
      return safeValue;
    }
  }

  function assetSaveRedirectUrl(payload, options = {}) {
    const returnTo = String(options.returnTo || "").trim();
    const surfaceUpdated = String(options.surfaceUpdated || "").trim();
    const targetWorkdir = String(options.workdir || currentWorkdirContext()).trim();
    const withTargetContext = (url) => (targetWorkdir ? workdirContextHref(url, targetWorkdir) : url);
    const returnRedirect = localUrlWithQueryParam(returnTo, "surface_updated", surfaceUpdated);
    if (returnRedirect) {
      return withTargetContext(returnRedirect);
    }
    const redirectUrl = safeLocalRecoveryUrl(payload?.redirect_url);
    if (redirectUrl && options.savedParam !== false) {
      const redirectWithFeedback = localUrlWithQueryParam(redirectUrl, "saved", "1") || redirectUrl;
      return withTargetContext(redirectWithFeedback);
    }
    return withTargetContext(safeLocalRedirectUrl(redirectUrl, options.fallback || "/"));
  }

  function controlTagName(control) {
    return String(control?.tagName || control?.nodeName || "").toUpperCase();
  }

  function isAnchorControl(control) {
    return (typeof HTMLAnchorElement === "function" && control instanceof HTMLAnchorElement)
      || controlTagName(control) === "A";
  }

  function isButtonControl(control) {
    return (typeof HTMLButtonElement === "function" && control instanceof HTMLButtonElement)
      || controlTagName(control) === "BUTTON";
  }

  function isNavigationControlLike(control) {
    return Boolean(
      control
      && typeof control === "object"
      && control.dataset
      && control.classList
      && typeof control.setAttribute === "function"
      && typeof control.removeAttribute === "function"
      && typeof control.getAttribute === "function"
      && typeof control.hasAttribute === "function",
    );
  }

  function setNavigationControlBlocked(control, blocked, options = {}) {
    if (!isNavigationControlLike(control)) {
      return;
    }
    const markerDataset = String(options.markerDataset || "navigationBlocked");
    const baseHrefDataset = String(options.baseHrefDataset || "navigationBaseHref");
    const disabledHrefDataset = String(options.disabledHrefDataset || "navigationDisabledHref");
    const baseDisabledDataset = String(options.baseDisabledDataset || "navigationBaseDisabled");
    const disabledClass = String(options.disabledClass || "is-disabled");
    const shouldRemoveHref = options.removeHref !== false;
    const shouldDisableButton = options.disableButton !== false;
    const anchor = shouldRemoveHref && isAnchorControl(control);
    const button = shouldDisableButton && isButtonControl(control);

    if (anchor && control.dataset[baseHrefDataset] === undefined) {
      control.dataset[baseHrefDataset] = control.getAttribute("href") || "";
    }
    if (button && control.dataset[baseDisabledDataset] === undefined) {
      control.dataset[baseDisabledDataset] = control.disabled ? "true" : "false";
    }

    if (!blocked) {
      control.classList.remove(disabledClass);
      control.setAttribute("aria-disabled", "false");
      control.removeAttribute("tabindex");
      delete control.dataset[markerDataset];
      if (button) {
        control.disabled = control.dataset[baseDisabledDataset] === "true";
      }
      if (anchor) {
        const disabledHref = control.dataset[disabledHrefDataset] || "";
        if (disabledHref) {
          control.setAttribute("href", disabledHref);
        } else if (!control.hasAttribute("href") && control.dataset[baseHrefDataset]) {
          control.setAttribute("href", control.dataset[baseHrefDataset]);
        }
        delete control.dataset[disabledHrefDataset];
      }
      return;
    }

    control.classList.add(disabledClass);
    control.setAttribute("aria-disabled", "true");
    control.setAttribute("tabindex", "-1");
    control.dataset[markerDataset] = "true";
    if (button) {
      control.disabled = true;
    }
    if (anchor) {
      const href = control.getAttribute("href") || control.dataset[disabledHrefDataset] || control.dataset[baseHrefDataset] || "";
      if (href) {
        control.dataset[disabledHrefDataset] = href;
      }
      control.removeAttribute("href");
    }
  }

  const NAVIGATION_CONTROL_HREF_DATASET_KEYS = [
    "navigationDisabledHref",
    "directPathDisabledHref",
    "disabledHref",
    "navigationBaseHref",
    "directPathBaseHref",
    "handoffBaseHref",
    "enabledHref",
  ];
  const NAVIGATION_CONTEXT_LINK_SELECTOR = [
    "a[href]",
    "a[data-navigation-disabled-href]",
    "a[data-direct-path-disabled-href]",
    "a[data-disabled-href]",
  ].join(", ");

  function navigationControlHref(control) {
    if (!isNavigationControlLike(control)) {
      return "";
    }
    const href = control.getAttribute("href") || "";
    if (href) {
      return href;
    }
    for (const key of NAVIGATION_CONTROL_HREF_DATASET_KEYS) {
      const value = control.dataset[key] || "";
      if (value) {
        return value;
      }
    }
    return "";
  }

  function setNavigationControlHref(control, href) {
    if (!isNavigationControlLike(control)) {
      return;
    }
    const value = String(href || "");
    if (control.hasAttribute("href")) {
      control.setAttribute("href", value);
      return;
    }
    for (const key of NAVIGATION_CONTROL_HREF_DATASET_KEYS) {
      if (control.dataset[key] !== undefined) {
        control.dataset[key] = value;
        return;
      }
    }
    control.setAttribute("href", value);
  }

  function isWorkdirFormLike(targetForm) {
    return Boolean(
      targetForm
      && typeof targetForm === "object"
      && targetForm.dataset
      && typeof targetForm.getAttribute === "function"
      && (
        (typeof HTMLFormElement === "function" && targetForm instanceof HTMLFormElement)
        || controlTagName(targetForm) === "FORM"
      ),
    );
  }

  function normalizeWorkdirContextMode(mode) {
    const value = String(mode || "").trim();
    return value === "workdir" || value === "alignment_workdir" ? value : "";
  }

  function workdirContextModeForUrl(url, preferredParam = "") {
    const forced = normalizeWorkdirContextMode(preferredParam);
    if (forced) {
      return forced;
    }
    if (url.searchParams.has("alignment_workdir") && !url.searchParams.has("workdir")) {
      return "alignment_workdir";
    }
    if (url.searchParams.has("workdir") || url.searchParams.has("return_to")) {
      return "workdir";
    }
    return "";
  }

  function workdirContextLooksServerAbsolute(value) {
    const path = String(value || "").trim();
    return path.startsWith("/") || /^[A-Za-z]:[\\/]/.test(path) || path.startsWith("\\\\");
  }

  function safeWorkdirContextValue(value) {
    const path = String(value || "").trim();
    return workdirContextLooksServerAbsolute(path) ? path : "";
  }

  function workdirContextValueForUrl(url) {
    return String(url.searchParams.get("workdir") || url.searchParams.get("alignment_workdir") || "").trim();
  }

  function preservesDemoPlaygroundTarget(url) {
    const playgroundWorkdir = safeWorkdirContextValue(document.body?.dataset.demoPlaygroundWorkdir || "");
    const targetWorkdir = safeWorkdirContextValue(workdirContextValueForUrl(url));
    return Boolean(
      playgroundWorkdir
      && targetWorkdir
      && sameWorkdir(playgroundWorkdir, targetWorkdir, {allowEmptyLeft: false, allowEmptyRight: false})
    );
  }

  function projectScopeRoot() {
    return document.querySelector("[data-project-scope-root]");
  }

  function projectScopeRequiresAllMarker() {
    return projectScopeRoot()?.dataset?.projectScopeRequiresAllMarker === "true";
  }

  function projectScopeIsAll() {
    const root = projectScopeRoot();
    if (!root) {
      return false;
    }
    return !safeWorkdirContextValue(root.dataset.currentWorkdir || "");
  }

  function applyAllProjectsScopeToUrl(url) {
    clearWorkdirContextParams(url);
    if (projectScopeRequiresAllMarker()) {
      url.searchParams.set(PROJECT_SCOPE_QUERY_PARAM, ALL_PROJECTS_SCOPE);
    } else {
      url.searchParams.delete(PROJECT_SCOPE_QUERY_PARAM);
    }
  }

  function clearWorkdirContextParams(url) {
    url.searchParams.delete("workdir");
    url.searchParams.delete("alignment_workdir");
  }

  function applyWorkdirContextToUrl(url, workdir, mode, options = {}) {
    const targetMode = normalizeWorkdirContextMode(mode);
    if (!targetMode) {
      return false;
    }
    const value = safeWorkdirContextValue(workdir);
    if (value) {
      url.searchParams.set(targetMode, value);
      url.searchParams.delete(PROJECT_SCOPE_QUERY_PARAM);
    } else {
      url.searchParams.delete(targetMode);
      if (projectScopeIsAll() && projectScopeRequiresAllMarker()) {
        url.searchParams.set(PROJECT_SCOPE_QUERY_PARAM, ALL_PROJECTS_SCOPE);
      } else {
        url.searchParams.delete(PROJECT_SCOPE_QUERY_PARAM);
      }
    }
    url.searchParams.delete(targetMode === "alignment_workdir" ? "workdir" : "alignment_workdir");
    syncReturnToWorkdirContext(url, value, targetMode, options);
    return true;
  }

  function currentWorkdirContext() {
    const contextCode = document.querySelector("[data-testid='global-workdir-context'] code");
    const renderedContext = String(contextCode?.textContent || "").trim();
    if (renderedContext) {
      return renderedContext;
    }
    try {
      const url = new URL(window.location.href);
      return safeWorkdirContextValue(workdirContextValueForUrl(url));
    } catch (_) {
      return "";
    }
  }

  function workdirContextHref(href, workdir = "", preferredParam = "workdir") {
    const targetWorkdir = safeWorkdirContextValue(workdir || currentWorkdirContext());
    try {
      const url = new URL(String(href || ""), window.location.origin);
      if (url.origin !== window.location.origin) {
        return String(href || "");
      }
      const existingWorkdir = workdirContextValueForUrl(url);
      if (existingWorkdir) {
        if (safeWorkdirContextValue(existingWorkdir)) {
          if (url.searchParams.has(PROJECT_SCOPE_QUERY_PARAM)) {
            url.searchParams.delete(PROJECT_SCOPE_QUERY_PARAM);
          }
          return `${url.pathname}${url.search}${url.hash}`;
        }
        clearWorkdirContextParams(url);
      }
      const mode = normalizeWorkdirContextMode(preferredParam) || "workdir";
      applyWorkdirContextToUrl(url, targetWorkdir, mode, {preserveNestedContext: true});
      return `${url.pathname}${url.search}${url.hash}`;
    } catch (_) {
      return String(href || "");
    }
  }

  function workdirContextRedirectUrl(value, {fallback = "/", workdir = "", preferredParam = "workdir"} = {}) {
    return workdirContextHref(safeLocalRedirectUrl(value, fallback), workdir, preferredParam);
  }

  function syncWorkdirFormAction(targetForm, workdir, preferredParam = "workdir") {
    if (!isWorkdirFormLike(targetForm)) {
      return;
    }
    try {
      const url = new URL(targetForm.getAttribute("action") || targetForm.action, window.location.origin);
      if (url.origin !== window.location.origin) {
        return;
      }
      const mode = normalizeWorkdirContextMode(preferredParam) || "workdir";
      if (applyWorkdirContextToUrl(url, workdir, mode)) {
        targetForm.action = `${url.pathname}${url.search}${url.hash}`;
      }
    } catch (_) {
      // Keep the server-rendered action if it cannot be parsed.
    }
  }

  function syncWorkdirFormContext(targetForm, workdir, preferredParam = "workdir") {
    syncWorkdirFormAction(targetForm, workdir, preferredParam);
    if (!targetForm?.dataset) {
      return;
    }
    if (String(targetForm.dataset.apiAction || "").trim()) {
      syncWorkdirDatasetUrl(targetForm, "apiAction", workdir, preferredParam);
    }
    if (String(targetForm.dataset.returnTo || "").trim()) {
      syncWorkdirDatasetUrl(targetForm, "returnTo", workdir, preferredParam);
    }
  }

  function syncWorkdirFormActionControl(control, workdir, preferredParam = "workdir") {
    if (!control?.dataset || typeof control.getAttribute !== "function" || typeof control.setAttribute !== "function") {
      return;
    }
    const action = String(control.getAttribute("formaction") || "").trim();
    if (!action) {
      return;
    }
    try {
      const url = new URL(action, window.location.origin);
      if (url.origin !== window.location.origin) {
        return;
      }
      const mode = normalizeWorkdirContextMode(preferredParam) || workdirContextModeForUrl(url, preferredParam);
      if (!mode || !applyWorkdirContextToUrl(url, workdir, mode)) {
        return;
      }
      control.setAttribute("formaction", `${url.pathname}${url.search}${url.hash}`);
    } catch (_) {
      // Keep the server-rendered action if it cannot be parsed.
    }
  }

  function syncWorkdirDatasetUrl(element, datasetKey, workdir, preferredParam = "", options = {}) {
    if (!element?.dataset || element.dataset[datasetKey] === undefined) {
      return;
    }
    try {
      const url = new URL(element.dataset[datasetKey] || "", window.location.origin);
      if (url.origin !== window.location.origin) {
        return;
      }
      if (
        options.preserveTargetContext
        && (url.searchParams.has("workdir") || url.searchParams.has("alignment_workdir"))
      ) {
        return;
      }
      const mode = workdirContextModeForUrl(url, preferredParam);
      if (!mode || !applyWorkdirContextToUrl(url, workdir, mode, options)) {
        return;
      }
      element.dataset[datasetKey] = `${url.pathname}${url.search}${url.hash}`;
    } catch (_) {
      // Keep the server-rendered dataset URL if it cannot be parsed.
    }
  }

  function syncWorkdirContextDatasetUrls(element, workdir) {
    const specs = String(element?.dataset?.workdirContextDatasetUrls || "").trim().split(/\s+/).filter(Boolean);
    specs.forEach((spec) => {
      const [rawDatasetKey, rawMode] = spec.split(":");
      const datasetKey = String(rawDatasetKey || "").trim();
      const mode = normalizeWorkdirContextMode(rawMode);
      if (!datasetKey || !mode) {
        return;
      }
      syncWorkdirDatasetUrl(element, datasetKey, workdir, mode);
    });
  }

  function navigationControlIsBlocked(control) {
    return Boolean(
      isNavigationControlLike(control)
      && (
        control.getAttribute("aria-disabled") === "true"
        || control.dataset.navigationBlocked === "true"
        || control.dataset.directPathBlocked === "true"
        || control.dataset.fitHandoffDisabled === "true"
        || control.dataset.createChoiceRouteBlocked === "true"
      ),
    );
  }

  function comparableWorkdir(value) {
    const path = String(value || "").trim().replace(/\s+/g, " ").replace(/\/+$/, "");
    if (path === "/private/tmp") {
      return "/tmp";
    }
    if (path.startsWith("/private/tmp/")) {
      return `/tmp/${path.slice("/private/tmp/".length)}`;
    }
    return path;
  }

  function sameWorkdir(left, right, {allowEmptyLeft = true, allowEmptyRight = true} = {}) {
    const normalizedLeft = comparableWorkdir(left);
    const normalizedRight = comparableWorkdir(right);
    if (!normalizedLeft) {
      return Boolean(allowEmptyLeft);
    }
    if (!normalizedRight) {
      return Boolean(allowEmptyRight);
    }
    return normalizedLeft === normalizedRight;
  }

  function tutorialFitPrefersDirectPath(payload) {
    const setupBlockers = Array.isArray(payload?.setup_command_blockers)
      ? payload.setup_command_blockers.map((blocker) => String(blocker || "").trim().replace(/\s+/g, " ")).filter(Boolean)
      : [];
    return Boolean(
      payload?.prefer_direct_path === true
      || payload?.fit_decision === "prefer_direct_path"
      || payload?.setup_gate === "direct_path_selected"
      || payload?.setup_blocker === "prefer_direct_path"
      || setupBlockers.includes("prefer_direct_path")
    );
  }

  function tutorialFitSetupCommandState(payload, {missingInputIds = [], setupAllowed = true, sourceWorkdir = ""} = {}) {
    if (tutorialFitPrefersDirectPath(payload)) {
      return {
        setupGateReady: false,
        setupGateBlockers: ["prefer_direct_path"],
        setupCommandsReady: false,
        setupCommandBlockers: ["prefer_direct_path"],
        routePreviewExecutable: false,
        routePreviewBlockers: ["prefer_direct_path"],
      };
    }
    const setupGateBlockers = Array.isArray(payload?.setup_gate_blockers)
      ? payload.setup_gate_blockers.map((blocker) => String(blocker || "").trim().replace(/\s+/g, " ")).filter(Boolean)
      : [];
    const blockers = new Set(
      setupGateBlockers.concat(Array.isArray(payload?.setup_command_blockers)
        ? payload.setup_command_blockers.map((blocker) => String(blocker || "").trim().replace(/\s+/g, " ")).filter(Boolean)
        : []),
    );
    if (!setupAllowed || missingInputIds.length > 0) {
      blockers.add("review_inputs_required");
    }
    if (!String(sourceWorkdir || "").trim()) {
      blockers.add("target_project_required");
    }
    const setupCommandBlockers = Array.from(blockers);
    const payloadRoutePreviewBlockers = Array.isArray(payload?.route_preview_blockers)
      ? payload.route_preview_blockers.map((blocker) => String(blocker || "").trim().replace(/\s+/g, " ")).filter(Boolean)
      : setupCommandBlockers;
    const setupGateReady = setupCommandBlockers.length === 0
      && payload?.setup_gate_ready !== false
      && payload?.setup_commands_ready !== false;
    const setupCommandsReady = setupGateReady;
    const routePreviewExecutable = setupCommandsReady
      && payloadRoutePreviewBlockers.length === 0
      && payload?.route_preview_executable !== false;
    return {
      setupGateReady,
      setupGateBlockers: setupGateReady ? [] : setupCommandBlockers,
      setupCommandsReady,
      setupCommandBlockers,
      routePreviewExecutable,
      routePreviewBlockers: routePreviewExecutable ? [] : payloadRoutePreviewBlockers,
    };
  }

  function syncProjectScopeDisplay(value) {
    const root = projectScopeRoot();
    if (!root) {
      return;
    }
    root.dataset.currentWorkdir = value;
    root.dataset.projectScopeExplicitAll = value ? "false" : "true";
    const allState = root.querySelector("[data-project-scope-all-state]");
    if (allState) {
      allState.hidden = Boolean(value);
    }
    root.querySelectorAll("[data-project-scope-option]").forEach((option) => {
      const optionWorkdir = safeWorkdirContextValue(option.dataset.projectScopeOption || "");
      const current = optionWorkdir
        ? sameWorkdir(optionWorkdir, value, {allowEmptyLeft: false, allowEmptyRight: false})
        : !value;
      if (current) {
        option.setAttribute("aria-current", "true");
      } else {
        option.removeAttribute("aria-current");
      }
    });
  }

  function syncReturnToWorkdirContext(url, workdir, preferredParam = "workdir", options = {}) {
    const returnTo = url.searchParams.get("return_to");
    if (!returnTo) {
      return;
    }
    const safeReturnTo = safeLocalRecoveryUrl(returnTo);
    if (!safeReturnTo) {
      url.searchParams.delete("return_to");
      return;
    }
    let nestedUrl;
    try {
      nestedUrl = new URL(safeReturnTo, window.location.origin);
    } catch (_) {
      return;
    }
    const hasNestedContext = nestedUrl.searchParams.has("workdir") || nestedUrl.searchParams.has("alignment_workdir");
    if (options.preserveNestedContext && hasNestedContext) {
      if (safeWorkdirContextValue(workdirContextValueForUrl(nestedUrl))) {
        url.searchParams.set("return_to", `${nestedUrl.pathname}${nestedUrl.search}${nestedUrl.hash}`);
        return;
      }
      clearWorkdirContextParams(nestedUrl);
    }
    const useAlignmentParam = nestedUrl.searchParams.has("alignment_workdir") && !nestedUrl.searchParams.has("workdir");
    const targetParam = useAlignmentParam || preferredParam === "alignment_workdir" ? "alignment_workdir" : "workdir";
    const value = safeWorkdirContextValue(workdir);
    if (value) {
      nestedUrl.searchParams.set(targetParam, value);
      nestedUrl.searchParams.delete(targetParam === "alignment_workdir" ? "workdir" : "alignment_workdir");
      nestedUrl.searchParams.delete(PROJECT_SCOPE_QUERY_PARAM);
    } else {
      applyAllProjectsScopeToUrl(nestedUrl);
    }
    url.searchParams.set("return_to", `${nestedUrl.pathname}${nestedUrl.search}${nestedUrl.hash}`);
  }

  function syncWorkdirContext(workdir, {syncUrl = false, urlParam = ""} = {}) {
    const value = safeWorkdirContextValue(workdir);
    const forcedUrlParam = ["workdir", "alignment_workdir"].includes(String(urlParam || "").trim())
      ? String(urlParam || "").trim()
      : "";
    const context = document.querySelector("[data-testid='global-workdir-context']");
    const code = context?.querySelector("code");
    syncProjectScopeDisplay(value);
    if (context && code) {
      code.textContent = value;
      code.title = value;
      context.hidden = !value;
    }
    document.querySelectorAll("[data-current-workdir]").forEach((element) => {
      element.dataset.currentWorkdir = value;
    });
    document.querySelectorAll(NAVIGATION_CONTEXT_LINK_SELECTOR).forEach((link) => {
      try {
        const href = navigationControlHref(link);
        if (!href) {
          return;
        }
        const url = new URL(href, window.location.origin);
        if (url.origin !== window.location.origin) {
          return;
        }
        if (preservesDemoPlaygroundTarget(url)) {
          return;
        }
        const preferredMode = link.hasAttribute("data-agent-adapter-workdir-context-link")
          ? "workdir"
          : String(link.dataset.workdirContextLink || "").trim();
        const mode = workdirContextModeForUrl(url, preferredMode);
        if (!mode || !applyWorkdirContextToUrl(url, value, mode)) {
          return;
        }
        setNavigationControlHref(link, `${url.pathname}${url.search}${url.hash}`);
      } catch (_) {
        // Keep the server-rendered link if the href cannot be parsed.
      }
    });
    document.querySelectorAll("[data-open-card]").forEach((card) => {
      const mode = String(card.dataset.workdirContextOpenCard || "").trim();
      const isContextCard = Boolean(normalizeWorkdirContextMode(mode));
      syncWorkdirDatasetUrl(card, "openCard", value, mode, {
        preserveNestedContext: !isContextCard,
        preserveTargetContext: !isContextCard,
      });
    });
    document.querySelectorAll("[data-workdir-context-dataset-urls]").forEach((element) => {
      syncWorkdirContextDatasetUrls(element, value);
    });
    document.querySelectorAll("form[data-workdir-context-form]").forEach((targetForm) => {
      const mode = String(targetForm.dataset.workdirContextForm || "").trim();
      syncWorkdirFormContext(targetForm, value, mode);
    });
    document.querySelectorAll("[data-workdir-context-formaction]").forEach((control) => {
      const mode = String(control.dataset.workdirContextFormaction || "").trim();
      syncWorkdirFormActionControl(control, value, mode);
    });
    bindActiveAlignmentComposerReturnLinks();
    if (!syncUrl) {
      document.dispatchEvent(new CustomEvent("loopora:workdirchange", {detail: {workdir: value}}));
      return;
    }
    const url = new URL(window.location.href);
    const useAlignmentParam = forcedUrlParam
      ? forcedUrlParam === "alignment_workdir"
      : url.searchParams.has("alignment_workdir") && !url.searchParams.has("workdir");
    url.searchParams.delete("alignment_session_id");
    if (useAlignmentParam) {
      if (value) {
        url.searchParams.set("alignment_workdir", value);
        url.searchParams.delete(PROJECT_SCOPE_QUERY_PARAM);
      } else {
        url.searchParams.delete("alignment_workdir");
        applyAllProjectsScopeToUrl(url);
      }
      url.searchParams.delete("workdir");
    } else {
      if (value) {
        url.searchParams.set("workdir", value);
        url.searchParams.delete(PROJECT_SCOPE_QUERY_PARAM);
      } else {
        url.searchParams.delete("workdir");
        applyAllProjectsScopeToUrl(url);
      }
      url.searchParams.delete("alignment_workdir");
    }
    window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
    document.dispatchEvent(new CustomEvent("loopora:workdirchange", {detail: {workdir: value}}));
  }

  function setRecoveryCommandCopyStatus(button, message, kind = "") {
    const panel = button.closest("[data-recovery-panel]");
    const status = clearRecoveryCommandCopyStatus(panel);
    if (!status || !message) {
      return;
    }
    status.hidden = false;
    status.textContent = message;
    status.className = `field-status manual-recovery-status${kind ? ` is-${kind}` : ""}`;
    window.setTimeout(() => {
      if (status.textContent === message) {
        clearRecoveryCommandCopyStatus(panel);
      }
    }, 4200);
  }

  function clearRecoveryCommandCopyStatus(panel) {
    const status = panel?.querySelector("[data-recovery-copy-status]");
    if (!status) {
      return null;
    }
    status.hidden = true;
    status.textContent = "";
    status.className = "field-status manual-recovery-status";
    return status;
  }

  function renderRecoveryCommandManualCopy(button, command) {
    const panel = button?.closest?.("[data-recovery-panel]");
    const container = panel?.querySelector?.("[data-recovery-command-manual-copy]");
    const panelId = String(panel?.dataset?.testid || "recovery").replace(/[^a-zA-Z0-9_-]+/g, "-");
    return renderManualCopy(container, command, {
      label: pickText({
        zh: button?.dataset?.copyManualLabelZh || "手动复制恢复命令",
        en: button?.dataset?.copyManualLabelEn || "Manual recovery command copy",
      }),
      textareaId: `${panelId}-recovery-command-manual-copy-textarea`,
      rows: 4,
    });
  }

  function createRecoveryCommandCopyFragment(command, options = {}) {
    const text = String(command || "").trim();
    const root = options.document || document;
    const fragment = root.createDocumentFragment();
    if (!text) {
      return fragment;
    }

    const code = root.createElement("code");
    code.textContent = text;
    fragment.append(code);

    const button = root.createElement("button");
    button.type = "button";
    button.className = "ghost-button";
    button.dataset.recoveryCommandCopy = "1";
    button.dataset.copyValue = text;
    button.textContent = options.label || pickText({zh: "复制命令", en: "Copy command"});
    fragment.append(button);
    return fragment;
  }

  function createRecoveryActionControlFragment(action, options = {}) {
    const root = options.document || document;
    const fragment = root.createDocumentFragment();
    const command = String(action?.command || "").trim();
    if (command) {
      fragment.append(createRecoveryCommandCopyFragment(command, options));
      return fragment;
    }
    const formId = String(action?.form_id || "").trim();
    const formMethod = String(action?.form_method || action?.method || "POST").trim().toUpperCase();
    if (formId && formMethod === "POST") {
      const button = root.createElement("button");
      button.type = "submit";
      button.className = "ghost-button";
      button.setAttribute("form", formId);
      const formAction = contextPreservingRecoveryUrl(action?.form_action);
      if (formAction) {
        button.setAttribute("formaction", formAction);
      }
      button.setAttribute("formmethod", "post");
      button.dataset.recoveryActionForm = "1";
      button.dataset.workdirContextFormaction = "workdir";
      button.textContent = options.formLabel || recoveryActionLabel(action);
      fragment.append(button);
      return fragment;
    }
    const redirectUrl = recoveryRedirectUrl(action);
    if (!redirectUrl) {
      return fragment;
    }
    const link = root.createElement("a");
    link.className = "ghost-button";
    link.href = redirectUrl;
    link.dataset.recoveryActionLink = "1";
    if (recoveryActionKind(action) === "refresh_run_detail") {
      link.dataset.runActionRecoveryLink = "1";
    }
    link.textContent = options.linkLabel || recoveryActionLinkLabel(action);
    fragment.append(link);
    return fragment;
  }

  function recoveryActionControlHtml(action, options = {}) {
    const command = String(action?.command || "").trim();
    if (command) {
      return `<code>${escapeHtml(command)}</code><button class="ghost-button" type="button" data-recovery-command-copy data-copy-value="${escapeHtml(command)}">${escapeHtml(options.label || pickText({zh: "复制命令", en: "Copy command"}))}</button>`;
    }
    const formId = String(action?.form_id || "").trim();
    const formMethod = String(action?.form_method || action?.method || "POST").trim().toUpperCase();
    if (formId && formMethod === "POST") {
      const formAction = contextPreservingRecoveryUrl(action?.form_action);
      const formActionAttribute = formAction ? ` formaction="${escapeHtml(formAction)}"` : "";
      const formLabel = options.formLabel || recoveryActionLabel(action);
      return `<button class="ghost-button" type="submit" form="${escapeHtml(formId)}"${formActionAttribute} formmethod="post" data-recovery-action-form data-workdir-context-formaction="workdir">${escapeHtml(formLabel)}</button>`;
    }
    const redirectUrl = recoveryRedirectUrl(action);
    if (redirectUrl) {
      const runActionLink = options.runActionRecoveryLink || recoveryActionKind(action) === "refresh_run_detail";
      const linkAttribute = runActionLink ? " data-run-action-recovery-link" : "";
      const linkLabel = options.linkLabel || recoveryActionLinkLabel(action);
      return `<a class="ghost-button" href="${escapeHtml(redirectUrl)}" data-recovery-action-link${linkAttribute}>${escapeHtml(linkLabel)}</a>`;
    }
    const emptyControlText = String(options.emptyControlText || "").trim();
    return emptyControlText ? `<span>${escapeHtml(emptyControlText)}</span>` : "";
  }

  function recoveryActionHtml(action, options = {}) {
    const kind = recoveryActionKind(action);
    const label = recoveryActionOptionValue(options.actionLabel, action) || recoveryActionLabel(action);
    const hint = recoveryActionOptionValue(options.actionHint, action) || recoveryActionHint(action);
    const customControl = String(recoveryActionOptionValue(options.actionControlHtml, action) || "").trim();
    const control = customControl || recoveryActionControlHtml(action, options);
    return `
        <div class="manual-recovery-action" data-recovery-action-kind="${escapeHtml(kind)}">
          <strong>${escapeHtml(label)}</strong>
          <span>${escapeHtml(hint)}</span>
          ${control}
        </div>
      `;
  }

  function recoveryPanelHtml(payload, options = {}) {
    const actions = Array.isArray(payload?.next_actions) ? payload.next_actions : [];
    if (!actions.length) {
      return "";
    }
    const title = String(options.title || "").trim();
    const summary = String(options.summary ?? payload?.summary ?? payload?.error ?? "").trim();
    const testid = String(options.testid || "").trim();
    const itemsTestid = String(options.itemsTestid || (testid ? `${testid}-items` : "")).trim();
    const itemsAttribute = itemsTestid ? ` data-testid="${escapeHtml(itemsTestid)}"` : "";
    const rows = actions.map((action) => recoveryActionHtml(action, options)).join("");
    return `
      <div class="manual-recovery-copy">
        ${title ? `<strong>${escapeHtml(title)}</strong>` : ""}
        ${summary ? `<p>${escapeHtml(summary)}</p>` : ""}
      </div>
      <div class="manual-recovery-actions"${itemsAttribute}>${rows}</div>
      <p class="field-status manual-recovery-status" data-recovery-copy-status aria-live="polite" hidden></p>
      <div class="manual-recovery-command-copy" data-recovery-command-manual-copy data-testid="recovery-command-manual-copy" hidden></div>
    `;
  }

  function setAssetStatus(element, message, kind = "") {
    if (!element) {
      return;
    }
    const text = String(message || "").trim();
    if (!text) {
      element.hidden = true;
      element.textContent = "";
      element.className = "field-status";
      return;
    }
    element.hidden = false;
    element.textContent = text;
    element.className = `field-status${kind ? ` is-${kind}` : ""}`;
  }

  function assetRecoveryFieldErrors(payload) {
    if (payload?.error_code !== "asset_validation_failed" || !Array.isArray(payload?.field_errors)) {
      return [];
    }
    return payload.field_errors
      .map((item) => ({
        field: String(item?.field || "").trim(),
        message: String(item?.message || payload?.error || "").trim(),
      }))
      .filter((item) => item.field && item.message);
  }

  function formControlByName(form, field) {
    return Array.from(form?.elements || []).find((element) => String(element?.name || "") === field) || null;
  }

  function recoveryTargetByField(form, field, options = {}) {
    const resolver = options.fieldTargets?.[field];
    if (typeof resolver === "function") {
      const resolved = resolver();
      if (resolved) {
        return resolved;
      }
    }
    const tagged = Array.from(form.querySelectorAll("[data-recovery-field]")).find((element) => (
      String(element.dataset.recoveryField || "").split(/\s+/).includes(field)
    ));
    return tagged || formControlByName(form, field);
  }

  function preserveAssetRecoveryDescription(target) {
    if (!target?.setAttribute) {
      return;
    }
    if (!Object.hasOwn(target.dataset || {}, "assetRecoveryDescribedby")) {
      target.dataset.assetRecoveryDescribedby = target.getAttribute("aria-describedby") || "";
    }
  }

  function restoreAssetRecoveryDescription(target) {
    if (!target?.setAttribute) {
      return;
    }
    const previous = target.dataset.assetRecoveryDescribedby || "";
    if (previous) {
      target.setAttribute("aria-describedby", previous);
    } else {
      target.removeAttribute("aria-describedby");
    }
    delete target.dataset.assetRecoveryDescribedby;
  }

  function isFieldControl(target) {
    const tag = String(target?.tagName || "").toLowerCase();
    return ["input", "select", "textarea", "button"].includes(tag);
  }

  function makeAssetFieldRecoveryNote(field, message, options = {}) {
    const note = document.createElement("small");
    const label = options.fieldLabels?.[field] || field.replaceAll("_", " ");
    note.className = "field-status is-error";
    note.dataset.assetFieldRecovery = "1";
    note.dataset.assetFieldRecoveryFor = field;
    note.textContent = `${label}: ${message}`;
    return note;
  }

  function describeAssetRecoveryTarget(target, note) {
    if (!target?.setAttribute || !note?.id) {
      return;
    }
    preserveAssetRecoveryDescription(target);
    const previous = target.getAttribute("aria-describedby") || "";
    const parts = previous.split(/\s+/).filter(Boolean);
    if (!parts.includes(note.id)) {
      parts.push(note.id);
    }
    target.setAttribute("aria-describedby", parts.join(" "));
  }

  function clearAssetFieldRecovery(form, options = {}) {
    if (!form) {
      return;
    }
    form.querySelectorAll("[data-asset-field-recovery]").forEach((node) => node.remove());
    form.querySelectorAll("[data-asset-field-recovery-list]").forEach((node) => node.remove());
    form.querySelectorAll("[data-asset-recovery-invalid]").forEach((target) => {
      target.removeAttribute("aria-invalid");
      restoreAssetRecoveryDescription(target);
      delete target.dataset.assetRecoveryInvalid;
    });
    if (options.clearStatus !== false) {
      setAssetStatus(options.statusElement || form.querySelector("[data-asset-form-error]"), "", "");
    }
  }

  function renderAssetFieldRecovery(form, payload, options = {}) {
    const fieldErrors = assetRecoveryFieldErrors(payload);
    if (!form || !fieldErrors.length) {
      return false;
    }
    clearAssetFieldRecovery(form, {statusElement: options.statusElement, clearStatus: false});
    const statusElement = options.statusElement || form.querySelector("[data-asset-form-error]");
    setAssetStatus(
      statusElement,
      payload.error || options.fallbackMessage || pickText({zh: "保存前需要修正字段。", en: "Fix the highlighted fields before saving."}),
      "error",
    );

    let firstTarget = null;
    fieldErrors.forEach((item, index) => {
      const target = recoveryTargetByField(form, item.field, options);
      if (!target) {
        return;
      }
      const note = makeAssetFieldRecoveryNote(item.field, item.message, options);
      note.id = `${options.noteIdPrefix || "asset-field-recovery"}-${index}`;
      target.insertAdjacentElement("afterend", note);
      target.dataset.assetRecoveryInvalid = "1";
      if (isFieldControl(target)) {
        target.setAttribute("aria-invalid", "true");
        describeAssetRecoveryTarget(target, note);
      }
      firstTarget ||= target;
    });

    if (firstTarget) {
      firstTarget.scrollIntoView?.({block: "center", behavior: "smooth"});
      if (typeof firstTarget.focus === "function" && isFieldControl(firstTarget)) {
        firstTarget.focus({preventScroll: true});
      }
    }
    renderAssetRecoveryActionPanel(form, payload, {
      ...options,
      recoveryFields: fieldErrors.map((item) => item.field),
    });
    return true;
  }

  function renderAssetRecoveryActionPanel(form, payload, options = {}) {
    const recoveryFields = Array.isArray(options.recoveryFields) ? options.recoveryFields : [];
    const actions = Array.isArray(payload?.next_actions)
      ? payload.next_actions.filter((action) => {
        const actionKind = recoveryActionKind(action);
        return actionKind === "fix_asset_fields"
          || actionKind === "retry_web_asset_save"
          || String(action?.command || "").trim()
          || String(action?.form_id || "").trim()
          || String(action?.redirect_url || "").trim();
      })
      : [];
    if (!form || !actions.length) {
      return;
    }
    const panel = document.createElement("div");
    panel.className = "manual-recovery-panel";
    panel.dataset.recoveryPanel = "1";
    panel.dataset.assetFieldRecovery = "1";
    panel.dataset.testid = options.recoveryTestid || "asset-field-recovery-actions";
    panel.innerHTML = recoveryPanelHtml(
      {...payload, next_actions: actions},
      {
        testid: panel.dataset.testid,
        title: options.recoveryTitle || pickText({zh: "修复后继续保存", en: "Fix, then save again"}),
        summary: payload?.error || options.fallbackMessage || "",
        actionControlHtml: (action) => assetRecoveryActionControlHtml(action, {
          ...options,
          recoveryFields,
        }),
      },
    );
    const anchor = options.statusElement || form.querySelector("[data-asset-form-error]") || form.firstElementChild;
    if (anchor?.insertAdjacentElement) {
      anchor.insertAdjacentElement("afterend", panel);
    } else {
      form.prepend(panel);
    }
    bindAssetRecoveryActionButtons(form, panel, options);
    bindRecoveryCommandCopy();
  }

  function assetRecoveryActionFields(action, fallbackFields = []) {
    const actionFields = Array.isArray(action?.fields) ? action.fields : [];
    const fields = (actionFields.length ? actionFields : fallbackFields)
      .map((field) => String(field || "").trim())
      .filter(Boolean);
    return Array.from(new Set(fields));
  }

  function assetRecoveryActionControlHtml(action, options = {}) {
    const actionKind = recoveryActionKind(action);
    const fields = assetRecoveryActionFields(action, options.recoveryFields || []);
    if (actionKind === "fix_asset_fields") {
      const fieldAttribute = fields.join(" ");
      return `<button class="ghost-button" type="button" data-asset-recovery-action="fix_asset_fields" data-asset-recovery-fields="${escapeHtml(fieldAttribute)}">${escapeHtml(recoveryActionLabel(action))}</button>`;
    }
    if (actionKind === "retry_web_asset_save") {
      return `<button class="ghost-button" type="button" data-asset-recovery-action="retry_web_asset_save">${escapeHtml(recoveryActionLabel(action))}</button>`;
    }
    return recoveryActionControlHtml(action, options);
  }

  function focusAssetRecoveryTarget(target) {
    if (!target) {
      return false;
    }
    target.scrollIntoView?.({block: "center", behavior: "smooth"});
    const focusTarget = isFieldControl(target)
      ? target
      : target.querySelector?.("input, select, textarea, button, [tabindex]:not([tabindex='-1'])");
    const targetToFocus = focusTarget || target;
    if (typeof targetToFocus.focus !== "function") {
      return true;
    }
    if (!isFieldControl(targetToFocus) && targetToFocus.setAttribute && !targetToFocus.hasAttribute("tabindex")) {
      targetToFocus.setAttribute("tabindex", "-1");
    }
    targetToFocus.focus({preventScroll: true});
    return true;
  }

  function focusFirstAssetRecoveryField(form, fields, options = {}) {
    for (const field of fields) {
      const target = recoveryTargetByField(form, field, options);
      if (focusAssetRecoveryTarget(target)) {
        return true;
      }
    }
    return false;
  }

  function submitAssetRecoveryForm(form, options = {}) {
    if (!form) {
      return;
    }
    const submitter = options.submitButton || form.querySelector("button[type='submit'], input[type='submit']");
    if (typeof form.requestSubmit === "function") {
      if (submitter && !submitter.disabled) {
        form.requestSubmit(submitter);
        return;
      }
      form.requestSubmit();
      return;
    }
    if (submitter && typeof submitter.click === "function") {
      submitter.click();
    }
  }

  function bindAssetRecoveryActionButtons(form, panel, options = {}) {
    panel?.querySelectorAll("[data-asset-recovery-action]").forEach((button) => {
      if (!(button instanceof HTMLButtonElement) || button.dataset.boundAssetRecoveryAction === "1") {
        return;
      }
      button.dataset.boundAssetRecoveryAction = "1";
      button.addEventListener("click", () => {
        const action = String(button.dataset.assetRecoveryAction || "").trim();
        if (action === "fix_asset_fields") {
          const fields = String(button.dataset.assetRecoveryFields || "")
            .split(/\s+/)
            .map((field) => field.trim())
            .filter(Boolean);
          focusFirstAssetRecoveryField(form, fields, options);
          return;
        }
        if (action === "retry_web_asset_save") {
          submitAssetRecoveryForm(form, options);
        }
      });
    });
  }

  function bindRecoveryCommandCopy() {
    document.querySelectorAll("[data-recovery-command-copy]").forEach((button) => {
      if (button.dataset.boundRecoveryCommandCopy === "1") {
        return;
      }
      button.dataset.boundRecoveryCommandCopy = "1";
      button.addEventListener("click", async () => {
        const command = String(button.dataset.copyValue || "").trim();
        if (!command) {
          return;
        }
        renderRecoveryCommandManualCopy(button, "");
        try {
          await writeTextToClipboard(command);
          button.classList.add("is-copied");
          setRecoveryCommandCopyStatus(button, pickText({
            zh: button.dataset.copySuccessZh || "命令已复制。",
            en: button.dataset.copySuccessEn || "Command copied.",
          }), "success");
          window.setTimeout(() => button.classList.remove("is-copied"), 1400);
        } catch (_) {
          setRecoveryCommandCopyStatus(
            button,
            pickText({
              zh: button.dataset.copyFailureZh || "浏览器未允许自动复制；请手动复制下面的恢复命令。",
              en: button.dataset.copyFailureEn || "The browser blocked automatic copy; copy the recovery command below manually.",
            }),
            "warning",
          );
          renderRecoveryCommandManualCopy(button, command);
        }
      });
    });
  }

  function bindProjectScopeSwitcher() {
    const switchers = Array.from(document.querySelectorAll("[data-project-scope-switcher]"));
    if (!switchers.length) {
      return;
    }

    const closeSwitcher = (switcher, {restoreFocus = false} = {}) => {
      if (!switcher.open) {
        return;
      }
      switcher.open = false;
      if (restoreFocus) {
        switcher.querySelector("summary")?.focus();
      }
    };

    switchers.forEach((switcher) => {
      if (switcher.dataset.boundProjectScope === "1") {
        return;
      }
      switcher.dataset.boundProjectScope = "1";
      switcher.addEventListener("keydown", (event) => {
        if (event.key !== "Escape" || !switcher.open) {
          return;
        }
        event.preventDefault();
        closeSwitcher(switcher, {restoreFocus: true});
      });

      const picker = switcher.querySelector("[data-project-scope-picker]");
      const input = switcher.querySelector("[data-testid='global-project-scope-workdir']");
      if (picker && input instanceof HTMLInputElement) {
        picker.addEventListener("click", async () => {
          picker.disabled = true;
          try {
            const response = await fetch("/api/system/pick-directory", {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({start_path: input.value || ""}),
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) {
              throw new Error(payload.error || pickText({
                zh: "无法打开目录选择器。",
                en: "Unable to open the folder picker.",
              }));
            }
            if (payload.path) {
              input.value = payload.path;
              input.focus();
              input.dispatchEvent(new Event("input", {bubbles: true}));
              input.dispatchEvent(new Event("change", {bubbles: true}));
            }
          } catch (error) {
            showAppFeedback(error.message || pickText({
              zh: "无法选择项目目录。",
              en: "Unable to choose a project folder.",
            }), "error");
          } finally {
            picker.disabled = false;
          }
        });
      }
    });

    document.addEventListener("click", (event) => {
      switchers.forEach((switcher) => {
        if (switcher.open && !switcher.contains(event.target)) {
          closeSwitcher(switcher);
        }
      });
    });

    const root = projectScopeRoot();
    const current = safeWorkdirContextValue(root?.dataset?.currentWorkdir || "");
    syncWorkdirContext(current);
    if (current && typeof URL === "function" && window.history?.replaceState) {
      try {
        const url = new URL(window.location.href);
        if (url.searchParams.get(PROJECT_SCOPE_QUERY_PARAM) === ALL_PROJECTS_SCOPE) {
          url.searchParams.delete(PROJECT_SCOPE_QUERY_PARAM);
          window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
        }
      } catch (_) {
        // URL cleanup is best-effort; server-side entity ownership remains authoritative.
      }
    }
  }

  function bindPathPickers() {
    document.querySelectorAll("[data-pick-file][data-target-input]").forEach((button) => {
      if (button.dataset.boundPickFile === "1") {
        return;
      }
      button.dataset.boundPickFile = "1";
      button.addEventListener("click", async () => {
        const endpoint = button.dataset.pickEndpoint || "/api/system/pick-bundle-file";
        const targetId = button.dataset.targetInput || "";
        const target = targetId ? document.getElementById(targetId) : null;
        if (!(target instanceof HTMLInputElement)) {
          return;
        }
        button.disabled = true;
        try {
          const response = await fetch(endpoint, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({start_path: target.value || ""}),
          });
          const payload = await response.json().catch(() => ({}));
          if (!response.ok) {
            throw new Error(payload.error || "failed");
          }
          if (payload.path) {
            target.value = payload.path;
            target.focus();
            target.dispatchEvent(new Event("change", {bubbles: true}));
          }
        } catch (error) {
          showAppFeedback(error.message || pickText({
            zh: "无法选择文件。",
            en: "Unable to choose a file.",
          }), "error");
        } finally {
          button.disabled = false;
        }
      });
    });
  }

  function bindRevealPathButtons() {
    document.querySelectorAll("[data-reveal-path]").forEach((button) => {
      if (button.dataset.boundRevealPath === "1") {
        return;
      }
      button.dataset.boundRevealPath = "1";
      button.addEventListener("click", async () => {
        const path = button.dataset.revealPath || "";
        if (button.dataset.pathActionMode === "copy") {
          renderGlobalManualCopy("");
          try {
            await writeTextToClipboard(path);
            showAppFeedback(pickText({
              zh: "路径已复制。",
              en: "Path copied.",
            }), "success");
          } catch (_) {
            renderGlobalManualCopy(path, {
              label: pickText({zh: "手动复制路径", en: "Manual path copy"}),
              textareaId: "global-path-manual-copy-textarea",
            });
            showAppFeedback(pickText({
              zh: "浏览器未允许自动复制；请手动复制上方路径。",
              en: "The browser blocked automatic copy; copy the path above manually.",
            }), "warning");
          }
          return;
        }
        revealPath(path);
      });
    });
  }

  function bindHelpTooltips() {
    let tooltip = document.querySelector(".help-floating-tooltip");
    if (!tooltip) {
      tooltip = document.createElement("div");
      tooltip.className = "help-floating-tooltip";
      tooltip.id = "help-floating-tooltip";
      tooltip.hidden = true;
      tooltip.setAttribute("role", "tooltip");
      document.body.appendChild(tooltip);
    } else if (!tooltip.id) {
      tooltip.id = "help-floating-tooltip";
    }

    let activeHelpTarget = null;

    const clearHelpDescription = (target) => {
      if (target?.getAttribute?.("aria-describedby") === tooltip.id) {
        target.removeAttribute("aria-describedby");
      }
    };

    const hide = (target = activeHelpTarget) => {
      if (target && target !== activeHelpTarget) {
        clearHelpDescription(target);
        return;
      }
      clearHelpDescription(activeHelpTarget);
      activeHelpTarget = null;
      tooltip.hidden = true;
      tooltip.textContent = "";
    };
    const show = (target) => {
      const text = target.getAttribute("data-tooltip") || "";
      if (!text) {
        hide();
        return;
      }
      if (activeHelpTarget && activeHelpTarget !== target) {
        clearHelpDescription(activeHelpTarget);
      }
      activeHelpTarget = target;
      target.setAttribute("aria-describedby", tooltip.id);
      tooltip.textContent = text;
      tooltip.hidden = false;
      positionHelpTooltip(tooltip, target);
    };

    document.querySelectorAll(".help-dot[data-tooltip]").forEach((button) => {
      if (button.dataset.boundHelpTooltip === "1") {
        return;
      }
      button.dataset.boundHelpTooltip = "1";
      button.addEventListener("mouseenter", () => show(button));
      button.addEventListener("focus", () => show(button));
      button.addEventListener("mousemove", () => positionHelpTooltip(tooltip, button));
      button.addEventListener("mouseleave", () => {
        if (document.activeElement !== button) {
          hide(button);
        }
      });
      button.addEventListener("blur", () => hide(button));
      button.addEventListener("click", (event) => {
        event.preventDefault();
        show(button);
      });
      button.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && activeHelpTarget === button) {
          event.stopPropagation();
          hide(button);
        }
      });
    });

    if (document.body.dataset.boundHelpTooltipDismiss === "1") {
      return;
    }
    document.body.dataset.boundHelpTooltipDismiss = "1";
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        hide();
      }
    });
    document.addEventListener("click", (event) => {
      if (!(event.target instanceof Node) || !activeHelpTarget) {
        return;
      }
      if (activeHelpTarget.contains(event.target)) {
        return;
      }
      hide();
    });
  }

  function positionHelpTooltip(tooltip, target) {
    if (tooltip.hidden) {
      return;
    }
    const rect = target.getBoundingClientRect();
    const tipRect = tooltip.getBoundingClientRect();
    const gap = 12;
    const viewportPadding = 14;
    const centered = rect.left + rect.width / 2 - tipRect.width / 2;
    const left = Math.max(viewportPadding, Math.min(centered, window.innerWidth - tipRect.width - viewportPadding));
    const above = rect.top - tipRect.height - gap;
    const top = above >= viewportPadding ? above : rect.bottom + gap;
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${Math.max(viewportPadding, top)}px`;
  }

  function savedAlignmentSessionId() {
    try {
      return window.localStorage.getItem(ALIGNMENT_SESSION_STORAGE_KEY) || "";
    } catch (_) {
      return "";
    }
  }

  async function activeSavedAlignmentSessionForWorkdir(workdir) {
    const sessionId = savedAlignmentSessionId();
    if (!sessionId) {
      return null;
    }
    const response = await fetch(`/api/alignments/sessions/${encodeURIComponent(sessionId)}`, {
      headers: {"accept": "application/json"},
    }).catch(() => null);
    if (!response?.ok) {
      return null;
    }
    const payload = await response.json().catch(() => ({}));
    const session = payload.session || {};
    if (!ACTIVE_ALIGNMENT_STATUSES.has(String(session.status || ""))) {
      return null;
    }
    if (!sameWorkdir(session.workdir, workdir, {allowEmptyLeft: false, allowEmptyRight: false})) {
      return null;
    }
    return session;
  }

  function currentPathname() {
    const pathname = String(window.location?.pathname || "");
    if (pathname) {
      return pathname;
    }
    try {
      return new URL(window.location?.href || "/", window.location?.origin || "http://loopora.local").pathname;
    } catch (_) {
      return "/";
    }
  }

  function activeAlignmentComposerReturnTarget(link, {allowBlocked = false} = {}) {
    if (!allowBlocked && navigationControlIsBlocked(link)) {
      return null;
    }
    let targetUrl;
    try {
      targetUrl = new URL(navigationControlHref(link), window.location.origin);
    } catch (_) {
      return null;
    }
    if (targetUrl.origin !== window.location.origin || targetUrl.pathname !== "/loops/new" || targetUrl.searchParams.has("alignment_session_id")) {
      return null;
    }
    const workdir = targetUrl.searchParams.get("workdir") || targetUrl.searchParams.get("alignment_workdir") || "";
    return workdir ? {targetUrl, workdir} : null;
  }

  function bindActiveAlignmentComposerReturnLinks() {
    if (currentPathname().startsWith("/loops/new")) {
      return;
    }
    document.querySelectorAll(NAVIGATION_CONTEXT_LINK_SELECTOR).forEach((link) => {
      if (link.dataset.boundActiveAlignmentComposerReturn === "1") {
        return;
      }
      if (!activeAlignmentComposerReturnTarget(link, {allowBlocked: true})) {
        return;
      }
      link.dataset.boundActiveAlignmentComposerReturn = "1";
      link.addEventListener("click", async (event) => {
        if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.target) {
          return;
        }
        const target = activeAlignmentComposerReturnTarget(link);
        if (!target) {
          return;
        }
        const sessionId = savedAlignmentSessionId();
        if (!sessionId) {
          return;
        }
        event.preventDefault();
        const session = await activeSavedAlignmentSessionForWorkdir(target.workdir);
        if (!session?.id) {
          window.location.href = `${target.targetUrl.pathname}${target.targetUrl.search}${target.targetUrl.hash}`;
          return;
        }
        const sessionUrl = new URL("/loops/new/bundle", window.location.origin);
        sessionUrl.searchParams.set("alignment_session_id", session.id);
        window.location.href = `${sessionUrl.pathname}${sessionUrl.search}`;
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    setLocale(currentLocale(), {persist: false});
    setTheme(currentTheme(), {persist: false});
    handleReturnedSurfaceUpdateFeedback();
    bindHashLinkedDisclosures();
    document.querySelectorAll("[data-set-locale]").forEach((button) => {
      button.addEventListener("click", () => setLocale(button.dataset.setLocale));
    });
    document.querySelectorAll("[data-set-theme]").forEach((button) => {
      button.addEventListener("click", () => setTheme(button.dataset.setTheme));
    });
    bindDeleteLoopButtons();
    bindOpenCards();
    bindPrimaryNavigation();
    revealActiveTopNavItem();
    bindNavPreferences();
    bindProjectScopeSwitcher();
    bindPathPickers();
    bindRevealPathButtons();
    bindAgentEntryCommandCopy();
    bindRecoveryCommandCopy();
    bindHelpTooltips();
    bindActiveAlignmentComposerReturnLinks();
  });

  window.LooporaUI = {
    currentLocale,
    detectPreferredLocale,
    setLocale,
    currentTheme,
    setTheme,
    pickText,
    showAppFeedback,
    returnedSurfaceUpdateMessage,
    handleReturnedSurfaceUpdateFeedback,
    translateStatus,
    translateRole,
    normalizeRoleName,
    applyLocalizedAttributes,
    bindDeleteLoopButtons,
    bindOpenCards,
    bindPrimaryNavigation,
    revealActiveTopNavItem,
    bindProjectScopeSwitcher,
    bindPathPickers,
    bindAgentEntryCommandCopy,
    bindRecoveryCommandCopy,
    clearRecoveryCommandCopyStatus,
    createRecoveryCommandCopyFragment,
    createRecoveryActionControlFragment,
    recoveryActionHtml,
    recoveryPanelHtml,
    clearAssetFieldRecovery,
    renderAssetFieldRecovery,
    bindHelpTooltips,
    recoveryActionLabel,
    recoveryActionHint,
    recoveryActionLinkLabel,
    safeLocalRecoveryUrl,
    safeLocalRedirectUrl,
    contextPreservingRedirectUrl,
    assetSaveRedirectUrl,
    setNavigationControlBlocked,
    syncWorkdirFormAction,
    workdirContextHref,
    workdirContextRedirectUrl,
    comparableWorkdir,
    sameWorkdir,
    tutorialFitPrefersDirectPath,
    tutorialFitSetupCommandState,
    syncWorkdirContext,
    writeTextToClipboard,
    renderManualCopy,
    renderGlobalManualCopy,
  };
  if (typeof window.matchMedia === "function") {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (event) => {
      if (!readSavedTheme()) {
        setTheme(event.matches ? "dark" : "light", {persist: false});
      }
    });
  }
})();

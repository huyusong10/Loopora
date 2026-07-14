(() => {
  const surface = document.querySelector("[data-bundle-review-surface]");
  const tabList = surface?.querySelector("[data-bundle-review-tabs]");
  const tabs = Array.from(surface?.querySelectorAll("[data-bundle-review-tab]") || []);
  const panels = Array.from(surface?.querySelectorAll("[data-bundle-review-panel]") || []);
  const management = document.querySelector("[data-testid='bundle-plan-management']");

  if (!surface || !tabList || !tabs.length || !panels.length) {
    return;
  }

  function knownView(value) {
    return tabs.some((tab) => tab.dataset.bundleReviewTab === value) ? value : "judgment";
  }

  function viewForHash(hash = window.location.hash) {
    const value = String(hash || "");
    if (value.includes("bundle-review-panel-workflow")) {
      return "workflow";
    }
    if (value.includes("bundle-review-panel-contract") || value.includes("bundle-spec-preview")) {
      return "contract";
    }
    return "judgment";
  }

  function selectView(value, {focus = false, updateHash = false} = {}) {
    const view = knownView(value);
    tabs.forEach((tab) => {
      const active = tab.dataset.bundleReviewTab === view;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
      if (active && focus) {
        tab.focus();
      }
    });
    panels.forEach((panel) => {
      panel.hidden = panel.dataset.bundleReviewPanel !== view;
    });
    surface.dataset.activeReviewView = view;
    if (updateHash) {
      const panel = panels.find((candidate) => candidate.dataset.bundleReviewPanel === view);
      if (panel?.id) {
        window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}#${panel.id}`);
      }
    }
  }

  function revealManagementTarget(link) {
    if (!management) {
      return;
    }
    management.open = true;
    const href = String(link.getAttribute("href") || "");
    if (!href.startsWith("#")) {
      return;
    }
    const target = document.getElementById(href.slice(1));
    let parentDetails = target?.closest("details");
    while (parentDetails) {
      parentDetails.open = true;
      parentDetails = parentDetails.parentElement?.closest("details") || null;
    }
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => {
      selectView(tab.dataset.bundleReviewTab, {updateHash: true});
    });
    tab.addEventListener("keydown", (event) => {
      let targetIndex = index;
      if (event.key === "ArrowRight" || event.key === "ArrowDown") {
        targetIndex = (index + 1) % tabs.length;
      } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
        targetIndex = (index - 1 + tabs.length) % tabs.length;
      } else if (event.key === "Home") {
        targetIndex = 0;
      } else if (event.key === "End") {
        targetIndex = tabs.length - 1;
      } else {
        return;
      }
      event.preventDefault();
      selectView(tabs[targetIndex].dataset.bundleReviewTab, {focus: true, updateHash: true});
    });
  });

  document.querySelectorAll("[data-open-bundle-management]").forEach((link) => {
    link.addEventListener("click", () => revealManagementTarget(link));
  });

  window.addEventListener("hashchange", () => {
    if (window.location.hash.startsWith("#bundle-review-panel-")) {
      selectView(viewForHash());
      return;
    }
    const target = document.getElementById(window.location.hash.slice(1));
    if (target?.closest("[data-testid='bundle-plan-management']")) {
      revealManagementTarget({getAttribute: () => window.location.hash});
    }
  });

  surface.classList.add("is-enhanced");
  selectView(viewForHash());
  tabList.hidden = false;
  if (window.location.hash && document.getElementById(window.location.hash.slice(1))?.closest("[data-testid='bundle-plan-management']")) {
    revealManagementTarget({getAttribute: () => window.location.hash});
  }
})();

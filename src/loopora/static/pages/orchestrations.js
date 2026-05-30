document.addEventListener("DOMContentLoaded", () => {
  if (!window.LooporaWorkflowDiagram) {
    return;
  }

  function renderAllWorkflowDiagrams() {
    document.querySelectorAll("[data-strategy-diagram], [data-workflow-diagram]").forEach((element) => {
      try {
        const strategySource = JSON.parse(element.dataset.strategyDiagram || element.dataset.workflowDiagram || "{}");
        window.LooporaWorkflowDiagram.renderInto(element, strategySource, {variant: "card"});
      } catch (_) {
        element.innerHTML = "";
      }
    });
  }

  document.addEventListener("loopora:localechange", renderAllWorkflowDiagrams);
  renderAllWorkflowDiagrams();
});

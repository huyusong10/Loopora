(function () {
  function projectionSummary(payload) {
    const projection = payload?.web_projection || payload?.initialProjection || {};
    const summary = projection.summary;
    return summary && typeof summary === "object" ? summary : {};
  }

  function projectionObject(payload) {
    const projection = payload?.web_projection || payload?.initialProjection || null;
    return projection && typeof projection === "object" ? projection : null;
  }

  function projectionRunPayload(projection) {
    const summary = projection.summary && typeof projection.summary === "object" ? projection.summary : {};
    const lifecycle = projection.lifecycle && typeof projection.lifecycle === "object" ? projection.lifecycle : {};
    const timing = projection.timing && typeof projection.timing === "object" ? projection.timing : {};
    const display = projection.display && typeof projection.display === "object" ? projection.display : {};
    const strategySource = projection.strategy_source && typeof projection.strategy_source === "object"
      ? projection.strategy_source
      : {};
    const taskVerdict = projection.task_verdict && typeof projection.task_verdict === "object"
      ? projection.task_verdict
      : {status: String(summary.task_verdict_status || "not_evaluated").trim() || "not_evaluated"};
    const runStatus = String(summary.run_status || lifecycle.run_status || projection.status || "").trim() || "unknown";
    const currentIter = Number.isInteger(summary.current_iter)
      ? summary.current_iter
      : (Number.isInteger(lifecycle.current_iter) ? lifecycle.current_iter : null);
    return {
      id: String(summary.run_id || lifecycle.run_id || "").trim(),
      loop_id: String(summary.loop_id || lifecycle.loop_id || "").trim(),
      status: runStatus,
      run_status: runStatus,
      current_iter: currentIter,
      active_role: String(summary.active_role || lifecycle.active_role || "").trim(),
      workdir: String(summary.workdir || lifecycle.workdir || "").trim(),
      task_verdict: taskVerdict,
      strategy_source: strategySource,
      summary_md: String(display.summary_md || ""),
      queued_at: String(timing.queued_at || ""),
      started_at: String(timing.started_at || ""),
      finished_at: String(timing.finished_at || ""),
      updated_at: String(timing.updated_at || ""),
      created_at: String(timing.created_at || ""),
      web_projection: projection,
    };
  }

  function normalizeRunPayload(payload = {}) {
    const raw = payload && typeof payload === "object" ? payload : {};
    const projection = projectionObject(raw);
    if (projection) {
      return projectionRunPayload(projection);
    }
    const summary = projectionSummary(raw);
    const runStatus = String(summary.run_status || raw.run_status || raw.status || "").trim();
    const rawStrategySource = raw.strategy_source && typeof raw.strategy_source === "object"
      ? raw.strategy_source
      : (raw.workflow_json && typeof raw.workflow_json === "object" ? raw.workflow_json : {});
    return {
      ...raw,
      id: String(summary.run_id || raw.id || "").trim(),
      loop_id: String(summary.loop_id || raw.loop_id || "").trim(),
      status: runStatus || "unknown",
      run_status: runStatus || "unknown",
      current_iter: Number.isInteger(summary.current_iter) ? summary.current_iter : raw.current_iter,
      active_role: String(summary.active_role || raw.active_role || "").trim(),
      workdir: String(summary.workdir || raw.workdir || "").trim(),
      strategy_source: rawStrategySource,
      web_projection: raw.web_projection || raw.initialProjection || null,
    };
  }

  function normalizeInitialRun(seed = {}) {
    return normalizeRunPayload({
      ...(seed.initialRun || {}),
      initialProjection: seed.initialProjection || null,
    });
  }

  window.LooporaRunDetailProjection = {
    normalizeInitialRun,
    normalizeRunPayload,
  };
})();

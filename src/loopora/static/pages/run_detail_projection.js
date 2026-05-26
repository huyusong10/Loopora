(function () {
  function projectionSummary(payload) {
    const projection = payload?.web_projection || payload?.initialProjection || {};
    const summary = projection.summary;
    return summary && typeof summary === "object" ? summary : {};
  }

  function normalizeRunPayload(payload = {}) {
    const raw = payload && typeof payload === "object" ? payload : {};
    const summary = projectionSummary(raw);
    const runStatus = String(summary.run_status || raw.run_status || raw.status || "").trim();
    return {
      ...raw,
      id: String(summary.run_id || raw.id || "").trim(),
      loop_id: String(summary.loop_id || raw.loop_id || "").trim(),
      status: runStatus || "unknown",
      run_status: runStatus || "unknown",
      current_iter: Number.isInteger(summary.current_iter) ? summary.current_iter : raw.current_iter,
      active_role: String(summary.active_role || raw.active_role || "").trim(),
      workdir: String(summary.workdir || raw.workdir || "").trim(),
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

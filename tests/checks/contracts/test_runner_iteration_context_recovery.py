from __future__ import annotations

import json
from pathlib import Path

from runner_helpers import _create_loop


CORRUPT_LATEST_STATE_PERSIST_CALL = 2


def test_workflow_iteration_context_recovers_corrupt_latest_state(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="plateau")
    original_persist_iteration_context = service._persist_iteration_context
    persist_calls = 0

    def corrupt_latest_state_before_second_persist(request):
        nonlocal persist_calls
        persist_calls += 1
        if persist_calls == CORRUPT_LATEST_STATE_PERSIST_CALL:
            request.layout.latest_state_path.write_text("{", encoding="utf-8")
        return original_persist_iteration_context(request)

    monkeypatch.setattr(service, "_persist_iteration_context", corrupt_latest_state_before_second_persist)
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Corrupt Latest State Loop",
        max_iters=2,
    )

    run = service.rerun(loop["id"])
    latest_state = json.loads((Path(run["runs_dir"]) / "context" / "latest_state.json").read_text(encoding="utf-8"))

    assert persist_calls == CORRUPT_LATEST_STATE_PERSIST_CALL
    assert run["status"] == "failed"
    assert "Expecting" not in str(run.get("error_message") or "")
    assert latest_state["latest_iteration"] == 1

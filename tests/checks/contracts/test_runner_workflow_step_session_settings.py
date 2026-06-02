from __future__ import annotations

import json
from pathlib import Path

from loopora.executor import CodexExecutor
from runner_helpers import _create_loop, _read_jsonl


def test_workflow_step_can_resume_its_own_previous_session_and_append_extra_cli_args(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    recorded_requests: list[dict] = []

    class SessionAwareExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            recorded_requests.append(
                {
                    "step_id": request.step_id,
                    "iter": request.extra_context.get("iter_id"),
                    "inherit_session": request.inherit_session,
                    "resume_session_id": request.resume_session_id,
                    "extra_cli_args_text": request.extra_cli_args_text,
                    "role_archetype": request.role_archetype,
                }
            )
            if request.role_archetype == "builder":
                request.extra_context["session_ref"] = {
                    "session_id": f"builder-session-{request.extra_context.get('iter_id')}",
                }
                payload = {
                    "attempted": "Made a targeted implementation change.",
                    "summary": "Builder progressed the workspace.",
                    "changed_files": [],
                }
            else:
                payload = {
                    "passed": False,
                    "decision_summary": "Keep iterating for the contract test.",
                    "feedback_to_builder": "Continue the workflow.",
                    "blocking_issues": [],
                    "metrics": [],
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 0.4,
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = SessionAwareExecutor
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Session Carry Loop",
        completion_mode="rounds",
        max_iters=2,
        workflow={
            "version": 1,
            "preset": "",
            "roles": [
                {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
                {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
            ],
            "steps": [
                {
                    "id": "builder_step",
                    "role_id": "builder",
                    "inherit_session": True,
                    "extra_cli_args": "--verbose",
                },
                {
                    "id": "gatekeeper_step",
                    "role_id": "gatekeeper",
                    "on_pass": "continue",
                    "inherit_session": False,
                },
            ],
        },
    )

    run = service.rerun(loop["id"])
    role_requests = _read_jsonl(Path(run["runs_dir"]) / "context" / "role_requests.jsonl")

    assert run["status"] == "succeeded"
    builder_calls = [item for item in recorded_requests if item["step_id"] == "builder_step"]
    gatekeeper_calls = [item for item in recorded_requests if item["step_id"] == "gatekeeper_step"]
    assert [item["resume_session_id"] for item in builder_calls] == ["", "builder-session-0"]
    assert all(item["inherit_session"] is True for item in builder_calls)
    assert all(item["extra_cli_args_text"] == "--verbose" for item in builder_calls)
    assert all(item["inherit_session"] is False for item in gatekeeper_calls)
    assert all(item["resume_session_id"] == "" for item in gatekeeper_calls)

    second_builder_request = next(item for item in role_requests if item["step_id"] == "builder_step" and item["iter"] == 1)
    assert second_builder_request["inherit_session"] is True
    assert second_builder_request["resume_session_id"] == "builder-session-0"
    assert second_builder_request["extra_cli_args_text"] == "--verbose"

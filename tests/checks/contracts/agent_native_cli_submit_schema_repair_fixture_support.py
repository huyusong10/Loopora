from dataclasses import dataclass

from agent_native_cli_test_support import (
    AgentNativeStepSubmitRequest,
    LooporaConflictError,
    Path,
    RunArtifactLayout,
    cli,
    json,
)


@dataclass(frozen=True)
class UnfilledTemplateFixture:
    workdir: Path
    layout: RunArtifactLayout
    result_outbox_dir: Path
    result_file: Path
    filled_result_file: Path


def write_unfilled_template_fixture(tmp_path: Path) -> UnfilledTemplateFixture:
    workdir = tmp_path / "project"
    workdir.mkdir()
    layout = RunArtifactLayout(tmp_path / "runs" / "run_unfilled")
    layout.initialize()
    (layout.run_dir / "agent_native").mkdir(parents=True, exist_ok=True)
    output_schema = {
        "type": "object",
        "properties": {
            "attempted": {"type": "string"},
            "abandoned": {"type": "string"},
            "assumption": {"type": "string"},
            "summary": {"type": "string"},
            "changed_files": {"type": "array", "items": {"type": "string"}},
            "proof_files": {"type": "array", "items": {"type": "string"}},
            "proof_artifacts": {"type": "array", "items": {"type": "object"}},
            "artifact_paths": {"type": "array", "items": {"type": "string"}},
        },
    }
    result_outbox_dir = workdir / ".loopora" / "agent_outbox" / "codex"
    result_file = result_outbox_dir / "run_unfilled__builder_step.result.template.json"
    filled_result_file = result_outbox_dir / "run_unfilled__builder_step.result.json"
    (layout.run_dir / "agent_native" / "state.json").write_text(
        json.dumps(
            {
                "active_step": {
                    "agent_step_view": {
                        "iter": 1,
                        "step_id": "builder_step",
                        "step_order": 0,
                        "role": {"name": "Builder", "id": "builder", "archetype": "builder"},
                        "role_dispatch": {"target_agent": "loopora-builder"},
                        "context_absolute_path": str(layout.step_instruction_context_path(0, 0, "builder_step")),
                        "output_schema": output_schema,
                        "submit_hint": {
                            "result_template_absolute_path": str(result_file),
                            "result_file_absolute_path": str(filled_result_file),
                            "result_outbox_absolute_dir": str(result_outbox_dir),
                        },
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        json.dumps(
            {
                "loopora_host_dispatch": {
                    "adapter": "codex",
                    "run_id": "run_unfilled",
                    "step_id": "builder_step",
                    "target_agent": "loopora-builder",
                    "actual_agent": "loopora-builder",
                    "dispatch_mode": "host_subagent",
                    "inline": False,
                },
                "result": {
                    "attempted": None,
                    "abandoned": None,
                    "assumption": None,
                    "summary": None,
                    "changed_files": [None],
                    "proof_files": [None],
                    "proof_artifacts": [None],
                    "artifact_paths": [None],
                },
            }
        ),
        encoding="utf-8",
    )
    return UnfilledTemplateFixture(
        workdir=workdir,
        layout=layout,
        result_outbox_dir=result_outbox_dir,
        result_file=result_file,
        filled_result_file=filled_result_file,
    )


def install_unfilled_template_fake_service(monkeypatch, fixture: UnfilledTemplateFixture) -> None:
    class FakeService:
        def submit_agent_native_step(self, _request: AgentNativeStepSubmitRequest):
            raise LooporaConflictError(
                "agent-native result does not match output_schema: "
                "$.attempted expected string, got null; "
                "$.abandoned expected string, got null; "
                "$.assumption expected string, got null; "
                "$.summary expected string, got null; "
                "$.changed_files[0] expected string, got null; "
                "$.proof_files[0] expected string, got null"
            )

        def get_run(self, run_id: str):
            assert run_id == "run_unfilled"
            return {"id": "run_unfilled", "runs_dir": str(fixture.layout.run_dir)}

    monkeypatch.setattr(cli, "create_service", FakeService)


def invoke_unfilled_template_submit(runner, fixture: UnfilledTemplateFixture, *, json_mode: bool = False):
    args = [
        "agent",
        "codex",
        "submit",
        "--workdir",
        str(fixture.workdir),
        "--run-id",
        "run_unfilled",
        "--step-id",
        "builder_step",
        "--result-file",
        str(fixture.result_file),
        "--entry-source",
        "codex_project_skill",
        "--no-web",
    ]
    if json_mode:
        args.append("--json")
    return runner.invoke(cli.app, args)

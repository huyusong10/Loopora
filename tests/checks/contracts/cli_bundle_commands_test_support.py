from __future__ import annotations

from pathlib import Path

from loopora import cli
from loopora.bundles import bundle_to_yaml


def write_cli_bundle(path: Path, workdir: Path) -> None:
    path.write_text(bundle_to_yaml(cli_bundle_payload(workdir, name="CLI Bundle")), encoding="utf-8")


def install_cli_bundle_service(monkeypatch, tmp_path: Path) -> dict[str, object]:
    calls: dict[str, object] = {}

    class FakeService:
        def list_bundles(self):
            return [
                {
                    "id": "bundle_cli",
                    "name": "CLI Bundle",
                    "revision": 2,
                    "loop_id": "loop_cli",
                    "workdir": str(tmp_path / "workdir"),
                }
            ]

        def import_bundle_file(self, path: Path, *, replace_bundle_id=None):
            calls["import"] = {"path": str(path), "replace_bundle_id": replace_bundle_id}
            return {"id": "bundle_cli", "name": "CLI Bundle"}

        def export_bundle_yaml(self, bundle_id: str):
            calls["export"] = bundle_id
            return "version: 1\nmetadata:\n  name: CLI Bundle\n"

        def write_bundle_file(self, bundle_id: str, path: Path):
            calls["write"] = {"bundle_id": bundle_id, "path": str(path)}
            path.write_text("version: 1\nmetadata:\n  name: CLI Bundle\n", encoding="utf-8")
            return path

        def derive_bundle_from_loop(self, loop_id: str, **kwargs):
            calls["derive"] = {"loop_id": loop_id, **kwargs}
            return cli_bundle_payload(
                tmp_path / "workdir",
                name=kwargs.get("name") or "Derived CLI Bundle",
                collaboration_summary=kwargs.get("collaboration_summary") or "Derived from an existing loop.",
                task_markdown="# Task\n\nDerived.\n\n# Done When\n- Ready.\n",
                collaboration_intent="",
            )

        def delete_bundle(self, bundle_id: str):
            calls["delete"] = bundle_id
            return {"id": bundle_id, "deleted": True}

    monkeypatch.setattr(cli, "create_service", FakeService)
    return calls


def cli_bundle_payload(
    workdir: Path,
    *,
    name: str,
    collaboration_summary: str = "Prefer evidence over rush.",
    task_markdown: str = "# Task\n\nShip the change.\n\n# Done When\n- It works.\n",
    collaboration_intent: str = "Verify before sign-off.",
) -> dict:
    return {
        "version": 1,
        "metadata": {"name": name, "description": "", "revision": 1},
        "collaboration_summary": collaboration_summary,
        "loop": {
            "name": f"{name} Loop",
            "workdir": str(workdir),
            "completion_mode": "gatekeeper",
            "executor_kind": "codex",
            "executor_mode": "preset",
            "command_cli": "codex",
            "command_args_text": "",
            "model": "",
            "reasoning_effort": "",
            "iteration_interval_seconds": 0,
            "max_iters": 2,
            "max_role_retries": 1,
            "delta_threshold": 0.005,
            "trigger_window": 2,
            "regression_window": 2,
        },
        "spec": {"markdown": task_markdown},
        "role_definitions": [
            {
                "key": "builder",
                "name": "Builder",
                "description": "",
                "archetype": "builder",
                "prompt_ref": "builder.md",
                "prompt_markdown": "---\nversion: 1\narchetype: builder\n---\nBuild it.\n",
                "posture_notes": "Favor maintainability when possible.",
                "executor_kind": "codex",
                "executor_mode": "preset",
                "command_cli": "codex",
                "command_args_text": "",
                "model": "",
                "reasoning_effort": "",
            },
            {
                "key": "gatekeeper",
                "name": "GateKeeper",
                "description": "",
                "archetype": "gatekeeper",
                "prompt_ref": "gatekeeper.md",
                "prompt_markdown": "---\nversion: 1\narchetype: gatekeeper\n---\nJudge it.\n",
                "posture_notes": "Close only on real evidence.",
                "executor_kind": "codex",
                "executor_mode": "preset",
                "command_cli": "codex",
                "command_args_text": "",
                "model": "",
                "reasoning_effort": "",
            },
        ],
        "workflow": {
            "version": 1,
            "preset": "",
            "collaboration_intent": collaboration_intent,
            "roles": [
                {"id": "builder", "role_definition_key": "builder"},
                {"id": "gatekeeper", "role_definition_key": "gatekeeper"},
            ],
            "steps": [
                {"id": "builder_step", "role_id": "builder", "on_pass": "continue"},
                {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
            ],
        },
    }

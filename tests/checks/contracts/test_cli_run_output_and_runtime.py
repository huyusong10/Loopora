from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from loopora import cli
from loopora.cli_run_output import print_run_result
from loopora.run_artifacts import RunArtifactLayout
from loopora.settings import app_home


def _assert_cli_list(output: str, key: str, *items: str) -> None:
    assert f"{key}:\n" in output
    assert f"{key}: [" not in output
    for item in items:
        assert f"- {item}" in output


def test_cli_run_output_has_dedicated_boundary() -> None:
    root = Path(__file__).resolve().parents[3]
    support_source = (root / "src" / "loopora" / "cli_run_support.py").read_text(encoding="utf-8")
    output_source = (root / "src" / "loopora" / "cli_run_output.py").read_text(encoding="utf-8")
    contract_output_source = (root / "src" / "loopora" / "cli_run_contract_output.py").read_text(encoding="utf-8")
    task_verdict_output_source = (root / "src" / "loopora" / "cli_task_verdict_output.py").read_text(
        encoding="utf-8"
    )
    step_presenters_source = (root / "src" / "loopora" / "cli_agent_step_presenters.py").read_text(
        encoding="utf-8"
    )
    design_source = (root / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_run_output import" in support_source
    assert "from loopora.cli_run_output import print_run_contract_summary, print_task_verdict" in step_presenters_source
    assert "from loopora.cli_run_contract_output import print_run_contract_summary" in output_source
    assert "from loopora.cli_task_verdict_output import print_task_verdict" in output_source
    assert "def print_run_result" in output_source
    assert "def print_loop_created" in output_source
    assert "def print_run_contract_summary" not in output_source
    assert "def print_task_verdict" not in output_source
    for marker in (
        "def print_run_contract_summary",
        "def _cli_judgment_summary",
    ):
        assert marker in contract_output_source
        assert marker not in support_source + output_source + task_verdict_output_source
    for marker in ("def print_task_verdict", "def _task_verdict_bucket_counts"):
        assert marker in task_verdict_output_source
        assert marker not in support_source + output_source + contract_output_source
    for marker in (
        "def background_worker_command",
        "def spawn_background_worker",
        "class LoopCreateRequest",
        "def create_and_maybe_start_loop",
    ):
        assert marker in support_source
        assert marker not in output_source
    assert "cli_run_output.py" in design_source
    assert "cli_run_contract_output.py" in design_source
    assert "cli_task_verdict_output.py" in design_source


def test_cli_run_result_separates_run_status_and_task_verdict(capsys, tmp_path: Path) -> None:
    print_run_result(
        {
            "id": "run_contract",
            "status": "succeeded",
            "run_status": "succeeded",
            "runs_dir": str(tmp_path / "runs" / "run_contract"),
            "task_verdict": {
                "status": "insufficient_evidence",
                "source": "rounds_completion",
                "summary": "The run ended, but evidence is still too thin.",
            },
        }
    )

    output = capsys.readouterr().out
    assert "run_status: succeeded" in output
    assert "task_verdict: insufficient_evidence" in output
    assert "task_verdict_source: rounds_completion" in output
    assert "task_verdict_summary: The run ended, but evidence is still too thin." in output


def test_cli_run_result_explains_passing_verdict_audit_buckets(capsys, tmp_path: Path) -> None:
    print_run_result(
        {
            "id": "run_passed_with_audit_buckets",
            "status": "succeeded",
            "run_status": "succeeded",
            "runs_dir": str(tmp_path / "runs" / "run_passed_with_audit_buckets"),
            "task_verdict": {
                "status": "passed",
                "source": "gatekeeper",
                "summary": "Required evidence passed.",
                "buckets": {
                    "proven": [{"id": "done_when.check_001", "label": "Required proof", "required": True}],
                    "weak": [{"label": "Earlier weak evidence remains visible."}],
                    "unproven": [{"id": "fake_done.risk_001", "label": "Advisory fake-done risk", "required": False}],
                    "blocking": [],
                    "residual_risk": [{"label": "Tracked follow-up.", "managed": True}],
                },
            },
        }
    )

    output = capsys.readouterr().out
    assert "task_verdict: passed" in output
    assert "task_verdict_buckets: proven 1 / weak 1 / unproven 1 / blocking 0 / residual_risk 1" in output
    assert "task_verdict_required_basis: 1/1 required targets proven; blocking 0" in output
    assert "task_verdict_bucket_note: passing verdict kept non-blocking" in output
    assert "for audit or accepted follow-up" in output
    assert "required coverage and GateKeeper support still passed" in output


def test_cli_run_result_prints_not_evaluated_when_task_verdict_is_missing(capsys, tmp_path: Path) -> None:
    print_run_result(
        {
            "id": "run_legacy",
            "status": "succeeded",
            "run_status": "succeeded",
            "runs_dir": str(tmp_path / "runs" / "run_legacy"),
        }
    )

    output = capsys.readouterr().out
    assert "run_status: succeeded" in output
    assert "task_verdict: not_evaluated" in output


def test_cli_run_result_prints_frozen_judgment_contract_summary(capsys, tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "runs" / "run_bundle")
    layout.initialize()
    layout.run_contract_path.write_text(
        json.dumps(
            {
                "collaboration_summary": "Prefer proof before speed.",
                "loop_fit_reasons": ["Future rounds keep proof alive."],
                "judgment_tradeoffs": ["Proof beats speed when closure is uncertain."],
                "execution_strategy": ["Prove the focused path first, then expand after evidence is strong."],
                "local_governance": ["GateKeeper treats skipped tests/ evidence as Blocking."],
                "role_postures": [
                    {
                        "role_name": "GateKeeper",
                        "archetype": "gatekeeper",
                        "posture_notes": "Fail closed when evidence is weak.",
                    }
                ],
                "source_bundle": {
                    "id": "bundle_cli",
                    "name": "CLI Frozen Contract Bundle",
                    "revision": 3,
                    "imported_from_path": "/tmp/loopora/cli-bundle.yml",
                    "bundle_sha256": "abcdef1234567890",
                    "bundle_bytes": 2048,
                },
                "completion_mode": "gatekeeper",
                "workflow": {
                    "preset": "quality_gate",
                    "collaboration_intent": "Builder evidence feeds Inspector review before GateKeeper closure.",
                },
                "compiled_spec": {
                    "goal": "Ship the requested behavior.",
                    "check_mode": "specified",
                    "checks": [{"id": "check_001"}, {"id": "check_002"}],
                    "coverage_targets": [
                        {"id": "done_when.check_001", "required": True},
                        {"id": "done_when.check_002", "required": True},
                        {"id": "success_surface.surface_001", "required": False},
                        {"id": "fake_done.risk_001", "required": False},
                        {"id": "fake_done.risk_002", "required": False},
                        {"id": "evidence_preference.pref_001", "required": False},
                        {"id": "evidence_preference.pref_002", "required": False},
                        {"id": "evidence_preference.pref_003", "required": False},
                        {"id": "gatekeeper.finish", "required": True},
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print_run_result(
        {
            "id": "run_bundle",
            "status": "succeeded",
            "run_status": "succeeded",
            "runs_dir": str(layout.run_dir),
            "task_verdict": {"status": "passed"},
        }
    )

    output = capsys.readouterr().out
    assert f"run_contract_path: {layout.run_contract_path}" in output
    assert "source_plan: CLI Frozen Contract Bundle (bundle_cli, rev 3)" in output
    assert "source_plan_path: /tmp/loopora/cli-bundle.yml" in output
    assert "source_plan_digest: sha256:abcdef123456, 2048 bytes" in output
    assert 'source_plan: {"id":' not in output
    assert "judgment_contract_summary: Prefer proof before speed." in output
    assert "check_mode: specified" in output and "completion_mode: gatekeeper" in output
    assert "strategy_preset: quality_gate" in output
    assert "strategy_collaboration_intent: Builder evidence feeds Inspector review before GateKeeper closure." in output
    assert "workflow_preset:" not in output and "workflow_collaboration_intent:" not in output
    assert "check_count: 2" in output
    _assert_cli_list(output, "coverage_targets", "done_when.check_001 (required)", "gatekeeper.finish (required)")
    assert "evidence_preference.pref_003" in output
    _assert_cli_list(output, "loop_fit_reasons", "Future rounds keep proof alive.")
    _assert_cli_list(output, "judgment_tradeoffs", "Proof beats speed when closure is uncertain.")
    _assert_cli_list(
        output,
        "execution_strategy",
        "Prove the focused path first, then expand after evidence is strong.",
    )
    _assert_cli_list(output, "local_governance", "GateKeeper treats skipped tests/ evidence as Blocking.")
    _assert_cli_list(output, "role_postures", "GateKeeper: Fail closed when evidence is weak.")


def test_cli_run_result_marks_truncated_judgment_summary(capsys, tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "runs" / "run_long_contract")
    layout.initialize()
    layout.run_contract_path.write_text(
        json.dumps(
            {
                "collaboration_summary": " ".join(["Evidence must stay visible before closure"] * 20),
                "completion_mode": "gatekeeper",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print_run_result(
        {
            "id": "run_long_contract",
            "status": "awaiting_agent",
            "run_status": "awaiting_agent",
            "runs_dir": str(layout.run_dir),
        }
    )

    output = capsys.readouterr().out
    summary_line = next(line for line in output.splitlines() if line.startswith("judgment_contract_summary: "))
    assert summary_line.endswith("...")
    assert len(summary_line) < 280


def test_cli_run_allows_zero_max_iters(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    calls: dict[str, object] = {}

    class FakeService:
        def create_loop(self, **kwargs):
            calls["create_loop"] = kwargs
            return {"id": "loop_test"}

        def rerun(self, loop_id: str, *, background: bool = False):
            calls["rerun"] = loop_id
            calls["background"] = background
            return {"id": "run_test", "status": "running", "runs_dir": str(tmp_path / "runs" / "run_test")}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "run",
            "--spec",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--max-iters",
            "0",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert calls["create_loop"]["max_iters"] == 0
    assert calls["rerun"] == "loop_test"
    assert calls["background"] is False


def test_cli_loop_creation_emits_structured_logs(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    class FakeService:
        def create_loop(self, **kwargs):
            return {"id": "loop_logged", "name": kwargs["name"], "workdir": str(kwargs["workdir"])}

        def rerun(self, loop_id: str, *, background: bool = False):
            raise AssertionError(f"loop creation without --start should not rerun: {loop_id=} {background=}")

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "loops",
            "create",
            "--spec",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--name",
            "Logged Loop",
        ],
    )

    assert result.exit_code == 0, result.stdout
    records = [
        json.loads(line)
        for line in (app_home() / "logs" / "service.log").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    created_record = next(item for item in records if item["event"] == "cli.loop.create.completed")
    assert created_record["loop_id"] == "loop_logged"
    assert created_record["context"]["start"] is False


@pytest.mark.parametrize("strategy_file_flag", ["--workflow-file", "--strategy-file"])
def test_cli_loop_create_accepts_parallel_strategy_file(strategy_file_flag: str, monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    workflow_path = tmp_path / "workflow.yml"
    workflow_path.write_text(
        """
version: 1
collaboration_intent: "Build first, then inspect contract and evidence in parallel before GateKeeper closes."
roles:
  - id: builder
    archetype: builder
    prompt_ref: builder.md
  - id: contract_inspector
    name: Contract Inspector
    archetype: inspector
    prompt_ref: inspector.md
  - id: evidence_inspector
    name: Evidence Inspector
    archetype: inspector
    prompt_ref: inspector.md
  - id: gatekeeper
    archetype: gatekeeper
    prompt_ref: gatekeeper.md
steps:
  - id: builder_step
    role_id: builder
  - id: contract_inspection_step
    role_id: contract_inspector
    parallel_group: inspection_pack
    inputs:
      handoffs_from: ["builder_step"]
      evidence_query:
        archetypes: ["builder"]
        limit: 8
      iteration_memory: summary_only
  - id: evidence_inspection_step
    role_id: evidence_inspector
    parallel_group: inspection_pack
    inputs:
      handoffs_from: ["builder_step"]
  - id: gatekeeper_step
    role_id: gatekeeper
    on_pass: finish_run
    inputs:
      handoffs_from: ["contract_inspection_step", "evidence_inspection_step"]
controls:
  - id: stale_evidence_check
    when:
      signal: no_evidence_progress
      after: 20m
    call:
      role_id: evidence_inspector
    mode: repair_guidance
    max_fires_per_run: 1
""",
        encoding="utf-8",
    )
    calls: dict[str, object] = {}

    class FakeService:
        def create_loop(self, **kwargs):
            calls["create_loop"] = kwargs
            return {"id": "loop_parallel", "name": kwargs["name"], "workdir": str(kwargs["workdir"])}

        def rerun(self, loop_id: str, *, background: bool = False):
            raise AssertionError(f"loop creation without --start should not rerun: {loop_id=} {background=}")

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "loops",
            "create",
            "--spec",
            str(spec_path),
            "--workdir",
            str(workdir),
            strategy_file_flag,
            str(workflow_path),
        ],
    )

    assert result.exit_code == 0, result.stdout
    workflow = calls["create_loop"]["workflow"]
    assert workflow["steps"][1]["parallel_group"] == "inspection_pack"
    assert workflow["steps"][1]["inputs"]["evidence_query"]["archetypes"] == ["builder"]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "contract_inspection_step",
        "evidence_inspection_step",
    ]
    assert workflow["controls"][0]["when"]["signal"] == "no_evidence_progress"
    assert workflow["controls"][0]["call"]["role_id"] == "evidence_inspector"


def test_cli_run_supports_command_mode_background_and_role_models(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    calls: dict[str, object] = {}

    class FakeService:
        def create_loop(self, **kwargs):
            calls["create_loop"] = kwargs
            return {"id": "loop_cmd", "name": kwargs["name"], "workdir": str(kwargs["workdir"])}

        def start_run(self, loop_id: str):
            calls["start_run"] = loop_id
            return {
                "id": "run_cmd",
                "status": "queued",
                "runs_dir": str(tmp_path / "runs" / "run_cmd"),
                "workdir": str(workdir),
            }

        def rerun(self, loop_id: str, *, background: bool = False):
            raise AssertionError(f"background CLI path should not call service.rerun(): {loop_id=} {background=}")

    monkeypatch.setattr(cli, "create_service", FakeService)

    def fake_spawn_background_worker(_service, run: dict):
        calls["spawned_run_id"] = run["id"]
        return run

    monkeypatch.setattr(cli, "_spawn_background_worker", fake_spawn_background_worker)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "run",
            "--spec",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--executor",
            "codex",
            "--executor-mode",
            "command",
            "--command-cli",
            "codex",
            "--command-arg",
            "exec",
            "--command-arg",
            "--json",
            "--command-arg",
            "--output-schema",
            "--command-arg",
            "{schema_path}",
            "--command-arg",
            "--output-last-message",
            "--command-arg",
            "{output_path}",
            "--command-arg",
            "--model",
            "--command-arg",
            "{model}",
            "--command-arg",
            "{prompt}",
            "--model",
            "gpt-5.4-mini",
            "--role-model",
            "generator=gpt-5.4",
            "--role-model",
            "verifier=gpt-5.4-mini",
            "--background",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert calls["start_run"] == "loop_cmd"
    assert calls["spawned_run_id"] == "run_cmd"
    assert calls["create_loop"]["executor_mode"] == "command"
    assert calls["create_loop"]["command_cli"] == "codex"
    assert "{schema_path}" in calls["create_loop"]["command_args_text"]
    assert "{model}" in calls["create_loop"]["command_args_text"]
    assert calls["create_loop"]["role_models"] == {
        "builder": "gpt-5.4",
        "gatekeeper": "gpt-5.4-mini",
    }


def test_cli_run_supports_round_completion_and_iteration_interval(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    calls: dict[str, object] = {}

    class FakeService:
        def create_loop(self, **kwargs):
            calls["create_loop"] = kwargs
            return {"id": "loop_rounds"}

        def rerun(self, loop_id: str, *, background: bool = False):
            assert background is False
            calls["rerun"] = loop_id
            return {"id": "run_rounds", "status": "succeeded", "runs_dir": str(tmp_path / "runs" / "run_rounds")}

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "run",
            "--spec",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--completion-mode",
            "rounds",
            "--iteration-interval-seconds",
            "60",
            "--max-iters",
            "2",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert calls["create_loop"]["completion_mode"] == "rounds"
    assert calls["create_loop"]["iteration_interval_seconds"] == 60.0
    assert calls["rerun"] == "loop_rounds"


def test_cli_loops_rerun_background_spawns_worker(monkeypatch, tmp_path: Path) -> None:
    calls: dict[str, object] = {}

    class FakeService:
        def start_run(self, loop_id: str):
            calls["start_run"] = loop_id
            return {
                "id": "run_background",
                "status": "queued",
                "runs_dir": str(tmp_path / "runs" / "run_background"),
                "workdir": str(tmp_path / "workdir"),
            }

        def rerun(self, loop_id: str, *, background: bool = False):
            raise AssertionError(f"background CLI path should not call service.rerun(): {loop_id=} {background=}")

    monkeypatch.setattr(cli, "create_service", FakeService)

    def fake_spawn_background_worker(_service, run: dict):
        calls["spawned"] = run["id"]
        return run

    monkeypatch.setattr(cli, "_spawn_background_worker", fake_spawn_background_worker)
    runner = CliRunner()

    result = runner.invoke(cli.app, ["loops", "rerun", "loop_saved", "--background"])

    assert result.exit_code == 0, result.stdout
    assert calls["start_run"] == "loop_saved"
    assert calls["spawned"] == "run_background"

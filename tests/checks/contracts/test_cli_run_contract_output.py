from __future__ import annotations

import json
from pathlib import Path

from cli_run_output_test_support import assert_cli_list, print_run_result_output
from loopora.run_artifacts import RunArtifactLayout


MAX_JUDGMENT_CONTRACT_SUMMARY_LINE_LENGTH = 280


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

    output = print_run_result_output(
        capsys,
        {
            "id": "run_bundle",
            "status": "succeeded",
            "run_status": "succeeded",
            "runs_dir": str(layout.run_dir),
            "task_verdict": {"status": "passed"},
        },
    )

    assert f"run_contract_path: {layout.run_contract_path}" in output
    assert "source_plan: CLI Frozen Contract Bundle (bundle_cli, rev 3)" in output
    assert "source_plan_path: /tmp/loopora/cli-bundle.yml" in output
    assert "source_plan_digest: sha256:abcdef123456, 2048 bytes" in output
    assert 'source_plan: {"id":' not in output
    assert "judgment_contract_summary: Prefer proof before speed." in output
    assert "check_mode: specified" in output
    assert "completion_mode: gatekeeper" in output
    assert "strategy_preset: quality_gate" in output
    assert "strategy_collaboration_intent: Builder evidence feeds Inspector review before GateKeeper closure." in output
    assert "workflow_preset:" not in output
    assert "workflow_collaboration_intent:" not in output
    assert "check_count: 2" in output
    assert_cli_list(output, "coverage_targets", "done_when.check_001 (required)", "gatekeeper.finish (required)")
    assert "evidence_preference.pref_003" in output
    assert_cli_list(output, "loop_fit_reasons", "Future rounds keep proof alive.")
    assert_cli_list(output, "judgment_tradeoffs", "Proof beats speed when closure is uncertain.")
    assert_cli_list(
        output,
        "execution_strategy",
        "Prove the focused path first, then expand after evidence is strong.",
    )
    assert_cli_list(output, "local_governance", "GateKeeper treats skipped tests/ evidence as Blocking.")
    assert_cli_list(output, "role_postures", "GateKeeper: Fail closed when evidence is weak.")


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

    output = print_run_result_output(
        capsys,
        {
            "id": "run_long_contract",
            "status": "awaiting_agent",
            "run_status": "awaiting_agent",
            "runs_dir": str(layout.run_dir),
        },
    )

    summary_line = next(line for line in output.splitlines() if line.startswith("judgment_contract_summary: "))
    assert summary_line.endswith("...")
    assert len(summary_line) < MAX_JUDGMENT_CONTRACT_SUMMARY_LINE_LENGTH

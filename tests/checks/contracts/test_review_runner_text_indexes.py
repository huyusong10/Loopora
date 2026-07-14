from __future__ import annotations

from pathlib import Path

from review_runner_test_support import write_artifact_paths_report, write_text_index_report


def test_concept_coherence_anchor_text_reaches_agent_first_execution_contract(tmp_path: Path) -> None:
    report = write_text_index_report("concept-coherence.md", "top-level-anchor-text", tmp_path)

    assert "Human-shaped Loop is not just the name of an essay." in report
    assert "Human-shaped Loop 不只是这篇文档的名字" in report
    assert "A candidate Loop cannot be only a task summary" in report
    assert "候选 Loop 不能只是任务摘要" in report
    assert "each step should inherit these judgments, action boundaries, and evidence gaps" in report
    assert "每一步都应继承这些判断、行动边界和证据缺口" in report


def test_concept_coherence_design_text_reaches_plan_and_run_contracts(tmp_path: Path) -> None:
    report = write_text_index_report("concept-coherence.md", "plan-run-contract-text", tmp_path)

    assert "The compiler turns task judgment into a reviewable and runnable Loop." in report
    assert "Web dialogue, Agent candidate plans, YAML import/export, preview, and run creation" in report
    assert "`/loopora-plan` creates, revises, repairs, or tightens reviewed Loop previews" in report
    assert "`/loopora-run` starts, resumes, replays, or continues evidence" in report
    assert "The default user model is linear and explainable" in report


def test_agent_native_handbook_reaches_real_probe_boundaries(tmp_path: Path) -> None:
    report = write_text_index_report("agent-native-behavior.md", "agent-native-handbook", tmp_path)

    assert "Agent Native lets the current Coding Agent remain the execution subject" in report
    assert "Real probes protect the real-environment boundary" in report
    assert "host-native dispatch" in report
    assert "native subagent / task mechanism" in report
    assert "`inline` to false" in report
    assert "output_schema" in report
    assert "known_evidence_ids" in report
    assert "Nested host CLI sentinels must remain silent." in report
    assert "Use these requirements to author, not copy, the candidate" in report
    assert "canonical candidate bundle draft" not in report
    assert '--show-playbook", action="store_true"' in report


def test_agent_native_missing_phase_report_hint_is_actionable(tmp_path: Path) -> None:
    report, hints = write_artifact_paths_report("agent-native-behavior.md", "real-probe-phase-reports", tmp_path)

    assert "Next evidence step:" in report
    assert "tests/probes/real_environment/README.md" in report
    assert "--suite real-agent" in report
    assert "--artifact phase=.loopora/real-probes/real-agent-phase-report.json" in report
    assert any("--suite real-agent" in hint for hint in hints)

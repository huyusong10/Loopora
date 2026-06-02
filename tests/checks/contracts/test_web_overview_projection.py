from __future__ import annotations

from pathlib import Path

from loopora.web_overviews import (
    _build_run_summary_snapshot,
    _decorate_loop_overview,
    _decorate_run_overview,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_web_task_verdict_overview_helpers_have_dedicated_boundary() -> None:
    overview_source = (REPO_ROOT / "src" / "loopora" / "web_overviews.py").read_text(encoding="utf-8")
    verdict_source = (REPO_ROOT / "src" / "loopora" / "web_task_verdict_overviews.py").read_text(encoding="utf-8")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.web_task_verdict_overviews import build_run_summary_snapshot as _build_run_summary_snapshot" in overview_source
    assert "def build_run_summary_snapshot" in verdict_source
    assert "def verdict_safe_excerpt_pair" in verdict_source
    assert "def _first_task_bucket_text" in verdict_source
    assert "def _first_task_bucket_text" not in overview_source
    assert "web_task_verdict_overviews.py" in contracts_source


def test_loop_overview_preserves_residual_risk_task_verdict() -> None:
    decorated = _decorate_loop_overview(
        {
            "id": "loop_1",
            "latest_run_id": "run_1",
            "latest_status": "succeeded",
            "latest_task_verdict_json": {
                "status": "passed_with_residual_risk",
                "source": "gatekeeper",
                "summary": "Accepted a visible follow-up risk.",
                "buckets": {"residual_risk": [{"label": "follow-up"}]},
            },
            "workflow_json": {},
        }
    )

    assert decorated["card_hint_en"] == "The latest task verdict passed with residual risk."
    assert decorated["card_hint_zh"] == "最近一次 Loop 裁决带残余风险通过。"

    summary = _build_run_summary_snapshot(
        {
            "status": "succeeded",
            "current_iter": 0,
            "summary_md": "",
            "last_verdict_json": {},
            "task_verdict": {
                "status": "passed_with_residual_risk",
                "source": "gatekeeper",
                "summary": "",
                "buckets": {"residual_risk": [{"label": "follow-up"}]},
            },
        }
    )

    assert summary["verdict_title_en"] == "Task verdict: passed with residual risk"
    assert summary["verdict_title_zh"] == "Loop 裁决：有残余风险地通过"
    assert summary["verdict_note_en"] == "follow-up"
    assert "Loop verdict" in summary["status_note_en"]
    assert "任务是否通过" in summary["status_note_zh"]


def test_web_overview_decorators_prefer_strategy_source_projection() -> None:
    strategy_source = {
        "roles": [{"id": "builder", "executor_kind": "codex"}],
        "steps": [{"id": "builder_step", "role_id": "builder"}],
    }
    stale_storage_source = {"roles": [], "steps": []}

    loop = _decorate_loop_overview(
        {"id": "loop_strategy", "strategy_source": strategy_source, "workflow_json": stale_storage_source}
    )
    run = _decorate_run_overview(
        {"id": "run_strategy", "strategy_source": strategy_source, "workflow_json": stale_storage_source}
    )

    assert loop["role_count"] == 1
    assert loop["step_count"] == 1
    assert run["role_executor_summary"] != "-"


def test_loop_overview_surfaces_unproven_terminal_task_verdicts() -> None:
    insufficient = _decorate_loop_overview(
        {
            "id": "loop_1",
            "latest_run_id": "run_1",
            "latest_status": "succeeded",
            "latest_task_verdict_json": {
                "status": "insufficient_evidence",
                "source": "gatekeeper",
                "summary": "Missing proof.",
            },
            "latest_summary_md": "# Loopora Run Summary\n\nAll done according to the Agent summary.",
            "workflow_json": {},
        }
    )
    failed = _decorate_loop_overview(
        {
            "id": "loop_2",
            "latest_run_id": "run_2",
            "latest_status": "failed",
            "latest_task_verdict_json": {
                "status": "failed",
                "source": "run_status",
                "summary": "Blocked.",
            },
            "workflow_json": {},
        }
    )

    assert insufficient["card_hint_en"] == "The latest task verdict has insufficient evidence."
    assert insufficient["card_hint_zh"] == "最近一次 Loop 裁决证据不足。"
    assert insufficient["card_excerpt_en"] == "Task verdict still insufficient: Missing proof."
    assert insufficient["card_excerpt_zh"] == "Loop 裁决证据不足：Missing proof."
    assert "All done" not in insufficient["card_excerpt_en"]
    assert failed["card_hint_en"] == "The latest task verdict failed."
    assert failed["card_hint_zh"] == "最近一次 Loop 裁决未通过。"

    summary = _build_run_summary_snapshot(
        {
            "status": "succeeded",
            "current_iter": 0,
            "summary_md": "# Loopora Run Summary\n\nAll done according to the Agent summary.",
            "last_verdict_json": {},
            "task_verdict": {
                "status": "insufficient_evidence",
                "source": "gatekeeper",
                "summary": "Missing proof.",
            },
        }
    )
    assert summary["summary_excerpt_en"] == "Task verdict still insufficient: Missing proof."
    assert summary["summary_excerpt_zh"] == "Loop 裁决证据不足：Missing proof."
    assert "All done" not in summary["summary_excerpt_en"]

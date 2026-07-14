from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from fastapi.testclient import TestClient
from runner_helpers import _create_loop
from strategy_source_architecture_test_support import design_boundary_source

from loopora.run_result_recording import (
    RUN_RESULT_LIFECYCLE_FAILURE_BLOCKED_REASON,
    RUN_RESULT_NOT_EVALUATED_BLOCKED_REASON,
)
from loopora.run_worker_start import BACKGROUND_WORKER_START_ERROR
from loopora.web import build_app
from loopora.web_home_attention import (
    decorate_home_loop_overview,
    home_loop_sections,
    loop_needs_active_attention,
    select_home_recent_loops,
    sort_home_attention_loops,
)
from loopora.web_overviews import (
    _build_run_summary_snapshot,
    _decorate_loop_overview,
    _decorate_run_overview,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def _assert_alignment_resume_href(href: str, *, session_id: str, workdir: Path | str) -> None:
    parts = urlsplit(href)
    query = parse_qs(parts.query)
    assert parts.path == "/loops/new/bundle"
    assert query.get("alignment_session_id") == [session_id]
    assert query.get("workdir") == [str(Path(workdir).resolve())]


def test_web_task_verdict_overview_helpers_have_dedicated_boundary() -> None:
    overview_source = (REPO_ROOT / "src" / "loopora" / "web_overviews.py").read_text(encoding="utf-8")
    verdict_source = (REPO_ROOT / "src" / "loopora" / "web_task_verdict_overviews.py").read_text(encoding="utf-8")
    home_attention_source = (REPO_ROOT / "src" / "loopora" / "web_home_attention.py").read_text(encoding="utf-8")
    route_pages_source = (REPO_ROOT / "src" / "loopora" / "web_route_pages.py").read_text(encoding="utf-8")
    home_create_route_source = (REPO_ROOT / "src" / "loopora" / "web_home_create_page_routes.py").read_text(encoding="utf-8")
    contracts_source = design_boundary_source()

    assert "from loopora.web_task_verdict_overviews import build_run_summary_snapshot as _build_run_summary_snapshot" in overview_source
    assert "def build_run_summary_snapshot" in verdict_source
    assert "def verdict_safe_excerpt_pair" in verdict_source
    assert "def _first_task_bucket_text" in verdict_source
    assert "def _first_task_bucket_text" not in overview_source
    assert "def sort_home_attention_loops" in home_attention_source
    assert "def select_home_recent_loops" in home_attention_source
    assert "def home_loop_sections" in home_attention_source
    assert "def _home_attention_projection" in home_attention_source
    assert "def _with_home_loop_start_projection" in home_attention_source
    assert "agent_entry_loop_start_projection" in home_attention_source
    assert "def _loop_card_href" in overview_source
    assert "def _loop_detail_href" in overview_source
    assert "def _alignment_session_card_href" in home_attention_source
    assert "def _home_attention_projection" not in route_pages_source
    assert "def _home_attention_projection" not in home_create_route_source
    assert "workdir_context = request_workdir_context(request)" in home_create_route_source
    assert "loop_sections = home_loop_sections(service, workdir_context=workdir_context)" in home_create_route_source
    assert "all_loop_sections = home_loop_sections(service) if workdir_context else loop_sections" in home_create_route_source
    assert "active_loop_ids =" not in home_create_route_source
    assert "web_task_verdict_overviews.py" in contracts_source
    assert "web_home_attention.py" in contracts_source


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
        {"id": "loop_strategy", "workdir": "/tmp/project", "strategy_source": strategy_source, "workflow_json": stale_storage_source}
    )
    run = _decorate_run_overview({"id": "run_strategy", "strategy_source": strategy_source, "workflow_json": stale_storage_source})

    assert (loop["role_count"], loop["step_count"], loop["card_href"], loop["detail_href"], loop["start_run_action"]) == (
        1,
        1,
        "/loops/loop_strategy?workdir=%2Ftmp%2Fproject",
        "/loops/loop_strategy?workdir=%2Ftmp%2Fproject",
        "/loops/loop_strategy/runs?workdir=%2Ftmp%2Fproject",
    )
    assert run["role_executor_summary"] != "-"


def test_loop_overview_splits_card_activity_from_loop_detail_href() -> None:
    loop = _decorate_loop_overview({"id": "loop_strategy", "workdir": "/tmp/project", "latest_run_id": "run_latest"})

    assert loop["card_href"] == "/runs/run_latest?workdir=%2Ftmp%2Fproject"
    assert loop["detail_href"] == "/loops/loop_strategy?workdir=%2Ftmp%2Fproject"
    assert loop["start_run_action"] == "/loops/loop_strategy/runs?workdir=%2Ftmp%2Fproject"


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


def test_web_overview_surfaces_lifecycle_failure_as_retry_not_evidence_gap() -> None:
    lifecycle_failed = _decorate_loop_overview(
        {
            "id": "loop_lifecycle",
            "latest_run_id": "run_lifecycle",
            "latest_status": "failed",
            "latest_error_message": BACKGROUND_WORKER_START_ERROR,
            "latest_task_verdict_json": {
                "status": "not_evaluated",
                "source": "lifecycle",
                "summary": "No evidence work started.",
            },
            "latest_summary_md": "# Loopora Run Summary\n\nAll done according to the Agent summary.",
            "workflow_json": {},
        }
    )
    summary = _build_run_summary_snapshot(
        {
            "status": "failed",
            "error_message": BACKGROUND_WORKER_START_ERROR,
            "summary_md": "# Loopora Run Summary\n\nAll done according to the Agent summary.",
            "task_verdict": {
                "status": "not_evaluated",
                "source": "lifecycle",
                "summary": "No evidence work started.",
            },
        }
    )

    assert lifecycle_failed["card_hint_en"] == "The latest run failed to start and needs retry."
    assert lifecycle_failed["card_hint_zh"] == "最近一次运行启动失败，需要重试运行。"
    assert lifecycle_failed["card_excerpt_en"] == "Run start failed: no recordable evidence was produced; retry the run."
    assert lifecycle_failed["card_excerpt_zh"] == "运行启动失败：未产生可记录证据，先重试运行。"
    assert "All done" not in lifecycle_failed["card_excerpt_en"]
    assert "Task verdict not evaluated" not in lifecycle_failed["card_excerpt_en"]
    assert summary["verdict_title_en"] == "Run start failed"
    assert summary["verdict_title_zh"] == "运行启动失败"
    assert summary["summary_excerpt_en"] == "Run start failed: no recordable evidence was produced; retry the run."
    assert summary["summary_excerpt_zh"] == "运行启动失败：未产生可记录证据，先重试运行。"
    assert "retry run start" in summary["status_note_en"]


def test_service_loop_list_carries_latest_lifecycle_failure_for_web_overview(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Lifecycle Failure Overview Loop")
    run = service.start_run(loop["id"])
    service.repository.update_run(
        run["id"],
        status="failed",
        error_message=BACKGROUND_WORKER_START_ERROR,
        summary_md="# Loopora Run Summary\n\nAll done according to the Agent summary.",
        task_verdict={
            "status": "not_evaluated",
            "source": "run_status",
            "summary": "No evidence work started.",
        },
    )

    loop_overview = next(item for item in service.list_loops() if item["id"] == loop["id"])
    decorated = _decorate_loop_overview(loop_overview)

    assert loop_overview["latest_error_message"] == BACKGROUND_WORKER_START_ERROR
    assert decorated["card_hint_en"] == "The latest run failed to start and needs retry."
    assert decorated["card_excerpt_en"] == "Run start failed: no recordable evidence was produced; retry the run."
    assert "All done" not in decorated["card_excerpt_en"]
    assert "Task verdict not evaluated" not in decorated["card_excerpt_en"]


def test_home_returning_attention_action_links_to_primary_active_work(
    service_factory,
    sample_spec_file: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    current_workdir = tmp_path / "current-project"
    current_workdir.mkdir()
    loop = _create_loop(service, sample_spec_file, current_workdir, name="Evidence Gap Loop")
    run = service.start_run(loop["id"])
    service.repository.update_run(
        run["id"],
        status="succeeded",
        summary_md="# Loopora Run Summary\n\nCoverage still needs direct evidence.",
        task_verdict={
            "status": "insufficient_evidence",
            "source": "gatekeeper",
            "summary": "Coverage still needs direct evidence.",
        },
    )
    client = TestClient(build_app(service=service))
    encoded_current = quote(str(current_workdir.resolve()), safe="")

    current_home = client.get(f"/?workdir={encoded_current}")

    assert current_home.status_code == 200
    assert 'data-testid="home-returning-attention-link"' in current_home.text
    assert (
        f'href="/runs/{run["id"]}?workdir={encoded_current}" data-testid="home-returning-attention-link" data-workdir-context-link="workdir"'
    ) in current_home.text
    assert 'href="#activity" data-testid="home-returning-attention-link"' not in current_home.text
    assert 'data-testid="home-active-loop"' in current_home.text
    assert "Review Recent Activity" not in current_home.text


def test_home_returning_state_labels_recent_activity_without_attention(
    service_factory,
    sample_spec_file: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    current_workdir = tmp_path / "current-project"
    current_workdir.mkdir()
    loop = _create_loop(service, sample_spec_file, current_workdir, name="Completed Evidence Loop")
    run = service.start_run(loop["id"])
    service.repository.update_run(
        run["id"],
        status="succeeded",
        summary_md="# Loopora Run Summary\n\nEvidence passed.",
        task_verdict={"status": "passed", "source": "gatekeeper", "summary": "Evidence passed."},
    )
    client = TestClient(build_app(service=service))
    encoded_current = quote(str(current_workdir.resolve()), safe="")

    current_home = client.get(f"/?workdir={encoded_current}")

    assert current_home.status_code == 200
    assert 'data-testid="home-returning-recent-link"' in current_home.text
    assert (
        f'href="/runs/{run["id"]}?workdir={encoded_current}" data-testid="home-returning-recent-link" data-workdir-context-link="workdir"'
    ) in current_home.text
    assert 'href="#activity" data-testid="home-returning-recent-link"' not in current_home.text
    assert 'data-testid="home-returning-attention-link"' not in current_home.text
    assert "Review Recent Activity" in current_home.text
    assert "Recent activity" in current_home.text
    assert "Review Needs Attention" not in current_home.text
    assert "Attention</span> 0" not in current_home.text


def test_home_filtered_empty_state_can_clear_target_context(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Global Saved Loop")
    other_workdir = tmp_path / "other-target"
    other_workdir.mkdir()
    encoded_other_workdir = quote(str(other_workdir.resolve()), safe="")
    client = TestClient(build_app(service=service))

    filtered_home = client.get(f"/?workdir={encoded_other_workdir}")
    filtered_create_choice = client.get(f"/loops/new?workdir={encoded_other_workdir}")
    global_home = client.get("/")

    assert filtered_home.status_code == 200
    assert filtered_create_choice.status_code == 200
    assert global_home.status_code == 200
    assert f'href="/loops/{loop["id"]}?workdir={quote(str(sample_workdir.resolve()), safe="")}"' not in filtered_home.text
    assert f'href="/loops/{loop["id"]}?workdir={quote(str(sample_workdir.resolve()), safe="")}"' in global_home.text
    assert 'data-testid="home-empty-show-all-link"' in filtered_home.text
    assert 'href="/" data-testid="home-empty-show-all-link"' in filtered_home.text
    assert 'data-testid="home-empty-show-all-link" data-workdir-context-link=' not in filtered_home.text
    assert 'data-testid="loops-empty-show-all-link"' in filtered_home.text
    assert 'href="/" data-testid="loops-empty-show-all-link"' in filtered_home.text
    assert f'href="/loops/new?workdir={encoded_other_workdir}" data-testid="loops-empty-create-choice-link"' in filtered_home.text
    assert 'data-testid="home-activity-show-all-link"' not in filtered_home.text
    assert 'data-testid="loop-create-existing-show-all-link"' in filtered_create_choice.text
    assert 'href="/" data-existing-action-kind="view_all_work" data-testid="loop-create-existing-show-all-link"' in filtered_create_choice.text
    assert 'data-testid="loop-create-existing-empty-state"' not in filtered_create_choice.text


class _AcceptanceService:
    def __init__(
        self,
        accepted_run_ids: set[str] | None = None,
        unrecordable_run_ids: set[str] | dict[str, str] | None = None,
        loops: list[dict] | None = None,
        alignment_sessions: list[dict] | None = None,
        repository: object | None = None,
    ) -> None:
        self._accepted_run_ids = accepted_run_ids or set()
        self._recording_blocked_reasons = unrecordable_run_ids if isinstance(unrecordable_run_ids, dict) else {}
        self._unrecordable_run_ids = set(self._recording_blocked_reasons) if isinstance(unrecordable_run_ids, dict) else unrecordable_run_ids or set()
        self._loops = loops or []
        self._alignment_sessions = alignment_sessions or []
        self.repository = repository

    def list_loops(self) -> list[dict]:
        return self._loops

    def list_alignment_sessions(self, *, limit: int = 30) -> list[dict]:
        return self._alignment_sessions[:limit]

    def run_result_acceptance_state(self, run_id: str) -> dict:
        if run_id in self._unrecordable_run_ids:
            return {
                "accepted": False,
                "recordable": False,
                "recording_blocked_reason": self._recording_blocked_reasons.get(
                    run_id,
                    RUN_RESULT_LIFECYCLE_FAILURE_BLOCKED_REASON,
                ),
            }
        if run_id not in self._accepted_run_ids:
            return {"accepted": False, "recordable": True}
        return {
            "accepted": True,
            "recorded_verdict_kind": "unproven_verdict_recorded",
            "recorded_coverage_target_basis": {
                "required": {"total": 2, "covered": 2, "open": 0},
                "advisory": {"total": 2, "covered": 1, "open": 1},
            },
            "recorded_advisory_follow_up_available": True,
        }

class _AlignmentSessionRepository:
    def __init__(self, sessions: list[dict]) -> None:
        self._sessions = sessions

    def list_all_alignment_sessions(self) -> list[dict]:
        return self._sessions


def _home_loop_record(
    loop_id: str,
    *,
    run_id: str,
    status: str,
    verdict_status: str,
    updated_at: str = "2026-06-16T00:00:00+00:00",
    **overrides: object,
) -> dict:
    record = {
        "id": loop_id,
        "workdir": "/tmp/project",
        "latest_run_id": run_id,
        "latest_status": status,
        "latest_run_updated_at": updated_at,
        "latest_task_verdict_json": {
            "status": verdict_status,
            "source": "gatekeeper",
            "summary": "Needs direct proof.",
        },
        "workflow_json": {},
    }
    record.update(overrides)
    return record


def test_home_attention_projection_separates_reason_action_and_recorded_state() -> None:
    service = _AcceptanceService(
        accepted_run_ids={"run_recorded"},
        unrecordable_run_ids={
            "run_recovery": RUN_RESULT_LIFECYCLE_FAILURE_BLOCKED_REASON,
            "run_not_evaluated": RUN_RESULT_NOT_EVALUATED_BLOCKED_REASON,
        },
    )
    evidence_gap = decorate_home_loop_overview(
        service,
        _home_loop_record(
            "loop_evidence",
            run_id="run_evidence",
            status="succeeded",
            verdict_status="insufficient_evidence",
        ),
    )
    awaiting = decorate_home_loop_overview(
        service,
        _home_loop_record("loop_agent", run_id="run_agent", status="awaiting_agent", verdict_status="not_evaluated"),
    )
    recorded = decorate_home_loop_overview(
        service,
        _home_loop_record(
            "loop_recorded",
            run_id="run_recorded",
            status="succeeded",
            verdict_status="insufficient_evidence",
        ),
    )
    recovery = decorate_home_loop_overview(
        service,
        _home_loop_record(
            "loop_recovery",
            run_id="run_recovery",
            status="failed",
            verdict_status="not_evaluated",
        ),
    )
    not_evaluated = decorate_home_loop_overview(
        service,
        _home_loop_record(
            "loop_not_evaluated",
            run_id="run_not_evaluated",
            status="succeeded",
            verdict_status="not_evaluated",
        ),
    )

    assert loop_needs_active_attention(evidence_gap) is True
    assert evidence_gap["attention_reason_kind"] == "needs_evidence"
    assert evidence_gap["attention_action_kind"] == "continue_evidence"
    assert evidence_gap["attention_priority"] == 30
    assert loop_needs_active_attention(awaiting) is True
    assert awaiting["attention_reason_kind"] == "awaiting_agent"
    assert awaiting["attention_action_kind"] == "continue_agent"
    assert awaiting["attention_priority"] == 20
    assert recorded["latest_run_result_accepted"] is True
    assert recorded["attention_reason_kind"] == "recorded_result"
    assert recorded["attention_action_kind"] == "review_recorded_result"
    assert recorded["latest_run_result_recorded_required_target_count"] == 2
    assert recorded["latest_run_result_recorded_required_covered_count"] == 2
    assert recorded["latest_run_result_recorded_advisory_open_count"] == 1
    assert recorded["latest_run_result_recorded_advisory_follow_up_available"] is True
    assert loop_needs_active_attention(recorded) is False
    assert recovery["latest_run_result_recordable"] is False
    assert loop_needs_active_attention(recovery) is True
    assert recovery["attention_reason_kind"] == "run_recovery"
    assert recovery["attention_action_kind"] == "retry_run"
    assert recovery["attention_priority"] == 15
    assert not_evaluated["latest_run_result_recordable"] is False
    assert loop_needs_active_attention(not_evaluated) is True
    assert not_evaluated["attention_reason_kind"] == "not_evaluated"
    assert not_evaluated["attention_action_kind"] == "review_unvalidated_verdict"
    assert not_evaluated["attention_priority"] == 40


def test_home_attention_sort_prioritizes_human_intervention_then_recency() -> None:
    service = _AcceptanceService()
    older_evidence_gap = decorate_home_loop_overview(
        service,
        _home_loop_record(
            "loop_old_evidence",
            run_id="run_old_evidence",
            status="succeeded",
            verdict_status="insufficient_evidence",
            updated_at="2026-06-16T00:00:00+00:00",
        ),
    )
    newer_evidence_gap = decorate_home_loop_overview(
        service,
        _home_loop_record(
            "loop_new_evidence",
            run_id="run_new_evidence",
            status="succeeded",
            verdict_status="insufficient_evidence",
            updated_at="2026-06-16T01:00:00+00:00",
        ),
    )
    active_progress = decorate_home_loop_overview(
        service,
        _home_loop_record(
            "loop_progress",
            run_id="run_progress",
            status="running",
            verdict_status="not_evaluated",
            updated_at="2026-06-16T02:00:00+00:00",
        ),
    )

    sorted_loops = sort_home_attention_loops([active_progress, older_evidence_gap, newer_evidence_gap])

    assert [loop["id"] for loop in sorted_loops] == ["loop_new_evidence", "loop_old_evidence", "loop_progress"]


def test_home_recent_selection_uses_latest_run_recency_and_excludes_attention_loops() -> None:
    service = _AcceptanceService()
    active_gap = decorate_home_loop_overview(
        service,
        _home_loop_record(
            "loop_active_gap",
            run_id="run_active_gap",
            status="succeeded",
            verdict_status="insufficient_evidence",
            updated_at="2026-06-16T03:00:00+00:00",
        ),
    )
    older_terminal = decorate_home_loop_overview(
        service,
        _home_loop_record(
            "loop_old_done",
            run_id="run_old_done",
            status="succeeded",
            verdict_status="passed",
            updated_at="2026-06-16T01:00:00+00:00",
        ),
    )
    newer_terminal = decorate_home_loop_overview(
        service,
        _home_loop_record(
            "loop_new_done",
            run_id="run_new_done",
            status="succeeded",
            verdict_status="passed",
            updated_at="2026-06-16T02:00:00+00:00",
        ),
    )

    recent_loops = select_home_recent_loops(
        [older_terminal, active_gap, newer_terminal],
        active_loop_ids={"loop_active_gap"},
    )

    assert [loop["id"] for loop in recent_loops] == ["loop_new_done", "loop_old_done"]


def test_home_loop_sections_owns_active_and_recent_selection() -> None:
    service = _AcceptanceService(
        loops=[
            _home_loop_record(
                "loop_old_done",
                run_id="run_old_done",
                status="succeeded",
                verdict_status="passed",
                updated_at="2026-06-16T01:00:00+00:00",
            ),
            _home_loop_record(
                "loop_attention",
                run_id="run_attention",
                status="succeeded",
                verdict_status="insufficient_evidence",
                updated_at="2026-06-16T03:00:00+00:00",
            ),
            _home_loop_record(
                "loop_new_done",
                run_id="run_new_done",
                status="succeeded",
                verdict_status="passed",
                updated_at="2026-06-16T02:00:00+00:00",
            ),
        ]
    )

    sections = home_loop_sections(service)

    assert [(loop["id"], loop["card_href"]) for loop in sections["active_loops"]] == [("loop_attention", "/runs/run_attention?workdir=%2Ftmp%2Fproject")]
    assert [loop["id"] for loop in sections["recent_loops"]] == ["loop_new_done", "loop_old_done"]


def test_home_loop_sections_surfaces_active_and_ready_alignment_sessions_by_workdir(tmp_path: Path) -> None:
    current_workdir = tmp_path / "current-project"
    other_workdir = tmp_path / "other-project"
    service = _AcceptanceService(
        alignment_sessions=[
            {
                "id": "align_current",
                "status": "repairing",
                "workdir": str(current_workdir),
                "title": "Compose the release workflow",
                "last_message": "Agent is drafting the loop.",
                "updated_at": "2026-06-16T04:00:00+00:00",
            },
            {
                "id": "align_other",
                "status": "running",
                "workdir": str(other_workdir),
                "title": "Other project compose",
                "updated_at": "2026-06-16T05:00:00+00:00",
            },
            {
                "id": "align_ready",
                "status": "ready",
                "workdir": str(current_workdir),
                "title": "Ready plan",
                "last_message": "Candidate plan is ready.",
                "updated_at": "2026-06-16T06:00:00+00:00",
            },
            {
                "id": "align_imported",
                "status": "ready",
                "workdir": str(current_workdir),
                "title": "Imported plan",
                "linked_bundle_id": "bundle_imported",
                "updated_at": "2026-06-16T07:00:00+00:00",
            },
        ],
    )

    global_sections = home_loop_sections(service)
    scoped_sections = home_loop_sections(service, workdir_context=str(current_workdir / ".." / "current-project"))

    assert [item["id"] for item in global_sections["active_loops"]] == ["align_ready", "align_other", "align_current"]
    assert [item["id"] for item in scoped_sections["active_loops"]] == ["align_ready", "align_current"]
    active_item = scoped_sections["active_loops"][0]
    assert active_item["source_kind"] == "alignment_session"
    assert active_item["latest_status"] == "ready"
    _assert_alignment_resume_href(active_item["card_href"], session_id="align_ready", workdir=current_workdir)
    assert active_item["attention_reason_kind"] == "alignment_ready"
    assert active_item["attention_action_kind"] == "review_alignment_bundle"
    assert active_item["attention_priority"] == 25
    assert active_item["card_hint_en"] == "Review the READY candidate, then create the Loop."
    assert active_item["card_excerpt_en"] == "Candidate plan is ready."
    assert scoped_sections["active_loops"][1]["attention_reason_kind"] == "alignment_active"
    assert scoped_sections["active_loops"][1]["attention_action_kind"] == "resume_alignment_session"


def test_home_loop_sections_does_not_page_out_same_target_active_alignment_session(tmp_path: Path) -> None:
    current_workdir = tmp_path / "current-project"
    other_workdir = tmp_path / "other-project"
    current_workdir.mkdir()
    other_workdir.mkdir()
    sessions = [
        {
            "id": f"ready_other_{index}",
            "status": "ready",
            "workdir": str(other_workdir),
            "bundle_path": str(tmp_path / "alignment_sessions" / f"ready_other_{index}" / "bundle.yaml"),
            "transcript": [{"role": "user", "content": f"Finished other project {index}"}],
            "updated_at": f"2026-06-16T05:{index:02d}:00+00:00",
            "created_at": "2026-06-16T00:00:00+00:00",
        }
        for index in range(35)
    ]
    sessions.append(
        {
            "id": "align_current_old",
            "status": "running",
            "workdir": str(current_workdir),
            "bundle_path": str(tmp_path / "alignment_sessions" / "align_current_old" / "bundle.yaml"),
            "transcript": [{"role": "user", "content": "Current project compose should remain visible."}],
            "updated_at": "2026-06-15T00:00:00+00:00",
            "created_at": "2026-06-15T00:00:00+00:00",
        }
    )
    service = _AcceptanceService(
        alignment_sessions=sessions[:30],
        repository=_AlignmentSessionRepository(sessions),
    )

    sections = home_loop_sections(service, workdir_context=str(current_workdir))

    assert [item["id"] for item in sections["active_loops"]] == ["align_current_old"]
    assert sections["active_loops"][0]["name"] == "Current project compose should remain visible."
    _assert_alignment_resume_href(
        sections["active_loops"][0]["card_href"],
        session_id="align_current_old",
        workdir=current_workdir,
    )


def test_home_loop_sections_keeps_recent_loop_when_alignment_session_reuses_id() -> None:
    service = _AcceptanceService(
        loops=[
            _home_loop_record(
                "shared_id",
                run_id="run_shared",
                status="succeeded",
                verdict_status="passed",
            ),
        ],
        alignment_sessions=[
            {
                "id": "shared_id",
                "status": "running",
                "workdir": "/tmp/project",
                "title": "Active Web conversation with reused id",
                "updated_at": "2026-06-16T04:00:00+00:00",
            },
        ],
    )

    sections = home_loop_sections(service)

    assert [item["source_kind"] for item in sections["active_loops"]] == ["alignment_session"]
    assert [loop["id"] for loop in sections["recent_loops"]] == ["shared_id"]


def test_home_loop_sections_scopes_to_requested_workdir_context(tmp_path: Path) -> None:
    current_workdir = tmp_path / "current-project"
    other_workdir = tmp_path / "other-project"
    service = _AcceptanceService(
        loops=[
            _home_loop_record(
                "loop_current",
                run_id="run_current",
                status="succeeded",
                verdict_status="insufficient_evidence",
                workdir=str(current_workdir),
            ),
            _home_loop_record(
                "loop_other",
                run_id="run_other",
                status="succeeded",
                verdict_status="insufficient_evidence",
                workdir=str(other_workdir),
            ),
        ]
    )

    global_sections = home_loop_sections(service)
    scoped_sections = home_loop_sections(service, workdir_context=str(current_workdir / ".." / "current-project"))

    assert [loop["id"] for loop in global_sections["loops"]] == ["loop_current", "loop_other"]
    assert [loop["id"] for loop in scoped_sections["loops"]] == ["loop_current"]
    assert [loop["id"] for loop in scoped_sections["active_loops"]] == ["loop_current"]

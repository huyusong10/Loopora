from __future__ import annotations

# Merged from alignment_workdir_context_test_support.py
class FakeAlignmentWorkdirContextRepository:
    def __init__(self, sessions: list[dict]) -> None:
        self.sessions = sessions
        self.list_limits: list[int] = []

    def list_alignment_sessions(self, *, limit: int = 100) -> list[dict]:
        self.list_limits.append(limit)
        return self.sessions[:limit]

# Merged from alignment_bundle_lifecycle_test_support.py
from loopora.service_alignment_bundle_lifecycle import AlignmentBundleLifecycleContext


class FakeAlignmentLifecycleRepository:
    def __init__(self, session: dict) -> None:
        self.session = dict(session)
        self.events: list[dict] = []

    def update_alignment_session(self, session_id: str, **fields: object) -> dict:
        assert session_id == self.session["id"]
        self.session.update(fields)
        return dict(self.session)

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict:
        assert session_id == self.session["id"]
        event = {"event_type": event_type, "payload": payload}
        self.events.append(event)
        return event


def lifecycle_context(
    repo: FakeAlignmentLifecycleRepository,
    validation_logs: list[tuple[str, dict]],
) -> AlignmentBundleLifecycleContext:
    def get_session(session_id: str) -> dict:
        assert session_id == repo.session["id"]
        return dict(repo.session)

    def write_validation_log(session: dict, payload: dict) -> None:
        validation_logs.append((session["id"], payload))

    return AlignmentBundleLifecycleContext(
        repository=repo,
        get_session=get_session,
        write_validation_log=write_validation_log,
    )

# Merged from alignment_clarifying_dialogue_test_support.py
from pathlib import Path
from typing import Any

from alignment_test_support import _wait_for_status

DEFAULT_EN_ALIGNMENT_MESSAGE = "I need help shaping this task."
DEFAULT_ZH_ALIGNMENT_MESSAGE = "请帮我编排一个长期任务。"


def start_waiting_alignment(
    service_factory: Any,
    sample_workdir: Path,
    *,
    scenario: str,
    message: str,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    service = service_factory(scenario=scenario)
    created = service.create_alignment_session(workdir=sample_workdir, message=message)
    return service, created, _wait_for_status(service, created["id"], "waiting_user")


def latest_transcript_message(session: dict[str, Any]) -> dict[str, Any]:
    return session["transcript"][-1]


def latest_assistant_content(session: dict[str, Any]) -> str:
    return str(latest_transcript_message(session)["content"])


def assert_bundle_not_written(session: dict[str, Any]) -> None:
    assert not Path(session["bundle_path"]).exists()


def assert_first_decision_option_recommended(session: dict[str, Any]) -> None:
    assert latest_transcript_message(session)["decision_options"][0]["recommended"] is True


def assert_question_reframed(service: Any, session_id: str, expected_issues: set[str]) -> None:
    events = service.list_alignment_events(session_id)
    assert any(
        event["event_type"] == "alignment_question_reframed"
        and expected_issues.issubset(set(event["payload"].get("issues", [])))
        for event in events
    )

# Merged from alignment_session_projection_test_support.py
from loopora.service_alignment_session_projection import AlignmentSessionAccessContext


class FakeAlignmentSessionProjectionRepository:
    def __init__(self, sessions: list[dict], events_by_session: dict[str, list[dict]] | None = None) -> None:
        self.sessions = {str(session["id"]): dict(session) for session in sessions}
        self.events_by_session = events_by_session or {}
        self.list_limits: list[int] = []

    def get_alignment_session(self, session_id: str) -> dict | None:
        session = self.sessions.get(session_id)
        return dict(session) if session else None

    def list_alignment_sessions(self, *, limit: int = 30) -> list[dict]:
        self.list_limits.append(limit)
        return [dict(session) for session in self.sessions.values()][:limit]

    def list_alignment_events(self, session_id: str, *, after_id: int = 0, limit: int = 200) -> list[dict]:
        return [
            dict(event)
            for event in self.events_by_session.get(session_id, [])
            if int(event.get("id") or 0) > int(after_id or 0)
        ][:limit]

    def latest_alignment_event_id(self, session_id: str) -> int:
        events = self.events_by_session.get(session_id, [])
        return max([int(event.get("id") or 0) for event in events], default=0)


def session_access_context(
    repo: FakeAlignmentSessionProjectionRepository,
    *,
    ensure_calls: list[str] | None = None,
) -> AlignmentSessionAccessContext:
    def ensure_session_layout(session: dict) -> dict:
        if ensure_calls is not None:
            ensure_calls.append(str(session["id"]))
        return {**session, "layout_checked": True}

    return AlignmentSessionAccessContext(
        repository=repo,
        ensure_session_layout=ensure_session_layout,
        candidate_event=lambda session_id: {
            "event_type": "agent_candidate_received",
            "payload": {
                "candidate_origin": "agent_entry",
                "requires_web_alignment": True,
                "requires_candidate_repair": False,
                "adapter": "codex",
                "entry_source": "codex_project_skill",
                "host_context_id": f"thread:{session_id}",
                "has_candidate_yaml": True,
            },
        },
        ready_event=lambda session_id: {"event_type": "ready", "payload": {"session_id": session_id}},
        active_statuses={"running"},
        missing_judgment_item_ids=["task_scope"],
    )

# Merged from alignment_bundle_candidate_test_support.py

from loopora.service_alignment_bundle_candidate import AlignmentBundleCandidateContext


class FakeAlignmentBundleCandidateRepository:
    def __init__(self, session: dict) -> None:
        self.session = dict(session)
        self.events: list[dict] = []

    def update_alignment_session(self, session_id: str, **fields: object) -> dict:
        assert session_id == self.session["id"]
        self.session.update(fields)
        return dict(self.session)

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict:
        assert session_id == self.session["id"]
        event = {"event_type": event_type, "payload": payload}
        self.events.append(event)
        return event


def bundle_candidate_context(
    repo: FakeAlignmentBundleCandidateRepository,
    *,
    validation_error: Exception | None = None,
) -> tuple[AlignmentBundleCandidateContext, list[dict], list[dict], list[dict]]:
    validation_logs: list[dict] = []
    transition_plans: list[dict] = []
    failures: list[dict] = []

    def get_session(session_id: str) -> dict:
        assert session_id == repo.session["id"]
        return dict(repo.session)

    def load_validated_bundle_text(_session: dict, raw_yaml: str, semantic_issues: list[str]) -> tuple[dict, str]:
        if validation_error is not None:
            semantic_issues.append("loop.done_when")
            raise validation_error
        return {"loop": {"name": "Candidate Loop"}}, raw_yaml.rstrip() + "\n# normalized\n"

    def write_validation_log(session: dict, validation: dict) -> None:
        validation_logs.append({"session": session, "validation": validation})

    def lifecycle_context() -> AlignmentBundleLifecycleContext:
        return AlignmentBundleLifecycleContext(
            repository=repo,
            get_session=get_session,
            write_validation_log=write_validation_log,
        )

    def apply_transition_plan(session_id: str, plan) -> None:
        fields = dict(plan.update_fields)
        if plan.finish_session:
            fields["finished_at"] = "2026-05-30T00:00:01Z"
        if plan.clear_active_child_pid:
            fields["clear_active_child_pid"] = True
        repo.update_alignment_session(session_id, **fields)
        repo.append_alignment_event(session_id, plan.event_type, plan.event_payload)
        transition_plans.append(
            {"action": plan.action, "fields": fields, "event_type": plan.event_type, "payload": plan.event_payload}
        )

    def fail_session(session_id: str, error: str) -> None:
        repo.update_alignment_session(
            session_id,
            status="failed",
            finished_at="2026-05-30T00:00:02Z",
            clear_active_child_pid=True,
            error_message=error,
        )
        repo.append_alignment_event(session_id, "alignment_failed", {"status": "failed", "error": error})
        failures.append({"session_id": session_id, "error": error})

    context = AlignmentBundleCandidateContext(
        repository=repo,
        get_session=get_session,
        load_validated_bundle_text=load_validated_bundle_text,
        bundle_lifecycle_context=lifecycle_context,
        apply_transition_plan=apply_transition_plan,
        fail_session=fail_session,
        now=lambda: "2026-05-30T00:00:00Z",
    )
    return context, validation_logs, transition_plans, failures


def candidate_session(tmp_path: Path, *, repair_attempts: object = 0) -> dict:
    return {
        "id": "align_candidate",
        "status": "running",
        "bundle_path": str(tmp_path / "align_candidate" / "artifacts" / "bundle.yml"),
        "repair_attempts": repair_attempts,
    }

# Merged from runner_advisory_coverage_results_test_support.py
import json
from collections.abc import Callable
from dataclasses import dataclass

from loopora.executor import CodexExecutor, FakeCodexExecutor

from runner_helpers import _create_loop, _read_jsonl

ADVISORY_TARGET_KINDS = {"success_surface", "fake_done", "evidence_preference"}
ADVISORY_TARGET_IDS = (
    "success_surface.surface_001",
    "success_surface.surface_002",
    "fake_done.risk_001",
    "evidence_preference.pref_001",
)
ADVISORY_VERIFY_REFS = (
    "target:success_surface.surface_001:covered",
    "target:fake_done.risk_001:covered",
    "target:evidence_preference.pref_001:covered",
)


AdvisoryCoverageFixtures = tuple[Any, Path, Path]


@dataclass(frozen=True)
class AdvisoryCoverageRun:
    run: dict[str, Any]
    coverage: dict[str, Any]
    evidence_ledger: list[dict[str, Any]]

def run_advisory_coverage_loop(
    fixtures: AdvisoryCoverageFixtures,
    *,
    name: str,
    executor_factory: Callable[[], CodexExecutor] | type[CodexExecutor],
    workflow: dict[str, Any] | None = None,
) -> AdvisoryCoverageRun:
    service_factory, sample_spec_file, sample_workdir = fixtures
    service = service_factory(scenario="success")
    service.executor_factory = executor_factory
    loop = _create_loop(service, sample_spec_file, sample_workdir, name=name, workflow=workflow)

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    return AdvisoryCoverageRun(
        run=run,
        coverage=json.loads((run_dir / "evidence" / "coverage.json").read_text(encoding="utf-8")),
        evidence_ledger=_read_jsonl(run_dir / "evidence" / "ledger.jsonl"),
    )


def assert_advisory_targets_covered(case: AdvisoryCoverageRun) -> None:
    target_status = {target["id"]: target["status"] for target in case.coverage["targets"]}
    assert case.run["status"] == "succeeded"
    assert case.coverage["status"] == "covered"
    for target_id in ADVISORY_TARGET_IDS:
        assert target_status[target_id] == "covered"


def gatekeeper_entry(case: AdvisoryCoverageRun) -> dict[str, Any]:
    return next(entry for entry in case.evidence_ledger if entry["archetype"] == "gatekeeper")


class InspectorAdvisoryCoverageExecutor(FakeCodexExecutor):
    def _build_payload(self, request: Any) -> dict[str, Any]:
        payload = super()._build_payload(request)
        if request.role_archetype == "inspector":
            payload["coverage_results"] = [
                {
                    "target_id": target["id"],
                    "status": "covered",
                    "evidence_refs": [],
                    "note": "Inspector explicitly verified this advisory target.",
                }
                for target in _compiled_coverage_targets(request)
            ]
        return payload


class GatekeeperAdvisoryCoverageExecutor(CodexExecutor):
    def execute(self, request: Any, _emit_event: Any, _should_stop: Any, set_child_pid: Any) -> dict[str, Any]:
        set_child_pid(None)
        if request.role_archetype == "inspector":
            payload = {
                "execution_summary": {"total_checks": 2, "passed": 2, "failed": 0, "errored": 0, "total_duration_ms": 50},
                "check_results": [
                    {"id": "check_001", "title": "Primary experience", "status": "passed", "notes": "Primary experience is covered."},
                    {"id": "check_002", "title": "Edge path", "status": "passed", "notes": "Edge path is covered."},
                ],
                "dynamic_checks": [],
                "tester_observations": "Required Done When checks are covered.",
                "coverage_results": [],
            }
        else:
            evidence_refs = [item["id"] for item in request.extra_context["step_instruction_context"]["evidence"]["items"]]
            payload = {
                "passed": True,
                "decision_summary": "GateKeeper explicitly covered advisory targets before closing.",
                "feedback_to_builder": "",
                "blocking_issues": [],
                "metrics": [{"name": "quality_score", "value": 1.0, "threshold": 0.9, "passed": True}],
                "failed_check_ids": [],
                "priority_failures": [],
                "composite_score": 1.0,
                "evidence_refs": evidence_refs,
                "evidence_claims": ["Inspector evidence covered the required checks."],
                "residual_risks": [],
                "coverage_results": [
                    {
                        "target_id": target["id"],
                        "status": "covered",
                        "evidence_refs": evidence_refs,
                        "note": "GateKeeper accepted this advisory target from the supporting inspection.",
                    }
                    for target in _compiled_coverage_targets(request)
                ],
            }
        request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return payload


def inspector_gatekeeper_workflow() -> dict[str, Any]:
    return {
        "version": 1,
        "roles": [
            {"id": "inspector", "name": "Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [{"id": "inspector_step", "role_id": "inspector"}, {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"}],
    }


def inspector_advisory_coverage_executor() -> InspectorAdvisoryCoverageExecutor:
    return InspectorAdvisoryCoverageExecutor(scenario="success")


def _compiled_coverage_targets(request: Any) -> list[dict[str, Any]]:
    targets = list((request.extra_context.get("compiled_spec") or {}).get("coverage_targets") or [])
    return [target for target in targets if target.get("kind") in ADVISORY_TARGET_KINDS]

# Merged from runner_no_evidence_progress_control_test_support.py
from pathlib import Path

from loopora.executor import CodexExecutor
from loopora.run_takeaways import build_run_key_takeaways



MISSING_REQUIRED_CHECK_IDS = ["check_001", "check_002"]
MISSING_REQUIRED_CHECK_COUNT = len(MISSING_REQUIRED_CHECK_IDS)


class CoverageStallExecutor(CodexExecutor):
    def execute(self, request, _emit_event, _should_stop, set_child_pid):
        set_child_pid(None)
        iter_id = int(request.extra_context.get("iter_id") or 0)
        if request.role_archetype == "builder":
            payload = {
                "attempted": "Kept changing the story without adding required proof.",
                "abandoned": "",
                "assumption": "",
                "summary": "No required coverage target was verified.",
                "changed_files": [],
            }
        elif request.role_archetype == "inspector":
            payload = {
                "execution_summary": {
                    "total_checks": 0,
                    "passed": 0,
                    "failed": 0,
                    "errored": 0,
                    "total_duration_ms": 1,
                },
                "check_results": [],
                "dynamic_checks": [],
                "tester_observations": "No required Done When target has direct evidence yet.",
                "coverage_results": [],
            }
        elif request.role_archetype == "guide":
            payload = {
                "created_at_iter": iter_id,
                "mode": "coverage_stalled",
                "consumed": False,
                "analysis": {
                    "recommended_shift": "Stop changing the narrative and produce one required proof target.",
                    "risk_note": "Coverage stalled while required checks remain missing.",
                },
                "seed_question": "Which missing Done When target can be proved next?",
                "meta_note": "Coverage control fired.",
            }
        else:
            payload = {
                "passed": False,
                "decision_summary": "Composite improved, but required evidence coverage did not.",
                "feedback_to_builder": "Produce direct proof for a required Done When target.",
                "blocking_issues": [],
                "metrics": [
                    {
                        "name": "quality_score",
                        "value": 0.5 + iter_id * 0.1,
                        "threshold": 0.9,
                        "passed": False,
                    }
                ],
                "failed_check_ids": [],
                "priority_failures": [],
                "composite_score": 0.5 + iter_id * 0.1,
                "evidence_refs": [],
                "evidence_claims": [],
            }
        request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return payload


def coverage_stall_workflow() -> dict:
    return {
        "version": 1,
        "roles": [
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
            {"id": "inspector", "name": "Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
            {"id": "guide", "name": "Guide", "archetype": "guide", "prompt_ref": "guide.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
            {"id": "inspector_step", "role_id": "inspector"},
            {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
        ],
        "controls": [
            {
                "id": "coverage_stall_guidance",
                "when": {"signal": "no_evidence_progress", "after": "0s"},
                "call": {"role_id": "guide"},
                "mode": "repair_guidance",
                "max_fires_per_run": 1,
            }
        ],
    }


def coverage_stall_artifacts(service, run: dict) -> dict:
    run_dir = Path(run["runs_dir"])
    role_requests = _read_jsonl(run_dir / "context" / "role_requests.jsonl")
    guide_request = next(item for item in role_requests if item["role_archetype"] == "guide")
    takeaways = build_run_key_takeaways(service.get_run(run["id"]))
    return {
        "stagnation": json.loads((run_dir / "timeline" / "stagnation.json").read_text(encoding="utf-8")),
        "latest_iteration_summary": json.loads(
            (run_dir / "context" / "latest_iteration_summary.json").read_text(encoding="utf-8")
        ),
        "events": service.stream_events(run["id"], limit=500),
        "evidence_ledger": _read_jsonl(run_dir / "evidence" / "ledger.jsonl"),
        "guide_request": guide_request,
        "guide_prompt": (run_dir / guide_request["prompt_path"]).read_text(encoding="utf-8"),
        "latest_takeaway": takeaways["iterations"][0],
    }


def assert_required_coverage_stalled(snapshot: dict) -> None:
    assert snapshot["evidence_progress_mode"] == "stalled"
    assert snapshot["coverage_status"] == "blocked"
    assert snapshot["covered_check_count"] == 0
    assert snapshot["missing_check_count"] == MISSING_REQUIRED_CHECK_COUNT
    assert snapshot["missing_check_ids"] == MISSING_REQUIRED_CHECK_IDS
    assert any(item["target_id"] == "done_when.check_001" for item in snapshot["coverage_top_gaps"])


def assert_guide_prompt_mentions_stalled_coverage(guide_prompt: str) -> None:
    assert "Evidence progress mode: stalled" in guide_prompt
    assert 'Missing required check ids: ["check_001", "check_002"]' in guide_prompt
    assert '"target_id": "done_when.check_001"' in guide_prompt
    assert "Required coverage: 0 covered, 2 missing" in guide_prompt


def assert_no_evidence_progress_control_recorded(events: list[dict], evidence_ledger: list[dict]) -> None:
    assert any(
        event["event_type"] == "control_triggered"
        and event["payload"]["signal"] == "no_evidence_progress"
        and "Required coverage did not improve" in event["payload"]["reason"]
        for event in events
    )
    assert any(entry["evidence_kind"] == "control" and "control:no_evidence_progress" in entry["verifies"] for entry in evidence_ledger)

# Merged from runner_gatekeeper_builder_handoff_gate_test_support.py
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loopora.executor import CodexExecutor

from runner_helpers import (
    _step_outputs_by_archetype,
)

BUILDER_EVIDENCE_REF = "ev_000_00_builder_step"
NON_SUPPORTING_GATE_ISSUE = "gatekeeper_pass_refs_not_supporting_evidence"
BUILDER_ROLE_ID = "builder"
GATEKEEPER_ROLE_ID = "gatekeeper"
BUILDER_STEP_ID = "builder_step"
GATEKEEPER_STEP_ID = "gatekeeper_step"


@dataclass(frozen=True)
class GatekeeperBuilderHandoffCase:
    run: dict[str, Any]
    coverage: dict[str, Any]
    manifest: dict[str, Any]
    gatekeeper_output: dict[str, Any]


def run_builder_gatekeeper_handoff_case(
    service_factory: Any,
    sample_spec_file: Path,
    sample_workdir: Path,
    *,
    executor_factory: type[CodexExecutor],
    name: str,
) -> GatekeeperBuilderHandoffCase:
    service = service_factory(scenario="success")
    service.executor_factory = executor_factory
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name=name,
        max_iters=1,
        workflow=_builder_gatekeeper_workflow(),
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    return GatekeeperBuilderHandoffCase(
        run=run,
        coverage=json.loads((run_dir / "evidence" / "coverage.json").read_text(encoding="utf-8")),
        manifest=json.loads((run_dir / "evidence" / "manifest.json").read_text(encoding="utf-8")),
        gatekeeper_output=_step_outputs_by_archetype(run_dir)["gatekeeper"][-1]["output"],
    )


def assert_gatekeeper_builder_ref_blocked(case: GatekeeperBuilderHandoffCase) -> None:
    assert case.run["status"] == "failed"
    assert case.gatekeeper_output["passed"] is False
    assert case.gatekeeper_output["evidence_gate_status"] == "blocked"
    assert case.gatekeeper_output["blocking_issues"] == [NON_SUPPORTING_GATE_ISSUE]
    assert case.coverage["latest_gatekeeper"]["supporting_evidence_refs"] == []
    assert case.coverage["latest_gatekeeper"]["non_supporting_evidence_refs"] == [BUILDER_EVIDENCE_REF]


def builder_claim(case: GatekeeperBuilderHandoffCase) -> dict[str, Any]:
    return next(item for item in case.manifest["claims"] if item["id"] == BUILDER_EVIDENCE_REF)


class BuilderHandoffOnlyExecutor(CodexExecutor):
    def execute(self, request: Any, _emit_event: Any, _should_stop: Any, set_child_pid: Any) -> dict[str, Any]:
        set_child_pid(None)
        if request.role_archetype == BUILDER_ROLE_ID:
            payload = {
                "attempted": "Produced a candidate without proof artifacts.",
                "abandoned": "",
                "assumption": "",
                "summary": "Builder says the task is done.",
                "changed_files": [],
                "proof_files": [],
                "proof_artifacts": [],
                "artifact_paths": [],
            }
        else:
            payload = _gatekeeper_pass_payload(
                decision_summary="GateKeeper accepted the Builder handoff as proof.",
                evidence_claim="The Builder handoff says the task is complete.",
            )
        return _write_payload(request, payload)


def missing_proof_artifact_executor(proof_path: Path) -> type[CodexExecutor]:
    class MissingProofArtifactExecutor(CodexExecutor):
        def execute(self, request: Any, _emit_event: Any, _should_stop: Any, set_child_pid: Any) -> dict[str, Any]:
            set_child_pid(None)
            if request.role_archetype == BUILDER_ROLE_ID:
                proof_path.parent.mkdir(parents=True, exist_ok=True)
                proof_path.write_text('{"ok": true}\n', encoding="utf-8")
                payload = {
                    "attempted": "Produced a candidate with a proof artifact.",
                    "abandoned": "",
                    "assumption": "",
                    "summary": "Builder left proof for the task.",
                    "changed_files": [],
                    "proof_files": ["tests/evidence/proof.json"],
                    "proof_artifacts": [],
                    "artifact_paths": [],
                }
            else:
                proof_path.unlink()
                payload = _gatekeeper_pass_payload(
                    decision_summary="GateKeeper accepted a proof artifact that is no longer available.",
                    evidence_claim="The proof artifact path should remain readable at close time.",
                )
            return _write_payload(request, payload)

    return MissingProofArtifactExecutor


def _builder_gatekeeper_workflow() -> dict[str, Any]:
    return {
        "version": 1,
        "roles": [
            {"id": BUILDER_ROLE_ID, "name": "Builder", "archetype": BUILDER_ROLE_ID, "prompt_ref": "builder.md"},
            {
                "id": GATEKEEPER_ROLE_ID,
                "name": "GateKeeper",
                "archetype": GATEKEEPER_ROLE_ID,
                "prompt_ref": "gatekeeper.md",
            },
        ],
        "steps": [
            {"id": BUILDER_STEP_ID, "role_id": BUILDER_ROLE_ID},
            {"id": GATEKEEPER_STEP_ID, "role_id": GATEKEEPER_ROLE_ID, "on_pass": "finish_run"},
        ],
    }


def _gatekeeper_pass_payload(*, decision_summary: str, evidence_claim: str) -> dict[str, Any]:
    return {
        "passed": True,
        "decision_summary": decision_summary,
        "feedback_to_builder": "",
        "blocking_issues": [],
        "metrics": [],
        "failed_check_ids": [],
        "priority_failures": [],
        "composite_score": 1.0,
        "evidence_refs": [BUILDER_EVIDENCE_REF],
        "evidence_claims": [evidence_claim],
    }


def _write_payload(request: Any, payload: dict[str, Any]) -> dict[str, Any]:
    request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload

# Merged from web_run_stream_test_support.py
def stream_response_text(response) -> str:
    return "".join(chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in response.iter_text())

# Merged from alignment_guidance_test_support.py
def assert_contains_all(text: str, snippets: tuple[str, ...]) -> None:
    missing = [snippet for snippet in snippets if snippet not in text]
    assert missing == []

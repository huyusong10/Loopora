from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from loopora.bundles import bundle_to_yaml, load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_context import alignment_source_option_id
from loopora.service_alignment_prompting import (
    AlignmentPromptBuildContext,
    alignment_improvement_context_text,
    build_alignment_prompt,
)
from loopora.service_alignment_requests import RevisionAlignmentSessionRequest, default_alignment_executor_settings
from loopora.service_alignment_revision import create_revision_alignment_session
from loopora.service_types import LooporaConflictError
from loopora.web import build_app

from alignment_test_support import (
    _wait_for_status,
    _confirm_alignment_agreement,
    _create_alignment_improvement_source_bundle,
    _write_run_revision_coverage,
    _assert_run_revision_coverage_agreement,
    _assert_run_revision_context_text,
)


def alignment_prompt(session: dict, *, mode: str = "normal") -> str:
    return build_alignment_prompt(AlignmentPromptBuildContext(), session, mode=mode)


def test_alignment_improvement_session_validates_feedback_driven_bundle_delta(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    source = _create_alignment_improvement_source_bundle(service, sample_spec_file, sample_workdir)

    created = service.create_bundle_revision_session(
        source["id"],
        message="Please improve this Loop while preserving its stable intent.",
        start_immediately=True,
    )
    session = _confirm_alignment_agreement(service, created["id"])

    assert session["validation"]["ok"] is True
    bundle_text = Path(session["bundle_path"]).read_text(encoding="utf-8")
    assert "Preserve the source Loop" in bundle_text
    assert "feedback-driven governance delta" in bundle_text
    assert "spec" in bundle_text
    assert "roles" in bundle_text
    assert "workflow" in bundle_text

def test_alignment_improvement_session_blocks_generic_final_bundle(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_improvement_generic_bundle")
    source = _create_alignment_improvement_source_bundle(service, sample_spec_file, sample_workdir)

    created = service.create_bundle_revision_session(
        source["id"],
        message="Please improve this Loop while preserving its stable intent.",
        start_immediately=True,
    )
    session = _confirm_alignment_agreement(service, created["id"], "failed")

    assert session["validation"]["ok"] is False
    assert "feedback-driven governance delta" in session["error_message"]
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_validation_failed"
        and "improvement bundle must state the feedback-driven governance delta" in event["payload"].get("error", "")
        for event in events
    )

def test_alignment_improvement_session_blocks_vague_improvement_agreement(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_improvement_missing_delta")
    source = _create_alignment_improvement_source_bundle(service, sample_spec_file, sample_workdir)

    created = service.create_bundle_revision_session(
        source["id"],
        message="Please improve this Loop.",
        start_immediately=True,
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert session["alignment_stage"] == "clarifying"
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_improvement_incomplete" and "improvement_delta" in event["payload"].get("missing", []) for event in events)

def test_alignment_improvement_session_can_start_from_run_evidence(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Run Evidence Source Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    source = service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="Run Evidence Source Bundle",
                description="Start from run evidence.",
                collaboration_summary="Use GateKeeper evidence to improve the plan.",
            )
        )
    )
    run = service.rerun(source["loop_id"])
    run_contract_path = Path(run["runs_dir"]) / "contract" / "run_contract.json"
    run_contract_payload = json.loads(run_contract_path.read_text(encoding="utf-8"))
    run_contract_payload["execution_strategy"] = ["Repair evidence gaps before broad polishing."]
    run_contract_payload["local_governance"] = ["GateKeeper treats skipped AGENTS.md evidence as Blocking."]
    run_contract_path.write_text(json.dumps(run_contract_payload, ensure_ascii=False), encoding="utf-8")
    _write_run_revision_coverage(Path(run["runs_dir"]) / "evidence" / "coverage.json")

    session = service.create_run_revision_session(run["id"], start_immediately=False)

    agreement = session["working_agreement"]
    assert agreement["mode"] == "improvement"
    assert agreement["source"]["source_type"] == "run"
    assert agreement["source"]["source_bundle_id"] == source["id"]
    assert agreement["source"]["source_run_id"] == run["id"]
    assert agreement["source"]["run_status"] == run["status"]
    assert agreement["source"]["artifact_paths"] == {
        "run_contract": "contract/run_contract.json",
        "task_verdict": "evidence/task_verdict.json",
        "evidence_ledger": "evidence/ledger.jsonl",
        "evidence_coverage": "evidence/coverage.json",
        "evidence_manifest": "evidence/manifest.json",
    }
    assert agreement["source"]["judgment_contract"]["contract_path"] == "contract/run_contract.json"
    assert agreement["source"]["judgment_contract"]["collaboration_summary"] == "Use GateKeeper evidence to improve the plan."
    assert agreement["source"]["judgment_contract"]["execution_strategy"] == ["Repair evidence gaps before broad polishing."]
    assert agreement["source"]["judgment_contract"]["local_governance"] == ["GateKeeper treats skipped AGENTS.md evidence as Blocking."]
    _assert_run_revision_coverage_agreement(agreement)
    context_text = alignment_improvement_context_text(session)
    _assert_run_revision_context_text(context_text, run, agreement)
    preview = service.get_alignment_bundle(session["id"])
    assert preview["ok"] is True
    assert preview["bundle"]["metadata"]["source_bundle_id"] == ""
    assert "source_bundle_id" not in preview["yaml"]

def test_alignment_run_revision_tolerates_corrupt_evidence_ledger(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Corrupt Evidence Revision Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.rerun(loop["id"])
    (Path(run["runs_dir"]) / "evidence" / "ledger.jsonl").write_bytes(b"\xff")
    (Path(run["runs_dir"]) / "evidence" / "task_verdict.json").unlink()

    session = service.create_run_revision_session(run["id"], start_immediately=False)

    agreement = session["working_agreement"]
    assert agreement["mode"] == "improvement"
    assert agreement["source"]["source_type"] == "run"
    assert agreement["source"]["source_run_id"] == run["id"]
    assert agreement["source"]["artifact_paths"] == {
        "run_contract": "contract/run_contract.json",
        "task_verdict": "evidence/task_verdict.json",
        "evidence_ledger": "evidence/ledger.jsonl",
        "evidence_coverage": "evidence/coverage.json",
        "evidence_manifest": "evidence/manifest.json",
    }
    assert agreement["source"]["judgment_contract"]["contract_path"] == "contract/run_contract.json"
    assert agreement["source"]["evidence_summary"] == []
    preview = service.get_alignment_bundle(session["id"])
    assert preview["ok"] is True

def test_alignment_run_evidence_summary_drops_malformed_trace_shapes(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="Malformed Evidence Summary Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.rerun(loop["id"])
    proof_path = sample_workdir / "proof.md"
    ledger_path = Path(run["runs_dir"]) / "evidence" / "ledger.jsonl"
    ledger_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "ev_bad_shape",
                        "claim": "Bad trace shapes should not become prompt structure.",
                        "verifies": "target:done_when.check_001:covered",
                        "artifact_refs": {"kind": "workspace", "relative_path": "proof.md"},
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "id": "ev_good_shape",
                        "claim": "Good trace shapes should keep only stable fields.",
                        "verifies": ["target:done_when.check_001:covered", 7, True],
                        "artifact_refs": [
                            {
                                "kind": "workspace",
                                "label": "proof",
                                "relative_path": "proof.md",
                                "workspace_path": "proof.md",
                                "absolute_path": str(proof_path),
                                "raw_payload": "uncommitted payload",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    session = service.create_run_revision_session(run["id"], start_immediately=False)

    summary = session["working_agreement"]["source"]["evidence_summary"]
    assert summary[0]["id"] == "ev_bad_shape"
    assert summary[0]["verifies"] == []
    assert summary[0]["artifact_refs"] == []
    assert summary[1]["id"] == "ev_good_shape"
    assert summary[1]["verifies"] == ["target:done_when.check_001:covered"]
    assert summary[1]["artifact_refs"] == [
        {
            "kind": "workspace",
            "label": "proof",
            "relative_path": "proof.md",
            "workspace_path": "proof.md",
            "absolute_path": str(proof_path),
        }
    ]
    assert "raw_payload" not in json.dumps(summary, ensure_ascii=False)

def test_alignment_api_creates_improvement_sessions_from_bundle_and_run(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = service.create_loop(
        name="API Improvement Source Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    source = service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="API Improvement Source Bundle",
                description="API improvement source.",
                collaboration_summary="Keep the source posture visible.",
            )
        )
    )
    run = service.rerun(source["loop_id"])
    client = TestClient(build_app(service=service))

    bundle_response = client.post(f"/api/bundles/{source['id']}/revise", json={"start_immediately": False})
    assert bundle_response.status_code == 201
    bundle_payload = bundle_response.json()
    assert bundle_payload["redirect_url"] == (f"/loops/new/bundle?alignment_session_id={bundle_payload['session']['id']}")
    assert bundle_payload["session"]["working_agreement"]["mode"] == "improvement"
    assert bundle_payload["session"]["working_agreement"]["source"]["source_type"] == "bundle"
    assert bundle_payload["session"]["working_agreement"]["source"]["source_bundle_id"] == source["id"]

    run_response = client.post(f"/api/runs/{run['id']}/revise", json={"start_immediately": False})
    assert run_response.status_code == 201
    run_payload = run_response.json()
    assert run_payload["redirect_url"] == f"/loops/new/bundle?alignment_session_id={run_payload['session']['id']}"
    assert run_payload["session"]["working_agreement"]["mode"] == "improvement"
    assert run_payload["session"]["working_agreement"]["source"]["source_type"] == "run"
    assert run_payload["session"]["working_agreement"]["source"]["source_run_id"] == run["id"]

def test_alignment_workdir_context_discovers_spec_and_requires_explicit_selection(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    empty_context = service.get_alignment_workdir_context(sample_workdir)
    assert empty_context["requires_choice"] is False
    assert empty_context["recommended_option_id"] == "regenerate"
    assert empty_context["resolution"]["action"] == "create_new"
    assert empty_context["resolution"]["confidence"] == "no_existing_context"
    assert empty_context["resolution"]["fresh"] is True

    state_dir = sample_workdir / ".loopora"
    state_dir.mkdir()
    spec_path = state_dir / "spec.md"
    spec_path.write_text("# Task\n\n编排一个英语学习网站。\n", encoding="utf-8")
    invocation_dir = state_dir / "alignment_sessions" / "align_old" / "invocations" / "0001"
    invocation_dir.mkdir(parents=True)
    (invocation_dir / "stdout.log").write_text("secret execution log\n", encoding="utf-8")

    context = service.get_alignment_workdir_context(sample_workdir)

    assert context["requires_choice"] is True
    assert context["resolution"]["action"] == "choose_source"
    assert context["resolution"]["requires_user_choice"] is True
    spec_option = next(option for option in context["options"] if option["source_type"] == "spec_file")
    assert spec_option["spec_path"] == str(spec_path)
    assert spec_option["label_zh"].startswith("从已有任务契约开始")
    assert "角色责任" in spec_option["description_zh"]
    assert "roles" not in spec_option["description_zh"]
    assert "workflow" not in spec_option["description_zh"]
    assert any(option["action"] == "regenerate" for option in context["options"])
    fresh_resolution = service.resolve_loopora_context(
        sample_workdir,
        intent="plan",
        source_option_id="regenerate",
    )
    assert fresh_resolution["action"] == "create_new"
    assert fresh_resolution["fresh"] is True
    assert fresh_resolution["confidence"] == "explicit_fresh"
    fresh_session = service.create_alignment_session(
        workdir=sample_workdir,
        message="重新创建一份 Loop，不复用旧 spec。",
        source_option_id="regenerate",
        start_immediately=False,
    )
    assert fresh_session["working_agreement"] == {}
    assert not fresh_session.get("linked_bundle_id")
    assert not fresh_session.get("linked_run_id")
    fresh_prompt = alignment_prompt(fresh_session)
    assert "Selected Loopora Source Context" not in fresh_prompt
    assert "secret execution log" not in fresh_prompt

    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="继续把这个目录编排成 Loop。",
        source_option_id=spec_option["option_id"],
        start_immediately=False,
    )

    agreement = session["working_agreement"]
    assert agreement["mode"] == "selected_source"
    assert agreement["source"]["source_type"] == "spec_file"
    assert "英语学习网站" in agreement["source"]["spec_markdown"]
    prompt = alignment_prompt(session)
    assert "Selected Loopora Source Context" in prompt
    assert "英语学习网站" in prompt
    assert "secret execution log" not in prompt

    continue_option = {"option_id": alignment_source_option_id("continue_session", session["id"])}
    with pytest.raises(LooporaConflictError):
        service.create_alignment_session(
            workdir=sample_workdir,
            message="不要新建，继续旧对话。",
            source_option_id=continue_option["option_id"],
            start_immediately=False,
        )

def test_alignment_workdir_context_only_lists_validated_local_ready_bundles(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    state_dir = sample_workdir / ".loopora"
    valid_bundle = state_dir / "alignment_sessions" / "align_valid" / "artifacts" / "bundle.yml"
    stale_ready_bundle = state_dir / "alignment_sessions" / "align_stale_ready" / "artifacts" / "bundle.yml"
    wrong_workdir_bundle = state_dir / "alignment_sessions" / "align_wrong_workdir" / "artifacts" / "bundle.yml"
    failed_bundle = state_dir / "alignment_sessions" / "align_failed" / "artifacts" / "bundle.yml"
    unknown_bundle = state_dir / "alignment_sessions" / "align_unknown" / "artifacts" / "bundle.yml"
    for bundle_path in (valid_bundle, stale_ready_bundle, wrong_workdir_bundle, failed_bundle, unknown_bundle):
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_path.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    (valid_bundle.parent / "validation.json").write_text('{"ok": true}\n', encoding="utf-8")
    stale_ready_bundle.write_text(
        stale_ready_bundle.read_text(encoding="utf-8").replace(
            "Accept minor polish gaps only when they are explicitly named and tracked as an owned follow-up; fail closed on unproven primary-flow behavior or weak verification evidence.",
            "Some risk is fine.",
        ),
        encoding="utf-8",
    )
    (stale_ready_bundle.parent / "validation.json").write_text('{"ok": true}\n', encoding="utf-8")
    wrong_workdir = sample_workdir.parent / "other-workdir"
    wrong_workdir_bundle.write_text(alignment_bundle_yaml(str(wrong_workdir.resolve())), encoding="utf-8")
    (wrong_workdir_bundle.parent / "validation.json").write_text('{"ok": true}\n', encoding="utf-8")
    (failed_bundle.parent / "validation.json").write_text('{"ok": false, "error": "semantic lint failed"}\n', encoding="utf-8")

    context = service.get_alignment_workdir_context(sample_workdir)
    local_options = [
        option
        for option in context["options"]
        if option.get("source_type") == "alignment_session_file"
    ]

    assert [option["source_alignment_session_id"] for option in local_options] == ["align_valid"]
    assert local_options[0]["bundle_path"] == str(valid_bundle)
    assert "方案文件" in local_options[0]["description_zh"]
    assert "bundle" not in local_options[0]["description_zh"]

def test_alignment_workdir_context_does_not_seed_from_stale_ready_session_bundle(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create a reusable READY Loop.")["id"],
    )
    bundle_path = Path(session["bundle_path"])
    stale_bundle = load_bundle_text(bundle_path.read_text(encoding="utf-8"))
    stale_bundle["spec"]["markdown"] = stale_bundle["spec"]["markdown"].replace(
        "Accept minor polish gaps only when they are explicitly named and tracked as an owned follow-up; fail closed on unproven primary-flow behavior or weak verification evidence.",
        "Some risk is fine.",
    )
    bundle_path.write_text(bundle_to_yaml(stale_bundle), encoding="utf-8")
    wrong_workdir_session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create another reusable READY Loop.")["id"],
    )
    wrong_workdir_bundle_path = Path(wrong_workdir_session["bundle_path"])
    wrong_workdir_bundle = load_bundle_text(wrong_workdir_bundle_path.read_text(encoding="utf-8"))
    wrong_workdir_bundle["loop"]["workdir"] = str((sample_workdir.parent / "other-workdir").resolve())
    wrong_workdir_bundle_path.write_text(bundle_to_yaml(wrong_workdir_bundle), encoding="utf-8")

    context = service.get_alignment_workdir_context(sample_workdir)

    assert any(
        option.get("action") == "continue_session" and option.get("session_id") == session["id"]
        for option in context["options"]
    )
    assert not any(
        option.get("action") == "improve"
        and option.get("source_type") == "alignment_session"
        and option.get("source_alignment_session_id") == session["id"]
        for option in context["options"]
    )
    assert not any(
        option.get("action") == "improve"
        and option.get("source_type") == "alignment_session"
        and option.get("source_alignment_session_id") == wrong_workdir_session["id"]
        for option in context["options"]
    )

def test_alignment_workdir_context_preserves_regenerate_option_when_source_list_is_bounded(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    for index in range(25):
        service.create_alignment_session(
            workdir=sample_workdir,
            message=f"Existing alignment source {index}",
            start_immediately=False,
        )

    context = service.get_alignment_workdir_context(sample_workdir)
    option_ids = [option["option_id"] for option in context["options"]]

    assert len(context["options"]) == 20
    assert context["requires_choice"] is True
    assert context["recommended_option_id"] == ""
    assert option_ids[-1] == "regenerate"
    assert sum(option_id == "regenerate" for option_id in option_ids) == 1

def test_alignment_source_context_redacts_sensitive_transcript_and_spec_material(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    state_dir = sample_workdir / ".loopora"
    state_dir.mkdir()
    spec_path = state_dir / "spec.md"
    spec_path.write_text("# Task\n\nCall the API with Authorization: Bearer SPEC_SECRET_MARKER.\n", encoding="utf-8")
    source_session_id = "align_secret_source"
    bundle_path = state_dir / "alignment_sessions" / source_session_id / "artifacts" / "bundle.yml"
    bundle_path.parent.mkdir(parents=True)
    bundle_path.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    service.repository.create_alignment_session(
        {
            "id": source_session_id,
            "status": "ready",
            "workdir": str(sample_workdir),
            "bundle_path": str(bundle_path),
            "transcript": [
                {
                    "role": "user",
                    "content": "Improve this Loop with --token TRANSCRIPT_TOKEN_SECRET_MARKER and Cookie: sid=TRANSCRIPT_COOKIE_SECRET_MARKER",
                    "created_at": "now",
                }
            ],
            "validation": {"ok": True},
            "alignment_stage": "ready",
            "working_agreement": {},
            "executor_session_ref": {},
        }
    )

    context = service.get_alignment_workdir_context(sample_workdir)
    context_text = json.dumps(context, ensure_ascii=False)

    assert "TRANSCRIPT_TOKEN_SECRET_MARKER" not in context_text
    assert "TRANSCRIPT_COOKIE_SECRET_MARKER" not in context_text

    session_option = next(option for option in context["options"] if option.get("source_alignment_session_id") == source_session_id)
    assert "方案文件" in session_option["description_zh"]
    assert "bundle" not in session_option["description_zh"]
    assert "session" not in session_option["description_zh"]
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Use the old alignment as source context.",
        source_option_id=session_option["option_id"],
        start_immediately=False,
    )
    prompt = alignment_prompt(session)
    source_text = json.dumps(session["working_agreement"], ensure_ascii=False)

    assert "TRANSCRIPT_TOKEN_SECRET_MARKER" not in source_text
    assert "TRANSCRIPT_COOKIE_SECRET_MARKER" not in source_text
    assert "TRANSCRIPT_TOKEN_SECRET_MARKER" not in prompt
    assert "TRANSCRIPT_COOKIE_SECRET_MARKER" not in prompt
    assert "<secret omitted>" in prompt

    spec_option = next(option for option in context["options"] if option["source_type"] == "spec_file")
    spec_session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Use the spec as source context.",
        source_option_id=spec_option["option_id"],
        start_immediately=False,
    )

    assert "SPEC_SECRET_MARKER" not in spec_session["working_agreement"]["source"]["spec_markdown"]
    assert "<secret omitted>" in alignment_prompt(spec_session)

def test_alignment_improvement_context_redacts_sensitive_run_source_values() -> None:
    session = {
        "working_agreement": {
            "mode": "improvement",
            "source": {
                "source_type": "run",
                "source_run_id": "run_secret",
                "evidence_summary": [{"claim": "Observed Authorization: Bearer RUN_EVIDENCE_SECRET_MARKER"}],
                "coverage_summary": {"reason": "Header x-api-key: RUN_API_KEY_SECRET_MARKER"},
                "task_verdict": {"summary": "Cookie: sid=RUN_COOKIE_SECRET_MARKER"},
                "gatekeeper_verdict": {"decision_summary": "tool --token RUN_TOKEN_SECRET_MARKER"},
            },
        }
    }

    context = alignment_improvement_context_text(session)

    assert "RUN_EVIDENCE_SECRET_MARKER" not in context
    assert "RUN_API_KEY_SECRET_MARKER" not in context
    assert "RUN_COOKIE_SECRET_MARKER" not in context
    assert "RUN_TOKEN_SECRET_MARKER" not in context
    assert "<secret omitted>" in context

def test_alignment_improvement_session_redacts_persisted_source_context(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    seed_bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))

    session = create_revision_alignment_session(
        service._alignment_revision_context(),
        RevisionAlignmentSessionRequest(
            seed_bundle=seed_bundle,
            message="Use sensitive source context.",
            start_immediately=False,
            source_context={
                "mode": "improvement",
                "source_type": "run",
                "source_run_id": "run_secret",
                "evidence_summary": [{"claim": "Authorization: Bearer PERSISTED_EVIDENCE_SECRET"}],
                "coverage_summary": {"reason": "x-api-key: PERSISTED_API_KEY_SECRET"},
                "task_verdict": {"summary": "Cookie: sid=PERSISTED_COOKIE_SECRET"},
                "gatekeeper_verdict": {"decision_summary": "tool --token PERSISTED_TOKEN_SECRET"},
            },
            linked_bundle_id="",
            linked_run_id="run_secret",
            executor_settings=default_alignment_executor_settings(),
        )
    )

    source_text = json.dumps(session["working_agreement"], ensure_ascii=False)

    assert "PERSISTED_EVIDENCE_SECRET" not in source_text
    assert "PERSISTED_API_KEY_SECRET" not in source_text
    assert "PERSISTED_COOKIE_SECRET" not in source_text
    assert "PERSISTED_TOKEN_SECRET" not in source_text
    assert "<secret omitted>" in source_text

def test_alignment_workdir_context_seeds_selected_existing_bundle(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    source = _create_alignment_improvement_source_bundle(service, sample_spec_file, sample_workdir)
    context = service.get_alignment_workdir_context(sample_workdir)
    bundle_option = next(option for option in context["options"] if option.get("source_bundle_id") == source["id"])

    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="在这个已有方案上继续改进证据路径。",
        source_option_id=bundle_option["option_id"],
        start_immediately=False,
    )

    agreement = session["working_agreement"]
    assert agreement["mode"] == "improvement"
    assert agreement["source"]["source_type"] == "bundle"
    assert agreement["source"]["source_bundle_id"] == source["id"]
    assert session["linked_bundle_id"] == source["id"]
    assert Path(session["bundle_path"]).exists()
    preview = service.get_alignment_bundle(session["id"])
    assert preview["ok"] is True
    assert preview["bundle"]["metadata"]["source_bundle_id"] == ""
    prompt = alignment_prompt(session)
    assert "Selected Loopora Source Context" in prompt
    assert "Current Bundle" in prompt

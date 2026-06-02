from __future__ import annotations

# Merged from test_alignment_run_context_exact_binding.py
from pathlib import Path

from loopora.service_alignment_run_context import resolve_alignment_run_context

from alignment_run_context_test_support import FakeAlignmentRunContextRepository, resolver_context


def test_alignment_run_context_resolver_uses_exact_binding_without_user_choice(tmp_path: Path) -> None:
    repo = FakeAlignmentRunContextRepository(
        [{"id": "align_1", "status": "ready", "workdir": str(tmp_path), "transcript": [{"role": "user", "content": "Ship it."}]}],
    )

    result = resolve_alignment_run_context(
        resolver_context(
            repo,
            read_binding=lambda _adapter, _root, *, context_id="": {
                "alignment_session_id": "align_1",
                "workdir": str(tmp_path),
                "host_context_id": context_id,
                "access_token": "SECRET",
            },
        ),
        tmp_path,
        adapter="codex",
        context_id="thread-a",
    )

    assert result["action"] == "start_ready_preview"
    assert result["confidence"] == "exact_context_card"
    assert result["requires_user_choice"] is False
    assert result["alignment_session_id"] == "align_1"
    assert result["binding"]["host_context_id"] == "thread-a"
    assert "access_token" not in result["binding"]
    assert result["choice"]["alignment_session_id"] == "align_1"
    assert result["choice"]["action"] == "start_ready_preview"

# Merged from test_alignment_run_context_missing_binding.py

from loopora.service_types import LooporaError

from alignment_run_context_test_support import (
    empty_binding,
)


def test_alignment_run_context_resolver_reports_plan_first_when_no_binding_or_recovery(tmp_path: Path) -> None:
    repo = FakeAlignmentRunContextRepository([])

    result = resolve_alignment_run_context(
        resolver_context(repo, read_binding=empty_binding),
        tmp_path,
        adapter="codex",
        context_id="thread-empty",
    )

    assert result["action"] == "plan_first"
    assert result["confidence"] == "no_context_card"
    assert result["requires_user_choice"] is False
    assert result["choices"] == []
    assert result["context_id"] == "thread-empty"


def test_alignment_run_context_resolver_reports_damaged_binding_before_recovery(tmp_path: Path) -> None:
    repo = FakeAlignmentRunContextRepository(
        [{"id": "align_1", "status": "ready", "workdir": str(tmp_path)}],
        events_by_session={
            "align_1": [
                {
                    "event_type": "agent_candidate_received",
                    "payload": {
                        "candidate_origin": "agent_entry",
                        "adapter": "codex",
                        "has_candidate_yaml": True,
                    },
                }
            ]
        },
    )

    def damaged_binding(_adapter: str, _root: Path, *, context_id: str = "") -> dict:
        assert context_id == "thread-broken"
        raise LooporaError("context card json is unreadable")

    result = resolve_alignment_run_context(
        resolver_context(repo, read_binding=damaged_binding),
        tmp_path,
        adapter="codex",
        context_id="thread-broken",
    )

    assert result["action"] == "repair_context_card"
    assert result["confidence"] == "damaged_context_card"
    assert "context card json is unreadable" in result["binding_error"]
    assert result["choices"] == []

# Merged from test_alignment_run_context_recoverable_choices.py




def test_alignment_run_context_resolver_lists_recoverable_choices_when_binding_is_absent(tmp_path: Path) -> None:
    repo = FakeAlignmentRunContextRepository(
        [{"id": "align_1", "status": "ready", "workdir": str(tmp_path), "transcript": [{"role": "user", "content": "Resume me."}]}],
        events_by_session={
            "align_1": [
                {
                    "event_type": "agent_candidate_received",
                    "payload": {
                        "candidate_origin": "agent_entry",
                        "adapter": "codex",
                        "entry_source": "codex_project_skill",
                        "host_context_id": "thread-a",
                        "has_candidate_yaml": True,
                    },
                }
            ]
        },
    )

    result = resolve_alignment_run_context(
        resolver_context(repo, read_binding=empty_binding),
        tmp_path,
        adapter="codex",
        context_id="thread-new",
    )

    assert result["action"] == "choose_recoverable_context"
    assert result["confidence"] == "single_recoverable"
    assert result["requires_user_choice"] is True
    assert result["choice_count"] == 1
    assert result["runnable_choice_count"] == 1
    assert result["choices"][0]["alignment_session_id"] == "align_1"
    assert result["choices"][0]["host_context_id"] == "thread-a"

# Merged from test_alignment_run_revision_corrupt_evidence.py

from alignment_run_revision_source_context_test_support import create_revision_source_loop


def test_alignment_run_revision_tolerates_corrupt_evidence_ledger(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_revision_source_loop(service, sample_spec_file, sample_workdir, name="Corrupt Evidence Revision Loop")
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

# Merged from test_alignment_run_revision_from_evidence.py
import json

from loopora.bundles import bundle_to_yaml
from loopora.service_alignment_prompting import alignment_improvement_context_text

from alignment_test_support import (
    _assert_run_revision_context_text,
    _assert_run_revision_coverage_agreement,
    _write_run_revision_coverage,
)


def test_alignment_improvement_session_can_start_from_run_evidence(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_revision_source_loop(service, sample_spec_file, sample_workdir, name="Run Evidence Source Loop")
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
    assert agreement["source"]["judgment_contract"]["local_governance"] == [
        "GateKeeper treats skipped AGENTS.md evidence as Blocking."
    ]
    _assert_run_revision_coverage_agreement(agreement)
    context_text = alignment_improvement_context_text(session)
    _assert_run_revision_context_text(context_text, run, agreement)
    preview = service.get_alignment_bundle(session["id"])
    assert preview["ok"] is True
    assert preview["bundle"]["metadata"]["source_bundle_id"] == ""
    assert "source_bundle_id" not in preview["yaml"]

# Merged from test_alignment_run_revision_malformed_trace_summary.py



def test_alignment_run_evidence_summary_drops_malformed_trace_shapes(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_revision_source_loop(service, sample_spec_file, sample_workdir, name="Malformed Evidence Summary Loop")
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

# Merged from test_alignment_run_source_projection.py

from loopora.service_alignment_run_source_projection import (
    alignment_run_evidence_summary,
    alignment_run_judgment_contract,
)


def test_alignment_run_source_projection_helpers_read_stable_artifacts(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_1"
    proof_path = tmp_path / "proof.md"
    (run_dir / "contract").mkdir(parents=True)
    (run_dir / "evidence").mkdir(parents=True)
    (run_dir / "contract" / "run_contract.json").write_text(
        json.dumps({"goal": "Ship the Loop.", "check_count": 1}, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "evidence" / "ledger.jsonl").write_text(
        json.dumps(
            {
                "id": "ev_1",
                "evidence_kind": "artifact",
                "claim": "A proof artifact exists.",
                "verifies": ["target:done_when.check_001:covered", 42],
                "artifact_refs": [
                    {
                        "kind": "workspace",
                        "label": "proof",
                        "relative_path": "proof.md",
                        "workspace_path": "proof.md",
                        "absolute_path": str(proof_path),
                        "debug_payload": "not stable",
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    run = {"runs_dir": str(run_dir)}

    assert alignment_run_judgment_contract(run)["goal"] == "Ship the Loop."
    assert alignment_run_evidence_summary(run) == [
        {
            "id": "ev_1",
            "kind": "artifact",
            "archetype": "",
            "step_id": "",
            "claim": "A proof artifact exists.",
            "result": "",
            "residual_risk": "",
            "verifies": ["target:done_when.check_001:covered"],
            "artifact_refs": [
                {
                    "kind": "workspace",
                    "label": "proof",
                    "relative_path": "proof.md",
                    "workspace_path": "proof.md",
                    "absolute_path": str(proof_path),
                }
            ],
        }
    ]

# Merged from test_alignment_run_source_redaction.py
import logging

from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_context_factory import AlignmentServiceContextFactory
from loopora.service_alignment_requests import RevisionAlignmentSessionRequest, default_alignment_executor_settings
from loopora.service_alignment_revision import create_revision_alignment_session


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
        AlignmentServiceContextFactory(service, logging.getLogger("tests.alignment")).revision_context(),
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

# Merged from test_alignment_run_source_seed_identity.py
from loopora.service_alignment_source_seed import alignment_run_revision_source_context, alignment_run_source_seed


def test_alignment_run_source_seed_preserves_projection_inputs_and_redacts_judgments() -> None:
    payload = alignment_run_source_seed(
        {"source_run_id": "run_1"},
        {
            "id": "run_1",
            "loop_id": "loop_1",
            "status": "succeeded",
            "task_verdict": {"summary": "Observed Authorization: Bearer RUN_TASK_TOKEN_SECRET"},
            "last_verdict_json": {"decision_summary": "tool --token RUN_GATE_TOKEN_SECRET"},
        },
        {"loop": {"completion_mode": "all_checks_pass"}},
        source_bundle_id="bundle_1",
        artifact_paths={"result": "/tmp/result.json"},
        judgment_contract={"done_when": ["proof exists"]},
        coverage_summary={"status": "covered"},
        evidence_summary=[{"claim": "Cookie: sid=RUN_EVIDENCE_COOKIE_SECRET"}],
        seed_bundle={"metadata": {"name": "Run seed"}},
    )
    rendered_agreement = str(payload["working_agreement"])

    assert "RUN_TASK_TOKEN_SECRET" not in rendered_agreement
    assert "RUN_GATE_TOKEN_SECRET" not in rendered_agreement
    assert "RUN_EVIDENCE_COOKIE_SECRET" not in rendered_agreement
    assert "<secret omitted>" in rendered_agreement
    assert payload["linked_bundle_id"] == "bundle_1"
    assert payload["linked_loop_id"] == "loop_1"
    assert payload["linked_run_id"] == "run_1"
    assert payload["working_agreement"]["source"]["artifact_paths"] == {"result": "/tmp/result.json"}
    assert payload["working_agreement"]["source"]["judgment_contract"] == {"done_when": ["proof exists"]}
    assert payload["event"] == {
        "source_type": "run",
        "source_bundle_id": "bundle_1",
        "source_loop_id": "loop_1",
        "source_run_id": "run_1",
        "source_alignment_session_id": "",
        "spec_path": "",
        "reason": "improve_from_workdir_run_evidence",
    }


def test_alignment_run_revision_source_context_preserves_projection_inputs() -> None:
    source = alignment_run_revision_source_context(
        "run_1",
        {
            "status": "succeeded",
            "task_verdict": {"summary": "pass"},
            "last_verdict_json": {"decision_summary": "accepted"},
        },
        {"loop": {"completion_mode": "manual_review"}},
        source_bundle_id="bundle_1",
        artifact_paths={"result": "/tmp/result.json"},
        judgment_contract={"done_when": ["proof"]},
        coverage_summary={"status": "covered"},
        evidence_summary=[{"claim": "ok"}],
    )

    assert source == {
        "mode": "improvement",
        "source_type": "run",
        "source_bundle_id": "bundle_1",
        "source_run_id": "run_1",
        "source_completion_mode": "manual_review",
        "reason": "improve_from_run_evidence",
        "run_status": "succeeded",
        "artifact_paths": {"result": "/tmp/result.json"},
        "judgment_contract": {"done_when": ["proof"]},
        "coverage_summary": {"status": "covered"},
        "evidence_summary": [{"claim": "ok"}],
        "task_verdict": {"summary": "pass"},
        "gatekeeper_verdict": {"decision_summary": "accepted"},
    }

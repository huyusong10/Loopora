from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.service_alignment_prompting import AlignmentPromptBuildContext, build_alignment_prompt
from loopora.web import build_app

from alignment_test_support import _create_alignment_improvement_source_bundle


def alignment_prompt(session: dict, *, mode: str = "normal") -> str:
    return build_alignment_prompt(AlignmentPromptBuildContext(), session, mode=mode)


def test_alignment_workdir_context_run_option_exposes_artifact_refs_and_rehydrates_source(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    source = _create_alignment_improvement_source_bundle(service, sample_spec_file, sample_workdir)
    run = service.rerun(source["loop_id"])

    context = service.get_alignment_workdir_context(sample_workdir)
    run_option = next(option for option in context["options"] if option.get("source_run_id") == run["id"])

    assert run_option["source_type"] == "run"
    assert "Loop 裁决" in run_option["description_zh"]
    assert "守门裁决" in run_option["description_zh"]
    for option in context["options"]:
        description_zh = option.get("description_zh", "")
        assert "task verdict" not in description_zh
        assert "最近一次 run" not in description_zh
        assert "GateKeeper" not in description_zh
        assert "bundle" not in description_zh
        assert "spec、roles" not in description_zh
        assert "workflow" not in description_zh
    assert run_option["artifact_paths"] == {
        "run_contract": "contract/run_contract.json",
        "task_verdict": "evidence/task_verdict.json",
        "evidence_ledger": "evidence/ledger.jsonl",
        "evidence_coverage": "evidence/coverage.json",
        "evidence_manifest": "evidence/manifest.json",
    }
    assert "evidence_summary" not in run_option
    assert "task_verdict" not in run_option
    assert "gatekeeper_verdict" not in run_option

    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="基于这次 run 的证据继续改进方案。",
        source_option_id=run_option["option_id"],
        start_immediately=False,
    )

    agreement = session["working_agreement"]
    assert agreement["mode"] == "improvement"
    assert agreement["source"]["source_type"] == "run"
    assert agreement["source"]["source_bundle_id"] == source["id"]
    assert agreement["source"]["source_run_id"] == run["id"]
    assert agreement["source"]["artifact_paths"] == {
        "run_contract": "contract/run_contract.json",
        "task_verdict": "evidence/task_verdict.json",
        "evidence_ledger": "evidence/ledger.jsonl",
        "evidence_coverage": "evidence/coverage.json",
        "evidence_manifest": "evidence/manifest.json",
    }
    assert agreement["source"]["judgment_contract"]["contract_path"] == "contract/run_contract.json"
    assert agreement["source"]["task_verdict"]["status"]
    assert agreement["source"]["gatekeeper_verdict"]["decision_summary"]
    assert any(item["artifact_refs"] for item in agreement["source"]["evidence_summary"])
    prompt = alignment_prompt(session)
    assert "Recent evidence summary:" in prompt
    assert "Frozen judgment contract:" in prompt
    assert "artifact_refs" in prompt


def test_alignment_workdir_context_api_creates_selected_source_session(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    state_dir = sample_workdir / ".loopora"
    state_dir.mkdir()
    spec_path = state_dir / "spec.md"
    spec_path.write_text("# Task\n\n整理一个可验证的改进 Loop。\n", encoding="utf-8")
    client = TestClient(build_app(service=service))

    context_response = client.post("/api/alignments/workdir-context", json={"workdir": str(sample_workdir)})
    assert context_response.status_code == HTTPStatus.OK
    context_payload = context_response.json()
    spec_option = next(option for option in context_payload["options"] if option["source_type"] == "spec_file")

    create_response = client.post(
        "/api/alignments/sessions",
        json={
            "workdir": str(sample_workdir),
            "message": "基于已有 spec 继续对齐。",
            "source_option_id": spec_option["option_id"],
        },
    )
    assert create_response.status_code == HTTPStatus.CREATED
    session = create_response.json()["session"]
    assert session["working_agreement"]["mode"] == "selected_source"
    assert session["working_agreement"]["source"]["spec_path"] == str(spec_path)


def test_alignment_selected_spec_source_degrades_invalid_utf8(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    state_dir = sample_workdir / ".loopora"
    state_dir.mkdir()
    spec_path = state_dir / "spec.md"
    spec_path.write_bytes(b"\xff")

    context = service.get_alignment_workdir_context(sample_workdir)
    spec_option = next(option for option in context["options"] if option["source_type"] == "spec_file")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Use this spec as source context.",
        source_option_id=spec_option["option_id"],
        start_immediately=False,
    )

    source = session["working_agreement"]["source"]
    assert source["spec_path"] == str(spec_path)
    assert source["artifact_paths"] == {"spec": str(spec_path)}
    assert source["spec_markdown"] == "Source file could not be read as UTF-8 text."

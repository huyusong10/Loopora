from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
import shlex

from fastapi.testclient import TestClient

from loopora.service_types import LooporaWorkdirUnavailableError
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


def test_alignment_session_seed_write_failure_returns_recovery(
    monkeypatch,
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    source = _create_alignment_improvement_source_bundle(service, sample_spec_file, sample_workdir)
    context = service.get_alignment_workdir_context(sample_workdir)
    source_option = next(option for option in context["options"] if option.get("source_bundle_id") == source["id"])
    private_path = tmp_path / "private" / "bundle.yml"
    original_replace = Path.replace

    def fail_seed_bundle_replace(path: Path, target: Path) -> Path:
        target_path = Path(target)
        if target_path.name == "bundle.yml" and "alignment_sessions" in target_path.parts:
            raise OSError(f"permission denied: {private_path}")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_seed_bundle_replace)
    client = TestClient(build_app(service=service), raise_server_exceptions=False)

    response = client.post(
        "/api/alignments/sessions",
        json={
            "workdir": str(sample_workdir),
            "message": "Improve the selected Plan File through Web alignment.",
            "source_option_id": source_option["option_id"],
        },
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    payload = response.json()
    expected_actions = [
        "review_alignment_source_context",
        "retry_alignment_session_create",
        "open_support",
    ]
    assert payload["ok"] is False
    assert payload["error"] == "alignment session could not be created"
    assert payload["resource_recovery"] == "alignment_session_creation_failed"
    assert payload["status"] == "blocked_by_alignment_session_creation"
    assert payload["surface"] == "web_alignment"
    assert payload["action"] == "create_alignment_session"
    assert payload["workdir"] == str(sample_workdir)
    assert payload["source_option_id"] == source_option["option_id"]
    assert [item["kind"] for item in payload["next_actions"]] == expected_actions
    assert payload["next_actions"][0]["endpoint"] == "/api/alignments/workdir-context"
    assert payload["next_actions"][1]["endpoint"] == "/api/alignments/sessions"
    assert payload["next_actions"][1]["after_action"] == "review_alignment_source_context"
    assert payload["next_actions"][2]["redirect_url"].startswith("/support")
    assert payload["next_action_kinds"] == expected_actions
    assert payload["next_action_ready_now_kinds"] == ["review_alignment_source_context", "open_support"]
    assert payload["next_action_ready_after_actions"] == {
        "retry_alignment_session_create": "review_alignment_source_context",
    }
    summary = payload["web_alignment_session_recovery_summary"]
    assert summary["next_action_kinds"] == expected_actions
    assert summary["next_action_ready_after_actions"] == payload["next_action_ready_after_actions"]
    assert "permission denied" not in response.text
    assert str(private_path) not in response.text
    assert service.list_alignment_sessions() == []


def test_alignment_workdir_context_api_projects_service_workdir_race_as_recovery(
    monkeypatch,
    service_factory,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    context_workdir = tmp_path / "context-race"
    session_workdir = tmp_path / "session-race"
    context_workdir.mkdir()
    session_workdir.mkdir()
    client = TestClient(build_app(service=service))

    def fail_context(_workdir: Path):
        context_workdir.rmdir()
        raise LooporaWorkdirUnavailableError(workdir=str(context_workdir), workdir_state="missing", action="alignment")

    monkeypatch.setattr(service, "get_alignment_workdir_context", fail_context)
    context_response = client.post("/api/alignments/workdir-context", json={"workdir": str(context_workdir)})

    assert context_response.status_code == HTTPStatus.BAD_REQUEST
    context_payload = context_response.json()
    assert context_payload["loop_recovery"] == "target_workdir_unavailable"
    assert context_payload["status"] == "blocked_by_workdir"
    assert context_payload["surface"] == "web_alignment"
    assert context_payload["action"] == "workdir_context"
    assert context_payload["workdir_state"]["status"] == "missing"

    def fail_session(**_kwargs):
        session_workdir.rmdir()
        raise LooporaWorkdirUnavailableError(workdir=str(session_workdir), workdir_state="missing", action="alignment")

    monkeypatch.setattr(service, "create_alignment_session", fail_session)
    session_response = client.post(
        "/api/alignments/sessions",
        json={"workdir": str(session_workdir), "message": "Create a Loop from this project."},
    )

    assert session_response.status_code == HTTPStatus.BAD_REQUEST
    session_payload = session_response.json()
    assert session_payload["loop_recovery"] == "target_workdir_unavailable"
    assert session_payload["status"] == "blocked_by_workdir"
    assert session_payload["surface"] == "web_alignment"
    assert session_payload["action"] == "create_alignment_session"
    assert session_payload["workdir_state"]["status"] == "missing"
    assert service.list_alignment_sessions() == []


def test_alignment_workdir_context_api_explains_unusable_workdir_before_compose(
    service_factory,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    missing_workdir = tmp_path / "missing project"
    file_workdir = tmp_path / "not-a-project"
    file_workdir.write_text("not a directory\n", encoding="utf-8")
    original_file = file_workdir.read_text(encoding="utf-8")

    for path, body, action in [
        ("/api/alignments/workdir-context", {"workdir": str(missing_workdir)}, "workdir_context"),
        (
            "/api/alignments/sessions",
            {"workdir": str(missing_workdir), "message": "Create a Loop from this project."},
            "create_alignment_session",
        ),
    ]:
        response = client.post(path, json=body)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert not missing_workdir.exists()
        payload = response.json()
        assert payload["loop_recovery"] == "target_workdir_unavailable"
        assert payload["status"] == "blocked_by_workdir"
        assert payload["surface"] == "web_alignment"
        assert payload["action"] == action
        assert payload["workdir"] == str(missing_workdir.resolve())
        assert payload["workdir_state"]["status"] == "missing"
        assert payload["workdir_state"]["usable_for_web_alignment"] is False
        assert "workdir does not exist:" not in payload["error"]
        assert "First run:" in payload["error"]
        assert payload["workdir_state"]["commands"]["create"] == f"mkdir -p {shlex.quote(str(missing_workdir.resolve()))}"
        assert [item["kind"] for item in payload["next_actions"]] == [
            "create_workdir",
            "confirm_readiness",
            "retry_web_compose",
        ]
        assert "loopora doctor --workdir" in payload["next_actions"][1]["command"]
        assert payload["next_actions"][2]["target"] == "web_alignment"
        assert service.list_alignment_sessions() == []

    for path, body, action in [
        ("/api/alignments/workdir-context", {"workdir": ""}, "workdir_context"),
        ("/api/alignments/sessions", {"workdir": "", "message": "Create a Loop from this project."}, "create_alignment_session"),
    ]:
        response = client.post(path, json=body)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        payload = response.json()
        assert payload["loop_recovery"] == "target_workdir_unavailable"
        assert payload["status"] == "blocked_by_workdir"
        assert payload["surface"] == "web_alignment"
        assert payload["action"] == action
        assert payload["workdir"] == ""
        assert payload["workdir_state"]["status"] == "required"
        assert [item["kind"] for item in payload["next_actions"]] == [
            "choose_workdir",
            "confirm_readiness",
            "retry_web_compose",
        ]
        assert "command" not in payload["next_actions"][1]
        assert "command" not in payload["next_actions"][2]
        assert payload["next_actions"][2]["target"] == "web_alignment"
        assert service.list_alignment_sessions() == []

    file_response = client.post("/api/alignments/workdir-context", json={"workdir": str(file_workdir)})

    assert file_response.status_code == HTTPStatus.BAD_REQUEST
    assert file_workdir.read_text(encoding="utf-8") == original_file
    file_payload = file_response.json()
    assert file_payload["loop_recovery"] == "target_workdir_unavailable"
    assert file_payload["status"] == "blocked_by_workdir"
    assert file_payload["workdir"] == str(file_workdir.resolve())
    assert file_payload["workdir_state"]["status"] == "not_directory"
    assert file_payload["workdir_state"]["usable_for_web_alignment"] is False
    assert file_payload["workdir_state"]["commands"] == {}
    assert [item["kind"] for item in file_payload["next_actions"]] == [
        "choose_workdir",
        "confirm_readiness",
        "retry_web_compose",
    ]
    assert "Target project path exists but is not a directory" in file_payload["error"]


def test_alignment_workdir_context_api_projects_path_normalization_failure_as_recovery(
    service_factory,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    for path, body, action in [
        ("/api/alignments/workdir-context", {"workdir": "bad\0workdir"}, "workdir_context"),
        (
            "/api/alignments/sessions",
            {"workdir": "bad\0workdir", "message": "Create a Loop from this project."},
            "create_alignment_session",
        ),
    ]:
        response = client.post(path, json=body)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        payload = response.json()
        assert payload["loop_recovery"] == "target_workdir_unavailable"
        assert payload["status"] == "blocked_by_workdir"
        assert payload["surface"] == "web_alignment"
        assert payload["action"] == action
        assert payload["workdir"] == ""
        assert payload["workdir_state"]["status"] == "unavailable"
        assert payload["workdir_state"]["error"] == "workdir could not be inspected"
        assert [item["kind"] for item in payload["next_actions"]] == [
            "choose_workdir",
            "confirm_readiness",
            "retry_web_compose",
        ]
        assert all("command" not in item for item in payload["next_actions"])
        assert "embedded null" not in response.text
        assert str(Path.cwd()) not in response.text

    assert service.list_alignment_sessions() == []


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

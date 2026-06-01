from __future__ import annotations

import json
from pathlib import Path

import pytest

from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_context import (
    add_alignment_context_option,
    alignment_bundle_context_option,
    alignment_context_option_by_id,
    alignment_context_title_from_session,
    alignment_file_bundle_context_option,
    alignment_loop_context_option,
    alignment_run_context_option,
    alignment_session_context_options,
    alignment_source_option_seed_kind,
    alignment_spec_file_context_option,
    bounded_alignment_context_options,
)
from loopora.service_alignment_language import (
    alignment_generation_prefers_chinese,
    alignment_prefers_chinese,
    alignment_user_language_hint,
)
from loopora.service_alignment_run_source_projection import (
    alignment_run_artifact_paths,
    alignment_run_evidence_summary,
    alignment_run_judgment_contract,
)
from loopora.service_alignment_ready_bundle_validation import (
    alignment_assert_bundle_workdir,
    alignment_bundle_file_has_ready_validation,
    alignment_bundle_file_is_valid_alignment_bundle,
)
from loopora.service_alignment_source_seed import (
    alignment_bundle_completion_mode,
    alignment_bundle_revision_source_context,
    alignment_bundle_source_seed,
    alignment_loop_bundle_id,
    alignment_loop_source_seed,
    alignment_revision_seed_bundle,
    alignment_run_revision_source_context,
    alignment_run_source_seed,
    alignment_session_source_seed,
    alignment_source_seed_payload,
    alignment_spec_file_source_seed,
    alignment_transcript_source_summary,
    bounded_alignment_file_text,
    redact_alignment_source_value,
)
from loopora.service_alignment_workdir_snapshot import alignment_same_workdir, alignment_workdir_spec_candidates
from loopora.service_types import LooporaError


REPO_ROOT = Path(__file__).resolve().parents[3]


def _loopora_source(module_name: str) -> str:
    return (REPO_ROOT / "src" / "loopora" / module_name).read_text(encoding="utf-8")


def test_alignment_ready_bundle_validation_has_dedicated_boundary() -> None:
    context_source = _loopora_source("service_alignment_context.py")
    ready_validation_source = _loopora_source("service_alignment_ready_bundle_validation.py")
    workdir_context_source = _loopora_source("service_alignment_workdir_context.py")
    validation_source = _loopora_source("service_alignment_validation.py")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_alignment_ready_bundle_validation import" in context_source
    for marker in (
        "def alignment_assert_bundle_workdir",
        "def alignment_bundle_file_is_valid_alignment_bundle",
        "def alignment_bundle_file_has_ready_validation",
        "def alignment_session_has_current_ready_bundle",
    ):
        assert marker in ready_validation_source
        assert marker not in context_source
    assert "from loopora.service_alignment_ready_bundle_validation import alignment_bundle_file_has_ready_validation" in workdir_context_source
    assert "from loopora.service_alignment_ready_bundle_validation import alignment_assert_bundle_workdir" in validation_source
    assert "service_alignment_ready_bundle_validation.py" in contracts_source


def test_alignment_source_context_helpers_have_dedicated_boundary() -> None:
    context_source = _loopora_source("service_alignment_context.py")
    seed_source = _loopora_source("service_alignment_source_seed.py")
    source_context = _loopora_source("service_alignment_source_context.py")
    context_factory_source = _loopora_source("service_alignment_context_factory.py")
    artifacts_source = _loopora_source("service_alignment_artifacts.py")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_alignment_source_context import" in seed_source
    assert "from loopora.service_alignment_source_context import" in context_source
    assert "from loopora.service_alignment_source_context import redact_alignment_source_value" in context_factory_source
    assert "from loopora.service_alignment_source_context import redact_alignment_source_value" in artifacts_source
    for marker in (
        "def bounded_alignment_file_text",
        "def alignment_transcript_source_summary",
        "def redact_alignment_source_value",
    ):
        assert marker in source_context
        assert marker not in seed_source
    for marker in (
        "def alignment_source_seed_payload",
        "def alignment_bundle_source_seed",
        "def alignment_run_source_seed",
        "def alignment_session_source_seed",
    ):
        assert marker in seed_source
        assert marker not in source_context
    assert "service_alignment_source_context.py" in contracts_source
    assert "service_alignment_source_seed.py" in contracts_source


def test_alignment_context_title_from_session_uses_first_redacted_user_message() -> None:
    title = alignment_context_title_from_session(
        {
            "id": "session_fallback",
            "transcript": [
                {"role": "assistant", "content": "Ignore assistant text."},
                {"role": "user", "content": "Please improve Authorization: Bearer CONTEXT_TITLE_TOKEN_SECRET"},
            ],
        }
    )

    assert "CONTEXT_TITLE_TOKEN_SECRET" not in title
    assert title.startswith("Please improve Authorization:")
    assert "<secret omitted>" in title


def test_alignment_language_projection_ignores_neutral_confirmations_and_preserves_ready_review_language() -> None:
    neutral_confirmation = {
        "alignment_stage": "clarifying",
        "transcript": [
            {"role": "user", "content": "OK"},
            {"role": "user", "content": "请继续整理证据。"},
        ],
    }
    ready_review = {
        "alignment_stage": "ready_review",
        "transcript": [{"role": "user", "content": "Please improve this Loop."}],
        "working_agreement": {
            "summary": "继续保留中文预览。",
            "readiness_evidence": {"task_scope": "中文证据"},
        },
    }

    assert alignment_prefers_chinese(neutral_confirmation) is True
    assert alignment_generation_prefers_chinese(ready_review) is True
    assert alignment_user_language_hint(ready_review).startswith("Chinese. Preserve the existing READY preview")
    assert alignment_user_language_hint({"transcript": [{"role": "user", "content": "Please continue."}]}).startswith(
        "Follow the user's language"
    )


def test_alignment_context_option_builder_redacts_labels_and_deduplicates() -> None:
    options: list[dict] = []
    seen: set[str] = set()
    option = {
        "option_id": "bundle:source",
        "label_en": "Improve Authorization: Bearer CONTEXT_OPTION_TOKEN_SECRET",
        "description_en": "Use Cookie: sid=CONTEXT_OPTION_COOKIE_SECRET",
    }

    add_alignment_context_option(option, options, seen)
    add_alignment_context_option({"option_id": "bundle:source", "label_en": "Duplicate"}, options, seen)

    rendered = str(options)
    assert len(options) == 1
    assert "CONTEXT_OPTION_TOKEN_SECRET" not in rendered
    assert "CONTEXT_OPTION_COOKIE_SECRET" not in rendered
    assert "<secret omitted>" in rendered


def test_alignment_context_option_by_id_matches_exact_dict_option() -> None:
    selected = alignment_context_option_by_id(
        [
            {"option_id": "bundle:one", "label_en": "One"},
            "not-an-option",
            {"option_id": "bundle:two", "label_en": "Two"},
        ],
        "bundle:two",
    )

    assert selected == {"option_id": "bundle:two", "label_en": "Two"}
    assert alignment_context_option_by_id([{"option_id": "bundle:one"}], "bundle:missing") == {}
    assert alignment_context_option_by_id([{"option_id": "bundle:one"}], "") == {}


def test_alignment_source_option_seed_kind_normalizes_session_sources() -> None:
    assert alignment_source_option_seed_kind({"source_type": "alignment_session"}) == "alignment_session"
    assert alignment_source_option_seed_kind({"source_type": "alignment_session_file"}) == "alignment_session"
    assert alignment_source_option_seed_kind({"source_type": "run"}) == "run"
    assert alignment_source_option_seed_kind({}) == ""


def test_alignment_bundle_completion_mode_handles_missing_or_invalid_loop() -> None:
    assert alignment_bundle_completion_mode({"loop": {"completion_mode": "all_checks_pass"}}) == "all_checks_pass"
    assert alignment_bundle_completion_mode({"loop": "not-a-dict"}) == ""
    assert alignment_bundle_completion_mode({}) == ""


def test_alignment_loop_bundle_id_handles_missing_or_invalid_bundle() -> None:
    assert alignment_loop_bundle_id({"bundle": {"id": "bundle_1"}}) == "bundle_1"
    assert alignment_loop_bundle_id({"bundle": "not-a-dict"}) == ""
    assert alignment_loop_bundle_id({}) == ""


def test_alignment_revision_seed_bundle_clears_import_identity_without_mutating_source() -> None:
    source_bundle = {
        "metadata": {
            "name": "Source bundle",
            "bundle_id": "bundle_1",
            "source_bundle_id": "bundle_source",
            "revision": 3,
        },
        "spec": {"markdown": "Task"},
    }

    seed = alignment_revision_seed_bundle(source_bundle)

    assert seed["metadata"] == {"name": "Source bundle", "bundle_id": ""}
    assert source_bundle["metadata"]["bundle_id"] == "bundle_1"
    assert source_bundle["metadata"]["source_bundle_id"] == "bundle_source"
    assert source_bundle["metadata"]["revision"] == 3


def test_alignment_context_option_budget_preserves_regenerate_choice() -> None:
    options = [{"option_id": f"source:{index}"} for index in range(4)]
    options.append({"option_id": "regenerate"})

    bounded = bounded_alignment_context_options(options, limit=3)

    assert [option["option_id"] for option in bounded] == ["source:0", "source:1", "regenerate"]


def test_alignment_workdir_spec_candidates_list_root_then_loop_specs_with_budget(tmp_path: Path) -> None:
    state_dir = tmp_path / ".loopora"
    root_spec = state_dir / "spec.md"
    loop_02_spec = state_dir / "loops" / "loop_02" / "spec.md"
    loop_01_spec = state_dir / "loops" / "loop_01" / "spec.md"
    root_spec.parent.mkdir(parents=True)
    loop_02_spec.parent.mkdir(parents=True)
    loop_01_spec.parent.mkdir(parents=True)
    root_spec.write_text("# Root spec\n", encoding="utf-8")
    loop_02_spec.write_text("# Loop 02 spec\n", encoding="utf-8")
    loop_01_spec.write_text("# Loop 01 spec\n", encoding="utf-8")
    (state_dir / "loops" / "loop_00").mkdir(parents=True)

    candidates = alignment_workdir_spec_candidates(state_dir)

    assert candidates[:3] == [root_spec, loop_01_spec, loop_02_spec]
    assert alignment_workdir_spec_candidates(tmp_path / "missing") == []


def test_alignment_workdir_spec_candidates_caps_source_budget(tmp_path: Path) -> None:
    state_dir = tmp_path / ".loopora"
    (state_dir / "loops").mkdir(parents=True)
    for index in range(25):
        spec_path = state_dir / "loops" / f"loop_{index:02d}" / "spec.md"
        spec_path.parent.mkdir()
        spec_path.write_text(f"# Loop {index}\n", encoding="utf-8")

    candidates = alignment_workdir_spec_candidates(state_dir)

    assert len(candidates) == 20
    assert candidates[0] == state_dir / "loops" / "loop_00" / "spec.md"
    assert candidates[-1] == state_dir / "loops" / "loop_19" / "spec.md"


def test_alignment_same_workdir_resolves_path_identity(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()

    assert alignment_same_workdir(root, root)
    assert alignment_same_workdir(root / ".." / "project", root)
    assert not alignment_same_workdir("", root)
    assert not alignment_same_workdir(tmp_path / "other", root)


def test_alignment_bundle_file_ready_validation_requires_current_valid_bundle(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    bundle_path = tmp_path / ".loopora" / "alignment_sessions" / "align_ready" / "artifacts" / "bundle.yml"
    bundle_path.parent.mkdir(parents=True)
    bundle_path.write_text(alignment_bundle_yaml(str(workdir.resolve())), encoding="utf-8")

    assert alignment_bundle_file_is_valid_alignment_bundle(bundle_path, expected_workdir=workdir)
    assert not alignment_bundle_file_has_ready_validation(bundle_path, expected_workdir=workdir)

    (bundle_path.parent / "validation.json").write_text('{"ok": true}\n', encoding="utf-8")

    assert alignment_bundle_file_has_ready_validation(bundle_path, expected_workdir=workdir)
    assert not alignment_bundle_file_has_ready_validation(bundle_path, expected_workdir=tmp_path / "other")


def test_alignment_assert_bundle_workdir_fails_closed_on_mismatch(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    bundle = load_bundle_text(alignment_bundle_yaml(str(workdir.resolve())))

    alignment_assert_bundle_workdir(bundle, expected_workdir=workdir)
    with pytest.raises(LooporaError):
        alignment_assert_bundle_workdir(bundle, expected_workdir=tmp_path / "other")


def test_alignment_session_context_options_project_continue_and_current_ready_bundle(tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    bundle_path = tmp_path / ".loopora" / "alignment_sessions" / "align_ready" / "artifacts" / "bundle.yml"
    bundle_path.parent.mkdir(parents=True)
    bundle_path.write_text(alignment_bundle_yaml(str(workdir.resolve())), encoding="utf-8")
    session = {
        "id": "align_ready",
        "status": "ready",
        "workdir": str(workdir),
        "bundle_path": str(bundle_path),
        "validation": {"ok": True},
        "updated_at": "2026-01-01T00:00:00+00:00",
        "transcript": [{"role": "user", "content": "Improve Authorization: Bearer SESSION_OPTION_TOKEN_SECRET"}],
    }

    options = alignment_session_context_options(session)
    wrong_workdir_options = alignment_session_context_options({**session, "workdir": str(tmp_path / "other")})

    assert [option["action"] for option in options] == ["continue_session", "improve"]
    assert options[0]["option_id"] == "continue_session:align_ready"
    assert options[1]["option_id"] == "alignment_session:align_ready"
    assert options[1]["bundle_path"] == str(bundle_path)
    assert "SESSION_OPTION_TOKEN_SECRET" not in str(options)
    assert "<secret omitted>" in str(options)
    assert [option["action"] for option in wrong_workdir_options] == ["continue_session"]


def test_alignment_source_option_factories_preserve_source_identity(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.yml"
    spec_path = tmp_path / "spec.md"

    file_option = alignment_file_bundle_context_option(source_session_id="session_1", bundle_path=bundle_path)
    bundle_option = alignment_bundle_context_option(
        "bundle_1",
        loop={"id": "loop_1", "name": "Loop One"},
        bundle={"name": "Bundle One"},
    )
    loop_option = alignment_loop_context_option({"id": "loop_2", "name": "Loop Two"})
    run_option = alignment_run_context_option(
        {"id": "run_1", "loop_id": "loop_1", "status": "succeeded", "runs_dir": str(tmp_path / "run_1")},
        loop={"id": "loop_1", "name": "Loop One"},
    )
    spec_option = alignment_spec_file_context_option(spec_path)

    assert file_option["source_alignment_session_id"] == "session_1"
    assert file_option["bundle_path"] == str(bundle_path)
    assert bundle_option["source_bundle_id"] == "bundle_1"
    assert bundle_option["source_loop_id"] == "loop_1"
    assert loop_option["source_loop_id"] == "loop_2"
    assert run_option["source_run_id"] == "run_1"
    assert run_option["artifact_paths"] == alignment_run_artifact_paths({"runs_dir": str(tmp_path / "run_1")})
    assert spec_option["spec_path"] == str(spec_path)
    assert spec_option["option_id"].startswith("spec_file:")


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


def test_alignment_source_seed_payload_redacts_source_and_emits_identity_event() -> None:
    payload = alignment_source_seed_payload(
        {
            "mode": "improvement",
            "source_type": "run",
            "source_bundle_id": "bundle_1",
            "source_loop_id": "loop_1",
            "source_run_id": "run_1",
            "reason": "improve_from_run",
            "auth_token": "SOURCE_SEED_TOKEN_SECRET",
            "nested": {"cookie": "sid=SOURCE_SEED_COOKIE_SECRET"},
        },
        seed_bundle={"metadata": {"name": "Seed", "api_key": "SOURCE_SEED_API_SECRET"}},
        linked_bundle_id="bundle_1",
        linked_loop_id="loop_1",
        linked_run_id="run_1",
    )
    rendered = str(payload["working_agreement"])

    assert "SOURCE_SEED_TOKEN_SECRET" not in rendered
    assert "SOURCE_SEED_COOKIE_SECRET" not in rendered
    assert "SOURCE_SEED_API_SECRET" not in rendered
    assert payload["linked_bundle_id"] == "bundle_1"
    assert payload["linked_loop_id"] == "loop_1"
    assert payload["linked_run_id"] == "run_1"
    assert payload["event"] == {
        "source_type": "run",
        "source_bundle_id": "bundle_1",
        "source_loop_id": "loop_1",
        "source_run_id": "run_1",
        "source_alignment_session_id": "",
        "spec_path": "",
        "reason": "improve_from_run",
    }
    assert "<secret omitted>" in rendered


def test_alignment_spec_file_source_seed_reads_redacted_spec_and_emits_identity_event(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("Task uses Authorization: Bearer SPEC_SOURCE_TOKEN_SECRET.\n", encoding="utf-8")

    payload = alignment_spec_file_source_seed({"spec_path": str(spec_path)})
    rendered_source = str(payload["working_agreement"]["source"])

    assert "SPEC_SOURCE_TOKEN_SECRET" not in rendered_source
    assert "<secret omitted>" in rendered_source
    assert payload["seed_bundle"] == {}
    assert payload["linked_bundle_id"] == ""
    assert payload["event"] == {
        "source_type": "spec_file",
        "source_bundle_id": "",
        "source_loop_id": "",
        "source_run_id": "",
        "source_alignment_session_id": "",
        "spec_path": str(spec_path),
        "reason": "start_from_workdir_spec",
    }
    assert payload["working_agreement"]["source"]["artifact_paths"] == {"spec": str(spec_path)}


def test_alignment_bundle_source_seed_preserves_identity_and_seed_metadata() -> None:
    payload = alignment_bundle_source_seed(
        {"source_bundle_id": "bundle_1", "source_loop_id": "loop_from_option"},
        {
            "loop_id": "loop_from_bundle",
            "loop": {"completion_mode": "all_checks_pass"},
        },
        seed_bundle={
            "metadata": {
                "name": "Bundle seed",
                "auth_token": "BUNDLE_SOURCE_SEED_TOKEN_SECRET",
            }
        },
    )
    rendered_agreement = str(payload["working_agreement"])

    assert "BUNDLE_SOURCE_SEED_TOKEN_SECRET" not in rendered_agreement
    assert "<secret omitted>" in rendered_agreement
    assert payload["linked_bundle_id"] == "bundle_1"
    assert payload["linked_loop_id"] == ""
    assert payload["working_agreement"]["source"]["source_loop_id"] == "loop_from_option"
    assert payload["working_agreement"]["source"]["source_completion_mode"] == "all_checks_pass"
    assert payload["event"] == {
        "source_type": "bundle",
        "source_bundle_id": "bundle_1",
        "source_loop_id": "loop_from_option",
        "source_run_id": "",
        "source_alignment_session_id": "",
        "spec_path": "",
        "reason": "improve_from_workdir_context",
    }


def test_alignment_bundle_revision_source_context_preserves_revision_reason() -> None:
    source = alignment_bundle_revision_source_context(
        "bundle_1",
        {"loop": {"completion_mode": "all_checks_pass"}},
    )

    assert source == {
        "mode": "improvement",
        "source_type": "bundle",
        "source_bundle_id": "bundle_1",
        "source_run_id": "",
        "source_completion_mode": "all_checks_pass",
        "reason": "improve_imported_bundle",
        "run_status": "",
        "evidence_summary": [],
        "task_verdict": {},
        "gatekeeper_verdict": {},
    }


def test_alignment_loop_source_seed_preserves_loop_identity_and_seed_metadata() -> None:
    payload = alignment_loop_source_seed(
        {"source_loop_id": "loop_1"},
        {"id": "loop_1", "name": "Improve --token LOOP_NAME_TOKEN_SECRET"},
        {"loop": {"completion_mode": "manual_review"}},
        seed_bundle={"metadata": {"name": "Loop seed"}},
    )
    rendered_agreement = str(payload["working_agreement"])

    assert "LOOP_NAME_TOKEN_SECRET" not in rendered_agreement
    assert "<secret omitted>" in rendered_agreement
    assert payload["linked_bundle_id"] == ""
    assert payload["linked_loop_id"] == "loop_1"
    assert payload["working_agreement"]["source"]["source_completion_mode"] == "manual_review"
    assert payload["event"] == {
        "source_type": "loop",
        "source_bundle_id": "",
        "source_loop_id": "loop_1",
        "source_run_id": "",
        "source_alignment_session_id": "",
        "spec_path": "",
        "reason": "improve_from_workdir_loop",
    }


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


def test_alignment_session_source_seed_preserves_session_identity_and_redacts_transcript() -> None:
    payload = alignment_session_source_seed(
        {
            "source_type": "alignment_session_file",
            "source_alignment_session_id": "align_1",
            "bundle_path": "/tmp/session-bundle.yml",
            "status": "ready",
        },
        {
            "id": "align_1",
            "status": "imported",
            "transcript": [
                {"role": "user", "content": "Use Cookie: sid=SESSION_TRANSCRIPT_COOKIE_SECRET", "created_at": "1"},
            ],
        },
        {"loop": {"completion_mode": "manual_review"}},
        seed_bundle={"metadata": {"name": "Session seed"}},
    )
    rendered_agreement = str(payload["working_agreement"])

    assert "SESSION_TRANSCRIPT_COOKIE_SECRET" not in rendered_agreement
    assert "<secret omitted>" in rendered_agreement
    assert payload["linked_bundle_id"] == ""
    assert payload["linked_loop_id"] == ""
    assert payload["linked_run_id"] == ""
    assert payload["working_agreement"]["source"]["source_status"] == "imported"
    assert payload["working_agreement"]["source"]["source_completion_mode"] == "manual_review"
    assert payload["event"] == {
        "source_type": "alignment_session_file",
        "source_bundle_id": "",
        "source_loop_id": "",
        "source_run_id": "",
        "source_alignment_session_id": "align_1",
        "spec_path": "",
        "reason": "improve_from_workdir_alignment_session",
    }


def test_redact_alignment_source_value_preserves_safe_structure() -> None:
    redacted = redact_alignment_source_value(
        {
            "source_type": "spec_file",
            "items": [{"label": "safe"}, {"password": "SOURCE_PASSWORD_SECRET"}],
        }
    )

    assert redacted == {
        "source_type": "spec_file",
        "items": [{"label": "safe"}, {"password": "<secret omitted>"}],
    }


def test_bounded_alignment_file_text_redacts_and_truncates(tmp_path: Path) -> None:
    source = tmp_path / "spec.md"
    source.write_text("Authorization: Bearer FILE_TEXT_TOKEN_SECRET\n" + ("x" * 80), encoding="utf-8")

    text = bounded_alignment_file_text(source, limit=40)

    assert "FILE_TEXT_TOKEN_SECRET" not in text
    assert "<secret omitted>" in text
    assert text.endswith("[Loopora truncated this source context for prompt size.]")


def test_alignment_transcript_source_summary_uses_recent_redacted_entries() -> None:
    session = {
        "transcript": [
            {"role": "user", "content": f"message {index}", "created_at": str(index)}
            for index in range(9)
        ]
        + [{"role": "assistant", "content": "Cookie: sid=TRANSCRIPT_COOKIE_SECRET", "created_at": "9"}]
    }

    summary = alignment_transcript_source_summary(session)
    rendered = str(summary)

    assert len(summary) == 8
    assert summary[0]["content"] == "message 2"
    assert "TRANSCRIPT_COOKIE_SECRET" not in rendered
    assert "<secret omitted>" in rendered

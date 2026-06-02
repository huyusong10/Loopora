from __future__ import annotations

from pathlib import Path

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
    alignment_spec_file_context_option,
    bounded_alignment_context_options,
)
from loopora.service_alignment_run_source_projection import alignment_run_artifact_paths


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


def test_alignment_context_option_budget_preserves_regenerate_choice() -> None:
    options = [{"option_id": f"source:{index}"} for index in range(4)]
    options.append({"option_id": "regenerate"})

    bounded = bounded_alignment_context_options(options, limit=3)

    assert [option["option_id"] for option in bounded] == ["source:0", "source:1", "regenerate"]


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

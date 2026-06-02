from __future__ import annotations

from pathlib import Path

import pytest

from loopora.service_alignment_context import alignment_source_option_id
from loopora.service_types import LooporaConflictError

from alignment_workdir_source_options_test_support import alignment_prompt


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

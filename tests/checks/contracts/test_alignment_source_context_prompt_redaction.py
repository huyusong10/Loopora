from __future__ import annotations

import json
from pathlib import Path

from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_prompting import AlignmentPromptBuildContext, build_alignment_prompt


def alignment_prompt(session: dict, *, mode: str = "normal") -> str:
    return build_alignment_prompt(AlignmentPromptBuildContext(), session, mode=mode)


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

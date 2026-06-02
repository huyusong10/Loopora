from __future__ import annotations

from pathlib import Path

from alignment_test_support import _create_alignment_improvement_source_bundle
from alignment_workdir_source_options_test_support import alignment_prompt


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

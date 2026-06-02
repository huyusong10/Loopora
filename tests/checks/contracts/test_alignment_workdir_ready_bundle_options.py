from __future__ import annotations

from pathlib import Path

from loopora.executor_fake_payloads import alignment_bundle_yaml

from alignment_test_support import _confirm_alignment_agreement
from alignment_workdir_source_options_test_support import (
    rewrite_bundle_workdir,
    weaken_ready_bundle_markdown,
    weaken_ready_bundle_text,
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
    weaken_ready_bundle_text(stale_ready_bundle)
    (stale_ready_bundle.parent / "validation.json").write_text('{"ok": true}\n', encoding="utf-8")
    wrong_workdir = sample_workdir.parent / "other-workdir"
    wrong_workdir_bundle.write_text(alignment_bundle_yaml(str(wrong_workdir.resolve())), encoding="utf-8")
    (wrong_workdir_bundle.parent / "validation.json").write_text('{"ok": true}\n', encoding="utf-8")
    (failed_bundle.parent / "validation.json").write_text('{"ok": false, "error": "semantic lint failed"}\n', encoding="utf-8")

    context = service.get_alignment_workdir_context(sample_workdir)
    local_options = [option for option in context["options"] if option.get("source_type") == "alignment_session_file"]

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
    weaken_ready_bundle_markdown(Path(session["bundle_path"]))
    wrong_workdir_session = _confirm_alignment_agreement(
        service,
        service.create_alignment_session(workdir=sample_workdir, message="Create another reusable READY Loop.")["id"],
    )
    wrong_workdir_bundle_path = Path(wrong_workdir_session["bundle_path"])
    rewrite_bundle_workdir(wrong_workdir_bundle_path, sample_workdir.parent / "other-workdir")

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

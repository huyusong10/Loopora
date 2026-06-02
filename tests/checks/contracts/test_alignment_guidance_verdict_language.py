from __future__ import annotations

from loopora.alignment_guidance import alignment_guidance_dir


def test_alignment_prompt_assets_separate_run_status_from_task_verdict() -> None:
    asset_dir = alignment_guidance_dir()
    playbook = (asset_dir / "alignment-playbook.md").read_text(encoding="utf-8")
    primer = (asset_dir / "product-primer.md").read_text(encoding="utf-8")

    main_workflow = "`compose Loop -> run Loop -> automatic iteration with evidence -> run status, task verdict, and result`"
    assert main_workflow in playbook
    assert main_workflow in primer
    assert "`Loop -> run -> automatic iteration -> evidence -> run status + task verdict + result`" in primer
    assert "The task verdict projection should be easy to map into stable buckets" in primer

    for path in sorted(asset_dir.glob("*.md")):
        source = path.read_text(encoding="utf-8")
        assert "evidence verdict and result" not in source, path.name
        assert "The evidence verdict should" not in source, path.name

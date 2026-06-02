from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _loopora_source(module_name: str) -> str:
    return (REPO_ROOT / "src" / "loopora" / module_name).read_text(encoding="utf-8")


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

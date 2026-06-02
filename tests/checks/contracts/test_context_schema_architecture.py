from __future__ import annotations

from pathlib import Path

from loopora import context_schema_evidence
from loopora import context_schema_shared
from loopora import context_schemas


def test_context_evidence_schemas_have_dedicated_boundary() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    evidence_source = (repo_root / "src" / "loopora" / "context_schema_evidence.py").read_text(encoding="utf-8")
    shared_source = (repo_root / "src" / "loopora" / "context_schema_shared.py").read_text(encoding="utf-8")
    step_source = (repo_root / "src" / "loopora" / "context_schema_step_instruction.py").read_text(encoding="utf-8")
    iteration_source = (repo_root / "src" / "loopora" / "context_schema_iteration_state.py").read_text(encoding="utf-8")
    schemas_source = (repo_root / "src" / "loopora" / "context_schemas.py").read_text(encoding="utf-8")
    contracts_source = (repo_root / "design" / "contracts.md").read_text(encoding="utf-8")

    for marker in (
        "ARTIFACT_REF_SCHEMA = {",
        "EVIDENCE_ITEM_SCHEMA = {",
        "EVIDENCE_MANIFEST_CLAIM_SCHEMA = {",
    ):
        assert marker in evidence_source
        assert marker not in shared_source
    assert "from loopora.context_schema_evidence import" in shared_source
    assert "from loopora.context_schema_evidence import" in step_source
    assert "from loopora.context_schema_evidence import" in iteration_source
    assert "from loopora.context_schema_evidence import" in schemas_source
    assert context_schema_shared.EVIDENCE_ITEM_SCHEMA is context_schema_evidence.EVIDENCE_ITEM_SCHEMA
    assert context_schemas.EVIDENCE_MANIFEST_CLAIM_SCHEMA is context_schema_evidence.EVIDENCE_MANIFEST_CLAIM_SCHEMA
    assert "context_schema_evidence.py" in contracts_source

from pathlib import Path

from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_validation import (
    AlignmentBundleTextValidationContext,
    alignment_validated_bundle_text_loader,
)


def test_alignment_validated_bundle_text_loader_uses_session_candidate_yaml_lookup(tmp_path: Path) -> None:
    candidate_checks: list[str] = []

    def has_agent_candidate_yaml(session_id: str) -> bool:
        candidate_checks.append(session_id)
        return False

    loader = alignment_validated_bundle_text_loader(
        AlignmentBundleTextValidationContext(has_agent_candidate_yaml=has_agent_candidate_yaml)
    )
    semantic_issues: list[str] = []
    workdir = str(tmp_path.resolve())

    bundle, normalized_yaml = loader(
        {
            "id": "align_validate",
            "workdir": workdir,
            "working_agreement": {},
            "transcript": [{"role": "user", "content": "Build the focused starter experience."}],
        },
        alignment_bundle_yaml(workdir),
        semantic_issues,
    )

    assert candidate_checks == ["align_validate"]
    assert semantic_issues == []
    assert bundle["loop"]["workdir"] == workdir
    assert "Aligned Starter Bundle" in normalized_yaml

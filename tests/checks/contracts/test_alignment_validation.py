from pathlib import Path

import pytest

from loopora.bundles import bundle_to_yaml, load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_validation import (
    AlignmentBundleTextValidationContext,
    alignment_validated_bundle_text_loader,
)
from loopora.service_types import LooporaError


def test_alignment_validated_bundle_text_loader_accepts_generic_task_without_domain_anchor(tmp_path: Path) -> None:
    loader = alignment_validated_bundle_text_loader(AlignmentBundleTextValidationContext())
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

    assert semantic_issues == []
    assert bundle["loop"]["workdir"] == workdir
    assert "Aligned Starter Bundle" in normalized_yaml


def test_alignment_validated_bundle_text_loader_rejects_web_bundle_that_drops_task_anchor(tmp_path: Path) -> None:
    loader = alignment_validated_bundle_text_loader(AlignmentBundleTextValidationContext())
    semantic_issues: list[str] = []
    workdir = str(tmp_path.resolve())

    with pytest.raises(LooporaError, match="host Agent task context"):
        loader(
            {
                "id": "align_stripe",
                "workdir": workdir,
                "working_agreement": {},
                "transcript": [
                    {
                        "role": "user",
                        "content": "Build Stripe webhook ledger reconciliation with replay and signature proof.",
                    }
                ],
            },
            alignment_bundle_yaml(workdir),
            semantic_issues,
        )


def test_alignment_validated_bundle_text_loader_rejects_incomplete_local_governance_projection(
    tmp_path: Path,
) -> None:
    loader = alignment_validated_bundle_text_loader(AlignmentBundleTextValidationContext())
    semantic_issues: list[str] = []
    workdir = str(tmp_path.resolve())
    bundle = load_bundle_text(alignment_bundle_yaml(workdir))
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n\nBuilder reads design/README.md, design/, and tests/ before changing work."
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\n\nInspector verifies design/README.md, design/, and tests/ obligations before accepting evidence."
    )

    with pytest.raises(LooporaError, match="bundle control summary missing traceability: local_governance"):
        loader(
            {
                "id": "align_local_governance",
                "workdir": workdir,
                "working_agreement": {},
                "transcript": [{"role": "user", "content": "Build the focused starter experience."}],
            },
            bundle_to_yaml(bundle),
            semantic_issues,
        )

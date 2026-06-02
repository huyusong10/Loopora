from __future__ import annotations

from pathlib import Path

import pytest

from bundle_lifecycle_test_support import _bundle_yaml
from loopora.service import LooporaError


def test_bundle_preview_rejects_spec_markdown_that_cannot_compile(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    invalid_yaml = _bundle_yaml(sample_workdir).replace("## Builder Notes", "Builder notes without a subheading")

    with pytest.raises(LooporaError, match="Role Notes"):
        service.preview_bundle_text(invalid_yaml)


def test_bundle_preview_rejects_task_contract_list_sections_without_bullets(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    invalid_yaml = _bundle_yaml(sample_workdir).replace(
        "- The implementation stays maintainable for the next round.",
        "The implementation stays maintainable for the next round.",
    )

    with pytest.raises(LooporaError, match="Success Surface"):
        service.preview_bundle_text(invalid_yaml)

from __future__ import annotations

from pathlib import Path

import pytest

from bundle_lifecycle_test_support import _bundle_yaml
from loopora.service import LooporaError


@pytest.mark.parametrize(
    ("metadata_line", "message"),
    [
        ('  bundle_id: "../outside"', r"bundle metadata\.bundle_id must use letters, numbers, dot, underscore, or dash"),
        ("  bundle_id: false", r"bundle metadata\.bundle_id must be a string"),
        ('  source_bundle_id: "../source"', r"bundle metadata\.source_bundle_id must use letters, numbers, dot, underscore, or dash"),
        ("  source_bundle_id: false", r"bundle metadata\.source_bundle_id must be a string"),
    ],
)
def test_bundle_preview_rejects_unsafe_metadata_identifiers(
    service_factory,
    sample_workdir: Path,
    metadata_line: str,
    message: str,
) -> None:
    service = service_factory(scenario="success")
    yaml_text = _bundle_yaml(sample_workdir).replace(
        '  description: "Bundle created from task-scoped alignment."',
        f'  description: "Bundle created from task-scoped alignment."\n{metadata_line}',
        1,
    )

    with pytest.raises(LooporaError, match=message):
        service.preview_bundle_text(yaml_text)


def test_bundle_import_rejects_unsafe_replace_bundle_id(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")

    with pytest.raises(LooporaError, match=r"bundle replace_bundle_id must use letters, numbers, dot, underscore, or dash"):
        service.import_bundle_text(_bundle_yaml(sample_workdir), replace_bundle_id="../escape")

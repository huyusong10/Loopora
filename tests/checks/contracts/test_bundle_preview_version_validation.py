from __future__ import annotations

from pathlib import Path

import pytest

from bundle_lifecycle_test_support import _bundle_yaml
from loopora.service import LooporaError


@pytest.mark.parametrize(
    ("yaml_edit", "message"),
    [
        (lambda text: text.replace("version: 1", "version: 0", 1), "unsupported bundle version: 0"),
        (lambda text: text.replace("version: 1", "version: 2", 1), "unsupported bundle version: 2"),
        (lambda text: text.replace("version: 1", "version: 1.0", 1), "bundle version must be an integer"),
        (lambda text: text.replace("version: 1", "version: false", 1), "bundle version must be an integer"),
        (lambda text: text.replace("version: 1", "version: not-a-number", 1), "bundle version must be an integer"),
        (
            lambda text: text.replace(
                '  description: "Bundle created from task-scoped alignment."',
                '  description: "Bundle created from task-scoped alignment."\n  revision: 0',
                1,
            ),
            r"bundle metadata\.revision must be >= 1",
        ),
        (
            lambda text: text.replace(
                '  description: "Bundle created from task-scoped alignment."',
                '  description: "Bundle created from task-scoped alignment."\n  revision: 1.0',
                1,
            ),
            r"bundle metadata\.revision must be an integer",
        ),
        (
            lambda text: text.replace(
                '  description: "Bundle created from task-scoped alignment."',
                '  description: "Bundle created from task-scoped alignment."\n  revision: false',
                1,
            ),
            r"bundle metadata\.revision must be an integer",
        ),
        (
            lambda text: text.replace(
                '  description: "Bundle created from task-scoped alignment."',
                '  description: "Bundle created from task-scoped alignment."\n  revision: not-a-number',
                1,
            ),
            r"bundle metadata\.revision must be an integer",
        ),
        (
            lambda text: text.replace(
                '  description: "Bundle created from task-scoped alignment."',
                '  description: "Bundle created from task-scoped alignment."\n  revision:',
                1,
            ),
            r"bundle metadata\.revision must be an integer",
        ),
        (
            lambda text: text.replace(
                '  description: "Bundle created from task-scoped alignment."',
                '  description: "Bundle created from task-scoped alignment."\n  revision: ""',
                1,
            ),
            r"bundle metadata\.revision must be an integer",
        ),
        (
            lambda text: text.replace("workflow:\n  version: 1", "workflow:\n  version: 0", 1),
            "unsupported bundle workflow version: 0",
        ),
        (
            lambda text: text.replace("workflow:\n  version: 1", "workflow:\n  version: 1.0", 1),
            "bundle workflow version must be an integer",
        ),
        (
            lambda text: text.replace("workflow:\n  version: 1", "workflow:\n  version: false", 1),
            "bundle workflow version must be an integer",
        ),
    ],
)
def test_bundle_preview_rejects_invalid_explicit_versions(
    service_factory,
    sample_workdir: Path,
    yaml_edit,
    message: str,
) -> None:
    service = service_factory(scenario="success")

    with pytest.raises(LooporaError, match=message):
        service.preview_bundle_text(yaml_edit(_bundle_yaml(sample_workdir)))


@pytest.mark.parametrize(
    "yaml_edit",
    [
        lambda text: text.replace("version: 1\n", "", 1),
        lambda text: text.replace("version: 1", 'version: ""', 1),
    ],
)
def test_bundle_preview_defaults_missing_or_empty_top_level_version(
    service_factory,
    sample_workdir: Path,
    yaml_edit,
) -> None:
    service = service_factory(scenario="success")

    preview = service.preview_bundle_text(yaml_edit(_bundle_yaml(sample_workdir)))

    assert preview["bundle"]["version"] == 1

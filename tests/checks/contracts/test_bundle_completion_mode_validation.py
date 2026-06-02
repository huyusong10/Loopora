from __future__ import annotations

from pathlib import Path

import pytest

from bundle_lifecycle_test_support import _bundle_yaml
from loopora.bundles import load_bundle_text
from loopora.service import LooporaError


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ('  completion_mode: "unknown"', "unsupported completion mode: unknown"),
        ("  completion_mode: false", "unsupported completion mode: False"),
        ("  completion_mode: 1", "unsupported completion mode: 1"),
    ],
)
def test_bundle_preview_rejects_invalid_completion_mode(
    service_factory,
    sample_workdir: Path,
    replacement: str,
    message: str,
) -> None:
    service = service_factory(scenario="success")
    invalid_yaml = _bundle_yaml(sample_workdir).replace('  completion_mode: "gatekeeper"', replacement, 1)

    with pytest.raises(LooporaError, match=message):
        service.preview_bundle_text(invalid_yaml)


def test_bundle_loader_normalizes_supported_completion_mode(sample_workdir: Path) -> None:
    bundle = load_bundle_text(
        _bundle_yaml(sample_workdir).replace('  completion_mode: "gatekeeper"', '  completion_mode: " RoundS "', 1)
    )

    assert bundle["loop"]["completion_mode"] == "rounds"

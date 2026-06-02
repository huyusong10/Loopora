from __future__ import annotations

from pathlib import Path

import pytest

from bundle_lifecycle_test_support import _bundle_yaml
from loopora.service import LooporaError


LOSSLESS_REGRESSION_WINDOW = 2
LOSSLESS_TRIGGER_WINDOW = 2
LOSSLESS_MAX_ITERS = 4
LOSSLESS_MAX_ROLE_RETRIES = 1


@pytest.mark.parametrize(
    ("yaml_line", "error_text"),
    [
        ('  delta_threshold: "inf"', "bundle loop settings must use finite numbers"),
        ("  delta_threshold: -0.1", "bundle loop.delta_threshold must be >= 0"),
    ],
)
def test_bundle_import_rejects_invalid_loop_runtime_numbers(
    service_factory,
    sample_workdir: Path,
    yaml_line: str,
    error_text: str,
) -> None:
    service = service_factory(scenario="success")
    yaml_text = _bundle_yaml(sample_workdir).replace("  delta_threshold: 0.005", yaml_line)

    with pytest.raises(LooporaError, match=error_text):
        service.import_bundle_text(yaml_text)


@pytest.mark.parametrize(
    ("yaml_line", "error_text"),
    [
        ("  max_iters: 4.5", "bundle loop.max_iters must be an integer"),
        ("  max_role_retries: 1.5", "bundle loop.max_role_retries must be an integer"),
        ("  trigger_window: 2.5", "bundle loop.trigger_window must be an integer"),
        ("  regression_window: 2.5", "bundle loop.regression_window must be an integer"),
    ],
)
def test_bundle_import_rejects_fractional_integer_runtime_numbers(
    service_factory,
    sample_workdir: Path,
    yaml_line: str,
    error_text: str,
) -> None:
    service = service_factory(scenario="success")
    original_key = yaml_line.split(":", 1)[0].strip()
    original_line = {
        "max_iters": "  max_iters: 4",
        "max_role_retries": "  max_role_retries: 1",
        "trigger_window": "  trigger_window: 2",
        "regression_window": "  regression_window: 2",
    }[original_key]
    yaml_text = _bundle_yaml(sample_workdir).replace(original_line, yaml_line)

    with pytest.raises(LooporaError, match=error_text):
        service.import_bundle_text(yaml_text)


def test_bundle_import_preserves_zero_loop_runtime_numbers(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    yaml_text = (
        _bundle_yaml(sample_workdir)
        .replace("  max_iters: 4", "  max_iters: 0")
        .replace("  max_role_retries: 1", "  max_role_retries: 0")
        .replace("  delta_threshold: 0.005", "  delta_threshold: 0")
    )

    imported = service.import_bundle_text(yaml_text)

    assert imported["loop"]["max_iters"] == 0
    assert imported["loop"]["max_role_retries"] == 0
    assert imported["loop"]["delta_threshold"] == 0.0
    exported = service.export_bundle(imported["id"])
    assert exported["loop"]["max_iters"] == 0
    assert exported["loop"]["max_role_retries"] == 0
    assert exported["loop"]["delta_threshold"] == 0.0


def test_bundle_import_accepts_lossless_float_encoded_integer_runtime_numbers(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    yaml_text = (
        _bundle_yaml(sample_workdir)
        .replace("  max_iters: 4", "  max_iters: 4.0")
        .replace("  max_role_retries: 1", "  max_role_retries: 1.0")
        .replace("  trigger_window: 2", "  trigger_window: 2.0")
        .replace("  regression_window: 2", "  regression_window: 2.0")
    )

    imported = service.import_bundle_text(yaml_text)

    assert imported["loop"]["max_iters"] == LOSSLESS_MAX_ITERS
    assert imported["loop"]["max_role_retries"] == LOSSLESS_MAX_ROLE_RETRIES
    assert imported["loop"]["trigger_window"] == LOSSLESS_TRIGGER_WINDOW
    assert imported["loop"]["regression_window"] == LOSSLESS_REGRESSION_WINDOW

from __future__ import annotations

from pathlib import Path

import pytest

from bundle_lifecycle_test_support import _bundle_yaml
from loopora.service import LooporaError


def test_bundle_round_trip_preserves_workflow_controls(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    yaml_text = _bundle_yaml(sample_workdir).replace(
        '      on_pass: "finish_run"\n',
        '      on_pass: "finish_run"\n'
        "  controls:\n"
        '    - id: "gatekeeper_rejection_review"\n'
        "      when:\n"
        '        signal: "gatekeeper_rejected"\n'
        '        after: "0s"\n'
        "      call:\n"
        '        role_id: "inspector"\n'
        '      mode: "advisory"\n'
        "      max_fires_per_run: 1\n",
    )

    imported = service.import_bundle_text(yaml_text)
    exported = service.export_bundle(imported["id"])

    assert exported["workflow"]["controls"] == [
        {
            "id": "gatekeeper_rejection_review",
            "when": {"signal": "gatekeeper_rejected", "after": "0s"},
            "call": {"role_id": "inspector"},
            "mode": "advisory",
            "max_fires_per_run": 1,
        }
    ]


def test_bundle_rejects_controls_that_call_builders(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    yaml_text = _bundle_yaml(sample_workdir).replace(
        '      on_pass: "finish_run"\n',
        '      on_pass: "finish_run"\n'
        "  controls:\n"
        '    - id: "implicit_repair"\n'
        "      when:\n"
        '        signal: "step_failed"\n'
        '        after: "0s"\n'
        "      call:\n"
        '        role_id: "builder"\n',
    )

    with pytest.raises(LooporaError, match="controls may only call Inspector, Guide, or GateKeeper"):
        service.preview_bundle_text(yaml_text)


def test_bundle_rejects_zero_workflow_control_max_fires(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    yaml_text = _bundle_yaml(sample_workdir).replace(
        '      on_pass: "finish_run"\n',
        '      on_pass: "finish_run"\n'
        "  controls:\n"
        '    - id: "disabled_review"\n'
        "      when:\n"
        '        signal: "gatekeeper_rejected"\n'
        '        after: "0s"\n'
        "      call:\n"
        '        role_id: "inspector"\n'
        '      mode: "advisory"\n'
        "      max_fires_per_run: 0\n",
    )

    with pytest.raises(LooporaError, match="control max_fires_per_run must be between 1 and 20"):
        service.preview_bundle_text(yaml_text)


def test_bundle_rejects_string_workflow_control_max_fires(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    yaml_text = _bundle_yaml(sample_workdir).replace(
        '      on_pass: "finish_run"\n',
        '      on_pass: "finish_run"\n'
        "  controls:\n"
        '    - id: "quoted_review"\n'
        "      when:\n"
        '        signal: "gatekeeper_rejected"\n'
        '        after: "0s"\n'
        "      call:\n"
        '        role_id: "inspector"\n'
        '      mode: "advisory"\n'
        '      max_fires_per_run: "2"\n',
    )

    with pytest.raises(LooporaError, match="control max_fires_per_run must be an integer"):
        service.preview_bundle_text(yaml_text)

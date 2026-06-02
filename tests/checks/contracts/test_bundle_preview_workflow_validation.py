from __future__ import annotations

from pathlib import Path

import pytest

from bundle_lifecycle_test_support import _bundle_yaml
from loopora.service import LooporaError


@pytest.mark.parametrize(
    ("yaml_edit", "message"),
    [
        (lambda text: text.replace('id: "inspector"', 'id: "inspect/or"', 1), "bundle workflow role id"),
        (lambda text: text.replace('id: "builder_step"', 'id: "../builder_step"', 1), "bundle workflow step id"),
        (
            lambda text: text.replace(
                'role_id: "inspector"\n    - id: "builder_step"',
                'role_id: "inspector"\n      parallel_group: "review/pack"\n    - id: "builder_step"',
                1,
            ),
            "workflow step parallel_group",
        ),
        (
            lambda text: text.replace(
                '      on_pass: "finish_run"\n',
                '      on_pass: "finish_run"\n'
                "  controls:\n"
                '    - id: "control/escape"\n'
                "      when:\n"
                '        signal: "gatekeeper_rejected"\n'
                "      call:\n"
                '        role_id: "inspector"\n',
            ),
            "workflow control id",
        ),
    ],
)
def test_bundle_preview_rejects_unsafe_workflow_identifiers(
    service_factory,
    sample_workdir: Path,
    yaml_edit,
    message: str,
) -> None:
    service = service_factory(scenario="success")
    invalid_yaml = yaml_edit(_bundle_yaml(sample_workdir))

    with pytest.raises(LooporaError, match=message):
        service.preview_bundle_text(invalid_yaml)


def test_bundle_preview_rejects_non_string_workflow_input_list_items(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    invalid_yaml = _bundle_yaml(sample_workdir).replace(
        '    - id: "gatekeeper_step"\n'
        '      role_id: "gatekeeper"\n'
        '      on_pass: "finish_run"',
        '    - id: "gatekeeper_step"\n'
        '      role_id: "gatekeeper"\n'
        '      on_pass: "finish_run"\n'
        "      inputs:\n"
        "        handoffs_from:\n"
        "          - 123",
    )

    with pytest.raises(LooporaError, match=r"workflow step inputs\.handoffs_from must contain only strings"):
        service.preview_bundle_text(invalid_yaml)


def test_bundle_preview_rejects_gatekeeper_mode_without_finishing_gatekeeper_step(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    invalid_yaml = _bundle_yaml(sample_workdir).replace('on_pass: "finish_run"', 'on_pass: "continue"')

    with pytest.raises(LooporaError, match="GateKeeper step"):
        service.preview_bundle_text(invalid_yaml)

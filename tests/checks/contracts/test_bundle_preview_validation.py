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


@pytest.mark.parametrize(
    ("metadata_line", "message"),
    (
        ('  bundle_id: "../outside"', r"bundle metadata\.bundle_id must use letters, numbers, dot, underscore, or dash"),
        ("  bundle_id: false", r"bundle metadata\.bundle_id must be a string"),
        ('  source_bundle_id: "../source"', r"bundle metadata\.source_bundle_id must use letters, numbers, dot, underscore, or dash"),
        ("  source_bundle_id: false", r"bundle metadata\.source_bundle_id must be a string"),
    ),
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

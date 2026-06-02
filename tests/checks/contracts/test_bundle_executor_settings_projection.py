from __future__ import annotations

from pathlib import Path

import pytest

from bundle_lifecycle_test_support import _bundle_yaml
from loopora.bundles import load_bundle_text
from loopora.service import LooporaError


@pytest.mark.parametrize(
    ("yaml_edit", "message"),
    [
        (
            lambda text: text.replace('  executor_kind: "codex"', '  executor_kind: "unknown"', 1),
            "unsupported executor kind",
        ),
        (
            lambda text: text.replace('  executor_mode: "preset"', '  executor_mode: "unknown"', 1),
            "unsupported executor mode",
        ),
        (
            lambda text: text.replace('  executor_kind: "codex"', '  executor_kind: "custom"', 1),
            "Custom Command only supports command mode",
        ),
        (
            lambda text: text.replace('  executor_mode: "preset"', '  executor_mode: "command"', 1),
            "custom command arguments are required in command mode",
        ),
    ],
)
def test_bundle_preview_rejects_invalid_loop_executor_settings(
    service_factory,
    sample_workdir: Path,
    yaml_edit,
    message: str,
) -> None:
    service = service_factory(scenario="success")

    with pytest.raises(LooporaError, match=message):
        service.preview_bundle_text(yaml_edit(_bundle_yaml(sample_workdir)))


def test_bundle_loader_normalizes_loop_executor_aliases(sample_workdir: Path) -> None:
    bundle = load_bundle_text(
        _bundle_yaml(sample_workdir)
        .replace('  executor_kind: "codex"', '  executor_kind: "claude-code"', 1)
        .replace('  executor_mode: "preset"', '  executor_mode: " PRESET "', 1)
        .replace('  model: "gpt-5.4"', '  model: ""', 1)
        .replace('  reasoning_effort: "medium"', '  reasoning_effort: "xhigh"', 1)
    )

    assert bundle["loop"]["executor_kind"] == "claude"
    assert bundle["loop"]["executor_mode"] == "preset"
    assert bundle["loop"]["command_cli"] == ""
    assert bundle["loop"]["command_args_text"] == ""
    assert bundle["loop"]["model"] == ""
    assert bundle["loop"]["reasoning_effort"] == "max"


def test_bundle_roles_inherit_loop_executor_when_role_fields_are_omitted(sample_workdir: Path) -> None:
    bundle = load_bundle_text(
        _bundle_yaml(sample_workdir)
        .replace('  executor_kind: "codex"', '  executor_kind: "claude-code"', 1)
        .replace('  model: "gpt-5.4"', '  model: ""', 1)
        .replace('  reasoning_effort: "medium"', '  reasoning_effort: "xhigh"', 1)
    )

    assert {role["executor_kind"] for role in bundle["role_definitions"]} == {"claude"}
    assert {role["executor_mode"] for role in bundle["role_definitions"]} == {"preset"}
    assert {role["model"] for role in bundle["role_definitions"]} == {""}
    assert {role["reasoning_effort"] for role in bundle["role_definitions"]} == {"max"}


def test_bundle_roles_inherit_loop_command_executor_when_role_fields_are_omitted(sample_workdir: Path) -> None:
    bundle = load_bundle_text(
        _bundle_yaml(sample_workdir)
        .replace('  executor_kind: "codex"', '  executor_kind: "custom"', 1)
        .replace(
            '  executor_mode: "preset"',
            '  executor_mode: "command"\n'
            '  command_cli: "my-agent"\n'
            "  command_args_text: |\n"
            "    {prompt}\n"
            "    --output\n"
            "    {output_path}",
            1,
        )
        .replace('  model: "gpt-5.4"', '  model: ""', 1)
        .replace('  reasoning_effort: "medium"', '  reasoning_effort: ""', 1)
    )

    assert {role["executor_kind"] for role in bundle["role_definitions"]} == {"custom"}
    assert {role["executor_mode"] for role in bundle["role_definitions"]} == {"command"}
    assert {role["command_cli"] for role in bundle["role_definitions"]} == {"my-agent"}
    assert {role["command_args_text"] for role in bundle["role_definitions"]} == {
        "{prompt}\n--output\n{output_path}\n"
    }

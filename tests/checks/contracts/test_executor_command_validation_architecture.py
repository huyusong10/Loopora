from __future__ import annotations

from executor_architecture_test_support import design_contracts_source, loopora_source


def test_executor_command_validation_has_dedicated_boundary() -> None:
    command_args_source = loopora_source("executor_command_args.py")
    validation_source = loopora_source("executor_command_validation.py")
    contracts_source = design_contracts_source()

    assert "from loopora.executor_command_validation import" in command_args_source
    for marker in ("def validate_command_args_text", "def parse_extra_cli_args_text"):
        assert marker in validation_source
        assert marker not in command_args_source
    assert "COMMAND_PLACEHOLDERS = frozenset" in validation_source
    assert "executor_command_validation.py" in contracts_source

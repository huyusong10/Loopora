from __future__ import annotations

from collections.abc import Mapping
import shlex

from loopora.agent_adapter_command_prefix import normalize_loopora_cli_entry, shell_join_loopora_command
from loopora.fit_review_catalog import (
    FIT_REVIEW_INPUT_FIELDS,
    _completion_placeholders,
    _direct_decision_completion_placeholders,
)


def _normalize_fit_review_text(value: object) -> str:
    return " ".join(str(value or "").split())


def _fit_review_completion_command(
    review_inputs: dict[str, str],
    *,
    language: str,
    cli_entry: str,
    workdir: str = "",
) -> str:
    option_by_id = {str(field["id"]): str(field["option"]) for field in FIT_REVIEW_INPUT_FIELDS}
    required_by_id = {str(field["id"]): bool(field.get("required_for_first_task", True)) for field in FIT_REVIEW_INPUT_FIELDS}
    placeholders = _completion_placeholders(language=language)
    parts = [*shlex.split(normalize_loopora_cli_entry(cli_entry)), "fit"]
    if workdir:
        parts.extend(("--workdir", workdir))
    if language != "en":
        parts.extend(("--language", language))
    for input_id, option in option_by_id.items():
        supplied_value = str(review_inputs.get(input_id) or "").strip()
        if not required_by_id[input_id] and not supplied_value:
            continue
        value = supplied_value or placeholders[input_id]
        parts.extend((f"--{option}", value))
    return shell_join_loopora_command(parts)


def _fit_direct_decision_completion_command(
    review_inputs: dict[str, str],
    *,
    language: str,
    cli_entry: str,
    workdir: str = "",
) -> str:
    placeholders = _direct_decision_completion_placeholders(language=language)
    parts = [*shlex.split(normalize_loopora_cli_entry(cli_entry)), "fit"]
    if workdir:
        parts.extend(("--workdir", workdir))
    if language != "en":
        parts.extend(("--language", language))
    parts.append("--prefer-direct")
    task_value = str(review_inputs.get("task") or "").strip()
    direct_path_value = str(review_inputs.get("direct_path_check") or "").strip()
    if task_value:
        parts.extend(("--task", task_value))
    if direct_path_value:
        parts.extend(("--direct-path", direct_path_value))
    if not direct_path_value:
        parts.extend(("--direct-path", placeholders["direct_path_check"]))
    return shell_join_loopora_command(parts)


def _fit_review_completion_action(
    review_inputs: Mapping[str, object],
    *,
    language: str,
    cli_entry: str,
    workdir: str = "",
) -> dict[str, object]:
    return {
        "kind": "complete_review_inputs",
        "command_template": _fit_review_completion_command(
            {str(key): str(value or "") for key, value in review_inputs.items()},
            language=language,
            cli_entry=cli_entry,
            workdir=workdir,
        ),
        "command_ready": False,
        "command_blockers": ["review_inputs_required"],
    }


def _fit_supplied_review_option_args(review_inputs: Mapping[str, object]) -> list[str]:
    parts: list[str] = []
    for field in FIT_REVIEW_INPUT_FIELDS:
        input_id = str(field["id"])
        value = _normalize_fit_review_text(review_inputs.get(input_id))
        if value:
            parts.extend([f"--{field['option']}", shlex.quote(value)])
    return parts

from __future__ import annotations

from copy import deepcopy

from loopora.asset_catalog_builtins import strategy_parallel_groups
from loopora.strategy_source import (
    StrategySourceError,
    normalize_strategy_prompt_ref,
    strategy_source_from_record,
    strategy_source_warnings,
)


def clone_asset_records(records: list[dict]) -> list[dict]:
    return [deepcopy(record) for record in records]


def decorate_orchestration_record(record: dict, *, source: str) -> dict:
    decorated = dict(record)
    decorated["prompt_files_json"] = sanitize_persisted_prompt_files(decorated.get("prompt_files_json"))
    decorated["source"] = source
    decorated["editable"] = source == "custom"
    decorated["deletable"] = source == "custom"
    strategy_source = strategy_source_from_record(decorated) or {}
    decorated["strategy_source"] = strategy_source
    decorated["workflow_warnings"] = strategy_source_warnings(strategy_source)
    decorated["parallel_groups"] = strategy_parallel_groups(strategy_source)
    decorated["parallel_group_count"] = len(decorated["parallel_groups"])
    return decorated


def decorate_role_definition_record(record: dict, *, source: str) -> dict:
    decorated = dict(record)
    decorated["source"] = source
    decorated["editable"] = source == "custom"
    decorated["deletable"] = source == "custom"
    return decorated


def sanitize_persisted_prompt_files(prompt_files: object) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for prompt_ref, markdown_text in dict(prompt_files or {}).items():
        candidate = str(prompt_ref).strip()
        if not candidate:
            continue
        try:
            normalized_prompt_ref = normalize_strategy_prompt_ref(candidate)
        except StrategySourceError:
            continue
        sanitized[normalized_prompt_ref] = str(markdown_text or "")
    return sanitized

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import shlex

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.strategy_source import DEFAULT_STRATEGY_SOURCE_PRESET, StrategySourceError, load_strategy_source_file, normalize_strategy_source


@dataclass(frozen=True)
class SpecInitStrategyContext:
    orchestration_id: object = ""
    strategy_preset: object = ""
    strategy_file: Path | str | None = None
    inline_strategy_source: bool = False


def effective_spec_init_strategy_context(
    *,
    orchestration_id: object = "",
    strategy_preset: object = "",
    strategy_file: Path | str | None = None,
    strategy_source: Mapping[str, object] | None = None,
) -> SpecInitStrategyContext:
    if strategy_file is not None:
        return SpecInitStrategyContext(strategy_file=strategy_file)
    if strategy_source is not None:
        preset = str(strategy_source.get("preset") or "").strip()
        has_inline_entries = bool(
            strategy_source.get("roles") or strategy_source.get("steps") or strategy_source.get("controls")
        )
        if preset and not has_inline_entries:
            return SpecInitStrategyContext(strategy_preset=preset)
        return SpecInitStrategyContext(inline_strategy_source=True)
    if str(orchestration_id or "").strip():
        return SpecInitStrategyContext(orchestration_id=orchestration_id)
    return SpecInitStrategyContext(strategy_preset=strategy_preset)


def spec_init_recovery_command(
    spec_path: Path | str,
    *,
    orchestration_id: object = "",
    strategy_preset: object = "",
    strategy_file: Path | str | None = None,
    strategy_context: SpecInitStrategyContext | None = None,
) -> str:
    context = strategy_context or SpecInitStrategyContext(
        orchestration_id=orchestration_id,
        strategy_preset=strategy_preset,
        strategy_file=strategy_file,
    )
    if spec_init_strategy_source_error(strategy_context=context):
        return ""
    parts = ["loopora", "spec", "init", shlex.quote(str(spec_path))]
    if context.strategy_file is not None:
        parts.extend(["--strategy-file", _quote_path(context.strategy_file)])
    elif context.inline_strategy_source:
        return ""
    elif str(context.orchestration_id or "").strip():
        parts.extend(["--orchestration-id", shlex.quote(str(context.orchestration_id).strip())])
    else:
        preset = str(context.strategy_preset or "").strip() or DEFAULT_STRATEGY_SOURCE_PRESET
        parts.extend(["--strategy-preset", shlex.quote(preset)])
    return copyable_loopora_command(" ".join(parts))


def spec_init_recovery_command_template(
    *,
    strategy_context: SpecInitStrategyContext | None = None,
) -> str:
    context = strategy_context or SpecInitStrategyContext()
    if spec_init_strategy_source_error(strategy_context=context):
        return ""
    parts = ["loopora", "spec", "init", "<spec-path>"]
    if context.strategy_file is not None:
        parts.extend(["--strategy-file", _quote_path(context.strategy_file)])
    elif context.inline_strategy_source:
        return ""
    elif str(context.orchestration_id or "").strip():
        parts.extend(["--orchestration-id", shlex.quote(str(context.orchestration_id).strip())])
    else:
        preset = str(context.strategy_preset or "").strip() or DEFAULT_STRATEGY_SOURCE_PRESET
        parts.extend(["--strategy-preset", shlex.quote(preset)])
    return copyable_loopora_command(" ".join(parts))


def _quote_path(path: Path | str) -> str:
    return shlex.quote(str(Path(path).expanduser().resolve(strict=False)))


def spec_init_strategy_source_error(*, strategy_context: SpecInitStrategyContext | None = None) -> str:
    context = strategy_context or SpecInitStrategyContext()
    if context.strategy_file is None:
        return ""
    try:
        strategy_source, _prompt_files = load_strategy_source_file(Path(context.strategy_file))
        normalize_strategy_source(strategy_source)
    except (StrategySourceError, OSError, ValueError) as exc:
        return str(exc)
    return ""

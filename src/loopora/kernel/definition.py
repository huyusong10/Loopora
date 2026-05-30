from __future__ import annotations

from dataclasses import dataclass, field

from loopora.kernel.contract import LoopContract
from loopora.kernel.strategy import LoopStrategy


@dataclass(frozen=True, slots=True)
class RuntimeDefaults:
    executor_kind: str = "codex"
    executor_mode: str = "preset"
    model: str = ""
    reasoning_effort: str = ""
    max_iterations: int = 1
    max_step_retries: int = 1
    completion_mode: str = "gatekeeper"


@dataclass(frozen=True, slots=True)
class LoopMetadata:
    workdir: str = ""
    spec_path: str = ""
    source_kind: str = ""
    source_id: str = ""
    labels: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class LoopDefinition:
    id: str
    name: str
    contract: LoopContract
    strategy: LoopStrategy
    runtime_defaults: RuntimeDefaults = field(default_factory=RuntimeDefaults)
    metadata: LoopMetadata = field(default_factory=LoopMetadata)

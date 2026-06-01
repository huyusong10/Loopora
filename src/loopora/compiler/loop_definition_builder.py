from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from loopora.compiler._coercion import integer, text
from loopora.compiler.contract_compiler import compile_loop_contract, compile_residual_risk_policy
from loopora.compiler.strategy_compiler import compile_loop_strategy
from loopora.kernel.definition import LoopDefinition, LoopMetadata, RuntimeDefaults


@dataclass(frozen=True, kw_only=True)
class LoopDefinitionParts:
    loop_id: str
    name: str
    compiled_spec: Mapping[str, object]
    strategy_source: Mapping[str, object]
    runtime_defaults: RuntimeDefaults
    metadata: LoopMetadata


def runtime_defaults_from_payload(payload: Mapping[str, object]) -> RuntimeDefaults:
    return RuntimeDefaults(
        executor_kind=text(payload.get("executor_kind"), fallback="codex"),
        executor_mode=text(payload.get("executor_mode"), fallback="preset"),
        model=text(payload.get("model")),
        reasoning_effort=text(payload.get("reasoning_effort")),
        max_iterations=integer(payload.get("max_iters"), fallback=1),
        max_step_retries=integer(payload.get("max_role_retries"), fallback=1),
        completion_mode=text(payload.get("completion_mode"), fallback="gatekeeper"),
    )


def compile_loop_definition(parts: LoopDefinitionParts) -> LoopDefinition:
    residual_risk_policy = compile_residual_risk_policy(parts.compiled_spec.get("residual_risk"))
    return LoopDefinition(
        id=parts.loop_id,
        name=parts.name,
        contract=compile_loop_contract(
            parts.loop_id,
            parts.compiled_spec,
            completion_mode=parts.runtime_defaults.completion_mode,
        ),
        strategy=compile_loop_strategy(
            parts.loop_id,
            parts.strategy_source,
            max_iterations=parts.runtime_defaults.max_iterations,
            max_step_retries=parts.runtime_defaults.max_step_retries,
            residual_risk_policy=residual_risk_policy,
        ),
        runtime_defaults=parts.runtime_defaults,
        metadata=parts.metadata,
    )

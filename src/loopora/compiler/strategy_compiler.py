from __future__ import annotations

from collections.abc import Mapping

from loopora.compiler._coercion import integer, mapping, mapping_list, strings, text
from loopora.kernel.contract import ResidualRiskPolicy
from loopora.kernel.strategy import EvidenceFlow, FinishPolicy, IterationPolicy, LoopStrategy, RoleSpec, StrategyStep


def compile_loop_strategy(
    loop_id: str,
    strategy_source: Mapping[str, object],
    *,
    max_iterations: int = 1,
    max_step_retries: int = 1,
    residual_risk_policy: ResidualRiskPolicy = ResidualRiskPolicy.ALLOW_MANAGED,
) -> LoopStrategy:
    roles = tuple(_compile_role(role, index) for index, role in enumerate(mapping_list(strategy_source.get("roles")), start=1))
    steps = tuple(_compile_step(step, index) for index, step in enumerate(mapping_list(strategy_source.get("steps")), start=1))
    role_ids = {role.id for role in roles}
    if not roles:
        roles = (
            RoleSpec(
                id="builder",
                name="Builder",
                archetype="builder",
                responsibility="Build the next evidence-bearing change.",
            ),
            RoleSpec(
                id="gatekeeper",
                name="GateKeeper",
                archetype="gatekeeper",
                responsibility="Judge whether evidence supports closure.",
            ),
        )
        role_ids = {role.id for role in roles}
    if not steps:
        steps = (
            StrategyStep(id="builder", role_id="builder", objective="Produce required evidence."),
            StrategyStep(id="gatekeeper", role_id="gatekeeper", objective="Judge closure.", can_finish_run=True),
        )
    known_steps = tuple(step for step in steps if step.role_id in role_ids)
    return LoopStrategy(
        id=f"{loop_id}:strategy",
        roles=roles,
        steps=known_steps or steps,
        evidence_flow=EvidenceFlow(
            required_target_ids=tuple(target for target in strings(strategy_source.get("required_target_ids")) if target),
            gatekeeper_step_id=next((step.id for step in steps if step.can_finish_run), ""),
        ),
        iteration_policy=IterationPolicy(
            max_iterations=integer(max_iterations, fallback=1),
            max_step_retries=integer(max_step_retries, fallback=1),
        ),
        finish_policy=FinishPolicy(
            require_verdict_pass=True,
            allow_residual_risk=residual_risk_policy != ResidualRiskPolicy.DISALLOW,
        ),
    )


def _compile_role(role: Mapping[str, object], index: int) -> RoleSpec:
    role_id = text(role.get("id"), fallback=f"role_{index:03d}")
    return RoleSpec(
        id=role_id,
        name=text(role.get("name"), fallback=role_id),
        archetype=text(role.get("archetype")),
        responsibility=text(role.get("responsibility") or role.get("description") or role.get("posture")),
    )


def _compile_step(step: Mapping[str, object], index: int) -> StrategyStep:
    action_policy = mapping(step.get("action_policy"))
    return StrategyStep(
        id=text(step.get("id"), fallback=f"step_{index:03d}"),
        role_id=text(step.get("role_id") or step.get("role"), fallback="builder"),
        objective=text(step.get("objective") or step.get("description") or step.get("prompt")),
        can_finish_run=bool(action_policy.get("can_finish_run") or step.get("can_finish_run")),
        parallel_group=text(step.get("parallel_group")),
    )

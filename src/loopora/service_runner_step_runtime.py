from __future__ import annotations

from pathlib import Path

from loopora.executor_types import RoleRequest
from loopora.headless_prompt import HeadlessPromptRequest, build_headless_prompt
from loopora.runner_step_instruction_contexts import prepare_runner_step_instruction_context
from loopora.runner_step_runtime_requests import RunnerStepRuntimeRequest
from loopora.service_role_execution import RoleExecutionRequest
from loopora.service_types import LooporaError
from loopora.step_instruction_context import STEP_INSTRUCTION_CONTEXT_KEY
from loopora.strategy_source import (
    StrategySourceError,
    validate_strategy_prompt_markdown,
)

from loopora.executor_command_args import coerce_reasoning_effort, normalize_reasoning_effort, validate_command_args_text

from loopora.providers import executor_profile, normalize_executor_kind, normalize_executor_mode


from loopora.strategy_source import strategy_role_uses_execution_snapshot

def resolve_runner_role_execution_settings(run: dict, step: dict, role: dict) -> dict[str, object]:
    step_model = str(step.get("model") or "").strip()
    step_inherit_session = bool(step.get("inherit_session"))
    step_extra_cli_args = str(step.get("extra_cli_args") or "").strip()
    role_model = str(role.get("model") or "").strip()

    if strategy_role_uses_execution_snapshot(role):
        executor_kind = normalize_executor_kind(role.get("executor_kind", "codex"))
        executor_mode = normalize_executor_mode(role.get("executor_mode", "preset"))
        profile = executor_profile(executor_kind)
        reasoning_effort = str(role.get("reasoning_effort") or "").strip()
        if profile.command_only and executor_mode != "command":
            raise LooporaError(f"{profile.label} only supports command mode")
        if executor_mode == "preset":
            return {
                "executor_kind": executor_kind,
                "executor_mode": executor_mode,
                "command_cli": "",
                "command_args_text": "",
                "model": step_model or role_model or profile.default_model,
                "reasoning_effort": normalize_reasoning_effort(reasoning_effort, executor_kind),
                "step_model": step_model,
                "inherit_session": step_inherit_session,
                "extra_cli_args_text": step_extra_cli_args,
            }
        command_args_text = str(role.get("command_args_text") or "")
        validate_command_args_text(command_args_text, executor_kind=executor_kind)
        return {
            "executor_kind": executor_kind,
            "executor_mode": executor_mode,
            "command_cli": str(role.get("command_cli") or "").strip() or profile.cli_name,
            "command_args_text": command_args_text,
            "model": step_model or role_model,
            "reasoning_effort": reasoning_effort,
            "step_model": step_model,
            "inherit_session": step_inherit_session,
            "extra_cli_args_text": step_extra_cli_args,
        }

    executor_kind = normalize_executor_kind(run.get("executor_kind", "codex"))
    executor_mode = normalize_executor_mode(run.get("executor_mode", "preset"))
    profile = executor_profile(executor_kind)
    if profile.command_only and executor_mode != "command":
        raise LooporaError(f"{profile.label} only supports command mode")
    if executor_mode == "preset":
        return {
            "executor_kind": executor_kind,
            "executor_mode": executor_mode,
            "command_cli": "",
            "command_args_text": "",
            "model": step_model or role_model or str(run.get("model") or "") or profile.default_model,
            "reasoning_effort": coerce_reasoning_effort(run.get("reasoning_effort", ""), executor_kind),
            "step_model": step_model,
            "inherit_session": step_inherit_session,
            "extra_cli_args_text": step_extra_cli_args,
        }

    command_args_text = str(run.get("command_args_text") or "")
    validate_command_args_text(command_args_text, executor_kind=executor_kind)
    return {
        "executor_kind": executor_kind,
        "executor_mode": executor_mode,
        "command_cli": str(run.get("command_cli") or "").strip() or profile.cli_name,
        "command_args_text": command_args_text,
        "model": step_model or role_model or str(run.get("model") or ""),
        "reasoning_effort": str(run.get("reasoning_effort") or "").strip(),
        "step_model": step_model,
        "inherit_session": step_inherit_session,
        "extra_cli_args_text": step_extra_cli_args,
    }


class ServiceRunnerStepRuntimeMixin:
    def prepare_runner_step_request(
        self,
        request: RunnerStepRuntimeRequest,
    ) -> dict[str, object]:
        runtime_request = request
        run = runtime_request.run
        layout = runtime_request.layout
        iter_id = runtime_request.iter_id
        step = runtime_request.step
        step_order = runtime_request.step_order
        role = runtime_request.role
        execution_settings = runtime_request.execution_settings
        step_dir = layout.step_dir(iter_id, step_order, step["id"])
        step_dir.mkdir(parents=True, exist_ok=True)
        output_path = layout.step_output_raw_path(iter_id, step_order, step["id"])
        prompt_metadata, prompt_body = self._parse_runtime_prompt(
            runtime_request.prompt_files[role["prompt_ref"]],
            expected_archetype=role["archetype"],
        )
        runtime_role = self._runtime_role_key(role)
        context_preparation = prepare_runner_step_instruction_context(runtime_request)
        step_instruction_context = context_preparation.step_instruction_context
        context_path = context_preparation.context_path
        current_handoffs_for_step = context_preparation.current_handoffs_for_step
        previous_iteration_summary_for_step = context_preparation.previous_iteration_summary_for_step
        self.append_run_event(
            run["id"],
            "step_instruction_context_prepared",
            {
                "iter": iter_id,
                "step_id": step["id"],
                "step_order": step_order,
                "role_name": role["name"],
                "archetype": role["archetype"],
                "context_path": layout.relative(context_path),
                "previous_iteration_exists": step_instruction_context["iteration"]["previous_iteration_exists"],
                "completed_steps_this_iteration": len(current_handoffs_for_step),
                "immediate_previous_step_id": (
                    step_instruction_context["upstream"]["immediate_previous_step"]["source"]["step_id"]
                    if step_instruction_context["upstream"]["immediate_previous_step"]
                    else None
                ),
            },
            role=runtime_role,
        )
        prompt_text = build_headless_prompt(
            HeadlessPromptRequest(
                role=role,
                prompt_label=str(prompt_metadata.get("label", role["name"])),
                prompt_body=prompt_body,
                step_instruction_context=step_instruction_context,
                compiled_spec=runtime_request.compiled_spec,
            )
        )
        resume_session_ref = runtime_request.previous_session_refs_by_step.get(step["id"]) if execution_settings["inherit_session"] else None
        role_request = RoleRequest(
            run_id=run["id"],
            role=runtime_role,
            role_archetype=role["archetype"],
            role_name=role["name"],
            step_id=step["id"],
            prompt=prompt_text,
            workdir=Path(run["workdir"]),
            executor_kind=execution_settings["executor_kind"],
            executor_mode=execution_settings["executor_mode"],
            command_cli=execution_settings["command_cli"],
            command_args_text=execution_settings["command_args_text"],
            inherit_session=bool(execution_settings["inherit_session"]),
            resume_session_id=str((resume_session_ref or {}).get("session_id", "")),
            extra_cli_args_text=str(execution_settings["extra_cli_args_text"]),
            model=execution_settings["model"],
            reasoning_effort=execution_settings["reasoning_effort"],
            output_schema=self._output_schema_for_archetype(role["archetype"]),
            output_path=output_path,
            run_dir=layout.run_dir,
            sandbox=self._sandbox_for_action_policy(step.get("action_policy")),
            idle_timeout_seconds=self.settings.role_idle_timeout_seconds,
            extra_context={
                "iter_id": iter_id,
                "compiled_spec": runtime_request.compiled_spec,
                "archetype": role["archetype"],
                "step_id": step["id"],
                "role_name": role["name"],
                "action_policy": dict(step.get("action_policy") or {}),
                "step_model": execution_settings["step_model"],
                "context_path": layout.relative(context_path),
                "inherit_session": bool(execution_settings["inherit_session"]),
                "extra_cli_args_text": str(execution_settings["extra_cli_args_text"]),
                "resume_session_id": str((resume_session_ref or {}).get("session_id", "")),
                "executor_kind": execution_settings["executor_kind"],
                "executor_mode": execution_settings["executor_mode"],
                "legacy_role": runtime_role,
                STEP_INSTRUCTION_CONTEXT_KEY: step_instruction_context,
                "immediate_previous_step": step_instruction_context["upstream"]["immediate_previous_step"],
                "previous_iteration_summary": previous_iteration_summary_for_step,
                "current_outputs_by_step": runtime_request.current_outputs_by_step,
                "current_outputs_by_role": runtime_request.current_outputs_by_role,
                "current_outputs_by_archetype": runtime_request.current_outputs_by_archetype,
                "previous_outputs_by_step": runtime_request.previous_outputs_by_step,
                "previous_outputs_by_role": runtime_request.previous_outputs_by_role,
                "previous_outputs_by_archetype": runtime_request.previous_outputs_by_archetype,
                "inspector_output": runtime_request.current_outputs_by_archetype.get("inspector"),
                "tester_output": runtime_request.current_outputs_by_archetype.get("inspector"),
                "previous_builder_result": runtime_request.previous_outputs_by_archetype.get("builder"),
                "previous_generator_result": runtime_request.previous_outputs_by_archetype.get("builder"),
                "previous_inspector_result": runtime_request.previous_outputs_by_archetype.get("inspector"),
                "previous_tester_result": runtime_request.previous_outputs_by_archetype.get("inspector"),
                "previous_gatekeeper_result": runtime_request.previous_outputs_by_archetype.get("gatekeeper"),
                "previous_verifier_result": runtime_request.previous_outputs_by_archetype.get("gatekeeper"),
                "previous_guide_result": runtime_request.previous_outputs_by_archetype.get("guide"),
                "previous_challenger_result": runtime_request.previous_outputs_by_archetype.get("guide"),
                "stagnation_mode": runtime_request.stagnation_mode,
                "evidence_progress_mode": runtime_request.evidence_progress_mode,
                "covered_check_count": runtime_request.covered_check_count,
                "missing_check_count": runtime_request.missing_check_count,
                "consecutive_no_required_coverage_delta": runtime_request.consecutive_no_required_coverage_delta,
            },
        )
        self._record_role_request(run["id"], role_request)
        return {
            STEP_INSTRUCTION_CONTEXT_KEY: step_instruction_context,
            "role_request": role_request,
            "prompt": prompt_text,
            "output_path": output_path,
            "runtime_role": runtime_role,
        }

    def _run_runner_step(
        self,
        request: RunnerStepRuntimeRequest,
    ) -> tuple[dict, dict, dict]:
        runtime_request = request
        run = runtime_request.run
        iter_id = runtime_request.iter_id
        step = runtime_request.step
        step_order = runtime_request.step_order
        role = runtime_request.role
        prepared = self.prepare_runner_step_request(request)
        step_instruction_context = prepared["step_instruction_context"]
        role_request = prepared["role_request"]
        runtime_role = str(prepared["runtime_role"])

        def execute_request() -> dict:
            return runtime_request.executor.execute(
                role_request,
                lambda event_type, payload: self.append_run_event(
                    run["id"],
                    event_type,
                    {
                        **payload,
                        "step_id": step["id"],
                        "step_order": step_order,
                        "role_name": role["name"],
                        "archetype": role["archetype"],
                    },
                    role=runtime_role,
                ),
                lambda: self.repository.should_stop(run["id"]),
                lambda pid: (
                    self.repository.update_run(run["id"], child_pid=pid) if pid is not None else self.repository.update_run(run["id"], clear_child_pid=True)
                ),
            )

        output = self._execute_role(
            RoleExecutionRequest(
                run_id=run["id"],
                iter_id=iter_id,
                role=runtime_role,
                fn=execute_request,
                retry_config=runtime_request.retry_config,
                event_context={
                    "step_id": step["id"],
                    "step_order": step_order,
                    "role_name": role["name"],
                    "archetype": role["archetype"],
                },
            )
        )
        session_ref = role_request.extra_context.get("session_ref")
        if not isinstance(session_ref, dict):
            session_ref = {}
        elif not session_ref.get("session_id") and role_request.resume_session_id.strip():
            session_ref = {
                **session_ref,
                "session_id": role_request.resume_session_id.strip(),
            }
        return output, step_instruction_context, session_ref

    def _resolve_role_execution_settings(self, run: dict, step: dict, role: dict) -> dict[str, object]:
        return resolve_runner_role_execution_settings(run, step, role)

    def _parse_runtime_prompt(self, prompt_markdown: str, *, expected_archetype: str) -> tuple[dict, str]:
        try:
            return validate_strategy_prompt_markdown(prompt_markdown, expected_archetype=expected_archetype)
        except StrategySourceError as exc:
            raise LooporaError(str(exc)) from exc

    def _sandbox_for_action_policy(self, action_policy: dict | None) -> str:
        policy = action_policy if isinstance(action_policy, dict) else {}
        if str(policy.get("workspace") or "").strip() == "workspace_write":
            return "workspace-write"
        return "read-only"

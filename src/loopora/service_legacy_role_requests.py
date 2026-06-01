from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loopora.executor_types import CodexExecutor, RoleRequest
from loopora.service_prompts import (
    CHECK_PLANNER_SCHEMA,
    CHALLENGER_SCHEMA,
    GENERATOR_SCHEMA,
    TESTER_SCHEMA,
    VERIFIER_SCHEMA,
    GeneratorPromptRequest,
)


@dataclass(frozen=True)
class IterationRoleRunRequest:
    executor: CodexExecutor
    run: dict
    compiled_spec: dict
    run_dir: Path
    iter_id: int
    mode: str = "default"
    previous_generator_result: dict | None = None
    previous_tester_result: dict | None = None
    previous_verifier_result: dict | None = None
    previous_challenger_result: dict | None = None
    tester_output: dict | None = None
    stagnation: dict | None = None


class ServiceLegacyRoleRequestMixin:
    def _role_request_defaults(self, run: dict, run_dir: Path, *, model: str) -> dict:
        return {
            "workdir": Path(run["workdir"]),
            "executor_kind": run.get("executor_kind", "codex"),
            "executor_mode": run.get("executor_mode", "preset"),
            "command_cli": run.get("command_cli", ""),
            "command_args_text": run.get("command_args_text", ""),
            "model": model,
            "reasoning_effort": run["reasoning_effort"],
            "run_dir": run_dir,
            "idle_timeout_seconds": self.settings.role_idle_timeout_seconds,
        }

    def _execute_request(self, executor: CodexExecutor, run: dict, request: RoleRequest) -> dict:
        self._record_role_request(run["id"], request)
        return executor.execute(
            request,
            lambda event_type, payload: self.append_run_event(run["id"], event_type, payload, role=request.role),
            lambda: self.repository.should_stop(run["id"]),
            lambda pid: self.repository.update_run(run["id"], child_pid=pid)
            if pid is not None
            else self.repository.update_run(run["id"], clear_child_pid=True),
        )

    def _run_generator(self, request: IterationRoleRunRequest) -> dict:
        role_request = RoleRequest(
            run_id=request.run["id"],
            role="generator",
            prompt=self._generator_prompt(
                GeneratorPromptRequest(
                    compiled_spec=request.compiled_spec,
                    workdir=Path(request.run["workdir"]),
                    iter_id=request.iter_id,
                    mode=request.mode,
                    previous_generator_result=request.previous_generator_result,
                    previous_tester_result=request.previous_tester_result,
                    previous_verifier_result=request.previous_verifier_result,
                    previous_challenger_result=request.previous_challenger_result,
                )
            ),
            output_schema=GENERATOR_SCHEMA,
            output_path=request.run_dir / "generator_output.json",
            sandbox="workspace-write",
            extra_context={
                "iter_id": request.iter_id,
                "compiled_spec": request.compiled_spec,
                "previous_generator_result": request.previous_generator_result,
                "previous_tester_result": request.previous_tester_result,
                "previous_verifier_result": request.previous_verifier_result,
                "previous_challenger_result": request.previous_challenger_result,
            },
            **self._role_request_defaults(
                request.run,
                request.run_dir,
                model=request.run["role_models_json"].get("generator", request.run["model"]),
            ),
        )
        return self._execute_request(request.executor, request.run, role_request)

    def _run_check_planner(
        self,
        executor: CodexExecutor,
        run: dict,
        compiled_spec: dict,
        run_dir: Path,
    ) -> dict:
        layout = self._run_artifact_layout(run_dir)
        request = RoleRequest(
            run_id=run["id"],
            role="check_planner",
            prompt=self._check_planner_prompt(compiled_spec),
            output_schema=CHECK_PLANNER_SCHEMA,
            output_path=layout.check_planner_output_raw_path,
            sandbox="read-only",
            extra_context={"compiled_spec": compiled_spec},
            **self._role_request_defaults(run, run_dir, model=run["model"]),
        )
        return self._execute_request(executor, run, request)

    def _run_tester(self, request: IterationRoleRunRequest) -> dict:
        role_request = RoleRequest(
            run_id=request.run["id"],
            role="tester",
            prompt=self._tester_prompt(request.compiled_spec, request.iter_id, request.mode),
            output_schema=TESTER_SCHEMA,
            output_path=request.run_dir / "tester_output.raw.json",
            sandbox="workspace-write",
            extra_context={"iter_id": request.iter_id, "compiled_spec": request.compiled_spec},
            **self._role_request_defaults(
                request.run,
                request.run_dir,
                model=request.run["role_models_json"].get("tester", request.run["model"]),
            ),
        )
        return self._execute_request(request.executor, request.run, role_request)

    def _run_verifier(self, request: IterationRoleRunRequest) -> dict:
        tester_output = request.tester_output or {}
        role_request = RoleRequest(
            run_id=request.run["id"],
            role="verifier",
            prompt=self._verifier_prompt(request.compiled_spec, tester_output, request.iter_id, request.mode),
            output_schema=VERIFIER_SCHEMA,
            output_path=request.run_dir / "verifier_output.raw.json",
            sandbox="read-only",
            extra_context={"iter_id": request.iter_id, "compiled_spec": request.compiled_spec, "tester_output": tester_output},
            **self._role_request_defaults(
                request.run,
                request.run_dir,
                model=request.run["role_models_json"].get("verifier", request.run["model"]),
            ),
        )
        return self._execute_request(request.executor, request.run, role_request)

    def _run_challenger(self, request: IterationRoleRunRequest) -> dict:
        stagnation = request.stagnation or {}
        role_request = RoleRequest(
            run_id=request.run["id"],
            role="challenger",
            prompt=self._challenger_prompt(request.compiled_spec, stagnation, request.iter_id),
            output_schema=CHALLENGER_SCHEMA,
            output_path=request.run_dir / "challenger_output.raw.json",
            sandbox="read-only",
            extra_context={
                "iter_id": request.iter_id,
                "compiled_spec": request.compiled_spec,
                "stagnation_mode": stagnation["stagnation_mode"],
            },
            **self._role_request_defaults(
                request.run,
                request.run_dir,
                model=request.run["role_models_json"].get("challenger", request.run["model"]),
            ),
        )
        return self._execute_request(request.executor, request.run, role_request)

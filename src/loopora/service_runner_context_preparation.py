from __future__ import annotations

import logging
import time
from pathlib import Path

from loopora.diagnostics import get_logger, log_event
from loopora.engine.runner_context import RunnerRunContext
from loopora.recovery import RetryConfig
from loopora.service_types import normalize_completion_mode
from loopora.strategy_source import normalize_strategy_source
from loopora.utils import read_json

logger = get_logger(__name__)


class ServiceRunnerContextPreparationMixin:
    def _prepare_runner_run_context(
        self,
        run_id: str,
        run: dict,
        run_dir: Path,
        strategy_source: dict,
    ) -> RunnerRunContext:
        executor = self.executor_factory()
        compiled_spec = run["compiled_spec_json"]
        retry_config = RetryConfig(max_retries=run["max_role_retries"])
        prompt_files = self._read_prompt_files_for_run(run)
        layout = self._run_artifact_layout(run_dir)
        strategy_source = normalize_strategy_source(strategy_source)
        role_by_id = {role["id"]: role for role in strategy_source.get("roles", [])}
        strategy_steps = list(strategy_source.get("steps", []))
        strategy_controls = list(strategy_source.get("controls", []))
        completion_mode = normalize_completion_mode(run.get("completion_mode", "gatekeeper"))

        self.append_run_event(run_id, "run_started", {"status": "running"})
        self._write_summary(run_id, "running", "Resolving checks for this run.")
        compiled_spec = self._resolve_run_checks(run, executor, compiled_spec, run_dir, retry_config)
        run_contract = read_json(layout.run_contract_path)
        self._write_summary(run_id, "running", "Waiting for the first runner iteration to complete.")
        log_event(
            logger,
            logging.INFO,
            "service.runner.execution.started",
            "Starting runner run execution",
            **self._run_log_context(
                run,
                completion_mode=completion_mode,
                step_count=len(strategy_steps),
                role_count=len(role_by_id),
            ),
        )
        return RunnerRunContext(
            run_id=run_id,
            run=run,
            run_dir=run_dir,
            strategy_source=strategy_source,
            executor=executor,
            compiled_spec=compiled_spec,
            retry_config=retry_config,
            prompt_files=prompt_files,
            layout=layout,
            run_contract=run_contract,
            strategy_steps=strategy_steps,
            strategy_controls=strategy_controls,
            control_fire_counts={},
            runner_started_at=time.monotonic(),
            role_by_id=role_by_id,
            completion_mode=completion_mode,
        )

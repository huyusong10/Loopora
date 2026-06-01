from __future__ import annotations

import logging
from pathlib import Path

from loopora.diagnostics import get_logger, log_event
from loopora.evidence_coverage import write_evidence_coverage_projection
from loopora.evidence_coverage_targets import with_coverage_targets
from loopora.executor_types import CodexExecutor
from loopora.recovery import RetryConfig
from loopora.run_artifacts import write_json_with_mirrors
from loopora.service_legacy_role_requests import (
    IterationRoleRunRequest as IterationRoleRunRequest,
    ServiceLegacyRoleRequestMixin,
)
from loopora.service_role_execution_lifecycle import (
    RoleExecutionRequest as RoleExecutionRequest,
    ServiceRoleExecutionLifecycleMixin,
)
from loopora.service_types import LooporaError
from loopora.utils import read_json, utc_now

logger = get_logger(__name__)


class ServiceRoleExecutionMixin(ServiceRoleExecutionLifecycleMixin, ServiceLegacyRoleRequestMixin):
    def _resolve_run_checks(
        self,
        run: dict,
        executor: CodexExecutor,
        compiled_spec: dict,
        run_dir: Path,
        retry_config: RetryConfig,
    ) -> dict:
        layout = self._run_artifact_layout(run_dir)
        checks = compiled_spec.get("checks", [])
        if checks:
            self.append_run_event(
                run["id"],
                "checks_resolved",
                {"source": "specified", "count": len(checks)},
            )
            log_event(
                logger,
                logging.INFO,
                "service.run.checks.resolved",
                "Run checks were resolved from the user-provided spec",
                **self._run_log_context(run, source="specified", check_count=len(checks)),
            )
            return compiled_spec

        planner_result = self._execute_role(
            RoleExecutionRequest(
                run_id=run["id"],
                iter_id=None,
                role="check_planner",
                fn=lambda: self._run_check_planner(executor, run, compiled_spec, run_dir),
                retry_config=retry_config,
            )
        )
        resolved_checks = self._normalize_generated_checks(planner_result.get("checks", []))
        if not resolved_checks:
            raise LooporaError("check planner returned no checks")

        resolved_spec = with_coverage_targets(
            {
                **compiled_spec,
                "checks": resolved_checks,
                "check_mode": "auto_generated",
                "check_generation_notes": str(planner_result.get("generation_notes", "")).strip(),
            },
            completion_mode=str(run.get("completion_mode", "gatekeeper")),
        )
        write_json_with_mirrors(layout.contract_compiled_spec_path, resolved_spec)
        write_json_with_mirrors(
            layout.contract_auto_checks_path,
            {
                "generated_at": utc_now(),
                "count": len(resolved_checks),
                "notes": resolved_spec["check_generation_notes"],
                "checks": resolved_checks,
            },
            mirror_paths=[layout.legacy_auto_checks_path],
        )
        run_contract = read_json(layout.run_contract_path)
        if run_contract:
            run_contract["compiled_spec"] = resolved_spec
            write_json_with_mirrors(layout.run_contract_path, run_contract)
        write_evidence_coverage_projection(layout)
        self.repository.update_run(run["id"], compiled_spec=resolved_spec)
        self.append_run_event(
            run["id"],
            "checks_resolved",
            {
                "source": "auto_generated",
                "count": len(resolved_checks),
                "notes": resolved_spec["check_generation_notes"],
            },
        )
        log_event(
            logger,
            logging.INFO,
            "service.run.checks.resolved",
            "Run checks were generated automatically for exploratory execution",
            **self._run_log_context(
                run,
                source="auto_generated",
                check_count=len(resolved_checks),
                notes=resolved_spec["check_generation_notes"],
            ),
        )
        return resolved_spec

from __future__ import annotations

import logging
from hashlib import sha256
from pathlib import Path
from typing import Any

from loopora.context_contract_snapshot import RunContractSnapshotRequest, build_run_contract_snapshot
from loopora.diagnostics import get_logger, log_event
from loopora.evidence_coverage import write_evidence_coverage_projection
from loopora.evidence_coverage_targets import with_coverage_targets
from loopora.executor_command_args import coerce_reasoning_effort
from loopora.run_artifacts import INITIAL_STAGNATION_STATE, write_json_with_mirrors, write_text_with_mirrors
from loopora.service_cleanup_diagnostics import best_effort_rmtree
from loopora.service_types import (
    ACTIVE_WORKDIR_CONFLICT_MESSAGE,
    LooporaConflictError,
    LooporaError,
    LooporaNotFoundError,
    LooporaWorkdirUnavailableError,
)
from loopora.strategy_source import StrategySourceError
from loopora.utils import make_id
from loopora.workdir_inputs import workdir_path_state

logger = get_logger(__name__)

RUN_ARTIFACT_PREPARE_ERROR = "run artifacts could not be prepared"


class ServiceRunStartMixin:
    def start_run(self, loop_id: str) -> dict:
        loop = self.repository.get_loop(loop_id)
        if not loop:
            raise LooporaNotFoundError(f"unknown loop: {loop_id}")
        log_event(
            logger,
            logging.INFO,
            "service.run.start.requested",
            "Received run start request",
            **self._loop_log_context(loop),
        )
        workdir = _ensure_loop_workdir_available_for_run(loop)
        workdir_text = str(workdir)
        if self.repository.has_active_run_for_workdir(workdir_text):
            raise LooporaConflictError(ACTIVE_WORKDIR_CONFLICT_MESSAGE)

        strategy_source = self._normalized_strategy_source_from_record(loop)
        try:
            prompt_files = self._read_prompt_files_for_loop(workdir_text, loop["id"], strategy_source)
        except StrategySourceError as exc:
            raise LooporaError(str(exc)) from exc
        run_id = make_id("run")
        try:
            run_dir = self._ensure_run_dir(workdir, run_id)
        except OSError as exc:
            raise LooporaError(RUN_ARTIFACT_PREPARE_ERROR) from exc
        layout = self._run_artifact_layout(run_dir)
        try:
            layout.initialize()
            queued_summary = "# Loopora Run Summary\n\nQueued.\n"
            workspace_baseline = self._capture_workspace_manifest(workdir)
            write_text_with_mirrors(layout.summary_path, queued_summary)
            write_json_with_mirrors(layout.workspace_baseline_path, workspace_baseline)
            write_json_with_mirrors(
                layout.timeline_stagnation_path,
                dict(INITIAL_STAGNATION_STATE),
                mirror_paths=[layout.run_dir / "stagnation.json"],
            )
            compiled_spec = with_coverage_targets(
                loop["compiled_spec_json"],
                completion_mode=str(loop.get("completion_mode", "gatekeeper")),
            )
            source_bundle = self._loop_source_bundle_snapshot(loop_id)
            write_json_with_mirrors(layout.contract_compiled_spec_path, compiled_spec)
            write_text_with_mirrors(layout.contract_spec_path, loop["spec_markdown"])
            write_json_with_mirrors(
                layout.contract_strategy_source_path,
                strategy_source,
                mirror_paths=[layout.contract_workflow_path],
            )
            self._persist_prompt_files(layout.contract_dir, prompt_files)

            run_contract = build_run_contract_snapshot(
                RunContractSnapshotRequest(
                    run={
                        "id": run_id,
                        "loop_id": loop_id,
                        "workdir": workdir_text,
                        "completion_mode": loop.get("completion_mode", "gatekeeper"),
                        "max_iters": loop["max_iters"],
                        "max_role_retries": loop["max_role_retries"],
                        "delta_threshold": loop["delta_threshold"],
                        "trigger_window": loop["trigger_window"],
                        "regression_window": loop["regression_window"],
                        "iteration_interval_seconds": loop.get("iteration_interval_seconds", 0.0),
                        "executor_kind": loop.get("executor_kind", "codex"),
                        "executor_mode": loop.get("executor_mode", "preset"),
                        "model": loop["model"],
                        "reasoning_effort": coerce_reasoning_effort(
                            loop["reasoning_effort"],
                            loop.get("executor_kind", "codex"),
                        ),
                    },
                    compiled_spec=compiled_spec,
                    strategy_source=strategy_source,
                    prompt_files=prompt_files,
                    workspace_baseline=workspace_baseline,
                    layout=layout,
                    collaboration_summary=str(source_bundle.get("collaboration_summary") or "").strip(),
                    source_bundle=source_bundle,
                )
            )
            write_json_with_mirrors(layout.run_contract_path, run_contract)
            write_evidence_coverage_projection(layout)
        except OSError as exc:
            best_effort_rmtree(
                run_dir,
                logger,
                operation="run_artifact_prepare_failed_cleanup",
                owner_id=loop_id,
                workdir=workdir_text,
            )
            raise LooporaError(RUN_ARTIFACT_PREPARE_ERROR) from exc
        except Exception:
            best_effort_rmtree(
                run_dir,
                logger,
                operation="run_artifact_prepare_failed_cleanup",
                owner_id=loop_id,
                workdir=workdir_text,
            )
            raise

        try:
            run = self.repository.create_run(
                {
                    "id": run_id,
                    "loop_id": loop_id,
                    "workdir": workdir_text,
                    "spec_path": loop["spec_path"],
                    "spec_markdown": loop["spec_markdown"],
                    "compiled_spec": compiled_spec,
                    "executor_kind": loop.get("executor_kind", "codex"),
                    "executor_mode": loop.get("executor_mode", "preset"),
                    "command_cli": loop.get("command_cli", ""),
                    "command_args_text": loop.get("command_args_text", ""),
                    "model": loop["model"],
                    "reasoning_effort": coerce_reasoning_effort(
                        loop["reasoning_effort"],
                        loop.get("executor_kind", "codex"),
                    ),
                    "completion_mode": loop.get("completion_mode", "gatekeeper"),
                    "iteration_interval_seconds": loop.get("iteration_interval_seconds", 0.0),
                    "max_iters": loop["max_iters"],
                    "max_role_retries": loop["max_role_retries"],
                    "delta_threshold": loop["delta_threshold"],
                    "trigger_window": loop["trigger_window"],
                    "regression_window": loop["regression_window"],
                    "orchestration_id": loop.get("orchestration_id", ""),
                    "orchestration_name": loop.get("orchestration_name", ""),
                    "role_models": loop["role_models_json"],
                    "workflow": strategy_source,
                    "status": "queued",
                    "runs_dir": str(run_dir),
                    "summary_md": queued_summary,
                }
            )
        except Exception:
            best_effort_rmtree(
                run_dir,
                logger,
                operation="run_registration_failed_cleanup",
                owner_id=loop_id,
                workdir=workdir_text,
            )
            raise
        self.append_run_event(run_id, "run_registered", {"loop_id": loop_id, "status": "queued"})
        log_event(
            logger,
            logging.INFO,
            "service.run.registered",
            "Registered queued run",
            **self._run_log_context(run, status=run["status"]),
        )
        return self._hydrate_run_files(run)

    def _loop_bundle_collaboration_summary(self, loop_id: str) -> str:
        return str(self._loop_source_bundle_snapshot(loop_id).get("collaboration_summary") or "").strip()

    def _loop_source_bundle_snapshot(self, loop_id: str) -> dict:
        try:
            bundle = self.repository.get_bundle_by_loop_id(loop_id)
        except AttributeError:
            return {}
        if not bundle:
            return {}
        bundle_id = str(bundle.get("id") or "").strip()
        return {
            **self._loop_source_bundle_fingerprint(bundle_id),
            "id": str(bundle.get("id") or "").strip(),
            "name": str(bundle.get("name") or "").strip(),
            "revision": bundle.get("revision", 0),
            "source_bundle_id": str(bundle.get("source_bundle_id") or "").strip(),
            "imported_from_path": str(bundle.get("imported_from_path") or "").strip(),
            "collaboration_summary": str(bundle.get("collaboration_summary") or "").strip(),
        }

    def _loop_source_bundle_fingerprint(self, bundle_id: str) -> dict[str, Any]:
        fingerprint: dict[str, Any] = {"bundle_sha256": "", "bundle_bytes": 0, "bundle_yaml_path": ""}
        if not bundle_id:
            return fingerprint
        bundle_yaml_path = getattr(self, "_bundle_yaml_path", None)
        if callable(bundle_yaml_path):
            fingerprint["bundle_yaml_path"] = str(bundle_yaml_path(bundle_id))
        export_bundle_yaml = getattr(self, "export_bundle_yaml", None)
        if not callable(export_bundle_yaml):
            return fingerprint
        try:
            bundle_yaml = str(export_bundle_yaml(bundle_id) or "")
        except (LooporaError, OSError, UnicodeError, ValueError):
            return fingerprint
        data = bundle_yaml.encode("utf-8")
        fingerprint["bundle_sha256"] = sha256(data).hexdigest()
        fingerprint["bundle_bytes"] = len(data)
        return fingerprint


def _ensure_loop_workdir_available_for_run(loop: dict) -> Path:
    state = workdir_path_state(loop.get("workdir"))
    workdir = str(state.get("workdir") or "")
    status = str(state.get("status") or "")
    if status == "ready":
        return Path(workdir)
    raise LooporaWorkdirUnavailableError(workdir=workdir, workdir_state=status)

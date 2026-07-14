from __future__ import annotations

import logging
from pathlib import Path

from loopora.diagnostics import get_logger, log_event
from loopora.local_workdir_artifacts import loop_artifact_dir_for_ready_workdir
from loopora.service_cleanup_diagnostics import best_effort_rmtree, record_cleanup_failure
from loopora.service_types import ACTIVE_RUN_STATUSES, LooporaConflictError

logger = get_logger(__name__)


class ServiceLoopDeletionMixin:
    def preview_loop_delete(self, loop_id: str) -> dict:
        loop = self.get_loop(loop_id)
        runs = loop.get("runs") if isinstance(loop.get("runs"), list) else []
        run_ids = [
            str(run.get("id") or "").strip()
            for run in runs
            if isinstance(run, dict) and str(run.get("id") or "").strip()
        ]
        active_run_ids = [
            str(run.get("id") or "").strip()
            for run in runs
            if isinstance(run, dict)
            and str(run.get("status") or "").strip() in ACTIVE_RUN_STATUSES
            and str(run.get("id") or "").strip()
        ]
        return {
            "status": "dry_run",
            "dry_run": True,
            "delete_allowed": not active_run_ids,
            "id": loop.get("id"),
            "name": loop.get("name") or "",
            "workdir": loop.get("workdir") or "",
            "would_delete": {"loop": loop.get("id"), "run_count": len(runs), "run_ids": run_ids},
            "blocked_by_active_runs": active_run_ids,
            "does_not_delete": [
                "target_project_workdir",
                "source_spec_file",
                "exported_plan_files",
                "external_provider_history",
            ],
        }

    def delete_loop(self, loop_id: str, *, allow_bundle_owned: bool = False) -> dict:
        if not allow_bundle_owned and hasattr(self, "_bundle_record_for_loop_id"):
            bundle = self._bundle_record_for_loop_id(loop_id)
            if bundle:
                raise LooporaConflictError(f"loop {loop_id} is managed by bundle {bundle['id']}; delete the bundle instead")
        loop = self.get_loop(loop_id)
        active_runs = [run["id"] for run in loop["runs"] if run["status"] in ACTIVE_RUN_STATUSES]
        if active_runs:
            raise LooporaConflictError(f"cannot delete loop with active runs: {', '.join(active_runs)}")

        paths_to_remove = [Path(run["runs_dir"]) for run in loop["runs"]]
        loop_artifact_dir = loop_artifact_dir_for_ready_workdir(loop["workdir"], loop_id)
        if loop_artifact_dir is not None:
            paths_to_remove.append(loop_artifact_dir)

        self.repository.delete_loop(loop_id)
        for path in paths_to_remove:
            best_effort_rmtree(
                path,
                logger,
                operation="loop_artifact_delete",
                owner_id=loop_id,
                workdir=loop["workdir"],
            )
            self._mark_local_asset_cleanup_by_path(path, operation="loop_artifact_delete", owner_id=loop_id)
        self._write_recent_workdirs()
        result = {"id": loop_id, "deleted_runs": len(loop["runs"]), "workdir": loop["workdir"]}
        log_event(
            logger,
            logging.INFO,
            "service.loop.deleted",
            "Deleted loop definition and local artifacts",
            loop_id=loop_id,
            workdir=loop["workdir"],
            deleted_run_count=len(loop["runs"]),
        )
        return result

    def _mark_local_asset_cleanup_by_path(self, path: Path, *, operation: str = "local_asset_cleanup", owner_id: object = "") -> None:
        target = Path(path)
        state = "cleaned" if not target.exists() else "orphaned"
        if hasattr(self.repository, "mark_local_asset_root_state_by_path"):
            try:
                self.repository.mark_local_asset_root_state_by_path(path=target, state=state)
            except Exception as exc:  # noqa: BLE001 - local asset registry marking is diagnostic-only cleanup.
                record_cleanup_failure(
                    logger,
                    operation=f"{operation}_registry_mark",
                    resource_type="local_asset_root",
                    resource_id=target,
                    owner_id=owner_id,
                    error=exc,
                )

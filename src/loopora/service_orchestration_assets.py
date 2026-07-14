from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, TypeVar, cast

from loopora.diagnostics import log_event
from loopora.service_asset_common import logger, record_bundle_asset_update_rollback_failure
from loopora.service_types import LooporaConflictError, LooporaError
from loopora.strategy_source import strategy_source_from_record

T = TypeVar("T")


@dataclass(frozen=True)
class OrchestrationMutationRequest:
    name: str
    description: str = ""
    strategy_source: dict | None = None
    prompt_files: dict | None = None
    role_models: dict | None = None

    @property
    def workflow(self) -> dict | None:
        return self.strategy_source


class ServiceOrchestrationAssetMixin:
    def list_orchestrations(self) -> list[dict]:
        return self._asset_call(self.asset_catalog.list_orchestrations)

    def get_orchestration(self, orchestration_id: str) -> dict:
        self._reconcile_local_orphaned_runs()
        return self._asset_call(self.asset_catalog.get_orchestration, orchestration_id)

    def preview_orchestration_delete(self, orchestration_id: str) -> dict:
        orchestration = self.get_orchestration(orchestration_id)
        blockers = self._orchestration_delete_blockers(orchestration_id)
        referencing_loop_ids = _loop_ids_referencing_orchestration(self.repository, orchestration_id)
        return {
            "status": "dry_run",
            "dry_run": True,
            "delete_allowed": not blockers,
            "id": orchestration["id"],
            "name": orchestration.get("name", ""),
            "would_delete": {
                "orchestration": orchestration["id"],
                "referencing_loop_count": len(referencing_loop_ids),
                "referencing_loop_ids": referencing_loop_ids,
            },
            "blockers": blockers,
            "does_not_delete": [
                "saved_loop_snapshots",
                "target_project_workdirs",
                "external_provider_history",
            ],
        }

    def create_orchestration(
        self,
        *,
        name: str,
        description: str = "",
        strategy_source: dict | None = None,
        prompt_files: dict | None = None,
        role_models: dict | None = None,
        **legacy_fields: Any,
    ) -> dict:
        strategy_source = _strategy_source_from_legacy_fields(strategy_source, legacy_fields)
        orchestration = self._asset_call(
            self.asset_catalog.create_orchestration,
            name=name,
            description=description,
            strategy_source=strategy_source,
            prompt_files=prompt_files,
            role_models=role_models,
        )
        role_count, step_count = _strategy_source_counts(orchestration)
        log_event(
            logger,
            logging.INFO,
            "service.orchestration.created",
            "Created orchestration definition",
            orchestration_id=orchestration["id"],
            orchestration_name=orchestration["name"],
            role_count=role_count,
            step_count=step_count,
        )
        return orchestration

    def update_orchestration(
        self,
        orchestration_id: str,
        request: OrchestrationMutationRequest | None = None,
        **raw_request: Any,
    ) -> dict:
        request = (
            _orchestration_mutation_request_from_kwargs(raw_request)
            if request is None
            else _validated_request(request, raw_request)
        )
        bundle = None
        previous_orchestration = None
        if hasattr(self, "_bundle_record_for_orchestration_id"):
            bundle = self._bundle_record_for_orchestration_id(orchestration_id)
            if bundle:
                previous_orchestration = self.get_orchestration(orchestration_id)
        orchestration = self._asset_call(
            self.asset_catalog.update_orchestration,
            orchestration_id,
            name=request.name,
            description=request.description,
            strategy_source=request.strategy_source,
            prompt_files=request.prompt_files,
            role_models=request.role_models,
        )
        if bundle and hasattr(self, "_touch_bundle_for_orchestration"):
            try:
                self._touch_bundle_for_orchestration(orchestration_id)
            except LooporaError:
                if previous_orchestration:
                    self.repository.update_orchestration(
                        orchestration_id,
                        {
                            "name": previous_orchestration["name"],
                            "description": previous_orchestration.get("description", ""),
                            "workflow": strategy_source_from_record(previous_orchestration) or {},
                            "prompt_files": previous_orchestration.get("prompt_files_json") or {},
                        },
                    )
                    if hasattr(self, "_sync_bundle_loop_snapshot"):
                        try:
                            self._sync_bundle_loop_snapshot(bundle["id"])
                        except Exception as rollback_exc:  # noqa: BLE001 - rollback diagnostics must preserve the original update error.
                            record_bundle_asset_update_rollback_failure(self, bundle, rollback_exc)
                raise
        role_count, step_count = _strategy_source_counts(orchestration)
        log_event(
            logger,
            logging.INFO,
            "service.orchestration.updated",
            "Updated orchestration definition",
            orchestration_id=orchestration["id"],
            orchestration_name=orchestration["name"],
            role_count=role_count,
            step_count=step_count,
        )
        return orchestration

    def delete_orchestration(self, orchestration_id: str, *, allow_bundle_owned: bool = False) -> dict:
        if not allow_bundle_owned:
            self._assert_orchestration_delete_allowed(orchestration_id)
        result = self._asset_call(self.asset_catalog.delete_orchestration, orchestration_id)
        log_event(
            logger,
            logging.INFO,
            "service.orchestration.deleted",
            "Deleted orchestration definition",
            orchestration_id=orchestration_id,
        )
        return result

    def _orchestration_delete_blockers(self, orchestration_id: str) -> list[dict]:
        blockers: list[dict] = []
        if hasattr(self, "_bundle_record_for_orchestration_id"):
            bundle = self._bundle_record_for_orchestration_id(orchestration_id)
            if bundle:
                blockers.append({"kind": "bundle_owned", "bundle_id": bundle["id"]})
        referencing_loop_ids = _loop_ids_referencing_orchestration(self.repository, orchestration_id)
        if referencing_loop_ids:
            blockers.append({"kind": "referenced_by_loops", "loop_ids": referencing_loop_ids})
        return blockers

    def _assert_orchestration_delete_allowed(self, orchestration_id: str) -> None:
        if hasattr(self, "_bundle_record_for_orchestration_id"):
            bundle = self._bundle_record_for_orchestration_id(orchestration_id)
            if bundle:
                raise LooporaConflictError(
                    f"orchestration {orchestration_id} is managed by bundle {bundle['id']}; delete the bundle instead"
                )
        referencing_loop_ids = _loop_ids_referencing_orchestration(self.repository, orchestration_id)
        if referencing_loop_ids:
            raise LooporaConflictError(
                f"orchestration {orchestration_id} is referenced by loops: {', '.join(referencing_loop_ids)}"
            )


def _pop_required(raw_request: dict[str, Any], field_name: str) -> Any:
    try:
        return raw_request.pop(field_name)
    except KeyError as exc:
        raise TypeError(f"missing required orchestration request field: {field_name}") from exc


def _validated_request(request: T, raw_request: dict[str, Any]) -> T:
    if raw_request:
        raise TypeError("orchestration request object cannot be combined with keyword fields")
    return request


_MISSING: Any = object()


def _pop_strategy_source_field(fields: dict[str, Any]) -> dict | None:
    strategy_source = fields.pop("strategy_source", _MISSING)
    workflow = fields.pop("workflow", _MISSING)
    if strategy_source is not _MISSING and workflow is not _MISSING:
        raise TypeError("orchestration request fields strategy_source and workflow cannot both be provided")
    if strategy_source is not _MISSING:
        return strategy_source
    if workflow is not _MISSING:
        return workflow
    return None


def _strategy_source_from_legacy_fields(strategy_source: dict | None, legacy_fields: dict[str, Any]) -> dict | None:
    workflow = legacy_fields.pop("workflow", _MISSING)
    if legacy_fields:
        unexpected_fields = ", ".join(sorted(legacy_fields))
        raise TypeError(f"unexpected orchestration request fields: {unexpected_fields}")
    if strategy_source is not None and workflow is not _MISSING:
        raise TypeError("orchestration request fields strategy_source and workflow cannot both be provided")
    return strategy_source if workflow is _MISSING else cast(dict | None, workflow)


def _orchestration_mutation_request_from_kwargs(raw_request: dict[str, Any]) -> OrchestrationMutationRequest:
    fields = dict(raw_request)
    request = OrchestrationMutationRequest(
        name=_pop_required(fields, "name"),
        description=fields.pop("description", ""),
        strategy_source=_pop_strategy_source_field(fields),
        prompt_files=fields.pop("prompt_files", None),
        role_models=fields.pop("role_models", None),
    )
    if fields:
        unexpected_fields = ", ".join(sorted(fields))
        raise TypeError(f"unexpected orchestration request fields: {unexpected_fields}")
    return request


def _strategy_source_counts(orchestration: dict) -> tuple[int, int]:
    strategy_source = strategy_source_from_record(orchestration)
    if not strategy_source:
        return 0, 0
    return len(list(strategy_source.get("roles") or [])), len(list(strategy_source.get("steps") or []))


def _loop_ids_referencing_orchestration(repository, orchestration_id: str) -> list[str]:
    target_id = str(orchestration_id or "").strip()
    if not target_id:
        return []
    return sorted(
        str(loop.get("id") or "").strip()
        for loop in repository.list_loops()
        if str(loop.get("orchestration_id") or "").strip() == target_id and str(loop.get("id") or "").strip()
    )

from __future__ import annotations

import logging

from loopora.asset_catalog import RoleDefinitionPayloadInput
from loopora.diagnostics import log_event
from loopora.service_asset_common import logger, record_bundle_asset_update_rollback_failure
from loopora.service_bundle_graph_preflight import strategy_source_role_definition_ids
from loopora.service_types import LooporaConflictError, LooporaError
from loopora.strategy_source import strategy_source_from_record


class ServiceRoleDefinitionAssetMixin:
    def list_role_definitions(self) -> list[dict]:
        return self._asset_call(self.asset_catalog.list_role_definitions)

    def get_role_definition(self, role_definition_id: str) -> dict:
        return self._asset_call(self.asset_catalog.get_role_definition, role_definition_id)

    def preview_role_definition_delete(self, role_definition_id: str) -> dict:
        role_definition = self.get_role_definition(role_definition_id)
        blockers = self._role_definition_delete_blockers(role_definition_id)
        referencing_orchestration_ids = _orchestration_ids_referencing_role_definition(self.repository, role_definition_id)
        return {
            "status": "dry_run",
            "dry_run": True,
            "delete_allowed": not blockers,
            "id": role_definition["id"],
            "name": role_definition.get("name", ""),
            "would_delete": {
                "role_definition": role_definition["id"],
                "referencing_orchestration_count": len(referencing_orchestration_ids),
                "referencing_orchestration_ids": referencing_orchestration_ids,
            },
            "blockers": blockers,
            "does_not_delete": [
                "saved_orchestration_snapshots",
                "saved_loop_snapshots",
                "target_project_workdirs",
                "external_provider_history",
            ],
        }

    def create_role_definition(
        self,
        request: RoleDefinitionPayloadInput | None = None,
        **raw_payload: object,
    ) -> dict:
        role_definition = self._asset_call(
            self.asset_catalog.create_role_definition,
            request,
            **raw_payload,
        )
        log_event(
            logger,
            logging.INFO,
            "service.role_definition.created",
            "Created role definition",
            role_definition_id=role_definition["id"],
            archetype=role_definition["archetype"],
            executor_kind=role_definition.get("executor_kind"),
            role_name=role_definition["name"],
        )
        return role_definition

    def update_role_definition(
        self,
        role_definition_id: str,
        request: RoleDefinitionPayloadInput | None = None,
        **raw_payload: object,
    ) -> dict:
        bundle = None
        previous_role_definition = None
        if hasattr(self, "_bundle_record_for_role_definition_id"):
            bundle = self._bundle_record_for_role_definition_id(role_definition_id)
            if bundle:
                previous_role_definition = self.get_role_definition(role_definition_id)
        role_definition = self._asset_call(
            self.asset_catalog.update_role_definition,
            role_definition_id,
            request,
            **raw_payload,
        )
        if bundle and hasattr(self, "_touch_bundle_for_role_definition"):
            try:
                self._touch_bundle_for_role_definition(role_definition_id)
            except LooporaError:
                if previous_role_definition:
                    self.repository.update_role_definition(
                        role_definition_id,
                        {
                            "name": previous_role_definition["name"],
                            "description": previous_role_definition.get("description", ""),
                            "archetype": previous_role_definition["archetype"],
                            "prompt_ref": previous_role_definition["prompt_ref"],
                            "prompt_markdown": previous_role_definition["prompt_markdown"],
                            "posture_notes": previous_role_definition.get("posture_notes", ""),
                            "executor_kind": previous_role_definition.get("executor_kind", "codex"),
                            "executor_mode": previous_role_definition.get("executor_mode", "preset"),
                            "command_cli": previous_role_definition.get("command_cli", ""),
                            "command_args_text": previous_role_definition.get("command_args_text", ""),
                            "model": previous_role_definition.get("model", ""),
                            "reasoning_effort": previous_role_definition.get("reasoning_effort", ""),
                        },
                    )
                    if hasattr(self, "_sync_bundle_loop_snapshot"):
                        try:
                            self._sync_bundle_loop_snapshot(bundle["id"])
                        except Exception as rollback_exc:  # noqa: BLE001 - rollback diagnostics must preserve the original update error.
                            record_bundle_asset_update_rollback_failure(self, bundle, rollback_exc)
                raise
        log_event(
            logger,
            logging.INFO,
            "service.role_definition.updated",
            "Updated role definition",
            role_definition_id=role_definition["id"],
            archetype=role_definition["archetype"],
            executor_kind=role_definition.get("executor_kind"),
            role_name=role_definition["name"],
        )
        return role_definition

    def delete_role_definition(self, role_definition_id: str, *, allow_bundle_owned: bool = False) -> dict:
        if not allow_bundle_owned:
            self._assert_role_definition_delete_allowed(role_definition_id)
        result = self._asset_call(self.asset_catalog.delete_role_definition, role_definition_id)
        log_event(
            logger,
            logging.INFO,
            "service.role_definition.deleted",
            "Deleted role definition",
            role_definition_id=role_definition_id,
        )
        return result

    def _role_definition_delete_blockers(self, role_definition_id: str) -> list[dict]:
        blockers: list[dict] = []
        if hasattr(self, "_bundle_record_for_role_definition_id"):
            bundle = self._bundle_record_for_role_definition_id(role_definition_id)
            if bundle:
                blockers.append({"kind": "bundle_owned", "bundle_id": bundle["id"]})
        referencing_orchestration_ids = _orchestration_ids_referencing_role_definition(self.repository, role_definition_id)
        if referencing_orchestration_ids:
            blockers.append({"kind": "referenced_by_orchestrations", "orchestration_ids": referencing_orchestration_ids})
        return blockers

    def _assert_role_definition_delete_allowed(self, role_definition_id: str) -> None:
        if hasattr(self, "_bundle_record_for_role_definition_id"):
            bundle = self._bundle_record_for_role_definition_id(role_definition_id)
            if bundle:
                raise LooporaConflictError(
                    f"role definition {role_definition_id} is managed by bundle {bundle['id']}; delete the bundle instead"
                )
        referencing_orchestration_ids = _orchestration_ids_referencing_role_definition(self.repository, role_definition_id)
        if referencing_orchestration_ids:
            raise LooporaConflictError(
                f"role definition {role_definition_id} is referenced by orchestrations: "
                f"{', '.join(referencing_orchestration_ids)}"
            )


def _orchestration_ids_referencing_role_definition(repository, role_definition_id: str) -> list[str]:
    target_id = str(role_definition_id or "").strip()
    if not target_id:
        return []
    return sorted(
        str(orchestration.get("id") or "").strip()
        for orchestration in repository.list_orchestrations()
        if target_id in strategy_source_role_definition_ids(strategy_source_from_record(orchestration) or {})
        and str(orchestration.get("id") or "").strip()
    )

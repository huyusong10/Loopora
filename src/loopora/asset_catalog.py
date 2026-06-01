from __future__ import annotations

from copy import deepcopy
from typing import Any

from loopora.asset_catalog_builtins import (
    build_builtin_orchestration_records,
    build_builtin_role_definition_records,
)
from loopora.asset_catalog_decoration import clone_asset_records
from loopora.asset_catalog_decoration import decorate_orchestration_record
from loopora.asset_catalog_decoration import decorate_role_definition_record
from loopora.asset_catalog_decoration import sanitize_persisted_prompt_files
from loopora.asset_catalog_inputs import (
    OrchestrationPayloadInput,
    RoleDefinitionPayloadInput as RoleDefinitionPayloadInput,
    orchestration_payload_input_from_args as _orchestration_payload_input_from_args,
    strategy_source_from_legacy_fields as _strategy_source_from_legacy_fields,
)
from loopora.asset_catalog_orchestration_resolution import (
    OrchestrationResolutionRequest,
    resolve_orchestration_input as _resolve_orchestration_input,
)
from loopora.asset_catalog_errors import AssetCatalogError as AssetCatalogError
from loopora.asset_catalog_errors import AssetCatalogNotFoundError
from loopora.asset_catalog_role_facade import RoleDefinitionAssetCatalogMixin
from loopora.db import LooporaRepository
from loopora.strategy_source import strategy_source_from_record
from loopora.utils import make_id


class StrategyTemplateAssetCatalog(RoleDefinitionAssetCatalogMixin):
    """Owns strategy-template and role-template asset records."""

    def __init__(self, repository: LooporaRepository) -> None:
        self.repository = repository
        self._builtin_orchestrations = build_builtin_orchestration_records()
        self._builtin_role_definitions = build_builtin_role_definition_records()

    def _clone_records(self, records: list[dict]) -> list[dict]:
        return clone_asset_records(records)

    def _decorate_orchestration(self, record: dict, *, source: str) -> dict:
        return decorate_orchestration_record(record, source=source)

    def _decorate_role_definition(self, record: dict, *, source: str) -> dict:
        return decorate_role_definition_record(record, source=source)

    @staticmethod
    def _sanitize_persisted_prompt_files(prompt_files: object) -> dict[str, str]:
        return sanitize_persisted_prompt_files(prompt_files)

    def list_orchestrations(self) -> list[dict]:
        custom_records = [
            self._decorate_orchestration(record, source="custom")
            for record in self.repository.list_orchestrations()
        ]
        builtin_records = [
            record
            for record in self._builtin_orchestrations
            if bool(record.get("visible", True))
        ]
        return self._clone_records(builtin_records) + custom_records

    def get_orchestration(self, orchestration_id: str) -> dict:
        orchestration_key = str(orchestration_id or "").strip()
        if not orchestration_key:
            raise ValueError("orchestration_id is required")
        if orchestration_key.startswith("builtin:"):
            for record in self._builtin_orchestrations:
                if record["id"] == orchestration_key:
                    return deepcopy(record)
            raise AssetCatalogNotFoundError(f"unknown built-in orchestration: {orchestration_key.split(':', 1)[1]}")
        record = self.repository.get_orchestration(orchestration_key)
        if not record:
            raise AssetCatalogNotFoundError(f"unknown orchestration: {orchestration_key}")
        return self._decorate_orchestration(record, source="custom")

    def resolve_orchestration_input(
        self,
        *,
        orchestration_id: str | None,
        workflow: dict | None,
        prompt_files: dict | None,
        role_models: dict | None,
    ) -> dict:
        return _resolve_orchestration_input(
            OrchestrationResolutionRequest(
                orchestration_id=orchestration_id,
                workflow=workflow,
                prompt_files=prompt_files,
                role_models=role_models,
                builtin_orchestrations=self._builtin_orchestrations,
                get_orchestration=self.get_orchestration,
                get_role_definition=self.get_role_definition,
                not_found_errors=(AssetCatalogNotFoundError,),
            )
        )

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
        normalized_name = str(name or "").strip()
        if not normalized_name:
            raise ValueError("name is required")
        strategy_source = _strategy_source_from_legacy_fields(strategy_source, legacy_fields)
        resolved = self.resolve_orchestration_input(
            orchestration_id=None,
            workflow=strategy_source,
            prompt_files=prompt_files,
            role_models=role_models,
        )
        orchestration = self.repository.create_orchestration(
            {
                "id": make_id("orch"),
                "name": normalized_name,
                "description": str(description or "").strip(),
                "workflow": resolved["workflow"],
                "prompt_files": resolved["prompt_files"],
            }
        )
        return self._decorate_orchestration(orchestration, source="custom")

    def update_orchestration(
        self,
        orchestration_id: str,
        request: OrchestrationPayloadInput | None = None,
        **raw_payload: object,
    ) -> dict:
        current = self.get_orchestration(orchestration_id)
        if current.get("source") == "builtin":
            raise ValueError("built-in orchestrations cannot be updated")
        payload_input = _orchestration_payload_input_from_args(request, raw_payload)
        normalized_name = str(payload_input.name or "").strip()
        if not normalized_name:
            raise ValueError("name is required")
        current_strategy_source = deepcopy(strategy_source_from_record(current) or {})
        current_prompt_files = dict(current.get("prompt_files_json") or {})
        effective_strategy_source = (
            payload_input.strategy_source if payload_input.strategy_source is not None else current_strategy_source
        )
        effective_prompt_files = dict(current_prompt_files)
        effective_prompt_files.update(dict(payload_input.prompt_files or {}))
        resolved = self.resolve_orchestration_input(
            orchestration_id=None,
            workflow=effective_strategy_source,
            prompt_files=effective_prompt_files,
            role_models=payload_input.role_models,
        )
        orchestration = self.repository.update_orchestration(
            orchestration_id,
            {
                "name": normalized_name,
                "description": str(payload_input.description or "").strip(),
                "workflow": resolved["workflow"],
                "prompt_files": resolved["prompt_files"],
            },
        )
        if not orchestration:
            raise AssetCatalogNotFoundError(f"unknown orchestration: {orchestration_id}")
        return self._decorate_orchestration(orchestration, source="custom")

    def delete_orchestration(self, orchestration_id: str) -> dict:
        orchestration = self.get_orchestration(orchestration_id)
        if orchestration.get("source") == "builtin":
            raise ValueError("built-in orchestrations cannot be deleted")
        if not self.repository.delete_orchestration(orchestration_id):
            raise AssetCatalogNotFoundError(f"unknown orchestration: {orchestration_id}")
        return orchestration


WorkflowAssetCatalog = StrategyTemplateAssetCatalog

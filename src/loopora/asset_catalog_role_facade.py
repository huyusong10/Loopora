from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

from loopora.asset_catalog_errors import AssetCatalogNotFoundError
from loopora.asset_catalog_inputs import (
    RoleDefinitionPayloadInput,
    role_definition_payload_input_from_args as _role_definition_payload_input_from_args,
)
from loopora.asset_catalog_role_payloads import (
    ensure_unique_role_definition_prompt_ref,
    normalize_role_definition_payload,
)
from loopora.strategy_source import normalize_strategy_archetype
from loopora.utils import make_id


class RoleDefinitionAssetCatalogMixin:
    def list_role_definitions(self) -> list[dict]:
        custom_records = [
            self._decorate_role_definition(record, source="custom")
            for record in self.repository.list_role_definitions()
        ]
        return custom_records + self._clone_records(self._builtin_role_definitions)

    def get_role_definition(self, role_definition_id: str) -> dict:
        definition_key = str(role_definition_id or "").strip()
        if not definition_key:
            raise ValueError("role_definition_id is required")
        if definition_key.startswith("builtin:"):
            for record in self._builtin_role_definitions:
                if record["id"] == definition_key:
                    return deepcopy(record)
            raise AssetCatalogNotFoundError(f"unknown built-in role definition: {definition_key}")
        record = self.repository.get_role_definition(definition_key)
        if not record:
            raise AssetCatalogNotFoundError(f"unknown role definition: {definition_key}")
        return self._decorate_role_definition(record, source="custom")

    def create_role_definition(
        self,
        request: RoleDefinitionPayloadInput | None = None,
        **raw_payload: object,
    ) -> dict:
        role_definition_id = make_id("role")
        payload_input = _role_definition_payload_input_from_args(
            request,
            raw_payload,
            role_definition_id=role_definition_id,
        )
        payload = normalize_role_definition_payload(payload_input)
        ensure_unique_role_definition_prompt_ref(
            payload["prompt_ref"],
            builtin_records=self._builtin_role_definitions,
            custom_records=self.repository.list_role_definitions(),
        )
        role_definition = self.repository.create_role_definition(
            {
                "id": role_definition_id,
                **payload,
            }
        )
        return self._decorate_role_definition(role_definition, source="custom")

    def update_role_definition(
        self,
        role_definition_id: str,
        request: RoleDefinitionPayloadInput | None = None,
        **raw_payload: object,
    ) -> dict:
        existing = self.get_role_definition(role_definition_id)
        if existing.get("source") == "builtin":
            raise ValueError("built-in role definitions cannot be updated in place")
        existing_prompt_ref = str(existing.get("prompt_ref", "")).strip()
        payload_input = _role_definition_payload_input_from_args(
            request,
            raw_payload,
            role_definition_id=role_definition_id,
            existing_prompt_ref=existing_prompt_ref,
        )
        normalized_archetype = normalize_strategy_archetype(payload_input.archetype)
        if normalized_archetype != str(existing.get("archetype", "")).strip():
            raise ValueError("saved role definitions cannot change archetype")
        normalized_prompt_ref = str(payload_input.prompt_ref).strip() or existing_prompt_ref
        if normalized_prompt_ref != existing_prompt_ref:
            raise ValueError("saved role definitions cannot change prompt_ref")
        payload = normalize_role_definition_payload(
            replace(
                payload_input,
                archetype=normalized_archetype,
                prompt_ref=normalized_prompt_ref,
            )
        )
        ensure_unique_role_definition_prompt_ref(
            payload["prompt_ref"],
            builtin_records=self._builtin_role_definitions,
            custom_records=self.repository.list_role_definitions(),
            exclude_role_definition_id=role_definition_id,
        )
        updated = self.repository.update_role_definition(role_definition_id, payload)
        if not updated:
            raise AssetCatalogNotFoundError(f"unknown role definition: {role_definition_id}")
        return self._decorate_role_definition(updated, source="custom")

    def delete_role_definition(self, role_definition_id: str) -> dict:
        existing = self.get_role_definition(role_definition_id)
        if existing.get("source") == "builtin":
            raise ValueError("built-in role definitions cannot be deleted")
        if not self.repository.delete_role_definition(role_definition_id):
            raise AssetCatalogNotFoundError(f"unknown role definition: {role_definition_id}")
        return {"id": role_definition_id, "deleted": True}

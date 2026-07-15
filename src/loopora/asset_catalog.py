from __future__ import annotations

from copy import deepcopy
from typing import Any

from loopora.db import LooporaRepository
from loopora.strategy_source import strategy_source_from_record
from loopora.utils import make_id



from loopora.strategy_source import (
    StrategySourceError,
    normalize_strategy_prompt_ref,
    strategy_source_warnings,
)

from loopora.strategy_source import (
    STRATEGY_SOURCE_ARCHETYPES,
    build_preset_strategy_source,
    builtin_strategy_prompt_markdown,
    default_strategy_role_execution_settings,
    resolve_strategy_prompt_files,
    strategy_archetype_display_name,
    strategy_source_preset_copy,
    strategy_source_preset_names,
)

from collections.abc import Callable

from dataclasses import dataclass


from loopora.strategy_source import (
    normalize_strategy_source,
)


from dataclasses import replace




from loopora.strategy_source import normalize_strategy_archetype


import re

from collections.abc import Iterable, Mapping


from loopora.strategy_source import (
    normalize_strategy_role_execution_settings,
    validate_strategy_prompt_markdown,
)


from typing import cast




from loopora.strategy_source import (
    STRATEGY_ROLE_EXECUTION_FIELDS,
    STRATEGY_ROLE_POSTURE_FIELDS,
)

@dataclass(frozen=True)
class RoleSnapshotDefinition:
    role: dict
    definition: Mapping[str, object]
    role_definition_id: str
    role_label: str

def hydrate_strategy_role_snapshots(
    strategy_source: dict | None,
    prompt_files: dict | None,
    *,
    get_role_definition: Callable[[str], Mapping[str, object]],
) -> tuple[dict | None, dict[str, str] | None]:
    if strategy_source is None:
        return None, dict(prompt_files or {}) if prompt_files is not None else None

    hydrated_strategy_source = deepcopy(strategy_source)
    raw_roles = hydrated_strategy_source.get("roles")
    if not isinstance(raw_roles, list):
        return hydrated_strategy_source, dict(prompt_files or {}) if prompt_files is not None else None

    hydrated_prompt_files = dict(prompt_files or {})
    hydrated_strategy_source["roles"] = [
        _hydrate_strategy_role_snapshot(
            raw_role,
            hydrated_prompt_files=hydrated_prompt_files,
            get_role_definition=get_role_definition,
        )
        for raw_role in raw_roles
    ]
    return hydrated_strategy_source, hydrated_prompt_files

def _hydrate_strategy_role_snapshot(
    raw_role: object,
    *,
    hydrated_prompt_files: dict[str, str],
    get_role_definition: Callable[[str], Mapping[str, object]],
) -> object:
    if not isinstance(raw_role, dict):
        return raw_role
    role = dict(raw_role)
    role_definition_id = str(role.get("role_definition_id", "")).strip()
    if not role_definition_id:
        return role

    snapshot = RoleSnapshotDefinition(
        role=role,
        definition=get_role_definition(role_definition_id),
        role_definition_id=role_definition_id,
        role_label=str(role.get("id", "")).strip() or role_definition_id,
    )
    _hydrate_role_snapshot_fields(snapshot)
    _hydrate_role_prompt_file(snapshot, hydrated_prompt_files=hydrated_prompt_files)
    return role

def _hydrate_role_snapshot_fields(snapshot: RoleSnapshotDefinition) -> None:
    for field in ("archetype", "prompt_ref", *STRATEGY_ROLE_EXECUTION_FIELDS):
        _hydrate_role_snapshot_field(snapshot, field=field)
    if "name" not in snapshot.role:
        snapshot.role["name"] = snapshot.definition.get("name", "")
    for field in STRATEGY_ROLE_POSTURE_FIELDS:
        if field not in snapshot.role:
            snapshot.role[field] = snapshot.definition.get(field, "")

def _hydrate_role_snapshot_field(snapshot: RoleSnapshotDefinition, *, field: str) -> None:
    if field in snapshot.role:
        provided_value = _canonical_role_snapshot_field(field, snapshot.role.get(field))
        expected_value = _canonical_role_snapshot_field(field, snapshot.definition.get(field))
        if provided_value != expected_value:
            raise StrategySourceError(
                f"workflow role {snapshot.role_label} conflicts with role_definition_id "
                f"{snapshot.role_definition_id} on {field}"
            )
    if field not in snapshot.role:
        snapshot.role[field] = snapshot.definition.get(field, "")

def _hydrate_role_prompt_file(
    snapshot: RoleSnapshotDefinition,
    *,
    hydrated_prompt_files: dict[str, str],
) -> None:
    prompt_ref = str(snapshot.role.get("prompt_ref", "")).strip()
    if not prompt_ref:
        return
    prompt_markdown = str(snapshot.definition.get("prompt_markdown", ""))
    if prompt_ref not in hydrated_prompt_files:
        if prompt_markdown:
            hydrated_prompt_files[prompt_ref] = prompt_markdown
        return
    provided_prompt_markdown = hydrated_prompt_files[prompt_ref]
    if prompt_markdown and _canonical_prompt_markdown(provided_prompt_markdown) != _canonical_prompt_markdown(prompt_markdown):
        raise StrategySourceError(
            f"workflow role {snapshot.role_label} conflicts with role_definition_id "
            f"{snapshot.role_definition_id} on prompt_markdown"
        )

def _canonical_role_snapshot_field(field: str, value: object) -> object:
    if field == "archetype":
        return normalize_strategy_archetype(str(value or ""))
    if field == "prompt_ref":
        raw_prompt_ref = str(value or "").strip()
        return normalize_strategy_prompt_ref(raw_prompt_ref) if raw_prompt_ref else ""
    if field == "command_args_text":
        return str(value or "")
    return str(value or "").strip()

def _canonical_prompt_markdown(markdown: object) -> str:
    return str(markdown or "").replace("\r\n", "\n").replace("\r", "\n").strip()

@dataclass(frozen=True, kw_only=True)
class RoleDefinitionPayloadInput:
    name: str
    archetype: str
    prompt_markdown: str
    description: str = ""
    posture_notes: str = ""
    prompt_ref: str = ""
    executor_kind: str = "codex"
    executor_mode: str = "preset"
    command_cli: str = ""
    command_args_text: str = ""
    model: str = ""
    reasoning_effort: str = ""
    role_definition_id: str = ""
    existing_prompt_ref: str = ""

@dataclass(frozen=True, kw_only=True)
class OrchestrationPayloadInput:
    name: str
    description: str = ""
    strategy_source: dict | None = None
    prompt_files: dict | None = None
    role_models: dict | None = None

    @property
    def workflow(self) -> dict | None:
        return self.strategy_source

def role_definition_payload_input_from_args(
    request: RoleDefinitionPayloadInput | None,
    raw_payload: dict[str, object],
    *,
    role_definition_id: str,
    existing_prompt_ref: str = "",
) -> RoleDefinitionPayloadInput:
    if request is not None:
        if raw_payload:
            raise TypeError("role definition request object cannot be combined with keyword fields")
        return replace(
            request,
            role_definition_id=role_definition_id,
            existing_prompt_ref=existing_prompt_ref,
        )

    fields = dict(raw_payload)
    payload_input = RoleDefinitionPayloadInput(
        name=_required_role_definition_field(fields, "name"),
        archetype=_required_role_definition_field(fields, "archetype"),
        prompt_markdown=_required_role_definition_field(fields, "prompt_markdown"),
        description=fields.pop("description", ""),
        posture_notes=fields.pop("posture_notes", ""),
        prompt_ref=fields.pop("prompt_ref", ""),
        executor_kind=fields.pop("executor_kind", "codex"),
        executor_mode=fields.pop("executor_mode", "preset"),
        command_cli=fields.pop("command_cli", ""),
        command_args_text=fields.pop("command_args_text", ""),
        model=fields.pop("model", ""),
        reasoning_effort=fields.pop("reasoning_effort", ""),
        role_definition_id=role_definition_id,
        existing_prompt_ref=existing_prompt_ref,
    )
    if fields:
        unexpected_fields = ", ".join(sorted(fields))
        raise TypeError(f"unexpected role definition fields: {unexpected_fields}")
    return payload_input

def orchestration_payload_input_from_args(
    request: OrchestrationPayloadInput | None,
    raw_payload: dict[str, object],
) -> OrchestrationPayloadInput:
    if request is not None:
        if raw_payload:
            raise TypeError("orchestration request object cannot be combined with keyword fields")
        return request

    fields = dict(raw_payload)
    try:
        name = fields.pop("name")
    except KeyError as exc:
        raise TypeError("missing orchestration field: name") from exc
    payload_input = OrchestrationPayloadInput(
        name=name,
        description=fields.pop("description", ""),
        strategy_source=_pop_strategy_source_payload(fields),
        prompt_files=fields.pop("prompt_files", None),
        role_models=fields.pop("role_models", None),
    )
    if fields:
        unexpected_fields = ", ".join(sorted(fields))
        raise TypeError(f"unexpected orchestration fields: {unexpected_fields}")
    return payload_input

def strategy_source_from_legacy_fields(strategy_source: dict | None, legacy_fields: dict[str, Any]) -> dict | None:
    workflow = legacy_fields.pop("workflow", _MISSING)
    if legacy_fields:
        unexpected_fields = ", ".join(sorted(legacy_fields))
        raise TypeError(f"unexpected orchestration fields: {unexpected_fields}")
    if strategy_source is not None and workflow is not _MISSING:
        raise TypeError("orchestration fields strategy_source and workflow cannot both be provided")
    return strategy_source if workflow is _MISSING else cast(dict | None, workflow)

_MISSING = object()

def _required_role_definition_field(fields: dict[str, object], field: str) -> object:
    try:
        return fields.pop(field)
    except KeyError as exc:
        raise TypeError(f"missing role definition field: {field}") from exc

def _pop_strategy_source_payload(fields: dict[str, object]) -> object:
    strategy_source = fields.pop("strategy_source", _MISSING)
    workflow = fields.pop("workflow", _MISSING)
    if strategy_source is not _MISSING and workflow is not _MISSING:
        raise TypeError("orchestration fields strategy_source and workflow cannot both be provided")
    if strategy_source is not _MISSING:
        return strategy_source
    if workflow is not _MISSING:
        return workflow
    return None

_orchestration_payload_input_from_args = orchestration_payload_input_from_args
_strategy_source_from_legacy_fields = strategy_source_from_legacy_fields
_role_definition_payload_input_from_args = role_definition_payload_input_from_args

def normalize_role_definition_payload(payload_input: RoleDefinitionPayloadInput) -> dict:
    normalized = {
        "name": str(payload_input.name).strip(),
        "description": str(payload_input.description).strip(),
        "prompt_markdown": str(payload_input.prompt_markdown),
        "posture_notes": str(payload_input.posture_notes or "").strip(),
    }
    if not normalized["name"]:
        raise ValueError("name is required")
    normalized["archetype"] = normalize_strategy_archetype(payload_input.archetype)
    resolved_prompt_ref = (
        str(payload_input.prompt_ref).strip()
        or str(payload_input.existing_prompt_ref).strip()
        or _auto_prompt_ref(
            name=normalized["name"],
            archetype=normalized["archetype"],
            role_definition_id=payload_input.role_definition_id,
        )
    )
    normalized["prompt_ref"] = normalize_strategy_prompt_ref(resolved_prompt_ref)
    validate_strategy_prompt_markdown(normalized["prompt_markdown"], expected_archetype=normalized["archetype"])
    normalized.update(
        normalize_strategy_role_execution_settings(
            {
                "executor_kind": payload_input.executor_kind,
                "executor_mode": payload_input.executor_mode,
                "command_cli": payload_input.command_cli,
                "command_args_text": payload_input.command_args_text,
                "model": payload_input.model,
                "reasoning_effort": payload_input.reasoning_effort,
            }
        )
    )
    return normalized

def ensure_unique_role_definition_prompt_ref(
    prompt_ref: str,
    *,
    builtin_records: Iterable[Mapping[str, object]],
    custom_records: Iterable[Mapping[str, object]],
    exclude_role_definition_id: str = "",
) -> None:
    try:
        normalized_prompt_ref = normalize_strategy_prompt_ref(prompt_ref)
    except StrategySourceError as exc:
        raise ValueError(str(exc)) from exc
    excluded_id = str(exclude_role_definition_id or "").strip()
    for record in builtin_records:
        if record["id"] != excluded_id and str(record.get("prompt_ref", "")).strip() == normalized_prompt_ref:
            raise ValueError(f"prompt_ref already in use: {normalized_prompt_ref}")
    for record in custom_records:
        if record["id"] != excluded_id and str(record.get("prompt_ref", "")).strip() == normalized_prompt_ref:
            raise ValueError(f"prompt_ref already in use: {normalized_prompt_ref}")

def _auto_prompt_ref(*, name: str, archetype: str, role_definition_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(name).strip().lower()).strip("-")
    if not slug:
        slug = archetype
    suffix = str(role_definition_id).split("_")[-1]
    return f"{slug}-{suffix}.md"

class AssetCatalogError(ValueError):
    """Base error for strategy asset catalog validation failures."""

class AssetCatalogNotFoundError(AssetCatalogError):
    """Raised when a stable role definition or orchestration asset is missing."""

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

@dataclass(frozen=True)
class OrchestrationResolutionRequest:
    orchestration_id: str | None
    workflow: dict | None
    prompt_files: dict | None
    role_models: dict | None
    builtin_orchestrations: list[dict]
    get_orchestration: Callable[[str], dict]
    get_role_definition: Callable[[str], dict]
    not_found_errors: tuple[type[Exception], ...] = ()

def resolve_orchestration_input(request: OrchestrationResolutionRequest) -> dict:
    orchestration_id = request.orchestration_id
    workflow = request.workflow
    prompt_files = request.prompt_files
    role_models = request.role_models
    builtin_orchestrations = request.builtin_orchestrations
    get_orchestration = request.get_orchestration
    not_found_errors = request.not_found_errors

    if orchestration_id and workflow is None and not prompt_files:
        orchestration = request.get_orchestration(orchestration_id)
        hydrated_strategy_source, hydrated_prompt_files = hydrate_strategy_role_snapshots(
            strategy_source_from_record(orchestration) or {},
            orchestration.get("prompt_files_json") or {},
            get_role_definition=request.get_role_definition,
        )
        normalized_strategy_source = normalize_strategy_source(hydrated_strategy_source, role_models=role_models)
        resolved_prompt_files = resolve_strategy_prompt_files(
            normalized_strategy_source,
            hydrated_prompt_files,
        )
        return {
            "id": orchestration["id"],
            "name": orchestration["name"],
            "workflow": normalized_strategy_source,
            "prompt_files": resolved_prompt_files,
        }

    hydrated_strategy_source, hydrated_prompt_files = hydrate_strategy_role_snapshots(
        workflow,
        prompt_files,
        get_role_definition=request.get_role_definition,
    )
    normalized_strategy_source = normalize_strategy_source(hydrated_strategy_source, role_models=role_models)
    resolved_prompt_files = resolve_strategy_prompt_files(normalized_strategy_source, hydrated_prompt_files)
    derived_id = str(orchestration_id or "").strip()
    derived_name = _orchestration_name_for_id(
        derived_id,
        get_orchestration=get_orchestration,
        not_found_errors=not_found_errors,
    )
    if not derived_id and normalized_strategy_source.get("preset"):
        derived_id = f"builtin:{normalized_strategy_source['preset']}"
        derived_name = _builtin_orchestration_name(
            derived_id,
            builtin_orchestrations=builtin_orchestrations,
            default_name=normalized_strategy_source["preset"],
        )
    return {
        "id": derived_id,
        "name": derived_name,
        "workflow": normalized_strategy_source,
        "prompt_files": resolved_prompt_files,
    }

def _orchestration_name_for_id(
    orchestration_id: str,
    *,
    get_orchestration: Callable[[str], dict],
    not_found_errors: tuple[type[Exception], ...],
) -> str:
    if not orchestration_id:
        return ""
    try:
        return str(get_orchestration(orchestration_id).get("name") or "")
    except not_found_errors:
        return ""

def _builtin_orchestration_name(
    orchestration_id: str,
    *,
    builtin_orchestrations: list[dict],
    default_name: object,
) -> str:
    return next(
        (
            str(record.get("name") or "")
            for record in builtin_orchestrations
            if record.get("id") == orchestration_id
        ),
        str(default_name),
    )

_resolve_orchestration_input = resolve_orchestration_input

def build_builtin_orchestration_records() -> list[dict]:
    records = []
    for preset_name in strategy_source_preset_names(include_hidden=True):
        strategy_source = build_preset_strategy_source(preset_name)
        prompt_files = resolve_strategy_prompt_files(strategy_source)
        copy = strategy_source_preset_copy(preset_name)
        parallel_groups = strategy_parallel_groups(strategy_source)
        records.append(
            {
                "id": f"builtin:{preset_name}",
                "name": copy["label_en"],
                "description": copy["description_en"],
                "description_zh": copy["description_zh"],
                "description_en": copy["description_en"],
                "scenario_zh": copy["scenario_zh"],
                "scenario_en": copy["scenario_en"],
                "choice_zh": copy["choice_zh"],
                "choice_en": copy["choice_en"],
                "decision_zh": copy["decision_zh"],
                "decision_en": copy["decision_en"],
                "spec_practice_summary_zh": copy["spec_practice_summary_zh"],
                "spec_practice_summary_en": copy["spec_practice_summary_en"],
                "spec_practice_markdown_zh": copy["spec_practice_markdown_zh"],
                "spec_practice_markdown_en": copy["spec_practice_markdown_en"],
                "visible": copy["visible"] == "true",
                "source": "builtin",
                "preset": preset_name,
                "editable": False,
                "deletable": False,
                "strategy_source": strategy_source,
                "workflow_json": strategy_source,
                "parallel_groups": parallel_groups,
                "parallel_group_count": len(parallel_groups),
                "prompt_files_json": prompt_files,
                "workflow_warnings": strategy_source_warnings(strategy_source),
            }
        )
    return records

def build_builtin_role_definition_records() -> list[dict]:
    descriptions = {
        "builder": "Edits the workspace and pushes implementation forward.",
        "inspector": "Collects evidence, checks, and benchmark results.",
        "gatekeeper": "Decides whether the evidence is strong enough to pass.",
        "guide": "Suggests the next direction when progress stalls.",
        "custom": "A low-permission custom support role that can read, analyze, and recommend, but cannot close the run.",
    }
    records = []
    for archetype in STRATEGY_SOURCE_ARCHETYPES:
        prompt_ref = {
            "gatekeeper": "gatekeeper.md",
        }.get(archetype, f"{archetype}.md")
        default_name = strategy_archetype_display_name(archetype, locale="en")
        if archetype == "custom":
            default_name = "Custom (Restricted)"
        records.append(
            {
                "id": f"builtin:{archetype}",
                "name": default_name,
                "description": descriptions.get(archetype, ""),
                "archetype": archetype,
                "prompt_ref": prompt_ref,
                "prompt_markdown": builtin_strategy_prompt_markdown(prompt_ref),
                "posture_notes": "",
                **default_strategy_role_execution_settings(),
                "source": "builtin",
                "editable": False,
                "deletable": False,
            }
        )
    return records

def strategy_parallel_groups(strategy_source: dict | None) -> list[str]:
    if not isinstance(strategy_source, dict):
        return []
    counts: dict[str, int] = {}
    for step in list(strategy_source.get("steps") or []):
        if not isinstance(step, dict):
            continue
        group = str(step.get("parallel_group") or "").strip()
        if group:
            counts[group] = counts.get(group, 0) + 1
    return [group for group, count in counts.items() if count >= 2]

def clone_asset_records(records: list[dict]) -> list[dict]:
    return [deepcopy(record) for record in records]

def decorate_orchestration_record(record: dict, *, source: str) -> dict:
    decorated = dict(record)
    decorated["prompt_files_json"] = sanitize_persisted_prompt_files(decorated.get("prompt_files_json"))
    decorated["source"] = source
    decorated["editable"] = source == "custom"
    decorated["deletable"] = source == "custom"
    strategy_source = strategy_source_from_record(decorated) or {}
    decorated["strategy_source"] = strategy_source
    decorated["workflow_warnings"] = strategy_source_warnings(strategy_source)
    decorated["parallel_groups"] = strategy_parallel_groups(strategy_source)
    decorated["parallel_group_count"] = len(decorated["parallel_groups"])
    return decorated

def decorate_role_definition_record(record: dict, *, source: str) -> dict:
    decorated = dict(record)
    decorated["source"] = source
    decorated["editable"] = source == "custom"
    decorated["deletable"] = source == "custom"
    return decorated

def sanitize_persisted_prompt_files(prompt_files: object) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for prompt_ref, markdown_text in dict(prompt_files or {}).items():
        candidate = str(prompt_ref).strip()
        if not candidate:
            continue
        try:
            normalized_prompt_ref = normalize_strategy_prompt_ref(candidate)
        except StrategySourceError:
            continue
        sanitized[normalized_prompt_ref] = str(markdown_text or "")
    return sanitized


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

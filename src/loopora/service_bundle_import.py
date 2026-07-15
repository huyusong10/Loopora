from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from loopora.bundles import BundleError, bundle_to_yaml, normalize_bundle_identifier
from loopora.service_bundle_import_cleanup import (
    BundleImportRollbackState,
    BundleImportTarget,
    ServiceBundleImportCleanupMixin,
)
from loopora.service_types import LooporaConflictError, LooporaError
from loopora.utils import make_id

class ServiceBundleImportMixin(ServiceBundleImportCleanupMixin):
    def _import_normalized_bundle(
        self,
        bundle: dict,
        *,
        replace_bundle_id: str | None = None,
        imported_from_path: str,
    ) -> dict:
        target = self._prepare_bundle_import_target(
            bundle,
            replace_bundle_id=replace_bundle_id,
            imported_from_path=imported_from_path,
        )
        state = BundleImportRollbackState(target=target)
        try:
            target.bundle_dir.mkdir(parents=True, exist_ok=True)
            spec_path = self._write_imported_bundle_spec(target.target_bundle_id, bundle)
            role_definition_id_by_key = self._create_imported_bundle_roles(
                bundle,
                prompt_ref_namespace=target.prompt_ref_namespace,
                created_role_ids=state.created_role_ids,
            )
            workflow_payload = self._bundle_import_workflow_payload(bundle, role_definition_id_by_key)
            orchestration = self.create_orchestration(
                name=bundle["metadata"]["name"],
                description=bundle["metadata"].get("description", ""),
                strategy_source=workflow_payload,
                prompt_files=None,
                role_models=None,
            )
            state.orchestration_id = orchestration["id"]
            loop_settings = bundle["loop"]
            loop = self._create_imported_bundle_loop(
                loop_settings,
                spec_path=spec_path,
                orchestration_id=state.orchestration_id,
            )
            state.loop_id = loop["id"]
            payload = self._bundle_import_payload(target, bundle, loop_settings, state)
            self._write_imported_bundle_yaml(target.target_bundle_id, payload, state.loop_id)
            if target.existing:
                state.saved = self.repository.replace_bundle_graph(target.target_bundle_id, payload)
                state.saved = self.repository.get_bundle(target.target_bundle_id) if state.saved else None
            else:
                state.saved = self.repository.create_bundle(payload)
            if not state.saved:
                raise LooporaError(f"failed to persist bundle: {target.target_bundle_id}")
            if target.existing:
                self._delete_replaced_bundle_artifact_paths(target.target_bundle_id, target.old_local_paths)
            state.committed = True
            return self.get_bundle(state.saved["id"])
        except Exception:
            self._rollback_failed_bundle_import(state)
            raise
        finally:
            self._cleanup_bundle_import_backup_dir(target)

    def _prepare_bundle_import_target(
        self,
        bundle: dict,
        *,
        replace_bundle_id: str | None,
        imported_from_path: str,
    ) -> BundleImportTarget:
        if replace_bundle_id is not None:
            try:
                target_bundle_id = normalize_bundle_identifier(
                    replace_bundle_id,
                    field_name="bundle replace_bundle_id",
                )
            except BundleError as exc:
                raise LooporaError(str(exc)) from exc
        else:
            target_bundle_id = str(bundle["metadata"].get("bundle_id") or make_id("bundle")).strip()
        existing = self.repository.get_bundle(target_bundle_id)
        if existing and not replace_bundle_id:
            raise LooporaConflictError(f"bundle already exists: {target_bundle_id}")
        old_local_paths = self._preflight_existing_bundle_graph(existing) if existing else []
        bundle_dir = self._bundle_dir(target_bundle_id)
        backup_dir = self._backup_bundle_dir(bundle_dir) if existing else None
        prompt_ref_namespace = target_bundle_id if not existing else f"{target_bundle_id}/{make_id('replace')}"
        return BundleImportTarget(
            target_bundle_id=target_bundle_id,
            existing=existing,
            old_local_paths=old_local_paths,
            bundle_dir=bundle_dir,
            backup_dir=backup_dir,
            prompt_ref_namespace=prompt_ref_namespace,
            imported_from_path=imported_from_path,
        )

    def _bundle_import_payload(
        self,
        target: BundleImportTarget,
        bundle: dict,
        loop_settings: dict,
        state: BundleImportRollbackState,
    ) -> dict:
        return {
            "id": target.target_bundle_id,
            "name": bundle["metadata"]["name"],
            "description": bundle["metadata"].get("description", ""),
            "collaboration_summary": bundle["collaboration_summary"],
            "workdir": loop_settings["workdir"],
            "loop_id": state.loop_id,
            "orchestration_id": state.orchestration_id,
            "role_definition_ids": state.created_role_ids,
            "source_bundle_id": "",
            "revision": int((target.existing or {}).get("revision", 1) or 1) if target.existing else 1,
            "imported_from_path": target.imported_from_path,
        }

    def _write_imported_bundle_spec(self, target_bundle_id: str, bundle: dict) -> Path:
        spec_path = self._bundle_spec_path(target_bundle_id)
        spec_path.write_text(str(bundle["spec"]["markdown"]), encoding="utf-8")
        return spec_path

    def _create_imported_bundle_roles(
        self,
        bundle: dict,
        *,
        prompt_ref_namespace: str,
        created_role_ids: list[str],
    ) -> dict[str, str]:
        role_definition_id_by_key: dict[str, str] = {}
        for entry in bundle["role_definitions"]:
            imported = self.create_role_definition(
                name=entry["name"],
                description=entry.get("description", ""),
                archetype=entry["archetype"],
                prompt_ref=self._imported_prompt_ref(prompt_ref_namespace, entry["key"], entry["archetype"]),
                prompt_markdown=entry["prompt_markdown"],
                posture_notes=entry.get("posture_notes", ""),
                executor_kind=entry["executor_kind"],
                executor_mode=entry["executor_mode"],
                command_cli=entry.get("command_cli", ""),
                command_args_text=entry.get("command_args_text", ""),
                model=entry.get("model", ""),
                reasoning_effort=entry.get("reasoning_effort", ""),
            )
            role_definition_id_by_key[entry["key"]] = imported["id"]
            created_role_ids.append(imported["id"])
        return role_definition_id_by_key

    @staticmethod
    def _imported_prompt_ref(bundle_id: str, role_key: str, archetype: str) -> str:
        normalized_key = "".join(char if char.isalnum() else "-" for char in role_key.lower()).strip("-") or archetype
        return f"bundles/{bundle_id}/{normalized_key}.md"

    @staticmethod
    def _bundle_import_workflow_payload(bundle: dict, role_definition_id_by_key: dict[str, str]) -> dict:
        workflow_payload = {
            "version": bundle["workflow"]["version"],
            "preset": bundle["workflow"]["preset"],
            "collaboration_intent": bundle["workflow"].get("collaboration_intent", ""),
            "roles": [
                {
                    "id": entry["id"],
                    "role_definition_id": role_definition_id_by_key[entry["role_definition_key"]],
                }
                for entry in bundle["workflow"]["roles"]
            ],
            "steps": list(bundle["workflow"]["steps"]),
        }
        if bundle["workflow"].get("controls"):
            workflow_payload["controls"] = deepcopy(bundle["workflow"].get("controls") or [])
        return workflow_payload

    def _create_imported_bundle_loop(self, loop_settings: dict, *, spec_path: Path, orchestration_id: str) -> dict:
        return self.create_loop(
            name=loop_settings["name"],
            spec_path=spec_path,
            workdir=Path(loop_settings["workdir"]),
            model=loop_settings["model"],
            reasoning_effort=loop_settings["reasoning_effort"],
            max_iters=loop_settings["max_iters"],
            max_role_retries=loop_settings["max_role_retries"],
            delta_threshold=loop_settings["delta_threshold"],
            trigger_window=loop_settings["trigger_window"],
            regression_window=loop_settings["regression_window"],
            executor_kind=loop_settings["executor_kind"],
            executor_mode=loop_settings["executor_mode"],
            command_cli=loop_settings["command_cli"],
            command_args_text=loop_settings["command_args_text"],
            orchestration_id=orchestration_id,
            completion_mode=loop_settings["completion_mode"],
            iteration_interval_seconds=loop_settings["iteration_interval_seconds"],
        )

    def _write_imported_bundle_yaml(self, target_bundle_id: str, payload: dict, loop_id: str) -> None:
        export_payload = self.derive_bundle_from_loop(
            loop_id,
            bundle_id=target_bundle_id,
            name=payload["name"],
            description=payload["description"],
            collaboration_summary=payload["collaboration_summary"],
        )
        self._bundle_yaml_path(target_bundle_id).write_text(bundle_to_yaml(export_payload), encoding="utf-8")

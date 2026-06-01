from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from loopora.evidence_coverage_targets import with_coverage_targets
from loopora.run_artifacts import write_json_with_mirrors
from loopora.service_asset_common import normalize_role_models
from loopora.service_types import LooporaError, LooporaNotFoundError
from loopora.specs import compile_markdown_spec
from loopora.strategy_source import (
    STRATEGY_ROLE_EXECUTION_FIELDS,
    STRATEGY_ROLE_POSTURE_FIELDS,
    strategy_source_from_record,
    strategy_source_has_finish_gatekeeper_step,
)
from loopora.utils import write_json


class ServiceBundleLoopSnapshotMixin:
    def _sync_bundle_loop_snapshot(self, bundle_id: str) -> dict | None:
        snapshot = self._build_bundle_loop_snapshot(bundle_id)
        if snapshot is None:
            return None
        return self._apply_bundle_loop_snapshot(snapshot)

    def _build_bundle_loop_snapshot(
        self,
        bundle_id: str,
        *,
        spec_markdown: str | None = None,
    ) -> dict | None:
        bundle = self.repository.get_bundle(bundle_id)
        if not bundle:
            raise LooporaNotFoundError(f"unknown bundle: {bundle_id}")
        loop_id = str(bundle.get("loop_id", "") or "").strip()
        if not loop_id:
            return None
        loop = self.repository.get_loop(loop_id)
        if not loop:
            raise LooporaNotFoundError(f"unknown bundle loop: {loop_id}")

        spec_path = self._bundle_spec_path(bundle_id)
        if spec_markdown is None:
            if not spec_path.exists():
                raise LooporaError(f"bundle spec does not exist: {spec_path}")
            effective_spec_markdown, compiled_spec = self._read_and_compile_spec(spec_path)
        else:
            effective_spec_markdown = str(spec_markdown or "").strip() + "\n"
            compiled_spec = compile_markdown_spec(effective_spec_markdown)
        compiled_spec = with_coverage_targets(
            compiled_spec,
            completion_mode=str(loop.get("completion_mode", "gatekeeper")),
        )
        role_models = normalize_role_models(loop.get("role_models_json") or loop.get("role_models") or {})
        resolved_orchestration = self._resolve_bundle_orchestration_for_snapshot(bundle, role_models=role_models)
        normalized_workflow = resolved_orchestration["workflow"]
        if loop.get("completion_mode") == "gatekeeper" and not strategy_source_has_finish_gatekeeper_step(
            normalized_workflow
        ):
            raise LooporaError("gatekeeper completion mode requires a GateKeeper step that can finish the run")
        return {
            "bundle": bundle,
            "loop": loop,
            "loop_id": loop_id,
            "spec_path": spec_path,
            "spec_markdown": effective_spec_markdown,
            "compiled_spec": compiled_spec,
            "resolved_orchestration": resolved_orchestration,
        }

    def _apply_bundle_loop_snapshot(self, snapshot: dict) -> dict:
        loop = snapshot["loop"]
        loop_id = snapshot["loop_id"]
        spec_path = snapshot["spec_path"]
        spec_markdown = snapshot["spec_markdown"]
        compiled_spec = snapshot["compiled_spec"]
        resolved_orchestration = snapshot["resolved_orchestration"]
        self._persist_refreshed_bundle_orchestration(resolved_orchestration)

        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(spec_markdown, encoding="utf-8")
        loop_dir = self._ensure_loop_dir(Path(loop["workdir"]), loop_id)
        (loop_dir / "spec.md").write_text(spec_markdown, encoding="utf-8")
        write_json(loop_dir / "compiled_spec.json", compiled_spec)
        self._persist_prompt_files(loop_dir, resolved_orchestration["prompt_files"])
        write_json_with_mirrors(
            loop_dir / "strategy_source.json",
            resolved_orchestration["workflow"],
            mirror_paths=[loop_dir / "workflow.json"],
        )

        updated = self.repository.update_loop_contract(
            loop_id,
            {
                "orchestration_id": resolved_orchestration["id"],
                "orchestration_name": resolved_orchestration["name"],
                "spec_path": str(spec_path.resolve()),
                "spec_markdown": spec_markdown,
                "compiled_spec": compiled_spec,
                "workflow": resolved_orchestration["workflow"],
            },
        )
        if not updated:
            raise LooporaError(f"failed to update bundle loop snapshot: {loop_id}")
        return self._hydrate_loop_files(updated)

    def _resolve_bundle_orchestration_for_snapshot(self, bundle: dict, *, role_models: dict) -> dict:
        orchestration_id = str(bundle.get("orchestration_id", "") or "").strip()
        if not orchestration_id:
            raise LooporaError(f"bundle {bundle['id']} has no orchestration")
        orchestration = self.get_orchestration(orchestration_id)
        workflow, prompt_files = self._refresh_bundle_role_snapshots(
            workflow=strategy_source_from_record(orchestration) or {},
            prompt_files=orchestration.get("prompt_files_json") or {},
            role_definition_ids=[
                str(item).strip()
                for item in (bundle.get("role_definition_ids") or bundle.get("role_definition_ids_json") or [])
                if str(item).strip()
            ],
        )
        resolved = self._asset_call(
            self.asset_catalog.resolve_orchestration_input,
            orchestration_id=orchestration_id,
            workflow=workflow,
            prompt_files=prompt_files,
            role_models=role_models,
        )
        resolved["stored_orchestration"] = orchestration
        resolved["refreshed_workflow"] = workflow
        resolved["refreshed_prompt_files"] = prompt_files
        return resolved

    def _persist_refreshed_bundle_orchestration(self, resolved_orchestration: dict) -> None:
        orchestration = resolved_orchestration.get("stored_orchestration") or {}
        orchestration_id = str(resolved_orchestration.get("id", "") or "").strip()
        if not orchestration_id:
            return
        workflow = resolved_orchestration.get("refreshed_workflow") or {}
        prompt_files = resolved_orchestration.get("refreshed_prompt_files") or {}
        if workflow == (strategy_source_from_record(orchestration) or {}) and prompt_files == orchestration.get(
            "prompt_files_json"
        ):
            return
        self._asset_call(
            self.asset_catalog.update_orchestration,
            orchestration_id,
            name=orchestration["name"],
            description=orchestration.get("description", ""),
            strategy_source=workflow,
            prompt_files=prompt_files,
            role_models=None,
        )

    def _refresh_bundle_role_snapshots(
        self,
        *,
        workflow: dict,
        prompt_files: dict,
        role_definition_ids: list[str],
    ) -> tuple[dict, dict[str, str]]:
        refreshed_workflow = deepcopy(workflow)
        refreshed_prompt_files = dict(prompt_files or {})
        owned_role_ids = {str(item).strip() for item in role_definition_ids if str(item).strip()}
        refreshed_roles = []
        for raw_role in refreshed_workflow.get("roles", []):
            if not isinstance(raw_role, dict):
                refreshed_roles.append(raw_role)
                continue
            role = dict(raw_role)
            role_definition_id = str(role.get("role_definition_id", "") or "").strip()
            if role_definition_id in owned_role_ids:
                definition = self.get_role_definition(role_definition_id)
                for field in (
                    "name",
                    "archetype",
                    "prompt_ref",
                    *STRATEGY_ROLE_EXECUTION_FIELDS,
                    *STRATEGY_ROLE_POSTURE_FIELDS,
                ):
                    role[field] = definition.get(field, "")
                prompt_ref = str(definition.get("prompt_ref", "") or "").strip()
                if prompt_ref:
                    refreshed_prompt_files[prompt_ref] = str(definition.get("prompt_markdown", "") or "")
            refreshed_roles.append(role)
        refreshed_workflow["roles"] = refreshed_roles
        return refreshed_workflow, refreshed_prompt_files

from __future__ import annotations

from loopora.service_types import LooporaError


class ServiceBundleLinksMixin:
    def _hydrate_bundle_links(self, bundle: dict) -> dict:
        hydrated = dict(bundle)
        loop_id = str(hydrated.get("loop_id", "") or "").strip()
        orchestration_id = str(hydrated.get("orchestration_id", "") or "").strip()
        role_definition_ids = [str(item).strip() for item in hydrated.get("role_definition_ids_json", []) if str(item).strip()]
        hydrated["role_definition_ids"] = role_definition_ids
        hydrated["managed_dir"] = str(self._bundle_dir(hydrated["id"]))
        hydrated["bundle_yaml_path"] = str(self._bundle_yaml_path(hydrated["id"]))
        if loop_id:
            try:
                hydrated["loop"] = self.get_loop(loop_id)
            except LooporaError:
                hydrated["loop"] = None
        else:
            hydrated["loop"] = None
        if orchestration_id:
            try:
                hydrated["orchestration"] = self.get_orchestration(orchestration_id)
            except LooporaError:
                hydrated["orchestration"] = None
        else:
            hydrated["orchestration"] = None
        role_definitions = []
        for role_definition_id in role_definition_ids:
            try:
                role_definitions.append(self.get_role_definition(role_definition_id))
            except LooporaError:
                continue
        hydrated["role_definitions"] = role_definitions
        return hydrated

    def _bundle_record_for_loop_id(self, loop_id: str) -> dict | None:
        normalized = str(loop_id or "").strip()
        if not normalized:
            return None
        for bundle in self.repository.list_bundles():
            if str(bundle.get("loop_id", "") or "").strip() == normalized:
                return bundle
        return None

    def _bundle_record_for_orchestration_id(self, orchestration_id: str) -> dict | None:
        normalized = str(orchestration_id or "").strip()
        if not normalized:
            return None
        for bundle in self.repository.list_bundles():
            if str(bundle.get("orchestration_id", "") or "").strip() == normalized:
                return bundle
        return None

    def _bundle_record_for_role_definition_id(self, role_definition_id: str) -> dict | None:
        normalized = str(role_definition_id or "").strip()
        if not normalized:
            return None
        for bundle in self.repository.list_bundles():
            role_ids = [
                str(item).strip()
                for item in (bundle.get("role_definition_ids") or bundle.get("role_definition_ids_json") or [])
                if str(item).strip()
            ]
            if normalized in role_ids:
                return bundle
        return None

    def _touch_bundle_for_orchestration(self, orchestration_id: str) -> dict | None:
        bundle = self._bundle_record_for_orchestration_id(orchestration_id)
        if not bundle:
            return None
        return self.update_bundle(bundle["id"])

    def _touch_bundle_for_role_definition(self, role_definition_id: str) -> dict | None:
        bundle = self._bundle_record_for_role_definition_id(role_definition_id)
        if not bundle:
            return None
        return self.update_bundle(bundle["id"])

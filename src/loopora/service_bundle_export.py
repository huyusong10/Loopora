from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loopora.bundles import BundleError, bundle_to_yaml, normalize_bundle
from loopora.service_bundle_file_writes import write_bundle_text_atomically
from loopora.projections import LoopfileExportProjectionInput, build_loopfile_export_projection
from loopora.service_types import LooporaError
from loopora.strategy_source import normalize_strategy_source, strategy_source_from_record

PLAN_FILE_EXPORT_ERROR = "plan file could not be exported"
PLAN_FILE_OUTPUT_DIRECTORY_ERROR = "plan file output must be a file, not a directory"
PLAN_FILE_SAVE_ERROR = "plan file could not be saved"


@dataclass(frozen=True)
class BundleDeriveRequest:
    loop_id: str
    bundle_id: str = ""
    name: str | None = None
    description: str = ""
    collaboration_summary: str = ""
    source_bundle_id: str = ""
    revision: int = 1


def _derive_bundle_request_from_args(
    request: BundleDeriveRequest | str,
    raw_request: dict[str, object],
) -> BundleDeriveRequest:
    if isinstance(request, BundleDeriveRequest):
        if raw_request:
            raise TypeError("bundle derive request object cannot be combined with keyword fields")
        return request

    fields = dict(raw_request)
    derive_request = BundleDeriveRequest(
        loop_id=request,
        bundle_id=fields.pop("bundle_id", ""),
        name=fields.pop("name", None),
        description=fields.pop("description", ""),
        collaboration_summary=fields.pop("collaboration_summary", ""),
        source_bundle_id=fields.pop("source_bundle_id", ""),
        revision=fields.pop("revision", 1),
    )
    if fields:
        unexpected_fields = ", ".join(sorted(fields))
        raise TypeError(f"unexpected bundle derive request fields: {unexpected_fields}")
    return derive_request


class ServiceBundleExportMixin:
    def export_bundle(self, bundle_id: str) -> dict:
        bundle = self.get_bundle(bundle_id)
        return self.derive_bundle_from_loop(
            bundle["loop_id"],
            bundle_id=bundle["id"],
            name=bundle["name"],
            description=str(bundle.get("description", "")),
            collaboration_summary=str(bundle.get("collaboration_summary", "")),
        )

    def export_bundle_yaml(self, bundle_id: str) -> str:
        return bundle_to_yaml(self.export_bundle(bundle_id))

    def derive_bundle_from_loop(self, request: BundleDeriveRequest | str, **raw_request: object) -> dict:
        request = _derive_bundle_request_from_args(request, raw_request)
        loop_id = request.loop_id
        loop = self.get_loop(loop_id)
        strategy_source = normalize_strategy_source(strategy_source_from_record(loop) or {})
        prompt_files = dict(loop.get("prompt_files") or {})
        role_definition_by_id = {}
        for role in strategy_source.get("roles", []):
            role_definition_id = str(role.get("role_definition_id", "") or "").strip()
            if not role_definition_id or role_definition_id in role_definition_by_id:
                continue
            try:
                role_definition_by_id[role_definition_id] = self.get_role_definition(role_definition_id)
            except LooporaError:
                role_definition_by_id[role_definition_id] = None
        try:
            return normalize_bundle(
                build_loopfile_export_projection(
                    LoopfileExportProjectionInput(
                        loop=loop,
                        loop_id=loop_id,
                        strategy_source=strategy_source,
                        prompt_files=prompt_files,
                        role_definition_by_id=role_definition_by_id,
                        bundle_id=request.bundle_id,
                        name=request.name,
                        description=request.description,
                        collaboration_summary=request.collaboration_summary,
                    )
                )
            )
        except (BundleError, ValueError) as exc:
            raise LooporaError(str(exc)) from exc

    def write_bundle_file(self, bundle_id: str, path: Path) -> Path:
        return write_plan_file_yaml(path, self.export_bundle_yaml(bundle_id))

    def _sync_bundle_yaml(self, bundle_id: str) -> None:
        try:
            write_bundle_text_atomically(self._bundle_yaml_path(bundle_id), self.export_bundle_yaml(bundle_id))
        except OSError as exc:
            raise LooporaError(PLAN_FILE_SAVE_ERROR) from exc


def write_plan_file_yaml(path: Path, yaml_text: str) -> Path:
    target = path.expanduser()
    try:
        if target.is_dir():
            raise IsADirectoryError
        write_bundle_text_atomically(target, yaml_text)
    except IsADirectoryError as exc:
        raise LooporaError(PLAN_FILE_OUTPUT_DIRECTORY_ERROR) from exc
    except OSError as exc:
        raise LooporaError(PLAN_FILE_EXPORT_ERROR) from exc
    return target

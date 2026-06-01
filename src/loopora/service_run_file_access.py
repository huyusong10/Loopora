from __future__ import annotations

from pathlib import Path

from loopora.branding import state_dir_for_workdir
from loopora.file_previews import preview_existing_path
from loopora.service_types import LooporaError


class ServiceRunFileAccessMixin:
    def _file_root_base(self, run: dict, root: str) -> Path:
        workdir = Path(run["workdir"])
        if root == "workdir":
            return workdir
        if root == "loopora":
            base = state_dir_for_workdir(workdir)
            base.mkdir(parents=True, exist_ok=True)
            return base
        raise LooporaError("invalid file root")

    def _resolve_file_path(self, run_id: str, root: str, relative_path: str) -> tuple[Path, Path]:
        run = self.get_run(run_id)
        base = self._file_root_base(run, root)
        base_resolved = base.resolve()
        resolved = (base_resolved / relative_path).resolve()
        if not resolved.is_relative_to(base_resolved):
            raise LooporaError("requested path is outside the allowed root")
        if not resolved.exists():
            raise LooporaError(f"path does not exist: {resolved}")
        return base_resolved, resolved

    def preview_file(self, run_id: str, root: str, relative_path: str = "") -> dict:
        base, resolved = self._resolve_file_path(run_id, root, relative_path)
        return preview_existing_path(base=base, relative_path=relative_path, resolved=resolved)

    def download_file_path(self, run_id: str, root: str, relative_path: str = "") -> Path:
        _base, resolved = self._resolve_file_path(run_id, root, relative_path)
        if not resolved.is_file():
            raise LooporaError("path is not a file")
        return resolved

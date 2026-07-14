from __future__ import annotations

from collections.abc import Callable, MutableMapping
from pathlib import Path
from typing import Protocol


class AlignmentFactorySettings(Protocol):
    polling_interval_seconds: float
    role_idle_timeout_seconds: float
    stop_grace_period_seconds: float


class AlignmentFactoryService(Protocol):
    repository: object
    settings: AlignmentFactorySettings
    executor_factory: Callable[[], object]
    _threads: MutableMapping[str, object]

    def _bundle_preview_payload(self, bundle: dict, *, source_path: str = "", validation: dict | None = None) -> dict: ...

    def _mark_local_asset_cleanup_by_path(
        self,
        path: Path,
        *,
        operation: str = "local_asset_cleanup",
        owner_id: object = "",
    ) -> None: ...

    def create_alignment_session(self, *args: object, **raw_request: object) -> dict: ...

    def get_alignment_session(self, session_id: str) -> dict: ...

    def start_alignment_session_async(self, session_id: str) -> None: ...

    def retry_alignment_generation(self, session_id: str, **raw_settings: object) -> dict: ...

    def get_alignment_workdir_context(self, workdir: Path) -> dict: ...

    def export_bundle(self, bundle_id: str) -> dict: ...

    def derive_bundle_from_loop(self, request: object, **raw_request: object) -> dict: ...

    def get_loop(self, loop_id: str) -> dict: ...

    def list_loops(self) -> list[dict]: ...

    def get_run(self, run_id: str) -> dict: ...

    def import_bundle_text(
        self,
        raw_text: str,
        *,
        replace_bundle_id: str | None = None,
        imported_from_path: str = "",
    ) -> dict: ...

    def start_run(self, loop_id: str) -> dict: ...

    def start_run_async(self, run_id: str) -> None: ...

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from loopora.bundles import BundleError
from loopora.bundle_io import decode_bundle_text, read_bundle_file_text, resolve_bundle_file_path
from loopora.service import LooporaError
from loopora.web_workdir_recovery import (
    web_alignment_workdir_ready,
    web_bundle_import_workdir_recovery_payload,
)


def web_bundle_import_text_workdir_recovery(raw_text: str, *, action: str) -> dict[str, object] | None:
    try:
        bundle = decode_bundle_text(raw_text)
    except BundleError as exc:
        raise LooporaError(str(exc)) from exc
    return web_bundle_import_workdir_recovery(bundle, action=action)


def web_bundle_import_file_workdir_recovery(path: Path, *, action: str) -> dict[str, object] | None:
    try:
        bundle = decode_bundle_text(read_bundle_file_text(resolve_bundle_file_path(path)))
    except BundleError as exc:
        raise LooporaError(str(exc)) from exc
    return web_bundle_import_workdir_recovery(bundle, action=action)


def web_bundle_import_workdir_recovery(
    bundle: Mapping[str, object],
    *,
    action: str,
) -> dict[str, object] | None:
    loop = bundle.get("loop")
    if not isinstance(loop, Mapping):
        return None
    workdir = str(loop.get("workdir") or "").strip()
    if not web_alignment_workdir_ready(workdir):
        return web_bundle_import_workdir_recovery_payload(workdir, action=action)
    return None

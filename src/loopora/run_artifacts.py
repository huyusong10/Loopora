from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from loopora import run_artifact_io as _run_artifact_io
from loopora.run_artifact_catalog import (
    RUN_ARTIFACT_SPECS as RUN_ARTIFACT_SPECS,
    artifact_slug as artifact_slug,
    list_run_artifacts as list_run_artifacts,
)
from loopora.run_artifact_io import (
    INITIAL_STAGNATION_STATE as INITIAL_STAGNATION_STATE,
    append_jsonl_with_mirrors as append_jsonl_with_mirrors,
    read_jsonl as read_jsonl,
    read_stagnation_state as read_stagnation_state,
    write_text_with_mirrors as write_text_with_mirrors,
)
from loopora.run_artifact_layout import RunArtifactLayout as RunArtifactLayout, artifact_ref as artifact_ref
from loopora.run_artifact_layout import (
    INITIAL_LATEST_STATE as INITIAL_LATEST_STATE,
    initialize_run_artifact_layout as initialize_run_artifact_layout,
    legacy_role_output_alias_paths as legacy_role_output_alias_paths,
)
from loopora.utils import write_json


def write_json_with_mirrors(path: Path, payload: dict, *, mirror_paths: Iterable[Path] = ()) -> None:
    original_write_json = _run_artifact_io.write_json
    _run_artifact_io.write_json = write_json
    try:
        _run_artifact_io.write_json_with_mirrors(path, payload, mirror_paths=mirror_paths)
    finally:
        _run_artifact_io.write_json = original_write_json

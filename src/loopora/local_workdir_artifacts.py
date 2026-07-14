from __future__ import annotations

from pathlib import Path

from loopora.branding import state_dir_for_workdir
from loopora.workdir_inputs import workdir_path_state


def state_dir_for_ready_workdir(workdir: Path | str | None) -> Path | None:
    state = workdir_path_state(workdir)
    if state["status"] != "ready":
        return None
    return state_dir_for_workdir(str(state["workdir"]))


def loop_artifact_dir_for_ready_workdir(workdir: Path | str | None, loop_id: str) -> Path | None:
    state_dir = state_dir_for_ready_workdir(workdir)
    if state_dir is None:
        return None
    return state_dir / "loops" / loop_id


def stored_local_asset_path(path: object) -> Path | None:
    path_text = str(path or "").strip()
    if not path_text:
        return None
    candidate = Path(path_text).expanduser()
    if not candidate.is_absolute():
        return None
    return candidate

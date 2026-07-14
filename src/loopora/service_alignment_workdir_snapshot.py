from __future__ import annotations

import os
from pathlib import Path

from loopora.branding import APP_STATE_DIRNAME
from loopora.workdir_inputs import PATH_PROBE_ERRORS, same_workdir_identity


WORKDIR_UNREADABLE_MESSAGE = "Workdir could not be inspected."


def alignment_project_boundary(root: Path) -> Path | None:
    project_markers = (".git", "pyproject.toml", "package.json", "Cargo.toml", "go.mod")
    for candidate in (root, *root.parents):
        if any((candidate / marker).exists() for marker in project_markers):
            return candidate
    return None


def alignment_applicable_agents_paths(root: Path) -> list[Path]:
    boundary = alignment_project_boundary(root)
    search_dirs = [root]
    if boundary is not None:
        for parent in root.parents:
            search_dirs.append(parent)
            if parent == boundary:
                break

    agents_paths: list[Path] = []
    seen: set[Path] = set()
    for directory in search_dirs:
        agents_path = directory / "AGENTS.md"
        if agents_path in seen or not agents_path.is_file():
            continue
        seen.add(agents_path)
        agents_paths.append(agents_path)
    return agents_paths


def alignment_workdir_snapshot(workdir: Path) -> str:
    try:
        root = workdir.expanduser().resolve()
        if not root.exists() or not root.is_dir():
            return WORKDIR_UNREADABLE_MESSAGE
        entries = sorted(root.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
        visible = [item for item in entries if item.name not in {".DS_Store", APP_STATE_DIRNAME}][:40]
        workdir_appears_empty = not visible
        marker_names = {
            "README.md",
            "README.zh-CN.md",
            "package.json",
            "pyproject.toml",
            "Cargo.toml",
            "go.mod",
            "pnpm-lock.yaml",
            "uv.lock",
            "requirements.txt",
            "AGENTS.md",
        }
        markers = [item.name for item in visible if item.name in marker_names]
        design_dir = root / "design"
        design_readme = design_dir / "README.md"
        tests_dir = root / "tests"
        agents_file = root / "AGENTS.md"
        applicable_agents = alignment_applicable_agents_paths(root)
        lines = [f"Top-level entries ({len(visible)} shown):"]
        if workdir_appears_empty:
            lines.append("Workdir appears empty. Treat technology choices as assumptions until the run verifies them.")
        for item in visible:
            suffix = "/" if item.is_dir() else ""
            lines.append(f"- {item.name}{suffix}")
        if markers:
            lines.append("Detected markers: " + ", ".join(markers))
        lines.append(f"AGENTS.md exists: {'yes' if agents_file.is_file() else 'no'}")
        lines.append(f"Applicable AGENTS.md exists: {'yes' if applicable_agents else 'no'}")
        if applicable_agents:
            agents_relpaths = [os.path.relpath(path, root) for path in applicable_agents]
            lines.append("Applicable AGENTS.md paths: " + ", ".join(agents_relpaths))
        lines.append(f"design/ exists: {'yes' if design_dir.is_dir() else 'no'}")
        lines.append(f"design/README.md exists: {'yes' if design_readme.is_file() else 'no'}")
        lines.append(f"tests/ exists: {'yes' if tests_dir.is_dir() else 'no'}")
        return "\n".join(lines)
    except PATH_PROBE_ERRORS:
        return WORKDIR_UNREADABLE_MESSAGE


def alignment_workdir_snapshot_has_governance_markers(workdir_snapshot: str) -> bool:
    snapshot = str(workdir_snapshot or "").lower()
    return any(
        marker in snapshot
        for marker in (
            "agents.md exists: yes",
            "applicable agents.md exists: yes",
            "design/ exists: yes",
            "design/readme.md exists: yes",
            "tests/ exists: yes",
        )
    )


def alignment_workdir_spec_candidates(state_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    root_spec = state_dir / "spec.md"
    if _path_is_file(root_spec):
        candidates.append(root_spec)
    loops_dir = state_dir / "loops"
    if _path_is_dir(loops_dir):
        candidates.extend(path for path in _glob_paths(loops_dir, "*/spec.md") if _path_is_file(path))
    return candidates[:20]


def alignment_same_workdir(candidate: object, expected: Path) -> bool:
    return same_workdir_identity(candidate, expected)


def _path_is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except PATH_PROBE_ERRORS:
        return False


def _path_is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except PATH_PROBE_ERRORS:
        return False


def _glob_paths(path: Path, pattern: str) -> list[Path]:
    try:
        return sorted(path.glob(pattern))
    except PATH_PROBE_ERRORS:
        return []

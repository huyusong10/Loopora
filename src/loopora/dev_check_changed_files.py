from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
import subprocess

from loopora.dev_check_types import ChangedFileDetection

UNSTAGED_RENAME_NAME_SIMILARITY = 0.55
UNSTAGED_RENAME_TEXT_SIMILARITY = 0.80


def changed_file_detection(changed_files: list[str] | None, *, root: Path) -> ChangedFileDetection:
    if changed_files is not None:
        files, ignored_files = provided_changed_file_projection(changed_files, root=root)
        return ChangedFileDetection(files=files, source="provided", status="provided", ignored_files=tuple(ignored_files))
    files, git_available = git_changed_files(root)
    status = "detected" if files else "clean"
    if not git_available:
        status = "unavailable"
    return ChangedFileDetection(files=files, source="git", status=status)


def normalized_changed_files(changed_files: list[str], *, root: Path | None = None) -> list[str]:
    return provided_changed_file_projection(changed_files, root=root)[0]


def provided_changed_file_projection(changed_files: list[str], *, root: Path | None = None) -> tuple[list[str], list[str]]:
    normalized: set[str] = set()
    ignored: set[str] = set()
    for path in changed_files:
        raw_path = str(path).strip()
        if not raw_path:
            continue
        normalized_path = normalized_changed_file(raw_path, root=root)
        if normalized_path:
            normalized.add(normalized_path)
        else:
            ignored.add(raw_path.replace("\\", "/"))
    return sorted(normalized), sorted(ignored)


def normalized_changed_file(path: object, *, root: Path | None = None) -> str:
    raw_path = str(path).strip()
    if not raw_path:
        return ""
    candidate = Path(raw_path).expanduser()
    if root is not None and candidate.is_absolute():
        try:
            return candidate.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
        except (OSError, ValueError):
            return ""
    normalized = strip_current_dir_prefix(raw_path.replace("\\", "/"))
    if normalized == ".." or normalized.startswith("../"):
        return ""
    return normalized


def git_changed_files(root: Path) -> tuple[list[str], bool]:
    commands = (
        ("git", "diff", "--name-status"),
        ("git", "diff", "--cached", "--name-status"),
    )
    paths: set[str] = set()
    deleted_paths: set[str] = set()
    for command in commands:
        completed = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
        if completed.returncode != 0:
            return [], False
        for line in completed.stdout.splitlines():
            status, *items = line.strip().split("\t")
            if not status or not items:
                continue
            path = items[-1].strip()
            paths.add(path)
            if status.startswith("D"):
                deleted_paths.add(path)
    completed = subprocess.run(("git", "ls-files", "--others", "--exclude-standard"), cwd=root, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return [], False
    untracked_paths = {line.strip() for line in completed.stdout.splitlines() if line.strip()}
    paths.update(untracked_paths)
    paths = collapse_unstaged_git_renames(paths, deleted_paths=deleted_paths, untracked_paths=untracked_paths, root=root)
    return normalized_changed_files(sorted(paths)), True


def collapse_unstaged_git_renames(
    paths: set[str],
    *,
    deleted_paths: set[str],
    untracked_paths: set[str],
    root: Path,
) -> set[str]:
    if not deleted_paths or not untracked_paths:
        return paths
    untracked_files = read_untracked_file_bytes(untracked_paths, root=root)
    if not untracked_files:
        return paths
    collapsed = set(paths)
    for path in deleted_paths:
        normalized = normalized_changed_file(path, root=root)
        if not normalized:
            continue
        old_bytes = git_head_file_bytes(root, path)
        if old_bytes is None:
            continue
        candidates = [
            new_path
            for new_path, new_bytes in untracked_files
            if looks_like_unstaged_git_rename(
                old_path=normalized,
                old_bytes=old_bytes,
                new_path=new_path,
                new_bytes=new_bytes,
            )
        ]
        if len(candidates) == 1:
            collapsed.discard(path)
    return collapsed


def read_untracked_file_bytes(untracked_paths: set[str], *, root: Path) -> list[tuple[str, bytes]]:
    files: list[tuple[str, bytes]] = []
    for path in untracked_paths:
        normalized = normalized_changed_file(path, root=root)
        if not normalized:
            continue
        try:
            candidate = (root / normalized).resolve(strict=False)
            if candidate.is_file():
                files.append((normalized, candidate.read_bytes()))
        except OSError:
            continue
    return files


def looks_like_unstaged_git_rename(*, old_path: str, old_bytes: bytes, new_path: str, new_bytes: bytes) -> bool:
    old = Path(old_path)
    new = Path(new_path)
    if old.parent != new.parent or old.suffix != new.suffix:
        return False
    if SequenceMatcher(None, old.name, new.name).ratio() < UNSTAGED_RENAME_NAME_SIMILARITY:
        return False
    return old_bytes == new_bytes or text_similarity(old_bytes, new_bytes) >= UNSTAGED_RENAME_TEXT_SIMILARITY


def text_similarity(left: bytes, right: bytes) -> float:
    if b"\0" in left or b"\0" in right:
        return 0.0
    return SequenceMatcher(None, left.decode("utf-8", errors="replace"), right.decode("utf-8", errors="replace")).ratio()


def git_head_file_bytes(root: Path, path: str) -> bytes | None:
    completed = subprocess.run(("git", "show", f"HEAD:{path}"), cwd=root, capture_output=True, check=False)
    return completed.stdout if completed.returncode == 0 else None


def strip_current_dir_prefix(path: str) -> str:
    normalized = path.strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized

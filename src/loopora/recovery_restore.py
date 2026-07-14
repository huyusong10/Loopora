from __future__ import annotations

from contextlib import suppress
from hashlib import sha256
import os
from pathlib import Path, PurePosixPath
import shlex
import sqlite3
from tempfile import TemporaryDirectory
from uuid import uuid4
from zipfile import ZipFile

from loopora.branding import app_home_path, state_dir_for_workdir
from loopora.recovery_archive import validated_recovery_manifest
from loopora.service_types import LooporaError
from loopora.workdir_inputs import normalize_existing_workdir


def restore_recovery_archive(*, archive: Path, workdir: Path, apply: bool = False) -> dict:
    archive_path, manifest = validated_recovery_manifest(archive)
    root = normalize_existing_workdir(workdir)
    home = app_home_path().resolve(strict=False)
    _validate_restore_identity(manifest, home=home, root=root)
    entries = _restore_entries(manifest, home=home, root=root)
    planned, already_present, conflicts = _restore_plan(entries)
    result = {
        "status": "blocked" if conflicts else ("restored" if apply else "preview"),
        "dry_run": not apply,
        "archive": str(archive_path),
        "app_home": str(home),
        "workdir": str(root),
        "planned": [str(item["target"]) for item in planned],
        "already_present": [str(item["target"]) for item in already_present],
        "conflicts": [str(item["target"]) for item in conflicts],
        "restored": [],
        "public_safe": False,
        "content_scope": "private_full_recovery",
    }
    if conflicts or not apply:
        return result
    restored = _apply_restore(archive_path, planned)
    result["restored"] = [str(path) for path in restored]
    return result


def _validate_restore_identity(manifest: dict, *, home: Path, root: Path) -> None:
    source = manifest["source"]
    source_home = Path(source["app_home"])
    source_workdir = Path(source["workdir"])
    if home != source_home:
        raise LooporaError(
            "recovery archive belongs to a different App home; restore with "
            f"LOOPORA_HOME={shlex.quote(str(source_home))} or inspect the archive without writing"
        )
    if root != source_workdir:
        raise LooporaError(
            "recovery archive belongs to a different target project; exact-path recovery requires "
            f"--workdir {shlex.quote(str(source_workdir))}"
        )


def _restore_entries(manifest: dict, *, home: Path, root: Path) -> list[dict]:
    entries: list[dict] = []
    for entry in manifest["files"]:
        archive_path = str(entry["path"])
        relative = PurePosixPath(archive_path)
        if relative.parts[0] == "app":
            target = home.joinpath(*relative.parts[1:])
            boundary = home
        else:
            target = root.joinpath(*relative.parts[1:])
            boundary = state_dir_for_workdir(root)
        entries.append({**entry, "target": target, "boundary": boundary})
    return entries


def _restore_plan(entries: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    planned: list[dict] = []
    already_present: list[dict] = []
    conflicts: list[dict] = []
    for entry in entries:
        target = entry["target"]
        boundary = entry["boundary"]
        if _has_symlink_parent(target, boundary=boundary):
            conflicts.append(entry)
        elif not target.exists():
            planned.append(entry)
        elif target.is_symlink() or not target.is_file():
            conflicts.append(entry)
        elif _restore_target_matches(entry):
            already_present.append(entry)
        else:
            conflicts.append(entry)
    return planned, already_present, conflicts


def _restore_target_matches(entry: dict) -> bool:
    target = entry["target"]
    if entry["path"] == "app/app.db":
        return _database_snapshot_matches(target, entry)
    return _file_sha256(target) == entry["sha256"] and target.stat().st_size == entry["size_bytes"]


def _database_snapshot_matches(path: Path, entry: dict) -> bool:
    try:
        with TemporaryDirectory(prefix="loopora-recovery-compare-") as temporary_dir:
            snapshot = Path(temporary_dir) / "app.db"
            source = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
            destination = sqlite3.connect(snapshot)
            try:
                source.backup(destination)
                integrity = destination.execute("PRAGMA quick_check").fetchone()
            finally:
                destination.close()
                source.close()
            if integrity is None or integrity[0] != "ok":
                return False
            return snapshot.stat().st_size == entry["size_bytes"] and _file_sha256(snapshot) == entry["sha256"]
    except (OSError, sqlite3.Error):
        return False


def _has_symlink_parent(target: Path, *, boundary: Path) -> bool:
    current = target.parent
    while current != boundary.parent:
        if current.exists() and current.is_symlink():
            return True
        if current == boundary:
            return False
        current = current.parent
    return True


def _apply_restore(archive_path: Path, planned: list[dict]) -> list[Path]:
    staged: list[tuple[dict, Path]] = []
    restored: list[Path] = []
    try:
        with ZipFile(archive_path, mode="r") as archive:
            for entry in planned:
                target = entry["target"]
                if _has_symlink_parent(target, boundary=entry["boundary"]):
                    raise LooporaError(f"recovery target parent changed after preview: {target}")
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(f".{target.name}.restore.{uuid4().hex}")
                _stage_archive_member(archive, entry, temporary)
                staged.append((entry, temporary))
        for entry, temporary in sorted(staged, key=lambda item: item[0]["path"] == "app/app.db"):
            target = entry["target"]
            if _has_symlink_parent(target, boundary=entry["boundary"]):
                raise LooporaError(f"recovery target parent changed after preview: {target}")
            try:
                os.link(temporary, target)
            except FileExistsError as exc:
                raise LooporaError(f"recovery target changed after preview and was not overwritten: {target}") from exc
            restored.append(target)
    except LooporaError:
        _rollback_restored_links(restored, staged)
        raise
    except OSError as exc:
        _rollback_restored_links(restored, staged)
        raise LooporaError("recovery archive could not be restored") from exc
    finally:
        for _entry, temporary in staged:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)
    return restored


def _rollback_restored_links(restored: list[Path], staged: list[tuple[dict, Path]]) -> None:
    staged_by_target = {entry["target"]: temporary for entry, temporary in staged}
    for target in reversed(restored):
        temporary = staged_by_target.get(target)
        if temporary is None:
            continue
        with suppress(OSError):
            if target.exists() and target.samefile(temporary):
                target.unlink()


def _stage_archive_member(archive: ZipFile, entry: dict, temporary: Path) -> None:
    digest = sha256()
    size = 0
    with archive.open(entry["path"], mode="r") as source, temporary.open("xb") as target:
        while chunk := source.read(1024 * 1024):
            target.write(chunk)
            digest.update(chunk)
            size += len(chunk)
        target.flush()
        os.fsync(target.fileno())
    if size != entry["size_bytes"] or digest.hexdigest() != entry["sha256"]:
        temporary.unlink(missing_ok=True)
        raise LooporaError(f"recovery archive changed after validation: {entry['path']}")


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()

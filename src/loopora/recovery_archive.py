from __future__ import annotations

from contextlib import suppress
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
from tempfile import TemporaryDirectory
from uuid import uuid4
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo

from loopora.branding import state_dir_for_workdir
from loopora.service_types import ACTIVE_RUN_STATUSES, LooporaError
from loopora.settings import app_home, db_path
from loopora.utils import utc_now
from loopora.workdir_inputs import normalize_existing_workdir

RECOVERY_ARCHIVE_KIND = "loopora_recovery_archive"
RECOVERY_ARCHIVE_SCHEMA_VERSION = 1
RECOVERY_MANIFEST_PATH = "manifest.json"
RECOVERY_DATABASE_PATH = "app/app.db"
RECOVERY_MAX_FILE_COUNT = 100_000
RECOVERY_MAX_TOTAL_BYTES = 8 * 1024 * 1024 * 1024
RECOVERY_PROJECT_DIRS = ("loops", "runs", "alignment_sessions")
RECOVERY_APP_FILES = ("settings.json", "recent_workdirs.json")
RECOVERY_EXCLUSIONS = (
    "project source files",
    "App and project diagnostic logs",
    "Coding Agent project entries and inbox files",
    "temporary, visual-review, and unknown .loopora directories",
    "environment variables and external provider credentials",
)
_FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class RecoveryActiveWorkError(LooporaError):
    def __init__(self, *, active_runs: int, active_planning_sessions: int) -> None:
        self.active_runs = active_runs
        self.active_planning_sessions = active_planning_sessions
        super().__init__(
            "stop active Runs and planning sessions before creating a recovery archive "
            f"(active Runs: {active_runs}, active planning sessions: {active_planning_sessions})"
        )


def default_recovery_archive_path() -> Path:
    token = utc_now().replace("-", "").replace(":", "").replace("+00:00", "Z")
    return Path.cwd() / f"loopora-recovery-{token}.zip"


def create_recovery_archive(*, workdir: Path, output: Path | None = None, overwrite: bool = False) -> dict:
    root = normalize_existing_workdir(workdir)
    home = app_home().resolve()
    database = db_path()
    target = (output or default_recovery_archive_path()).expanduser().resolve(strict=False)
    _validate_create_inputs(home=home, root=root, database=database, target=target, overwrite=overwrite)

    try:
        with TemporaryDirectory(prefix="loopora-recovery-") as temporary_dir:
            staging = Path(temporary_dir)
            _reject_active_work(database)
            sources = _managed_recovery_sources(home=home, root=root)
            entries = [_stage_source_file(source, archive_path, staging) for source, archive_path in sources]
            database_target = staging / RECOVERY_DATABASE_PATH
            database_target.parent.mkdir(parents=True, exist_ok=True)
            schema_version = _snapshot_database(database, database_target)
            _reject_active_work(database_target)
            entries.append(_file_entry(database_target, RECOVERY_DATABASE_PATH))
            entries.sort(key=lambda item: item["path"])
            _validate_archive_budget(entries)
            manifest = _recovery_manifest(home=home, root=root, schema_version=schema_version, entries=entries)
            written = _write_recovery_zip(target, staging=staging, manifest=manifest, overwrite=overwrite)
    except LooporaError:
        raise
    except (OSError, sqlite3.Error) as exc:
        raise LooporaError("recovery archive could not be created") from exc
    return {
        "status": "created",
        "path": str(written),
        "public_safe": False,
        "content_scope": "private_full_recovery",
        "file_count": len(manifest["files"]),
        "size_bytes": written.stat().st_size,
        "source": manifest["source"],
        "excluded": manifest["excluded"],
    }


def inspect_recovery_archive(path: Path) -> dict:
    archive_path = _normalize_archive_input(path)
    try:
        with TemporaryDirectory(prefix="loopora-recovery-inspect-") as temporary_dir:
            database_target = Path(temporary_dir) / "app.db"
            manifest = _validate_recovery_zip(archive_path, database_target=database_target)
            schema_version = _inspect_database(database_target)
    except LooporaError:
        raise
    except (OSError, BadZipFile, sqlite3.Error) as exc:
        raise LooporaError("recovery archive is unreadable or invalid") from exc
    source = manifest["source"]
    return {
        "status": "valid",
        "path": str(archive_path),
        "public_safe": False,
        "content_scope": manifest["content_scope"],
        "file_count": len(manifest["files"]),
        "size_bytes": archive_path.stat().st_size,
        "source": source,
        "database_schema_version": schema_version,
        "scope": manifest["scope"],
        "excluded": manifest["excluded"],
        "manifest": manifest,
    }


def validated_recovery_manifest(path: Path) -> tuple[Path, dict]:
    inspected = inspect_recovery_archive(path)
    return Path(inspected["path"]), inspected["manifest"]


def _validate_create_inputs(*, home: Path, root: Path, database: Path, target: Path, overwrite: bool) -> None:
    if not database.exists() or not database.is_file() or database.is_symlink():
        raise LooporaError("no restorable Loopora App database was found; start Loopora once before creating a recovery archive")
    if target.exists() and not overwrite:
        raise LooporaError(f"output already exists: {target}; pass --force to replace it")
    if target.exists() and not target.is_file():
        raise LooporaError(f"recovery archive output is not a file: {target}")
    managed_project_root = state_dir_for_workdir(root)
    if target.is_relative_to(home) or target.is_relative_to(managed_project_root):
        raise LooporaError("recovery archive output must be outside Loopora-managed App and project state")


def _managed_recovery_sources(*, home: Path, root: Path) -> list[tuple[Path, str]]:
    sources: list[tuple[Path, str]] = []
    for filename in RECOVERY_APP_FILES:
        source = home / filename
        if source.exists():
            sources.append((source, f"app/{filename}"))
    bundle_root = home / "bundles"
    sources.extend(_tree_recovery_sources(bundle_root, archive_root="app/bundles"))
    project_state = state_dir_for_workdir(root)
    for dirname in RECOVERY_PROJECT_DIRS:
        sources.extend(
            _tree_recovery_sources(project_state / dirname, archive_root=f"project/.loopora/{dirname}")
        )
    return sorted(sources, key=lambda item: item[1])


def _tree_recovery_sources(root: Path, *, archive_root: str) -> list[tuple[Path, str]]:
    if not root.exists():
        return []
    if root.is_symlink() or not root.is_dir():
        raise LooporaError(f"Loopora-managed recovery root is not a regular directory: {root}")
    sources: list[tuple[Path, str]] = []
    for source in sorted(root.rglob("*")):
        if source.is_symlink():
            raise LooporaError(f"recovery archive refuses symbolic links in Loopora-managed state: {source}")
        if source.is_dir():
            continue
        if not source.is_file():
            raise LooporaError(f"recovery archive refuses non-regular Loopora state: {source}")
        if source.name == ".DS_Store":
            continue
        relative = source.relative_to(root).as_posix()
        sources.append((source, f"{archive_root}/{relative}"))
    return sources


def _stage_source_file(source: Path, archive_path: str, staging: Path) -> dict:
    if source.is_symlink() or not source.is_file():
        raise LooporaError(f"recovery archive source is not a regular file: {source}")
    before = source.stat()
    destination = staging / archive_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    after = source.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise LooporaError(f"Loopora state changed while recovery archive was being created: {source}")
    return _file_entry(destination, archive_path)


def _snapshot_database(source_path: Path, destination_path: Path) -> int:
    source = sqlite3.connect(f"{source_path.resolve().as_uri()}?mode=ro", uri=True)
    destination = sqlite3.connect(destination_path)
    try:
        source.backup(destination)
        result = destination.execute("PRAGMA quick_check").fetchone()
        if result is None or result[0] != "ok":
            raise LooporaError("Loopora App database failed SQLite integrity checking")
        return int(destination.execute("PRAGMA user_version").fetchone()[0])
    finally:
        destination.close()
        source.close()


def _reject_active_work(database: Path) -> None:
    connection = sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        active_runs = _active_row_count(connection, "loop_runs", ACTIVE_RUN_STATUSES) if "loop_runs" in tables else 0
        active_alignments = (
            _active_row_count(connection, "alignment_sessions", {"running", "validating", "repairing"})
            if "alignment_sessions" in tables
            else 0
        )
    finally:
        connection.close()
    if active_runs or active_alignments:
        raise RecoveryActiveWorkError(
            active_runs=active_runs,
            active_planning_sessions=active_alignments,
        )


def _active_row_count(connection: sqlite3.Connection, table: str, statuses: set[str] | frozenset[str]) -> int:
    placeholders = ", ".join("?" for _ in statuses)
    row = connection.execute(f"SELECT COUNT(*) FROM {table} WHERE status IN ({placeholders})", sorted(statuses)).fetchone()
    return int(row[0]) if row else 0


def _recovery_manifest(*, home: Path, root: Path, schema_version: int, entries: list[dict]) -> dict:
    return {
        "schema_version": RECOVERY_ARCHIVE_SCHEMA_VERSION,
        "kind": RECOVERY_ARCHIVE_KIND,
        "created_at": utc_now(),
        "public_safe": False,
        "content_scope": "private_full_recovery",
        "sharing_note": "Contains task plans, transcripts, prompts, model output, evidence, local paths, and settings. Do not share as a public support bundle.",
        "source": {
            "app_home": str(home),
            "workdir": str(root),
            "database_schema_version": schema_version,
        },
        "scope": {
            "app_catalog": True,
            "project_state_directories": list(RECOVERY_PROJECT_DIRS),
            "restore_identity": "exact_source_app_home_and_workdir",
        },
        "excluded": list(RECOVERY_EXCLUSIONS),
        "files": entries,
    }


def _file_entry(path: Path, archive_path: str) -> dict:
    digest = sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return {"path": archive_path, "size_bytes": size, "sha256": digest.hexdigest()}


def _validate_archive_budget(entries: list[dict]) -> None:
    if len(entries) > RECOVERY_MAX_FILE_COUNT:
        raise LooporaError(f"recovery archive exceeds the {RECOVERY_MAX_FILE_COUNT:,}-file safety limit")
    total = sum(int(item["size_bytes"]) for item in entries)
    if total > RECOVERY_MAX_TOTAL_BYTES:
        raise LooporaError("recovery archive exceeds the 8 GiB uncompressed safety limit")


def _write_recovery_zip(target: Path, *, staging: Path, manifest: dict, overwrite: bool) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp.{uuid4().hex}")
    try:
        with ZipFile(temporary, mode="w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
            _write_zip_bytes(archive, RECOVERY_MANIFEST_PATH, _json_bytes(manifest))
            for entry in manifest["files"]:
                _write_zip_file(archive, entry["path"], staging / entry["path"])
        if overwrite:
            temporary.replace(target)
        else:
            try:
                os.link(temporary, target)
            except FileExistsError as exc:
                raise LooporaError(f"output already exists: {target}; pass --force to replace it") from exc
            finally:
                temporary.unlink(missing_ok=True)
    except LooporaError:
        raise
    except OSError as exc:
        raise LooporaError("recovery archive could not be written") from exc
    finally:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)
    return target.resolve()


def _write_zip_bytes(archive: ZipFile, path: str, content: bytes) -> None:
    info = _zip_info(path)
    archive.writestr(info, content)


def _write_zip_file(archive: ZipFile, path: str, source: Path) -> None:
    info = _zip_info(path)
    with source.open("rb") as source_stream, archive.open(info, mode="w") as target_stream:
        shutil.copyfileobj(source_stream, target_stream, length=1024 * 1024)


def _zip_info(path: str) -> ZipInfo:
    info = ZipInfo(path, date_time=_FIXED_ZIP_TIMESTAMP)
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o100600 << 16
    return info


def _normalize_archive_input(path: Path) -> Path:
    archive_path = path.expanduser().resolve(strict=False)
    if not archive_path.exists() or not archive_path.is_file() or archive_path.is_symlink():
        raise LooporaError(f"recovery archive file is unavailable: {archive_path}")
    return archive_path


def _validate_recovery_zip(archive_path: Path, *, database_target: Path) -> dict:
    with ZipFile(archive_path, mode="r") as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise LooporaError("recovery archive contains duplicate paths")
        if RECOVERY_MANIFEST_PATH not in names:
            raise LooporaError("recovery archive manifest is missing")
        manifest_info = archive.getinfo(RECOVERY_MANIFEST_PATH)
        _reject_non_regular_zip_member(manifest_info)
        if manifest_info.file_size > 2 * 1024 * 1024:
            raise LooporaError("recovery archive manifest exceeds the safety limit")
        try:
            manifest = json.loads(archive.read(RECOVERY_MANIFEST_PATH).decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise LooporaError("recovery archive manifest is malformed") from exc
        entries = _validated_manifest_entries(manifest)
        expected_names = {RECOVERY_MANIFEST_PATH, *(item["path"] for item in entries)}
        if set(names) != expected_names:
            raise LooporaError("recovery archive contains files outside its manifest")
        info_by_name = {info.filename: info for info in infos}
        _validate_archive_budget(entries)
        for entry in entries:
            info = info_by_name[entry["path"]]
            _validate_zip_member(info, entry)
            destination = database_target if entry["path"] == RECOVERY_DATABASE_PATH else None
            _verify_zip_member(archive, info, entry, destination=destination)
    return manifest


def _validated_manifest_entries(manifest: object) -> list[dict]:
    if not isinstance(manifest, dict):
        raise LooporaError("recovery archive manifest must be an object")
    if manifest.get("kind") != RECOVERY_ARCHIVE_KIND or manifest.get("schema_version") != RECOVERY_ARCHIVE_SCHEMA_VERSION:
        raise LooporaError("recovery archive format is not supported by this Loopora version")
    if manifest.get("public_safe") is not False or manifest.get("content_scope") != "private_full_recovery":
        raise LooporaError("recovery archive privacy boundary is missing")
    source = manifest.get("source")
    if not isinstance(source, dict) or not _absolute_source_path(source.get("app_home")) or not _absolute_source_path(source.get("workdir")):
        raise LooporaError("recovery archive source identity is malformed")
    raw_entries = manifest.get("files")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise LooporaError("recovery archive file manifest is empty")
    validated = [_validated_manifest_file_entry(entry) for entry in raw_entries]
    paths = [item["path"] for item in validated]
    if len(paths) != len(set(paths)) or RECOVERY_DATABASE_PATH not in paths:
        raise LooporaError("recovery archive file manifest is incomplete or duplicated")
    return validated


def _validated_manifest_file_entry(entry: object) -> dict:
    if not isinstance(entry, dict):
        raise LooporaError("recovery archive file entry is malformed")
    path = entry.get("path")
    size = entry.get("size_bytes")
    digest = entry.get("sha256")
    if not _valid_recovery_member_path(path):
        raise LooporaError(f"recovery archive contains an unsafe path: {path!r}")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise LooporaError(f"recovery archive contains an invalid size: {path}")
    if not isinstance(digest, str) or not _SHA256_PATTERN.fullmatch(digest):
        raise LooporaError(f"recovery archive contains an invalid checksum: {path}")
    return {"path": path, "size_bytes": size, "sha256": digest}


def _absolute_source_path(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and Path(value).is_absolute()


def _valid_recovery_member_path(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return False
    parts = path.parts
    if value in {RECOVERY_DATABASE_PATH, "app/settings.json", "app/recent_workdirs.json"}:
        return True
    if len(parts) >= 3 and parts[:2] == ("app", "bundles"):
        return True
    return len(parts) >= 4 and parts[:2] == ("project", ".loopora") and parts[2] in RECOVERY_PROJECT_DIRS


def _validate_zip_member(info: ZipInfo, entry: dict) -> None:
    _reject_non_regular_zip_member(info)
    if info.file_size != entry["size_bytes"]:
        raise LooporaError(f"recovery archive size mismatch: {info.filename}")


def _reject_non_regular_zip_member(info: ZipInfo) -> None:
    mode = (info.external_attr >> 16) & 0o170000
    if info.is_dir() or mode not in {0, 0o100000}:
        raise LooporaError(f"recovery archive contains a non-regular member: {info.filename}")


def _verify_zip_member(archive: ZipFile, info: ZipInfo, entry: dict, *, destination: Path | None) -> None:
    digest = sha256()
    size = 0
    target_stream = destination.open("wb") if destination is not None else None
    try:
        with archive.open(info, mode="r") as source_stream:
            while chunk := source_stream.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
                if target_stream is not None:
                    target_stream.write(chunk)
    finally:
        if target_stream is not None:
            target_stream.close()
    if size != entry["size_bytes"] or digest.hexdigest() != entry["sha256"]:
        raise LooporaError(f"recovery archive checksum mismatch: {info.filename}")


def _inspect_database(database: Path) -> int:
    connection = sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)
    try:
        result = connection.execute("PRAGMA quick_check").fetchone()
        if result is None or result[0] != "ok":
            raise LooporaError("recovery archive database failed SQLite integrity checking")
        return int(connection.execute("PRAGMA user_version").fetchone()[0])
    finally:
        connection.close()


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

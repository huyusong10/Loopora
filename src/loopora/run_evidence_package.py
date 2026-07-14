from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path, PureWindowsPath
import re
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from loopora.service_types import LooporaError
from loopora.utils import utc_now

MAX_EVIDENCE_PACKAGE_BYTES = 32 * 1024 * 1024
EVIDENCE_PACKAGE_PATHS = (
    "summary.md",
    "contract/spec.md",
    "contract/compiled_spec.json",
    "contract/strategy_source.json",
    "contract/run_contract.json",
    "evidence/ledger.jsonl",
    "evidence/coverage.json",
    "evidence/manifest.json",
    "evidence/task_verdict.json",
    "timeline/iterations.jsonl",
)
EVIDENCE_PACKAGE_OMISSIONS = (
    "workspace files",
    "provider transcripts",
    "prompts and role requests",
    "raw and normalized model outputs",
    "runtime events and logs",
)
_FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True, slots=True)
class RunEvidencePackage:
    filename: str
    content: bytes
    manifest: dict


def build_run_evidence_package(run: dict) -> RunEvidencePackage:
    run_id = str(run.get("id") or "").strip()
    run_dir_text = str(run.get("runs_dir") or "").strip()
    if not run_id or not run_dir_text:
        raise LooporaError("run evidence package source is unavailable")

    run_dir = Path(run_dir_text).expanduser()
    if not run_dir.is_absolute():
        raise LooporaError("run evidence package source must be an absolute path")
    try:
        resolved_run_dir = run_dir.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise LooporaError("run evidence package source is unavailable") from exc
    if not resolved_run_dir.is_dir():
        raise LooporaError("run evidence package source is unavailable")

    replacements = _local_path_replacements(run, resolved_run_dir)
    payload_files: dict[str, bytes] = {}
    missing_files: list[str] = []
    total_bytes = 0
    for relative_path in EVIDENCE_PACKAGE_PATHS:
        source = run_dir / relative_path
        if not source.exists():
            missing_files.append(relative_path)
            continue
        content = _review_projection_bytes(source, resolved_run_dir, replacements)
        total_bytes += len(content)
        if total_bytes > MAX_EVIDENCE_PACKAGE_BYTES:
            raise LooporaError("run evidence package exceeds the 32 MiB review-package limit")
        payload_files[relative_path] = content

    verdict_status = _task_verdict_status(payload_files.get("evidence/task_verdict.json"))
    manifest = {
        "schema_version": 1,
        "kind": "loopora_run_evidence_package",
        "generated_at": utc_now(),
        "run": {
            "id": run_id,
            "loop_id": str(run.get("loop_id") or ""),
            "status": str(run.get("status") or "unknown"),
            "task_verdict_status": verdict_status,
        },
        "public_safe": False,
        "content_scope": "private_task_review",
        "sharing_note": "Contains task content. Review every file before sharing outside the intended audience.",
        "files": [
            {
                "path": path,
                "size_bytes": len(content),
                "sha256": sha256(content).hexdigest(),
            }
            for path, content in payload_files.items()
        ],
        "missing_files": missing_files,
        "omitted_by_default": list(EVIDENCE_PACKAGE_OMISSIONS),
    }
    archive_files = {
        "README.md": _package_readme(manifest).encode("utf-8"),
        "manifest.json": _json_bytes(manifest),
        **payload_files,
    }
    content = _zip_bytes(archive_files)
    if len(content) > MAX_EVIDENCE_PACKAGE_BYTES:
        raise LooporaError("run evidence package exceeds the 32 MiB review-package limit")
    return RunEvidencePackage(
        filename=f"loopora-evidence-{_filename_token(run_id)}.zip",
        content=content,
        manifest=manifest,
    )


def write_run_evidence_package(path: Path, package: RunEvidencePackage, *, overwrite: bool = False) -> Path:
    target = path.expanduser()
    if target.exists() and not overwrite:
        raise LooporaError(f"output already exists: {target}; pass --force to replace it")
    if target.exists() and not target.is_file():
        raise LooporaError(f"output is not a file: {target}")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.tmp.{uuid4().hex}")
        temporary.write_bytes(package.content)
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
        with suppress(OSError, UnboundLocalError):
            temporary.unlink(missing_ok=True)
        raise LooporaError("run evidence package could not be written") from exc
    return target.resolve()


def _review_projection_bytes(source: Path, resolved_run_dir: Path, replacements: tuple[tuple[str, str], ...]) -> bytes:
    text = _read_review_source(source, resolved_run_dir)
    try:
        if source.suffix == ".json":
            return _json_bytes(_sanitize_value(json.loads(text), replacements))
        if source.suffix == ".jsonl":
            lines = [
                json.dumps(_sanitize_value(json.loads(line), replacements), ensure_ascii=False, separators=(",", ":"))
                for line in text.splitlines()
                if line.strip()
            ]
            return (("\n".join(lines) + "\n") if lines else "").encode("utf-8")
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise LooporaError(f"run evidence artifact is malformed: {source.name}") from exc
    return _sanitize_text(text, replacements).encode("utf-8")


def _read_review_source(source: Path, resolved_run_dir: Path) -> str:
    try:
        if source.is_symlink():
            raise LooporaError(f"run evidence artifact is a symbolic link: {source.name}")
        resolved_source = source.resolve(strict=True)
        if not resolved_source.is_relative_to(resolved_run_dir) or not resolved_source.is_file():
            raise LooporaError("run evidence artifact is outside the saved Run directory")
        if resolved_source.stat().st_size > MAX_EVIDENCE_PACKAGE_BYTES:
            raise LooporaError("run evidence artifact exceeds the review-package limit")
        return resolved_source.read_text(encoding="utf-8")
    except LooporaError:
        raise
    except (OSError, UnicodeError, RuntimeError) as exc:
        raise LooporaError(f"run evidence artifact could not be read: {source.name}") from exc


def _sanitize_value(value, replacements: tuple[tuple[str, str], ...], *, key: str = ""):
    if isinstance(value, dict):
        return {item_key: _sanitize_value(item_value, replacements, key=str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(item, replacements) for item in value]
    if isinstance(value, str):
        if key == "absolute_path":
            return "<local-path>"
        sanitized = _sanitize_text(value, replacements)
        if _is_absolute_path(sanitized):
            return "<local-path>"
        return sanitized
    return value


def _sanitize_text(text: str, replacements: tuple[tuple[str, str], ...]) -> str:
    sanitized = text
    for local_path, placeholder in replacements:
        sanitized = sanitized.replace(local_path, placeholder)
        sanitized = sanitized.replace(local_path.replace("\\", "/"), placeholder)
    return sanitized


def _local_path_replacements(run: dict, resolved_run_dir: Path) -> tuple[tuple[str, str], ...]:
    candidates = {
        str(resolved_run_dir): "<run-dir>",
        str(Path.home().expanduser().resolve()): "<home>",
    }
    workdir_text = str(run.get("workdir") or "").strip()
    if workdir_text:
        with suppress(OSError, RuntimeError):
            candidates[str(Path(workdir_text).expanduser().resolve())] = "<workdir>"
    return tuple(sorted(candidates.items(), key=lambda item: len(item[0]), reverse=True))


def _is_absolute_path(value: str) -> bool:
    if not value or "\n" in value or "\r" in value:
        return False
    return Path(value).is_absolute() or PureWindowsPath(value).is_absolute() or bool(PureWindowsPath(value).drive)


def _task_verdict_status(content: bytes | None) -> str:
    if not content:
        return "unavailable"
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return "unavailable"
    return str(payload.get("status") or "unknown") if isinstance(payload, dict) else "unknown"


def _package_readme(manifest: dict) -> str:
    run = manifest["run"]
    included = "\n".join(f"- `{item['path']}`" for item in manifest["files"]) or "- No Run artifacts were available."
    omitted = "\n".join(f"- {item}" for item in manifest["omitted_by_default"])
    return (
        "# Loopora Run Evidence Package\n\n"
        "> Private task-review material. This package is not public-safe; review every file before sharing.\n\n"
        f"- Run: `{run['id']}`\n"
        f"- Lifecycle status: `{run['status']}`\n"
        f"- Task verdict: `{run['task_verdict_status']}`\n\n"
        "Local absolute paths were replaced with placeholders. Relative artifact references remain for review.\n\n"
        "## Included\n\n"
        f"{included}\n\n"
        "## Omitted by default\n\n"
        f"{omitted}\n\n"
        "This is a curated evidence snapshot, not a project backup, complete transcript, or independent proof that the task passed.\n"
    )


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    output = BytesIO()
    with ZipFile(output, mode="w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(files):
            info = ZipInfo(path, date_time=_FIXED_ZIP_TIMESTAMP)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, files[path])
    return output.getvalue()


def _filename_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
    return token or "run"

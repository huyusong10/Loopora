from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path

from loopora.branding import state_dir_for_workdir
from loopora.event_redaction import redact_alignment_event_payload, redact_run_event_payload
from loopora.event_redaction_audit_results import event_redaction_sample, redaction_changed
from loopora.run_artifacts import RunArtifactLayout
from loopora.settings import load_recent_workdirs

EventRedactor = Callable[[str, Mapping[str, object]], dict]


def audit_timeline_files(repository, *, fix: bool) -> dict:
    paths: list[Path] = []
    for runs_dir in _candidate_run_dirs(repository):
        layout = RunArtifactLayout(Path(runs_dir))
        paths.extend((layout.timeline_events_path, layout.legacy_events_path))
    return _audit_event_jsonl_paths(paths, fix=fix, redactor=redact_run_event_payload, sample_source="timeline")


def audit_alignment_event_files(repository, *, fix: bool) -> dict:
    paths = (Path(session_dir) / "events" / "events.jsonl" for session_dir in _candidate_alignment_session_dirs(repository))
    return _audit_event_jsonl_paths(paths, fix=fix, redactor=redact_alignment_event_payload, sample_source="alignment_file")


def _audit_event_jsonl_paths(
    paths: Iterable[Path],
    *,
    fix: bool,
    redactor: EventRedactor,
    sample_source: str,
) -> dict:
    scanned_files = 0
    scanned_events = 0
    suspect = 0
    fixed = 0
    samples = []
    unfixable = []
    seen_paths: set[Path] = set()
    for path in paths:
        if path in seen_paths:
            continue
        seen_paths.add(path)
        if not path.exists():
            continue
        scanned_files += 1
        file_report = _audit_event_jsonl_file(
            path,
            fix=fix,
            redactor=redactor,
            sample_source=sample_source,
        )
        scanned_events += file_report["scanned"]
        suspect += file_report["suspect"]
        fixed += file_report["fixed"]
        samples.extend(file_report["samples"])
        unfixable.extend(file_report["unfixable"])
    return {
        "scanned_files": scanned_files,
        "scanned_events": scanned_events,
        "suspect": suspect,
        "fixed": fixed,
        "samples": samples[:20],
        "unfixable": unfixable,
    }


def _candidate_run_dirs(repository) -> list[Path]:
    candidates: list[Path] = []
    seen: set[Path] = set()

    for event in repository.list_run_events_for_redaction_audit():
        _add_candidate_path(candidates, seen, event.get("runs_dir"))

    if hasattr(repository, "list_local_asset_roots"):
        for row in repository.list_local_asset_roots(resource_type="run", states={"active", "orphaned"}):
            _add_candidate_path(candidates, seen, row.get("path"))

    for workdir in load_recent_workdirs(limit=100):
        root = state_dir_for_workdir(workdir) / "runs"
        if not root.exists():
            continue
        for run_dir in sorted(item for item in root.iterdir() if item.is_dir()):
            _add_candidate_path(candidates, seen, run_dir)

    return candidates


def _candidate_alignment_session_dirs(repository) -> list[Path]:
    candidates: list[Path] = []
    seen: set[Path] = set()

    if hasattr(repository, "list_alignment_events_for_redaction_audit"):
        for event in repository.list_alignment_events_for_redaction_audit():
            bundle_path = str(event.get("bundle_path") or "").strip()
            if bundle_path:
                _add_candidate_path(candidates, seen, _alignment_event_artifact_root(Path(bundle_path)))

    if hasattr(repository, "list_local_asset_roots"):
        for row in repository.list_local_asset_roots(resource_type="alignment_session", states={"active", "orphaned"}):
            _add_candidate_path(candidates, seen, row.get("path"))

    for workdir in load_recent_workdirs(limit=100):
        root = state_dir_for_workdir(workdir) / "alignment_sessions"
        if not root.exists():
            continue
        for session_dir in sorted(item for item in root.iterdir() if item.is_dir()):
            _add_candidate_path(candidates, seen, session_dir)

    return candidates


def _add_candidate_path(candidates: list[Path], seen: set[Path], path: object) -> None:
    text = str(path or "").strip()
    if not text:
        return
    candidate = Path(text).expanduser()
    if candidate in seen:
        return
    seen.add(candidate)
    candidates.append(candidate)


def _alignment_event_artifact_root(bundle_path: Path) -> Path:
    return bundle_path.parent.parent if bundle_path.parent.name == "artifacts" else bundle_path.parent


def _audit_event_jsonl_file(path: Path, *, fix: bool, redactor: EventRedactor, sample_source: str) -> dict:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        return {
            "scanned": 0,
            "suspect": 0,
            "fixed": 0,
            "samples": [],
            "unfixable": [
                {
                    "source": sample_source,
                    "path": str(path),
                    "reason": "read_failed",
                    "error_type": type(exc).__name__,
                }
            ],
        }
    next_lines: list[str] = []
    scanned = 0
    suspect = 0
    fixed = 0
    pending_fixed = 0
    samples = []
    unfixable = []
    changed = False
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            next_lines.append(line)
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            unfixable.append({"source": sample_source, "path": str(path), "line": line_number, "reason": "invalid_json"})
            next_lines.append(line)
            continue
        scanned += 1
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        redacted = redactor(str(event.get("event_type") or ""), payload)
        if not redaction_changed(payload, redacted):
            next_lines.append(line)
            continue
        suspect += 1
        samples.append(event_redaction_sample(sample_source, event, redacted, path=path, line=line_number))
        if fix:
            event["payload"] = redacted
            next_lines.append(json.dumps(event, ensure_ascii=False))
            pending_fixed += 1
            changed = True
        else:
            next_lines.append(line)
    if fix and changed:
        try:
            path.write_text("\n".join(next_lines) + ("\n" if next_lines else ""), encoding="utf-8")
        except OSError as exc:
            unfixable.append(
                {
                    "source": sample_source,
                    "path": str(path),
                    "reason": "write_failed",
                    "error_type": type(exc).__name__,
                }
            )
        else:
            fixed = pending_fixed
    return {
        "scanned": scanned,
        "suspect": suspect,
        "fixed": fixed,
        "samples": samples,
        "unfixable": unfixable,
    }

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from loopora.event_redaction import redact_sensitive_text
from loopora.service_alignment_decision_options import normalize_alignment_decision_options
from loopora.service_alignment_context import redact_alignment_source_value
from loopora.structured_numbers import structured_non_negative_int


@dataclass(frozen=True)
class AlignmentMessageRecord:
    entry: dict
    event_payload: dict


def alignment_artifact_root_from_bundle_path(bundle_path: Path) -> Path:
    bundle_path = Path(bundle_path)
    return bundle_path.parent.parent if bundle_path.parent.name == "artifacts" else bundle_path.parent


def alignment_session_root(session: dict) -> Path:
    return alignment_artifact_root_from_bundle_path(Path(session["bundle_path"]))


def alignment_artifact_paths_from_root(root: Path) -> dict[str, Path]:
    root = Path(root)
    return {
        "root": root,
        "manifest": root / "manifest.json",
        "conversation_dir": root / "conversation",
        "transcript": root / "conversation" / "transcript.jsonl",
        "agreement_dir": root / "agreement",
        "agreement": root / "agreement" / "current.json",
        "artifacts_dir": root / "artifacts",
        "bundle": root / "artifacts" / "bundle.yml",
        "validation": root / "artifacts" / "validation.json",
        "events_dir": root / "events",
        "events": root / "events" / "events.jsonl",
        "invocations_dir": root / "invocations",
        "legacy_dir": root / "legacy",
    }


def alignment_artifact_paths(session: dict) -> dict[str, Path]:
    return alignment_artifact_paths_from_root(alignment_session_root(session))


def ensure_alignment_artifact_dirs(root: Path) -> None:
    paths = alignment_artifact_paths_from_root(root)
    for key in ("conversation_dir", "agreement_dir", "artifacts_dir", "events_dir", "invocations_dir"):
        paths[key].mkdir(parents=True, exist_ok=True)


def alignment_manifest_payload(session: dict) -> dict:
    transcript = [item for item in (session.get("transcript") or []) if isinstance(item, dict)]
    first_user = ""
    last_message = ""
    for entry in transcript:
        content = redact_sensitive_text(str(entry.get("content", "") or "").strip())
        if not content:
            continue
        if not first_user and entry.get("role") == "user":
            first_user = content
        last_message = content
    root = alignment_session_root(session)
    return {
        "id": session.get("id", ""),
        "status": session.get("status", ""),
        "executor_kind": session.get("executor_kind", "codex"),
        "executor_mode": session.get("executor_mode", "preset"),
        "model": session.get("model", ""),
        "reasoning_effort": session.get("reasoning_effort", ""),
        "workdir": session.get("workdir", ""),
        "bundle_path": session.get("bundle_path", ""),
        "artifact_dir": str(root),
        "alignment_stage": session.get("alignment_stage", "clarifying"),
        "linked_bundle_id": session.get("linked_bundle_id", ""),
        "linked_loop_id": session.get("linked_loop_id", ""),
        "linked_run_id": session.get("linked_run_id", ""),
        "repair_attempts": alignment_repair_attempts(session),
        "created_at": session.get("created_at", ""),
        "updated_at": session.get("updated_at", ""),
        "finished_at": session.get("finished_at", ""),
        "error_message": redact_sensitive_text(str(session.get("error_message", "") or "")),
        "message_count": len(transcript),
        "title": first_user[:96] if first_user else session.get("id", ""),
        "last_message": last_message[:160],
        "paths": {
            "transcript": "conversation/transcript.jsonl",
            "working_agreement": "agreement/current.json",
            "bundle": "artifacts/bundle.yml",
            "validation": "artifacts/validation.json",
            "events": "events/events.jsonl",
            "invocations": "invocations",
        },
    }


def write_alignment_manifest(session: dict) -> None:
    paths = alignment_artifact_paths(session)
    ensure_alignment_artifact_dirs(paths["root"])
    paths["manifest"].write_text(
        json.dumps(alignment_manifest_payload(session), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_alignment_transcript_log(session: dict) -> None:
    paths = alignment_artifact_paths(session)
    ensure_alignment_artifact_dirs(paths["root"])
    transcript = list(session.get("transcript") or [])
    with paths["transcript"].open("w", encoding="utf-8") as handle:
        for entry in transcript:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    paths["agreement"].write_text(
        json.dumps(session.get("working_agreement") or {}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_alignment_manifest(session)


def write_alignment_validation_artifacts(session: dict, validation: dict, *, invocation_dir: Path) -> None:
    paths = alignment_artifact_paths(session)
    ensure_alignment_artifact_dirs(paths["root"])
    payload = json.dumps(validation, ensure_ascii=False, indent=2) + "\n"
    paths["validation"].write_text(payload, encoding="utf-8")
    invocation_dir.mkdir(parents=True, exist_ok=True)
    (invocation_dir / "validation.json").write_text(payload, encoding="utf-8")
    write_alignment_manifest(session)


def alignment_assistant_message_record(
    assistant_message: str,
    *,
    created_at: str,
    decision_options: list[dict] | None = None,
    missing_items: list[str] | None = None,
) -> AlignmentMessageRecord:
    entry = {"role": "assistant", "content": assistant_message, "created_at": created_at}
    normalized_options = normalize_alignment_decision_options(decision_options)
    if normalized_options:
        entry["decision_options"] = normalized_options
    if missing_items:
        entry["missing_items"] = list(missing_items)
    event_payload = {"role": "assistant", "content": assistant_message}
    if normalized_options:
        event_payload["decision_options"] = normalized_options
    if missing_items:
        event_payload["missing_items"] = list(missing_items)
    return AlignmentMessageRecord(entry=entry, event_payload=event_payload)


def alignment_user_message_record(user_message: str, *, created_at: str) -> AlignmentMessageRecord:
    return AlignmentMessageRecord(
        entry={"role": "user", "content": user_message, "created_at": created_at},
        event_payload={"role": "user", "content": user_message},
    )


def write_alignment_invocation_input_files(invocation_dir: Path, *, prompt: str, output_schema: dict) -> None:
    invocation_dir.mkdir(parents=True, exist_ok=True)
    (invocation_dir / "prompt.md").write_text(prompt.rstrip() + "\n", encoding="utf-8")
    (invocation_dir / "schema.json").write_text(
        json.dumps(output_schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (invocation_dir / "stdout.log").touch(exist_ok=True)
    (invocation_dir / "stderr.log").touch(exist_ok=True)


def alignment_bundle_content_fingerprint(bundle_yaml: str) -> dict[str, int | str]:
    data = bundle_yaml.encode("utf-8")
    return {"bundle_sha256": sha256(data).hexdigest(), "bundle_bytes": len(data)}


def alignment_output_debug_payload(output: dict, bundle_path: Path) -> dict:
    payload = dict(output) if isinstance(output, dict) else {}
    bundle_yaml = str(payload.pop("bundle_yaml", "") or "")
    if bundle_yaml:
        payload["bundle_written"] = True
        payload["bundle_path"] = str(bundle_path)
        payload.update(alignment_bundle_content_fingerprint(bundle_yaml))
    else:
        payload["bundle_written"] = False
        payload.setdefault("bundle_path", str(bundle_path))
        payload["bundle_sha256"] = ""
        payload["bundle_bytes"] = 0
    redacted_payload = redact_alignment_source_value(payload)
    return redacted_payload if isinstance(redacted_payload, dict) else {}


def finalize_alignment_invocation_files(invocation_dir: Path, output: dict, bundle_path: Path) -> None:
    schema_path = invocation_dir / "alignment_schema.json"
    if schema_path.exists() and not (invocation_dir / "schema.json").exists():
        schema_path.replace(invocation_dir / "schema.json")
    elif schema_path.exists():
        schema_path.unlink()
    (invocation_dir / "output.json").write_text(
        json.dumps(alignment_output_debug_payload(output, bundle_path), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def alignment_invocation_dir(root: Path, attempt: int, *, repair: bool) -> Path:
    suffix = "-repair" if repair else ""
    attempt_index = structured_non_negative_int(attempt)
    return Path(root) / "invocations" / f"{attempt_index + 1:04d}{suffix}"


def alignment_next_invocation_dir(root: Path, attempt: int, *, repair: bool) -> Path:
    suffix = "-repair" if repair else ""
    invocations_dir = Path(root) / "invocations"
    index = structured_non_negative_int(attempt) + 1
    while True:
        candidate = invocations_dir / f"{index:04d}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def alignment_latest_invocation_dir(root: Path) -> Path | None:
    invocations_dir = Path(root) / "invocations"
    if not invocations_dir.is_dir():
        return None
    candidates = [path for path in invocations_dir.iterdir() if path.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime_ns)


def write_alignment_validation_log(session: dict, validation: dict) -> None:
    paths = alignment_artifact_paths(session)
    attempt = alignment_repair_attempts(session)
    invocation_dir = alignment_latest_invocation_dir(paths["root"]) or alignment_invocation_dir(
        paths["root"],
        attempt,
        repair=attempt > 0,
    )
    write_alignment_validation_artifacts(session, validation, invocation_dir=invocation_dir)


def alignment_repair_attempts(session: dict | None, *, invalid_default: int = 0) -> int:
    if not session or session.get("repair_attempts") is None:
        return 0
    return structured_non_negative_int(session.get("repair_attempts"), default=invalid_default)

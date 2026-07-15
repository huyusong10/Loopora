from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from loopora.bundles import BundleError, bundle_to_yaml, load_bundle_text, read_bundle_file_text
from loopora.service_types import LooporaError
from loopora.utils import utc_now


from loopora.service_alignment_artifacts import alignment_bundle_content_fingerprint

def alignment_bundle_validation_success(
    bundle_path: Path,
    *,
    checked_at: str,
    normalized_yaml: str = "",
) -> dict:
    validation: dict = {
        "ok": True,
        "error": "",
        "bundle_path": str(bundle_path),
        "checked_at": checked_at,
        "semantic_lint": {"ok": True, "issues": []},
    }
    if normalized_yaml:
        validation.update(alignment_bundle_content_fingerprint(normalized_yaml))
    return validation

def alignment_bundle_validation_failure(
    bundle_path: Path,
    *,
    error: str,
    semantic_issues: list[str],
    checked_at: str,
) -> dict:
    return {
        "ok": False,
        "error": error,
        "bundle_path": str(bundle_path),
        "checked_at": checked_at,
        "semantic_lint": {"ok": not semantic_issues, "issues": list(semantic_issues)},
    }

def alignment_bundle_missing_file_validation(bundle_path: Path, *, checked_at: str) -> dict:
    error = f"alignment bundle does not exist: {bundle_path}"
    return {
        "ok": False,
        "error": error,
        "bundle_path": str(bundle_path),
        "checked_at": checked_at,
        "semantic_lint": {"ok": False, "issues": [error]},
    }


class AlignmentBundlePreviewBuilder(Protocol):
    def __call__(self, bundle: dict, *, source_path: str = "", validation: dict | None = None) -> dict: ...


@dataclass(frozen=True)
class AlignmentBundlePreviewContext:
    build_preview: AlignmentBundlePreviewBuilder
    load_validated_bundle_text: Callable[[dict, str, list[str]], tuple[dict, str]]
    now: Callable[[], str] = utc_now


def alignment_bundle_preview(context: AlignmentBundlePreviewContext, session: dict) -> dict:
    bundle_path = Path(session["bundle_path"])
    if not bundle_path.exists():
        return {
            "ok": False,
            "session": session,
            "yaml": "",
            "bundle": None,
            "validation": session.get("validation") or {"ok": False, "error": "bundle file does not exist"},
        }
    raw_yaml = ""
    semantic_issues: list[str] = []
    try:
        raw_yaml = read_bundle_file_text(bundle_path)
        if session["status"] in {"ready", "imported", "running_loop"}:
            bundle, normalized_yaml = context.load_validated_bundle_text(session, raw_yaml, semantic_issues)
            validation = alignment_bundle_validation_success(bundle_path, checked_at=context.now())
        else:
            bundle = load_bundle_text(raw_yaml)
            normalized_yaml = bundle_to_yaml(bundle)
            validation = session.get("validation") or {"ok": True, "bundle_path": str(bundle_path)}
    except (BundleError, LooporaError, OSError) as exc:
        return {
            "ok": False,
            "session": session,
            "yaml": raw_yaml,
            "bundle": None,
            "validation": alignment_bundle_validation_failure(
                bundle_path,
                error=str(exc),
                semantic_issues=semantic_issues,
                checked_at=context.now(),
            ),
        }
    preview = context.build_preview(
        bundle,
        source_path=str(bundle_path),
        validation=validation,
    )
    preview["session"] = session
    preview["yaml"] = normalized_yaml
    return preview

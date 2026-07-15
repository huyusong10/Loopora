from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from loopora.agent_native_adapter_contracts import normalize_agent_adapter_kind
from loopora.branding import state_dir_for_workdir
from loopora.service_types import LooporaError
from loopora.utils import utc_now


def resolve_adapter_project_root(workdir: Path | str | None) -> Path:
    root = Path(workdir or ".").expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise LooporaError(f"adapter project root does not exist: {root}")
    return root


def agent_context_binding_path(
    adapter: str,
    workdir: Path | str,
    *,
    context_id: str = "",
) -> Path:
    kind = normalize_agent_adapter_kind(adapter)
    root = resolve_adapter_project_root(workdir)
    key = agent_context_key(kind, root, context_id=context_id)
    return state_dir_for_workdir(root) / "agent_adapters" / kind / "bindings" / f"{key}.json"


def agent_context_key(adapter: str, workdir: Path | str, *, context_id: str = "") -> str:
    kind = normalize_agent_adapter_kind(adapter)
    root = resolve_adapter_project_root(workdir)
    context_identity = resolved_agent_context_id(kind, context_id=context_id)
    source = context_identity or f"workdir:{root}"
    return hashlib.sha256(f"{kind}:{source}".encode()).hexdigest()[:20]


def resolved_agent_context_id(adapter: str, *, context_id: str = "") -> str:
    kind = normalize_agent_adapter_kind(adapter)
    return (
        str(context_id or "").strip()
        or os.environ.get("LOOPORA_AGENT_SESSION_ID", "").strip()
        or _adapter_session_env(kind)
    )


def agent_context_source(adapter: str, *, context_id: str = "") -> str:
    kind = normalize_agent_adapter_kind(adapter)
    if str(context_id or "").strip():
        return "explicit"
    if os.environ.get("LOOPORA_AGENT_SESSION_ID", "").strip():
        return "loopora_env"
    if kind == "codex" and _adapter_session_env(kind):
        return "codex_env"
    if kind == "claude" and _adapter_session_env(kind):
        return "claude_env"
    if kind == "opencode" and _adapter_session_env(kind):
        return "opencode_env"
    return "workdir"


def write_agent_binding(
    adapter: str,
    workdir: Path | str,
    payload: dict[str, Any],
    *,
    context_id: str = "",
    entry_version: int,
) -> dict[str, Any]:
    path = agent_context_binding_path(adapter, workdir, context_id=context_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    kind = normalize_agent_adapter_kind(adapter)
    root = resolve_adapter_project_root(workdir)
    updated_at = utc_now()
    body = {
        "adapter": kind,
        "workdir": str(root),
        "context_key": path.stem,
        "context_source": agent_context_source(kind, context_id=context_id),
        "host_context_id": resolved_agent_context_id(kind, context_id=context_id),
        "entry_version": entry_version,
        "updated_at": updated_at,
        **payload,
    }
    body["context_card"] = _agent_context_card(kind, root, path, body, updated_at=updated_at)
    _atomic_write_text(path, json.dumps(body, ensure_ascii=False, indent=2) + "\n")
    return {**body, "path": str(path)}


def read_agent_binding(adapter: str, workdir: Path | str, *, context_id: str = "") -> dict[str, Any]:
    path = agent_context_binding_path(adapter, workdir, context_id=context_id)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LooporaError(f"agent context card is unreadable: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise LooporaError(f"agent context card is invalid: {path}")
    payload["path"] = str(path)
    return payload


def _agent_context_card(
    kind: str,
    root: Path,
    path: Path,
    body: dict[str, Any],
    *,
    updated_at: str,
) -> dict[str, Any]:
    previous_card = body.get("context_card") if isinstance(body.get("context_card"), dict) else {}
    started_at = str(previous_card.get("started_at") or body.get("started_at") or updated_at).strip()
    recovery_action = _agent_context_recovery_action(body)
    return {
        "schema_version": 1,
        "adapter": kind,
        "workdir": str(root),
        "context_key": path.stem,
        "context_source": str(body.get("context_source") or ""),
        "host_context_id": str(body.get("host_context_id") or ""),
        "alignment_session_id": str(body.get("alignment_session_id") or ""),
        "alignment_status": str(body.get("alignment_status") or ""),
        "linked_run_id": str(body.get("linked_run_id") or ""),
        "entry_version": body.get("entry_version"),
        "started_at": started_at,
        "updated_at": updated_at,
        "recovery_action": recovery_action,
    }


def _agent_context_recovery_action(body: dict[str, Any]) -> str:
    if body.get("requires_candidate_repair") is True:
        return "repair_candidate_plan_file"
    if body.get("requires_web_alignment") is True:
        return "finish_web_review"
    if str(body.get("linked_run_id") or "").strip():
        return "resume_run"
    if str(body.get("alignment_status") or "").strip() in {"ready", "imported"}:
        return "start_ready_preview"
    if str(body.get("alignment_session_id") or "").strip():
        return "preview_not_ready"
    return "plan_first"


def _adapter_session_env(kind: str) -> str:
    if kind == "codex":
        return os.environ.get("CODEX_SESSION_ID", "").strip() or os.environ.get("CODEX_THREAD_ID", "").strip()
    if kind == "claude":
        return os.environ.get("CLAUDE_SESSION_ID", "").strip()
    if kind == "opencode":
        return os.environ.get("OPENCODE_SESSION_ID", "").strip()
    return ""


def _atomic_write_text(path: Path, content: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)

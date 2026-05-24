from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_adapter_check_utils import (
    adapter_check,
    adapter_label,
    markdown_frontmatter,
    read_text_or_empty,
)


def adapter_entry_frontmatter_checks(kind: str, root: Path, entry_paths: list[str]) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    for entry_path in entry_paths:
        target = root / entry_path
        if not target.exists():
            continue
        metadata = markdown_frontmatter(read_text_or_empty(target))
        entry = "run" if entry_path.endswith("loopora-run.md") or "/loopora-run/" in entry_path else "plan"
        gaps = _entry_frontmatter_gaps(kind, entry, metadata)
        checks.append(
            adapter_check(
                "entry_frontmatter_contract",
                ok=not gaps,
                path=entry_path,
                message="" if not gaps else _entry_frontmatter_message(kind, entry, gaps),
            )
        )
    return checks


def _entry_frontmatter_gaps(kind: str, entry: str, metadata: dict[str, Any]) -> list[str]:
    if not metadata:
        return ["parseable frontmatter"]
    gaps = _common_entry_gaps(kind, entry, metadata)
    if kind == "claude":
        gaps.extend(_claude_entry_gaps(entry, metadata))
    if kind == "opencode":
        gaps.extend(_opencode_entry_gaps(entry, metadata))
    return gaps


def _common_entry_gaps(kind: str, entry: str, metadata: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if kind in {"codex", "claude"}:
        expected_name = f"loopora-{entry}"
        if metadata.get("name") != expected_name:
            gaps.append(f"name={expected_name}")
    if not str(metadata.get("description") or "").strip():
        gaps.append("description")
    return gaps


def _claude_entry_gaps(entry: str, metadata: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if metadata.get("disable-model-invocation") is not True:
        gaps.append("disable-model-invocation=true")
    allowed_tools = str(metadata.get("allowed-tools") or "")
    if f"loopora agent claude {entry}" not in allowed_tools:
        gaps.append(f"allowed-tools includes loopora agent claude {entry}")
    if entry == "run":
        gaps.extend(item for item in ("Agent", "Task") if item not in allowed_tools)
    return [f"allowed-tools includes {item}" if item in {"Agent", "Task"} else item for item in gaps]


def _opencode_entry_gaps(entry: str, metadata: dict[str, Any]) -> list[str]:
    if entry != "run":
        return []
    gaps: list[str] = []
    if metadata.get("agent") != "loopora-orchestrator":
        gaps.append("agent=loopora-orchestrator")
    if metadata.get("subtask") is not True:
        gaps.append("subtask=true")
    return gaps


def _entry_frontmatter_message(kind: str, entry: str, gaps: list[str]) -> str:
    return (
        f"{adapter_label(kind)} /loopora-{entry} entry must preserve discoverable frontmatter and native dispatch metadata; "
        f"drift: {', '.join(gaps)}; reinstall the adapter to restore the managed entry"
    )

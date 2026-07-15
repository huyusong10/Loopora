from __future__ import annotations

from pathlib import Path

from loopora.agent_adapter_manifest import adapter_check
from loopora.agent_native_adapter_contracts import (
    NATIVE_RUN_ENTRY_CONTRACT_BULLETS,
    NATIVE_RUN_ENTRY_CONTRACT_TITLE,
)


from typing import Any

from loopora.agent_adapter_manifest import (
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


def adapter_reference_paths(kind: str) -> list[str]:
    refs: set[str] = set()
    for reference_paths in adapter_entry_reference_map(kind).values():
        refs.update(reference_paths)
    return sorted(refs)


def adapter_supporting_files_checks(kind: str, root: Path) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    for entry_path, refs in adapter_entry_reference_map(kind).items():
        entry = root / entry_path
        try:
            entry_text = entry.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            entry_text = ""
        for ref in refs:
            ref_path = root / ref
            checks.append(
                adapter_check(
                    "supporting_file",
                    ok=ref_path.exists() and ref_path.is_file() and entry_mentions_reference(entry_text, ref),
                    path=ref,
                    message=f"referenced by {entry_path}",
                )
            )
    return checks


def entry_mentions_reference(entry_text: str, reference_path: str) -> bool:
    path = Path(reference_path)
    return reference_path in entry_text or path.name in entry_text or f"references/{path.name}" in entry_text


def adapter_entry_reference_map(kind: str) -> dict[str, tuple[str, ...]]:
    if kind == "codex":
        return {
            ".agents/skills/loopora-plan/SKILL.md": (".agents/skills/loopora-plan/references/loopora-plan-contract.md",),
            ".agents/skills/loopora-run/SKILL.md": (
                ".agents/skills/loopora-run/references/loopora-run-contract.md",
                ".agents/skills/loopora-run/references/loopora-recovery-matrix.md",
                ".agents/skills/loopora-run/references/loopora-result-template-guide.md",
                ".agents/skills/loopora-run/references/loopora-role-dispatch-guide.md",
            ),
        }
    if kind == "claude":
        return {
            ".claude/skills/loopora-plan/SKILL.md": (".claude/skills/loopora-plan/references/loopora-plan-contract.md",),
            ".claude/skills/loopora-run/SKILL.md": (
                ".claude/skills/loopora-run/references/loopora-run-contract.md",
                ".claude/skills/loopora-run/references/loopora-recovery-matrix.md",
                ".claude/skills/loopora-run/references/loopora-result-template-guide.md",
                ".claude/skills/loopora-run/references/loopora-role-dispatch-guide.md",
            ),
        }
    if kind == "opencode":
        return {
            ".opencode/commands/loopora-plan.md": (".opencode/loopora/references/loopora-plan-contract.md",),
            ".opencode/commands/loopora-run.md": (
                ".opencode/loopora/references/loopora-run-contract.md",
                ".opencode/loopora/references/loopora-recovery-matrix.md",
                ".opencode/loopora/references/loopora-result-template-guide.md",
                ".opencode/loopora/references/loopora-role-dispatch-guide.md",
            ),
        }
    return {}


def adapter_entry_shape_checks(kind: str, root: Path) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    entry_paths = list(adapter_entry_reference_map(kind))
    checks.extend(adapter_entry_frontmatter_checks(kind, root, entry_paths))
    for entry_path in entry_paths:
        target = root / entry_path
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = ""
        checks.append(adapter_check("entry_frontmatter", ok=text.startswith("---\n") and "\n---\n" in text[4:], path=entry_path))
        if entry_path_is_plan_entry(entry_path):
            checks.append(
                adapter_check(
                    "entry_is_interactive_plan_dispatcher",
                    ok=len(text.splitlines()) <= 80 and "interactive planning dispatcher" in text,
                    path=entry_path,
                )
            )
        else:
            checks.append(adapter_check("entry_is_thin_dispatcher", ok=len(text.splitlines()) <= 80 and "thin dispatcher" in text, path=entry_path))
        if entry_path_is_run_entry(entry_path):
            native_contract_ok = entry_has_native_run_contract(text)
            checks.append(
                adapter_check(
                    "entry_native_run_contract",
                    ok=native_contract_ok,
                    path=entry_path,
                    message="" if native_contract_ok else "managed /loopora-run entry is missing the native-run contract; reinstall the adapter",
                )
            )
    return checks


def entry_path_is_plan_entry(entry_path: str) -> bool:
    return "/loopora-plan/" in entry_path or entry_path.endswith("/loopora-plan.md")


def entry_path_is_run_entry(entry_path: str) -> bool:
    return "/loopora-run/" in entry_path or entry_path.endswith("/loopora-run.md")


def entry_has_native_run_contract(text: str) -> bool:
    return all(
        snippet in text
        for snippet in (NATIVE_RUN_ENTRY_CONTRACT_TITLE, *NATIVE_RUN_ENTRY_CONTRACT_BULLETS)
    )

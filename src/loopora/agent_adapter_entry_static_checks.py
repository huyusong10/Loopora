from __future__ import annotations

from pathlib import Path

from loopora.agent_adapter_check_utils import adapter_check
from loopora.agent_adapter_entry_checks import adapter_entry_frontmatter_checks
from loopora.agent_native_adapter_contracts import (
    NATIVE_RUN_ENTRY_CONTRACT_BULLETS,
    NATIVE_RUN_ENTRY_CONTRACT_TITLE,
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


def entry_path_is_run_entry(entry_path: str) -> bool:
    return "/loopora-run/" in entry_path or entry_path.endswith("/loopora-run.md")


def entry_has_native_run_contract(text: str) -> bool:
    return all(
        snippet in text
        for snippet in (NATIVE_RUN_ENTRY_CONTRACT_TITLE, *NATIVE_RUN_ENTRY_CONTRACT_BULLETS)
    )

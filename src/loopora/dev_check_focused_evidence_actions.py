from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.dev_check_command_projection import dev_check_final_pr_evidence_command, dev_check_focused_command
from loopora.dev_check_focus import DEFAULT_FOCUSED_SELECTION
from loopora.dev_check_focus import dedupe_text as _dedupe_text
from loopora.dev_check_focus import listed_focused_guide as _listed_focused_guide
from loopora.dev_check_guides import FOCUSED_CHECK_GUIDES
from loopora.dev_check_types import DevCheckReportContext


def completed_focused_run_guide_ids(*guide_id_lists: list[str]) -> list[str]:
    return _dedupe_text(guide_id for guide_ids in guide_id_lists for guide_id in guide_ids if guide_id)


def declared_focused_run_guide_ids(
    context: DevCheckReportContext,
    *,
    recommended_guides: list[dict[str, Any]],
) -> list[str]:
    if not context.focused_ran_tokens:
        return []
    focused_guides = [_listed_focused_guide(guide) for guide in FOCUSED_CHECK_GUIDES]
    all_guide_ids = set(focused_guide_ids(focused_guides))
    guide_ids: list[str] = []
    for token in context.focused_ran_tokens:
        if token == DEFAULT_FOCUSED_SELECTION:
            guide_ids.extend(focused_guide_ids(recommended_guides))
        elif token == "all":
            guide_ids.extend(focused_guide_ids(focused_guides))
        elif token in all_guide_ids:
            guide_ids.append(token)
    return _dedupe_text(guide_ids)


def focused_guide_ids(guides: list[dict[str, Any]]) -> list[str]:
    return [guide_id for guide in guides if (guide_id := str(guide.get("id") or "").strip())]


def focused_guides_cover_recommended(
    focused_ids: list[str],
    *,
    recommended_guides: list[dict[str, Any]],
) -> bool:
    recommended_ids = set(focused_guide_ids(recommended_guides))
    if not recommended_ids:
        return True
    return recommended_ids.issubset(set(focused_ids))


def recommended_focused_guides_covered(
    context: DevCheckReportContext,
    *,
    recommended_guides: list[dict[str, Any]],
) -> bool:
    recommended_ids = set(focused_guide_ids(recommended_guides))
    if not recommended_ids:
        return False
    declared_ids = declared_focused_run_guide_ids(context, recommended_guides=recommended_guides)
    return recommended_ids.issubset(set(declared_ids))


def pr_evidence_ready_action(
    recommended_guides: list[dict[str, Any]],
) -> dict[str, Any]:
    guide_ids = focused_guide_ids(recommended_guides)
    if not guide_ids:
        return {}
    return {
        "kind": "pr_evidence_ready",
        "guide_ids": guide_ids,
    }


def run_recommended_focused_checks_action(
    context: DevCheckReportContext,
    *,
    recommended_guides: list[dict[str, Any]],
    changed_files: list[str] | None = None,
) -> dict[str, Any]:
    if not recommended_guides:
        return {}
    return {
        "kind": "run_recommended_focused_checks",
        "guide_ids": focused_guide_ids(recommended_guides),
        "command": dev_check_focused_command(
            DEFAULT_FOCUSED_SELECTION,
            workdir=context.workdir,
            changed_files=changed_files,
        ),
    }


def run_remaining_recommended_focused_checks_action(
    context: DevCheckReportContext,
    *,
    recommended_guides: list[dict[str, Any]],
    completed_ids: list[str],
    changed_files: list[str] | None = None,
) -> dict[str, Any]:
    completed = set(completed_ids)
    remaining_guides = [guide for guide in recommended_guides if (guide_id := str(guide.get("id") or "").strip()) and guide_id not in completed]
    guide_ids = focused_guide_ids(remaining_guides)
    if not guide_ids:
        return {}
    return {
        "kind": "run_remaining_recommended_focused_checks",
        "guide_ids": guide_ids,
        "already_ran_guide_ids": [guide_id for guide_id in completed_ids if guide_id],
        "command": dev_check_focused_command(
            ",".join(guide_ids),
            workdir=context.workdir,
            changed_files=changed_files,
            focused_ran=completed_ids,
        ),
    }


def final_pr_evidence_gate_action(
    workdir: Path,
    *,
    focused_ran_ids: list[str],
    changed_files: list[str] | None = None,
) -> dict[str, Any]:
    guide_ids = [guide_id for guide_id in focused_ran_ids if guide_id]
    if not guide_ids:
        return {}
    return {
        "kind": "run_final_pr_evidence_gate",
        "guide_ids": guide_ids,
        "command": dev_check_final_pr_evidence_command(workdir=workdir, focused_ran_ids=guide_ids, changed_files=changed_files),
    }

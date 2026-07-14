from __future__ import annotations

from pathlib import Path
import shlex

import typer

from loopora.dev_check_command_projection import copyable_dev_check_command
from loopora.dev_check import DEFAULT_FAST_PROFILE, FOCUSED_PROFILE
from loopora.cli_dev_next_action_text import (
    dev_check_file_list_summary,
    dev_check_guide_suffix,
    dev_check_next_action_text,
    dev_check_next_summary,
)

DEV_CHECK_PR_EVIDENCE_SCHEMA_VERSION = 8
PR_EVIDENCE_PUBLIC_SAFETY_REMINDER = (
    "Public evidence: paste redacted diagnostic output only; use <project-dir>, <Loopora checkout>, or <redacted> "
    "instead of real local paths in command/path examples."
)


def dev_check_pr_evidence_payload(result: dict, *, focused_ran: list[str] | None = None) -> dict[str, object]:
    workdir = Path(str(result.get("workdir") or ".").strip() or ".")
    recommended_ids = _dev_check_guide_ids(result, "recommended_focused_guides")
    selected_ids = _dev_check_guide_ids(result, "selected_focused_guides")
    evidence_stage = _dev_check_pr_evidence_stage(result)
    focused_run_ids = _dev_check_declared_or_observed_focused_run_ids(
        result,
        focused_ran=focused_ran,
        recommended_ids=recommended_ids,
        selected_ids=selected_ids,
    )
    payload = {
        "schema_version": DEV_CHECK_PR_EVIDENCE_SCHEMA_VERSION,
        "evidence_stage": evidence_stage,
        "evidence_command_source": _dev_check_public_command_source(),
        "profile": str(result.get("profile") or DEFAULT_FAST_PROFILE),
        "status": str(result.get("status") or "unknown"),
        "decision_scope_evidence": _dev_check_decision_scope_evidence_text(evidence_stage),
        "changed_file_detection": _dev_check_detection_text(result),
        "recommended_focused_guide_ids": recommended_ids,
        "focused_guide_ids_run": focused_run_ids,
        "skipped_focused_guide_ids": _dev_check_skipped_focused_guide_ids(recommended_ids, focused_run_ids),
        "focused_ran_decision_note": _dev_check_focused_ran_decision_note(evidence_stage, focused_ran=focused_ran),
        "ignored_changed_files": _dev_check_changed_files_summary(result, key="ignored"),
        "unmatched_changed_files": _dev_check_changed_files_summary(result, key="unmatched"),
        "default_fast_gate": _dev_check_default_fast_gate_summary(result),
        "failed_step": _dev_check_failed_step_text(result),
        "package_build_cleanup": dev_check_package_build_cleanup_summary(workdir),
        "public_evidence_reminder": PR_EVIDENCE_PUBLIC_SAFETY_REMINDER,
        "next": dev_check_next_summary(result),
    }
    payload["template_markdown"] = _dev_check_pr_evidence_template_markdown(payload)
    return payload


def print_dev_check_pr_evidence_summary(result: dict) -> None:
    summary = result.get("pr_evidence_summary")
    if not isinstance(summary, dict):
        summary = dev_check_pr_evidence_payload(result)
    typer.echo("Loopora PR evidence summary")
    typer.echo(f"workdir: {result.get('workdir')}")
    typer.echo(f"evidence stage: {summary['evidence_stage']}")
    typer.echo(f"evidence command source: {summary.get('evidence_command_source') or _dev_check_public_command_source()}")
    typer.echo(f"dev check status: {summary['profile']} / {summary['status']}")
    typer.echo(f"changed-file detection: {summary['changed_file_detection']}")
    typer.echo(f"recommended focused guide IDs: {_dev_check_id_list_text(summary['recommended_focused_guide_ids'], empty='none')}")
    typer.echo(f"focused guide IDs run: {_dev_check_id_list_text(summary['focused_guide_ids_run'], empty='not run by this command')}")
    typer.echo(f"skipped focused guide IDs: {_dev_check_optional_id_list_text(summary.get('skipped_focused_guide_ids'))}")
    if summary.get("focused_ran_decision_note"):
        typer.echo(f"focused-ran decision note: {summary['focused_ran_decision_note']}")
    typer.echo(f"ignored changed files: {summary['ignored_changed_files']}")
    typer.echo(f"unmatched changed files: {summary['unmatched_changed_files']}")
    typer.echo(f"final default-fast gate: {summary['default_fast_gate']}")
    if summary.get("failed_step"):
        typer.echo(f"failed step: {summary['failed_step']}")
        _print_dev_check_pr_evidence_failed_step_output(result)
    typer.echo(f"package-build cleanup: {summary['package_build_cleanup']}")
    typer.echo(str(summary.get("public_evidence_reminder") or PR_EVIDENCE_PUBLIC_SAFETY_REMINDER))
    typer.echo(f"next: {summary['next']}")
    typer.echo("copyable PR evidence block:")
    typer.echo(str(summary.get("template_markdown") or "").rstrip())


def dev_check_package_build_cleanup_summary(workdir: Path) -> str:
    states = [
        f"{path.as_posix()} {'absent' if not (workdir / path).exists() else 'present'}" for path in (Path("tmp/package-check"), Path("src/loopora.egg-info"))
    ]
    return "; ".join(states)


def dev_check_focused_ran_tokens(values: list[str] | None) -> list[str]:
    return dev_check_selection_tokens(values)


def dev_check_selection_tokens(values: list[str] | None) -> list[str]:
    return dedupe_text(token for value in list(values or []) for token in str(value or "").replace(",", " ").split() if token)


def dedupe_text(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _print_dev_check_pr_evidence_failed_step_output(result: dict) -> None:
    failed_step = next(
        (step for step in list(result.get("steps") or []) if isinstance(step, dict) and step.get("status") == "fail"),
        {},
    )
    stdout = str(failed_step.get("stdout") or "").strip()
    stderr = str(failed_step.get("stderr") or "").strip()
    if not stdout and not stderr:
        return
    typer.echo("failed step output:")
    if stdout:
        typer.echo("  stdout:")
        typer.echo(_indent_block(stdout))
    if stderr:
        typer.echo("  stderr:")
        typer.echo(_indent_block(stderr))


def _indent_block(text: str) -> str:
    return "\n".join(f"    {line}" for line in str(text).splitlines())


def _dev_check_pr_evidence_template_markdown(summary: dict[str, object]) -> str:
    recommended_ids = _dev_check_id_list_text(summary.get("recommended_focused_guide_ids"), empty="none")
    focused_ids = _dev_check_id_list_text(summary.get("focused_guide_ids_run"), empty="not run by this command")
    skipped_ids = _dev_check_optional_id_list_text(summary.get("skipped_focused_guide_ids"))
    return "\n".join(
        [
            "### Loopora PR Evidence",
            f"- PR evidence stage: {summary.get('evidence_stage')}",
            f"- Evidence command source: `{summary.get('evidence_command_source') or _dev_check_public_command_source()}`",
            f"- Decision scope evidence: {summary.get('decision_scope_evidence')}",
            f"- Changed-file detection: {summary.get('changed_file_detection')}",
            f"- Recommended focused guide IDs: {recommended_ids}",
            f"- Unmatched changed files: {summary.get('unmatched_changed_files')}",
            f"- Ignored changed files: {summary.get('ignored_changed_files')}",
            f"- Focused guide IDs run: {focused_ids}",
            f"- Skipped recommended or boundary-relevant guide IDs: {skipped_ids}",
            *([f"- Focused-ran decision note: {summary.get('focused_ran_decision_note')}"] if summary.get("focused_ran_decision_note") else []),
            f"- Final dev-check result: {summary.get('default_fast_gate')}",
            *([f"- Failed step: {summary.get('failed_step')}"] if summary.get("failed_step") else []),
            f"- Package-build cleanup: {summary.get('package_build_cleanup')}",
            f"- Public evidence reminder: {summary.get('public_evidence_reminder') or PR_EVIDENCE_PUBLIC_SAFETY_REMINDER}",
        ]
    )


def _dev_check_pr_evidence_stage(result: dict) -> str:
    profile = str(result.get("profile") or DEFAULT_FAST_PROFILE)
    status = str(result.get("status") or "unknown")
    if profile == FOCUSED_PROFILE:
        return {"pass": "focused_passed", "fail": "focused_failed", "skipped": "focused_skipped"}.get(status, "focused_listed")
    return {"pass": "default_fast_passed", "fail": "default_fast_failed"}.get(status, "decision")


def _dev_check_decision_scope_evidence_text(evidence_stage: str) -> str:
    if evidence_stage == "decision":
        return "collected by this list-stage PR evidence command"
    return (
        "collected by this PR evidence command using the same changed-file, ignored-file, unmatched-file, "
        "and focused-recommendation scope as the list-stage PR evidence command"
    )


def _dev_check_public_command_source() -> str:
    try:
        tokens = shlex.split(copyable_dev_check_command(""))
    except ValueError:
        return "loopora dev check"
    tokens = [token for token in tokens if not _dev_check_public_command_env_token(token)]
    source = "loopora dev check"
    if len(tokens) >= 5 and tokens[:2] == ["uv", "--directory"] and tokens[3] == "run":
        runner = tokens[4:]
        if runner[:3] == ["python", "-m", "loopora"]:
            source = "uv --directory <Loopora checkout> run python -m loopora dev check"
        elif runner[:1] == ["loopora"]:
            source = "uv --directory <Loopora checkout> run loopora dev check"
    elif tokens[:3] == ["uv", "run", "loopora"]:
        source = "uv run loopora dev check"
    elif tokens[:5] == ["uv", "run", "python", "-m", "loopora"]:
        source = "uv run python -m loopora dev check"
    elif tokens[:3] == ["python", "-m", "loopora"]:
        source = "python -m loopora dev check"
    return source


def _dev_check_public_command_env_token(token: str) -> bool:
    name, separator, _value = str(token or "").partition("=")
    return bool(separator and name.startswith("LOOPORA_"))


def _dev_check_guide_ids(result: dict, key: str) -> list[str]:
    return [guide_id for guide in list(result.get(key) or []) if isinstance(guide, dict) and (guide_id := str(guide.get("id") or "").strip())]


def _dev_check_focused_run_ids(result: dict, *, selected_ids: list[str]) -> list[str]:
    if str(result.get("profile") or "") != "focused" or str(result.get("status") or "") == "listed":
        return []
    step_ids = [
        str(step.get("guide_id") or "").strip()
        for step in list(result.get("steps") or [])
        if isinstance(step, dict) and str(step.get("status") or "") != "skipped"
    ]
    return dedupe_text(step_ids) or selected_ids


def _dev_check_declared_or_observed_focused_run_ids(
    result: dict,
    *,
    focused_ran: list[str] | None,
    recommended_ids: list[str],
    selected_ids: list[str],
) -> list[str]:
    profile = str(result.get("profile") or DEFAULT_FAST_PROFILE)
    status = str(result.get("status") or "unknown")
    if profile == FOCUSED_PROFILE:
        if status == "listed":
            return []
        observed_ids = _dev_check_focused_run_ids(result, selected_ids=selected_ids)
        if status != "pass":
            return observed_ids
        declared_ids = _dev_check_declared_focused_run_ids(result, focused_ran=focused_ran, recommended_ids=recommended_ids)
        return dedupe_text([*declared_ids, *observed_ids])
    if status == "listed":
        return []
    return _dev_check_declared_focused_run_ids(result, focused_ran=focused_ran, recommended_ids=recommended_ids)


def _dev_check_declared_focused_run_ids(
    result: dict,
    *,
    focused_ran: list[str] | None,
    recommended_ids: list[str],
) -> list[str]:
    tokens = dev_check_focused_ran_tokens(focused_ran)
    if not tokens:
        return []
    guide_ids = _dev_check_guide_ids(result, "focused_guides")
    expanded: list[str] = []
    for token in tokens:
        if token == "recommended":
            expanded.extend(recommended_ids)
        elif token == "all":
            expanded.extend(guide_ids)
        else:
            expanded.append(token)
    return dedupe_text(expanded)


def _dev_check_focused_ran_decision_note(evidence_stage: str, *, focused_ran: list[str] | None) -> str:
    tokens = dev_check_focused_ran_tokens(focused_ran)
    if evidence_stage != "decision" or not tokens:
        return ""
    values = ", ".join(tokens)
    return f"received focused-ran values ({values}); --list decision evidence does not count them until the final non-list PR evidence command"


def _dev_check_skipped_focused_guide_ids(recommended_ids: list[str], focused_run_ids: list[str]) -> list[str] | None:
    if not focused_run_ids:
        return None
    ran = set(focused_run_ids)
    return [guide_id for guide_id in recommended_ids if guide_id not in ran]


def _dev_check_id_list_text(ids: object, *, empty: str) -> str:
    values = [str(value).strip() for value in list(ids or []) if str(value).strip()]
    return ", ".join(values) if values else empty


def _dev_check_optional_id_list_text(ids: object) -> str:
    if ids is None:
        return "not recorded by this command"
    return _dev_check_id_list_text(ids, empty="none")


def _dev_check_detection_text(result: dict) -> str:
    detection = result.get("changed_file_detection") if isinstance(result.get("changed_file_detection"), dict) else {}
    source = str(detection.get("source") or "unknown").strip() or "unknown"
    status = str(detection.get("status") or "unknown").strip() or "unknown"
    count = int(detection.get("count") or 0)
    return f"{source}/{status} ({count} file(s))"


def _dev_check_changed_files_summary(result: dict, *, key: str) -> str:
    count = int(result.get(f"{key}_changed_file_count") or 0)
    if count <= 0:
        return "none"
    files = [str(path) for path in list(result.get(f"{key}_changed_files") or []) if str(path).strip()]
    omitted = int(result.get(f"omitted_{key}_changed_file_count") or 0)
    return dev_check_file_list_summary(files, {"file_count": count, "omitted_file_count": omitted})


def _dev_check_default_fast_gate_summary(result: dict) -> str:
    profile = str(result.get("profile") or DEFAULT_FAST_PROFILE)
    status = str(result.get("status") or "unknown")
    return status if profile == DEFAULT_FAST_PROFILE and status != "listed" else "not run by this command"


def _dev_check_failed_step_text(result: dict) -> str:
    failed_step = result.get("failed_step") if isinstance(result.get("failed_step"), dict) else {}
    step_id = str(failed_step.get("id") or "").strip()
    if not step_id:
        return ""
    returncode = failed_step.get("returncode")
    code_text = f" (exit {returncode})" if returncode is not None else ""
    command = str(failed_step.get("command") or "").strip()
    return f"{step_id}{code_text}: {command}" if command else f"{step_id}{code_text}"


__all__ = (
    "DEV_CHECK_PR_EVIDENCE_SCHEMA_VERSION",
    "PR_EVIDENCE_PUBLIC_SAFETY_REMINDER",
    "dedupe_text",
    "dev_check_file_list_summary",
    "dev_check_focused_ran_tokens",
    "dev_check_guide_suffix",
    "dev_check_next_action_text",
    "dev_check_next_summary",
    "dev_check_package_build_cleanup_summary",
    "dev_check_pr_evidence_payload",
    "dev_check_selection_tokens",
    "print_dev_check_pr_evidence_summary",
)

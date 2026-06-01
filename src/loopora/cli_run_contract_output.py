from __future__ import annotations

import json
from pathlib import Path

import typer

from loopora.run_takeaway_judgment import build_judgment_contract


def print_run_contract_summary(result: dict) -> None:
    runs_dir = str(result.get("runs_dir") or "").strip()
    if not runs_dir:
        return
    run_contract_path = Path(runs_dir) / "contract" / "run_contract.json"
    if not run_contract_path.exists() or not run_contract_path.is_file():
        return
    try:
        run_contract = json.loads(run_contract_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return
    if not isinstance(run_contract, dict):
        return
    judgment_contract = build_judgment_contract(result)
    typer.echo(f"run_contract_path: {run_contract_path}")
    _print_run_contract_source_bundle(judgment_contract)
    judgment_summary = _cli_judgment_summary(judgment_contract)
    if judgment_summary:
        typer.echo(f"judgment_contract_summary: {judgment_summary}")
    _print_run_contract_execution_fields(judgment_contract)
    _print_run_contract_list("loop_fit_reasons", _cli_loop_fit_reasons(judgment_contract))
    _print_run_contract_list("judgment_tradeoffs", _cli_judgment_tradeoffs(judgment_contract))
    _print_run_contract_list("execution_strategy", _cli_execution_strategy(judgment_contract))
    _print_run_contract_list("local_governance", _cli_local_governance(judgment_contract))
    _print_run_contract_list("role_postures", _cli_role_postures(judgment_contract))
    _print_run_contract_judgment_fields(judgment_contract)


def _print_run_contract_list(key: str, values: list[str]) -> None:
    if not values:
        return
    typer.echo(f"{key}:")
    for value in values:
        typer.echo(f"- {value}")


def _print_run_contract_source_bundle(judgment_contract: dict) -> None:
    source_bundle = judgment_contract.get("source_bundle")
    if not isinstance(source_bundle, dict) or not source_bundle.get("id"):
        return
    source_id = str(source_bundle.get("id") or "").strip()
    source_name = str(source_bundle.get("name") or "").strip()
    revision = source_bundle.get("revision")
    revision_text = f", rev {revision}" if isinstance(revision, int) and not isinstance(revision, bool) else ""
    label = source_name or source_id
    id_text = f" ({source_id}{revision_text})" if source_name and source_id else revision_text
    typer.echo(f"source_plan: {label}{id_text}")
    imported_from = str(source_bundle.get("imported_from_path") or "").strip()
    if imported_from:
        typer.echo(f"source_plan_path: {imported_from}")
    bundle_path = str(source_bundle.get("bundle_yaml_path") or "").strip()
    if bundle_path and bundle_path != imported_from:
        typer.echo(f"source_plan_archive: {bundle_path}")
    sha = str(source_bundle.get("bundle_sha256") or "").strip()
    bundle_bytes = source_bundle.get("bundle_bytes")
    if sha:
        digest = sha[:12]
        size = f", {bundle_bytes} bytes" if isinstance(bundle_bytes, int) and not isinstance(bundle_bytes, bool) else ""
        typer.echo(f"source_plan_digest: sha256:{digest}{size}")


def _print_run_contract_execution_fields(judgment_contract: dict) -> None:
    for key in ("check_mode", "completion_mode", "strategy_preset", "strategy_collaboration_intent"):
        value = _cli_judgment_contract_text(judgment_contract, key)
        if value:
            typer.echo(f"{key}: {value}")
    check_count = judgment_contract.get("check_count")
    if isinstance(check_count, int) and not isinstance(check_count, bool) and check_count > 0:
        typer.echo(f"check_count: {check_count}")
    _print_run_contract_list("coverage_targets", _cli_coverage_targets(judgment_contract))


def _print_run_contract_judgment_fields(run_contract: dict) -> None:
    for key in ("success_surface", "fake_done_states", "evidence_preferences"):
        _print_run_contract_list(key, _cli_judgment_contract_list(run_contract, key))
    residual_risk = _cli_judgment_contract_text(run_contract, "residual_risk")
    if residual_risk:
        typer.echo(f"residual_risk: {residual_risk}")


def _cli_judgment_summary(run_contract: dict) -> str:
    compiled_spec = run_contract.get("compiled_spec") if isinstance(run_contract.get("compiled_spec"), dict) else {}
    workflow = run_contract.get("workflow") if isinstance(run_contract.get("workflow"), dict) else {}
    for value in (
        run_contract.get("collaboration_summary"),
        run_contract.get("goal"),
        compiled_spec.get("goal"),
        run_contract.get("strategy_collaboration_intent"),
        workflow.get("collaboration_intent"),
        run_contract.get("residual_risk"),
        compiled_spec.get("residual_risk"),
    ):
        if isinstance(value, str) and value.strip():
            return _clip_cli_text(value.strip(), 240)
    for values in (
        compiled_spec.get("success_surface"),
        compiled_spec.get("fake_done_states"),
        compiled_spec.get("evidence_preferences"),
    ):
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str) and value.strip():
                return _clip_cli_text(value.strip(), 240)
    return ""


def _cli_loop_fit_reasons(run_contract: dict) -> list[str]:
    values = run_contract.get("loop_fit_reasons")
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()][:4]


def _cli_judgment_tradeoffs(run_contract: dict) -> list[str]:
    values = run_contract.get("judgment_tradeoffs")
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()][:4]


def _cli_execution_strategy(run_contract: dict) -> list[str]:
    values = run_contract.get("execution_strategy")
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()][:4]


def _cli_local_governance(run_contract: dict) -> list[str]:
    values = run_contract.get("local_governance")
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()][:4]


def _cli_role_postures(run_contract: dict) -> list[str]:
    values = run_contract.get("role_postures")
    if not isinstance(values, list):
        workflow = run_contract.get("workflow") if isinstance(run_contract.get("workflow"), dict) else {}
        values = workflow.get("roles")
    if not isinstance(values, list):
        return []
    postures: list[str] = []
    for item in values:
        if isinstance(item, dict):
            posture = str(item.get("posture_notes") or "").strip()
            if not posture:
                continue
            role_name = str(item.get("role_name") or item.get("name") or "").strip()
            archetype = str(item.get("archetype") or "").strip()
            label = role_name or archetype
            if label and archetype and archetype not in label.lower():
                label = f"{label} ({archetype})"
            postures.append(f"{label}: {posture}" if label else posture)
            continue
        text = str(item or "").strip()
        if text:
            postures.append(text)
    return postures[:6]


def _cli_judgment_contract_list(run_contract: dict, key: str) -> list[str]:
    values = run_contract.get(key)
    if not isinstance(values, list):
        compiled_spec = run_contract.get("compiled_spec") if isinstance(run_contract.get("compiled_spec"), dict) else {}
        values = compiled_spec.get(key)
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()][:4]


def _cli_judgment_contract_text(run_contract: dict, key: str) -> str:
    value = run_contract.get(key)
    if not isinstance(value, str) or not value.strip():
        compiled_spec = run_contract.get("compiled_spec") if isinstance(run_contract.get("compiled_spec"), dict) else {}
        value = compiled_spec.get(key)
    return _clip_cli_text(str(value or "").strip(), 600) if isinstance(value, str) else ""


def _cli_coverage_targets(judgment_contract: dict) -> list[str]:
    values = judgment_contract.get("coverage_targets")
    if not isinstance(values, list):
        return []
    targets: list[str] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("id") or item.get("target_id") or "").strip()
        if not target_id:
            continue
        suffix = " (required)" if item.get("required") is True else ""
        targets.append(f"{target_id}{suffix}")
    return targets


def _clip_cli_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(limit - 3, 0)].rstrip() + "..."

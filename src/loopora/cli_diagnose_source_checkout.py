from __future__ import annotations

from pathlib import Path

import typer

from loopora.agent_adapter_command_prefix import copyable_loopora_command
from loopora.cli_shared import echo_json
from loopora.diagnose_doctor import (
    DOCTOR_PUBLIC_SCHEMA_VERSION,
    DOCTOR_SCHEMA_VERSION,
)
from loopora.diagnose_doctor_identity import package_identity_report, package_source_label
from loopora.diagnose_doctor_web_state import DEFAULT_WEB_HOST, DEFAULT_WEB_PORT


def exit_if_source_checkout_target_required(  # noqa: PLR0913 - shared Doctor target gate mirrors CLI options.
    *,
    workdir: Path | None,
    web_host: str,
    web_port: int,
    json_output: bool,
    public_json_output: bool,
    language: str = "en",
) -> None:
    if workdir is not None or not doctor_source_checkout_needs_target_project(Path.cwd()):
        return
    payload = source_checkout_target_project_payload(web_host=web_host, web_port=web_port)
    if public_json_output:
        echo_json(source_checkout_public_target_project_payload())
    elif json_output:
        echo_json(payload)
    else:
        print_source_checkout_target_project(payload, language=language)
    raise typer.Exit(code=1)


def doctor_source_checkout_needs_target_project(cwd: Path) -> bool:
    return (cwd / "pyproject.toml").is_file() and (cwd / "src" / "loopora").is_dir()


def source_checkout_target_project_payload(*, web_host: str, web_port: int) -> dict:
    web_args = _doctor_web_args(web_host=web_host, web_port=web_port)
    doctor_command = copyable_loopora_command(f'loopora doctor --workdir "$PWD"{web_args}')
    fit_command = copyable_loopora_command('loopora fit --workdir "$PWD"')
    support_command = copyable_loopora_command(f'loopora support --workdir "$PWD"{web_args}')
    payload = {
        "schema_version": DOCTOR_SCHEMA_VERSION,
        "status": "target_required",
        "ready": False,
        "agent_entry_ready": False,
        "strict_ready": False,
        "target_project_required": True,
        "workdir": "",
        "workdir_state": {
            "status": "required",
            "workdir": "",
            "needs_attention": True,
            "summary": "Target project directory is required before checking same-Agent readiness from a source checkout.",
        },
        "package": package_identity_report(),
        "next_action_items": [
            {"kind": "choose_workdir", "command": doctor_command, "command_ready": True, "command_blockers": []},
            {"kind": "check_fit_first", "command": fit_command, "command_ready": True, "command_blockers": []},
            {"kind": "support", "command": support_command, "command_ready": True, "command_blockers": []},
        ],
        "next_action_kinds": ["choose_workdir", "check_fit_first", "support"],
    }
    payload["next_steps"] = [
        f"Rerun doctor from the target project before installing same-Agent project entries: {doctor_command}",
        f"If task fit is uncertain, run the fit guide from the target project first: {fit_command}",
        f"Usage/setup help from the target project: {support_command}",
    ]
    return payload


def source_checkout_public_target_project_payload() -> dict:
    return {
        "doctor_schema_version": DOCTOR_PUBLIC_SCHEMA_VERSION,
        "status": "target_required",
        "ready": False,
        "agent_entry_ready": False,
        "strict_ready": False,
        "target_project_required": True,
        "project_directory_status": "required",
        "next_actions": ["choose_project_directory", "check_fit_first", "support"],
        "next_action_summaries": [
            {
                "kind": "choose_project_directory",
                "summary": "Choose a usable target project before checking same-Agent readiness.",
            },
            {
                "kind": "check_fit_first",
                "summary": "If task fit is uncertain, run the fit guide before installing same-Agent project entries.",
            },
            {"kind": "support", "summary": "Open usage/setup support guidance for redacted public reporting."},
        ],
        "package": _public_package_identity(),
        "environment": _public_environment_identity(),
    }


def print_source_checkout_target_project(payload: dict, *, language: str = "en") -> None:
    if language == "zh":
        _print_source_checkout_target_project_zh(payload)
        return
    typer.echo("Loopora doctor: target_required")
    typer.echo("same-Agent project entry ready: no")
    typer.echo("readiness summary: target project directory is required before same-Agent readiness can be checked.")
    steps = [str(item).strip() for item in list(payload.get("next_steps") or []) if str(item).strip()]
    if steps:
        typer.echo(f"primary next action: {steps[0]}")
    typer.echo("project directory: not supplied")
    package = payload.get("package") if isinstance(payload.get("package"), dict) else {}
    if package:
        source = package_source_label(package)
        source_note = f"; {source}" if source else ""
        typer.echo(f"package: loopora {package.get('version')} (Python {package.get('python')}{source_note})")
    typer.echo("next:")
    for step in steps:
        typer.echo(f"- {step}")


def _print_source_checkout_target_project_zh(payload: dict) -> None:
    actions = [item for item in list(payload.get("next_action_items") or []) if isinstance(item, dict)]
    commands = {str(action.get("kind") or ""): _localized_source_checkout_command(action) for action in actions}
    steps = [
        f"从目标项目重跑 Doctor，再安装同一 Agent 项目入口：{commands.get('choose_workdir', '')}",
        f"如果还不确定任务是否适合，先从目标项目运行 fit 指南：{commands.get('check_fit_first', '')}",
        f"从目标项目查看使用/设置支持：{commands.get('support', '')}",
    ]
    typer.echo("Loopora Doctor：需要目标项目（target_required）")
    typer.echo("同一 Agent 项目入口就绪：否")
    typer.echo("就绪摘要：检查同一 Agent 就绪状态前，需要明确目标项目目录。")
    typer.echo(f"首要下一步：{steps[0]}")
    typer.echo("项目目录：未提供")
    package = payload.get("package") if isinstance(payload.get("package"), dict) else {}
    if package:
        source = package_source_label(package).replace("source ", "源码 ", 1)
        source_note = f"；{source}" if source else ""
        typer.echo(f"包：loopora {package.get('version')}（Python {package.get('python')}{source_note}）")
    typer.echo("下一步：")
    for step in steps:
        typer.echo(f"- {step}")


def _localized_source_checkout_command(action: dict) -> str:
    command = str(action.get("command") or "").strip()
    return command if not command or "--language" in command else f"{command} --language zh"


def _doctor_web_args(*, web_host: str, web_port: int) -> str:
    args: list[str] = []
    if web_host != DEFAULT_WEB_HOST:
        args.append(f"--web-host {web_host}")
    if web_port != DEFAULT_WEB_PORT:
        args.append(f"--web-port {web_port}")
    return f" {' '.join(args)}" if args else ""


def _public_package_identity() -> dict[str, object]:
    package = package_identity_report()
    return {
        "name": package.get("name"),
        "version": package.get("version"),
        "source_revision": package.get("source_revision"),
        "source_tree_status": package.get("source_tree_status"),
        "python": package.get("python"),
    }


def _public_environment_identity() -> dict[str, object]:
    package = package_identity_report()
    return {
        "python_implementation": package.get("python_implementation"),
        "os": package.get("os"),
        "machine": package.get("machine"),
    }

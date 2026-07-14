from __future__ import annotations

from typing import Annotated

import typer
import uvicorn

from loopora.agent_adapter_command_prefix import current_project_file_loopora_cli_entry
from loopora.cli_shared import handle_error
from loopora.demo_environment import normalize_demo_language, seeded_demo_environment
from loopora.runtime_task_language import runtime_task_text
from loopora.service import LooporaError
from loopora.serve_browser_open import schedule_browser_open_if_requested
from loopora.web import build_app
from loopora.web_bind_preflight import next_available_web_port, probe_web_bind
from loopora.web_url_utils import with_query_params


DemoOpenOption = Annotated[
    bool,
    typer.Option("--open", help="Open the completed sample Run in the default browser."),
]
DemoLanguageOption = Annotated[
    str,
    typer.Option("--language", help="Demo task, evidence, verdict, and terminal language: en or zh."),
]
DemoPortOption = Annotated[
    str,
    typer.Option("--port", help="Preferred loopback port; an available nearby port is selected when occupied."),
]


def register_demo_command(app: typer.Typer) -> None:
    @app.command()
    def demo(
        port: DemoPortOption = "8743",
        language: DemoLanguageOption = "en",
        *,
        open_browser: DemoOpenOption = False,
    ) -> None:
        """Open an isolated completed Loop with simulated evidence."""
        try:
            normalized_language = normalize_demo_language(language)
            selected_port = _available_demo_port(_normalize_demo_port(port))
            with seeded_demo_environment(language=normalized_language) as environment:
                origin = f"http://127.0.0.1:{selected_port}"
                browser_url = f"{origin}{environment.run_path}"
                playground_path = with_query_params(
                    "/loops/new/bundle",
                    alignment_workdir=str(environment.playground_workdir),
                )
                playground_url = f"{origin}{playground_path}"
                real_task_command = demo_real_task_start_command(normalized_language)
                typer.echo("Loopora Demo")
                typer.echo(
                    runtime_task_text(
                        normalized_language,
                        "mode: isolated temporary App state with a simulated executor",
                        "模式：使用模拟 executor 的隔离临时 App 状态",
                    )
                )
                typer.echo(_demo_result_line(environment.run, language=normalized_language))
                typer.echo(runtime_task_text(normalized_language, f"browser: {browser_url}", f"浏览器：{browser_url}"))
                typer.echo(
                    runtime_task_text(
                        normalized_language,
                        f"try creating a Loop: {playground_url}",
                        f"试着创建 Loop：{playground_url}",
                    )
                )
                typer.echo(
                    runtime_task_text(
                        normalized_language,
                        f"real task: after stopping Demo, run this from the target project: {real_task_command}",
                        f"真实任务：停止 Demo 后，在目标项目目录运行：{real_task_command}",
                    )
                )
                typer.echo(
                    runtime_task_text(
                        normalized_language,
                        "lifecycle: keep this command running; press Ctrl-C to stop and delete all demo data",
                        "生命周期：保持此命令运行；按 Ctrl-C 停止并删除全部 Demo 数据",
                    )
                )
                web_app = build_app(
                    service=environment.service,
                    bind_host="127.0.0.1",
                    bind_port=selected_port,
                    startup_workdir=str(environment.workdir),
                    demo_mode=True,
                    demo_evidence_path=environment.run_path,
                    demo_playground_workdir=str(environment.playground_workdir),
                    demo_workdir_root=str(environment.root),
                    demo_real_task_command=real_task_command,
                )
                schedule_browser_open_if_requested(browser_url if open_browser else "")
                uvicorn.run(web_app, host="127.0.0.1", port=selected_port, log_level="info", access_log=False)
        except LooporaError as exc:
            handle_error(exc)


def _normalize_demo_port(value: str) -> int:
    try:
        port = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise LooporaError("demo port must be an integer from 1 to 65535") from exc
    if not 1 <= port <= 65535:
        raise LooporaError("demo port must be an integer from 1 to 65535")
    return port


def _available_demo_port(port: int) -> int:
    try:
        probe_web_bind("127.0.0.1", port)
        return port
    except OSError:
        alternate = next_available_web_port(host="127.0.0.1", port=port)
        if alternate is None:
            raise LooporaError("no available loopback port was found for the demo") from None
        return alternate


def _demo_result_line(run: dict, *, language: str) -> str:
    run_status = str(run.get("status") or "")
    task_status = str((run.get("task_verdict") or {}).get("status") or "")
    if language == "zh":
        localized_run_status = {"succeeded": "运行成功", "failed": "运行失败", "stopped": "运行已停止"}.get(
            run_status,
            run_status,
        )
        localized_task_status = {
            "passed": "任务裁决通过",
            "passed_with_residual_risk": "任务裁决通过，但仍有残余风险",
            "failed": "任务裁决失败",
            "insufficient_evidence": "任务证据不足",
            "not_evaluated": "任务尚未裁决",
        }.get(task_status, task_status)
        return f"结果：{localized_run_status} / {localized_task_status}"
    return f"result: {run_status} / task verdict {task_status}"


def demo_real_task_start_command(language: str) -> str:
    normalized_language = normalize_demo_language(language)
    return f'{current_project_file_loopora_cli_entry()} start --workdir "$PWD" --language {normalized_language}'

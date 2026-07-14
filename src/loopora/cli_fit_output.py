from __future__ import annotations

import typer

from loopora.agent_adapter_command_prefix import current_copyable_loopora_cli_entry
from loopora.cli_fit_output_common import (
    fit_text as _fit_text,
    payload_dict_list as _payload_dict_list,
    payload_language as _payload_language,
    payload_list as _payload_list,
)
from loopora.cli_fit_review_output import (
    print_direct_path_next_actions as _print_direct_path_next_actions,
    print_fit_review_questions as _print_fit_review_questions,
    print_incomplete_task_fit_next_step as _print_incomplete_task_fit_next_step,
    print_task_fit_review as _print_task_fit_review,
    task_fit_review_needs_completion as _task_fit_review_needs_completion,
    task_fit_review_prefers_direct as _task_fit_review_prefers_direct,
)
from loopora.cli_fit_route_output import print_fit_ready_next_actions as _print_fit_ready_next_actions


def fit_cli_entry() -> str:
    return current_copyable_loopora_cli_entry()


def print_fit_guidance(payload: dict[str, object]) -> None:
    language = _payload_language(payload)
    typer.echo(_fit_text(language, "Loopora fit guide", "Loopora 适配指南"))
    typer.echo(
        _fit_text(
            language,
            "Decision guide: not an automatic classifier; use it to make and record your own fit judgment.",
            "决策指南：不是自动分类器；请用它形成并记录你自己的适配判断。",
        )
    )
    typer.echo(_fit_text(language, "Use Loopora when:", "适合用 Loopora 的情况:"))
    for item in _payload_list(payload, "strong_fit_signals"):
        typer.echo(f"- {item}")
    typer.echo(
        _fit_text(
            language,
            "Prefer direct Agent, /goal, or hard checks when:",
            "更适合直接用 Agent、/goal 或硬性检查的情况:",
        )
    )
    for item in _payload_list(payload, "prefer_direct_agent_or_checks"):
        typer.echo(f"- {item}")
    has_task_review = isinstance(payload.get("task_fit_review"), dict)
    if has_task_review:
        _print_task_fit_review(payload, language=language)
    else:
        _print_fit_review_questions(_payload_dict_list(payload, "task_review_questions"), language=language)
        typer.echo(
            _fit_text(
                language,
                "No first /loopora-plan message yet: fill --task, --fit-reason, --fake-done, --evidence, and --tradeoffs to generate one.",
                "还没有第一条 /loopora-plan 消息：先补齐 --task、--fit-reason、--fake-done、--evidence 和 --tradeoffs 才会生成。",
            )
        )
    if _task_fit_review_prefers_direct(payload):
        _print_direct_path_next_actions(payload, language=language)
        return
    _print_direct_path_next_actions(payload, language=language)
    if _task_fit_review_needs_completion(payload):
        _print_incomplete_task_fit_next_step(payload, language=language)
        return
    _print_fit_ready_next_actions(payload, language=language)

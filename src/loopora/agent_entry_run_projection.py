from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_adapters import agent_loop_command, agent_loop_json_command
from loopora.agent_native_next_step_summary import agent_next_step_continuation_summary
from loopora.agent_native_surface import attach_native_run_surface
from loopora.agent_native_task_proof import agent_task_proof_summary
from loopora.run_takeaways import build_judgment_contract
from loopora.utils import utc_now


def agent_entry_loop_command(
    adapter: str,
    workdir: Path | str,
    entry_source: str = "",
    *,
    context_id: str = "",
    source_option_id: str = "",
) -> str:
    return agent_loop_command(
        adapter,
        workdir,
        entry_source=entry_source,
        context_id=context_id,
        source_option_id=source_option_id,
    )


def agent_entry_loop_json_command(
    adapter: str,
    workdir: Path | str,
    entry_source: str = "",
    *,
    context_id: str = "",
    source_option_id: str = "",
) -> str:
    return agent_loop_json_command(
        adapter,
        workdir,
        entry_source=entry_source,
        context_id=context_id,
        source_option_id=source_option_id,
    )


def agent_entry_loop_projection_messages(next_loop_action: str) -> dict[str, str]:
    if next_loop_action == "start_next_run_for_unproven_verdict":
        return {
            "message_zh": (
                "上一轮已经到达终态，但 Loop 裁决仍未证明任务通过；回到同一个 Agent 执行 /loopora-run "
                "会基于这份已审查 Loop 开启下一轮，继续补齐证据缺口。"
            ),
            "message_en": (
                "The previous run reached a terminal lifecycle state, but the task verdict is still not proven; "
                "run /loopora-run in the same Agent to start the next run from this reviewed Loop and keep closing evidence gaps."
            ),
        }
    return {
        "message_zh": (
            "这个 Loop 来自当前 Coding Agent 的 /loopora-plan；继续运行必须回到同一个 Agent 执行 /loopora-run，"
            "避免 Web 悄悄切到后台 headless worker。"
        ),
        "message_en": (
            "This Loop came from the current Coding Agent via /loopora-plan; continue it from the same Agent "
            "with /loopora-run so Web does not silently switch to a headless worker."
        ),
    }


def agent_loop_result(adapter: str, root: Path, session: dict[str, Any], binding: dict[str, Any], run_result: dict[str, Any]) -> dict[str, Any]:
    run = run_result["run"]
    summary = agent_loop_summary(adapter, run, run_result)
    return {
        "adapter": adapter,
        "workdir": str(root),
        "status": session["status"],
        "agent_run_summary": summary,
        "session": session,
        "binding": binding,
        "run": run,
        "judgment_contract": build_judgment_contract(run),
        "run_path": f"/runs/{run['id']}",
        "started_new_run": bool(run_result["started_new_run"]),
        "execution_plane": "agent_native",
        "next_step": run_result.get("next_step"),
        "complete": bool(run_result.get("complete", False)),
        "task_next_action": run_result.get("task_next_action") if isinstance(run_result.get("task_next_action"), dict) else {},
    }


def agent_loop_summary(adapter: str, run: dict[str, Any], run_result: dict[str, Any]) -> dict[str, Any]:
    next_step = run_result.get("next_step") if isinstance(run_result.get("next_step"), dict) else {}
    role_dispatch = next_step.get("role_dispatch") if isinstance(next_step.get("role_dispatch"), dict) else {}
    task_verdict = run.get("task_verdict") if isinstance(run.get("task_verdict"), dict) else run.get("task_verdict_json")
    task_verdict = task_verdict if isinstance(task_verdict, dict) else {}
    task_next_action = run_result.get("task_next_action") if isinstance(run_result.get("task_next_action"), dict) else {}
    run_id = str(run.get("id") or "").strip()
    task_verdict_status = str(task_verdict.get("status") or "").strip()
    task_verdict_summary = str(task_verdict.get("summary") or "").strip()
    target_agent = str(role_dispatch.get("target_agent") or next_step.get("target_agent") or "").strip()
    summary = {
        "schema_version": 1,
        "run_id": run_id,
        "run_status": str(run.get("status") or run.get("run_status") or "").strip(),
        "started_new_run": bool(run_result.get("started_new_run")),
        "complete": bool(run_result.get("complete", False)),
        "next_step_id": str(next_step.get("step_id") or "").strip(),
        "next_target_agent": target_agent,
        "task_verdict_status": task_verdict_status,
        "task_verdict_summary": task_verdict_summary,
        "task_next_action": task_next_action,
        "run_path": f"/runs/{run_id}" if run_id else "",
    }
    attach_native_run_surface(summary, adapter=adapter)
    if target_agent and role_dispatch.get("target_agent_config_exists") is not False:
        summary["dispatch_next"] = f"invoke {target_agent} with the next context/capsule paths below; do not perform this role inline"
    native_todo = next_step.get("native_todo") if isinstance(next_step.get("native_todo"), dict) else {}
    if native_todo:
        summary["native_todo"] = native_todo
    native_trace_contract = role_dispatch.get("native_trace_contract") if isinstance(role_dispatch.get("native_trace_contract"), dict) else {}
    if native_trace_contract:
        summary["native_trace_contract"] = native_trace_contract
    summary.update(
        agent_task_proof_summary(
            complete=bool(run_result.get("complete", False)),
            task_verdict_status=task_verdict_status,
            task_verdict_summary=task_verdict_summary,
            task_next_action=task_next_action,
        )
    )
    summary.update(agent_next_step_continuation_summary(next_step))
    return summary


def agent_loop_unready_error(adapter: str, binding: dict[str, Any], session: dict[str, Any]) -> str:
    label = adapter_label_for_error(adapter)
    status = str(session.get("status") or "").strip() or "unknown"
    if binding.get("requires_candidate_repair"):
        validation = session.get("validation") if isinstance(session.get("validation"), dict) else {}
        error = str(session.get("error_message") or validation.get("error") or "").strip()
        detail = f": {error}" if error else ""
        if binding.get("loopora_fit_contradiction"):
            return (
                f"{label} Loop preview is blocked before /loopora-run because the task summary looked one-off, "
                f"direct-answer, no-new-evidence, or benchmark/test-harness-only (current status: {status}); define later evidence, handoff, "
                f"or GateKeeper value, then rerun /loopora-plan with a reframed or repaired candidate{detail}"
            )
        return (
            f"{label} Loop preview needs plan file repair before /loopora-run "
            f"(current status: {status}); rerun /loopora-plan with a repaired candidate or continue Web review{detail}"
        )
    if binding.get("requires_web_alignment"):
        if binding.get("loopora_fit_contradiction"):
            return (
                f"{label} Loop preview needs Web review before /loopora-run "
                f"(current status: {status}); the task summary looked one-off, direct-answer, no-new-evidence, or benchmark/test-harness-only, "
                "so define later evidence, handoff, or GateKeeper value in /loopora-plan or Web review first"
            )
        return (
            f"{label} Loop preview needs Web review before /loopora-run "
            f"(current status: {status}); continue /loopora-plan or Web review first"
        )
    return ""


def append_agent_entry_invocation(binding: dict[str, Any], *, action: str, entry_source: str) -> list[dict[str, str]]:
    existing = binding.get("entry_invocations") if isinstance(binding, dict) else []
    invocations = [item for item in existing if isinstance(item, dict)] if isinstance(existing, list) else []
    source = str(entry_source or "").strip() or "direct_cli"
    next_invocations = [
        {
            "action": str(item.get("action") or ""),
            "entry_source": str(item.get("entry_source") or ""),
            "at": str(item.get("at") or ""),
        }
        for item in invocations
        if item.get("action")
    ]
    next_invocations.append({"action": action, "entry_source": source, "at": utc_now()})
    return next_invocations[-20:]


def adapter_label_for_error(adapter: str) -> str:
    return {
        "codex": "Codex",
        "claude": "Claude Code",
        "opencode": "OpenCode",
    }.get(adapter, adapter)

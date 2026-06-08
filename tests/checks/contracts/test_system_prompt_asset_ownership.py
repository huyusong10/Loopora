from __future__ import annotations

import ast
from pathlib import Path
import re

from compacted_contract_support import assert_contains_all
from loopora.agent_adapter_entry_contracts import agent_plan_contract
from loopora.agent_adapter_claude_hook import claude_session_additional_context
from loopora.agent_adapter_run_contract import agent_native_loop_body
from loopora.agent_adapter_role_contracts import role_agent_body
from loopora.agent_native_next_step_sections import agent_dispatch_next_summary
from loopora.agent_native_role_dispatch import agent_native_trace_contract
from loopora.agent_native_step_contracts import agent_native_evidence_rules, agent_native_todo_contract
from loopora.agent_native_task_proof import agent_native_task_next_action
from loopora.context_flow import output_contract_prompt, system_prompt_prefix
from loopora.service_prompts import ServiceRunPromptMixin
from loopora.system_prompt_assets import render_system_prompt_asset, system_prompt_asset_path


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPO_ROOT / "src" / "loopora"
SYSTEM_PROMPT_ROOT = SOURCE_ROOT / "assets" / "system_prompts"


def _source(name: str) -> str:
    return (SOURCE_ROOT / name).read_text(encoding="utf-8")


def _system_prompt_assets_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(SYSTEM_PROMPT_ROOT.rglob("*.md")))


def _python_source_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(SOURCE_ROOT.rglob("*.py")))


def test_system_prompt_bodies_live_in_assets_not_python_modules() -> None:
    prompt_source_by_file = {
        "agent_adapter_entry_contracts.py": (
            "Enter Loopora's planning stage",
            "Candidate Bundle Skeleton",
        ),
        "agent_adapter_run_contract.py": (
            "Enter Loopora's run stage",
            "Do not launch `codex`, `claude`, or `opencode` from inside this entry.",
        ),
        "agent_adapter_entry_templates.py": (
            "Manual /loopora-plan entry",
            "Do not inspect `$HOME/.claude`",
        ),
        "agent_adapter_role_contracts.py": (
            "You are the Loopora Orchestrator agent.",
            "Return exactly one raw wrapper JSON object",
            "Execute Loopora Builder step contracts, make allowed workspace changes, and return structured proof-oriented output.",
            "Dispatch Loopora step contracts to the required native role agent and preserve verifiable host dispatch metadata.",
        ),
        "context_prompt_contracts.py": (
            "System safety rules:",
            "Output contract: return JSON",
        ),
        "service_prompts.py": (
            "You are the Generator role inside Loopora.",
            "You are the Verifier role inside Loopora.",
            "Use this evidence as your starting point for the next focused improvement.",
        ),
        "agent_native_next_step_summary.py": (
            "Use this exact string as the whole Agent/Task prompt",
            "GateKeeper evidence reuse rule: inspect known evidence",
            "in the main Agent session, open the template, save a filled copy to result_file_to_write",
        ),
        "agent_native_next_step_sections.py": (
            "invoke {{target_agent}} with the next context and step contract paths below; do not perform this role inline",
            "repair the managed role agent config before dispatching this role; do not submit inline role work",
        ),
        "agent_native_step_view.py": (
            "Result file must contain one wrapper JSON object with loopora_host_dispatch and a schema-shaped result",
        ),
        "agent_native_role_dispatch.py": (
            "Cite the host's official subagent/task invocation trace when available",
        ),
        "agent_native_task_proof.py": (
            "Task verdict already passed; no new evidence pass will start unless the task scope changes.",
            "Run lifecycle is complete, but the task is not proven. Run /loopora-run again in the same Agent session",
        ),
        "agent_entry_run_projection.py": (
            "invoke {{target_agent}} with the next context and step contract paths below; do not perform this role inline",
        ),
        "cli_agent_current_step_output.py": (
            "invoke {{target_agent}} with the next context and step contract paths below; do not perform this role inline",
            "in the main Agent session, open the template, replace null placeholders in result",
        ),
        "cli_agent_step_presenters.py": (
            "Task verdict already passed; no new evidence pass will start unless the task scope changes.",
            "Run lifecycle is complete, but the task is not proven. Run /loopora-run again in the same Agent session",
            "run lifecycle is complete but the task is not proven; run /loopora-run again in this Agent session",
        ),
        "agent_adapter_claude_hook.py": (
            "Loopora managed Agent entries are already project-local",
            "Do not treat a detailed first prompt as confirmation",
        ),
        "cli_agent_plan_recovery.py": (
            "If the current host user prompt already contains the goal, fake-done risks, required evidence",
            "Use the host's official user-question or follow-up capability",
            "Do not ask user questions from a role subagent",
            "Ask the user the ask_user question, then rerun /loopora-plan",
        ),
        "cli_agent_recovery_results.py": (
            "Ask the user for task context, run /loopora-plan, review the READY preview",
            "Ask the user the ask_user question, then run /loopora-plan",
        ),
        "cli_agent_plan_recovery_results.py": (
            "rerun repair_cli_command exactly with --json --compact-json",
            "repair the candidate plan file directly and do not inspect alignment session artifacts",
            "Do not answer this alignment question from host inference",
            "ask the user alignment_assistant_message in this Agent session and stop",
            "return to this Agent session and run /loopora-run; do not start the Agent Runner run from Web",
        ),
        "cli_agent_plan_guidance_output.py": (
            "repair the candidate plan file so it preserves repair_task_message and repair_focus",
            "return to this Agent session and run /loopora-run; do not start the Agent Runner run from Web",
        ),
        "service_alignment_run_context_recovery_fields.py": (
            "repair the candidate plan file, rerun /loopora-plan, then use /loopora-run only after the preview is ready",
        ),
        "agent_adapter_role_checks.py": (
            "Return exactly one raw wrapper JSON object",
            "Do not launch codex, claude, or opencode from inside this role.",
        ),
        "service_alignment_language.py": (
            "Preserve the existing READY preview and working-agreement language",
            "Follow the dominant substantive task language from the transcript and source context",
        ),
        "agent_native_step_contracts.py": (
            "Create or update the host's official todo/progress-list when available",
            "Fill the provided result template without changing Loopora's frozen contract fields.",
            "Every evidence_refs value, including coverage_results evidence_refs",
            "Do not add a passed gatekeeper.finish coverage row",
        ),
    }
    for source_file, snippets in prompt_source_by_file.items():
        source = _source(source_file)
        for snippet in snippets:
            assert snippet not in source

    assert_contains_all(
        _system_prompt_assets_text(),
        tuple(snippet for snippets in prompt_source_by_file.values() for snippet in snippets),
    )


def test_system_prompt_asset_long_lines_do_not_reappear_in_python_source() -> None:
    source = _python_source_text()
    conflicts: list[str] = []
    for path in sorted(SYSTEM_PROMPT_ROOT.rglob("*.md")):
        asset_ref = path.relative_to(SYSTEM_PROMPT_ROOT)
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            text = line.strip()
            if len(text) < 80 or "{{" in text or text.startswith("---"):
                continue
            if text in source:
                conflicts.append(f"{asset_ref}:{line_number}")

    assert conflicts == []


def test_prompt_rendering_modules_do_not_inline_instruction_bodies() -> None:
    prompt_rendering_files = [
        path
        for path in sorted(SOURCE_ROOT.rglob("*.py"))
        if "system_prompt_assets import" in path.read_text(encoding="utf-8")
    ]
    directive_pattern = re.compile(
        r"\b(?:You are|Do not|Never|Always|Return exactly|Output contract|System safety rules)\b|"
        r"\b(?:Execute|Dispatch)\s+Loopora\b|"
        r"(?:你是|不要|不得|必须|只能|返回)",
        re.IGNORECASE,
    )
    conflicts: list[str] = []
    for path in prompt_rendering_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            value = node.value.strip()
            if len(value) < 80:
                continue
            if directive_pattern.search(value):
                conflicts.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")

    assert conflicts == []


def test_prompt_contract_named_modules_do_not_inline_system_style_instruction_bodies() -> None:
    prompt_surface_files = [
        path
        for path in sorted(SOURCE_ROOT.rglob("*.py"))
        if re.search(r"(?:prompt|contract)", path.stem)
        and path.stem not in {"bundle_contract", "service_prompt_checks", "service_prompt_requests", "service_prompt_schemas"}
    ]
    directive_pattern = re.compile(
        r"\b(?:You are|Do not|Never|Always|Return exactly|Output contract|System safety rules|"
        r"Invoke|Read top-level|Fill the provided|Every evidence_refs)\b|"
        r"\b(?:Execute|Dispatch)\s+Loopora\b|"
        r"(?:你是|不要|不得|必须|只能|返回)",
        re.IGNORECASE,
    )
    conflicts: list[str] = []
    for path in prompt_surface_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            value = node.value.strip()
            if len(value) < 80:
                continue
            if directive_pattern.search(value):
                conflicts.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")

    assert conflicts == []


def test_system_prompt_assets_do_not_branch_by_named_user_language() -> None:
    assets = _system_prompt_assets_text()

    forbidden_patterns = (
        r"\bnon[- ]english\b",
        r"\bfor\s+(?:english|chinese|spanish|french|japanese|korean)\s+users?\b",
        r"\bif\s+(?:the\s+)?user(?:'s|s)?\s+(?:is|are|uses?|speaks?)\s+"
        r"(?:english|chinese|spanish|french|japanese|korean)\b",
        r"\b(?:english|chinese|spanish|french|japanese|korean)\s+(?:task|tasks|prompt|prompts|branch|branches)\b",
        r"(?:中文|英文|西班牙语|法语|日语|韩语).{0,16}(?:用户|任务|提示词|分支)",
    )

    assert not any(re.search(pattern, assets, re.IGNORECASE) for pattern in forbidden_patterns)


def test_system_prompt_asset_refs_are_not_locale_variants() -> None:
    localized_refs = [
        path.relative_to(SYSTEM_PROMPT_ROOT).as_posix()
        for path in sorted(SYSTEM_PROMPT_ROOT.rglob("*.md"))
        if path.stem.split(".")[-1].lower() in {"zh", "en", "es", "fr", "ja", "ko"}
    ]

    assert localized_refs == []


def test_alignment_transcript_notices_do_not_reintroduce_localized_system_message_api() -> None:
    source = _python_source_text()

    forbidden_tokens = (
        "localized_alignment_system_message",
        "AlignmentLocalizedSystemMessageAppender",
        "append_system_message",
        "append_alignment_system_message",
    )

    assert not any(token in source for token in forbidden_tokens)


def test_static_system_prompt_asset_references_exist() -> None:
    missing: list[str] = []
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            function_name = ""
            if isinstance(node.func, ast.Name):
                function_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                function_name = node.func.attr
            if function_name not in {"load_system_prompt_asset", "render_system_prompt_asset"}:
                continue
            first_arg = node.args[0]
            if not isinstance(first_arg, ast.Constant) or not isinstance(first_arg.value, str):
                continue
            asset_ref = first_arg.value
            if not system_prompt_asset_path(asset_ref).is_file():
                missing.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}:{asset_ref}")

    assert missing == []


def test_asset_rendered_system_prompts_keep_public_contract_snippets() -> None:
    assert "interactive alignment conversation, not a one-prompt compiler" in agent_plan_contract(
        "codex",
        "Codex",
        "codex_project_skill",
    )
    assert "Start, resume, or continue evidence collection" in agent_native_loop_body(
        adapter="codex",
        marker_source="codex_project_skill",
    )
    assert "You are the Loopora GateKeeper role agent." in role_agent_body("gatekeeper")
    assert "System safety rules:" in system_prompt_prefix("builder")
    assert "Output contract: return JSON" in output_contract_prompt("gatekeeper")
    assert "message-only plan call" in claude_session_additional_context()

    gatekeeper_rules = agent_native_evidence_rules("gatekeeper")
    assert any("Every evidence_refs value" in rule["rule"] for rule in gatekeeper_rules)
    assert any("gatekeeper.finish coverage row" in rule["rule"] for rule in gatekeeper_rules)

    native_todo = agent_native_todo_contract(step_id="inspect_1", target_agent="loopora-inspector")
    assert "official todo/progress-list" in native_todo["host_policy"]
    assert "Read top-level summary and the step contract for inspect_1." in native_todo["items"]
    assert "Invoke loopora-inspector through the host's official subagent/task mechanism." in native_todo["items"]

    dispatch_summary = agent_dispatch_next_summary(
        {"target_agent": "loopora-builder", "target_agent_config_exists": True}
    )
    assert "do not perform this role inline" in dispatch_summary
    assert "subagent/task invocation trace" in agent_native_trace_contract()["purpose"]
    continue_action = agent_native_task_next_action(
        {
            "complete": True,
            "run": {
                "status": "succeeded",
                "task_verdict": {"status": "insufficient_evidence", "summary": "More proof needed."},
            },
        }
    )
    assert "same Agent session" in continue_action["guidance"]


def test_system_prompt_asset_renderer_rejects_unresolved_placeholders() -> None:
    rendered = render_system_prompt_asset("runtime/headless-role-intro.md", {"role_name": "Task Builder"})
    assert rendered.strip() == "You are Task Builder inside Loopora."

    prompt = ServiceRunPromptMixin()._check_planner_prompt(
        {
            "goal": "Ship the narrow change",
            "constraints": "No destructive edits",
        }
    )
    assert "You are the Check Planner inside Loopora." in prompt
    assert "{{" not in prompt

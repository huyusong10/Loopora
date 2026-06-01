from __future__ import annotations

import re
from collections.abc import Mapping

from loopora.providers import executor_profile
from loopora.service import LooporaError
from loopora.strategy_source import (
    STRATEGY_SOURCE_ARCHETYPES,
    builtin_strategy_prompt_markdown,
    builtin_strategy_prompt_markdown_by_locale,
    default_strategy_role_execution_settings,
    normalize_strategy_prompt_locale,
    strategy_archetype_display_name,
)


DEFAULT_ROLE_DEFINITION_FORM = {
    "name": "",
    "description": "",
    "posture_notes": "",
    "archetype": "builder",
    "prompt_ref": "builder.md",
    "prompt_markdown": builtin_strategy_prompt_markdown("builder.md", locale="en"),
    **default_strategy_role_execution_settings(),
}


def _normalize_role_definition_form(values: Mapping[str, object] | None, *, locale: str = "en") -> dict[str, object]:
    normalized = dict(DEFAULT_ROLE_DEFINITION_FORM)
    normalized["prompt_markdown"] = builtin_strategy_prompt_markdown("builder.md", locale=locale)
    if not values:
        return normalized
    for key in normalized:
        if key in values:
            normalized[key] = values[key]
    if "prompt_markdown" not in values:
        archetype = str(normalized.get("archetype", "builder") or "builder")
        normalized["prompt_markdown"] = builtin_strategy_prompt_markdown(
            _builtin_prompt_ref_for_archetype(archetype),
            locale=locale,
        )
    try:
        profile = executor_profile(str(normalized.get("executor_kind", "codex")))
    except ValueError:
        profile = executor_profile("codex")
    if profile.command_only:
        normalized["executor_mode"] = "command"
    if not str(normalized.get("command_cli", "")).strip():
        normalized["command_cli"] = profile.cli_name
    return normalized


def _archetype_ui_copy() -> dict[str, dict[str, str]]:
    return {
        "builder": {
            "summary_zh": "直接推进实现，适合把 Loop 契约和交接记录落成真实代码与文件改动。",
            "summary_en": "Pushes the implementation forward and turns specs plus handoffs into real code changes.",
            "recommendation_zh": "建议把它放在需要实际修改工作区的位置，并给它明确的主线目标。",
            "recommendation_en": "Use it where the workflow needs actual workspace edits, with a crisp main-path goal.",
            "warning_zh": "",
            "warning_en": "",
            "card_tip_zh": "",
            "card_tip_en": "",
        },
        "inspector": {
            "summary_zh": "收集证据、跑检查、整理事实，适合验证当前产出到底到了什么程度。",
            "summary_en": "Collects evidence, runs checks, and summarizes facts so the workflow knows what is truly working.",
            "recommendation_zh": "建议接在构建者之后，优先覆盖最关键、最可复现的用户路径。",
            "recommendation_en": "Usually works best after the Builder, starting with the most critical reproducible user paths.",
            "warning_zh": "",
            "warning_en": "",
            "card_tip_zh": "",
            "card_tip_en": "",
        },
        "gatekeeper": {
            "summary_zh": "负责做放行判断，只根据检查项、证据和风险决定是否通过。",
            "summary_en": "Owns the pass/fail decision and judges readiness strictly from checks, evidence, and risk.",
            "recommendation_zh": "建议只放一个在流程收束位，避免多个最终裁决角色相互打架。",
            "recommendation_en": "Keep one of these near the end of the workflow so there is a single clear final verdict.",
            "warning_zh": "不建议把它当成实现角色使用，它的职责是裁决，不是补做工作。",
            "warning_en": "Do not use it as an implementation role. Its job is to decide, not to compensate for missing work.",
            "card_tip_zh": "巡检者负责收集证据和跑检查，只回答“现在发生了什么”；守门者负责基于这些证据做最终放行判断，回答“现在能不能过”。没有守门者时，流程里就少了一个专门做通过/不通过裁决的角色。",
            "card_tip_en": "The Inspector gathers evidence and runs checks, answering “what is happening now.” The GateKeeper uses that evidence to make the final pass/fail call, answering “is this ready to pass.” Without a GateKeeper, the workflow loses its dedicated final judge.",
        },
        "guide": {
            "summary_zh": "在停滞、回退或噪音过多时提供新的方向，帮流程恢复有效推进。",
            "summary_en": "Intervenes when progress stalls or gets noisy, then suggests a tighter next direction.",
            "recommendation_zh": "建议放在流程末尾或条件分支里，用来给下一轮提供更高杠杆的突破口。",
            "recommendation_en": "Use it near the end or in recovery branches to generate the next high-leverage move.",
            "warning_zh": "",
            "warning_en": "",
            "card_tip_zh": "",
            "card_tip_en": "",
        },
        "custom": {
            "summary_zh": "最低权限的补充角色，适合做只读分析、专门观察和窄范围建议。",
            "summary_en": "A restricted support role for read-only analysis, specialized observations, and narrow recommendations.",
            "recommendation_zh": "适合安全审计、文案评审、风险盘点这类辅助任务；通常不要让它承担最终放行。",
            "recommendation_en": "Great for sidecar tasks like security review, copy critique, or risk scans; usually not for the final verdict.",
            "warning_zh": "它不能充当最终放行角色；如果选择自定义执行工具，也只能使用直接命令模式。",
            "warning_en": "It cannot be the final pass/fail role. If you pair it with the custom executor, direct-command mode is required.",
            "card_tip_zh": "",
            "card_tip_en": "",
        },
    }


def _archetype_options() -> list[dict[str, str]]:
    labels = []
    copy = _archetype_ui_copy()
    for archetype in STRATEGY_SOURCE_ARCHETYPES:
        item = copy[archetype]
        english_label = (
            "Custom (Restricted)" if archetype == "custom" else strategy_archetype_display_name(archetype, locale="en")
        )
        chinese_label = strategy_archetype_display_name(archetype, locale="zh")
        labels.append(
            {
                "id": archetype,
                "label_zh": chinese_label,
                "label_en": english_label,
                **item,
            }
        )
    return labels


def _role_definition_form_values_from_record(role_definition: Mapping[str, object], *, locale: str = "en") -> dict[str, object]:
    prompt_ref = str(role_definition.get("prompt_ref", ""))
    prompt_markdown = str(role_definition.get("prompt_markdown", ""))
    if str(role_definition.get("source", "")).strip() == "builtin" and prompt_ref:
        prompt_markdown = builtin_strategy_prompt_markdown(prompt_ref, locale=locale)
    return {
        "name": str(role_definition.get("name", "")),
        "description": str(role_definition.get("description", "")),
        "posture_notes": str(role_definition.get("posture_notes", "")),
        "archetype": str(role_definition.get("archetype", "builder") or "builder"),
        "prompt_ref": prompt_ref,
        "prompt_markdown": prompt_markdown,
        "executor_kind": str(role_definition.get("executor_kind", "codex") or "codex"),
        "executor_mode": str(role_definition.get("executor_mode", "preset") or "preset"),
        "command_cli": str(role_definition.get("command_cli", "")),
        "command_args_text": str(role_definition.get("command_args_text", "")),
        "model": str(role_definition.get("model", "")),
        "reasoning_effort": str(role_definition.get("reasoning_effort", "")),
    }


def _role_definition_payload_from_mapping(payload: Mapping[str, object]) -> dict[str, object]:
    name = str(payload.get("name", "")).strip()
    description = str(payload.get("description", "")).strip()
    posture_notes = str(payload.get("posture_notes", ""))
    archetype = str(payload.get("archetype", "builder")).strip() or "builder"
    prompt_ref = str(payload.get("prompt_ref", "")).strip()
    prompt_markdown = str(payload.get("prompt_markdown", ""))
    executor_kind = str(payload.get("executor_kind", "codex")).strip() or "codex"
    executor_mode = str(payload.get("executor_mode", "preset")).strip() or "preset"
    command_cli = str(payload.get("command_cli", "")).strip()
    command_args_text = str(payload.get("command_args_text", ""))
    model = str(payload.get("model", "")).strip()
    reasoning_effort = str(payload.get("reasoning_effort", "")).strip()
    if not name:
        raise LooporaError("name is required")
    if not prompt_markdown.strip():
        raise LooporaError("prompt_markdown is required")
    return {
        "name": name,
        "description": description,
        "posture_notes": posture_notes,
        "archetype": archetype,
        "prompt_ref": prompt_ref,
        "prompt_markdown": prompt_markdown,
        "executor_kind": executor_kind,
        "executor_mode": executor_mode,
        "command_cli": command_cli,
        "command_args_text": command_args_text,
        "model": model,
        "reasoning_effort": reasoning_effort,
    }


def _builtin_prompt_ref_for_archetype(archetype: str) -> str:
    return "gatekeeper.md" if archetype == "gatekeeper" else f"{archetype}.md"


def _builtin_role_templates(*, locale: str = "en") -> dict[str, dict[str, object]]:
    templates: dict[str, dict[str, object]] = {}
    for archetype in STRATEGY_SOURCE_ARCHETYPES:
        prompt_ref = _builtin_prompt_ref_for_archetype(archetype)
        prompt_markdown_by_locale = builtin_strategy_prompt_markdown_by_locale(prompt_ref)
        templates[archetype] = {
            "prompt_ref": prompt_ref,
            "prompt_markdown": prompt_markdown_by_locale[normalize_strategy_prompt_locale(locale)],
            "prompt_markdown_by_locale": prompt_markdown_by_locale,
        }
    return templates


def _decorate_role_definition_overview(role_definition: Mapping[str, object]) -> dict[str, object]:
    executor_kind = str(role_definition.get("executor_kind", "codex") or "codex")
    archetype = str(role_definition.get("archetype", "builder") or "builder")
    template_name = "Custom (Restricted)" if archetype.strip() == "custom" else strategy_archetype_display_name(
        archetype,
        locale="en",
    )
    archetype_copy = _archetype_ui_copy()[archetype]
    name = str(role_definition.get("name", "")).strip()
    normalized_name = re.sub(r"[^a-z0-9]+", "", name.lower())
    normalized_template = re.sub(r"[^a-z0-9]+", "", template_name.lower())
    return {
        **role_definition,
        "executor_label": executor_profile(executor_kind).label,
        "template_display_name": template_name,
        "show_template_meta": str(role_definition.get("source", "")).strip() == "custom" and normalized_name != normalized_template,
        "summary_zh": archetype_copy["summary_zh"],
        "summary_en": archetype_copy["summary_en"],
        "card_tip_zh": archetype_copy["card_tip_zh"],
        "card_tip_en": archetype_copy["card_tip_en"],
    }

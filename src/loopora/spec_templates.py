from __future__ import annotations

"""Markdown spec template rendering."""

from typing import Any

from loopora.strategy_source import (
    build_preset_strategy_source,
    normalize_strategy_role_display_name,
    normalize_strategy_source,
)

GENERIC_ROLE_NOTE_COPY = {
    "zh": "补充当前角色执行这个任务时应优先关注的重点、证据偏好或工作方式。不要在这里新增真正的通过条件。",
    "en": "Add the priorities, evidence preferences, or working style this role should keep in mind for this task. Do not add hidden pass/fail criteria here.",
}

ROLE_NOTE_DEFAULTS = {
    "builder": {
        "zh": "优先做聚焦、原地的小改动，把任务尽快推进到可验证的状态。",
        "en": "Prefer focused in-place changes that move the task quickly toward a verifiable state.",
    },
    "inspector": {
        "zh": "优先收集最关键、最可复现的证据，不要把模糊推测包装成确定结论。",
        "en": "Start with the most important reproducible evidence, and do not present guesses as certain findings.",
    },
    "gatekeeper": {
        "zh": "只有在 Done When 和 Guardrails 都有直接证据支撑时才放行；证据偏弱时宁可保守。",
        "en": "Only pass when Done When and Guardrails are backed by direct evidence; stay conservative when evidence is weak.",
    },
    "guide": {
        "zh": "把上游证据、未证明缺口或停滞信号收窄成最小但高杠杆的方向调整，不要变成第二个 GateKeeper。",
        "en": "Turn upstream evidence, unproven gaps, or stagnation signals into the smallest high-leverage direction change instead of acting like a second GateKeeper.",
    },
    "custom": {
        "zh": "保持只读辅助角色定位，优先给出具体观察和窄范围建议。",
        "en": "Stay in a read-only supporting role and focus on concrete observations plus narrow recommendations.",
    },
}


def render_spec_template(
    locale: str = "zh",
    workflow: dict[str, Any] | None = None,
    *,
    strategy_source: dict[str, Any] | None = None,
) -> str:
    return render_spec_template_for_strategy_source(
        locale=locale,
        strategy_source=strategy_source if strategy_source is not None else workflow,
    )


def render_spec_template_for_strategy_source(
    locale: str = "zh",
    strategy_source: dict[str, Any] | None = None,
) -> str:
    use_zh = locale.lower().startswith("zh")
    normalized_strategy_source = {"version": 1, "preset": "", "roles": [], "steps": []}
    if strategy_source:
        roles = strategy_source.get("roles") if isinstance(strategy_source, dict) else None
        steps = strategy_source.get("steps") if isinstance(strategy_source, dict) else None
        preset_name = str(strategy_source.get("preset", "")).strip() if isinstance(strategy_source, dict) else ""
        if isinstance(roles, list) and isinstance(steps, list) and (roles or steps):
            normalized_strategy_source = normalize_strategy_source(strategy_source)
        elif preset_name:
            normalized_strategy_source = build_preset_strategy_source(preset_name)
    role_note_sections = _render_role_note_sections(normalized_strategy_source, locale="zh" if use_zh else "en")
    if use_zh:
        return (
            "<!--\n"
            "这段提示看完就可以删。\n\n"
            "必填：\n"
            "- 保留 `# Task`。如果删掉，spec 校验会直接失败。\n\n"
            "可选：\n"
            "- 如果你还不想固定成功条件，可以先删掉整个 `# Done When`，Loopora 会在 run 开始时自动生成并冻结一组 checks。\n"
            "- 如果暂时没有额外边界，可以删掉 `# Guardrails` 里的占位项。\n"
            "- `# Success Surface`、`# Fake Done`、`# Evidence Preferences`、`# Residual Risk` 用来表达这次任务的协作合同；不写也可以，但写了会一起进入运行期契约。\n"
            "- `# Role Notes` 只会附加到对应角色的 prompt，不会变成隐藏的通过标准。\n"
            "-->\n\n"
            "# Task\n\n"
            "用一句到两句话写清这次 run 最终要完成什么。\n\n"
            "# Done When\n\n"
            "- 写一条最关键、可判定的成功结果\n"
            "- 再写 1 到 2 条需要保住的结果或证据\n\n"
            "# Guardrails\n\n"
            "- 不允许破坏什么\n"
            "- 哪些目录或接口必须保留\n"
            "- 是否必须保留现有用户文件\n"
            "- 是否要求原地小改、避免大范围重写\n\n"
            "# Success Surface\n\n"
            "- 哪些结果虽然不一定是 Done When，但这次任务里也很重要\n"
            "- 哪些质量面、可维护性面或用户感知面需要一起保住\n\n"
            "# Fake Done\n\n"
            "- 哪些“看起来完成了”但你不会接受\n"
            "- 哪些表面结果算糊弄，不能当成真正完成\n\n"
            "# Evidence Preferences\n\n"
            "- 这次你最信什么证据：真实运行、测试、benchmark、截图、日志或别的什么\n"
            "- 如果证据不足，系统更应该补什么\n\n"
            "# Residual Risk\n\n"
            "用一两句话写这次可以接受什么残余风险，或者明确说明要尽量 fail closed。\n\n"
            "# Role Notes\n\n"
            "如果当前流程已经确定，可以按角色补充一些工作方式提示。这里的内容只会附加到对应角色的 prompt，"
            "不会变成隐藏的通过标准。\n\n"
            f"{role_note_sections}".rstrip()
            + "\n"
        )
    return (
        "<!--\n"
        "Delete this note whenever you want.\n\n"
        "Required:\n"
        "- Keep `# Task`. If you delete it, spec validation fails.\n\n"
        "Optional:\n"
        "- If you are not ready to lock success criteria yet, delete `# Done When` and Loopora will auto-generate plus freeze checks at run start.\n"
        "- If there are no extra boundaries yet, remove the placeholder bullets inside `# Guardrails`.\n"
        "- `# Success Surface`, `# Fake Done`, `# Evidence Preferences`, and `# Residual Risk` express the task contract for this run. They remain optional, but when present they become part of the runtime contract.\n"
        "- `# Role Notes` only adjusts role prompts. It does not change pass/fail rules.\n"
        "-->\n\n"
        "# Task\n\n"
        "Describe in one or two sentences what this run should accomplish.\n\n"
        "# Done When\n\n"
        "- State the most important judgeable success outcome\n"
        "- Add 1 to 2 more outcomes or evidence requirements if they matter\n\n"
        "# Guardrails\n\n"
        "- Say what must not be broken\n"
        "- Say which directories or interfaces must be preserved\n"
        "- Say whether you must preserve existing user files\n"
        "- Say whether focused in-place edits are preferred over broad rewrites\n\n"
        "# Success Surface\n\n"
        "- List the additional quality surfaces that matter in this task even beyond Done When\n"
        "- Keep the user-facing or maintainability outcomes you still want protected\n\n"
        "# Fake Done\n\n"
        "- List the outcomes that may look complete but would still feel unacceptable\n"
        "- Describe the shortcuts or shallow fixes that should not count as done\n\n"
        "# Evidence Preferences\n\n"
        "- Say which evidence you trust most in this task: real runs, tests, benchmarks, screenshots, logs, or something else\n"
        "- Say what the system should gather first when evidence is still weak\n\n"
        "# Residual Risk\n\n"
        "Use one or two sentences to describe the residual risk you can accept here, or say clearly that the run should fail closed.\n\n"
        "# Role Notes\n\n"
        "If the workflow is already chosen, add role-specific working notes here. These notes are appended to the matching "
        "role prompt only and never become hidden pass/fail rules.\n\n"
        f"{role_note_sections}".rstrip()
        + "\n"
    )


def _render_role_note_sections(strategy_source: dict[str, Any], *, locale: str) -> str:
    sections: list[str] = []
    seen: set[str] = set()
    roles = strategy_source.get("roles") if isinstance(strategy_source, dict) else []
    if not isinstance(roles, list):
        roles = []
    for role in roles:
        if not isinstance(role, dict):
            continue
        archetype = str(role.get("archetype") or "").strip()
        title = normalize_strategy_role_display_name(role.get("name"), archetype=archetype) or str(
            role.get("name") or ""
        ).strip()
        if not title or title.lower() in seen:
            continue
        seen.add(title.lower())
        note_copy = ROLE_NOTE_DEFAULTS.get(archetype, GENERIC_ROLE_NOTE_COPY)["zh" if locale == "zh" else "en"]
        sections.append(f"## {title} Notes\n\n{note_copy}")
    if sections:
        return "\n\n".join(sections)
    fallback = ROLE_NOTE_DEFAULTS["builder"]["zh" if locale == "zh" else "en"]
    return f"## Builder Notes\n\n{fallback}"

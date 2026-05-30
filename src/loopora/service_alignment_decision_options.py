from __future__ import annotations

import re
from collections.abc import Collection


def alignment_needs_user_input(output: dict) -> bool:
    return output.get("needs_user_input") is True


def normalize_alignment_missing_items(
    raw_items: object,
    *,
    allowed_item_ids: Collection[str],
    limit: int = 12,
) -> list[str]:
    if not isinstance(raw_items, list):
        return []
    items: list[str] = []
    seen: set[str] = set()
    for raw_item in raw_items:
        item = str(raw_item or "").strip()
        if item not in allowed_item_ids or item in seen:
            continue
        seen.add(item)
        items.append(item)
        if len(items) >= limit:
            break
    return items


def normalize_alignment_decision_options(raw_options: object) -> list[dict]:
    if not isinstance(raw_options, list):
        return []
    options: list[dict] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw_options[:4], start=1):
        if not isinstance(item, dict):
            continue
        label = _alignment_text_snippet(item.get("label"), limit=80)
        description = _alignment_text_snippet(item.get("description"), limit=220)
        user_reply = _alignment_text_snippet(item.get("user_reply"), limit=260)
        if not label or not description or not user_reply:
            continue
        option_id = str(item.get("id") or f"option_{index}").strip()
        option_id = re.sub(r"[^A-Za-z0-9_.:-]+", "-", option_id).strip("-") or f"option_{index}"
        if option_id in seen_ids:
            option_id = f"{option_id}-{index}"
        seen_ids.add(option_id)
        options.append(
            {
                "id": option_id,
                "label": label,
                "description": description,
                "recommended": item.get("recommended") is True,
                "user_reply": user_reply,
            }
        )
    return options


def alignment_has_recommended_decision_options(output: dict) -> bool:
    options = normalize_alignment_decision_options(output.get("decision_options"))
    return alignment_decision_options_are_visible(options)


def alignment_decision_options_are_visible(options: list[dict]) -> bool:
    return len(options) >= 2 and any(option.get("recommended") is True for option in options)


def visible_alignment_decision_options(output: dict, *, has_bundle: bool, prefers_chinese: bool) -> list[dict]:
    if has_bundle:
        return []
    phase = str(output.get("alignment_phase", "") or "").strip().lower()
    status = str(output.get("status", "") or "").strip().lower()
    if not alignment_needs_user_input(output) and phase != "blocked" and status != "blocked":
        return []
    options = normalize_alignment_decision_options(output.get("decision_options"))
    if alignment_decision_options_are_visible(options):
        return options
    if phase == "agreement":
        return agreement_confirmation_decision_options(prefers_chinese=prefers_chinese)
    if phase == "blocked" or status == "blocked":
        return not_fit_alignment_decision_options(prefers_chinese=prefers_chinese)
    return default_alignment_decision_options(prefers_chinese=prefers_chinese)


def default_alignment_decision_options(*, prefers_chinese: bool) -> list[dict]:
    if prefers_chinese:
        return [
            {
                "id": "evidence_first",
                "label": "优先阻断假完成（推荐）",
                "description": "少做一点也可以，但必须证明核心路径真的成立。",
                "recommended": True,
                "user_reply": "采用推荐：优先阻断看起来完成但证据不足的结果，少而真实也可以。",
            },
            {
                "id": "speed_first",
                "label": "优先快速推进",
                "description": "先交一个更务实的首版，允许部分残余风险保持可见。",
                "recommended": False,
                "user_reply": "我选择优先快速推进，可以接受部分残余风险保持可见。",
            },
            {
                "id": "add_judgment",
                "label": "我补充判断",
                "description": "我想说明另一种更重要的完成标准或风险。",
                "recommended": False,
                "user_reply": "我想补充另一种判断：",
            },
        ]
    return [
        {
            "id": "evidence_first",
            "label": "Block fake done (Recommended)",
            "description": "A smaller result is acceptable, but the core path must be proven.",
            "recommended": True,
            "user_reply": "Use the recommendation: block results that look done but lack evidence, even if the first version is smaller.",
        },
        {
            "id": "speed_first",
            "label": "Move faster",
            "description": "Ship a more pragmatic first pass and keep residual risks visible.",
            "recommended": False,
            "user_reply": "I choose speed first and can accept visible residual risks.",
        },
        {
            "id": "add_judgment",
            "label": "I'll add judgment",
            "description": "I want to name a different completion standard or risk.",
            "recommended": False,
            "user_reply": "I want to add another judgment:",
        },
    ]


def agreement_confirmation_decision_options(*, prefers_chinese: bool) -> list[dict]:
    if prefers_chinese:
        return [
            {
                "id": "confirm_agreement",
                "label": "采用这个方向（推荐）",
                "description": "按这份工作协议生成 Loop 方案。",
                "recommended": True,
                "user_reply": "确认，采用这个方向。",
            },
            {
                "id": "adjust_agreement",
                "label": "我想调整",
                "description": "先修改其中一个判断，再生成方案。",
                "recommended": False,
                "user_reply": "我想调整这份工作协议：",
            },
        ]
    return [
        {
            "id": "confirm_agreement",
            "label": "Use this direction (Recommended)",
            "description": "Generate the Loop plan from this working agreement.",
            "recommended": True,
            "user_reply": "Confirm; use this direction.",
        },
        {
            "id": "adjust_agreement",
            "label": "I want changes",
            "description": "Revise one judgment before generating the plan.",
            "recommended": False,
            "user_reply": "I want to adjust this working agreement:",
        },
    ]


def not_fit_alignment_decision_options(*, prefers_chinese: bool) -> list[dict]:
    if prefers_chinese:
        return [
            {
                "id": "skip_loop",
                "label": "先不生成 Loop（推荐）",
                "description": "这更像一次性任务，不需要额外编排。",
                "recommended": True,
                "user_reply": "同意，先不生成 Loop 方案。",
            },
            {
                "id": "still_compile",
                "label": "仍然编排",
                "description": "我会说明需要继承的反复判断或新证据。",
                "recommended": False,
                "user_reply": "仍然需要编排，因为这套判断需要被后续运行继承：",
            },
        ]
    return [
        {
            "id": "skip_loop",
            "label": "Skip Loop for now (Recommended)",
            "description": "This looks like a one-off task that does not need governance.",
            "recommended": True,
            "user_reply": "Agreed, do not generate a Loop plan for now.",
        },
        {
            "id": "still_compile",
            "label": "Still compose it",
            "description": "I will explain the repeated judgment or new evidence this run must inherit.",
            "recommended": False,
            "user_reply": "I still need a Loop because this judgment should be inherited by the run:",
        },
    ]


def _alignment_text_snippet(value: object, *, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"

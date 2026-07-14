from __future__ import annotations

import json
import re

from loopora.service_alignment_language import alignment_message_is_language_neutral_confirmation

ALIGNMENT_SESSION_TRANSCRIPT_BLOCK_RE = re.compile(
    r"## Session Transcript\s*```json\s*(.*?)\s*```",
    re.DOTALL,
)
ALIGNMENT_PROMPT_USER_CONTENT_RE = re.compile(
    r'"role"\s*:\s*"user"\s*,\s*"content"\s*:\s*("(?:\\.|[^"\\])*")',
    re.DOTALL,
)


def alignment_task_text_from_prompt(prompt: str) -> str:
    messages = _alignment_user_messages_from_prompt(prompt)
    task_messages: list[str] = []
    for message in messages:
        task_message = alignment_task_anchor_from_user_message(message)
        if not task_message or _alignment_message_is_confirmation(task_message):
            continue
        if task_message not in task_messages:
            task_messages.append(task_message)
        if len(task_messages) >= 3:
            break
    return _alignment_join_task_messages(task_messages)


def alignment_task_anchor_from_user_message(message: str) -> str:
    text = " ".join(str(message or "").split())
    if not text:
        return ""
    text = _alignment_strip_mixed_confirmation_adjustment_prefix(text)
    for marker in (
        "Continue Web review from this /loopora-plan task anchor:",
        "First re-check whether this /loopora-plan task anchor fits Loopora:",
        "Task anchor:",
        "请基于这次 /loopora-plan 的任务锚点继续 Web review：",
        "请先按这次 /loopora-plan 的任务锚点重新判断是否适合 Loopora：",
        "任务锚点：",
        "Continuar Web review desde este ancla de tarea de /loopora-plan:",
        "Primero vuelve a comprobar si este ancla de tarea de /loopora-plan encaja con Loopora:",
        "Ancla de tarea:",
    ):
        if marker in text:
            text = text.split(marker, 1)[1].strip()
            break
    for trailer in (
        "Use the evidence-first path:",
        "If we should continue,",
        "推荐采用证据优先路径：",
        "如果仍要继续，",
        "Usa el camino de evidencia primero:",
        "Si debemos continuar,",
    ):
        if trailer in text:
            text = text.split(trailer, 1)[0].strip()
    return text.strip(" \t\r\n:：,，.。")


def _alignment_user_messages_from_prompt(prompt: str) -> list[str]:
    transcript = _alignment_prompt_transcript(prompt)
    if transcript:
        return [
            str(entry.get("content") or "").strip()
            for entry in transcript
            if isinstance(entry, dict) and entry.get("role") == "user" and str(entry.get("content") or "").strip()
        ]
    messages: list[str] = []
    for match in ALIGNMENT_PROMPT_USER_CONTENT_RE.finditer(str(prompt or "")):
        try:
            content = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if str(content or "").strip():
            messages.append(str(content).strip())
    return messages


def _alignment_prompt_transcript(prompt: str) -> list[dict]:
    match = ALIGNMENT_SESSION_TRANSCRIPT_BLOCK_RE.search(str(prompt or ""))
    if not match:
        return []
    try:
        transcript = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    if not isinstance(transcript, list):
        return []
    return [entry for entry in transcript if isinstance(entry, dict)]


def _alignment_strip_mixed_confirmation_adjustment_prefix(text: str) -> str:
    value = str(text or "").strip()
    value = re.sub(
        r"^(?:确认|同意|可以|好的?|行|没问题)[\s,，;；.。]*(?:但|但是|不过|只是|同时|并且)?[\s,，;；.。]*",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()
    value = re.sub(
        r"^(?:要)?(?:调整|修改|更改|补充|改一下|再改)(?:这份|这个|当前)?(?:工作协议|协议|方案|方向)?[\s:：,，;；]*",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()
    value = re.sub(
        r"^(?:confirm(?:ed)?|approve(?:d)?|ok(?:ay)?|looks good|go ahead|proceed)[\s,;:.]*(?:but|however|and)[\s,;:.]*(?:please\s+)?",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()
    value = re.sub(
        r"^(?:confirmo|confirmado|de acuerdo|ok)[\s,;:.]*(?:pero|y|aunque)[\s,;:.]*(?:por favor\s+)?",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()
    return value or str(text or "").strip()


def _alignment_message_is_confirmation(message: str) -> bool:
    if alignment_message_is_language_neutral_confirmation(message):
        return True
    normalized = " ".join(str(message or "").strip().lower().split())
    if not normalized:
        return False
    if re.fullmatch(
        r"(?:confirm|confirmed|approve|approved|go ahead|proceed)(?:\s+(?:this|the)\s+(?:working\s+)?agreement)?[\s.!?]*",
        normalized,
    ):
        return True
    compact = re.sub(r"[\s.!?。！？,，;；:：\"'“”‘’]+", "", normalized)
    return bool(re.fullmatch(r"(?:确认|同意|采用|可以|好的?)(?:采用)?(?:这份|这个|当前)?(?:工作协议|协议|方案|方向)?", compact) and len(compact) <= 24)


def _alignment_join_task_messages(messages: list[str]) -> str:
    text = "\n".join(message for message in messages if message.strip()).strip()
    if len(text) <= 1200:
        return text
    return text[:1199].rstrip() + "…"

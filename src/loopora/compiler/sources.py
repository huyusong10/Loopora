from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class LoopSourceKind(StrEnum):
    AGENT_MESSAGE = "agent_message"
    WEB_ALIGNMENT = "web_alignment"
    MARKDOWN_CONTRACT = "markdown_contract"
    LOOPFILE = "loopfile"
    STRATEGY_TEMPLATE = "strategy_template"
    EXISTING_LOOP_RECORD = "existing_loop_record"


@dataclass(frozen=True, slots=True)
class LoopSource:
    kind: LoopSourceKind
    id: str = ""
    payload: dict = field(default_factory=dict)

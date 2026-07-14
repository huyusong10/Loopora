from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PUBLIC_READER_DOCS = (
    ROOT / "README.md",
    ROOT / "README.zh-CN.md",
    ROOT / "HUMAN-SHAPED-LOOP.md",
    ROOT / "HUMAN-SHAPED-LOOP.zh-CN.md",
    ROOT / "CODE_OF_CONDUCT.md",
    ROOT / "CHANGELOG.md",
    ROOT / "GOVERNANCE.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "SECURITY.md",
    ROOT / "SUPPORT.md",
)
CHINESE_PUBLIC_READER_DOCS = (
    ROOT / "README.zh-CN.md",
    ROOT / "HUMAN-SHAPED-LOOP.zh-CN.md",
)
INLINE_REVIEW_NOTE_PATTERN = re.compile(
    r"（[^）]*(?:一点也|这个图|这里可能|看看怎么|有点突兀|受到质疑|吸引力|不是它能干什么|拒绝和阻断|不够好理解|不要出现|请巡检|用户很容易看不懂|太冗长|不适合做最后总结|简化|去掉)[^）]*）"
)
CHINESE_PUBLIC_INTERNAL_TERM_PATTERN = re.compile(
    r"\b(?:happy path|proof harness|run contract|step capsule|judgment_contract|required coverage|GateKeeper|blocking issue|workflow handoff|run status|task verdict|READY)\b|benchmark",
    re.IGNORECASE,
)
PUBLIC_DOC_MAX_LINE_LENGTH = 1400


def _assert_semantic_groups(text: str, groups: tuple[tuple[str, ...], ...], *, label: str) -> None:
    normalized = text.casefold()
    missing = [group for group in groups if not all(term.casefold() in normalized for term in group)]

    assert not missing, f"{label} is missing public-reader Agent Native semantics: {missing[:3]}"

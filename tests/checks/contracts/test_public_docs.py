from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PUBLIC_READER_DOCS = (
    ROOT / "README.md",
    ROOT / "README.zh-CN.md",
    ROOT / "HUMAN-SHAPED-LOOP.md",
    ROOT / "HUMAN-SHAPED-LOOP.zh-CN.md",
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


def test_public_reader_docs_do_not_ship_inline_review_notes() -> None:
    for doc in PUBLIC_READER_DOCS:
        text = doc.read_text(encoding="utf-8")
        leaked_notes = INLINE_REVIEW_NOTE_PATTERN.findall(text)

        assert not leaked_notes, f"{doc.relative_to(ROOT)} exposes inline review notes: {leaked_notes[:3]}"


def test_chinese_public_reader_docs_use_reader_level_runtime_language() -> None:
    for doc in CHINESE_PUBLIC_READER_DOCS:
        text = doc.read_text(encoding="utf-8")
        internal_terms = sorted(set(CHINESE_PUBLIC_INTERNAL_TERM_PATTERN.findall(text)))

        assert not internal_terms, f"{doc.relative_to(ROOT)} exposes internal runtime terms: {internal_terms[:5]}"


def test_public_reader_docs_keep_agent_runner_contract_readable() -> None:
    for doc in PUBLIC_READER_DOCS:
        long_lines = [(index, len(line)) for index, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), start=1) if len(line) > PUBLIC_DOC_MAX_LINE_LENGTH]

        assert not long_lines, f"{doc.relative_to(ROOT)} has oversized public-reader lines: {long_lines[:3]}"


def test_public_reader_docs_explain_agent_runner_capability_contract_semantics() -> None:
    english_docs = {
        "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
        "HUMAN-SHAPED-LOOP.md": (ROOT / "HUMAN-SHAPED-LOOP.md").read_text(encoding="utf-8"),
    }
    chinese_docs = {
        "README.zh-CN.md": (ROOT / "README.zh-CN.md").read_text(encoding="utf-8"),
        "HUMAN-SHAPED-LOOP.zh-CN.md": (ROOT / "HUMAN-SHAPED-LOOP.zh-CN.md").read_text(encoding="utf-8"),
    }

    english_semantics = (
        ("capability contract",),
        ("current host Agent", "executes"),
        ("/loopora-plan", "/loopora-run"),
        ("explicit", "Activation"),
        ("managed", ".loopora/"),
        ("project-local", "thin"),
        ("host-native", "Role handoff"),
        ("nested", "CLI"),
        ("Task proof", "evidence", "task verdict"),
        ("Model/provider routing", "permissions", "credentials"),
        ("hints", "host memory"),
    )
    chinese_semantics = (
        ("能力契约",),
        ("当前宿主 Agent", "执行主体"),
        ("/loopora-plan", "/loopora-run"),
        ("显式", "激活"),
        ("托管", ".loopora/"),
        ("项目本地", "薄"),
        ("宿主原生机制", "角色交接"),
        ("嵌套启动", "命令行"),
        ("任务证明", "证据", "任务裁决"),
        ("模型", "权限", "凭据"),
        ("提示", "宿主记忆"),
    )

    for label, text in english_docs.items():
        _assert_semantic_groups(text, english_semantics, label=label)
    for label, text in chinese_docs.items():
        _assert_semantic_groups(text, chinese_semantics, label=label)


def _assert_semantic_groups(text: str, groups: tuple[tuple[str, ...], ...], *, label: str) -> None:
    normalized = text.casefold()
    missing = [group for group in groups if not all(term.casefold() in normalized for term in group)]

    assert not missing, f"{label} is missing public-reader Agent Runner semantics: {missing[:3]}"

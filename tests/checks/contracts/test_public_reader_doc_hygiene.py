from __future__ import annotations

from public_docs_test_support import (
    CHINESE_PUBLIC_INTERNAL_TERM_PATTERN,
    CHINESE_PUBLIC_READER_DOCS,
    INLINE_REVIEW_NOTE_PATTERN,
    PUBLIC_DOC_MAX_LINE_LENGTH,
    PUBLIC_READER_DOCS,
    ROOT,
)


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
        long_lines = [
            (index, len(line))
            for index, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), start=1)
            if len(line) > PUBLIC_DOC_MAX_LINE_LENGTH
        ]

        assert not long_lines, f"{doc.relative_to(ROOT)} has oversized public-reader lines: {long_lines[:3]}"

from __future__ import annotations

import pytest

from loopora.specs import SpecError, compile_markdown_spec, load_spec_file


def test_load_spec_file_reports_encoding_errors(tmp_path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_bytes(b"\xff")

    with pytest.raises(SpecError, match="UTF-8 encoded Markdown"):
        load_spec_file(spec_path)


def test_compile_markdown_spec_requires_task() -> None:
    with pytest.raises(SpecError, match="missing top-level sections: Task"):
        compile_markdown_spec("# Guardrails\n\nOnly guardrails.\n")


def test_compile_markdown_spec_rejects_legacy_sections() -> None:
    with pytest.raises(SpecError, match="legacy spec headings") as exc_info:
        compile_markdown_spec("# Goal\n\nLegacy.\n")
    message = str(exc_info.value)
    assert "# Success Surface" in message
    assert "# Fake Done" in message
    assert "# Evidence Preferences" in message
    assert "# Residual Risk" in message


def test_compile_markdown_spec_rejects_duplicate_top_level_sections() -> None:
    with pytest.raises(SpecError, match="duplicate top-level sections: Done When"):
        compile_markdown_spec(
            """# Task

Ship the requested behavior.

# Done When

- The primary flow works.

# Done When

- A second list must not silently replace the first.
"""
        )


def test_compile_markdown_spec_rejects_duplicate_role_note_sections() -> None:
    with pytest.raises(SpecError, match="duplicate role note sections: builder"):
        compile_markdown_spec(
            """# Task

Ship the requested behavior.

# Role Notes

## Builder Notes

Keep changes focused.

## builder notes

This duplicate note must not silently replace the first note.
"""
        )


def test_compile_markdown_spec_rejects_nested_only_contract_lists() -> None:
    with pytest.raises(SpecError, match="`# Done When` must contain at least one top-level bullet item"):
        compile_markdown_spec(
            """# Task

Ship the requested behavior.

# Done When

  - This nested-looking item must not become a frozen check.
"""
        )

    with pytest.raises(SpecError, match="`# Fake Done` must contain at least one top-level bullet item"):
        compile_markdown_spec(
            """# Task

Ship the requested behavior.

# Fake Done

  - This nested-looking item must not become a fake-done risk.
"""
        )

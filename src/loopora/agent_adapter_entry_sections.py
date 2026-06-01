from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdapterEntrySection:
    title: str
    body: str


def render_adapter_entry_sections(sections: list[AdapterEntrySection]) -> str:
    rendered: list[str] = []
    for section in sections:
        body = section.body.strip()
        if not body:
            continue
        rendered.append(f"## {section.title}\n\n{body}")
    return "\n\n".join(rendered).strip()

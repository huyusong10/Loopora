from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SVG_NAMESPACE = {"svg": "http://www.w3.org/2000/svg"}
PUBLIC_SVG_DIRS = (
    ROOT / "src/loopora/assets/logo",
    ROOT / "assets/diagrams",
)
PUBLIC_MARKDOWN_DOCS = (
    ROOT / "README.md",
    ROOT / "README.zh-CN.md",
    ROOT / "HUMAN-SHAPED-LOOP.md",
    ROOT / "HUMAN-SHAPED-LOOP.zh-CN.md",
)
PUBLIC_MARKDOWN_SVG_REF_PATTERN = re.compile(
    r'<img\s+[^>]*src="(\./(?:assets/diagrams|src/loopora/assets/logo)/[^"]+\.svg)"'
)


def public_svg_files() -> list[Path]:
    return [path for directory in PUBLIC_SVG_DIRS for path in sorted(directory.glob("*.svg"))]


def read_svg(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def public_markdown_svg_refs(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8")
    return PUBLIC_MARKDOWN_SVG_REF_PATTERN.findall(raw)

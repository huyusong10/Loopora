from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from public_svg_asset_test_support import ROOT, SVG_NAMESPACE, public_svg_files, read_svg

ALLOWED_FONT_WEIGHTS = {"normal", "bold", "400", "500", "600", "700"}
LEGACY_WARM_NEUTRALS = {
    "#faf9f6",
    "#f8f5ef",
    "#e8dfd3",
    "#d9d0c5",
    "#8d8378",
    "#6d665d",
    "#211b15",
    "#2c2118",
}
PLAN_JUDGMENT_TABLE_ROW_COUNT = 6


def test_public_svg_assets_are_parseable_and_avoid_fragile_typography() -> None:
    for path in public_svg_files():
        raw = read_svg(path)

        ET.fromstring(raw)
        assert not re.search(r'letter-spacing="-\d', raw), f"{path.relative_to(ROOT)} uses negative tracking"

        font_weights = re.findall(r'font-weight="([^"]+)"', raw)
        unsupported = sorted({weight for weight in font_weights if weight not in ALLOWED_FONT_WEIGHTS})
        assert not unsupported, f"{path.relative_to(ROOT)} uses fragile font weights: {unsupported}"


def test_logo_assets_do_not_depend_on_fixed_white_tiles() -> None:
    for path in sorted((ROOT / "src/loopora/assets/logo").glob("*.svg")):
        root = ET.fromstring(read_svg(path))
        white_rects = [
            rect
            for rect in root.findall(".//svg:rect", SVG_NAMESPACE)
            if rect.attrib.get("fill", "").lower() in {"white", "#fff", "#ffffff"}
        ]
        assert not white_rects, f"{path.relative_to(ROOT)} should render as a transparent logo asset"


def test_document_diagrams_keep_accessible_metadata_and_current_palette() -> None:
    for path in sorted((ROOT / "assets/diagrams").glob("*.svg")):
        raw = read_svg(path)
        root = ET.fromstring(raw)

        assert root.attrib.get("role") == "img"
        assert root.attrib.get("aria-labelledby") == "title desc"
        assert root.find("svg:title", SVG_NAMESPACE) is not None
        assert root.find("svg:desc", SVG_NAMESPACE) is not None

        lower_raw = raw.lower()
        leaked_legacy_colors = sorted(color for color in LEGACY_WARM_NEUTRALS if color in lower_raw)
        assert not leaked_legacy_colors, f"{path.relative_to(ROOT)} uses legacy warm-neutral palette: {leaked_legacy_colors}"


def test_judgment_surfaces_diagrams_use_execution_strategy_language() -> None:
    diagram_en = read_svg(ROOT / "assets" / "diagrams" / "judgment-surfaces.en.svg")
    diagram_zh = read_svg(ROOT / "assets" / "diagrams" / "judgment-surfaces.zh.svg")

    assert "Execution strategy" in diagram_en
    assert "execution posture" not in diagram_en.lower()
    assert "执行策略" in diagram_zh
    assert "执行姿态" not in diagram_zh


def test_plan_judgment_diagrams_keep_table_rows_inside_panel() -> None:
    for locale in ("en", "zh"):
        root = ET.fromstring((ROOT / "assets" / "diagrams" / f"plan-judgment-structure.{locale}.svg").read_text(encoding="utf-8"))
        panel = next(
            rect
            for rect in root.findall("svg:rect", SVG_NAMESPACE)
            if rect.attrib.get("x") == "58" and rect.attrib.get("y") == "126"
        )
        panel_bottom = float(panel.attrib["y"]) + float(panel.attrib["height"])
        row_rects = [
            rect
            for rect in root.findall("svg:rect", SVG_NAMESPACE)
            if rect.attrib.get("x") == "98" and rect.attrib.get("width") == "804"
        ]

        assert len(row_rects) == PLAN_JUDGMENT_TABLE_ROW_COUNT
        assert max(float(rect.attrib["y"]) + float(rect.attrib["height"]) for rect in row_rects) < panel_bottom

        diagram_text = " ".join(node.text or "" for node in root.iter())
        if locale == "en":
            assert "Execution strategy" in diagram_text
        else:
            assert "执行策略" in diagram_text

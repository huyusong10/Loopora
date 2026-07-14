from __future__ import annotations

import xml.etree.ElementTree as ET

from public_svg_asset_test_support import ROOT, PUBLIC_MARKDOWN_DOCS, public_markdown_svg_refs, public_svg_files


def test_public_markdown_svg_refs_are_manifested_distribution_assets() -> None:
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert "include README.md README.zh-CN.md" in manifest
    assert "include HUMAN-SHAPED-LOOP.md HUMAN-SHAPED-LOOP.zh-CN.md" in manifest
    assert "include CONTRIBUTING.md" in manifest
    assert "include CODE_OF_CONDUCT.md" in manifest
    assert "include CHANGELOG.md" in manifest
    assert "include GOVERNANCE.md" in manifest
    assert "include SECURITY.md" in manifest
    assert "include SUPPORT.md" in manifest
    assert "recursive-include assets/diagrams *.svg *.md" in manifest
    assert "recursive-include src/loopora/assets/logo *.svg" in manifest

    for doc in PUBLIC_MARKDOWN_DOCS:
        refs = public_markdown_svg_refs(doc)
        assert refs, f"{doc.relative_to(ROOT)} should keep its public SVG references explicit"
        for ref in refs:
            asset = ROOT / ref.removeprefix("./")
            assert asset.is_file(), f"{doc.relative_to(ROOT)} references missing public SVG {ref}"

    logo_ref = "./src/loopora/assets/logo/logo-with-text-horizontal.svg"
    assert logo_ref in public_markdown_svg_refs(ROOT / "README.md")
    assert logo_ref in public_markdown_svg_refs(ROOT / "README.zh-CN.md")


def test_public_svg_distribution_omits_provisional_asset_names() -> None:
    provisional_tokens = ("_new", "-new", "draft", "tmp", "temp", "candidate")
    offenders = [
        path.relative_to(ROOT).as_posix()
        for path in public_svg_files()
        if any(token in path.stem.lower() for token in provisional_tokens)
    ]

    assert offenders == []


def test_readme_first_use_docs_describe_plan_files_without_bundle_internals() -> None:
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    diagram_en = ET.fromstring((ROOT / "assets" / "diagrams" / "plan-judgment-structure.en.svg").read_text(encoding="utf-8"))
    diagram_zh = ET.fromstring((ROOT / "assets" / "diagrams" / "plan-judgment-structure.zh.svg").read_text(encoding="utf-8"))

    assert "plan file" in readme_en.lower()
    assert "Bundle" not in readme_en
    assert "方案文件" in readme_zh
    assert "Bundle" not in readme_zh

    diagram_en_text = " ".join(node.text or "" for node in diagram_en.iter())
    diagram_zh_text = " ".join(node.text or "" for node in diagram_zh.iter())
    assert "plan file" in diagram_en_text.lower()
    assert "bundle" not in diagram_en_text.lower()
    assert "方案文件" in diagram_zh_text
    assert "Bundle" not in diagram_zh_text


def test_public_plan_file_judgment_faces_map_to_runtime_contract() -> None:
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    contracts = (ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    for term in (
        "Task contract",
        "Agent responsibilities",
        "Execution strategy",
        "Run flow",
        "Evidence rules",
        "Verdict rules",
    ):
        assert term in readme_en

    for term in ("任务契约", "Agent 职责", "执行策略", "运行流程", "证据规则", "裁决规则"):
        assert term in readme_zh

    for term in (
        "Task contract",
        "Agent responsibilities",
        "Execution strategy",
        "Run flow",
        "Evidence rules",
        "Verdict rules",
    ):
        assert term.lower().split()[0] in contracts.lower()
    assert "Bundle is a Web-operable exchange file" in contracts
    assert "UI projections such as summaries, traceability aliases, or diagnostics are derived views" in contracts
    assert "Run status and Loop verdict are separate" in contracts

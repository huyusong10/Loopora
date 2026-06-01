from __future__ import annotations

from pathlib import Path


def alignment_bundle_governance_sentence(workdir: str, *, locale: str) -> str:
    markers = _governance_markers_for_workdir(workdir)
    if not markers:
        return ""
    marker_text = ", ".join(markers)
    if locale == "zh":
        return (
            f" 项目本地治理入口（{marker_text}）也是运行责任：Builder 读取适用规则，"
            "Inspector / Custom 验证相关 design 或 test 契约，GateKeeper 将跳过本地治理或缺少预期验证视为 Weak、Unproven 或 Blocking。"
        )
    return (
        f" Project-local governance markers ({marker_text}) are runtime responsibilities: "
        "Builder reads the applicable rules, Inspector / Custom verifies related design or test contracts, "
        "and GateKeeper treats skipped local governance or missing expected validation as Weak, Unproven, or Blocking."
    )


def alignment_bundle_governance_role_snippet(workdir: str, *, role: str, locale: str) -> str:
    markers = _governance_markers_for_workdir(workdir)
    if not markers:
        return ""
    marker_text = ", ".join(markers)
    if locale == "zh":
        snippets = {
            "builder": f"\n      Builder 读取适用的项目本地治理入口（{marker_text}），再修改工作并在 handoff 中说明治理证据。",
            "inspector": f"\n      Inspector 验证 Builder 是否遵守 {marker_text} 中相关规则、design 或 test 契约；跳过本地治理应作为弱证据或缺失证明。",
            "gatekeeper": f"\n      GateKeeper 将跳过 {marker_text} 中相关本地治理责任或缺少预期验证视为 Weak、Unproven 或 Blocking。",
        }
    else:
        snippets = {
            "builder": f"\n      Builder reads applicable project-local governance markers ({marker_text}) before changing work and names the governance evidence in the handoff.",
            "inspector": f"\n      Inspector verifies whether Builder followed the relevant {marker_text} rules, design, or test contracts; skipped local governance is weak or missing evidence.",
            "gatekeeper": f"\n      GateKeeper treats skipped {marker_text} local-governance responsibilities or missing expected validation as Weak, Unproven, or Blocking.",
        }
    return snippets.get(role, "")


def _governance_markers_for_workdir(workdir: str) -> list[str]:
    root = Path(str(workdir or "")).expanduser()
    markers: list[str] = []
    if (root / "AGENTS.md").is_file():
        markers.append("AGENTS.md")
    design_dir = root / "design"
    if (design_dir / "README.md").is_file():
        markers.append("design/README.md")
    if design_dir.is_dir():
        markers.append("design/")
    if (root / "tests").is_dir():
        markers.append("tests/")
    return markers

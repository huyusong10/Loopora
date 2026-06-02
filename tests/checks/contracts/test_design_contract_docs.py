from __future__ import annotations

from pathlib import Path


MAX_DESIGN_DOC_COUNT = 4


def test_design_main_workflow_anchors_separate_run_status_and_loop_verdict() -> None:
    root = Path(__file__).resolve().parents[3]
    design_sources = {
        "design/README.md": (root / "design" / "README.md").read_text(encoding="utf-8"),
        "design/contracts.md": (root / "design" / "contracts.md").read_text(encoding="utf-8"),
    }

    contracts = design_sources["design/contracts.md"]
    assert "Web is full-function" in contracts
    assert "READY preview must reflect current canonical content" in contracts
    assert "Run status and Loop verdict are separate" in contracts
    assert "Templates/tests inherit host model/provider defaults" in contracts
    assert "Loopora only owns `.loopora/` state" in contracts
    assert "Loopora-managed host entry files" in contracts
    assert "Public adapter names stay `loopora-*`" in contracts

    for source in design_sources.values():
        assert "bundle library" not in source.lower()
        assert "Web 只是观察面" not in source


def test_design_tree_stays_small_and_current() -> None:
    root = Path(__file__).resolve().parents[3]
    design_files = sorted(path.relative_to(root).as_posix() for path in (root / "design").rglob("*.md"))

    assert "design/core-ideas/product-principle.md" not in design_files
    assert "design/detailed-design/09-web-bundle-alignment.md" not in design_files
    assert {"design/contracts.md", "design/loopora_loop_kernel_refactor.md"} <= set(design_files)
    assert len(design_files) <= MAX_DESIGN_DOC_COUNT


def test_workflow_design_default_is_linear_with_advanced_compatibility() -> None:
    root = Path(__file__).resolve().parents[3]
    runtime_design = (root / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "Builder -> optional Inspector/Guide -> GateKeeper" in runtime_design
    assert "Advanced parallel/control fields are compatibility or expert-only surfaces" in runtime_design


def test_compiler_design_keeps_web_and_agent_on_same_core() -> None:
    root = Path(__file__).resolve().parents[3]
    contracts = (root / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "same Core" in contracts
    assert "One shared success path and one shared failure path across Web/Agent" in contracts
    assert "Templates/tests inherit host model/provider defaults" in contracts
    assert "model/provider defaults" in contracts


def test_agent_native_execution_plane_decision_uses_current_step_view_terms() -> None:
    root = Path(__file__).resolve().parents[3]
    decision = (root / "design" / "decisions" / "agent-native-execution-plane.md").read_text(encoding="utf-8")

    assert "Agent Step View projection" in decision
    assert "StepInstruction context boundary" in decision
    assert "execution capsule" not in decision
    assert "step capsule" not in decision
    assert "control capsules" not in decision
    assert "StepContextPacket" not in decision

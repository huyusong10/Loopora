from __future__ import annotations

import yaml

from review_runner_test_support import ROOT, case_targets, target_terms


AGENT_NATIVE_HANDBOOK_MIN_BYTES_PER_FILE = 48000
PLAN_RUN_CONTRACT_MIN_BYTES_PER_FILE = 40000
TOP_LEVEL_ANCHOR_MIN_BYTES_PER_FILE = 30000


def test_default_path_language_case_keeps_hint_scope_on_default_surfaces() -> None:
    _case, targets = case_targets("default-path-language.md")

    text_globs = set(targets["default-path-text"]["globs"])
    hint_globs = set(targets["expert-language-hints"]["globs"])
    hint_terms = target_terms(targets["expert-language-hints"])

    assert "src/loopora/assets/alignment/product-primer.md" in text_globs
    assert "src/loopora/assets/system_prompts/alignment/web-alignment-agent.md" in text_globs
    assert "README.md" in text_globs
    assert "README.zh-CN.md" in text_globs
    assert "src/loopora/templates/partials/*.html" in text_globs
    assert "src/loopora/templates/partials/*.html" in hint_globs
    assert {"workflow", "workflow controls", "orchestration"}.issubset(hint_terms)
    assert all(not glob.startswith("src/loopora/assets/alignment/") for glob in hint_globs)
    assert "README.md" in hint_globs
    assert "README.zh-CN.md" in hint_globs
    assert "src/loopora/templates/bundle_detail.html" not in hint_globs
    assert "src/loopora/templates/bundles.html" not in hint_globs
    assert "src/loopora/templates/new_orchestration.html" not in hint_globs
    assert "src/loopora/templates/new_role_definition.html" not in hint_globs
    assert "src/loopora/templates/orchestrations.html" not in hint_globs
    assert "src/loopora/templates/role_definitions.html" not in hint_globs
    assert "src/loopora/templates/index.html" in hint_globs
    assert "src/loopora/templates/new_loop.html" in hint_globs
    assert "src/loopora/templates/run_detail.html" in hint_globs


def test_concept_coherence_case_keeps_core_concepts_out_of_drift_hints() -> None:
    case, targets = case_targets("concept-coherence.md")
    anchor_globs = set(targets["top-level-anchor-text"]["globs"])
    drift_terms = target_terms(targets["concept-drift-hints"])
    drift_globs = set(targets["concept-drift-hints"]["globs"])
    source_globs = set(targets["concept-source-text"]["globs"])
    plan_run_globs = set(targets["plan-run-contract-text"]["globs"])

    assert anchor_globs == {
        "README.md",
        "README.zh-CN.md",
        "HUMAN-SHAPED-LOOP.md",
        "HUMAN-SHAPED-LOOP.zh-CN.md",
    }
    assert targets["top-level-anchor-text"]["max_bytes_per_file"] >= TOP_LEVEL_ANCHOR_MIN_BYTES_PER_FILE
    assert {"prompt pack", "role zoo", "generic chat", "script runner", "loop script", "chat wrapper"}.issubset(
        drift_terms
    )
    assert {"一点也", "这个图", "这里可能", "看看怎么", "有点突兀", "受到质疑", "吸引力"}.issubset(
        drift_terms
    )
    assert "human-in-the-loop" not in drift_terms
    assert "evidence" not in drift_terms
    assert "judgment" not in drift_terms
    assert "GateKeeper" not in drift_terms
    assert "design/contracts.md" in source_globs
    assert "src/loopora/assets/system_prompts/alignment/web-alignment-agent.md" in source_globs
    assert "design/detailed-design/08-bundles-and-alignment.md" not in source_globs
    assert "design/detailed-design/10-agent-adapters.md" not in source_globs
    assert plan_run_globs == {"design/contracts.md"}
    assert targets["plan-run-contract-text"]["max_bytes_per_file"] >= PLAN_RUN_CONTRACT_MIN_BYTES_PER_FILE
    assert "design/core-ideas/*.md" not in drift_globs
    assert "src/loopora/assets/alignment/*.md" not in drift_globs
    assert "README.md" in drift_globs
    assert "src/loopora/templates/tutorial.html" in drift_globs
    assert "Whether bundle design still externalizes task-scoped human judgment" in case.brief
    assert "Whether `/loopora-plan` still helps the human externalize judgment" in case.brief
    assert "Whether `/loopora-run` still executes the reviewed Loop" in case.brief


def test_agent_native_case_keeps_core_concepts_out_of_shortcut_hints() -> None:
    _case, targets = case_targets("agent-native-behavior.md")
    risk_terms = set(targets["agent-native-risk-hints"]["terms"])
    risk_globs = set(targets["agent-native-risk-hints"]["globs"])
    handbook_globs = set(targets["agent-native-handbook"]["globs"])

    assert {"inline", "nested", "prewritten", "host dispatch"}.issubset(risk_terms)
    assert "READY" not in risk_terms
    assert "evidence" not in risk_terms
    assert targets["agent-native-risk-hints"]["optional"] is True
    assert ".loopora/real-probes/*phase-report.json" in risk_globs
    assert ".loopora/real-probes/**/*phase-report.json" in risk_globs
    assert "design/contracts.md" in handbook_globs
    assert "design/decisions/agent-native-execution-plane.md" in handbook_globs
    assert "src/loopora/assets/system_prompts/agent_native/*.md" in handbook_globs
    assert "tests/probes/real_environment/README.md" in handbook_globs
    assert "tests/probes/real_environment/test_real_agent_adapter_probe.py" in handbook_globs
    assert targets["agent-native-handbook"]["max_bytes_per_file"] >= AGENT_NATIVE_HANDBOOK_MIN_BYTES_PER_FILE
    assert "design/contracts.md" not in risk_globs
    assert "tests/probes/real_environment/README.md" not in risk_globs
    assert "tests/probes/real_environment/*.py" not in risk_globs


def test_review_case_files_have_valid_front_matter() -> None:
    for path in sorted((ROOT / "tests" / "reviews" / "cases").glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        assert raw.startswith("---\n"), path
        _prefix, front_matter, _body = raw.split("---", 2)
        metadata = yaml.safe_load(front_matter)
        assert metadata["id"]
        assert metadata["targets"]

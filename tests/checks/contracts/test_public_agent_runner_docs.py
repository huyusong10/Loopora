from __future__ import annotations

from public_docs_test_support import ROOT, _assert_semantic_groups


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
        ("model selection", "backend routing", "permissions", "credentials"),
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
        ("模型选择", "后端路由", "权限", "凭据"),
        ("提示", "宿主记忆"),
    )

    for label, text in english_docs.items():
        _assert_semantic_groups(text, english_semantics, label=label)
    for label, text in chinese_docs.items():
        _assert_semantic_groups(text, chinese_semantics, label=label)


def test_readmes_link_public_contribution_and_security_paths() -> None:
    english_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese_readme = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

    _assert_semantic_groups(
        english_readme,
        (
            ("actions/workflows/ci.yml", "actions/workflows/codeql.yml"),
            ("CONTRIBUTING.md", "quality gates"),
            ("SECURITY.md", "public issues"),
        ),
        label="README.md",
    )
    _assert_semantic_groups(
        chinese_readme,
        (
            ("actions/workflows/ci.yml", "actions/workflows/codeql.yml"),
            ("CONTRIBUTING.md", "质量门"),
            ("SECURITY.md", "公开 issue"),
        ),
        label="README.zh-CN.md",
    )

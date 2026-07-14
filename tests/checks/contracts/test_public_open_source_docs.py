from __future__ import annotations

import tomllib

import yaml

from public_docs_test_support import ROOT, _assert_semantic_groups


def test_public_readmes_offer_an_isolated_demo_without_misrepresenting_simulated_evidence() -> None:
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    for text in (english, chinese):
        assert "loopora demo --open" in text
        assert "Ctrl-C" in text
        assert "temporary App" in text or "临时 App" in text
        assert "simulated" in text or "模拟" in text
        assert "provider" in text


def test_public_docs_position_run_evidence_export_as_private_review_material() -> None:
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for text in (english, chinese, changelog):
        assert "loopora loops export-run <run-id>" in text
        assert "--force" in text
        assert "support bundle" in text
        assert "workspace files" in text or "工作区文件" in text
        assert "private" in text or "私有" in text


def test_public_docs_explain_cross_run_progress_without_evidence_count_shortcuts() -> None:
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for text in (english, chinese, changelog):
        assert "run_progress" in text
        assert "coverage target" in text
        assert "evidence count" in text or "evidence 条数" in text
        assert "contract changed" in text or "契约发生变化" in text or "changed target contracts" in text


def test_public_docs_explain_saved_loop_evidence_continuation_and_recorded_closure() -> None:
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for text in (english, chinese, changelog):
        assert "POST /api/loops/<loop-id>/runs" in text
        assert "evidence gaps" in text or "证据缺口" in text
        assert "lifecycle failure" in text or "生命周期失败" in text
        assert "recorded" in text or "已经记录" in text
        assert "advisory" in text or "建议跟进" in text


def test_public_docs_explain_cross_run_continuation_as_action_control() -> None:
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for text in (english, chinese, changelog):
        assert "change_approach" in text
        assert "repair_regression" in text
        assert "target-level" in text or "目标级" in text
        assert "evidence count" in text or "evidence volume" in text or "evidence 数量" in text
        assert "loopora loops status <run-id>" in text
        assert "GET /api/runs/<run-id>" in text


def test_pyproject_public_metadata_keeps_loopora_positioning_discoverable() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    description = project["description"].lower()
    keywords = set(project["keywords"])

    for term in ("evidence", "loop", "long-running", "agent"):
        assert term in description
    assert {"ai-agents", "agent-workflows", "evidence", "human-in-the-loop", "local-first", "long-running-agents"} <= keywords
    assert project["authors"] == [{"name": "Loopora contributors"}]
    assert project["maintainers"] == [{"name": "Loopora maintainers"}]
    assert project["urls"]["Community"] == "https://github.com/huyusong10/Loopora/blob/dev/CODE_OF_CONDUCT.md"
    assert project["urls"]["Documentation"] == "https://github.com/huyusong10/Loopora/blob/dev/README.md"
    assert project["urls"]["Governance"] == "https://github.com/huyusong10/Loopora/blob/dev/GOVERNANCE.md"
    assert project["urls"]["Support"] == "https://github.com/huyusong10/Loopora/blob/dev/SUPPORT.md"
    assert "license" not in project
    assert not any(str(classifier).startswith("License ::") for classifier in project["classifiers"])


def test_contributing_doc_keeps_local_quality_gates_and_boundary_rules_actionable() -> None:
    text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    required_semantics = (
        ("Python 3.11", "uv", "Node.js"),
        (".editorconfig", ".gitattributes", "LF"),
        ("uv sync --locked",),
        ("uv run loopora dev check",),
        ("default gate", "package-build cleanup", "tmp/package-check", "src/loopora.egg-info", "final PR evidence"),
        ("uv run loopora dev check --list", "--pr-evidence", "focused check guide"),
        ("current Git changes", "non-ignored untracked files"),
        ("changed files", "do not match any focused guide"),
        ("ignored changed files: none", "unmatched changed files: none"),
        ("Plain output", "PR evidence:", "template-ready Markdown block", "evidence_stage", "decision", "focused_passed", "default_fast_passed", "--focused-ran"),
        ("cover the recommended boundary", "remaining recommended guide IDs", "already-passed guide IDs"),
        ("focused selector choices", "recommended", "all", "guide IDs"),
        ("uv run loopora dev check --focused recommended",),
        ("Paste the final `### Loopora PR Evidence` block", "main local evidence block", "decision scope", "skipped guide IDs", "package-build cleanup", "Add separate notes only", "unmatched stable-boundary files", "additional focused, journey, review, or probe evidence", "skipped with a reason"),
        ("First-use readiness", "doctor", "adapter setup", "App/Web reset"),
        ("Web routes", "diagnostics APIs", "static assets"),
        ("Agent Native", "/loopora-plan", "/loopora-run"),
        ("Alignment dialogue", "READY validation", "traceability"),
        ("Kernel/Event Core", "context schema", "executor/provider profiles"),
        ("Run lifecycle", "run observation", "settings/local App state"),
        ("Contributor docs", "design map", "GitHub templates/workflows", "review/scenario evidence workflows", "package contents"),
        ("first_use_readiness", "web_surfaces", "agent_native", "alignment_bundle"),
        ("core_execution", "runtime_state", "open_source_collaboration"),
        ("uv run loopora dev check --focused first_use_readiness",),
        ("uv run loopora dev check --focused open_source_collaboration",),
        ("current expanded pytest commands", "instead of copying static file lists"),
        ("uv run pytest tests/checks/journeys -q",),
        ("Dependency update pull requests", "uv", "GitHub Actions", "uv.lock"),
        ("CodeQL", "Python", "JavaScript/TypeScript"),
        ("Real Probe", "workflow_dispatch", "release", "ordinary pull requests"),
        ("Real Probe", ".loopora/real-probes/", "GitHub artifact", "phase evidence"),
        ("Release Readiness", "maintainer-owned evidence", "not an ordinary pull request gate"),
        ("candidate version or tag", "supported", "SECURITY.md"),
        ("Copy the release-plan evidence commands as printed", "preserve the release workdir", "intended checkout"),
        ("uv run loopora dev check --list --pr-evidence", "recommended focused guide IDs"),
        ("uv run loopora dev check --focused recommended", "uv run loopora dev check"),
        ("browser journey checks", "touched Web behavior", "affected boundary"),
        ("Real Probe", "workflow_dispatch", "default `release` suite", ".loopora/real-probes/"),
        ("package_build", "wheel", "sdist", "no-license boundary"),
        ("CHANGELOG.md", "unreleased entries", "supported status"),
        ("Release notes", "skipped probes", "residual risks", "security-sensitive details"),
        ("bug report template", "feature request template", "SECURITY.md"),
        ("Select the PR template change type", "bug fixes", "user-visible behavior", "docs/support work", "refactors", "release/security/distribution-sensitive changes"),
        ("Bug reports", "report scope", "behavior regression", "setup/readiness blocker", "upstream Agent/OS/tool issue"),
        ("Bug reports", "impact/workaround", "maintainers"),
        ("SUPPORT.md", "best-effort help path"),
        ("placeholder-safe command shapes", "<project-dir>", "<Loopora checkout>", "<redacted>", "real local paths"),
        ("Feature proposals", "Loopora", "direct Agent use", "ordinary tests/checks", "project-specific workflow"),
        ("affected workflow/adoption impact", "observable success criteria", "non-goals", "evidence", "compatibility risk"),
        ("Feature proposals", "first-use", "Web", "readiness", "package identity", "environment behavior"),
        ("public readiness report status", "public issue support bundle first", "public doctor/version output", "never paste command lines"),
        ("public PR evidence", "public issue support bundle first", "public doctor/version output", "redacted diagnostic output", "not local command lines", "<project-dir>", "<Loopora checkout>", "<redacted>"),
        ("Community Standards", "CODE_OF_CONDUCT.md", "respectful", "safe", "evidence-oriented"),
        ("GOVERNANCE.md", "supported release tags", "package distribution", "security posture", "compatibility/migration risk", "license status"),
        ("design/README.md", "design/contracts.md"),
        ("CLI output", "Web routes", "API payloads", "runner state"),
        ("observable contracts", "structured outputs", "accessible behavior"),
        ("license", "maintainer approval"),
    )

    _assert_semantic_groups(text, required_semantics, label="CONTRIBUTING.md")
    assert "test_readme_first_use_commands.py" not in text


def test_readmes_keep_first_use_entry_paths_clear() -> None:
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

    assert english.index("## Project Status") < english.index("## From `/goal` To Loop")
    assert chinese.index("## 项目状态") < chinese.index("## 从 `/goal` 到 Loop")
    assert english.index("## Project Status") < english.index("## Start Here") < english.index("## From `/goal` To Loop")
    assert chinese.index("## 项目状态") < chinese.index("## 从这里开始") < chinese.index("## 从 `/goal` 到 Loop")
    english_intro = english.split("## Project Status", 1)[0]
    chinese_intro = chinese.split("## 项目状态", 1)[0]
    _assert_semantic_groups(
        english_intro,
        (
            ("first choose the right route", "before setup or creation"),
            ("When the task fits Loopora", "/loopora-plan", "/loopora-run"),
        ),
        label="README.md intro",
    )
    _assert_semantic_groups(
        chinese_intro,
        (
            ("先在设置或创建前选对路线",),
            ("当任务适合 Loopora", "适配理由", "/loopora-plan", "/loopora-run"),
        ),
        label="README.zh-CN.md intro",
    )
    assert "first use `/loopora-plan`" not in english_intro
    assert "先用 `/loopora-plan`" not in chinese_intro
    assert "agent--native-loop" in english
    assert "agent--native-loop" in chinese
    assert "agent--first-loop" not in english
    assert "agent--first-loop" not in chinese
    assert "open the Fit Guide/Web choices route" in english
    assert "打开适用性判断/Web 选择路线" in chinese
    assert "Web conversation, Plan File import, and manual expert paths enter the same local records" in english
    assert "Web 对话、Plan File 导入和手动专家路径都会进入同一套本地记录" in chinese
    assert "Loopora first-use routes" in english
    assert "Loopora first-use entries" not in english
    _assert_semantic_groups(
        english,
        (
                (
                    "Project Status",
                    "experimental local-first",
                    "wheel-backed copy",
                    "editable checkout",
                    "build-time Git revision",
                    "clean/dirty state",
                    "without local checkout paths",
                "SUPPORT.md",
                "SECURITY.md",
                "does not declare a license",
                "no guaranteed response time",
                "current development line",
                "release tags maintainers explicitly mark as supported",
                "loopora --version",
                "loopora version --json",
                "loopora support",
                "doctor --public-json",
                "preview-only",
                "support --workdir",
                "public issue bundle or public doctor command becomes ready", "missing or not a directory", "setup target remains not ready",
                "diagnostic material",
                "public issue support bundle first",
                "public doctor/version output only",
                "loopora support --json",
                "JSON command fields",
                "local-only",
                "private reporting is unavailable",
                "public issue may only ask for a private channel",
            ),
            ("Before install", "install command plus readiness check"),
            ("Agent-session happy path", "reviewed plan in the Agent", "same Agent session"),
            ("Run handoff is progressively disclosed", "exact host-native role message", "result-file path", "Full frozen judgment", "--json"),
            ("not already inside an Agent session", "Fit Guide/Web choices route"),
            ("Web conversation", "Plan File import", "manual expert paths", "same local records", "Same-Agent setup stays separate"),
            ("creation, review, and management surface", "review evidence", "inspect runs"),
            ("Web links", "creation choices", "run status", "details"),
            ("maintenance commands below", "adapter you chose above", "replace `<agent>` with `codex`, `claude`, or `opencode`", "current Agent host"),
            ("remove Loopora from one project entry", "loopora uninstall <agent> --workdir", "loopora doctor --workdir"),
            ("only files proven Loopora-managed", "does not delete Loop records", "run artifacts", "global Agent configuration", "external service history"),
            ("refresh or restart", "Reinstall later", "loopora init <agent> --workdir"),
            (
                "CODE_OF_CONDUCT.md",
                "respectful",
                "safe",
                "evidence-oriented",
                "public collaboration",
            ),
            (
                "GOVERNANCE.md",
                "maintainer-owned decisions",
                "supported release tags",
                "license/distribution posture",
                "security disclosure",
                "compatibility or migration risk",
            ),
            (
                "CHANGELOG.md",
                "public change history",
                "unreleased adoption notes",
                "release-note requirements",
                "source-checkout behavior",
            ),
            (
                "loopora support",
                "SUPPORT.md",
                "best-effort usage or setup support",
                "loopora support --workdir \"$PWD\" --public-issue-bundle",
                "preview-only",
                "support --workdir",
                "public issue bundle or public doctor command becomes ready", "missing or not a directory", "setup target remains not ready",
                "diagnostic material",
                "public issue support bundle first",
                "public doctor/version output only",
                "loopora version --json",
                "structured identity",
                "support JSON",
                "JSON command fields",
                "local Web Support URLs",
                "local-only",
            ),
            ("License", "does not declare a license", "redistribution", "reuse", "maintainer-approved decisions"),
            ("Start Here", "loopora start --workdir", "source checkout before install", "uv run loopora start", "uv --directory <Loopora checkout> run loopora start --workdir", "hides route commands", "rerun command", "target project", "no completed fit review", "review-only Web Fit Guide command", "Setup, creation, init, doctor, `/loopora-plan`, and run routes stay hidden or blocked", "review actions separate from future route state", "completed strong-fit review", "preflights the default local Web port", "available alternate", "Web can continue independently", "same-Agent path shows `init current` before the reviewed `/loopora-plan` message", "must not be pasted until setup reports ready", "setup_gate_ready", "setup_gate_blockers", "reviewed setup readiness", "read-only", "does not install same-Agent project entries", "start Web", "decide whether"),
            ("Start Here", "Pick the route before you install same-Agent project entries or create a Loop"),
            ("Unsure whether this task needs Loopora", "loopora fit", "uv run loopora fit", "before setup"),
            ("Already working inside Codex", "loopora init current --workdir", "uv --directory <Loopora checkout> run loopora init current", "explicit `<agent>`", "loopora doctor --workdir", "/loopora-plan", "/loopora-run"),
            ("Not inside an Agent session", "Fit Guide/Web choices", "loopora serve --open --workdir", "uv --directory <Loopora checkout> run loopora serve --open --workdir \"$PWD\"", "Web conversation", "Plan File import", "manual expert mode", "use same-Agent setup only"),
            ("Manage same-Agent project entries", "install, update, or remove", "same-Agent project entries"),
            ("Already have a plan file", "Web import", "manual expert path", "Preview before creating or running"),
            ("Inspecting an existing Loop or run", "Review evidence", "verdict state", "residual risk", "next action"),
        ),
        label="README.md",
    )
    _assert_semantic_groups(
        chinese,
        (
            (
                "项目状态",
                "实验性",
                "local-first",
                "wheel 形式的独立副本",
                "editable 源码安装",
                "构建时的 Git 修订",
                "clean/dirty 状态",
                "不记录本地源码路径",
                "SUPPORT.md",
                "SECURITY.md",
                "尚未声明 license",
                "没有响应时间承诺",
                "当前开发线",
                "supported 的 release tag",
                "loopora --version",
                "loopora version --json",
                "loopora support --language zh",
                "doctor --public-json",
                "人工可读就绪摘要",
                "仅预览",
                "support --language zh --workdir",
                "公开 issue 支持包或 public doctor 命令才是可复制的就绪命令", "目标不存在或不是目录", "设置目标仍未就绪",
                "公开 issue",
                "诊断材料",
                "优先粘贴公开 issue 支持包",
                "loopora support --json",
                "JSON command 字段",
                "本地 Web 支持页 URL",
                "只留在本地",
                "私密报告入口不可用",
                "公开 issue 只能请求私密渠道",
            ),
            ("安装前", "安装命令和就绪检查"),
            ("Agent 会话内的最短路径", "在 Agent 内创建已审查方案", "同一个 Agent 会话"),
            ("运行交接采用渐进披露", "精确的宿主原生角色消息", "结果文件路径", "完整冻结判断", "--json"),
            ("不在 Agent 会话里", "适用性判断/Web 选择路线"),
            ("Web 对话", "Plan File 导入", "手动专家路径", "同一套本地记录", "同一 Agent 设置则保留"),
            ("创建、审查和管理界面", "审查证据", "查看运行"),
            ("Web 链接", "选择创建路径", "运行状态", "详情"),
            ("管理同一 Agent 项目入口", "安装、更新或移除", "同一 Agent 项目入口"),
            ("下面维护命令", "上面选定的适配器", "把 `<agent>` 换成", "`codex`、`claude` 或 `opencode`"),
            ("移除 Loopora 的同一 Agent 项目入口", "loopora uninstall <agent> --workdir", "loopora doctor --workdir"),
            ("只会移除能证明由 Loopora 托管", "不会删除 Loop 记录", "运行证据", "全局 Agent 配置", "外部服务历史"),
            ("刷新或重启", "恢复", "loopora init <agent> --workdir"),
            (
                "CODE_OF_CONDUCT.md",
                "尊重",
                "安全",
                "证据导向",
                "公共协作",
            ),
            (
                "GOVERNANCE.md",
                "维护者所有",
                "supported release tag",
                "license/distribution",
                "安全披露",
                "兼容性或迁移风险",
            ),
            (
                "CHANGELOG.md",
                "公开变更历史",
                "未发布采用提示",
                "release note 要求",
                "源码检出行为",
            ),
            (
                "loopora support --language zh",
                "SUPPORT.md",
                "使用或设置支持",
                "loopora support --language zh --workdir \"$PWD\" --public-issue-bundle",
                "仅预览",
                "support --language zh --workdir",
                "公开 issue 支持包或 public doctor 命令才是可复制的就绪命令", "目标不存在或不是目录", "设置目标仍未就绪",
                "诊断材料",
                "优先粘贴公开 issue 支持包",
                "public doctor/version 输出",
                "support JSON",
                "JSON command 字段",
                "本地 Web 支持页 URL",
                "只留在本地",
            ),
            ("License", "尚未声明 license", "重新分发", "复用", "维护者明确批准"),
            ("从这里开始", "loopora start --workdir", "安装前仍在源码检出中", "uv run loopora start", "uv --directory <Loopora 源码检出> run loopora start --workdir", "隐藏路线命令", "目标项目重跑", "适配审查尚未补齐", "仅用于继续审查的 Web Fit Guide 命令", "设置、创建、init、doctor、`/loopora-plan` 和 run 路线仍保持隐藏或阻止", "把审查动作与未来路线状态分开", "强适配审查补齐后", "预检默认本地 Web 端口", "可用替代端口", "Web 可以独立继续", "同一 Agent 路线会先展示 `init current`", "设置报告就绪前不能粘贴发送", "setup_gate_ready", "setup_gate_blockers", "已审查设置就绪", "只读向导", "不会安装同一 Agent 项目入口", "不会启动 Web", "不会替你判断"),
            ("从这里开始", "先选路线", "安装同一 Agent 项目入口或创建 Loop"),
            ("还不确定任务是否需要 Loopora", "loopora fit --language zh", "uv run loopora fit --language zh", "设置前"),
            ("已经在 Codex", "loopora init current --workdir", "uv --directory <Loopora 源码检出> run loopora init current", "明确的 `<agent>`", "loopora doctor --workdir", "/loopora-plan", "审查预览", "/loopora-run"),
            ("当前不在 Agent 会话里", "适用性判断/Web 选择", "loopora serve --open --workdir", "uv --directory <Loopora 源码检出> run loopora serve --open --workdir \"$PWD\"", "Web 对话", "Plan File 导入", "手动专家模式", "才走同一 Agent 设置"),
            ("已经有方案文件", "Web 导入", "手动专家路径", "创建或运行 Loop 前先预览"),
            ("已有 Loop 或 run", "审查证据", "裁决状态", "残余风险", "下一步动作"),
        ),
        label="README.zh-CN.md",
    )
    assert "Web observation command" not in english
    assert "Web 观察命令" not in chinese
    assert "composer and management surface" not in english
    assert "observation and management surface" not in english
    assert "观察和管理界面" not in chinese
    english_start_here = english.split("## Start Here", 1)[1].split("## From `/goal` To Loop", 1)[0]
    chinese_start_here = chinese.split("## 从这里开始", 1)[1].split("## 从 `/goal` 到 Loop", 1)[0]
    assert english_start_here.index("Not inside an Agent session") < english_start_here.index("Already working inside Codex")
    assert chinese_start_here.index("当前不在 Agent 会话里") < chinese_start_here.index("已经在 Codex")
    assert english.index("adapter you chose above") < english.index("loopora init <agent> --workdir \"$PWD\" --check") < english.index("loopora uninstall <agent> --workdir \"$PWD\" --dry-run")
    assert chinese.index("上面选定的适配器") < chinese.index("loopora init <agent> --workdir \"$PWD\" --check") < chinese.index("loopora uninstall <agent> --workdir \"$PWD\" --dry-run")


def test_readmes_make_loopora_fit_guidance_discoverable_before_setup() -> None:
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

    _assert_semantic_groups(
        english,
        (
            ("loopora fit", "static decision guide", "not a classifier"),
            ("Installed Loopora command", "loopora fit"),
            ("Source checkout before `uv tool install`", "uv run loopora fit"),
            ("uv --directory <Loopora checkout> run loopora", "--workdir \"$PWD\"", "plain `uv run loopora ...`", "shell is still in the checkout", "loopora fit --workdir \"$PWD\""),
            ("strong-fit signals", "direct Agent use", "hard checks", "route family", "Targetless plain output hides", "JSON keeps `<project-dir>`", "--workdir", "validates that target", "target is usable"),
            ("loopora fit --task", "completed fit review", "human review draft", "does not declare the task fit automatically"),
            ("--language zh", "zh-CN", "normalized", "zh"),
            ("loopora doctor --workdir", "Chinese terminal report", "Doctor/Fit/Support", "language-neutral schema"),
            ("--fake-done", "--evidence", "--tradeoffs", "--why-not-direct", "first `/loopora-plan` message shape", "review-only Web Fit Guide command", "terminal completion command as an alternative", "unlock setup before review"),
            ("--prefer-direct", "direct-path reason", "task-only `--prefer-direct` stays blocked", "setup routes stay blocked", "no copyable `/loopora-plan` message"),
            (
                "Quick Start", "Before install",
                "uv run loopora --version",
                "uv run loopora fit",
                "uv run loopora fit --prefer-direct --direct-path", "uv tool install .", "uv tool install --editable .",
                "cd /path/to/your/project", "loopora start --workdir \"$PWD\"", "route chooser output as the next-step authority",
                "uv tool update-shell", "uv tool install --force .", "uv tool install --force --editable .",
                "uv tool uninstall loopora", "separate from `loopora uninstall <agent> --workdir \"$PWD\"`",
            ),
            (
                "Quick Start",
                "complete copyable `/loopora-plan` handoff",
                "single Agent message",
                "/loopora-plan",
                "Loopora fit reason",
                "task goal",
                "fake-done risk",
                "required evidence",
                "judgment tradeoffs",
                "direct-path context",
            ),
        ),
        label="README.md",
    )
    _assert_semantic_groups(
        chinese,
        (
            ("loopora fit", "静态决策指南", "不是分类器"),
            ("已安装 Loopora 命令", "loopora fit --language zh"),
            ("源码检出", "uv tool install", "uv run loopora fit --language zh"),
            ("uv --directory <Loopora 源码检出> run loopora", "--workdir \"$PWD\"", "裸 `uv run loopora ...`", "Loopora 源码目录", "loopora fit --workdir \"$PWD\""),
            ("强适配信号", "直接用 Agent", "硬性检查", "路线类型", "没有目标项目", "普通文本会隐藏 Web/init/doctor 命令细节", "JSON 会保留 `<project-dir>`", "--workdir", "验证该目标", "目标可用"),
            ("loopora fit --task", "完整适配性审查", "人工判断草稿", "不会自动宣布这个任务适合 Loopora"),
            ("--language zh", "zh-CN", "归一回", "zh"),
            ("loopora doctor --workdir", "完整中文终端报告", "Doctor/Fit/Support", "schema、状态值与 action kind", "语言无关"),
            ("--fake-done", "--evidence", "--tradeoffs", "--why-not-direct", "第一条 `/loopora-plan` 消息形状", "仅用于继续审查的 Web Fit Guide 命令", "终端补全命令作为备选", "审查完成前放开设置"),
            ("--prefer-direct", "直接路径理由", "只有任务目标的 `--prefer-direct` 会保持阻止", "设置路线会保持阻止", "不会生成可复制的 `/loopora-plan` 消息"),
            (
                "快速开始", "安装前",
                "uv run loopora --version",
                "uv run loopora fit --language zh",
                "uv run loopora fit --prefer-direct --direct-path",
                "uv tool install .", "uv tool install --editable .",
                "cd /path/to/your/project", "loopora start --workdir \"$PWD\"", "路线向导输出作为下一步依据",
                "uv tool update-shell", "uv tool install --force .", "uv tool install --force --editable .",
                "uv tool uninstall loopora", "这和下面的 `loopora uninstall <agent> --workdir \"$PWD\"` 不同",
            ),
            (
                "快速开始",
                "完整可复制 `/loopora-plan` 交接",
                "一条 Agent 消息",
                "/loopora-plan",
                "Loopora 适配理由",
                "任务目标",
                "伪完成风险",
                "必要证据",
                "判断取舍",
                "可选直接路径上下文",
            ),
        ),
        label="README.zh-CN.md",
    )
    english_quick_start = english.split("## Quick Start", 1)[1].split("## How `/loopora-plan` Plans", 1)[0]
    chinese_quick_start = chinese.split("## 快速开始", 1)[1].split("## `/loopora-plan` 如何规划", 1)[0]
    assert english_quick_start.index("uv run loopora --version") < english_quick_start.index("uv tool install .")
    assert english_quick_start.index("uv run loopora fit") < english_quick_start.index("uv tool install .")
    assert english_quick_start.index("uv tool install .") < english_quick_start.index("uv tool install --editable .")
    assert english_quick_start.index("uv tool update-shell") < english_quick_start.index("loopora serve")
    assert english_quick_start.index("uv tool update-shell") < english_quick_start.index("loopora init codex")
    assert chinese_quick_start.index("uv run loopora --version") < chinese_quick_start.index("uv tool install .")
    assert chinese_quick_start.index("uv run loopora fit --language zh") < chinese_quick_start.index("uv tool install .")
    assert chinese_quick_start.index("uv tool install .") < chinese_quick_start.index("uv tool install --editable .")
    assert chinese_quick_start.index("uv tool update-shell") < chinese_quick_start.index("loopora serve")
    assert chinese_quick_start.index("uv tool update-shell") < chinese_quick_start.index("loopora init codex")
    assert "setup path when the fit is strong" not in english
    assert "task or direct-path reason" not in english
    assert "适配度较高时的设置路径" not in chinese
    assert "任务或直接路径理由" not in chinese


def test_readmes_keep_custom_web_target_doctor_guidance_actionable() -> None:
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

    _assert_semantic_groups(
        english,
        (
            ("same Web target", "--workdir", "--web-host", "--web-port"),
            ("token-required guidance", "--auth-token '<token>'", "unsafe opt-in", "bare start command"),
            ("custom host or port", "checks that port before Web initialization", "alternate free port"),
            (
                "Web/App state is blocked", "start, fit, doctor, and serve recovery",
                'LOOPORA_HOME="$(mktemp -d)"',
                "current Loopora CLI entry",
                "uv --directory <Loopora checkout> run loopora",
                "temporary Web preview", "port/bind preflight",
                "target project",
            ),
            ("without deleting or migrating the blocked App database",),
            ("loopora --version", "package/source identity", "support"),
            (
                "public issue support bundle",
                "human-readable readiness summary",
                "project-directory status",
                "source revision",
                "redacted Web readiness blockers and recovery actions",
                "action summaries",
                "local paths",
                "ports",
                "commands",
            ),
        ),
        label="README.md",
    )
    _assert_semantic_groups(
        chinese,
        (
            ("同一个 Web 目标", "--workdir", "--web-host", "--web-port"),
            ("需要 token", "--auth-token '<token>'", "unsafe opt-in", "裸启动命令"),
            ("自定义 host 或端口", "初始化 Web 前检查端口", "替代端口"),
            (
                "Web/本地应用数据被阻断", "start、fit、doctor 和 serve",
                'LOOPORA_HOME="$(mktemp -d)"',
                "当前 Loopora CLI 入口",
                "uv --directory <Loopora 源码检出> run loopora",
                "临时 Web 预览", "端口/绑定预检",
                "目标项目",
            ),
            ("不会删除或迁移被阻断的 App 数据库",),
            ("loopora --version", "普通报告", "源码身份", "公开 issue"),
            ("public doctor 报告", "包版本", "源码 revision", "人工可读就绪摘要", "脱敏后的 Web 就绪阻塞原因与恢复动作", "本地路径", "端口", "命令"),
        ),
        label="README.zh-CN.md",
    )


def test_readmes_keep_web_entry_management_target_explicit() -> None:
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

    _assert_semantic_groups(
        english,
        (
            ("Manage same-Agent project entries", "Pick a recent project", "choose a local folder", "paste a server-side target", "install", "update", "remove"),
            ("Codex", "Claude Code", "OpenCode", "same-Agent project entries"),
            (
                "Carry task brief",
                "complete or partial fit draft",
                "Web conversation",
                "Plan File import",
                "manual expert mode",
                "same-Agent setup keep stronger readiness requirements",
            ),
            ("task goal", "fake-done risk", "required evidence", "judgment tradeoffs", "optional direct-path context", "clarifies missing items"),
            ("another target project", "stays separate", "stale context"),
        ),
        label="README.md",
    )
    _assert_semantic_groups(
        chinese,
        (
            ("管理同一 Agent 项目入口", "先选最近项目", "选择本地目录", "粘贴服务端目标", "安装", "更新", "移除"),
            ("Codex", "Claude Code", "OpenCode", "同一 Agent 项目入口"),
            ("带入任务 brief", "完整或部分 fit 草稿", "Web 对话", "Plan File 导入", "手动专家模式", "同一 Agent 设置保留更强的就绪要求"),
            ("适配理由", "任务目标", "伪完成风险", "必要证据", "判断取舍", "可选直接路径上下文", "补齐缺失项"),
            ("另一个目标项目", "保持分离", "过期上下文"),
        ),
        label="README.zh-CN.md",
    )
    assert "browser-session storage" not in english
    assert "not through the URL or server" not in english
    assert "浏览器会话暂存" not in chinese
    assert "不进入 URL 或服务器" not in chinese


def test_bug_report_template_asks_for_public_readiness_report_without_private_paths() -> None:
    template_path = ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml"
    text = template_path.read_text(encoding="utf-8")
    form = yaml.safe_load(text)
    fields = {item["id"]: item for item in form["body"] if "id" in item}
    required_semantics = (
        ("Actual Behavior", "Expected Behavior"),
        ("stable error", "status", "visible result"),
        ("public contract", "recovery path"),
        ("Report Scope", "usage support", "feature request", "private security report"),
        ("Reproducible Loopora behavior regression",),
        ("Setup/readiness blocker after following SUPPORT.md",),
        ("Loopora makes an upstream Agent, OS, or tool issue worse",),
        ("Unsure; explained in Evidence",),
        ("Impact And Workaround", "workflow is blocked", "how often", "safe workaround"),
        ("Reproduction", "public command shapes", "<project-dir>", "<Loopora checkout>", "<redacted>"),
        ("Do not paste command lines with real local paths",),
        ("Public Issue Support Bundle Or Readiness Report",),
        ("Public Readiness Report Status", "Included above", "Not relevant", "Could not run"),
        ("Public diagnostic material allowlist", "loopora support", "safe public reporting router", "public issue support bundle first", "doctor --public-json", "version output", "loopora version --json"),
        ("support JSON", "printed command lines", "JSON command fields", "local Web Support URLs", "local-only"),
        ("Evidence", "short redacted stable error text", "visible status", "minimal safe log excerpts"),
        ("Public Issue Support Bundle Or Readiness Report field below", "Do not paste support JSON", "local Web Support URLs", "raw private logs", "full run artifacts"),
        ("Prefer running `loopora support --workdir \"$PWD\" --public-issue-bundle` first", "public issue support bundle", "not the command line, support JSON, or local Web Support URL"),
        ("public issue support bundle", "human-readable readiness summary", "package/source identity"),
        ("Version Or Commit", "Optional when the public issue support bundle", "package/source identity"),
        ("loopora --version", "loopora version --json", "paste the output", "not the command line"),
        ("Environment", "Optional when the public issue support bundle", "OS and Python details", "Agent host"),
        ('loopora doctor --public-json --workdir "$PWD"',),
        ("source checkout", "uv run loopora support --workdir <project-dir> --public-issue-bundle", "shell is in the Loopora checkout"),
        ("uv --directory <Loopora checkout> run loopora support --workdir \"$PWD\" --public-issue-bundle", "after changing into the target project"),
        ("loopora doctor --public-json", "underlying report"),
        ("custom Web host or port", "--web-host", "--web-port"),
        ("loopora doctor --public-json",),
        ("package/source identity", "human-readable readiness summary", "Python", "OS", "coarse project-directory status", "missing or not_directory", "setup target remains not ready", "redacted Web readiness blockers", "action summaries"),
        ("omit local paths", "ports", "commands by design"),
        ("removed secrets", "private workspace paths"),
        ("loopora support", "SUPPORT.md", "public allowlist"),
        ("SECURITY.md",),
    )

    _assert_semantic_groups(text, required_semantics, label="bug_report.yml")
    assert form["name"] == "Bug Report"
    assert form["labels"] == ["bug"]
    assert fields["actual_behavior"]["validations"] == {"required": True}
    assert fields["expected_behavior"]["validations"] == {"required": True}
    assert fields["report_scope"]["validations"] == {"required": True}
    assert fields["impact"]["validations"] == {"required": True}
    assert fields["public_doctor_status"]["validations"] == {"required": True}
    assert fields["version"]["validations"] == {"required": False}
    assert fields["version"]["attributes"]["placeholder"] == "Included in public issue support bundle above"
    assert fields["environment"]["validations"] == {"required": False}
    assert "Included in public issue support bundle above" in fields["environment"]["attributes"]["placeholder"]
    assert "Paste relevant command output" not in text


def test_support_doc_keeps_source_checkout_bundle_preferred_before_doctor_fallback() -> None:
    text = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")

    _assert_semantic_groups(
        text,
        (
            ("Need a public readiness report?", "prefer", "loopora support --workdir \"$PWD\" --public-issue-bundle"),
            ("public issue support bundle", "human-readable", "readiness summary", "redacted doctor report JSON"),
            ("source checkout before install", "uv run loopora support --workdir <project-dir> --public-issue-bundle", "Loopora checkout"),
            ("After changing into the target project", "uv --directory <Loopora checkout> run loopora support --workdir \"$PWD\" --public-issue-bundle"),
            ("doctor --public-json", "only when maintainers request", "lower-level readiness evidence"),
        ),
        label="SUPPORT.md",
    )


def test_feature_request_template_collects_loopora_fit_and_scope_boundaries() -> None:
    template_path = ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml"
    text = template_path.read_text(encoding="utf-8")
    form = yaml.safe_load(text)
    fields = {item["id"]: item for item in form["body"] if "id" in item}
    required_semantics = (
        ("Proposed Behavior", "user-observable behavior", "public contract"),
        ("SUPPORT.md", "usage or setup questions"),
        ("SECURITY.md", "private reporting", "posting details publicly"),
        ("Success Criteria And Adoption Impact", "Who would use this", "workflow becomes easier or safer", "observable result"),
        ("Loopora Fit And Non-Goals", "direct Agent use", "normal test/check", "project-specific workflow"),
        ("out of scope",),
        ("Evidence Or Examples", "prove this works"),
        ("Evidence Or Examples", "screenshots", "scenarios", "Public Issue Support Bundle Or Readiness Report field below"),
        ("command shape", "<project-dir>", "<Loopora checkout>", "<redacted>"),
        ("Do not paste support JSON", "command lines with real local paths", "local Web Support URLs", "raw private logs", "full run artifacts"),
        ("Public Issue Support Bundle Or Readiness Report", "first-use", "Web", "readiness", "package identity", "environment behavior"),
        ("Public Readiness Report Status", "Included above", "Not relevant to this proposal", "Could not run"),
        ("loopora support", "safe public reporting router", "command/support metadata local-only"),
        ("loopora support --workdir", "public issue support bundle", "not the command line, support JSON, or local Web Support URL"),
        ("doctor --public-json", "lower-level readiness evidence", "not the command line"),
        ("loopora version --json", "structured package/source identity"),
        ("source checkout", "uv run loopora support --workdir <project-dir> --public-issue-bundle", "shell is in the Loopora checkout"),
        ("uv --directory <Loopora checkout> run loopora support --workdir \"$PWD\" --public-issue-bundle", "after changing into the target project"),
        ("doctor --public-json", "lower-level readiness evidence"),
        ("human-readable readiness summary", "coarse project-directory status", "missing or not_directory", "setup target remains not ready", "redacted Web readiness blockers", "action summaries"),
        ("omit local paths", "ports", "commands by design"),
        ("Compatibility And Risk", "public API", "data", "permission", "accessibility", "localization"),
        ("public issue support bundle first", "public doctor/version output only when lower-level evidence or identity is requested", "support JSON", "command lines", "JSON command fields", "local Web Support URLs", "local-only"),
        ("affected workflow", "adoption impact", "observable success criteria"),
        ("normal tests/checks", "not enough", "non-goals"),
        ("removed secrets", "private workspace paths", "sensitive run artifacts"),
        ("loopora support", "SUPPORT.md", "public allowlist"),
    )

    _assert_semantic_groups(text, required_semantics, label="feature_request.yml")
    assert form["name"] == "Feature Request"
    assert form["labels"] == ["enhancement"]
    assert fields["success_criteria"]["validations"] == {"required": True}
    assert fields["evidence"]["validations"] == {"required": True}
    assert fields["public_doctor"]["validations"] == {"required": False}
    assert fields["public_doctor"]["attributes"]["render"] == "text"
    assert fields["public_doctor_status"]["validations"] == {"required": True}
    assert fields["risks"]["validations"] == {"required": True}


def test_issue_template_config_routes_support_and_private_security_outside_blank_issues() -> None:
    config = yaml.safe_load((ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml").read_text(encoding="utf-8"))

    assert config["blank_issues_enabled"] is False
    assert config["contact_links"][0]["name"] == "Private Security Report"
    assert "security/advisories/new" in config["contact_links"][0]["url"]
    support_links = [link for link in config["contact_links"] if link["name"] == "Support And Questions"]
    assert len(support_links) == 1
    assert support_links[0]["url"] == "https://github.com/huyusong10/Loopora/blob/dev/SUPPORT.md"
    assert "public issue support bundle allowlist" in support_links[0]["about"]


def test_pull_request_template_keeps_stable_boundary_risk_and_redacted_evidence_actionable() -> None:
    text = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
    required_semantics = (
        ("Change Type", "Bug fix or setup/readiness blocker", "User-visible feature or workflow change"),
        ("Documentation, support, or contributor experience", "Internal refactor with preserved public behavior"),
        ("Release, packaging, security, license, or distribution-sensitive change"),
        ("Stable Behavior", "public contract"),
        ("Boundary And Design", "Touched stable boundary"),
        ("Risk Level", "Low: internal", "Elevated:"),
        ("Decision scope evidence", "uv run loopora dev check --list --pr-evidence", "Loopora PR Evidence"),
        ("Loopora PR Evidence", "evidence command source", "changed-file detection", "recommended focused guide IDs", "final dev-check result", "package-build cleanup"),
        ("tmp/package-check", "src/loopora.egg-info"),
        ("unmatched/ignored changed files", "focused guide IDs run", "skipped guide IDs"),
        ("Journey, review, or probe checks", "provider behavior", "Agent host integration"),
        (
            "Issue/PR-facing readiness evidence",
            "public issue support bundle first",
            "public issue support bundle",
            "public doctor/version output",
            "lower-level evidence or identity is requested",
            "loopora version --json",
            "structured identity",
            "not local command lines",
            "local Web Support URLs",
            "loopora support --workdir",
            "--public-issue-bundle",
            "loopora doctor --public-json",
            "redacted report",
        ),
        ("public command or path examples", "<project-dir>", "<Loopora checkout>", "<redacted>", "real local paths"),
        ("same", "--web-host", "--web-port", "custom Web targets"),
        ("private workspace paths", "SECURITY.md"),
        ("license", "maintainer approval"),
    )

    _assert_semantic_groups(text, required_semantics, label="pull_request_template.md")

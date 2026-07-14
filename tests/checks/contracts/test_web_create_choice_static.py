from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _assert_peer_start_navigation_links(
    *,
    base_template: str,
    index_template: str,
    tools_template: str,
    tutorial_template: str,
    bundles_template: str,
) -> None:
    tutorial_script = (ROOT / "src" / "loopora" / "static" / "pages" / "tutorial.js").read_text(encoding="utf-8")
    bundle_route_source = (ROOT / "src" / "loopora" / "web_route_context_bundle_pages.py").read_text(encoding="utf-8")
    bundle_derive_form_route_source = (ROOT / "src" / "loopora" / "web_bundle_derive_form_routes.py").read_text(encoding="utf-8")

    assert 'href="{{ nav_home_href }}"' in base_template
    assert 'data-testid="nav-home-brand"' in base_template
    assert 'href="{{ nav_home_href }}" data-testid="nav-loops-link" data-workdir-context-link="workdir"' in base_template
    assert all(
        fragment in base_template
        for fragment in (
            'href="{{ nav_compose_href }}" data-testid="nav-compose-link" data-workdir-context-link="workdir"',
            'href="{{ nav_tools_href }}" data-testid="nav-tools-link" data-workdir-context-link="workdir"',
            "request.url.path in ['/same-agent', '/tools']",
            "request.url.path in ['/fit-guide', '/tutorial']",
            'href="{{ nav_support_href }}" data-testid="nav-support-link" data-workdir-context-link="workdir"',
            '<span data-lang="zh">同一 Agent 设置</span>',
            '<span data-lang="en">Same-Agent Setup</span>',
            '<span data-lang="zh">适用性判断</span>',
            '<span data-lang="en">Fit Guide</span>',
            '<span data-lang="zh">支持</span>',
            '<span data-lang="en">Support</span>',
        )
    )
    assert [
        base_template.index(f'data-testid="{testid}"')
        for testid in (
            "nav-loops-link",
            "nav-tutorial-link",
            "nav-compose-link",
            "nav-tools-link",
            "nav-resource-toggle",
            "nav-support-link",
        )
    ] == sorted(
        base_template.index(f'data-testid="{testid}"')
        for testid in (
            "nav-loops-link",
            "nav-tutorial-link",
            "nav-compose-link",
            "nav-tools-link",
            "nav-resource-toggle",
            "nav-support-link",
        )
    )
    assert 'href="{{ nav_bundles_href }}"\n            id="nav-resource-toggle"' in base_template
    assert all(
        fragment in index_template
        for fragment in (
            'href="{{ nav_tools_href }}" data-testid="home-agent-entry-link" data-workdir-context-link="workdir"',
            'data-testid="home-compose-loop-link" data-workdir-context-link="alignment_workdir"',
            'href="{{ nav_tutorial_fit_href }}" data-testid="home-fit-guide-link" data-workdir-context-link="workdir"',
            'class="primary-button" href="{{ nav_tutorial_fit_href }}" data-testid="home-fit-guide-link" data-workdir-context-link="workdir"',
            'class="ghost-button" href="{{ nav_tools_href }}" data-testid="home-agent-entry-link" data-workdir-context-link="workdir"',
            'href="{{ nav_compose_href }}" data-testid="loops-empty-create-choice-link" data-workdir-context-link="workdir"',
            'href="{{ nav_tools_href }}" data-testid="loops-empty-agent-setup-link" data-workdir-context-link="workdir"',
            'href="{{ nav_bundle_import_href }}" data-testid="loops-empty-import-plan-link" data-workdir-context-link="workdir"',
            "Fit Guide/Web Choices",
            "Import Plan File",
            "适用性判断/Web 选择",
            "导入 Plan File",
            'data-testid="home-returning-actions"',
            "{% set has_attention_work = active_loops|length > 0 %}",
            "{% set has_recent_activity = recent_loops|length > 0 %}",
            "{% set has_saved_loops = loops|length > 0 %}",
            "{% set primary_attention_item = active_loops[0] if has_attention_work else none %}",
            "{% set primary_recent_item = recent_loops[0] if has_recent_activity else none %}",
            "{% set primary_attention_href = workdir_context_href(primary_attention_item.card_href, workdir_context) if primary_attention_item else '#activity' %}",
            "{% set primary_recent_href = workdir_context_href(primary_recent_item.card_href, workdir_context) if primary_recent_item else '#activity' %}",
            "{% set single_saved_loop_available = loops|length == 1 %}",
            "{% set primary_saved_loop_item = loops[0] if single_saved_loop_available else none %}",
            "{% set primary_saved_loop_href = workdir_context_href(primary_saved_loop_item.detail_href|default(primary_saved_loop_item.card_href, true), workdir_context) if primary_saved_loop_item else '#saved-loops' %}",
            "{% set has_hidden_home_work = workdir_context and not demo_playground_active and (hidden_activity_count > 0 or hidden_loop_count > 0) %}",
            "{% set is_true_first_run = not has_visible_home_work and not has_hidden_home_work %}",
            "{% if has_attention_work %}",
            'href="{{ primary_attention_href }}" data-testid="home-returning-attention-link" data-workdir-context-link="workdir"',
            'href="{{ primary_recent_href }}" data-testid="home-returning-recent-link" data-workdir-context-link="workdir"',
            "Review Recent Activity",
            'href="{{ primary_saved_loop_href }}" data-testid="home-returning-saved-link"',
            '{% if single_saved_loop_available %}data-workdir-context-link="workdir" {% endif %}data-home-saved-action-kind=',
            'href="{{ home_all_href }}" data-testid="home-empty-show-all-link"',
            'href="{{ home_all_href }}" data-testid="home-activity-show-all-link"',
            'href="{{ home_all_href }}" data-testid="loops-empty-show-all-link"',
            "data-home-saved-action-kind=",
            "Open saved Loop",
            "Review Saved Loops",
            "No Loops for this target project",
            "View Work in Other Projects",
            "View All Loops",
            "Recent activity",
            'href="{{ nav_compose_href }}" data-testid="home-returning-compose-link" data-workdir-context-link="workdir"',
            'href="{{ nav_tutorial_fit_href }}" data-testid="home-returning-fit-link" data-workdir-context-link="workdir"',
            "One task goal is enough to start a Web conversation",
            "current work: Web conversations still composing, READY Plan File candidates, same-Agent handoffs",
            "READY 候选、运行推进",
            "等待同一 Agent",
            "waiting on same-Agent work",
            "Start New Loop",
            "开始新的 Loop",
            "Same-Agent Setup",
            "同一 Agent 设置",
            "Open Fit Guide/Web choices, then choose Web conversation, Same-Agent Setup, or the expert import/manual path",
            "进入适用性判断/Web 选择，再选择 Web 对话、同一 Agent 设置或专家导入/手动编排",
            "Existing judgment can travel with the first message, but it is not required to begin",
            "View All Creation Paths",
        )
    )
    assert all(
        fragment in tools_template
        for fragment in (
            'action="{{ support_target_form_action }}"',
            "{% if support_return_to %}",
            'href="{{ support_return_to }}" data-testid="support-return-link" data-workdir-context-link="workdir"',
            'href="{{ support_guidance.links.support }}"\n        target="_blank"\n        rel="noreferrer"\n        data-testid="support-policy-link"',
            'href="{{ support_guidance.links.security_policy }}"\n        target="_blank"\n        rel="noreferrer"\n        data-testid="support-security-link"',
        )
    )
    assert all(
        fragment in index_template
        for fragment in (
            "{% set loop_item_card_href = workdir_context_href(loop_item.card_href, workdir_context) %}",
            "{% set loop_item_detail_href = workdir_context_href(loop_item.detail_href|default('/loops/' ~ loop_item.id, true), workdir_context) %}",
            "{% set loop_item_start_run_action = workdir_context_href(loop_item.start_run_action|default('/loops/' ~ loop_item.id ~ '/runs', true), workdir_context) %}",
            "{% set loop_item_agent_entry_start = loop_item.agent_entry_start|default({}) %}",
            "{% set loop_item_can_start_from_card = not loop_item.latest_run_id and loop_item.can_start_web_run|default(false) %}",
            'href="{{ loop_item_card_href }}" data-testid="home-active-loop"',
            'href="{{ loop_item_card_href }}" data-testid="home-recent-loop" data-workdir-context-link="workdir"',
            'data-open-card="{{ loop_item_card_href }}"',
            'data-workdir-context-open-card="workdir"',
            'data-testid="loop-card-agent-run-guide-link"',
            'data-testid="loop-card-start-run-form" data-workdir-context-form="workdir"',
            'data-testid="loop-card-start-run-button"',
            'href="{{ loop_item_detail_href }}" data-workdir-context-link="workdir"',
            'action="{{ loop_item_start_run_action }}"',
            'href="{{ loop_item_card_href }}" data-workdir-context-link="workdir"',
        )
    )
    assert all(
        fragment not in index_template
        for fragment in (
            "Agent entry or the Web creation path",
            "from an Agent entry, Web conversation",
            "Web conversation, an Agent session",
            "composing, Agent handoffs",
            "waiting on Agent work",
            "从 Agent 入口还是 Web 创建路径开始",
            "从 Agent 入口、Web 对话",
            "从 Web 对话、Agent 会话",
            "正在编排、等待 Agent",
            "Install Agent entry",
            "安装 Agent 入口",
            "Start with Loops waiting",
            "Start Another Loop",
        )
    )
    assert [index_template.index(f'data-testid="{testid}"') for testid in ("home-fit-guide-link", "home-compose-loop-link", "home-agent-entry-link")] == sorted(
        index_template.index(f'data-testid="{testid}"') for testid in ("home-fit-guide-link", "home-compose-loop-link", "home-agent-entry-link")
    )
    assert all(
        fragment in tools_template
        for fragment in (
            "Run locally; paste generated outputs only",
            "Run ready commands; preview preferred bundle/fallback report commands only",
            "Run preferred bundle/fallback report/identity commands; setup target not ready",
            "在本地运行；只粘贴生成的输出",
            "运行已就绪命令；优先支持包/兜底报告命令仅预览",
            "运行优先支持包/兜底报告/身份命令；设置目标未就绪",
            "Preferred public issue support bundle command",
            "Preferred public issue support bundle command shape",
            "优先公开 issue 支持包命令",
            "优先公开 issue 支持包命令形状",
            "Fallback redacted readiness report command",
            "Fallback redacted readiness report command shape",
            "兜底脱敏就绪报告命令",
            "兜底脱敏就绪报告命令形状",
            "Compact version/source identity command",
            "紧凑版本/源码身份命令",
            "Structured version/source identity command",
            "结构化版本/源码身份命令",
            "Copy preferred bundle command",
            "Choose target before copying preferred bundle command",
            "Copy fallback report command",
            "Choose target before copying fallback report command",
            "Copy version/source command",
            "Copy structured version command",
            'data-testid="tools-support-copy-public-issue-bundle-command"',
            'data-testid="tools-support-copy-version-json"',
            "support_guidance.commands.public_issue_bundle",
            "support_guidance.commands.version_json",
        )
    )
    assert all(
        fragment in tools_template
        for fragment in (
            'href="{{ nav_tutorial_fit_href }}"',
            'data-testid="tools-fit-guide-link"',
            'data-agent-adapter-workdir-context-link="1"',
            "Loopora fit reason, task goal, fake-done risk, required evidence, judgment tradeoffs, and optional direct-path context",
            "Same-Agent Setup",
            "Confirm the Codex, Claude Code, or OpenCode host used for this project",
            "同一 Agent 设置",
            "设置目标与当前宿主",
            "Setup target and current host",
            "pages/tools.css",
            'data-testid="tools-page-intro"',
            'class="tools-setup-context-grid"',
            'data-testid="agent-adapter-target"',
            'data-testid="agent-host-selector"',
            'data-testid="tools-route-actions"',
            'href="{{ nav_compose_href }}" data-testid="tools-create-choice-link"',
            'data-testid="tools-hero-fit-guide-link"',
            'href="#tools-support-panel" data-testid="tools-hero-support-link"',
            'id="agent-adapters-panel" data-testid="agent-adapters-panel"',
            'id="tools-support-panel"',
            'data-testid="tools-support-panel"',
            "data-support-next-action-kinds=",
            "data-support-ready-next-action-kinds=",
            "data-support-blocked-next-action-kinds=",
            "data-support-target-project-status=",
            "data-support-target-project-setup-ready=",
            "data-support-target-project-report-only=",
            "support_guidance.support_summary.ready_next_action_kinds|join(',')",
            "support_guidance.support_summary.blocked_next_action_kinds|join(',')",
            'data-testid="tools-support-commands"',
            'data-testid="tools-support-actions"',
            'data-support-copy-public-report="true" {% if support_guidance.target_project_required %}disabled aria-disabled="true"{% endif %}',
            'data-testid="tools-support-copy-public-report"',
            "Choose target before copying public issue bundle",
            "Copy public issue bundle",
            'data-support-command-copy="{{ support_guidance.commands.public_issue_bundle }}"',
            'data-support-command-copy="{{ support_guidance.commands.public_doctor }}"',
            'data-support-command-requires-target="{{',
            "support_guidance.command_fields_executable",
            'disabled aria-disabled="true"',
            'data-testid="tools-support-target-required"',
            'data-testid="tools-support-target-state"',
            "data-support-target-required-note",
            "data-support-target-state-note",
            "support_target_status_en",
            "support_target_status_zh",
            'data-support-next-action-kind="choose_workdir_for_public_report"',
            "choose and refresh a target project before copying the public issue bundle or requested redacted report command",
            "先选择并刷新目标项目，再复制公开 issue 支持包或按需复制脱敏报告命令",
            'data-testid="tools-support-copy-public-issue-bundle-command"',
            'data-testid="tools-support-copy-public-report-command"',
            'data-support-next-action-kind="run_public_issue_bundle"',
            'data-support-next-action-kind="run_public_doctor_report"',
            'data-support-next-action-kind="run_version_identity"',
            'data-testid="tools-support-copy-version-json"',
            'data-testid="tools-support-status"',
            "data-support-public-report-manual-copy",
            'data-testid="tools-support-public-report-manual-copy"',
            "Support and safe reporting",
            "安全支持与公开报告",
            "rendering this panel does not run diagnostics",
            "页面渲染这个面板时不会运行诊断",
            "support_posting_guidance_en",
            "support_posting_guidance_zh",
            'data-testid="tools-support-public-materials"',
            "Paste publicly only",
            "公开 issue 只粘贴",
            "support_public_paste_en",
            "support_public_paste_zh",
            'data-testid="tools-support-local-only"',
            "Keep local only",
            "仅限本地使用",
            "support_local_only_en",
            "support_local_only_zh",
            "{% for action in support_guidance.next_actions %}",
            'action.route_kind == "bug_report"',
            'action.route_kind == "feature_request"',
            'action.route_kind == "usage_or_setup"',
            'action.route_kind == "security"',
            'data-support-route-kind="{{ action.route_kind }}"',
            'href="{{ action.url }}" target="_blank" rel="noreferrer"',
            'href="{{ action.policy_url }}" target="_blank" rel="noreferrer"',
            'href="{{ action.private_report_url }}" target="_blank" rel="noreferrer"',
            'data-support-public-fallback="{{ action.public_fallback }}"',
            "otherwise public issues may only ask for a private channel",
            "否则公开 issue 只能请求私密渠道",
            "support_guidance.commands.public_issue_bundle",
            "support_guidance.commands.public_doctor",
            "support_guidance.commands.version_json",
            "support_redaction_en",
        )
    )
    assert tools_template.index('data-testid="agent-adapter-target"') < tools_template.index('data-testid="agent-host-selector"') < tools_template.index('data-testid="agent-readiness-summary"') < tools_template.index('data-testid="tools-route-actions"')
    assert all(fragment not in tools_template for fragment in ('data-testid="tools-route-brief"', 'data-testid="tools-same-agent-continue-link"', 'data-testid="agent-adapter-recent-workdirs"'))
    assert all(
        fragment in tutorial_template
        for fragment in (
            'data-testid="tutorial-page-intro"',
            'class="ghost-button" href="#tutorial-guide-panel" data-testid="tutorial-boundary-link"',
            "pages/tutorial.css",
            'data-testid="tutorial-fit-signal-disclosure"',
            'data-testid="tutorial-flow-comparison-disclosure"',
            'class="panel tutorial-disclosure" data-testid="tutorial-workflow-scenarios-panel"',
            'href="{{ nav_tools_href }}"\n                data-testid="tutorial-fit-task-use-tools"\n                data-workdir-context-link="workdir"',
            'href="{{ nav_web_compose_href }}"\n                data-testid="tutorial-fit-task-use-web"\n                data-workdir-context-link="workdir"',
            'class="primary-button" href="{{ nav_compose_href }}" data-testid="tutorial-web-compose-link" data-workdir-context-link="workdir" data-tutorial-fit-route="choice" data-tutorial-fit-empty-allowed="true"',
            'class="ghost-button" href="{{ nav_tools_href }}" data-testid="tutorial-agent-entry-link" data-workdir-context-link="workdir" data-tutorial-fit-route="setup" data-tutorial-fit-empty-allowed="true"',
            'class="ghost-button" href="{{ nav_manual_loop_href }}" data-testid="tutorial-manual-compose-link" data-workdir-context-link="workdir" data-tutorial-fit-route="expert" data-tutorial-fit-empty-allowed="true"',
            'class="ghost-button" href="{{ nav_orchestrations_href }}" data-testid="tutorial-workflow-examples-link" data-workdir-context-link="workdir"',
            "Loopora Fit Guide",
            "Loopora 适用性判断",
            "Same-Agent Setup",
            "install the same-Agent project entry",
            "安装同一 Agent 项目入口",
            "同一 Agent 设置",
            'data-fit-field-kind="{{ \'task\' if field.id == \'task\' else \'direct-check\' if field.id == \'direct_path_check\' else \'loop-review\' }}"',
            'data-testid="tutorial-fit-detail-fields"',
        )
    )
    assert all(
        fragment in tutorial_script
        for fragment in (
            "function canonicalizeFitGuideAlias()",
            'window.location?.pathname !== "/tutorial"',
            'const nextUrl = `/fit-guide${window.location.search || ""}${window.location.hash || ""}`',
            'window.history.replaceState(window.history.state, "", nextUrl)',
            "canonicalizeFitGuideAlias();",
        )
    )
    assert all(fragment not in tutorial_template for fragment in ("Install Agent entry", "安装 Agent 入口", "Use in Tools", "带到 Tools"))
    tutorial_first_use_order = (
        "tutorial-page-intro",
        "tutorial-decision-tree-panel",
        "tutorial-fit-task-review",
        "tutorial-fit-signal-disclosure",
        "tutorial-flow-comparison-disclosure",
        "tutorial-guide-panel",
        "tutorial-workflow-scenarios-panel",
        "tutorial-actions-panel",
    )
    assert [tutorial_template.index(f'data-testid="{testid}"') for testid in tutorial_first_use_order] == sorted(
        tutorial_template.index(f'data-testid="{testid}"') for testid in tutorial_first_use_order
    )
    fit_route_order = ("tutorial-fit-task-use-web", "tutorial-fit-task-use-tools", "tutorial-web-compose-link", "tutorial-agent-entry-link")
    assert [tutorial_template.index(f'data-testid="{testid}"') for testid in fit_route_order] == sorted(
        tutorial_template.index(f'data-testid="{testid}"') for testid in fit_route_order
    )
    assert all(
        fragment in bundles_template
        for fragment in (
            'href="#bundle-import-panel" data-testid="bundles-import-plan-link"',
            'href="{{ nav_bundle_import_href }}" data-testid="bundles-create-loop-import-link" data-workdir-context-link="workdir"',
            'href="{{ nav_compose_href }}" data-testid="bundles-compose-loop-link" data-workdir-context-link="workdir"',
            'data-testid="bundle-import-form"',
            'data-workdir-context-form="workdir"',
            'data-testid="bundle-derive-form"',
            'href="{{ bundles_all_href }}" data-testid="bundle-derive-show-all-link"',
            'href="{{ nav_compose_href }}" data-testid="bundle-derive-create-loop-link" data-workdir-context-link="workdir"',
            'class="primary-button" href="#bundle-import-panel" data-testid="bundles-empty-import-plan-link"',
            'href="{{ bundles_all_href }}" data-testid="bundles-empty-show-all-link"',
            'href="{{ nav_compose_href }}" data-testid="bundles-empty-create-choice-link" data-workdir-context-link="workdir"',
            'href="{{ nav_tools_href }}" data-testid="bundles-empty-agent-setup-link" data-workdir-context-link="workdir"',
            "Fit Guide/Web Choices",
            "Same-Agent Setup",
            "适用性判断/Web 选择",
            "同一 Agent 设置",
            "Open same-Agent run guide",
            "打开同一 Agent 运行指引",
        )
    )
    assert all(
        fragment in bundles_template
        for fragment in (
            "{% set bundle_detail_href = workdir_context_href(bundle.detail_href|default('/bundles/' ~ bundle.id, true), workdir_context) %}",
            "{% set bundle_export_href = workdir_context_href(bundle.export_href|default('/bundles/' ~ bundle.id ~ '/export', true), workdir_context) %}",
            'data-open-card="{{ bundle_detail_href }}"',
            'data-workdir-context-open-card="workdir"',
            'href="{{ bundle_detail_href }}" tabindex="-1" aria-hidden="true" data-workdir-context-link="workdir"',
            "{% set bundle_loop_href = workdir_context_href(bundle.loop_detail_href|default('/loops/' ~ bundle.loop_id, true), workdir_context) %}",
            'href="{{ bundle_loop_href }}" data-testid="bundle-list-open-agent-run-guide-{{ bundle.id }}" data-workdir-context-link="workdir"',
            "{% set bundle_start_run_action = workdir_context_href(bundle.start_run_action|default('/bundles/' ~ bundle.id ~ '/runs', true), workdir_context) %}",
            'action="{{ bundle_start_run_action }}" class="inline-form" data-testid="bundle-list-start-run-form-{{ bundle.id }}" data-workdir-context-form="workdir"',
            'href="{{ bundle_detail_href }}" data-workdir-context-link="workdir"',
            'href="{{ bundle_export_href }}" data-workdir-context-link="workdir"',
        )
    )
    assert all(
        fragment in bundle_route_source
        for fragment in (
            "from loopora.workdir_inputs import same_workdir_identity",
            "all_loops = self.svc().list_loops()",
            "loops = _bundle_derive_loops(all_loops, workdir_context=workdir_context)",
            'all_bundles = self._bundle_list_items(workdir_context="")',
            "bundles = _bundle_list_items_for_workdir(all_bundles, workdir_context=workdir_context)",
            '"hidden_bundle_count": max(0, len(all_bundles) - len(bundles))',
            '"hidden_loop_count": max(0, len(all_loops) - len(loops))',
            '"bundles_all_href": request_all_projects_scope_href(request, "/bundles")',
            'def _bundle_list_items(self, *, workdir_context: str = "")',
            "if workdir_context and not same_workdir_identity(bundle_workdir, workdir_context):",
            "def _bundle_list_items_for_workdir(items: list[dict], *, workdir_context: str) -> list[dict]:",
            'item["export_href"] = with_query_params(',
            "def _bundle_derive_loops",
            'return [loop for loop in loops if same_workdir_identity(loop.get("workdir"), workdir_context)]',
        )
    )
    assert 'request_workdir_context_href(request, f"/bundles/derive/export?{urlencode(query_params)}")' in bundle_derive_form_route_source
    assert all(fragment not in bundles_template for fragment in ("Open Agent run guide", "打开 Agent 运行指引"))


def test_loop_create_choice_surfaces_agent_web_expert_and_existing_work_entries() -> None:
    base_template = (ROOT / "src" / "loopora" / "templates" / "base.html").read_text(encoding="utf-8")
    index_template = (ROOT / "src" / "loopora" / "templates" / "index.html").read_text(encoding="utf-8")
    tools_template = (
        (ROOT / "src" / "loopora" / "templates" / "tools.html").read_text(encoding="utf-8")
        + (ROOT / "src" / "loopora" / "templates" / "partials" / "support_panel.html").read_text(encoding="utf-8")
        + (ROOT / "src" / "loopora" / "templates" / "support.html").read_text(encoding="utf-8")
    )
    tutorial_template = (ROOT / "src" / "loopora" / "templates" / "tutorial.html").read_text(encoding="utf-8")
    bundles_template = (ROOT / "src" / "loopora" / "templates" / "bundles.html").read_text(encoding="utf-8")
    template = (ROOT / "src" / "loopora" / "templates" / "new_loop.html").read_text(encoding="utf-8")
    create_choice_script = (ROOT / "src" / "loopora" / "static" / "pages" / "create_choice.js").read_text(encoding="utf-8") + (
        ROOT / "src" / "loopora" / "static" / "pages" / "new_loop.js"
    ).read_text(encoding="utf-8")
    web_source = (ROOT / "src" / "loopora" / "web.py").read_text(encoding="utf-8")
    home_create_route_source = (ROOT / "src" / "loopora" / "web_home_create_page_routes.py").read_text(encoding="utf-8")
    support_route_source = (ROOT / "src" / "loopora" / "web_support_page_routes.py").read_text(encoding="utf-8")
    route_source = (ROOT / "src" / "loopora" / "web_route_context_loop_pages.py").read_text(encoding="utf-8")
    create_context_source = (ROOT / "src" / "loopora" / "web_loop_create_context.py").read_text(encoding="utf-8")
    app_script = (ROOT / "src" / "loopora" / "static" / "app.js").read_text(encoding="utf-8")
    app_styles = (ROOT / "src" / "loopora" / "static" / "app.css").read_text(encoding="utf-8")
    styles = (ROOT / "src" / "loopora" / "static" / "pages" / "alignment.css").read_text(encoding="utf-8")

    web_index, agent_index, expert_index, existing_index = (
        template.index(f'data-testid="{testid}"')
        for testid in ("loop-create-bundle-choice", "loop-create-agent-choice", "loop-create-manual-choice", "loop-create-existing-choice")
    )
    assert web_index < agent_index < expert_index < existing_index
    assert (
        template.index('data-testid="alignment-path-chat"')
        < template.index('data-testid="alignment-path-agent-setup"')
        < template.index('data-testid="alignment-path-import"')
        < template.index('data-testid="alignment-path-manual"')
        < template.index('data-compose-action-kind="new_web_conversation"')
    )
    _assert_peer_start_navigation_links(
        base_template=base_template,
        index_template=index_template,
        tools_template=tools_template,
        tutorial_template=tutorial_template,
        bundles_template=bundles_template,
    )
    assert all(
        fragment in template
        for fragment in (
            'data-testid="loop-create-agent-link"',
            "data-create-choice-setup-start",
            'data-testid="loop-create-bundle-link"',
            "data-create-choice-expert-start",
            'data-testid="loop-create-import-link"',
            'data-testid="alignment-direct-path-check-input"',
            'data-testid="loop-create-manual-link"',
            'data-testid="loop-create-existing-attention-link"',
            'data-testid="loop-create-existing-saved-link"',
            "data-current-workdir=\"{{ workdir_context or '' }}\"",
            'data-testid="loop-create-tutorial-handoff-use-source"',
            'data-testid="loop-create-tutorial-handoff-review"',
            'data-testid="loop-create-tutorial-handoff-review-count"',
            'data-create-choice-handoff-web data-create-choice-web-start data-testid="loop-create-tutorial-handoff-web-link" data-workdir-context-link="alignment_workdir"',
            "data-create-choice-handoff-copy-direct",
            "one task goal is enough to begin",
            "Outside an Agent session",
            "Already working in Codex, Claude Code, or OpenCode",
            "Use Same-Agent Setup",
            "Import Plan File or compose manually",
            "不在 Agent 会话里",
            "已经在 Codex、Claude Code 或 OpenCode",
            "走同一 Agent 设置",
            "导入 Plan File 或手动编排",
            "Create in the same Agent",
            "用同一 Agent 创建",
            "Same-Agent Setup",
            "same-Agent project entry",
            "同一 Agent 设置",
            "同一 Agent 项目入口",
            "your current Agent remains the executor",
            "执行主体仍是你的当前 Agent",
            "confirm doctor readiness",
            "READY preview matches the task judgment",
            "确认 doctor 就绪",
            "READY 预览匹配任务判断",
            "Leave blank for the selected tool default model",
            "留空使用所选工具的默认模型",
            "codex | claude | opencode | custom",
            'class="panel create-choice-card create-choice-card--primary"',
            'class="panel create-choice-card create-choice-card--agent"',
            "create-choice-card--existing{% if not existing_work_available %} is-empty{% endif %}",
            'href="{{ nav_tutorial_fit_href }}" data-testid="loop-create-fit-guide-link" data-workdir-context-link="workdir"',
            'class="primary-button create-choice-card-route-action" href="{{ create_choice_links.bundle }}" data-create-choice-web-start data-testid="loop-create-bundle-link" data-workdir-context-link="alignment_workdir"',
            'class="secondary-button create-choice-card-route-action" href="{{ create_choice_links.agent }}" data-create-choice-setup-start data-testid="loop-create-agent-link" data-workdir-context-link="workdir"',
            'href="{{ create_choice_links.import }}" data-create-choice-expert-start data-testid="loop-create-import-link" data-workdir-context-link="workdir"',
            'href="{{ create_choice_links.manual }}" data-create-choice-expert-start data-testid="loop-create-manual-link" data-workdir-context-link="workdir"',
            'href="{{ existing_primary_activity_href if existing_primary_activity_available else create_choice_links.existing_attention }}" data-existing-action-kind="{{ existing_primary_activity_display_action_kind }}" data-testid="loop-create-existing-attention-link" data-workdir-context-link="workdir"',
            'href="{{ existing_saved_review_href }}" data-existing-action-kind="{{ existing_saved_action_kind }}" data-testid="loop-create-existing-saved-link" data-workdir-context-link="workdir"',
            "{{ 'ghost-button' if existing_activity_available else 'secondary-button' }}",
            "data-existing-work-state=\"{{ 'available' if existing_work_available else 'empty' }}\"",
            "{% set existing_hidden_work_available = create_choice_existing_work.has_hidden_work|default(false) %}",
            "{% set existing_activity_available = create_choice_existing_work.has_activity|default(false) %}",
            "{% set existing_saved_available = create_choice_existing_work.has_saved_loops|default(false) %}",
            "{% set existing_attention_available = create_choice_existing_work.active_attention_count|default(0) > 0 %}",
            '{% set existing_primary_activity_action_kind = create_choice_existing_work.primary_activity_action_kind|default("") %}',
            '{% set existing_primary_activity_action_zh = create_choice_existing_work.primary_activity_action_zh|default("") %}',
            '{% set existing_primary_activity_action_en = create_choice_existing_work.primary_activity_action_en|default("") %}',
            "{% set existing_primary_activity_available = existing_primary_activity_href %}",
            '{% set existing_primary_alignment_available = create_choice_existing_work.primary_activity_source_kind|default("") == "alignment_session"',
            '{% set existing_primary_alignment_ready = existing_primary_alignment_available and existing_primary_activity_action_kind == "review_alignment_bundle" %}',
            "{% set existing_primary_activity_display_action_kind = existing_primary_activity_action_kind if existing_primary_activity_available and existing_primary_activity_action_kind else",
            "{% set existing_recent_available = create_choice_existing_work.recent_loop_count|default(0) > 0 %}",
            "{% set existing_saved_loop_count = create_choice_existing_work.loop_count|default(0) %}",
            '{% set existing_primary_saved_loop_href = create_choice_existing_work.primary_saved_loop_href|default("") %}',
            "{% set existing_single_saved_loop_available = existing_saved_loop_count == 1 and existing_primary_saved_loop_href %}",
            "{% set existing_saved_review_href = existing_primary_saved_loop_href if existing_single_saved_loop_available else create_choice_links.existing_saved %}",
            "{% set existing_saved_action_kind = 'open_saved_loop' if existing_single_saved_loop_available else 'review_saved_loops' %}",
            'data-existing-action-kind="{{ existing_primary_activity_display_action_kind }}"',
            "Review and create Loop",
            "{{ existing_primary_activity_action_en }}",
            "Continue Web Conversation",
            "Open saved Loop",
            "Review Saved Loops",
            "{% if existing_primary_alignment_ready %}",
            "{% elif existing_primary_activity_action_zh or existing_primary_activity_action_en %}",
            "{% elif existing_attention_available %}",
            "{% elif existing_activity_available %}",
            "{% if existing_single_saved_loop_available %}",
            "{% if existing_saved_available %}",
            "{% if existing_hidden_work_available %}",
            'href="{{ create_choice_existing_work.all_work_href|default(\'/\') }}" data-existing-action-kind="view_all_work" data-testid="loop-create-existing-show-all-link"',
            'data-testid="loop-create-existing-empty-state"',
            "open the most relevant continuation target first",
            "other target projects already have work",
        )
    )
    assert all(
        template.index(f'data-testid="{link_testid}"') < template.index(body)
        for link_testid, body in (
            ("loop-create-bundle-link", "When you are not inside an Agent session"),
            ("loop-create-agent-link", "When you are already working inside Codex"),
            ("loop-create-import-link", "Use the full expert path"),
            ("loop-create-existing-empty-state", "After a Web conversation starts"),
        )
    )
    assert all(
        fragment in template
        for fragment in ("run `/loopora-run` only after the READY preview matches the task judgment", "READY 预览匹配任务判断后才运行 `/loopora-run`")
    )
    assert all(
        fragment not in template
        for fragment in (
            "Agent first",
            "Agent 优先",
            "Check Agent Entry",
            "检查 Agent 入口",
            "Create from your current Agent",
            "Use Agent Runner",
            "Codex CLI default",
        )
    )
    assert '"workdir_context": workdir_context' in web_source
    assert '"nav_tools_href": scope_href("/same-agent")' in web_source
    assert all(key in web_source for key in ('"nav_tutorial_href":', '"nav_tutorial_fit_href":'))
    assert '"nav_support_href": support_href' in web_source
    assert all(
        fragment in home_create_route_source
        for fragment in (
            '"all_loop_count": len(all_loop_sections["loops"])',
            '"hidden_loop_count": max(0, len(all_loop_sections["loops"]) - len(loop_sections["loops"]))',
            '"all_activity_count": all_activity_count',
            '"hidden_activity_count": max(0, all_activity_count - scoped_activity_count)',
            '"home_all_href": request_all_projects_scope_href(request, "/")',
        )
    )
    assert all(
        fragment in support_route_source
        for fragment in (
            "return_to = _support_target_return_to(request, workdir_context=target_workdir)",
            "url=_support_target_redirect_url(",
            "def _support_target_return_to",
            'safe_local_return_path(request.query_params.get("return_to", ""))',
            "workdir_context_return_to(return_to, workdir_context)",
            "def _support_target_redirect_url",
        )
    )
    assert 'data-testid="global-workdir-context" {% if not workdir_context %}hidden{% endif %}' in base_template
    assert all(
        fragment in route_source
        for fragment in (
            '"workdir_context": workdir_context',
            "and not workdir_context",
            "create_context = loop_create_page_context(request, service, page_mode=state.page_mode)",
            '"create_choice_links": create_context["create_choice_links"]',
            '"create_choice_existing_work": create_context["create_choice_existing_work"]',
        )
    )
    assert all(
        fragment in create_context_source
        for fragment in (
            "primary_activity = active_items[0] if active_items else {}",
            "if not primary_activity and recent_loops:",
            "primary_activity = recent_loops[0]",
            "primary_saved_loop = loops[0] if len(loops) == 1 else {}",
            '"primary_activity_href": _create_choice_primary_activity_href(',
            '"primary_saved_loop_href": _create_choice_primary_saved_loop_href(',
            '"hidden_loop_count": hidden_loop_count',
            '"hidden_activity_count": hidden_activity_count',
            '"has_hidden_work": bool(workdir_context and (hidden_activity_count or hidden_loop_count))',
            '"all_work_href": all_work_href',
            "all_existing_work_sections = (",
            "all_sections=all_existing_work_sections",
            'all_work_href=request_all_projects_scope_href(request, "/")',
            "def _create_choice_primary_activity_href",
            "def _create_choice_primary_saved_loop_href",
            'target = str(primary_saved_loop.get("detail_href") or primary_saved_loop.get("card_href") or "").strip()',
            "return workdir_context_href(target, workdir_context)",
            '"agent": request_project_scope_href(request, "/same-agent", workdir_context="")',
            '"agent": with_query_params("/same-agent", workdir=workdir)',
        )
    )
    assert all(
        fragment in template
        for fragment in (
            'href="{{ create_choice_links.bundle }}"',
            "create_choice_links.existing_attention",
            'href="{{ existing_saved_review_href }}" data-existing-action-kind="{{ existing_saved_action_kind }}"',
            'href="{{ create_choice_links.import }}"',
            'href="{{ create_choice_links.manual }}"',
            'href="{{ composer_roles_href }}" data-testid="manual-roles-link" data-workdir-context-link="workdir"',
            'href="{{ composer_orchestrations_href }}" data-testid="manual-orchestrations-link" data-workdir-context-link="workdir"',
            'href="{{ nav_tutorial_href }}" data-testid="manual-fit-guide-link" data-workdir-context-link="workdir"',
            'href="{{ nav_home_href }}" data-testid="manual-cancel-link" data-workdir-context-link="workdir"',
            "const manualLoopFormHref = {{ create_choice_links.manual|tojson }};",
            "const bundleImportHref = {{ create_choice_links.import|tojson }};",
            "window.location.replace(manualLoopFormHref)",
            "window.location.replace(bundleImportHref)",
            'data-history-empty-start-href="{{ create_choice_links.bundle }}"',
            'data-workdir-context-dataset-urls="historyEmptyStartHref:alignment_workdir"',
            'data-compose-import-href="{{ create_choice_links.import }}"',
            'data-compose-manual-href="{{ create_choice_links.manual }}"',
            'data-tutorial-fit-href="{{ nav_tutorial_fit_href }}"',
            'data-workdir-context-dataset-urls="composeImportHref:workdir composeManualHref:workdir tutorialFitHref:workdir"',
            'data-compose-path-kind="web_conversation"',
            'href="{{ create_choice_links.agent }}"',
            'data-compose-path-kind="same_agent_setup"',
            'data-testid="alignment-path-agent-setup"',
            'data-compose-path-kind="plan_file_import"',
            'data-compose-path-kind="manual_expert"',
            'data-compose-action-kind="new_web_conversation"',
            'href="{{ create_choice_links.bundle }}" data-testid="manual-spec-web-guidance-link" data-workdir-context-link="alignment_workdir"',
            "If the Loop contract is already clear and you know which built-in or custom flow to use",
            "Start with a built-in flow by default",
            "role and flow customization is for reusable team assets",
            "go back to Web conversation and clarify the task goal",
            "Use flow examples only as expert-path assistance",
        )
    )
    assert all(
        fragment in create_choice_script
        for fragment in (
            "function currentWorkdirContext()",
            "function handoffMatchesTarget(handoff)",
            "const targetWorkdir = currentWorkdirContext()",
            "allowEmptyLeft: !targetWorkdir",
            'const toolsBaseHref = toolsLink?.getAttribute("href") || "/same-agent";',
            "function activeLinkHref(link)",
            "function rememberWebStartBaseHrefs()",
            "const hasWorkdirMismatch = Boolean(rawHandoff && !handoffMatchesTarget(rawHandoff));",
            "const directPathBlocksCurrentTarget = Boolean(rawHandoff?.prefersDirect && !hasWorkdirMismatch);",
            "rawHandoff.readyForWeb && !hasWorkdirMismatch",
            "webStartBlocked: directPathBlocksCurrentTarget",
            'bridge.classList.toggle("is-warning", hasWorkdirMismatch)',
            'finishLink?.classList.remove("is-primary-recovery")',
            "window.LooporaUI.tutorialFitSetupCommandState",
            "setupGateReady",
            "setupGateBlockers",
            "Choose a target project before copying same-Agent setup commands",
            "sourceWorkdirCreateChoiceHref",
            "use Same-Agent Setup",
            "inputLabel(inputId, handoff.prefersDirect)",
            "window.LooporaUI.tutorialFitPrefersDirectPath(payload)",
            "prefer_direct_path",
            "const directDecisionReady = !prefersDirect || Boolean(compactText(inputs.direct_path_check));",
            "Direct-path decision blocks Loopora setup",
            "Direct-path decision belongs to the source project",
            "readyForWeb: !prefersDirect",
            "data-create-choice-handoff-use-source",
            "data-create-choice-handoff-tools",
            "data-create-choice-handoff-copy-direct",
            "data-create-choice-handoff-direct-manual-copy",
            "loop-create-tutorial-handoff-direct-manual-copy-textarea",
            "function renderDirectManualCopy",
            "window.LooporaUI?.renderManualCopy?.(directManualCopy",
            "The browser blocked automatic copy; copy the direct-path command from the page manually.",
            "toolsLink.hidden = handoff.directPathBlocksCurrentTarget",
            "directCopyButton.hidden = !directCommand",
            "window.LooporaUI.writeTextToClipboard(command)",
            'function sourceWorkdirScopedHref(baseHref, sourceWorkdir, {urlParam = "workdir"} = {})',
            "url.searchParams.set(targetParam, workdir)",
            "function setWebStartHrefs",
            'sourceWorkdirScopedHref(baseHref, workdir, {urlParam: "alignment_workdir"})',
            'setWebStartHrefs(handoff.sourceWorkdir && !currentWorkdirContext() ? handoff.sourceWorkdir : "")',
            "finishLink.href = sourceWorkdirScopedHref(finishBaseHref, handoff.sourceWorkdir)",
            "toolsLink.href = sourceWorkdirScopedHref(toolsBaseHref, handoff.sourceWorkdir)",
            'document.querySelectorAll("[data-create-choice-web-start]")',
            'document.querySelectorAll("[data-create-choice-setup-start]")',
            'document.querySelectorAll("[data-create-choice-expert-start]")',
            'document.addEventListener("loopora:workdirchange", () => {',
            "rememberWebStartBaseHrefs();",
            "renderHandoffBridge();",
            "function focusFirstEnabledCreateChoiceRoute()",
            'link.closest("[hidden]")',
            "focusFirstEnabledCreateChoiceRoute();",
            "function setLinkEnabled(link, enabled)",
            "window.LooporaUI.setNavigationControlBlocked(link, !enabled",
            'baseHrefDataset: "enabledHref"',
            'disabledHrefDataset: "disabledHref"',
            "function setSetupLinkEnabled(enabled)",
            "function setExpertLinkEnabled(enabled)",
            "setSetupLinkEnabled(!handoff.directPathBlocksCurrentTarget)",
            "setExpertLinkEnabled(!handoff.directPathBlocksCurrentTarget)",
            "currentHandoff?.directPathBlocksCurrentTarget",
            "setWebLinkEnabled(!handoff.webStartBlocked)",
            "setWebLinkEnabled(true)",
            "setSetupLinkEnabled(true)",
            "setExpertLinkEnabled(true)",
            'markerDataset: "createChoiceRouteBlocked"',
            "function blockedRouteMessage()",
            'window.LooporaUI?.showAppFeedback?.(blockedRouteMessage(), "error")',
            'webStartLinks.forEach((link) => link.addEventListener("click"',
            "currentHandoff?.webStartBlocked",
            "blockRouteStart(event)",
            "event.preventDefault()",
            "No runnable flow is available",
            "return to creation choices",
        )
    )
    assert all(
        fragment in app_script
        for fragment in (
            "function syncWorkdirContextDatasetUrls(element, workdir)",
            'document.querySelectorAll("[data-workdir-context-dataset-urls]")',
            "syncWorkdirDatasetUrl(element, datasetKey, workdir, mode)",
        )
    )
    assert all(
        fragment not in template + create_choice_script
        for fragment in (
            "Tools for the Agent path",
            "Shape role definitions and flow first",
            "Create one from Flows.",
            "Start with a flow example.",
            "先去流程编排看样例",
        )
    )
    assert all(
        fragment in app_styles
        for fragment in (
            ".global-workdir-context",
            ".global-workdir-context[hidden]",
            "overflow-wrap: anywhere",
            ".top-nav-links .nav-dropdown",
            "flex-basis: auto",
            "min-width: max-content",
        )
    )
    assert all(
        fragment in styles
        for fragment in (
            "repeat(4, minmax(0, 1fr))",
            "(min-width: 981px) and (max-width: 1180px)",
            ".create-choice-card--existing",
            ".create-choice-card-route",
            ".create-choice-card-actions",
            ".alignment-starter-grid",
            "display: none",
            ".alignment-starter-disclosure[open] > .alignment-starter-grid",
            "display: grid",
            "pointer-events: none",
        )
    )

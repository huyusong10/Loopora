from __future__ import annotations

import json
import socket
from hashlib import sha256
from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from loopora import cli
from loopora.agent_adapters import install_agent_adapter
from loopora.settings import app_home, save_recent_workdirs
from loopora.web import build_app

from cli_first_use_docs_test_support import result_error_text

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_cli_serve_command_projection_has_dedicated_boundary() -> None:
    commands_source = (REPO_ROOT / "src" / "loopora" / "cli_serve_commands.py").read_text(encoding="utf-8")
    projection_source = (REPO_ROOT / "src" / "loopora" / "cli_serve_command_projection.py").read_text(encoding="utf-8")
    recovery_source = (REPO_ROOT / "src" / "loopora" / "cli_serve_recovery.py").read_text(encoding="utf-8")
    workdir_recovery_source = (REPO_ROOT / "src" / "loopora" / "cli_serve_workdir_recovery.py").read_text(encoding="utf-8")
    guide_source = (REPO_ROOT / "src" / "loopora" / "dev_check_guide_first_use.py").read_text(encoding="utf-8")
    service_boundaries = (REPO_ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")

    assert "from loopora.cli_serve_command_projection import" in commands_source
    assert "from loopora.web import build_app" in commands_source
    assert "uvicorn.run(" in commands_source
    assert "from loopora.cli_serve_command_projection import" in recovery_source
    assert "from loopora.cli_serve_command_projection import serve_retry_command" in workdir_recovery_source
    for marker in (
        "def serve_development_reset_extra_recovery_lines",
        "def copyable_serve_start_command",
        "def serve_start_command",
        "def serve_retry_command",
        "def serve_alternate_port_action",
        "def serve_temporary_app_home_action",
        "def serve_temporary_app_home_command",
    ):
        assert marker in projection_source
        assert marker not in commands_source
    assert "cli_serve_command_projection.py" in guide_source
    assert "cli_serve_command_projection.py" in service_boundaries


def _read_tools_assets() -> tuple[str, str, str, str]:
    return (
        (REPO_ROOT / "src" / "loopora" / "static" / "pages" / "tools.js").read_text(encoding="utf-8"),
        (REPO_ROOT / "src" / "loopora" / "static" / "pages" / "support.js").read_text(encoding="utf-8"),
        (REPO_ROOT / "src" / "loopora" / "static" / "styles" / "legacy.css").read_text(encoding="utf-8"),
        (REPO_ROOT / "src" / "loopora" / "static" / "app.js").read_text(encoding="utf-8"),
    )


def _free_local_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _assert_contains_all(text: str, fragments: tuple[str, ...]) -> None:
    for fragment in fragments:
        assert fragment in text


def _assert_tools_readiness_assets(response_text: str, tools_js: str) -> None:
    assert response_text.index('data-testid="agent-readiness-summary"') < response_text.index('data-testid="agent-adapter-grid"')
    _assert_contains_all(
        tools_js,
        (
            "/api/diagnostics/doctor",
            "function renderAgentReadiness",
            "function renderAgentReadinessPending",
            "function renderAgentAdaptersPending",
            "function refreshAgentAdapterTargetFromInput",
            "clearAgentAdapterHandoff",
            "agentAdapterTargetRefreshTimer",
            'addEventListener("input"',
            "renderAgentReadinessPending(workdir);",
            "renderAgentAdaptersPending();",
            "refreshAgentAdapters({expectedWorkdir}).catch",
            "refreshAgentReadiness({expectedWorkdir}).catch",
            "agentAdapterResponseMatchesExpected(payload, expectedWorkdir)",
            "expectedWorkdir",
            "refreshAgentReadiness",
            "const expectedWorkdir = options.expectedWorkdir ?? agentAdapterWorkdir();",
            "agentReadinessActionItems",
            "agentReadinessActionCommand",
            'agentReadinessActionCommand(payload, "create_recovery_archive")',
            'appStateCommand(appState, "recovery_archive")',
            "function agentReadinessWebBlockers",
            "web.readiness_blockers",
            'kind: "app_state_not_ready"',
            "agentReadinessLegacyWebRecoveryAction",
            "function agentReadinessWebBlockerSummary",
            "create_workdir",
            "choose_workdir",
            "function agentReadinessWebStatusLabel",
            "Web readiness needs attention",
            "Web start needs an auth token",
            "Web port is already in use",
            "Web start waits for App state",
            "Web start ready",
            "next_action_items",
            'const createWorkdirCommand = agentReadinessActionCommand(payload, "create_workdir");',
            'testId: "agent-readiness-copy-create-workdir"',
            "install commands stay hidden until the directory is usable",
            "confirm_readiness",
            "Choose the current Codex, Claude Code, or OpenCode host",
            "After installing the matching same-Agent project entry, confirm readiness before returning to Agent",
            "confirm_agent_visibility",
            "If /loopora-plan or /loopora-run is not visible",
            "function agentReadinessWebAction",
            "function agentReadinessWebActionCopyButton",
            "agent-readiness-copy-web",
            "Copy Web auth start",
            "Copy Web port recovery",
            "Copy Web bind recovery",
            "Copy Web start", "Copy Web open",
            "use_temporary_app_home",
            "Preview Web temporarily without changing the blocked App database",
            "agent-readiness-copy-temporary-app-home", "agent-readiness-copy-recovery-archive",
            "Copy temporary Web preview", "Copy private recovery archive",
            "configure_web_auth",
            "Set a Web auth token before starting network Web",
            "resolve_web_port",
            "Choose a free Web port or stop the service using the configured port",
            "resolve_web_bind",
            "Choose a different Web bind host or port",
            "Open Fit Guide/Web choices in Web", "Open the existing Loopora Web service",
            "Web conversation, Plan File import, or manual expert paths",
            "Web 对话、Plan File 导入或手动专家路径",
            "function agentReadinessCommandBlockerText",
            "After ${planBlockerEn}",
            "After installing the matching same-Agent project entry",
            "agentReadinessSteps(payload, fallbackSteps)",
            "function shortCommandLabel",
            "--directory <Loopora checkout>",
            "--workdir <target>",
            "LOOPORA_HOME",
            "<app-home>",
            '.replace(/\\s+/g, " ")',
            "function agentReadinessCopyButton",
            "agent-readiness-copy-readiness",
            "agent-readiness-copy-label",
            "function agentReadinessPreservesConfiguredAppHome",
            "agent-readiness-app-home-note",
            '!== "use_temporary_app_home"',
            "Copyable commands preserve this Web session's LOOPORA_HOME.",
            'title="${escapeHtml(value)}"',
            'aria-label="${escapeHtml(accessibleLabel)}"',
            "`${label}：${value}`",
            "`${label}: ${value}`",
        ),
    )


def _assert_tools_readiness_button_order(tools_js: str) -> None:
    action_block = tools_js.split("const actionButtons =", 1)[1].split("const publicReportButton", 1)[0]
    reset_command_block = tools_js.split("const resetCommand =", 1)[1].split("const readinessCommand =", 1)[0]
    assert reset_command_block.index('agentReadinessActionCommand(payload, "preview_app_database_reset")') < reset_command_block.index(
        'appStateCommand(appState, "preview_reset")'
    )
    assert reset_command_block.index('appStateCommand(appState, "preview_reset")') < reset_command_block.index('appStateCommand(appState, "reset")')
    assert action_block.index("!hasExplicitTarget || !hasSelectedHost") < action_block.index("selectedReady")
    ready_block, not_ready_block = action_block.split(": selectedReady", 1)[1].split(": `", 1)
    assert ready_block.index("recoveryArchiveButton") < ready_block.index("resetButton") < ready_block.index("temporaryAppHomeButton") < ready_block.index("agent-readiness-copy-plan")
    assert ready_block.index("agent-readiness-copy-plan") < ready_block.index("agent-readiness-copy-run")
    assert ready_block.index("agent-readiness-copy-run") < ready_block.index("webActionButton")
    assert not_ready_block.index("createWorkdirButton") < not_ready_block.index("recoveryArchiveButton") < not_ready_block.index("resetButton")
    assert "agent-readiness-copy-install" not in not_ready_block
    assert not_ready_block.index("resetButton") < not_ready_block.index("temporaryAppHomeButton") < not_ready_block.index("agent-readiness-copy-readiness")
    assert not_ready_block.index("agent-readiness-copy-readiness") < not_ready_block.index("webActionButton")
    assert 'const installCommand = agentReadinessCommand(entry, "install");' not in tools_js


def _assert_tools_public_report_assets(tools_html: str, tools_js: str, support_js: str, legacy_css: str, app_js: str) -> None:
    _assert_contains_all(
        tools_js,
        (
            "agentReadinessAppState",
            "agent-readiness-copy-reset",
            "agent-readiness-copy-public",
            "agentReadinessPublicUrl",
            "Choose a target project before copying a public report.",
            'public", "true"',
            'params.set("workdir", workdir);',
            "return window.LooporaUI.writeTextToClipboard(text);",
            "renderAgentReadinessPublicReportManualCopy",
            "renderAgentCommandManualCopy",
            "clearAgentCommandManualCopy",
            "agent-readiness-command-manual-copy",
            "agent-readiness-command-manual-copy-textarea",
            "The browser blocked automatic copy; copy the command below manually.",
            "publicReportManualCopyContainer",
            "clearAgentReadinessPublicReportManualCopy",
            "agent-readiness-public-report-textarea",
            "tools-support-public-report-textarea",
            "data-support-public-report-manual-copy",
            "data-support-copy-public-report",
            "data-support-command-copy",
            "supportCommandRequiresTarget",
            "SUPPORT_PUBLIC_ISSUE_BUNDLE_ACTION_KIND",
            "SUPPORT_TARGET_SCOPED_ACTION_KINDS",
            "function supportTargetProjectStatus",
            "function supportReportCommandReady",
            "function setToolsSupportTargetDataset",
            "function syncToolsSupportTargetStateNote",
            "function syncToolsSupportTargetState",
            "syncTargetScopedSupportCommandButton",
            "setToolsSupportActionGroups(hasTarget, reportCommandReady)",
            "supportReadyNextActionKinds",
            "supportBlockedNextActionKinds",
            "orderedSupportActionKinds",
            "targetRequiredNote.hidden = hasTarget",
            "button.dataset.supportCommandTemplate = template",
            "supportPublicDoctorCommandWithWorkdir(template, workdir)",
            "function supportPublicReportUrlWithWorkdir",
            "/api/diagnostics/public-issue-bundle",
            'params.set("language"',
            'toolsSupportPanel.dataset.supportPublicReportUrl = reportCommandReady ? supportPublicReportUrlWithWorkdir(workdir) : ""',
            'commandButton.dataset.supportCommandRequiresTarget = hasTarget ? "false" : "true"',
            'commandButton.dataset.supportCommandReady = commandReady ? "true" : "false"',
            "Refresh target before copying preferred bundle command",
            "Refresh target before copying fallback report command",
            "Copy public issue bundle for unusable target",
            "Copy preferred bundle command",
            "Copy fallback report command",
            "syncToolsSupportTargetState();",
            "clearAgentReadinessPublicReportManualCopy();",
            "const manualCopyContainer = publicReportManualCopyContainer(button);\n    clearAgentReadinessPublicReportManualCopy();\n    const {response, payload} = await fetchJson(agentReadinessPublicUrl());",
        ),
    )
    _assert_contains_all(
        support_js + app_js,
        (
            "data-support-copy-public-report",
            "supportReportButtons",
            "handlePublicReportButton(button)",
            "copyPublicReport(button)",
            "fetchPublicIssueBundleText(url)",
            'Accept: "text/plain, application/json"',
            "payload.public_issue_bundle_text",
            "payload.public_issue_bundle",
            "The public issue bundle response did not include copyable text.",
            "Public issue support bundle copied.",
            "data-support-command-copy",
            "tools-support-status",
            "tools-support-public-report-textarea",
            "tools-support-command-manual-copy-textarea",
            "support-target-form",
            "data-support-browse-workdir",
            "data-support-recent-workdir",
            "data-support-target-summary",
            "data-support-target-description",
            "supportHeroReportLink?.addEventListener",
            "function syncStandaloneSupportTargetState",
            "function syncStandaloneSupportCommandButton",
            'supportPanel.dataset.supportPublicReportUrl = hasTarget ? supportPublicReportUrlWithWorkdir(value) : ""',
            'control.dataset.supportCopyPublicReport = "true"',
            'document.addEventListener("loopora:workdirchange"',
            '"/api/system/pick-directory"',
            "supportTargetForm.requestSubmit",
            "Target project folder selected.",
            "Clearing target project context",
            'url.searchParams.delete("workdir");',
            'url.searchParams.set("support_target_feedback", "target_required");',
            "window.location.assign(`${url.pathname}${url.search}${url.hash}`);",
            "Local command copied. Prefer the support bundle output in public issues.",
            "The browser blocked automatic copy; copy the local command below manually.",
            "Choose and refresh a target project before copying preferred bundle or fallback report commands",
            "Open this page with a target project before copying preferred bundle or fallback report commands",
            "return window.LooporaUI.writeTextToClipboard(text);",
            'renderManualCopy("");\n    const url = String(supportPanel.dataset.supportPublicReportUrl || "").trim();',
            'renderManualCopy("");\n    if (button.dataset.supportCommandRequiresTarget === "true"',
            "renderManualCommandCopy(value);",
            "window.LooporaUI?.renderManualCopy?.(manualCopyContainer",
            "function renderManualCopy(container, value, options = {})",
            "textarea.focus({preventScroll: true});\n      } catch (_) {\n        textarea.focus();",
            "renderManualCopy,",
        ),
    )
    _assert_contains_all(
        tools_html,
        (
            "data-support-next-action-kinds=",
            "data-support-ready-next-action-kinds=",
            "data-support-blocked-next-action-kinds=",
            "data-support-target-required-note",
            "data-support-panel-context=",
            "data-support-manual-copy",
            "run_public_issue_bundle",
            "run_public_doctor_report",
            "run_version_identity",
            "open_bug_report",
            "open_feature_request",
            "read_support_policy",
            "use_private_security_reporting",
            "public issue support bundle",
            'data-support-next-action-kind="run_public_issue_bundle"',
            'data-support-next-action-kind="run_public_doctor_report"',
            'data-support-allows-nonzero-exit="true"',
            'data-support-command-ready="false"',
            'data-support-next-action-kind="run_version_identity"',
            'data-support-command-ready="true"',
            'data-testid="tools-support-copy-public-issue-bundle-command"',
            'data-testid="tools-support-copy-version-json"',
            "loopora version --json",
            'data-support-route-kind="bug_report"',
            'data-support-route-kind="feature_request"',
            'data-support-route-kind="usage_or_setup"',
            'data-support-route-kind="security"',
            'data-support-public-fallback="private_channel_request_only"',
            "pages/support.js",
        ),
    )
    assert "copyTextWithSelectionFallback" not in tools_js + support_js
    assert not any(
        term in tools_js + support_js
        for term in (
            "navigator.clipboard.writeText",
            'document.execCommand("copy")',
            "function publicIssueBundleText",
            "function packageSourceIdentity",
            'event.preventDefault();\n      setSupportTargetStatus(localeText("先填写目标项目路径。',
        )
    )
    assert 'if (workdir) {\n      params.set("workdir", workdir);' not in tools_js
    _assert_contains_all(
        legacy_css,
        (
            "agent-readiness-public-report",
            "support-target-control",
            ".field-status.is-warning",
            "agent-readiness-copy-label",
            ".agent-readiness-copy-button code {\n  max-width: 100%;\n  white-space: normal;\n  overflow-wrap: anywhere;\n  word-break: normal;",
        ),
    )
    assert ".agent-readiness-copy-button code {\n  max-width: 100%;\n  overflow: hidden;\n  text-overflow: ellipsis;" not in legacy_css


def _assert_tools_adapter_handoff_assets(tools_js: str, legacy_css: str) -> None:
    _assert_contains_all(
        tools_js,
        (
            "function renderAgentAdapterUninstallSummary",
            "agent-adapter-uninstall-summary",
            "agent-adapter-reinstall-command",
            "agentAdapterFirstTaskExamples",
            "agentAdapterFirstTaskExampleStates",
            "agentAdapterNextCommands",
            "agentAdapterHandoffUsesFitDraft",
            "agentAdapterFirstTaskHandoffPolicies",
            "agentAdapterFirstTaskHandoffPolicy",
            "normalizeAgentAdapterFirstTaskExampleState",
            "rerenderAgentAdapterHandoff",
            "rememberAgentAdapterNextCommands",
            'const doctorCommand = agentReadinessCurrentTargetCommand()\n      || agentAdapterNextCommand(adapter, item, "doctor");',
            "agentAdapterDiagnosticButton",
            "agent-adapter-command-flow--with-brief",
            "agent-adapter-first-task-example",
            "agent-adapter-first-task-preferred-source",
            "agent-adapter-clear-first-task-example",
            "agent-adapter-copy-first-task-example",
            'firstTaskReviewedMessageText || "/loopora-plan"',
            'firstTaskReviewedMessageText ? "agent-adapter-copy-first-task-example" : "agent-adapter-copy-gen"',
            "Copy one-message /loopora-plan handoff",
            "复制单条 /loopora-plan 交接消息",
            "agent-adapter-diagnostic-actions",
            "agent-adapter-copy-readiness",
            "first_task_message_example",
            "first_task_handoff_policy",
            "outside an Agent session, Web conversation, Plan File import, and manual expert paths",
            "不在 Agent 会话中时，Web 对话、Plan File 导入和手动专家路径",
            "next_commands",
            "Generic fallback example",
            "agent-adapter-first-task-orientation-example",
            "agentAdapterRemovedFiles",
            "agentAdapterKeptFiles",
            "agentAdapterUninstallReinstallCommand",
            "next_commands?.reinstall",
            "agent-adapter-managed-file-summary",
            "data-agent-adapter-command-manual-copy",
            "agent-adapter-command-manual-copy-textarea",
            "The browser blocked automatic copy; copy the Agent command below manually.",
        ),
    )
    assert "agent-adapter-copy-web-start" not in tools_js
    assert all(term not in tools_js for term in ("loopora init ${adapter}", "Copy first task message", "复制第一条任务消息"))
    _assert_contains_all(
        legacy_css,
        (
            "agent-adapter-uninstall-summary",
            "agent-adapter-command-flow--with-brief",
            "agent-adapter-first-task-example",
            "agent-adapter-first-task-example-head",
            "agent-adapter-first-task-source-note",
            "agent-adapter-example-button",
        ),
    )
    assert "agent-adapter-manifest-path" not in tools_js


def _assert_tools_adapter_mutation_assets(response_text: str, tools_js: str) -> None:
    _assert_contains_all(
        response_text,
        (
            "这里的目标会同步为 Web 项目作用域",
            "This target also becomes the Web project scope",
            'data-agent-adapter-preference-scope="',
            'list="agent-adapter-recent-workdir-options"',
            'data-testid="global-project-scope-options"',
            "data-project-scope-option",
            'data-testid="agent-adapter-browse-workdir"',
            "选择目录",
            "Choose folder",
            'data-testid="agent-adapter-use-server-workdir"',
            "使用服务目录",
            "Use service folder",
            'data-testid="agent-host-selector"',
            'data-testid="agent-host-codex"',
            'data-testid="agent-host-claude"',
            'data-testid="agent-host-opencode"',
            'data-testid="agent-adapter-grid" hidden',
        ),
    )
    assert 'data-testid="agent-adapter-recent-workdirs"' not in response_text
    for testid in (
        "agent-adapter-install-codex",
        "agent-adapter-uninstall-codex",
        "agent-adapter-install-claude",
        "agent-adapter-uninstall-claude",
        "agent-adapter-install-opencode",
        "agent-adapter-uninstall-opencode",
    ):
        assert f'data-testid="{testid}" disabled' in response_text
    _assert_contains_all(
        tools_js,
        (
            "Choose a recent project from Switch project above",
            "Both target controls stay in sync.",
            "This is also the Web project scope",
            "const hasExplicitTarget = Boolean(agentAdapterWorkdir());",
            "Confirm the same-Agent target project",
            "No same-Agent target project is selected yet.",
            "adopt the service folder as the explicit target",
            "where you are using Codex, Claude Code, or OpenCode",
            "After refresh, copy install, readiness, or public diagnostic commands.",
            "const steps = !hasExplicitTarget",
            "const actionButtons = !hasExplicitTarget || !hasSelectedHost",
            "const publicReportButton = hasExplicitTarget",
            "No target selected",
            "function setAgentAdapterTargetWorkdir",
            "function agentAdapterResponseWorkdir",
            "function agentAdapterResponseMatchesExpected",
            "function normalizeAgentAdapterTargetFromPayload",
            'window.LooporaUI.syncWorkdirContext(resolved, {syncUrl: true, urlParam: "workdir"})',
            'window.LooporaUI.syncWorkdirContext(workdir, {syncUrl: true, urlParam: "workdir"})',
            'window.LooporaUI.syncWorkdirContext("", {syncUrl: true, urlParam: "workdir"})',
            "persistAgentAdapterWorkdirPreference(resolved)",
            "normalizeAgentAdapterTargetFromPayload(payload, expectedWorkdir);",
            "agentAdapterBrowseWorkdirButton",
            "function browseAgentAdapterWorkdir",
            '"/api/system/pick-directory"',
            "Target project folder selected.",
            "agentAdapterUseServerWorkdirButton",
            "function updateAgentAdapterUseServerWorkdirButton",
            "function applyAgentAdapterServerWorkdir",
            "dataset.serverWorkdir",
            "Service folder set as the target project.",
            "function agentAdapterWorkdirPreferenceKey",
            "dataset.agentAdapterPreferenceScope",
            "window.localStorage.getItem(agentAdapterWorkdirPreferenceKey())",
            "window.localStorage.removeItem(preferenceKey)",
            "window.localStorage.removeItem(AGENT_ADAPTER_WORKDIR_PREF_KEY)",
            "Enter the target project directory before installing or removing same-Agent project entries.",
            "function agentAdapterTargetRequiredMessage",
            "const explicitWorkdir = agentAdapterWorkdir();",
            "if (!explicitWorkdir)",
            "const hasExplicitTarget = Boolean(agentAdapterWorkdir());",
            "function setAgentAdapterMutationButtonBaseState",
            "setAgentAdapterMutationButtonBaseState(button,",
            "function ensureAgentHostSelection",
            "payload?.current_agent_host",
            'String(detectedHost?.state || "") === "detected"',
            "function agentHostSelectionBlocksMutation",
            "return JSON.stringify({workdir});",
            "mutationError.payload = payload;",
            "function agentAdapterWorkdirRecoveryMessage",
            'payload?.loop_recovery !== "adapter_workdir_unavailable"',
            "First run:",
            "Enter an existing project directory.",
        ),
    )
    assert all(fragment not in tools_js for fragment in ("return JSON.stringify(workdir ? {workdir} : {});", "agentAdapterRecentWorkdirButtons", "function applyAgentAdapterRecentWorkdir"))


def test_api_doctor_reports_first_use_readiness(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="127.0.0.1", bind_port=9123))

    before_install = client.get("/api/diagnostics/doctor", params={"workdir": str(sample_workdir)})

    assert before_install.status_code == HTTPStatus.OK
    before_payload = before_install.json()
    assert before_payload["status"] == "not_ready"
    assert before_payload["ready"] is False
    assert before_payload["agent_entry_ready"] is False
    assert before_payload["strict_ready"] is False
    assert before_payload["workdir"] == str(sample_workdir.resolve())
    assert before_payload["schema_version"] == 2
    assert before_payload["app_state"]["status"] == "not_initialized"
    assert before_payload["app_state"]["web_ready"] is True
    assert before_payload["web"]["origin"] == "http://127.0.0.1:9123"
    assert before_payload["web"]["already_running"] is True
    assert before_payload["web"]["start_available"] is True
    assert before_payload["web"]["access_mode"] == "open_existing"
    assert before_payload["first_task_message_example"].startswith("/loopora-plan\n\nLoopora fit:")
    assert before_payload["first_task_handoff_policy"]["preferred_source"] == "completed_fit_review"
    assert [item["kind"] for item in before_payload["next_action_items"]] == [
        "check_fit_first",
        "install_agent_entry",
        "confirm_readiness",
        "run_loopora_plan",
        "support",
    ]
    assert (before_payload["next_action_items"][1]["selection_required"], before_payload["next_action_items"][2]["after_action"]) == (
        True,
        "install_agent_entry",
    )
    assert [choice["adapter"] for choice in before_payload["next_action_items"][1]["adapter_choices"]] == ["codex", "claude", "opencode"]
    assert all(key not in before_payload["next_action_items"][1] for key in ("adapter", "command"))
    assert "loopora doctor --workdir" in before_payload["next_action_items"][2]["command"]
    assert before_payload["primary_next_action_kind"] == "check_fit_first"
    assert any(item["adapter"] == "codex" and item["next_action"] == "install_agent_entry" for item in before_payload["agent_entries"])

    install_agent_adapter("codex", sample_workdir)
    after_install = client.get("/api/diagnostics/doctor", params={"workdir": str(sample_workdir)})

    assert after_install.status_code == HTTPStatus.OK
    after_payload = after_install.json()
    assert after_payload["status"] == "ready"
    assert after_payload["ready"] is True
    assert after_payload["agent_entry_ready"] is True
    assert after_payload["strict_ready"] is True
    assert after_payload["app_state"]["status"] == "not_initialized"
    assert after_payload["ready_adapter_count"] == 1
    assert after_payload["first_task_message_example"].startswith("/loopora-plan\n\nLoopora fit:")
    assert after_payload["first_task_handoff_policy"]["fallback_source"] == "generic_example"
    assert [item["kind"] for item in after_payload["next_action_items"]] == [
        "return_to_agent",
        "confirm_agent_visibility",
        "run_loopora_plan",
        "review_ready_loop_preview",
        "run_loopora_run",
        "support",
        "start_web",
    ]
    assert (after_payload["next_action_items"][-1]["operation"], after_payload["next_action_items"][-1]["already_running"]) == (
        "open_existing", True,
    )
    assert any(item["adapter"] == "codex" and item["ready"] is True for item in after_payload["agent_entries"])


def test_api_doctor_handles_workdir_resolve_failure_before_entry_checks(
    monkeypatch,
    service_factory,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    blocked_workdir = tmp_path / "resolve-blocked-project"
    private_path = tmp_path / "private" / "resolve-blocked-project"
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *args, **kwargs) -> Path:
        if path == blocked_workdir:
            raise OSError(f"permission denied: {private_path}")
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", fail_resolve)

    response = client.get("/api/diagnostics/doctor", params={"workdir": str(blocked_workdir)})
    public = client.get("/api/diagnostics/doctor", params={"workdir": str(blocked_workdir), "public": "true"})

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    encoded = json.dumps(payload, ensure_ascii=False)
    assert payload["workdir_state"]["status"] == "unavailable"
    assert payload["workdir_state"]["error"] == "workdir could not be inspected"
    assert [item["kind"] for item in payload["next_action_items"]] == [
        "choose_workdir",
        "confirm_readiness",
        "support",
    ]
    assert "loopora init codex" not in json.dumps(payload["next_action_items"], ensure_ascii=False)
    assert "permission denied" not in encoded
    assert str(private_path) not in encoded

    assert public.status_code == HTTPStatus.OK
    public_payload = public.json()
    public_encoded = json.dumps(public_payload, ensure_ascii=False)
    assert public_payload["project_directory_status"] == "unavailable"
    assert public_payload["next_actions"] == ["choose_project_directory", "confirm_readiness", "support"]
    assert "install_agent_entry" not in public_payload["next_actions"]
    assert str(blocked_workdir) not in public_encoded
    assert "permission denied" not in public_encoded
    assert str(private_path) not in public_encoded


def test_api_doctor_network_mode_distinguishes_open_and_bind_origins(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", bind_port=9124, auth_token="secret-token"))
    install_agent_adapter("codex", sample_workdir)

    response = client.get(
        "/api/diagnostics/doctor",
        params={"workdir": str(sample_workdir)},
        headers={"Authorization": "Bearer secret-token"},
    )
    payload = response.json()

    assert response.status_code == HTTPStatus.OK
    assert payload["web"]["origin"] == "http://127.0.0.1:9124"
    assert payload["web"]["bind_origin"] == "http://0.0.0.0:9124"
    assert payload["web"]["remote_origin_hint"] == "http://<server-host>:9124"
    assert payload["web"]["wildcard_bind"] is True
    assert payload["web"]["already_running"] is True
    assert payload["web"]["start_available"] is True
    assert payload["next_action_items"][-1]["kind"] == "start_web"
    assert payload["next_action_items"][-1]["origin"] == "http://127.0.0.1:9124"


def test_cli_diagnose_doctor_web_bind_failure_is_stable_and_redacted(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    port = _free_local_port()
    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(tmp_path)])
    assert install.exit_code == 0, result_error_text(install)

    def fail_probe_web_bind(_host: str, _port: int) -> None:
        raise OSError("permission denied: /private/socket")

    monkeypatch.setattr("loopora.diagnose_doctor.probe_web_bind", fail_probe_web_bind)

    result = runner.invoke(cli.app, ["doctor", "--workdir", str(tmp_path), "--web-port", str(port), "--json"])
    plain = runner.invoke(cli.app, ["doctor", "--workdir", str(tmp_path), "--web-port", str(port)])
    public = runner.invoke(cli.app, ["doctor", "--workdir", str(tmp_path), "--web-port", str(port), "--public-json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    encoded = json.dumps(payload, ensure_ascii=False)
    assert payload["status"] == "ready_with_warnings"
    assert payload["ready"] is True
    assert payload["strict_ready"] is False
    assert payload["diagnose_doctor_summary"]["web_start_available"] is False
    assert payload["diagnose_doctor_summary"]["web_start_blocked_reason"] == "bind_failed"
    assert payload["web"]["start_available"] is False
    assert payload["web"]["start_blocked_reason"] == "bind_failed"
    assert payload["web"]["start_error"] == "bind target is unavailable"
    assert payload["web"]["suggested_start_command"] == ""
    assert payload["next_action_items"][-1]["kind"] == "resolve_web_bind"
    assert payload["next_action_items"][-1]["command"] == payload["web"]["requested_start_command"]
    assert "permission denied" not in encoded
    assert "/private/socket" not in encoded

    assert plain.exit_code == 0, plain.stdout
    assert f"web: http://127.0.0.1:{port} (bind failed; loopback local default)" in plain.stdout
    assert "web start unavailable:" in plain.stdout
    assert f"--port {port}" in plain.stdout
    assert "web start: choose a different --web-host / --web-port" in plain.stdout
    assert "permission denied" not in plain.stdout
    assert "/private/socket" not in plain.stdout

    assert public.exit_code == 0, public.stdout
    public_payload = json.loads(public.stdout)
    public_encoded = json.dumps(public_payload, ensure_ascii=False)
    assert public_payload["web"]["start_available"] is False
    assert public_payload["web"]["start_blocked_reason"] == "bind_failed"
    assert public_payload["web"]["recovery_action"] == "choose_different_bind_host_or_port"
    assert public_payload["web"]["alternate_port_available"] is False
    assert public_payload["next_action_summaries"][-1] == {
        "kind": "resolve_web_bind",
        "summary": "Choose a different Web bind host or port.",
    }
    assert public_payload["diagnose_doctor_public_summary"]["next_action_kinds"] == public_payload["next_action_kinds"]
    assert public_payload["diagnose_doctor_public_summary"]["next_action_summaries"] == public_payload["next_action_summaries"]
    assert str(port) not in public_encoded
    assert "permission denied" not in public_encoded
    assert "/private/socket" not in public_encoded


def test_cli_serve_bind_failure_is_stable_before_app_start(monkeypatch) -> None:
    runner = CliRunner()

    def fail_probe_web_bind(_host: str, _port: int) -> None:
        raise OSError("permission denied: /private/socket")

    def fail_build_app(**_kwargs):
        raise AssertionError("serve should fail before building the app when bind preflight fails")

    def fail_uvicorn_run(_app, **_kwargs) -> None:
        raise AssertionError("serve should fail before starting uvicorn when bind preflight fails")

    monkeypatch.setattr("loopora.cli_serve_output.probe_web_bind", fail_probe_web_bind)
    monkeypatch.setattr("loopora.cli_serve_commands.build_app", fail_build_app)
    monkeypatch.setattr("loopora.cli_serve_commands.uvicorn.run", fail_uvicorn_run)

    result = runner.invoke(cli.app, ["serve", "--host", "127.0.0.1", "--port", "9755"])

    assert result.exit_code == 1
    error_text = result_error_text(result)
    assert "cannot start Loopora Web on http://127.0.0.1:9755: bind target is unavailable." in error_text
    assert "Choose a different --host / --port" in error_text
    assert "permission denied" not in error_text
    assert "/private/socket" not in error_text
    assert "Loopora Web:" not in result.stdout


def test_tools_page_surfaces_doctor_readiness_before_adapter_actions(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="127.0.0.1", bind_port=9123))
    recent_alpha = tmp_path / "recent-alpha"
    recent_beta = tmp_path / "recent-beta"
    save_recent_workdirs([str(recent_alpha), str(recent_beta)])

    response = client.get("/tools")
    tools_js, support_js, legacy_css, app_js = _read_tools_assets()
    expected_scope = f"app-home-sha256:{sha256(str(app_home()).encode('utf-8')).hexdigest()}"

    assert response.status_code == HTTPStatus.OK
    assert f'data-agent-adapter-preference-scope="{expected_scope}"' in response.text
    assert str(app_home()) not in response.text
    assert (str(recent_alpha) in response.text, str(recent_beta) in response.text) == (True, True)
    assert "--web-host 127.0.0.1 --web-port 9123 --workdir &#39;&lt;project-dir&gt;&#39; || true" in response.text
    _assert_tools_readiness_assets(response.text, tools_js)
    _assert_tools_readiness_button_order(tools_js)
    _assert_tools_public_report_assets(response.text, tools_js, support_js, legacy_css, app_js)
    _assert_tools_adapter_handoff_assets(tools_js, legacy_css)
    _assert_tools_adapter_mutation_assets(response.text, tools_js)


def test_tools_preference_scope_uses_resolved_app_home_without_leaking_path(
    monkeypatch,
    service_factory,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOOPORA_HOME", "relative app home")
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    resolved_home = tmp_path / "relative app home"
    expected_scope = f"app-home-sha256:{sha256(str(resolved_home).encode('utf-8')).hexdigest()}"

    response = client.get("/tools")

    assert response.status_code == HTTPStatus.OK
    assert f'data-agent-adapter-preference-scope="{expected_scope}"' in response.text
    assert "relative app home" not in response.text
    assert str(resolved_home) not in response.text


def test_tools_network_mode_keeps_local_asset_actions_copy_only(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    response = client.get("/tools", headers={"Authorization": "Bearer secret-token"})
    support_response = client.get("/support", headers={"Authorization": "Bearer secret-token"})
    tools_js, _, _, _ = _read_tools_assets()

    assert response.status_code == HTTPStatus.OK
    assert 'data-testid="local-assets-diagnostics-panel"' in response.text
    assert 'data-native-dialogs-enabled="false"' in response.text
    assert 'data-testid="local-assets-remote-path-note"' in response.text
    assert 'data-testid="agent-adapter-browse-workdir"' not in response.text
    assert 'data-testid="support-browse-workdir"' not in support_response.text
    _assert_contains_all(
        tools_js,
        (
            "localAssetsNativeDialogsEnabled",
            "Copy folder path",
            "Network mode cannot open host folders",
            "Server-side path copied to clipboard.",
            "window.LooporaUI?.renderGlobalManualCopy?.(value",
            "local-asset-path-manual-copy-textarea",
            "The browser blocked automatic copy; copy the server-side path at the bottom of the page manually.",
            "copyOriginalPathButton",
        ),
    )

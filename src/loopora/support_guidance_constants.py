from __future__ import annotations

SUPPORT_HELP_EPILOG = (
    "Support is best-effort and security-sensitive details do not belong in public issues. "
    "Use `loopora support` when you need the safe public reporting route; it stays route-only and does not run "
    "diagnostics. Use `loopora support --workdir \"$PWD\" --public-issue-bundle` when you need one pasteable "
    "public issue bundle, or run the printed "
    "`loopora doctor --public-json --workdir ...` command only when maintainers ask for a separate redacted readiness report. "
    "Without a target project, support-bundle/fallback-report commands are preview-only; rerun support from the target project with "
    "`--workdir \"$PWD\"` before copying the public issue bundle or fallback public doctor command, or replace `<project-dir>` only when "
    "intentionally copying the preview shape. "
    "When checking a custom Web target, pass the same `--web-host`/`--web-port` to keep the local redacted "
    "doctor command aligned with the Web service you intend to inspect. "
    "Paste publicly the public issue bundle first; use redacted doctor output, `loopora --version` output, or "
    "`loopora version --json` output only when requested; keep support JSON, printed command lines, JSON command fields, "
    "and local Web Support URLs local-only. "
    "Use `--language zh` for Chinese human output; JSON keeps stable route kinds, command fields, and command "
    "execution blockers. "
    "Use SECURITY.md or private reporting for vulnerabilities, credentials, tokens, private logs, private workspace "
    "paths, run artifacts, evidence records, or Web access tokens. If private reporting is unavailable, a public "
    "issue may only ask maintainers for a private channel and must not include sensitive details."
)
SUPPORT_SCHEMA_VERSION = 1
SUPPORT_WORKDIR_PLACEHOLDER = "<project-dir>"
SUPPORT_REDACTION_ITEMS = [
    "credentials",
    "tokens",
    "provider transcripts",
    "private logs",
    "local paths",
    "local command lines that include checkout or project paths",
    "sensitive workspace data",
    "run artifacts or evidence records that expose private project details",
]
SUPPORT_PUBLIC_PASTE_ITEMS = [
    "public_issue_bundle_output",
    "public_doctor_output",
    "version_output",
    "version_identity_json_output",
]
SUPPORT_PREFERRED_PUBLIC_PASTE_ITEMS = ["public_issue_bundle_output"]
SUPPORT_FALLBACK_PUBLIC_PASTE_ITEMS = ["public_doctor_output"]
SUPPORT_IDENTITY_PUBLIC_PASTE_ITEMS = ["version_output", "version_identity_json_output"]
SUPPORT_LOCAL_ONLY_ITEMS = [
    "support_json",
    "printed_command_lines",
    "command_fields",
    "local_web_support_urls",
]
SUPPORT_PUBLIC_PASTE_ITEMS_EN = [
    "public issue support bundle output (preferred for readiness/environment evidence)",
    "redacted doctor --public-json report output (fallback when requested)",
    "loopora --version output (when identity is requested)",
    "loopora version --json output (when structured identity is requested)",
]
SUPPORT_LOCAL_ONLY_ITEMS_EN = [
    "support JSON",
    "printed command lines",
    "JSON command fields",
    "local Web Support URLs",
]
SUPPORT_REDACTION_ITEMS_ZH = [
    "凭据",
    "令牌",
    "provider transcript",
    "私有日志",
    "本地路径",
    "包含源码检出或项目路径的本地命令行",
    "敏感工作区数据",
    "会暴露私有项目细节的 run artifact 或 evidence record",
]
SUPPORT_PUBLIC_PASTE_ITEMS_ZH = [
    "公开 issue 支持包输出（就绪/环境证据优先使用）",
    "doctor --public-json 的脱敏报告输出（被要求时作为兜底）",
    "loopora --version 的版本/源码输出（被要求提供身份时）",
    "loopora version --json 的结构化版本/源码身份输出（被要求提供结构化身份时）",
]
SUPPORT_LOCAL_ONLY_ITEMS_ZH = [
    "support JSON",
    "本页打印的命令行",
    "JSON command 字段",
    "本地 Web 支持页 URL",
]
SUPPORT_DOCUMENT_URL = "https://github.com/huyusong10/Loopora/blob/dev/SUPPORT.md"
SECURITY_POLICY_URL = "https://github.com/huyusong10/Loopora/security/policy"
PRIVATE_SECURITY_REPORT_URL = "https://github.com/huyusong10/Loopora/security/advisories/new"
BUG_REPORT_URL = "https://github.com/huyusong10/Loopora/issues/new?template=bug_report.yml"
FEATURE_REQUEST_URL = "https://github.com/huyusong10/Loopora/issues/new?template=feature_request.yml"
SECURITY_PUBLIC_FALLBACK = (
    "If private reporting is unavailable, open a public issue only asking for a private reporting channel; "
    "include no exploit details or sensitive data."
)
SECURITY_PUBLIC_FALLBACK_ZH = "如果私密报告入口不可用，公开 issue 只能请求私密渠道，不要包含漏洞细节或敏感数据。"

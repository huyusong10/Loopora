from __future__ import annotations

from loopora.support_guidance_constants import (
    BUG_REPORT_URL,
    FEATURE_REQUEST_URL,
    PRIVATE_SECURITY_REPORT_URL,
    SECURITY_POLICY_URL,
    SECURITY_PUBLIC_FALLBACK,
    SECURITY_PUBLIC_FALLBACK_ZH,
    SUPPORT_DOCUMENT_URL,
)


def support_issue_routes() -> list[dict[str, str]]:
    return [
        {
            "kind": "bug_report",
            "destination": "GitHub Bug Report template",
            "destination_en": "GitHub Bug Report template",
            "destination_zh": "GitHub Bug Report 模板",
            "url": BUG_REPORT_URL,
            "when": "reproducible Loopora defect or setup/readiness blocker after SUPPORT.md",
            "when_en": "reproducible Loopora defect or setup/readiness blocker after SUPPORT.md",
            "when_zh": "可复现的 Loopora 缺陷，或已经阅读 SUPPORT.md 后仍存在的设置/就绪阻塞",
        },
        {
            "kind": "feature_request",
            "destination": "GitHub Feature Request template",
            "destination_en": "GitHub Feature Request template",
            "destination_zh": "GitHub Feature Request 模板",
            "url": FEATURE_REQUEST_URL,
            "when": "new user-visible Loopora behavior or compatibility proposal",
            "when_en": "new user-visible Loopora behavior or compatibility proposal",
            "when_zh": "新的 Loopora 用户可见行为，或兼容性提案",
        },
        {
            "kind": "usage_or_setup",
            "destination": "SUPPORT.md then bug or feature template only when the question becomes reproducible or behavior-changing",
            "destination_en": (
                "SUPPORT.md then bug or feature template only when the question becomes reproducible or behavior-changing"
            ),
            "destination_zh": "先阅读 SUPPORT.md；只有问题变成可复现缺陷或行为变更提案时才使用 bug/feature 模板",
            "url": SUPPORT_DOCUMENT_URL,
            "when": "best-effort usage or setup question",
            "when_en": "best-effort usage or setup question",
            "when_zh": "best-effort 使用或设置问题",
        },
        {
            "kind": "security",
            "destination": "SECURITY.md or private vulnerability reporting",
            "destination_en": "SECURITY.md or private vulnerability reporting",
            "destination_zh": "SECURITY.md 或私密漏洞报告",
            "url": PRIVATE_SECURITY_REPORT_URL,
            "policy_url": SECURITY_POLICY_URL,
            "private_report_url": PRIVATE_SECURITY_REPORT_URL,
            "public_fallback": SECURITY_PUBLIC_FALLBACK,
            "public_fallback_en": SECURITY_PUBLIC_FALLBACK,
            "public_fallback_zh": SECURITY_PUBLIC_FALLBACK_ZH,
            "when": "vulnerability, credential, token, private path, private log, run artifact, evidence record, or Web access token exposure",
            "when_en": (
                "vulnerability, credential, token, private path, private log, run artifact, evidence record, "
                "or Web access token exposure"
            ),
            "when_zh": "漏洞、凭据、令牌、私有路径、私有日志、run artifact、evidence record 或 Web 访问令牌暴露",
        },
    ]


def support_issue_route_actions(*, language: str) -> list[dict[str, object]]:
    route_action_kinds = {
        "bug_report": "open_bug_report",
        "feature_request": "open_feature_request",
        "usage_or_setup": "read_support_policy",
        "security": "use_private_security_reporting",
    }
    actions: list[dict[str, object]] = []
    for route in support_issue_routes():
        route_kind = route["kind"]
        action: dict[str, object] = {
            "kind": route_action_kinds.get(route_kind, f"open_{route_kind}"),
            "route_kind": route_kind,
            "url": route["url"],
            "note": route["when_zh"] if language == "zh" else route["when_en"],
        }
        for key in ("policy_url", "private_report_url"):
            if key in route:
                action[key] = route[key]
        if route_kind == "security":
            action["public_fallback"] = "private_channel_request_only"
            action["public_fallback_no_sensitive_details"] = True
            action["public_fallback_text"] = route.get("public_fallback", "")
        actions.append(action)
    return actions

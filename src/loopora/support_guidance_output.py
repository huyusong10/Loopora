from __future__ import annotations

from collections.abc import Mapping

from loopora.support_guidance_text import (
    support_command_status_lines,
    support_local_command_lines,
    support_local_only_items,
    support_payload_language,
    support_posting_guidance_text,
    support_public_paste_items,
    support_redaction_items,
    support_target_project_lines,
    support_text,
    support_web_lines,
)


def public_support_guidance_lines(payload: Mapping[str, object]) -> list[str]:
    commands = payload.get("commands") if isinstance(payload.get("commands"), Mapping) else {}
    links = payload.get("links") if isinstance(payload.get("links"), Mapping) else {}
    language = support_payload_language(payload)
    route_urls = _support_route_urls(payload)
    return [
        support_text(language, "Loopora support", "Loopora 支持"),
        support_text(language, "Support scope: best-effort; no guaranteed response time.", "支持范围：best-effort；不保证响应时间。"),
        support_text(language, "Public diagnostic:", "公开诊断:"),
        support_posting_guidance_text(payload, language=language),
        *support_target_project_lines(payload, language=language),
        *support_command_status_lines(payload, language=language),
        support_text(
            language,
            "Paste publicly only (preferred first; fallbacks only when requested):",
            "公开 issue 只粘贴（优先支持包；兜底材料按需提供）:",
        ),
        *[f"- {item}" for item in support_public_paste_items(language)],
        support_text(language, "Keep local only:", "仅限本地使用:"),
        *[f"- {item}" for item in support_local_only_items(language)],
        *support_local_command_lines(payload, commands=commands, language=language),
        *support_web_lines(payload, language=language),
        support_text(language, "Before posting publicly, remove:", "公开发布前请移除:"),
        *[f"- {item}" for item in support_redaction_items(language)],
        support_text(language, "Where to go:", "应该去哪里:"),
        support_text(
            language,
            f"- Reproducible defects or setup/readiness blockers: GitHub Bug Report template with public readiness status: {route_urls.get('bug_report')}",
            f"- 可复现缺陷或设置/就绪阻塞：使用 GitHub Bug Report 模板，并填写公开就绪报告状态: {route_urls.get('bug_report')}",
        ),
        support_text(
            language,
            f"- New user-visible behavior: GitHub Feature Request template with Loopora fit, non-goals, evidence, and risk: {route_urls.get('feature_request')}",
            f"- 新的用户可见行为：使用 GitHub Feature Request 模板，并说明 Loopora 适配性、非目标、证据和风险: {route_urls.get('feature_request')}",
        ),
        support_text(
            language,
            f"- Usage/setup questions: start with SUPPORT.md; file an issue only when it becomes a reproducible defect or proposal: {route_urls.get('usage_or_setup')}",
            f"- 使用/设置问题：先看 SUPPORT.md；只有变成可复现缺陷或产品提案时才开 issue: {route_urls.get('usage_or_setup')}",
        ),
        support_text(
            language,
            "- Vulnerabilities or sensitive details: read SECURITY.md and use private reporting when available; "
            f"if unavailable, a public issue may only ask for a private channel with no details: {links.get('security_policy')} / {route_urls.get('security')}",
            "- 漏洞或敏感细节：先读 SECURITY.md，优先走私密报告；如果私密入口不可用，公开 issue "
            f"只能请求私密渠道且不能写细节: {links.get('security_policy')} / {route_urls.get('security')}",
        ),
    ]


def _support_route_urls(payload: Mapping[str, object]) -> dict[str, str]:
    routes = payload.get("issue_routes") if isinstance(payload.get("issue_routes"), list) else []
    urls: dict[str, str] = {}
    for route in routes:
        if isinstance(route, Mapping):
            urls[str(route.get("kind") or "")] = str(route.get("url") or "")
    return urls

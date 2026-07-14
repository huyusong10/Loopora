from __future__ import annotations

from collections.abc import Mapping
import json

from loopora.support_guidance import normalize_support_guidance_language, support_text


def support_public_issue_bundle_text(public_doctor_payload: Mapping[str, object], *, language: str = "en") -> str:
    support_language = normalize_support_guidance_language(language)
    report_json = json.dumps(dict(public_doctor_payload), ensure_ascii=False, indent=2)
    return "\n".join(
        [
            support_text(support_language, "Loopora public issue support bundle", "Loopora 公开 issue 支持包"),
            support_text(
                support_language,
                "Paste publicly only; do not add local command lines, support JSON, or local Web URLs.",
                "只粘贴到公开 issue；不要附加本地命令行、support JSON 或本地 Web URL。",
            ),
            "",
            support_text(support_language, "Compact package/source identity:", "紧凑版本/源码身份:"),
            support_public_issue_bundle_identity(public_doctor_payload),
            "",
            *support_public_issue_bundle_summary_lines(public_doctor_payload, language=support_language),
            "",
            support_text(support_language, "Redacted doctor --public-json report:", "脱敏 doctor --public-json 报告:"),
            report_json,
        ]
    )


def support_public_issue_bundle_summary_lines(public_doctor_payload: Mapping[str, object], *, language: str = "en") -> list[str]:
    support_language = normalize_support_guidance_language(language)
    summary = _support_public_issue_bundle_summary_payload(public_doctor_payload)
    lines = [
        support_text(support_language, "Public readiness summary:", "公开就绪摘要:"),
        support_text(
            support_language,
            f"- Overall status: {_support_summary_scalar(summary, 'status')}",
            f"- 整体状态: {_support_summary_scalar(summary, 'status')}",
        ),
    ]
    axes = summary.get("readiness_axes")
    if isinstance(axes, list) and axes:
        lines.append(support_text(support_language, "- Readiness axes:", "- 就绪轴:"))
        for axis in axes:
            if not isinstance(axis, Mapping):
                continue
            lines.append(f"  - {_support_summary_axis_line(axis, language=support_language)}")
    else:
        lines.append(
            support_text(
                support_language,
                f"- Project directory: {_support_summary_scalar(summary, 'project_directory_status')}",
                f"- 项目目录: {_support_summary_scalar(summary, 'project_directory_status')}",
            )
        )

    ready_action_kinds = _support_summary_string_list(summary.get("next_action_ready_now_kinds"))
    blocked_action_lines = _support_summary_blocked_action_lines(summary, language=support_language)
    if ready_action_kinds:
        lines.append(
            support_text(
                support_language,
                f"- Ready next action kinds: {', '.join(ready_action_kinds)}",
                f"- 当前可执行的下一步类型: {', '.join(ready_action_kinds)}",
            )
        )
    if blocked_action_lines:
        lines.append(support_text(support_language, "- Blocked next action kinds:", "- 被阻止的下一步类型:"))
        lines.extend(f"  - {line}" for line in blocked_action_lines)
    return lines


def _support_public_issue_bundle_summary_payload(public_doctor_payload: Mapping[str, object]) -> Mapping[str, object]:
    public_summary = public_doctor_payload.get("diagnose_doctor_public_summary")
    if isinstance(public_summary, Mapping):
        return public_summary
    return public_doctor_payload


def _support_summary_axis_line(axis: Mapping[str, object], *, language: str) -> str:
    axis_name = _support_summary_scalar(axis, "axis")
    axis_status = _support_summary_scalar(axis, "status")
    details: list[str] = []
    blockers = _support_summary_string_list(axis.get("blockers"))
    if blockers:
        details.append(support_text(language, f"blockers: {', '.join(blockers)}", f"阻塞: {', '.join(blockers)}"))
    recovery_actions = _support_summary_string_list(axis.get("recovery_actions"))
    if recovery_actions:
        details.append(support_text(language, f"recovery: {', '.join(recovery_actions)}", f"恢复: {', '.join(recovery_actions)}"))
    detail_text = f" ({'; '.join(details)})" if details else ""
    return f"{axis_name}: {axis_status}{detail_text}"


def _support_summary_blocked_action_lines(summary: Mapping[str, object], *, language: str) -> list[str]:
    blocked_action_kinds = _support_summary_string_list(summary.get("next_action_blocked_kinds"))
    blockers_by_kind = summary.get("next_action_command_blockers")
    blockers_mapping = blockers_by_kind if isinstance(blockers_by_kind, Mapping) else {}
    lines: list[str] = []
    for kind in blocked_action_kinds:
        blockers = _support_summary_string_list(blockers_mapping.get(kind))
        if blockers:
            lines.append(support_text(language, f"{kind} (blockers: {', '.join(blockers)})", f"{kind} (阻塞: {', '.join(blockers)})"))
        else:
            lines.append(kind)
    return lines


def _support_summary_scalar(summary: Mapping[str, object], key: str, default: str = "unknown") -> str:
    value = summary.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int | float):
        return str(value)
    text = str(value).strip()
    return text or default


def _support_summary_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            items.append(text)
    return items


def support_public_issue_bundle_identity(public_doctor_payload: Mapping[str, object]) -> str:
    package = public_doctor_payload.get("package") if isinstance(public_doctor_payload.get("package"), Mapping) else {}
    name = str(package.get("name") or "loopora").strip() or "loopora"
    version = str(package.get("version") or "unknown").strip() or "unknown"
    revision = str(package.get("source_revision") or "").strip()
    status = str(package.get("source_tree_status") or "").strip()
    source = f"source {revision}" if revision and revision != "unknown" else "source unknown"
    if status and status != "unknown" and source != "source unknown":
        source = f"{source} {status}"
    return f"{name} {version} ({source})"

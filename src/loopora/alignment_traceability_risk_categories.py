from __future__ import annotations

"""Fake-done and evidence-preference traceability categories for Agent candidates."""

import re


def agent_candidate_fake_done_categories(task_text: str, *, require_explicit_marker: bool = True) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    explicit_fake_done_markers = (
        r"\bfake[- ]?(?:done|completion)\b",
        r"\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b",
        r"\b(?:looks|appears|seems)\s+(?:done|complete|finished|working)\b",
        r"\b(?:only|just|merely)\s+(?:a\s+)?(?:claim|screenshot|download|export|mock|stub|static)\b",
        r"\bhappy[- ]path[- ]only\b",
        r"假完成",
        r"看起来.{0,12}(?:完成|可用|通过)",
        r"(?:不能|不可|不要|不得).{0,16}(?:通过|算完成|收尾)",
    )
    if require_explicit_marker and not any(re.search(pattern, text, re.I) for pattern in explicit_fake_done_markers):
        return []
    categories: list[tuple[str, str]] = [
        (
            "fake-done/blocking",
            r"\bfake[- ]?(?:done|completion)\b|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|假完成|阻断|不得通过|不能通过",
        ),
    ]
    category_patterns = (
        (
            "permission/audit",
            r"\b(?:permission|permissions|authorization|auth|access|audit|auditing|audit[- ]?log)\b|权限|授权|审计|日志",
            r"\b(?:permission|permissions|authorization|auth|access|audit|auditing|audit[- ]?log)\b|权限|授权|审计|日志",
        ),
        (
            "download/export-only",
            r"\b(?:csv|download|export|file)\b|下载|导出|文件",
            r"\b(?:csv|download|export|file)\b|下载|导出|文件",
        ),
        (
            "payment/refund/billing",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过).{0,80}"
                r"(?:\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账)"
                r"|(?:\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账)"
                r".{0,80}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过)"
            ),
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|不得通过|不能通过).{0,80}"
                r"(?:\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账)"
                r"|(?:\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账)"
                r".{0,80}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|不得通过|不能通过)"
            ),
        ),
        (
            "data/export/report",
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过).{0,80}"
                r"(?:\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板)"
                r"|(?:\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板)"
                r".{0,80}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|阻断|不得通过|不能通过)"
            ),
            (
                r"(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|不得通过|不能通过).{0,80}"
                r"(?:\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板)"
                r"|(?:\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板)"
                r".{0,80}(?:\bfake[- ]?(?:done|completion)\b(?!\s+findings)|\b(?:do not|don't|cannot|can't|must not|never)\s+pass\b|"
                r"\b(?:only|just|merely)\b|假完成|不得通过|不能通过)"
            ),
        ),
        (
            "visual/polish/screenshot-only",
            r"\b(?:screenshot|visual|polish|ui|pretty|polished-looking)\b|截图|视觉|界面|美化|漂亮",
            r"\b(?:screenshot|visual|polish|ui|pretty|polished-looking)\b|截图|视觉|界面|美化|漂亮",
        ),
        (
            "claim/narrative-only",
            r"\b(?:claim|claims|narrative|story|description|self[- ]?report)\b|声明|叙事|描述|自述",
            r"\b(?:claim|claims|narrative|story|description|self[- ]?report)\b|声明|叙事|描述|自述",
        ),
        (
            "happy-path-only",
            r"\bhappy[- ]?path\b|主路径|快乐路径",
            r"\bhappy[- ]?path\b|主路径|快乐路径",
        ),
        (
            "mock/static/stub-only",
            r"\b(?:mock|stub|static|placeholder|fixture)\b|模拟|桩|静态|占位",
            r"\b(?:mock|stub|static|placeholder|fixture)\b|模拟|桩|静态|占位",
        ),
        (
            "accessibility/i18n",
            r"\b(?:accessibility|a11y|screen[- ]?reader|keyboard|aria|focus|wcag|locale|locali[sz]ation|i18n|translation|language)\b|无障碍|可访问|读屏|屏幕阅读器|键盘|焦点|多语言|国际化|本地化|翻译|语言",
            r"\b(?:accessibility|a11y|screen[- ]?reader|keyboard|aria|focus|wcag|locale|locali[sz]ation|i18n|translation|language)\b|无障碍|可访问|读屏|屏幕阅读器|键盘|焦点|多语言|国际化|本地化|翻译|语言",
        ),
    )
    categories.extend(
        (label, bundle_pattern)
        for label, task_pattern, bundle_pattern in category_patterns
        if re.search(task_pattern, text, re.I)
    )
    return categories


def agent_candidate_evidence_preference_categories(
    task_text: str,
    *,
    require_explicit_marker: bool = True,
) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    explicit_evidence_markers = (
        r"\b(?:evidence|proof|verification|verify)\b.{0,80}\b(?:must|should|prefer|include|require|needs?)\b",
        r"\b(?:must|should|prefer|include|require|needs?)\b.{0,80}\b(?:evidence|proof|verification|verify)\b",
        r"证据.{0,24}(?:必须|需要|优先|包括|包含)",
        r"(?:必须|需要|优先|包括|包含).{0,24}(?:证据|证明|验证)",
    )
    if require_explicit_marker and not any(re.search(pattern, text, re.I) for pattern in explicit_evidence_markers):
        return []
    categories: list[tuple[str, str]] = [
        (
            "evidence/proof",
            r"\b(?:evidence|proof|verify|verification|verified|proven)\b|证据|证明|验证|已证明",
        ),
    ]
    category_patterns = (
        (
            "browser/journey",
            r"\b(?:browser|playwright|journey|end[- ]?to[- ]?end|e2e)\b|浏览器|旅程|端到端",
        ),
        (
            "command/test",
            r"\b(?:command|cli|script|test|tests|pytest|unit|contract|lint|typecheck)\b|命令|脚本|测试|契约|类型检查",
        ),
        (
            "audit/log",
            r"\b(?:audit|auditing|audit[- ]?log|log|logs|ledger|trace)\b|审计|日志|账本|追踪",
        ),
        (
            "permission/auth",
            r"\b(?:permission|permissions|authorization|auth|access)\b|权限|授权|访问",
        ),
        (
            "payment/refund/billing",
            r"\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账",
        ),
        (
            "data/export/report",
            r"\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板",
        ),
        (
            "artifact/ref",
            r"\b(?:artifact|artifacts|file|files|ref|refs|report)\b|产物|文件|引用|报告",
        ),
        (
            "accessibility/a11y",
            r"\b(?:accessibility|a11y|screen[- ]?reader|keyboard|aria|focus|wcag|axe)\b|无障碍|可访问|读屏|屏幕阅读器|键盘|焦点",
        ),
        (
            "locale/i18n",
            r"\b(?:locale|locali[sz]ation|i18n|translation|language|chinese|english)\b|多语言|国际化|本地化|翻译|语言|中文|英文|英语",
        ),
        (
            "screenshot-is-weak",
            r"\b(?:screenshot|screenshots)\b|截图",
        ),
    )
    categories.extend((label, pattern) for label, pattern in category_patterns if re.search(pattern, text, re.I))
    return categories

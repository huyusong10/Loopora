from __future__ import annotations

"""Accessibility and locale domain-risk patterns."""

ACCESSIBILITY_A11Y_PATTERN = (
    r"\b(?:accessibility|a11y|screen[- ]?reader|keyboard(?:[- ]?navigation)?|aria|"
    r"focus(?:[- ]?(?:trap|order|management))?|wcag|axe|contrast|tab(?:bing)?|"
    r"live[- ]?region|error[- ]?(?:announcement|message))\b"
    r"|无障碍|可访问|读屏|屏幕阅读器|键盘|焦点|焦点陷阱|对比度|错误提示|错误播报"
)


LOCALE_I18N_PATTERN = (
    r"\b(?:locale|locali[sz]ation|i18n|translation|language|chinese|english|"
    r"language[- ]?switch|display[- ]?language|user[- ]?language|ui[- ]?language)\b"
    r"|多语言|国际化|本地化|翻译|语言切换|展示语言|用户语言|界面语言|任务语言|中文|英文|英语"
)


__all__ = (
    "ACCESSIBILITY_A11Y_PATTERN",
    "LOCALE_I18N_PATTERN",
)

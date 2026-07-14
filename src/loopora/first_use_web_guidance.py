from __future__ import annotations

WEB_CREATION_CHOICE_LABEL = "Fit Guide/Web choices"
WEB_CREATION_ROUTE_CONTEXTS = "Web conversation, Plan File import, or manual expert paths"
WEB_CREATION_REVIEW_TARGETS = "evidence, gaps, and verdicts"
WEB_CREATION_CHOICE_SUMMARY = (
    "Fit Guide first, then creation choices: Web conversation outside an Agent session, "
    "Plan File import, or manual expert paths; "
    f"then review {WEB_CREATION_REVIEW_TARGETS}"
)


def open_web_creation_step(*, target: str = "", sentence_case: bool = True) -> str:
    verb = "Open" if sentence_case else "open"
    base = f"{verb} {WEB_CREATION_CHOICE_LABEL} in Web: {WEB_CREATION_CHOICE_SUMMARY}"
    return f"{base}: {target}" if target else f"{base}."


def use_web_creation_step() -> str:
    return f"Use {WEB_CREATION_CHOICE_LABEL} in Web: {WEB_CREATION_CHOICE_SUMMARY} while execution stays in the Agent."


def web_creation_path_note() -> str:
    return (
        f"outside an Agent session, use {WEB_CREATION_ROUTE_CONTEXTS}; "
        "these Web paths do not require a same-Agent project entry or doctor check"
    )

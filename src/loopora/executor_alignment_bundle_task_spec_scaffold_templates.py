from __future__ import annotations

from functools import lru_cache
from typing import Any

from loopora.alignment_guidance import load_alignment_guidance_assets

TASK_SPEC_SCAFFOLD_TEMPLATES_ASSET_NAME = "task-spec-scaffold-templates.json"


def apply_task_spec_scaffold_template_from_asset(
    bundle: dict,
    *,
    template_key: str,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    template = task_spec_scaffold_template(
        template_key,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    bundle["spec"]["markdown"] = template.replace("{task}", task)


def task_spec_scaffold_template(
    template_key: str,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> str:
    language = _task_spec_scaffold_template_language(prefers_chinese=prefers_chinese, display_language=display_language)
    templates = _task_spec_scaffold_templates_asset()
    localized = templates.get(str(template_key or ""))
    if not isinstance(localized, dict):
        raise ValueError(f"missing task spec scaffold template asset: {template_key}")
    return localized.get(language) or localized["en"]


def _task_spec_scaffold_template_language(*, prefers_chinese: bool, display_language: str = "") -> str:
    if prefers_chinese:
        return "zh"
    if str(display_language or "").strip().lower() == "es":
        return "es"
    return "en"


@lru_cache
def _task_spec_scaffold_templates_asset() -> dict[str, dict[str, str]]:
    asset = load_alignment_guidance_assets().task_spec_scaffold_templates
    if not all(isinstance(template_key, str) and isinstance(localized, dict) for template_key, localized in asset.items()):
        raise ValueError(f"{TASK_SPEC_SCAFFOLD_TEMPLATES_ASSET_NAME} must map template keys to locale maps")
    return {template_key: _task_spec_scaffold_template_locales(template_key, localized) for template_key, localized in asset.items()}


def _task_spec_scaffold_template_locales(template_key: str, localized: dict[str, Any]) -> dict[str, str]:
    locales = localized.get("locales")
    if not isinstance(locales, dict):
        raise ValueError(f"{TASK_SPEC_SCAFFOLD_TEMPLATES_ASSET_NAME}.{template_key}.locales must be a locale map")
    required_locales = ("en", "zh", "es")
    if not all(isinstance(locales.get(locale), str) and locales[locale].strip() for locale in required_locales):
        raise ValueError(f"{TASK_SPEC_SCAFFOLD_TEMPLATES_ASSET_NAME}.{template_key}.locales must include en/zh/es templates")
    return {locale: _validated_task_spec_scaffold_template(template_key, locale, locales[locale]) for locale in required_locales}


def _validated_task_spec_scaffold_template(template_key: str, locale: str, template: str) -> str:
    if not template.startswith("# Task"):
        raise ValueError(f"{TASK_SPEC_SCAFFOLD_TEMPLATES_ASSET_NAME}.{template_key}.{locale} must start with # Task")
    if "{task}" not in template:
        raise ValueError(f"{TASK_SPEC_SCAFFOLD_TEMPLATES_ASSET_NAME}.{template_key}.{locale} must include {{task}}")
    return str(template)

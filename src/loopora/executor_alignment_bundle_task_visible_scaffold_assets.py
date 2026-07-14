from __future__ import annotations

from functools import lru_cache
from typing import Any

from loopora.alignment_guidance import load_alignment_guidance_assets

TASK_VISIBLE_SCAFFOLDS_ASSET_NAME = "task-visible-scaffolds.json"


def apply_task_visible_scaffold_from_asset(
    bundle: dict,
    *,
    scaffold_key: str,
    prefers_chinese: bool,
    display_language: str = "",
) -> None:
    scaffold = task_visible_scaffold(
        scaffold_key,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    metadata = bundle.get("metadata") if isinstance(bundle.get("metadata"), dict) else {}
    loop = bundle.get("loop") if isinstance(bundle.get("loop"), dict) else {}
    metadata["name"] = scaffold["metadata_name"]
    metadata["description"] = scaffold["metadata_description"]
    loop["name"] = scaffold["loop_name"]
    bundle["collaboration_summary"] = scaffold["collaboration_summary"]


def apply_task_visible_scaffold_template_from_asset(
    bundle: dict,
    *,
    scaffold_key: str,
    prefers_chinese: bool,
    task: str,
    projection: Any,
) -> None:
    scaffold = task_visible_scaffold(
        scaffold_key,
        prefers_chinese=prefers_chinese,
    )
    context = {
        "task": task,
        "success_focus": str(projection.success_focus),
        "fake_done_focus": str(projection.fake_done_focus),
        "evidence_focus": str(projection.evidence_focus),
    }
    metadata = bundle.get("metadata") if isinstance(bundle.get("metadata"), dict) else {}
    loop = bundle.get("loop") if isinstance(bundle.get("loop"), dict) else {}
    metadata["name"] = scaffold["metadata_name"]
    metadata["description"] = scaffold["metadata_description"]
    loop["name"] = scaffold["loop_name"]
    bundle["collaboration_summary"] = scaffold["collaboration_summary"].format_map(context)
    bundle["spec"]["markdown"] = scaffold["spec_markdown"].format_map(context)


def task_visible_scaffold(
    scaffold_key: str,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> dict[str, str]:
    language = _task_visible_scaffold_language(prefers_chinese=prefers_chinese, display_language=display_language)
    scaffolds = _task_visible_scaffolds_asset()
    localized = scaffolds.get(str(scaffold_key or ""))
    if not isinstance(localized, dict):
        raise ValueError(f"missing task visible scaffold asset: {scaffold_key}")
    return localized.get(language) or localized["en"]


def _task_visible_scaffold_language(*, prefers_chinese: bool, display_language: str = "") -> str:
    if prefers_chinese:
        return "zh"
    if str(display_language or "").strip().lower() == "es":
        return "es"
    return "en"


@lru_cache
def _task_visible_scaffolds_asset() -> dict[str, dict[str, dict[str, str]]]:
    asset = load_alignment_guidance_assets().task_visible_scaffolds
    if not all(isinstance(scaffold_key, str) and isinstance(localized, dict) for scaffold_key, localized in asset.items()):
        raise ValueError(f"{TASK_VISIBLE_SCAFFOLDS_ASSET_NAME} must map scaffold keys to locale maps")
    return {scaffold_key: _task_visible_scaffold_locales(scaffold_key, localized) for scaffold_key, localized in asset.items()}


def _task_visible_scaffold_locales(scaffold_key: str, localized: dict[str, Any]) -> dict[str, dict[str, str]]:
    required_locales = ("en", "zh", "es")
    if not all(isinstance(localized.get(locale), dict) for locale in required_locales):
        raise ValueError(f"{TASK_VISIBLE_SCAFFOLDS_ASSET_NAME}.{scaffold_key} must include en/zh/es scaffolds")
    return {locale: _task_visible_scaffold_fields(scaffold_key, locale, localized[locale]) for locale in required_locales}


def _task_visible_scaffold_fields(scaffold_key: str, locale: str, fields: dict[str, Any]) -> dict[str, str]:
    required_fields = ("metadata_name", "metadata_description", "loop_name", "collaboration_summary")
    if not all(isinstance(fields.get(field), str) and fields[field].strip() for field in required_fields):
        raise ValueError(f"{TASK_VISIBLE_SCAFFOLDS_ASSET_NAME}.{scaffold_key}.{locale} must include visible scaffold strings")
    rendered_fields = {field: str(fields[field]) for field in required_fields}
    if "spec_markdown" in fields:
        if not isinstance(fields["spec_markdown"], str) or not fields["spec_markdown"].strip():
            raise ValueError(f"{TASK_VISIBLE_SCAFFOLDS_ASSET_NAME}.{scaffold_key}.{locale}.spec_markdown must be a string")
        rendered_fields["spec_markdown"] = str(fields["spec_markdown"])
    return rendered_fields

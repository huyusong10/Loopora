from __future__ import annotations

from functools import lru_cache

from loopora.alignment_guidance import alignment_guidance_dir
from loopora.executor_alignment_bundle_governance_fixture import (
    alignment_bundle_governance_role_snippet,
    alignment_bundle_governance_sentence,
)


def alignment_bundle_yaml(workdir: str) -> str:
    replacements = {
        "workdir": workdir,
        "local_governance_sentence": alignment_bundle_governance_sentence(workdir, locale="en"),
        "builder_governance": alignment_bundle_governance_role_snippet(workdir, role="builder", locale="en"),
        "inspector_governance": alignment_bundle_governance_role_snippet(workdir, role="inspector", locale="en"),
        "gatekeeper_governance": alignment_bundle_governance_role_snippet(workdir, role="gatekeeper", locale="en"),
    }
    return _render_base_bundle_template(replacements)


def _render_base_bundle_template(replacements: dict[str, str]) -> str:
    rendered = _base_bundle_template()
    for key, value in replacements.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    if "{{" in rendered or "}}" in rendered:
        raise ValueError("unresolved base bundle template placeholder")
    return rendered


@lru_cache(maxsize=1)
def _base_bundle_template() -> str:
    return (alignment_guidance_dir() / "base-bundle.yml").read_text(encoding="utf-8")

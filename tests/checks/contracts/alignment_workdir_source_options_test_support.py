from __future__ import annotations

from pathlib import Path

from loopora.bundles import bundle_to_yaml, load_bundle_text
from loopora.service_alignment_prompting import AlignmentPromptBuildContext, build_alignment_prompt


READY_POLICY_TEXT = (
    "Accept minor polish gaps only when they are explicitly named and tracked as an owned follow-up; "
    "fail closed on unproven primary-flow behavior or weak verification evidence."
)
WEAK_READY_POLICY_TEXT = "Some risk is fine."


def alignment_prompt(session: dict, *, mode: str = "normal") -> str:
    return build_alignment_prompt(AlignmentPromptBuildContext(), session, mode=mode)


def weaken_ready_bundle_text(bundle_path: Path) -> None:
    bundle_text = bundle_path.read_text(encoding="utf-8")
    assert READY_POLICY_TEXT in bundle_text
    bundle_path.write_text(bundle_text.replace(READY_POLICY_TEXT, WEAK_READY_POLICY_TEXT), encoding="utf-8")


def weaken_ready_bundle_markdown(bundle_path: Path) -> None:
    bundle = load_bundle_text(bundle_path.read_text(encoding="utf-8"))
    assert READY_POLICY_TEXT in bundle["spec"]["markdown"]
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(READY_POLICY_TEXT, WEAK_READY_POLICY_TEXT)
    bundle_path.write_text(bundle_to_yaml(bundle), encoding="utf-8")


def rewrite_bundle_workdir(bundle_path: Path, workdir: Path) -> None:
    bundle = load_bundle_text(bundle_path.read_text(encoding="utf-8"))
    bundle["loop"]["workdir"] = str(workdir.resolve())
    bundle_path.write_text(bundle_to_yaml(bundle), encoding="utf-8")

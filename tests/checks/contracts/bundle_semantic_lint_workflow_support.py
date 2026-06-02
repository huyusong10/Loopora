from __future__ import annotations

from pathlib import Path

from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml


def load_default_alignment_bundle(sample_workdir: Path) -> dict:
    return load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))


def add_repair_guide_flow(bundle: dict) -> dict:
    bundle["role_definitions"].append(
        {
            "key": "repair-guide",
            "name": "Repair Direction Guide",
            "description": "Turns inspection evidence into a focused repair direction.",
            "archetype": "guide",
            "prompt_ref": "repair-guide.md",
            "prompt_markdown": """---
version: 1
archetype: guide
---

Use the inspection evidence to narrow the next Builder step. Leave a handoff that names the repair direction, the evidence behind it, and the scope that must not expand.""",
            "posture_notes": "Narrow the repair target from review evidence instead of offering broad advice.",
            "executor_kind": "codex",
            "executor_mode": "preset",
            "command_cli": "",
            "command_args_text": "",
            "model": "",
            "reasoning_effort": "",
        }
    )
    bundle["workflow"]["roles"].append({"id": "repair_guide", "role_definition_key": "repair-guide"})
    gatekeeper_step = bundle["workflow"]["steps"][-1]
    bundle["workflow"]["steps"].insert(
        -1,
        {
            "id": "repair_guide_step",
            "role_id": "repair_guide",
            "inputs": {
                "handoffs_from": ["contract_inspection_step", "evidence_inspection_step"],
                "evidence_query": {"archetypes": ["inspector"], "limit": 12},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
    )
    gatekeeper_step["inputs"]["handoffs_from"].append("repair_guide_step")
    gatekeeper_step["inputs"]["evidence_query"]["archetypes"].append("guide")
    return bundle


def make_contract_inspector_custom_review(bundle: dict) -> None:
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    contract_role = role_by_key["contract-inspector"]
    contract_role["archetype"] = "custom"
    contract_role["prompt_markdown"] = contract_role["prompt_markdown"].replace(
        "archetype: inspector",
        "archetype: custom",
    )
    contract_role["prompt_markdown"] += (
        "\n\n      Act as a read-only specialized Custom reviewer for contract evidence; do not edit files, and leave a focused handoff."
    )
    contract_role["posture_notes"] += " As a low-permission Custom reviewer, provide only specialized contract review signal."

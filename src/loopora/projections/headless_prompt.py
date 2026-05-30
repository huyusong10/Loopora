from __future__ import annotations

from loopora.kernel import StepInstruction


def headless_prompt_projection(instruction: StepInstruction) -> str:
    target_lines = "\n".join(f"- {target_id}" for target_id in instruction.evidence_scope.target_ids)
    return "\n".join(
        line
        for line in (
            f"Run: {instruction.run_id}",
            f"Step: {instruction.step_id}",
            f"Role: {instruction.role.name or instruction.role.id}",
            "",
            instruction.objective,
            "",
            "Evidence targets:",
            target_lines or "- none declared",
            "",
            f"Contract: {instruction.contract_ref}",
        )
        if line is not None
    )

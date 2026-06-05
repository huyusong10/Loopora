from __future__ import annotations

import re

from loopora.cli_summary_helpers import clip_inline as _clip_inline


def validation_repair_hints(error: str) -> list[str]:
    text = str(error or "")
    hints: list[str] = _task_projection_repair_hints(text)
    hints.extend(_semantic_lint_repair_hints(text))
    for patterns, hint in _VALIDATION_REPAIR_HINT_RULES:
        if any(pattern in text for pattern in patterns):
            hints.append(hint)
    deduped: list[str] = []
    for hint in hints:
        if hint not in deduped:
            deduped.append(hint)
    return deduped[:8]


def _semantic_lint_repair_hints(error: str) -> list[str]:
    issues = _semantic_lint_issues(error)
    hints: list[str] = []
    for issue in issues:
        hint = _semantic_lint_issue_hint(issue)
        if hint:
            hints.append(hint)
    return hints


def _semantic_lint_issues(error: str) -> list[str]:
    text = str(error or "").strip()
    if not text:
        return []
    prefix = "bundle semantic lint failed:"
    if prefix not in text:
        return []
    text = text.split(prefix, 1)[1]
    return [item.strip() for item in text.split(";") if item.strip()]


_SEMANTIC_LINT_HINT_RULES = (
    (
        ("collaboration_summary must explain why this task needs multi-round loopora governance",),
        "explain in collaboration_summary what later evidence, reviews, handoffs, or GateKeeper rounds add beyond one Agent pass",
    ),
    (
        ("collaboration_summary must explain the governance story",),
        "rewrite collaboration_summary with the concrete task, evidence flow, blockers, and GateKeeper closure",
    ),
    (("collaboration_summary must mention evidence",), "mention the evidence, proof, handoff, or blocker path in collaboration_summary"),
    (("collaboration_summary must explain gatekeeper",), "describe the GateKeeper or final judgment posture in collaboration_summary"),
    (
        ("spec must include residual risk guidance",),
        "add # Residual Risk guidance naming accepted risks, owners/follow-ups, or fail-closed conditions",
    ),
    (
        ("spec residual risk guidance must name accepted risk handling or fail closed",),
        "add # Residual Risk guidance naming accepted risks, owners/follow-ups, or fail-closed conditions",
    ),
    (
        ("alignment bundle must project task verdict evidence into proven, weak, unproven, blocking, and residual risk buckets",),
        "add one unwrapped line `Buckets: Proven, Weak, Unproven, Blocking, Residual risk.` to collaboration_summary, Evidence Preferences, Inspector posture, and GateKeeper closure",
    ),
    (
        ("alignment bundle must convert project-local governance markers into builder reading",),
        "add local governance responsibility sentences near the marker text: Builder reads and follows applicable project-local governance before edits; Inspector verifies related design/tests/governance evidence; GateKeeper treats skipped governance or missing expected validation as Weak, Unproven, or Blocking",
    ),
    (
        ("web alignment bundles must use gatekeeper completion_mode",),
        "set loop.completion_mode to gatekeeper and include a finishing GateKeeper role/step",
    ),
    (
        ("workflow.collaboration_intent must explain evidence flow",),
        "rewrite workflow.collaboration_intent to name evidence flow, GateKeeper closure, and weak-evidence or fake-done exposure",
    ),
    (
        ("workflow.collaboration_intent must explain the task-specific judgment order",),
        "rewrite workflow.collaboration_intent to explain the task-specific Builder, review, and GateKeeper order",
    ),
    (
        ("must query", "inputs.evidence_query"),
        "add inputs.evidence_query to the workflow step named in the lint issue so it can see required evidence",
    ),
    (
        ("must include", "inputs.handoffs_from"),
        "add inputs.handoffs_from to the workflow step named in the lint issue so upstream handoffs are explicit",
    ),
    (
        ("must name", "inputs.handoffs_from"),
        "add inputs.handoffs_from to the workflow step named in the lint issue so upstream handoffs are explicit",
    ),
    (
        ("must declare inputs.iteration_memory",),
        "add inputs.iteration_memory=summary_only where the lint issue names cross-iteration evidence flow",
    ),
    (
        ("must use inputs.iteration_memory=summary_only",),
        "set inputs.iteration_memory=summary_only for the workflow step named in the lint issue",
    ),
    (
        ("role_definition", "must use a task-specific role name"),
        "rename generic role_definitions to task-specific role names tied to this task's evidence responsibilities",
    ),
    (
        ("role_definition", "must include task-scoped posture_notes"),
        "add task-scoped posture_notes explaining each role's evidence responsibility",
    ),
    (
        ("role_definitions must have distinct task evidence responsibilities",),
        "split overlapping review roles so each role_definition owns a distinct task evidence responsibility",
    ),
    (("markdown-fenced output",), "save the candidate as one raw YAML document without markdown fences"),
    (("must start with version: 1",), "make the candidate YAML start with version: 1"),
    (
        ("metadata.source_bundle_id",),
        "remove lineage metadata such as metadata.source_bundle_id and metadata.revision from the final candidate",
    ),
    (
        ("metadata.revision",),
        "remove lineage metadata such as metadata.source_bundle_id and metadata.revision from the final candidate",
    ),
    (
        ("task-scoped, not personality memory",),
        "rewrite the bundle as a task-scoped Loop instead of global preferences or personality memory",
    ),
    (
        ("must not present prompt pack",),
        "reframe the bundle as Loopora governance, not a prompt pack, role zoo, loop script, benchmark grinder, or chat wrapper",
    ),
    (
        ("must not claim a single pass",),
        "remove claims that one pass, direct chat, or no-new-evidence work is sufficient; define evidence and GateKeeper value",
    ),
)


def _semantic_lint_issue_hint(issue: str) -> str:
    lower = issue.lower()
    section = _missing_spec_section(issue)
    if section:
        return f"add # {section} bullets that make the task judgment reviewable and runnable"
    for needles, hint in _SEMANTIC_LINT_HINT_RULES:
        if all(needle in lower for needle in needles):
            return hint
    return "address semantic lint issue in the plan file: " + _clip_inline(issue, 180)


def _missing_spec_section(issue: str) -> str:
    match = re.search(r"spec must include at least one (?P<section>Done When|Success Surface|Fake Done|Evidence Preferences) bullet", issue)
    if not match:
        return ""
    return str(match.group("section") or "").strip()


def _task_projection_repair_hints(error: str) -> list[str]:
    pattern = re.compile(
        r"agent-first candidate must project (?:the )?(?:explicit )?host Agent "
        r"(?P<area>[^:\n]+?) into runnable surfaces:\s*missing\s+(?P<terms>[^;.\n]+)"
    )
    hints: list[str] = []
    for match in pattern.finditer(str(error or "")):
        terms = [term.strip() for term in match.group("terms").split(",") if term.strip()]
        if not terms:
            continue
        area = str(match.group("area") or "task summary").strip()
        if area == "task summary":
            hints.extend(
                [
                    "add these missing task objects from --message to runnable plan surfaces: " + ", ".join(terms[:8]),
                    "include those objects in spec success criteria, role responsibilities, workflow intent, and evidence preferences",
                ]
            )
            continue
        hints.extend(
            [
                f"add these missing {area} categories from --message to runnable plan surfaces: " + ", ".join(terms[:8]),
                _task_projection_area_repair_hint(area),
            ]
        )
    return list(dict.fromkeys(hints))


def _task_projection_area_repair_hint(area: str) -> str:
    normalized = str(area or "").strip().lower()
    hints = {
        "success criteria": "include those categories in spec Done When/Success Surface, role responsibilities, workflow intent, evidence preferences, and GateKeeper closure",
        "fake-done risks": "include those risks in spec Fake Done, Inspector blocking checks, GateKeeper pass/block policy, and evidence expectations",
        "evidence preferences": "include those evidence modes in spec Evidence Preferences, Inspector responsibilities, workflow handoffs, and GateKeeper closure",
        "judgment tradeoffs": "include those tradeoffs in collaboration summary, role postures, workflow sequencing, and GateKeeper decision policy",
        "execution strategy": "include those strategy categories in workflow order, role responsibilities, next-pass priorities, and GateKeeper repair direction",
        "residual-risk policy": "include those residual-risk rules in spec Residual Risk, GateKeeper pass/block policy, and owner/follow-up semantics",
    }
    return hints.get(
        normalized,
        "include those categories in spec, role responsibilities, workflow intent, evidence rules, and GateKeeper closure",
    )


_VALIDATION_REPAIR_HINT_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("invalid bundle YAML", "unacceptable character"),
        "remove hidden YAML control characters such as NUL bytes from the plan file, especially inside quoted ids",
    ),
    (
        ("invalid bundle YAML", "#x0000"),
        "remove hidden YAML control characters such as NUL bytes from the plan file, especially inside quoted ids",
    ),
    (
        ("invalid bundle YAML", "special characters are not allowed"),
        "remove hidden YAML control characters such as NUL bytes from the plan file, especially inside quoted ids",
    ),
    (("metadata.name is required",), "add metadata.name so the plan has a stable reviewable identity"),
    (("spec is required", "spec."), "fill the spec with the concrete task contract, done conditions, risks, and evidence expectations"),
    (
        ("role_definitions", "workflow"),
        "include role_definitions and workflow steps so the Loop can run through Builder, reviewers, and GateKeeper",
    ),
    (("spec Task must describe the concrete user-facing task",), "make # Task name the concrete user-facing outcome, not only internal governance language"),
    (("must follow Chinese user language",), "keep user-facing plan names, spec prose, role names, and posture notes in the user's language"),
    (("host Agent task summary", "project the host Agent task summary"), "project the task objects from --message into spec, roles, workflow intent, and evidence rules"),
    (("evidence preferences", "explicit host Agent evidence"), "compile required evidence modes into runnable surfaces, not only the CLI summary"),
    (
        ("Loopora fit", "one-off", "no-new-evidence"),
        "explain what later rounds add: new evidence, handoffs, GateKeeper judgment, or residual-risk tracking",
    ),
)

from __future__ import annotations

from pathlib import Path

from alignment_test_support import _bundle_invocation_dir, _confirm_alignment_agreement


def test_alignment_prompt_and_source_sync_follow_user_language(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    (sample_workdir / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
    (sample_workdir / "design").mkdir()
    (sample_workdir / "design" / "README.md").write_text("# Design\n", encoding="utf-8")
    (sample_workdir / "tests").mkdir()

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="请帮我生成一个中文任务的循环方案。",
    )
    session = _confirm_alignment_agreement(service, created["id"])
    artifact_root = Path(session["artifact_dir"])
    prompt_text = (_bundle_invocation_dir(artifact_root) / "prompt.md").read_text(encoding="utf-8")

    assert prompt_text.index("## Loopora Product Primer") < prompt_text.index("## Agent-Led Compiler Policy")
    assert "## Embedded Skill" not in prompt_text
    for snippet in (
        "User language hint: `Follow the dominant substantive task language",
        "Assume you know nothing about Loopora except what is embedded below.",
        "internal Web compiler",
        "Agent drives semantic conversation; Loopora backend decides",
        "## Active Compiler Gate",
        "Current compiler gate: confirmed agreement",
        "Allowed candidate phase: bundle, or clarifying if a human-required judgment gap is discovered",
        "The Agent drives the semantic conversation. Loopora backend only accepts or rejects candidate phases.",
        "Before asking the user, answer anything you can from the transcript",
        "Follow the current decision branch",
        "Agent-led conversation is not a questionnaire",
        "branch-aware pressure testing",
        "answer everything you can from the transcript",
        "Follow the user's chosen or corrected branch",
        "`decision_options`",
        "state your current best judgment first",
        "Repairable issues may be fixed by the Agent",
        "Human-required issues must go back to conversation",
        "execution strategy, residual-risk policy, judgment tradeoff, local-governance responsibility",
        "execution priorities, residual-risk policy, local-governance responsibility",
        "Loopora Product Primer",
        "local-first platform for composing human-shaped governance loops",
        "human-in-the-loop -> human-shaped loop",
        "Loopora fit gate",
        "one Agent pass plus one human review",
        "direct answer or one-off task handling",
        "survive this chat as a run-owned, exportable, auditable contract",
        "new proof / artifact / handoff / observation / verdict context later rounds will create",
        "run-owned/exportable/auditable contract",
        "`readiness_checklist`: booleans for `loop_fit`, `task_scope`, `success_surface`, `fake_done_risks`, `evidence_preferences`, `execution_strategy`, `residual_risk_policy`, `judgment_tradeoffs`, `local_governance`",
        "`residual_risk_policy` must explain which remaining risks may be accepted and who or what follow-up / acceptance path owns them",
        "`judgment_tradeoffs` must capture a concrete preference order or contrast",
        "`local_governance` must explain whether project-local governance markers affect this Loop",
        "judgment structure quality × evidence feedback quality × error exposure speed",
        "prompt pack, role zoo, loop script, benchmark grinder",
        "global persona, or permanent preferences",
        "Project the confirmed working agreement into the bundle surfaces",
        "execution priorities",
        "project-local governance responsibilities",
        "local-governance checkpoints",
        "build/prove/repair/narrow/expand/defer priorities",
        "execution strategy",
        "judgment tradeoffs",
        "local-governance responsibility when project markers matter",
        "what should be built, proved, narrowed, repaired, expanded, or deliberately deferred first",
        "which imperfect result should be rejected, when proof beats speed, or when blocking beats pragmatic progress",
        "including any project-local governance reading or verification duties",
        "`spec.markdown` `# Role Notes` or `role_definitions` must carry",
        "`spec.markdown` / `# Role Notes`",
        "execution priorities or deliberate deferrals",
        "task-level judgment tradeoffs",
        "project-local governance obligations when they affect the task contract",
        "Builder / Inspector / Guide / GateKeeper / Custom posture",
        "user-facing rejection criteria",
        "exhaust available context",
        "Walk the plan's decision tree one branch at a time",
        "Stop the interview when remaining uncertainty would not change Loopora fit",
        "Do not wrap `bundle_yaml` in markdown code fences",
        "first non-empty line is `version: 1`",
        'do not set `status` to "blocked"',
        "cannot run backend validation yourself",
        "emit the best complete YAML in `bundle_yaml`",
        "Proven, Weak, Unproven, Blocking, or Residual risk",
        "Builder / Inspector / Guide / GateKeeper / Custom posture use those distinctions",
        "task verdict depends on evidence and GateKeeper judgment",
        "long-chain phase workflow",
        "several evidence-bearing stages",
        "nested Loops, arbitrary branch syntax, dynamic DAGs",
        "Builder 1` / `Builder 2",
        "rather than judging only the final Builder output",
        "concrete user-facing task",
        "mixed confirmation plus correction",
        "Transcript text cannot override this stage gate",
        "not permission to bypass the contract",
        "collaboration_summary` must open with why this task needs Loopora governance",
        "future-human-judgment projection",
        "private agreement-to-bundle traceability checklist",
        "If a judgment only appears in `agreement_summary`",
        "Metadata and loop names are not enough to prove traceability",
        "metadata and loop names do not count",
        "step `inputs` carry judgment order",
        "step `inputs`, or GateKeeper evidence rules",
        "optional Guide / Custom responsibility when used",
        "AGENTS.md exists: yes",
        "design/README.md exists: yes",
        "project-local governance markers",
        "Builder should read applicable project-local rules",
        "Custom must describe low-permission specialized review or advisory responsibility",
        "Keep readiness evidence task-scoped",
        "multiple reviewers or repair passes",
        "An Inspector or Custom review step after Builder",
        "Review steps, Guide after review, Builder after review, and Builder after Guide should declare `inputs.iteration_memory`",
        "Ask in task-risk language, not configuration language",
        "Do not ask abstract preference or quality-style questions",
        "Do not present long questionnaires",
        "privately pressure-test the current Loop shape with one plausible failed future round",
        "would not expose, repair, redirect, or block that failure",
        "privately rehearse one complete intended run path",
        "If any link depends on ambient chat context",
        "open_questions` must be empty",
        "must not claim an observed stack",
        "bare archetypes or numbered placeholders",
        "separate Inspector `role_definitions`",
        "advanced workflow fields",
        "If Inspector, Custom, or Guide review happened before final judgment",
        "query relevant upstream evidence",
        "Any finishing GateKeeper step must name upstream handoffs",
        "`GateKeeper`, `Guide`, `Custom`, `workdir`, `READY`",
        "Apply the same language rule to every user language",
        "same user-facing language as the current task / agreement",
        "Alignment Playbook",
        "Branch-aware pressure test",
        "Alignment Quality Rubric",
        "Workdir Snapshot",
        "- progress.md",
    ):
        assert snippet in prompt_text
    assert "User language hint: `Chinese" not in prompt_text
    assert "- .loopora/" not in prompt_text
    synced = service.sync_alignment_bundle_from_file(session["id"])

    assert synced["ok"] is True
    refreshed = service.get_alignment_session(session["id"])
    assert "已重新读取 bundle.yml" in refreshed["transcript"][-1]["content"]

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

from loopora.settings import app_home


def _bundle_yaml(workdir: Path, *, collaboration_summary: str = "Prefer evidence before rushing forward.") -> str:
    return (
        dedent(
            f"""
        version: 1
        metadata:
          name: "Guided Inspect First"
          description: "Bundle created from task-scoped alignment."
        collaboration_summary: |
          {collaboration_summary}
        loop:
          name: "Guided Inspect First"
          workdir: "{workdir}"
          completion_mode: "gatekeeper"
          executor_kind: "codex"
          executor_mode: "preset"
          model: "gpt-5.4"
          reasoning_effort: "medium"
          max_iters: 4
          max_role_retries: 1
          delta_threshold: 0.005
          trigger_window: 2
          regression_window: 2
        spec:
          markdown: |
            # Task

            Ship the requested behavior without creating brittle structure.

            # Done When

            - The primary experience completes successfully.
            - The edge path stays safe and understandable.

            # Guardrails

            - Keep changes focused.

            # Success Surface

            - The implementation stays maintainable for the next round.

            # Fake Done

            - A patch that only fixes the happy path while leaving obvious duplication behind.

            # Evidence Preferences

            - Prefer real project commands and reproducible tests over screenshots alone.

            # Residual Risk

            Minor copy polish can wait, but structural regressions should fail closed.

            # Role Notes

            ## Builder Notes

            Keep the implementation narrow and verifiable.
        role_definitions:
          - key: "builder"
            name: "Focused Builder"
            description: "Implements the smallest maintainable change."
            archetype: "builder"
            prompt_markdown: |
              ---
              version: 1
              archetype: builder
              ---

              Build carefully and keep the repo coherent.
            posture_notes: |
              Treat maintainability debt as first-class in this task.
          - key: "inspector"
            name: "Evidence Inspector"
            description: "Collects reproducible evidence."
            archetype: "inspector"
            prompt_markdown: |
              ---
              version: 1
              archetype: inspector
              ---

              Collect evidence conservatively.
            posture_notes: |
              Prefer project-owned commands and primary artifacts.
          - key: "gatekeeper"
            name: "Conservative GateKeeper"
            description: "Fails closed when evidence is weak."
            archetype: "gatekeeper"
            prompt_markdown: |
              ---
              version: 1
              archetype: gatekeeper
              ---

              Judge from direct evidence only.
            posture_notes: |
              Do not pass brittle fixes just because the happy path moved.
        workflow:
          version: 1
          preset: "inspect_first"
          collaboration_intent: "Start with evidence, then commit to one repair slice."
          roles:
            - id: "inspector"
              role_definition_key: "inspector"
            - id: "builder"
              role_definition_key: "builder"
            - id: "gatekeeper"
              role_definition_key: "gatekeeper"
          steps:
            - id: "inspector_step"
              role_id: "inspector"
            - id: "builder_step"
              role_id: "builder"
            - id: "gatekeeper_step"
              role_id: "gatekeeper"
              on_pass: "finish_run"
        """
        ).strip()
        + "\n"
    )


def _has_cleanup_record(caplog, *, operation: str, resource_type: str, owner_id: str | None = None) -> bool:
    records = [
        {
            "event": getattr(record, "event", ""),
            "context": getattr(record, "context", {}) or {},
        }
        for record in caplog.records
    ]
    log_path = app_home() / "logs" / "service.log"
    if log_path.exists():
        records.extend(json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip())
    return any(_matches_cleanup_record(record, operation=operation, resource_type=resource_type, owner_id=owner_id) for record in records)


def _matches_cleanup_record(record: dict, *, operation: str, resource_type: str, owner_id: str | None) -> bool:
    context = record.get("context") or {}
    return (
        record.get("event") == "service.cleanup.failed"
        and context.get("operation") == operation
        and context.get("resource_type") == resource_type
        and (owner_id is None or context.get("owner_id") == owner_id)
    )

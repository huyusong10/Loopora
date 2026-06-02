from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from bundle_lifecycle_test_support import _bundle_yaml
from loopora.bundles import load_bundle_text


def bundle_yaml_with_rejection_control(sample_workdir: Path) -> str:
    return _bundle_yaml(sample_workdir).replace(
        '      on_pass: "finish_run"\n',
        '      on_pass: "finish_run"\n'
        "  controls:\n"
        '    - id: "gatekeeper_rejection_review"\n'
        "      when:\n"
        '        signal: "gatekeeper_rejected"\n'
        '        after: "0s"\n'
        "      call:\n"
        '        role_id: "inspector"\n'
        '      mode: "advisory"\n',
    )


def round_builder_bundle(sample_workdir: Path) -> dict:
    return load_bundle_text(
        dedent(
            f"""
            version: 1
            metadata:
              name: "Round Builder"
            collaboration_summary: |
              Use a short rounds loop where no GateKeeper finish step is configured.
            loop:
              name: "Round Builder"
              workdir: "{sample_workdir}"
              completion_mode: "rounds"
              executor_kind: "codex"
              executor_mode: "preset"
              model: "gpt-5.4"
              reasoning_effort: "medium"
              max_iters: 2
              max_role_retries: 1
              delta_threshold: 0.005
              trigger_window: 2
              regression_window: 2
            spec:
              markdown: |
                # Task

                Build one small, reviewable change.

                # Done When

                - The primary path has a reproducible check.

                # Guardrails

                - Keep changes narrow.

                # Success Surface

                - The change is visible in a focused artifact.

                # Fake Done

                - A self-report without command evidence is fake done.

                # Evidence Preferences

                - Prefer project command output.

                # Residual Risk

                Minor polish can remain as a tracked follow-up owned by product.
            role_definitions:
              - key: "builder"
                name: "Builder"
                archetype: "builder"
                prompt_markdown: |
                  ---
                  version: 1
                  archetype: builder
                  ---

                  Build the focused change.
            workflow:
              version: 1
              preset: "round_builder"
              collaboration_intent: "Run a bounded builder-only loop."
              roles:
                - id: "builder"
                  role_definition_key: "builder"
              steps:
                - id: "builder_step"
                  role_id: "builder"
            """
        ).strip()
        + "\n"
    )


def bundle_yaml_with_legacy_guide(sample_workdir: Path) -> str:
    return (
        _bundle_yaml(sample_workdir)
        .replace(
            '  - key: "gatekeeper"\n',
            '  - key: "guide"\n'
            '    name: "Repair Guide"\n'
            '    description: "Narrows the next move from upstream evidence."\n'
            '    archetype: "guide"\n'
            "    prompt_markdown: |\n"
            "      ---\n"
            "      version: 1\n"
            "      archetype: guide\n"
            "      ---\n\n"
            "      Guide the next repair slice.\n"
            "    posture_notes: |\n"
            "      Turn weak or unproven evidence into a smaller repair direction.\n"
            '  - key: "gatekeeper"\n',
        )
        .replace(
            '    - id: "builder"\n      role_definition_key: "builder"\n',
            '    - id: "guide"\n      role_definition_key: "guide"\n'
            '    - id: "builder"\n      role_definition_key: "builder"\n',
        )
        .replace(
            '    - id: "builder_step"\n      role_id: "builder"\n',
            '    - id: "guide_step"\n      role_id: "guide"\n'
            '    - id: "builder_step"\n      role_id: "builder"\n',
        )
    )


def traceability_item(summary: dict, key: str) -> dict:
    return next(item for item in summary["traceability"]["items"] if item["key"] == key)

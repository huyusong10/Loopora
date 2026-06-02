from __future__ import annotations

from fastapi.testclient import TestClient

from loopora.web import build_app


def role_definition_client(service_factory) -> TestClient:
    service = service_factory(scenario="success")
    return TestClient(build_app(service=service))


def release_builder_payload() -> dict:
    return {
        "name": "Release Builder",
        "description": "Ship focused release changes.",
        "posture_notes": "Prefer maintainability evidence before calling this ready.",
        "archetype": "builder",
        "prompt_markdown": """---
version: 1
archetype: builder
---

Focus on scoped release work.
""",
        "executor_kind": "claude",
        "executor_mode": "preset",
        "model": "",
        "reasoning_effort": "high",
    }


def updated_release_builder_payload() -> dict:
    return {
        "name": "Release Builder v2",
        "description": "Updated role definition.",
        "posture_notes": "Tighten the evidence bar for refactors.",
        "archetype": "builder",
        "prompt_markdown": """---
version: 1
archetype: builder
---

Focus on scoped release work with tighter release constraints.
""",
        "executor_kind": "codex",
        "executor_mode": "command",
        "command_cli": "codex",
        "command_args_text": "\n".join(
            [
                "exec",
                "--json",
                "--cd",
                "{workdir}",
                "--output-schema",
                "{schema_path}",
                "--output-last-message",
                "{output_path}",
                "{prompt}",
            ]
        ),
        "model": "gpt-5.4",
        "reasoning_effort": "",
    }


def archetype_change_payload() -> dict:
    return {
        "name": "Release Inspector",
        "description": "Should fail.",
        "archetype": "inspector",
        "prompt_markdown": """---
version: 1
archetype: inspector
---

Inspect release work instead.
""",
        "executor_kind": "codex",
        "executor_mode": "preset",
        "model": "",
        "reasoning_effort": "medium",
    }


def custom_executor_preset_payload() -> dict:
    return {
        "name": "Custom Wrapper",
        "description": "Wrapper role.",
        "archetype": "custom",
        "prompt_markdown": """---
version: 1
archetype: custom
---

Observe and summarize.
""",
        "executor_kind": "custom",
        "executor_mode": "preset",
        "command_cli": "wrapper",
        "command_args_text": "--output\n{output_path}\n{prompt}\n",
        "model": "",
        "reasoning_effort": "",
    }


def unsafe_prompt_ref_payload() -> dict:
    return {
        "name": "Escaping Builder",
        "description": "Should fail when prompt_ref escapes the asset root.",
        "archetype": "builder",
        "prompt_ref": "../escape.md",
        "prompt_markdown": """---
version: 1
archetype: builder
---

Keep prompt refs inside prompts/.
""",
        "executor_kind": "codex",
        "executor_mode": "preset",
        "model": "gpt-5.4-mini",
        "reasoning_effort": "medium",
    }

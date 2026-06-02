from __future__ import annotations

import pytest

from loopora.workflows import WorkflowError, normalize_workflow, resolve_prompt_files


def test_resolve_prompt_files_drops_unused_entries() -> None:
    workflow = normalize_workflow(
        {
            "version": 1,
            "roles": [
                {"id": "builder", "archetype": "builder", "prompt_ref": "custom-builder.md"},
            ],
            "steps": [
                {"id": "builder_step", "role_id": "builder"},
            ],
        }
    )

    resolved = resolve_prompt_files(
        workflow,
        {
            "custom-builder.md": """---
version: 1
archetype: builder
---

Keep the builder prompt stable.
""",
            "unused.md": """---
version: 1
archetype: inspector
---

This prompt should be dropped.
""",
        },
    )

    assert resolved == {
        "custom-builder.md": """---
version: 1
archetype: builder
---

Keep the builder prompt stable.
""",
    }


def test_resolve_prompt_files_rejects_invalid_prompt_file_keys() -> None:
    workflow = normalize_workflow(
        {
            "version": 1,
            "roles": [
                {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"},
            ],
            "steps": [
                {"id": "builder_step", "role_id": "builder"},
            ],
        }
    )

    with pytest.raises(WorkflowError, match="prompt_ref must be a safe relative path"):
        resolve_prompt_files(
            workflow,
            {
                "../escape.md": """---
version: 1
archetype: builder
---

This key should be rejected instead of silently dropped.
""",
            },
        )


def test_resolve_prompt_files_rejects_shared_prompt_ref_with_mismatched_archetype() -> None:
    workflow = normalize_workflow(
        {
            "version": 1,
            "roles": [
                {"id": "builder", "archetype": "builder", "prompt_ref": "shared.md"},
                {"id": "inspector", "archetype": "inspector", "prompt_ref": "shared.md"},
            ],
            "steps": [
                {"id": "builder_step", "role_id": "builder"},
                {"id": "inspector_step", "role_id": "inspector"},
            ],
        }
    )

    with pytest.raises(
        WorkflowError,
        match="prompt archetype builder does not match expected archetype inspector",
    ):
        resolve_prompt_files(
            workflow,
            {
                "shared.md": """---
version: 1
archetype: builder
---

Keep the builder prompt stable.
""",
            },
        )

from __future__ import annotations

import pytest

from loopora.workflows import WorkflowError, normalize_workflow


def test_normalize_workflow_rejects_unsafe_prompt_ref_paths() -> None:
    with pytest.raises(WorkflowError, match="prompt_ref must be a safe relative path"):
        normalize_workflow(
            {
                "version": 1,
                "roles": [
                    {"id": "builder", "archetype": "builder", "prompt_ref": "../escape.md"},
                ],
                "steps": [
                    {"id": "builder_step", "role_id": "builder"},
                ],
            }
        )

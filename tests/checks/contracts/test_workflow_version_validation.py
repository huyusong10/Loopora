from __future__ import annotations

import pytest

from loopora.workflows import WorkflowError, normalize_workflow


@pytest.mark.parametrize(
    ("version", "message"),
    [
        (0, "unsupported workflow version: 0"),
        ("2", "unsupported workflow version: 2"),
        ("not-a-number", "workflow version must be an integer"),
        (False, "workflow version must be an integer"),
        (1.0, "workflow version must be an integer"),
        (1.2, "workflow version must be an integer"),
    ],
)
def test_normalize_workflow_rejects_invalid_explicit_version(version, message) -> None:
    with pytest.raises(WorkflowError, match=message):
        normalize_workflow(
            {
                "version": version,
                "roles": [{"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"}],
                "steps": [{"id": "builder_step", "role_id": "builder"}],
            }
        )

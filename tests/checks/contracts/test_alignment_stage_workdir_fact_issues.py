from __future__ import annotations

from loopora.service_alignment_stage import alignment_bundle_workdir_fact_issues


def test_alignment_bundle_workdir_fact_issues_ignore_supported_or_unknown_stack_claims() -> None:
    issues = alignment_bundle_workdir_fact_issues(
        {
            "collaboration_summary": "Observed React frontend.",
            "spec": {"markdown": "Observed Python tests."},
            "workflow": {"collaboration_intent": "Unknown stack must be verified during the run."},
            "role_definitions": [
                {
                    "key": "builder",
                    "description": "Observed FastAPI service.",
                    "prompt_markdown": "Assumption: React details are unknown.",
                    "posture_notes": "Observed test coverage expectations.",
                },
                "ignore malformed role",
            ],
        },
        workdir_snapshot="package.json\npyproject.toml\nrequirements.txt\ngo.mod\ntests/ exists: yes",
    )

    assert issues == []


def test_alignment_bundle_workdir_fact_issues_report_unsupported_observed_stack_claims() -> None:
    issues = alignment_bundle_workdir_fact_issues(
        {
            "collaboration_summary": "Observed React frontend.",
            "spec": {"markdown": "Observed Django service."},
            "workflow": {"collaboration_intent": "Unknown stack must be verified during the run."},
            "role_definitions": [
                {
                    "key": "builder",
                    "description": "Observed FastAPI service.",
                    "prompt_markdown": "Assumption: React details are unknown.",
                    "posture_notes": "看到 Go service.",
                }
            ],
        },
        workdir_snapshot="tests/ exists: yes",
    )

    assert issues == [
        "bundle field collaboration_summary must not claim an observed workdir stack unsupported by Workdir Snapshot",
        "bundle field spec.markdown must not claim an observed workdir stack unsupported by Workdir Snapshot",
        "bundle field role_definition builder.description must not claim an observed workdir stack unsupported by Workdir Snapshot",
        "bundle field role_definition builder.posture_notes must not claim an observed workdir stack unsupported by Workdir Snapshot",
    ]

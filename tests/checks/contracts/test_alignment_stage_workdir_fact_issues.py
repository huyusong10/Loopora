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


def test_alignment_bundle_workdir_fact_issues_allow_task_required_test_evidence_when_tests_are_not_observed() -> None:
    issues = alignment_bundle_workdir_fact_issues(
        {
            "collaboration_summary": (
                "The snapshot reports no tests marker, but the Loop should require unit and contract checks as "
                "future evidence. A fixed test-only harness is not sufficient by itself."
            ),
            "spec": {
                "markdown": (
                    "Treat repository stack and test runner as unknown until runtime inspection proves them. "
                    "Done When includes contract tests for metadata parsing."
                )
            },
            "workflow": {"collaboration_intent": "Inspector should collect test evidence if a runner exists or report it missing."},
        },
        workdir_snapshot="tests/ exists: no",
    )

    assert issues == []


def test_alignment_bundle_workdir_fact_issues_do_not_treat_next_pass_as_nextjs_stack() -> None:
    issues = alignment_bundle_workdir_fact_issues(
        {
            "collaboration_summary": (
                "The Workdir Snapshot reports no stack markers. Inspector findings should shift the next Builder "
                "pass from feature expansion to evidence hardening."
            )
        },
        workdir_snapshot="package.json not found",
    )

    assert issues == []


def test_alignment_bundle_workdir_fact_issues_allow_frontend_only_fake_done_risk() -> None:
    issues = alignment_bundle_workdir_fact_issues(
        {
            "spec": {
                "markdown": (
                    "Do not claim an observed stack, test runner, or existing implementation unless runtime "
                    "inspection proves it. GateKeeper must fail closed on login/logout happy path, "
                    "frontend-only session clear, framework defaults, short-expiry-only, or missing token negatives."
                )
            }
        },
        workdir_snapshot="package.json not found",
    )

    assert issues == []


def test_alignment_bundle_workdir_fact_issues_allow_task_target_stack_terms_without_observed_context() -> None:
    issues = alignment_bundle_workdir_fact_issues(
        {
            "spec": {
                "markdown": (
                    "Deliver a prompt asset migration from Python code into versioned prompt assets. "
                    "Do not claim Agent Native adapters, Claude session context, runtime renderers, "
                    "asset tree, tests, or lint were observed unless verified in the workdir."
                )
            }
        },
        workdir_snapshot="tests/ exists: no",
    )

    assert issues == []


def test_alignment_bundle_workdir_fact_issues_still_reject_nextjs_stack_without_package_marker() -> None:
    issues = alignment_bundle_workdir_fact_issues(
        {"collaboration_summary": "The Workdir Snapshot shows an observed Next.js app."},
        workdir_snapshot="package.json not found",
    )

    assert issues == [
        "bundle field collaboration_summary must not claim an observed workdir stack unsupported by Workdir Snapshot"
    ]

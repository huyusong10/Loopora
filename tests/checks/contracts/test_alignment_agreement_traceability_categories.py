from __future__ import annotations

from pathlib import Path

from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.alignment_traceability_rules import alignment_bundle_agreement_traceability_issues


def test_alignment_traceability_checks_loop_fit_task_terms(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "loop_fit": (
                    "Browsertrace needs Loopora because later rounds must create new browsertrace proof "
                    "before GateKeeper can close."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("loop_fit missing browsertrace" in issue for issue in issues)


def test_alignment_traceability_checks_agreement_success_categories(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
        "Ship the refund approval path so Support admin can approve a refund and audit log records the actor.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means Support admin can approve a refund, audit log records the actor, "
                    "and customer receives an email notification."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "notification/message" in issue for issue in issues)


def test_alignment_traceability_checks_agreement_evidence_preference_categories(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Prefer project-owned checks, direct run output, and concrete artifacts before screenshots or claims.",
        "Prefer browser journey proof before screenshots or claims.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "evidence_preferences": (
                    "Evidence must include a browser journey and audit log command output before GateKeeper can pass."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("evidence preferences" in issue and "audit/log" in issue for issue in issues)


def test_alignment_traceability_checks_agreement_accessibility_and_locale_categories(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means keyboard users can complete checkout, screen reader labels are available, "
                    "and Chinese and English variants preserve the same action."
                ),
                "evidence_preferences": (
                    "Evidence must include keyboard navigation proof and Chinese and English locale verification."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "accessibility/a11y" in issue for issue in issues)
    assert any("success surface" in issue and "locale/i18n" in issue for issue in issues)
    assert any("evidence preferences" in issue and "accessibility/a11y" in issue for issue in issues)
    assert any("evidence preferences" in issue and "locale/i18n" in issue for issue in issues)


def test_alignment_traceability_ignores_metadata_and_loop_names(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["metadata"]["name"] = "browsertrace"
    bundle["metadata"]["description"] = "browsertrace"
    bundle["loop"]["name"] = "browsertrace"
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "evidence_preferences": "browsertrace",
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("evidence_preferences missing browsertrace" in issue for issue in issues)


def test_alignment_traceability_counts_workflow_step_inputs_as_runtime_surface(
    sample_workdir: Path,
) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["workflow"]["steps"][0]["inputs"] = {"evidence_query": {"target_ids": ["browsertrace"]}}
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "evidence_preferences": "browsertrace",
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert not any("evidence_preferences" in issue for issue in issues)

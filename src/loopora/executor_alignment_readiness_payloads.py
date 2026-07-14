from __future__ import annotations

from functools import lru_cache

from loopora.alignment_guidance import load_alignment_guidance_assets
from loopora.alignment_readiness_shared import ALIGNMENT_READINESS_EVIDENCE_KEYS
from loopora.service_types import LooporaError

READINESS_ISSUE_FIXTURES_ASSET_NAME = "readiness-issue-fixtures.json"


def alignment_missing_readiness_evidence() -> dict[str, str]:
    evidence = dict.fromkeys(ALIGNMENT_READINESS_EVIDENCE_KEYS, "ok")
    evidence["open_questions"] = ""
    return evidence


def alignment_readiness_issue_for_scenario(scenario: str) -> tuple[str, str, str] | None:
    fixture = _readiness_issue_fixtures().get(str(scenario or ""))
    if fixture is None:
        return None
    return fixture["field"], fixture["evidence_text"], fixture["assistant_message"]


@lru_cache(maxsize=1)
def _readiness_issue_fixtures() -> dict[str, dict[str, str]]:
    asset = load_alignment_guidance_assets().readiness_issue_fixtures
    issues = asset.get("issues")
    if not isinstance(issues, dict):
        raise LooporaError(f"{READINESS_ISSUE_FIXTURES_ASSET_NAME} must define issue fixtures")
    return {str(scenario): _readiness_issue_fixture(str(scenario), fixture) for scenario, fixture in issues.items()}


def _readiness_issue_fixture(scenario: str, fixture: object) -> dict[str, str]:
    if not isinstance(fixture, dict):
        raise LooporaError(f"invalid readiness issue fixture: {scenario}")
    field = fixture.get("field")
    evidence_text = fixture.get("evidence_text")
    assistant_message = fixture.get("assistant_message")
    if (
        not isinstance(field, str)
        or field not in ALIGNMENT_READINESS_EVIDENCE_KEYS
        or not isinstance(evidence_text, str)
        or not isinstance(assistant_message, str)
        or not assistant_message.strip()
    ):
        raise LooporaError(f"invalid readiness issue fixture fields: {scenario}")
    return {
        "field": field,
        "evidence_text": evidence_text,
        "assistant_message": assistant_message,
    }

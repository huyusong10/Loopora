from __future__ import annotations

from pathlib import Path

from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml

GOVERNANCE_MARKER_EVIDENCE = "AGENTS.md, design/README.md, design/, and tests/ must shape runtime governance."


def alignment_bundle(workdir: Path) -> dict:
    return load_bundle_text(alignment_bundle_yaml(str(workdir)))


def governance_session(
    evidence: str = GOVERNANCE_MARKER_EVIDENCE,
    *,
    workdir: Path | None = None,
    key: str = "workdir_facts",
) -> dict:
    session = {"working_agreement": {"readiness_evidence": {key: evidence}}}
    if workdir is not None:
        session["workdir"] = str(workdir)
    return session


def has_governance_marker_issue(issues: list[str]) -> bool:
    return any("project-local governance markers" in issue for issue in issues)

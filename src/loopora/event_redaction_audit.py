from __future__ import annotations

from loopora.event_redaction_audit_db import audit_alignment_db_events, audit_db_events
from loopora.event_redaction_audit_files import audit_alignment_event_files, audit_timeline_files
from loopora.event_redaction_audit_results import combine_event_redaction_reports


def audit_event_redaction(repository, *, fix: bool = False) -> dict:
    return combine_event_redaction_reports(
        fix=fix,
        db_events=audit_db_events(repository, fix=fix),
        timeline_files=audit_timeline_files(repository, fix=fix),
        alignment_db_events=audit_alignment_db_events(repository, fix=fix),
        alignment_event_files=audit_alignment_event_files(repository, fix=fix),
    )


def audit_run_event_redaction(repository, *, fix: bool = False) -> dict:
    return audit_event_redaction(repository, fix=fix)

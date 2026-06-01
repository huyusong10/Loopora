from __future__ import annotations

from loopora.event_redaction import redact_alignment_event_payload, redact_run_event_payload
from loopora.event_redaction_audit_results import event_redaction_sample, redaction_changed


def audit_db_events(repository, *, fix: bool) -> dict:
    scanned = 0
    suspect = 0
    fixed = 0
    samples = []
    unfixable = []
    for event in repository.list_run_events_for_redaction_audit():
        scanned += 1
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        redacted = redact_run_event_payload(str(event.get("event_type") or ""), payload)
        if not redaction_changed(payload, redacted):
            continue
        suspect += 1
        samples.append(event_redaction_sample("db", event, redacted))
        if fix:
            if repository.update_run_event_payload_for_redaction(int(event["id"]), redacted):
                fixed += 1
            else:
                unfixable.append({"source": "db", "event_id": event.get("id"), "reason": "update_failed"})
    return {
        "scanned": scanned,
        "suspect": suspect,
        "fixed": fixed,
        "samples": samples[:20],
        "unfixable": unfixable,
    }


def audit_alignment_db_events(repository, *, fix: bool) -> dict:
    scanned = 0
    suspect = 0
    fixed = 0
    samples = []
    unfixable = []
    if not hasattr(repository, "list_alignment_events_for_redaction_audit"):
        return {"scanned": 0, "suspect": 0, "fixed": 0, "samples": [], "unfixable": []}
    for event in repository.list_alignment_events_for_redaction_audit():
        scanned += 1
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        redacted = redact_alignment_event_payload(str(event.get("event_type") or ""), payload)
        if not redaction_changed(payload, redacted):
            continue
        suspect += 1
        samples.append(event_redaction_sample("alignment_db", event, redacted))
        if fix:
            if repository.update_alignment_event_payload_for_redaction(int(event["id"]), redacted):
                fixed += 1
            else:
                unfixable.append({"source": "alignment_db", "event_id": event.get("id"), "reason": "update_failed"})
    return {
        "scanned": scanned,
        "suspect": suspect,
        "fixed": fixed,
        "samples": samples[:20],
        "unfixable": unfixable,
    }

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path


ALIGNMENT_CANDIDATE_REPAIR = "repair_candidate_plan"
ALIGNMENT_GENERATION_RETRY = "retry_alignment_generation"
ALIGNMENT_USER_CANCELLED = "user_cancelled"
ALIGNMENT_WORKER_INTERRUPTED = "resume_interrupted_planning"
ALIGNMENT_WORKER_INTERRUPTED_ERROR = "Planning was interrupted because the local Loopora worker stopped unexpectedly."
ALIGNMENT_WORKER_START_ERROR = "Planning could not start because the local Loopora worker was unavailable."


def alignment_failure_recovery_projection(session: Mapping[str, object]) -> dict[str, object]:
    if str(session.get("status") or "").strip() != "failed":
        return {}
    if bool(session.get("stop_requested")):
        return {
            "kind": ALIGNMENT_USER_CANCELLED,
            "failure_domain": "user_cancelled",
            "candidate_plan_available": alignment_candidate_plan_available(session),
            "retry_generation_available": False,
            "needs_attention": False,
        }
    candidate_available = alignment_candidate_plan_available(session)
    if not candidate_available and str(session.get("error_message") or "").strip() == ALIGNMENT_WORKER_INTERRUPTED_ERROR:
        return {
            "kind": ALIGNMENT_WORKER_INTERRUPTED,
            "failure_domain": "local_worker_interrupted",
            "candidate_plan_available": False,
            "retry_generation_available": True,
            "needs_attention": True,
        }
    return {
        "kind": ALIGNMENT_CANDIDATE_REPAIR if candidate_available else ALIGNMENT_GENERATION_RETRY,
        "failure_domain": "candidate_plan" if candidate_available else "execution",
        "candidate_plan_available": candidate_available,
        "retry_generation_available": not candidate_available,
        "needs_attention": True,
    }


def alignment_candidate_plan_available(session: Mapping[str, object]) -> bool:
    bundle_path = str(session.get("bundle_path") or "").strip()
    if not bundle_path:
        return False
    try:
        return Path(bundle_path).is_file()
    except OSError:
        return False

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from loopora.agent_entry_candidate import agent_ready_task_anchor_projection, ready_candidate_yaml_provenance
from loopora.agent_entry_run_projection import append_agent_entry_invocation
from loopora.service_agent_bundle_candidate_types import (
    AGENT_ALIGNMENT_CONTINUATION_ACTIVE_STATUSES,
    AGENT_ALIGNMENT_CONTINUATION_TERMINAL_STATUSES,
    AgentAlignmentContinuationRequest,
)
from loopora.service_types import LooporaError


class ServiceAgentBundleCandidateContinuationMixin:
    def _continue_agent_alignment_from_binding(
        self,
        request: AgentAlignmentContinuationRequest,
    ) -> dict[str, Any] | None:
        session = self._agent_alignment_continuation_session(request)
        if session is None:
            return None

        self.repository.append_alignment_event(
            session["id"],
            "agent_alignment_continuation_received",
            {
                "candidate_origin": "agent_entry",
                "adapter": request.adapter,
                "entry_source": request.entry_source,
                "host_context_id": request.host_context_id,
                "continued_from_binding": True,
            },
        )
        session = self.append_alignment_message_sync(session["id"], request.task_message)
        session = self._wait_for_agent_alignment_continuation_turn(session["id"])
        requires_web_alignment = session["status"] not in {"ready", "skipped"}
        ready_candidate_provenance = ready_candidate_yaml_provenance(session)
        ready_task_anchor = agent_ready_task_anchor_projection(session) if session["status"] == "ready" else {}
        binding_payload = {
            "alignment_session_id": session["id"],
            "alignment_status": session["status"],
            "bundle_path": session.get("bundle_path", ""),
            "candidate_origin": "agent_entry",
            "candidate_adapter": request.adapter,
            "candidate_entry_source": request.entry_source,
            "host_context_id": request.host_context_id,
            "requires_web_alignment": requires_web_alignment,
            "requires_candidate_repair": False,
            "loopora_fit_contradiction": request.loopora_fit_contradiction or bool(request.existing_binding.get("loopora_fit_contradiction")),
            "source_path": str(request.existing_binding.get("source_path") or ""),
            **request.candidate_provenance,
            **ready_candidate_provenance,
            **ready_task_anchor,
            "preview_path": f"/loops/new/bundle?alignment_session_id={session['id']}",
            "entry_invocations": append_agent_entry_invocation(
                request.existing_binding,
                action="plan",
                entry_source=request.entry_source,
            ),
        }
        binding, context_binding_error = self._write_agent_candidate_binding(
            request.adapter,
            request.root,
            binding_payload,
            context_id=request.context_id,
            session_id=session["id"],
        )
        requires_context_repair = bool(context_binding_error)
        return {
            "adapter": request.adapter,
            "workdir": str(request.root),
            "candidate_origin": "agent_entry",
            "candidate_entry_source": request.entry_source,
            "host_context_id": request.host_context_id,
            "continued_alignment_session": True,
            "requires_web_alignment": requires_web_alignment,
            "requires_candidate_repair": False,
            "requires_context_repair": requires_context_repair,
            "loopora_fit_contradiction": request.loopora_fit_contradiction or bool(request.existing_binding.get("loopora_fit_contradiction")),
            **request.candidate_provenance,
            **ready_candidate_provenance,
            **ready_task_anchor,
            "status": session["status"],
            "ready": False if requires_context_repair else session["status"] == "ready",
            "ready_review_projection": self._agent_ready_review_projection(session) if session["status"] == "ready" else {},
            "session": session,
            "binding": binding,
            "preview_path": f"/loops/new/bundle?alignment_session_id={session['id']}",
            "context_binding_error": context_binding_error,
            "error": context_binding_error,
            "loop_recovery": "repair_agent_context_card" if requires_context_repair else "",
        }

    def _agent_alignment_continuation_session(self, request: AgentAlignmentContinuationRequest) -> dict | None:
        binding = request.existing_binding
        if (
            _agent_message_requests_fresh_alignment(request.task_message)
            or binding.get("requires_web_alignment") is not True
            or binding.get("requires_candidate_repair") is True
        ):
            return None
        session_id = str(binding.get("alignment_session_id") or "").strip()
        if not session_id:
            return None
        try:
            session = self.get_alignment_session(session_id)
        except LooporaError:
            return None
        status = str(session.get("status") or "").strip()
        if not _agent_alignment_session_matches_workdir(session, request.root) or status in AGENT_ALIGNMENT_CONTINUATION_TERMINAL_STATUSES:
            return None
        if status == "idle" and not _agent_idle_review_continuation_message(session, request.task_message):
            return None
        if status in AGENT_ALIGNMENT_CONTINUATION_ACTIVE_STATUSES:
            raise LooporaError("alignment session is already running")
        return session

    def _wait_for_agent_alignment_continuation_turn(self, session_id: str) -> dict:
        deadline = time.time() + 30.0
        interval = max(0.01, float(getattr(getattr(self, "settings", None), "polling_interval_seconds", 0.05) or 0.05))
        session = self.get_alignment_session(session_id)
        while time.time() < deadline and session["status"] in AGENT_ALIGNMENT_CONTINUATION_ACTIVE_STATUSES:
            time.sleep(interval)
            session = self.get_alignment_session(session_id)
        return session


def _agent_message_requests_fresh_alignment(message: str) -> bool:
    normalized = " ".join(str(message or "").strip().lower().split())
    if normalized in {
        "fresh",
        "/loopora-plan fresh",
        "start fresh",
        "new loop",
        "new plan",
        "重新开始",
        "重新新建",
        "新建方案",
        "新建 loop",
    }:
        return True
    return any(
        normalized.startswith(prefix)
        for prefix in (
            "new task",
            "another task",
            "different task",
            "prepare a second ",
            "prepare another ",
            "start a new ",
            "start another ",
            "create a second ",
            "create another ",
            "另一个任务",
            "新的任务",
            "第二个任务",
        )
    )


def _agent_alignment_session_matches_workdir(session: dict[str, Any], root: Path) -> bool:
    try:
        return Path(str(session.get("workdir") or "")).expanduser().resolve() == root
    except (OSError, RuntimeError):
        return False


def _agent_idle_review_continuation_message(session: dict[str, Any], message: str) -> bool:
    normalized = _agent_inline_text(message).lower()
    if not normalized:
        return False
    if session.get("agent_entry_review"):
        return True
    review = session.get("agent_entry_review") if isinstance(session.get("agent_entry_review"), dict) else {}
    replies = [str(review.get("suggested_reply") or "")]
    replies.extend(str(option.get("user_reply") or "") for option in list(review.get("decision_options") or []) if isinstance(option, dict))
    if any(_agent_reply_matches(normalized, reply) for reply in replies):
        return True
    return any(
        marker in normalized
        for marker in (
            "continue web review from this /loopora-plan task anchor",
            "first re-check whether this /loopora-plan task anchor fits loopora",
            "请基于这次 /loopora-plan 的任务锚点继续 web review",
            "请先按这次 /loopora-plan 的任务锚点重新判断",
        )
    )


def _agent_reply_matches(normalized_message: str, reply: str) -> bool:
    normalized_reply = _agent_inline_text(reply).lower()
    if not normalized_reply:
        return False
    return normalized_message == normalized_reply or normalized_reply.startswith(normalized_message.rstrip("…"))


def _agent_inline_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()

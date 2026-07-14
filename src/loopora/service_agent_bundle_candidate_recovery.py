from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_adapter_context_binding import AGENT_CONTEXT_CARD_SAVE_ERROR
from loopora.agent_adapters import write_agent_binding
from loopora.agent_entry_candidate import agent_ready_review_projection
from loopora.bundles import BundleError
from loopora.service_agent_bundle_candidate_types import AGENT_CANDIDATE_PLAN_FILE_SAVE_ERROR
from loopora.service_bundle_file_writes import write_bundle_text_atomically
from loopora.service_types import LooporaError
from loopora.utils import utc_now


class ServiceAgentBundleCandidateRecoveryMixin:
    def _save_and_sync_agent_candidate(self, session: dict[str, Any], candidate_text: str) -> dict[str, Any]:
        try:
            write_bundle_text_atomically(Path(session["bundle_path"]), candidate_text)
            preview = self.sync_alignment_bundle_from_file(session["id"])
            return preview["session"]
        except OSError:
            return self._fail_agent_candidate_save(session["id"])

    def _fail_agent_candidate_save(self, session_id: str) -> dict[str, Any]:
        self.repository.update_alignment_session(
            session_id,
            status="failed",
            finished_at=utc_now(),
            clear_active_child_pid=True,
            error_message=AGENT_CANDIDATE_PLAN_FILE_SAVE_ERROR,
            validation={
                "status": "failed",
                "error": AGENT_CANDIDATE_PLAN_FILE_SAVE_ERROR,
            },
        )
        self.repository.append_alignment_event(
            session_id,
            "alignment_failed",
            {"status": "failed", "error": AGENT_CANDIDATE_PLAN_FILE_SAVE_ERROR},
        )
        return self.get_alignment_session(session_id)

    def _write_agent_candidate_binding(
        self,
        adapter: str,
        root: Path,
        payload: dict[str, Any],
        *,
        context_id: str,
        session_id: str,
    ) -> tuple[dict[str, Any], str]:
        try:
            return write_agent_binding(adapter, root, payload, context_id=context_id), ""
        except OSError:
            self.repository.append_alignment_event(
                session_id,
                "agent_context_card_save_failed",
                {"status": "blocked", "error": AGENT_CONTEXT_CARD_SAVE_ERROR},
            )
            return (
                {
                    "adapter": adapter,
                    "workdir": str(root),
                    **payload,
                    "context_binding_error": AGENT_CONTEXT_CARD_SAVE_ERROR,
                },
                AGENT_CONTEXT_CARD_SAVE_ERROR,
            )

    def _agent_ready_review_projection(self, session: dict) -> dict[str, Any]:
        try:
            preview = self.get_alignment_bundle(str(session.get("id") or ""))
        except (LooporaError, BundleError, OSError, ValueError):
            return {}
        return agent_ready_review_projection(preview)

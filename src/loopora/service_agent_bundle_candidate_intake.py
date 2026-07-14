from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_adapter_check_utils import adapter_unavailable_summary as _adapter_unavailable_summary
from loopora.agent_adapters import (
    normalize_agent_adapter_kind,
    read_agent_binding,
    resolve_adapter_project_root,
    resolved_agent_context_id,
)
from loopora.agent_entry_candidate import (
    agent_ready_task_anchor_projection,
    candidate_yaml_provenance,
    normalized_candidate_yaml,
    ready_candidate_yaml_provenance,
)
from loopora.agent_entry_run_projection import append_agent_entry_invocation
from loopora.alignment_semantics import text_mentions_loop_fit_contradiction
from loopora.bundles import BundleError, read_bundle_file_text
from loopora.bundle_io import resolve_bundle_file_path
from loopora.service_agent_bundle_candidate_continuation import ServiceAgentBundleCandidateContinuationMixin
from loopora.service_agent_bundle_candidate_recovery import ServiceAgentBundleCandidateRecoveryMixin
from loopora.service_agent_bundle_candidate_review import ServiceAgentBundleCandidateReviewMixin
from loopora.service_agent_bundle_candidate_types import AgentAlignmentContinuationRequest, AgentBundleCandidateRequest
from loopora.service_types import LooporaError


class ServiceAgentBundleCandidateMixin(
    ServiceAgentBundleCandidateContinuationMixin,
    ServiceAgentBundleCandidateRecoveryMixin,
    ServiceAgentBundleCandidateReviewMixin,
):
    def create_agent_bundle_candidate(self, request: AgentBundleCandidateRequest) -> dict[str, Any]:
        adapter = normalize_agent_adapter_kind(request.adapter)
        if adapter not in {"codex", "claude", "opencode"}:
            raise LooporaError(_adapter_unavailable_summary(adapter))
        root = resolve_adapter_project_root(request.workdir)
        entry_source = str(request.entry_source or "").strip() or "direct_cli"
        task_message = str(request.message or "").strip()
        if not task_message:
            raise LooporaError("agent candidate requires --message task context for traceability")
        raw_yaml = str(request.bundle_yaml or "")
        source_path = ""
        if not raw_yaml.strip() and request.bundle_file is not None:
            try:
                bundle_path = resolve_bundle_file_path(Path(request.bundle_file))
                raw_yaml = read_bundle_file_text(bundle_path)
            except BundleError as exc:
                raise LooporaError(str(exc)) from exc
            except OSError as exc:
                raise LooporaError("bundle file could not be read") from exc
            source_path = str(bundle_path)
        candidate_text = normalized_candidate_yaml(raw_yaml)
        candidate_provenance = candidate_yaml_provenance(candidate_text)
        loopora_fit_contradiction = text_mentions_loop_fit_contradiction(task_message)
        host_context_id = resolved_agent_context_id(adapter, context_id=request.context_id)
        existing_binding = read_agent_binding(adapter, root, context_id=request.context_id)

        if not candidate_text:
            continuation_request = AgentAlignmentContinuationRequest(
                adapter=adapter,
                root=root,
                task_message=task_message,
                entry_source=entry_source,
                host_context_id=host_context_id,
                context_id=request.context_id,
                existing_binding=existing_binding,
                candidate_provenance=candidate_provenance,
                loopora_fit_contradiction=loopora_fit_contradiction,
            )
            continuation = self._continue_agent_alignment_from_binding(
                continuation_request,
            )
            if continuation is not None:
                return continuation

        session = self.create_alignment_session(
            workdir=root,
            message=task_message,
            start_immediately=False,
            executor_kind=adapter,
            executor_mode="preset",
            command_cli="",
            command_args_text="",
            model="",
            reasoning_effort="",
        )
        self.repository.append_alignment_event(
            session["id"],
            "agent_candidate_received",
            {
                "candidate_origin": "agent_entry",
                "adapter": adapter,
                "entry_source": entry_source,
                "host_context_id": host_context_id,
                "has_candidate_yaml": bool(candidate_text),
                "requires_web_alignment": not bool(candidate_text),
                "requires_candidate_repair": False,
                "loopora_fit_contradiction": loopora_fit_contradiction,
                "source_path": source_path,
                **candidate_provenance,
                "ready_candidate_sha256": "",
                "ready_candidate_bytes": 0,
            },
        )
        if candidate_text:
            session = self._save_and_sync_agent_candidate(session, candidate_text)
        else:
            session = self._append_missing_agent_candidate_message(
                session,
                loopora_fit_contradiction=loopora_fit_contradiction,
            )
        requires_candidate_repair = bool(candidate_text) and session["status"] != "ready"
        ready_candidate_provenance = ready_candidate_yaml_provenance(session)
        ready_task_anchor = agent_ready_task_anchor_projection(session) if session["status"] == "ready" else {}
        if ready_candidate_provenance["ready_candidate_sha256"]:
            self.repository.append_alignment_event(
                session["id"],
                "agent_candidate_ready_content",
                {
                    "candidate_origin": "agent_entry",
                    "adapter": adapter,
                    "entry_source": entry_source,
                    "host_context_id": host_context_id,
                    "source_path": source_path,
                    **candidate_provenance,
                    **ready_candidate_provenance,
                },
            )
            session = self.get_alignment_session(session["id"])
        binding_payload = {
            "alignment_session_id": session["id"],
            "alignment_status": session["status"],
            "bundle_path": session.get("bundle_path", ""),
            "candidate_origin": "agent_entry",
            "candidate_adapter": adapter,
            "candidate_entry_source": entry_source,
            "host_context_id": host_context_id,
            "requires_web_alignment": not bool(candidate_text),
            "requires_candidate_repair": requires_candidate_repair,
            "loopora_fit_contradiction": loopora_fit_contradiction,
            "source_path": source_path,
            **candidate_provenance,
            **ready_candidate_provenance,
            **ready_task_anchor,
            "preview_path": f"/loops/new/bundle?alignment_session_id={session['id']}",
            "entry_invocations": append_agent_entry_invocation(
                existing_binding,
                action="plan",
                entry_source=entry_source,
            ),
        }
        binding, context_binding_error = self._write_agent_candidate_binding(
            adapter,
            root,
            binding_payload,
            context_id=request.context_id,
            session_id=session["id"],
        )
        requires_context_repair = bool(context_binding_error)
        return {
            "adapter": adapter,
            "workdir": str(root),
            "candidate_origin": "agent_entry",
            "candidate_entry_source": entry_source,
            "host_context_id": host_context_id,
            "requires_web_alignment": not bool(candidate_text),
            "requires_candidate_repair": requires_candidate_repair,
            "requires_context_repair": requires_context_repair,
            "loopora_fit_contradiction": loopora_fit_contradiction,
            **candidate_provenance,
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

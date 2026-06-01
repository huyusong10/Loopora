from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loopora.agent_adapters import (
    normalize_agent_adapter_kind,
    read_agent_binding,
    resolve_adapter_project_root,
    resolved_agent_context_id,
    write_agent_binding,
)
from loopora.agent_entry_candidate import (
    agent_ready_review_projection,
    candidate_yaml_provenance,
    normalized_candidate_yaml,
    ready_candidate_yaml_provenance,
)
from loopora.agent_entry_run_projection import append_agent_entry_invocation
from loopora.alignment_semantics import text_mentions_loop_fit_contradiction
from loopora.bundles import BundleError, read_bundle_file_text
from loopora.service_alignment_transcript import AlignmentTranscriptContext, localized_alignment_system_message_appender
from loopora.service_types import LooporaError


@dataclass(frozen=True)
class AgentBundleCandidateRequest:
    adapter: str
    workdir: Path | str
    message: str = ""
    bundle_yaml: str = ""
    bundle_file: Path | str | None = None
    context_id: str = ""
    entry_source: str = ""


class ServiceAgentBundleCandidateMixin:
    def create_agent_bundle_candidate(self, request: AgentBundleCandidateRequest) -> dict[str, Any]:
        adapter = normalize_agent_adapter_kind(request.adapter)
        if adapter not in {"codex", "claude", "opencode"}:
            raise LooporaError(f"{adapter} adapter is not implemented yet")
        root = resolve_adapter_project_root(request.workdir)
        entry_source = str(request.entry_source or "").strip() or "direct_cli"
        raw_yaml = str(request.bundle_yaml or "")
        source_path = ""
        if not raw_yaml.strip() and request.bundle_file is not None:
            bundle_path = Path(request.bundle_file).expanduser().resolve()
            try:
                raw_yaml = read_bundle_file_text(bundle_path)
            except OSError as exc:
                raise LooporaError(str(exc)) from exc
            source_path = str(bundle_path)
        candidate_text = normalized_candidate_yaml(raw_yaml)
        candidate_provenance = candidate_yaml_provenance(candidate_text)
        task_message = str(request.message or "").strip()
        if not task_message:
            raise LooporaError("agent candidate requires --message task summary for traceability")
        loopora_fit_contradiction = text_mentions_loop_fit_contradiction(task_message)
        host_context_id = resolved_agent_context_id(adapter, context_id=request.context_id)

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
            candidate_path = Path(session["bundle_path"])
            candidate_path.parent.mkdir(parents=True, exist_ok=True)
            candidate_path.write_text(candidate_text, encoding="utf-8")
            preview = self.sync_alignment_bundle_from_file(session["id"])
            session = preview["session"]
        else:
            session = self._append_missing_agent_candidate_message(
                session,
                loopora_fit_contradiction=loopora_fit_contradiction,
            )
        requires_candidate_repair = bool(candidate_text) and session["status"] != "ready"
        ready_candidate_provenance = ready_candidate_yaml_provenance(session)
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
        existing_binding = read_agent_binding(adapter, root, context_id=request.context_id)
        binding = write_agent_binding(
            adapter,
            root,
            {
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
                "preview_path": f"/loops/new/bundle?alignment_session_id={session['id']}",
                "entry_invocations": append_agent_entry_invocation(
                    existing_binding,
                    action="plan",
                    entry_source=entry_source,
                ),
            },
            context_id=request.context_id,
        )
        return {
            "adapter": adapter,
            "workdir": str(root),
            "candidate_origin": "agent_entry",
            "candidate_entry_source": entry_source,
            "host_context_id": host_context_id,
            "requires_web_alignment": not bool(candidate_text),
            "requires_candidate_repair": requires_candidate_repair,
            "loopora_fit_contradiction": loopora_fit_contradiction,
            **candidate_provenance,
            **ready_candidate_provenance,
            "status": session["status"],
            "ready": session["status"] == "ready",
            "ready_review_projection": self._agent_ready_review_projection(session) if session["status"] == "ready" else {},
            "session": session,
            "binding": binding,
            "preview_path": f"/loops/new/bundle?alignment_session_id={session['id']}",
        }

    def _agent_ready_review_projection(self, session: dict) -> dict[str, Any]:
        try:
            preview = self.get_alignment_bundle(str(session.get("id") or ""))
        except (LooporaError, BundleError, OSError, ValueError):
            return {}
        return agent_ready_review_projection(preview)

    def _append_missing_agent_candidate_message(self, session: dict, *, loopora_fit_contradiction: bool) -> dict:
        append_system_message = localized_alignment_system_message_appender(
            AlignmentTranscriptContext(repository=self.repository, get_session=self.get_alignment_session)
        )
        if loopora_fit_contradiction:
            return append_system_message(
                session["id"],
                zh=(
                    "Loopora 已把这次 /loopora-plan 打开为 Web review：宿主 Agent 没有提交候选方案文件，"
                    "而任务摘要已经说明这更像一次性处理、直接回答、不需要后续新证据，"
                    "或稳定 benchmark / proof harness 已足够裁决的工作，"
                    "所以这里不会伪装成可运行 Loop。若你仍想把范围改成可治理的长期 Loop，"
                    "请先补充为什么需要后续证据、handoff 或 GateKeeper 裁决。"
                ),
                en=(
                    "Loopora opened this /loopora-plan result as Web review because the host Agent did not submit "
                    "a candidate plan file, and the task summary says this is closer to a one-off fix, direct answer, "
                    "benchmark/test-harness-only path, or work where later rounds add no new evidence. This is not a runnable Loop yet. If you still "
                    "want to reshape it into a governed Loop, first explain what later evidence, handoffs, or "
                    "GateKeeper judgment would add."
                ),
            )
        return append_system_message(
            session["id"],
            zh=(
                "Loopora 已把这次 /loopora-plan 打开为 Web review：宿主 Agent 没有提交候选方案文件，"
                "所以这里不会伪装成可运行 Loop。请继续确认或补充成功标准、伪完成风险、证据预期、"
                "Loopora fit、执行策略、判断取舍、残余风险和本地治理责任，然后再生成可审查的 Loop 预览。"
            ),
            en=(
                "Loopora opened this /loopora-plan result as Web review because the host Agent did not submit "
                "a candidate plan file, so this is not a runnable Loop yet. Continue by confirming or filling "
                "in the success criteria, fake-done risks, evidence expectations, Loopora fit, execution strategy, "
                "judgment tradeoffs, residual-risk policy, and local governance responsibilities before "
                "generating a reviewable Loop preview."
            ),
        )

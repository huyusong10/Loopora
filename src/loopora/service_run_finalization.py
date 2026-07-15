from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loopora.diagnostics import get_logger, log_exception
from loopora.engine import (
    RepositoryRunEngine,
    RunEngineIssueVerdictRequest,
)
from loopora.kernel import ActorRef
from loopora.run_artifacts import RunArtifactLayout
from loopora.task_verdicts import build_task_verdict
from loopora.utils import utc_now, write_json

from collections.abc import Mapping


from loopora.compiler import compile_loop_contract

from loopora.engine import verdict_event_payload_from_kernel_verdict, verdict_from_legacy_coverage_projection

from loopora.evidence_coverage import load_or_build_evidence_coverage_projection


def kernel_event_verdict_for_finalization(
    *,
    run_id: str,
    existing_run: Mapping[str, object],
    run_dir: Path,
    last_verdict: object,
) -> dict:
    compiled_spec = _mapping(existing_run.get("compiled_spec") or existing_run.get("compiled_spec_json"))
    if not compiled_spec:
        return {}
    try:
        coverage = load_or_build_evidence_coverage_projection(RunArtifactLayout(run_dir))
    except (OSError, UnicodeError, ValueError):
        return {}
    if not isinstance(coverage.get("targets"), list):
        return {}
    loop_id = str(existing_run.get("loop_id") or run_id).strip() or run_id
    completion_mode = str(existing_run.get("completion_mode") or "gatekeeper").strip() or "gatekeeper"
    verdict = verdict_from_legacy_coverage_projection(
        compile_loop_contract(loop_id, compiled_spec, completion_mode=completion_mode),
        run_id=run_id,
        coverage_projection=coverage,
        raw_verdict=_mapping(last_verdict),
    )
    return verdict_event_payload_from_kernel_verdict(verdict)

def event_verdict_for_finalization(*, public_task_verdict: Mapping[str, object], kernel_event_verdict: Mapping[str, object]) -> dict:
    if not kernel_event_verdict:
        return dict(public_task_verdict)
    return {
        **dict(kernel_event_verdict),
        **dict(public_task_verdict),
        "next_gap": kernel_event_verdict.get("next_gap") or public_task_verdict.get("next_gap") or [],
    }

def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}

logger = get_logger(__name__)


@dataclass(frozen=True)
class TerminalRunFinalizationRequest:
    run_id: str
    run_dir: Path
    status: str
    summary: str
    error_message: str | None = None
    last_verdict: dict | None = None
    final_reason: str = ""
    hydrate: bool = False


class ServiceRunFinalizationMixin:
    def _write_summary(self, run_id: str, status: str, body: str) -> None:
        run = self.get_run(run_id)
        summary = body if body.startswith("#") else f"# Loopora Run Summary\n\nStatus: {status}\n\n{body}\n"
        self._persist_summary_file(Path(run["runs_dir"]), summary)
        self.repository.update_run(run_id, summary_md=summary)

    def _persist_summary_file(self, run_dir: Path, summary: str) -> None:
        run_dir.mkdir(parents=True, exist_ok=True)
        try:
            (run_dir / "summary.md").write_text(summary, encoding="utf-8")
        except OSError:
            log_exception(
                logger,
                "service.run.summary.persist_failed",
                "Failed to persist run summary file",
                runs_dir=run_dir,
            )

    def _write_run_verdict_files(self, run_dir: Path, verdict: dict, *, include_gatekeeper: bool = False) -> None:
        if include_gatekeeper:
            write_json(run_dir / "gatekeeper_verdict.json", verdict)
        write_json(run_dir / "verifier_verdict.json", verdict)

    def _persist_task_verdict_file(self, run_dir: Path, task_verdict: dict) -> None:
        try:
            write_json(RunArtifactLayout(run_dir).task_verdict_path, task_verdict)
        except OSError:
            log_exception(
                logger,
                "service.run.task_verdict.persist_failed",
                "Failed to persist run task verdict artifact",
                runs_dir=run_dir,
            )

    def _run_finished_event_payload(
        self,
        run: dict,
        *,
        status: str = "",
        reason: str = "",
        iter_id: int | None = None,
    ) -> dict:
        payload: dict[str, object] = {"status": str(status or run.get("status") or "").strip()}
        if reason:
            payload["reason"] = reason
        if iter_id is not None:
            payload["iter"] = iter_id
        task_verdict = run.get("task_verdict") if isinstance(run.get("task_verdict"), dict) else run.get("task_verdict_json")
        if isinstance(task_verdict, dict) and task_verdict:
            payload["task_verdict_status"] = str(task_verdict.get("status") or "").strip()
            payload["task_verdict_source"] = str(task_verdict.get("source") or "").strip()
            payload["task_verdict_summary"] = str(task_verdict.get("summary") or "").strip()
        return payload

    def _append_run_aborted_event(
        self,
        run_id: str,
        *,
        role: str | None,
        attempts: int,
        degraded: bool,
        error_text: str,
    ) -> None:
        self.append_run_event(
            run_id,
            "run_aborted",
            {
                "role": role,
                "attempts": attempts,
                "degraded": degraded,
                "error": error_text,
            },
        )

    def _finalize_terminal_run(
        self,
        request: TerminalRunFinalizationRequest,
    ) -> dict:
        self._persist_summary_file(request.run_dir, request.summary)
        existing_run = self.repository.get_run(request.run_id) or {}
        task_verdict = build_task_verdict(
            {
                **existing_run,
                "status": request.status,
                "last_verdict_json": request.last_verdict if request.last_verdict is not None else existing_run.get("last_verdict_json"),
            },
            run_dir=request.run_dir,
            final_reason=request.final_reason,
        )
        self._persist_task_verdict_file(request.run_dir, task_verdict)
        kernel_event_verdict = kernel_event_verdict_for_finalization(
            run_id=request.run_id,
            existing_run=existing_run,
            run_dir=request.run_dir,
            last_verdict=request.last_verdict if request.last_verdict is not None else existing_run.get("last_verdict_json"),
        )
        event_verdict = event_verdict_for_finalization(
            public_task_verdict=task_verdict,
            kernel_event_verdict=kernel_event_verdict,
        )
        RepositoryRunEngine(self.repository).issue_verdict(
            RunEngineIssueVerdictRequest(
                run_id=request.run_id,
                verdict=event_verdict,
                actor=ActorRef.verdict_engine(),
            )
        )
        result = self.repository.update_run(
            request.run_id,
            status=request.status,
            finished_at=utc_now(),
            error_message=request.error_message,
            last_verdict=request.last_verdict,
            task_verdict=task_verdict,
            summary_md=request.summary,
        )
        return self._hydrate_run_files(result) if request.hydrate else result

    def _finalize_crashed_run(
        self,
        run_id: str,
        run: dict,
        run_dir: Path,
        *,
        error_text: str,
        hydrate: bool = False,
    ) -> dict:
        summary = f"# Loopora Run Summary\n\nExecution crashed unexpectedly.\n\nReason: `{error_text}`.\n"
        self._persist_summary_file(run_dir, summary)
        try:
            task_verdict = build_task_verdict(
                {**run, "status": "failed"},
                run_dir=run_dir,
                final_reason="crashed",
            )
            self._persist_task_verdict_file(run_dir, task_verdict)
            failed = self.repository.update_run(
                run_id,
                status="failed",
                finished_at=utc_now(),
                error_message=error_text,
                task_verdict=task_verdict,
                summary_md=summary,
            )
            RepositoryRunEngine(self.repository).issue_verdict(
                RunEngineIssueVerdictRequest(
                    run_id=run_id,
                    verdict=task_verdict,
                    actor=ActorRef.verdict_engine(),
                )
            )
        except Exception:  # noqa: BLE001 - crash finalization must fall back to an in-memory failed state.
            log_exception(
                logger,
                "service.run.execution.crash_state_persist_failed",
                "Failed to persist crashed run state",
                **self._run_log_context(run),
            )
            return {
                **run,
                "status": "failed",
                "finished_at": utc_now(),
                "error_message": error_text,
                "summary_md": summary,
            }
        try:
            self._append_run_aborted_event(
                run_id,
                role=failed.get("active_role"),
                attempts=1,
                degraded=False,
                error_text=error_text,
            )
            self.append_run_event(
                run_id,
                "run_finished",
                self._run_finished_event_payload(failed, status="failed", reason="crashed"),
            )
        except Exception:  # noqa: BLE001 - crash event append failure must not mask the failed run state.
            log_exception(
                logger,
                "service.run.execution.crash_event_append_failed",
                "Failed to append crash event after a run crash",
                **self._run_log_context(run),
            )
        return self._hydrate_run_files(failed) if hydrate else failed

    def _cleanup_run_execution(self, run_id: str, run: dict | None, *, phase: str) -> None:
        self._mark_run_inactive(run_id)
        try:
            self.repository.release_run_slot(run_id)
        except Exception:  # noqa: BLE001 - cleanup must not raise after run execution has ended.
            log_exception(
                logger,
                "service.run.slot_release_failed",
                f"Failed to release run slot during {phase} cleanup",
                run_id=run_id,
                loop_id=run.get("loop_id") if run else None,
                workdir=run.get("workdir") if run else None,
            )
        self._threads.pop(run_id, None)

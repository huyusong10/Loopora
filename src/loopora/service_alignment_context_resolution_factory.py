from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_context_protocols import AlignmentFactoryService
from loopora.service_alignment_run_context import AlignmentRunContextResolverContext, resolve_alignment_run_context
from loopora.service_alignment_workdir_context import (
    AlignmentLooporaContextResolverContext,
    AlignmentWorkdirContextResolverContext,
    alignment_workdir_context_payload,
    resolve_plan_context_from_workdir_context,
)
from loopora.service_alignment_workdir_snapshot import alignment_same_workdir


def alignment_run_context_resolver_context(service: AlignmentFactoryService) -> AlignmentRunContextResolverContext:
    return AlignmentRunContextResolverContext(
        repository=service.repository,
        get_alignment_session=service.get_alignment_session,
        get_run=service.get_run,
        same_workdir=alignment_same_workdir,
    )


def alignment_workdir_context_resolver_context(service: AlignmentFactoryService) -> AlignmentWorkdirContextResolverContext:
    return AlignmentWorkdirContextResolverContext(
        repository=service.repository,
        list_loops=service.list_loops,
        get_run=service.get_run,
    )


def alignment_loopora_context_resolver_context(service: AlignmentFactoryService) -> AlignmentLooporaContextResolverContext:
    def workdir_context_payload(root: Path) -> dict:
        return alignment_workdir_context_payload(alignment_workdir_context_resolver_context(service), root)

    def resolve_plan_context(context: dict, *, source_option_id: str = "") -> dict:
        return resolve_plan_context_from_workdir_context(context, source_option_id=source_option_id)

    def resolve_run_context(root: Path, *, adapter: str, context_id: str) -> dict:
        return resolve_alignment_run_context(
            alignment_run_context_resolver_context(service),
            root=root,
            adapter=adapter,
            context_id=context_id,
        )

    return AlignmentLooporaContextResolverContext(
        workdir_context_payload=workdir_context_payload,
        resolve_plan_context=resolve_plan_context,
        resolve_run_context=resolve_run_context,
    )

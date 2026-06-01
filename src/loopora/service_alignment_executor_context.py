from __future__ import annotations

from loopora.service_alignment_artifacts import (
    alignment_next_invocation_dir,
    alignment_repair_attempts,
    ensure_alignment_artifact_dirs,
)
from loopora.service_alignment_context_protocols import AlignmentFactoryService
from loopora.service_alignment_invocation import (
    AlignmentExecutorInvocationConfig,
    AlignmentExecutorRunContext,
)
from loopora.service_alignment_prompting import (
    AlignmentPromptBuildContext,
    build_alignment_prompt as build_alignment_prompt_command,
)
from loopora.service_alignment_requests import ALIGNMENT_RESPONSE_SCHEMA


def alignment_executor_run_context(service: AlignmentFactoryService) -> AlignmentExecutorRunContext:
    def build_prompt(
        session: dict,
        *,
        mode: str,
        validation_error: str = "",
        invalid_yaml: str = "",
    ) -> str:
        return build_alignment_prompt_command(
            AlignmentPromptBuildContext(),
            session,
            mode=mode,
            validation_error=validation_error,
            invalid_yaml=invalid_yaml,
        )

    return AlignmentExecutorRunContext(
        repository=service.repository,
        get_session=service.get_alignment_session,
        config=AlignmentExecutorInvocationConfig(
            output_schema=ALIGNMENT_RESPONSE_SCHEMA,
            idle_timeout_seconds=service.settings.role_idle_timeout_seconds,
            executor_factory=service.executor_factory,
            build_prompt=build_prompt,
            ensure_artifact_dirs=ensure_alignment_artifact_dirs,
            next_invocation_dir=alignment_next_invocation_dir,
            repair_attempts=alignment_repair_attempts,
        ),
    )

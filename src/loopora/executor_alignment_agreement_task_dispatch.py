from __future__ import annotations

from loopora import executor_alignment_agreement_task_responses as task_responses
from loopora.executor_alignment_agreement_task_dispatch_catalog import TASK_AGREEMENT_FACTORIES
from loopora.executor_alignment_agreement_task_dispatch_types import LocalizedAgreementFactories


def alignment_task_anchored_agreement_response(
    task_text: str,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> dict:
    task = str(task_text or "").strip()
    for predicate, factories in TASK_AGREEMENT_FACTORIES:
        if predicate(task):
            return _localized_task_agreement_response(
                task,
                prefers_chinese=prefers_chinese,
                display_language=display_language,
                factories=factories,
            )
    return _localized_task_agreement_response(
        task,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
        factories=(
            task_responses.alignment_chinese_task_anchored_agreement_response,
            task_responses.alignment_spanish_task_anchored_agreement_response,
            task_responses.alignment_english_task_anchored_agreement_response,
        ),
    )


def _localized_task_agreement_response(
    task: str,
    *,
    prefers_chinese: bool,
    display_language: str,
    factories: LocalizedAgreementFactories,
) -> dict:
    chinese_factory, spanish_factory, english_factory = factories
    if prefers_chinese:
        return chinese_factory(task)
    if str(display_language or "").strip().lower() == "es":
        return spanish_factory(task)
    return english_factory(task)

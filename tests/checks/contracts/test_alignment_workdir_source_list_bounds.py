from __future__ import annotations

from pathlib import Path


ALIGNMENT_WORKDIR_CONTEXT_OPTION_LIMIT = 20


def test_alignment_workdir_context_preserves_regenerate_option_when_source_list_is_bounded(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    for index in range(25):
        service.create_alignment_session(
            workdir=sample_workdir,
            message=f"Existing alignment source {index}",
            start_immediately=False,
        )

    context = service.get_alignment_workdir_context(sample_workdir)
    option_ids = [option["option_id"] for option in context["options"]]

    assert len(context["options"]) == ALIGNMENT_WORKDIR_CONTEXT_OPTION_LIMIT
    assert context["requires_choice"] is True
    assert context["recommended_option_id"] == ""
    assert option_ids[-1] == "regenerate"
    assert sum(option_id == "regenerate" for option_id in option_ids) == 1

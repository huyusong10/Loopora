from __future__ import annotations

from pathlib import Path


CHINESE_ALIGNMENT_REQUEST = "请帮我编排一个中文任务的 Loop。"


def create_chinese_alignment_session(service_factory, sample_workdir: Path, *, scenario: str) -> tuple[object, dict]:
    service = service_factory(scenario=scenario)
    created = service.create_alignment_session(
        workdir=sample_workdir,
        message=CHINESE_ALIGNMENT_REQUEST,
    )
    return service, created

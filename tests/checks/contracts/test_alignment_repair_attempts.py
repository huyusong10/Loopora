from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_artifacts import alignment_invocation_dir, alignment_repair_attempts


INVALID_REPAIR_ATTEMPT_DEFAULT = 7
NORMALIZED_REPAIR_ATTEMPTS = 3


def test_alignment_repair_attempts_normalizes_invalid_values() -> None:
    assert alignment_repair_attempts({"repair_attempts": NORMALIZED_REPAIR_ATTEMPTS}) == NORMALIZED_REPAIR_ATTEMPTS
    assert alignment_repair_attempts({"repair_attempts": -1}) == 0
    assert alignment_repair_attempts({"repair_attempts": "bad"}, invalid_default=INVALID_REPAIR_ATTEMPT_DEFAULT) == INVALID_REPAIR_ATTEMPT_DEFAULT
    assert alignment_repair_attempts({}) == 0


def test_alignment_repair_attempts_require_integer_sequence(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a focused starter experience.",
    )

    updated = service.repository.update_alignment_session(session["id"], repair_attempts="2")

    assert updated["repair_attempts"] == 0
    assert alignment_repair_attempts({"repair_attempts": None}) == 0
    assert alignment_repair_attempts({"repair_attempts": "1"}, invalid_default=1) == 1
    assert alignment_invocation_dir(sample_workdir, "2", repair=False).name == "0001"

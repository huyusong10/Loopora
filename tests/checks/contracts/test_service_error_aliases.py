from __future__ import annotations

from loopora.service_types import StopRequested, StopRequestedError


def test_stop_requested_legacy_exception_alias_remains_compatible() -> None:
    assert StopRequested is StopRequestedError

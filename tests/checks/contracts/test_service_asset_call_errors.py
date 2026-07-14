from __future__ import annotations

import pytest

from loopora.service import LooporaError
from loopora.service_types import LooporaNotFoundError, StopRequested, StopRequestedError


def test_stop_requested_legacy_exception_alias_remains_compatible() -> None:
    assert StopRequested is StopRequestedError


def test_asset_call_does_not_classify_plain_unknown_validation_errors_as_not_found(service_factory) -> None:
    service = service_factory(scenario="success")

    with pytest.raises(LooporaError, match="unknown is just part of this validation message") as exc_info:
        service._asset_call(lambda: (_ for _ in ()).throw(ValueError("unknown is just part of this validation message")))

    assert not isinstance(exc_info.value, LooporaNotFoundError)

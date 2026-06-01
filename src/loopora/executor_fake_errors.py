from __future__ import annotations


class FakePayloadError(RuntimeError):
    """Raised when the fake executor scenario should fail like a provider failure."""

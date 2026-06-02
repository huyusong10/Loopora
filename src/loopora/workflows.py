from __future__ import annotations

"""Legacy workflow import compatibility.

Production code should import Strategy Source helpers through `loopora.strategy_source`.
"""

from loopora import strategy_source_definitions as _definitions

__all__ = sorted(name for name in dir(_definitions) if not name.startswith("_"))  # noqa: PLE0605 - legacy workflow facade mirrors Strategy Source exports dynamically.
globals().update({name: getattr(_definitions, name) for name in __all__})

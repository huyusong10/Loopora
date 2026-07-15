from __future__ import annotations

"""Compatibility imports for the public workflow API.

New code should use :mod:`loopora.strategy_source`; this facade keeps existing
integrations working without duplicating the implementation.
"""

from loopora import strategy_source_definitions as _definitions

__all__ = sorted(name for name in dir(_definitions) if not name.startswith("_"))  # noqa: PLE0605
globals().update({name: getattr(_definitions, name) for name in __all__})

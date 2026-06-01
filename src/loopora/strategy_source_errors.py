from __future__ import annotations


class StrategySourceError(ValueError):
    """Raised when strategy source or prompt files are invalid."""


WorkflowError = StrategySourceError

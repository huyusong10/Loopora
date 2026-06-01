from __future__ import annotations


class AssetCatalogError(ValueError):
    """Base error for strategy asset catalog validation failures."""


class AssetCatalogNotFoundError(AssetCatalogError):
    """Raised when a stable role definition or orchestration asset is missing."""

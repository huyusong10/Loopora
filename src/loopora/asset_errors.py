from __future__ import annotations


def asset_mutation_error_message(exc: BaseException, *, asset_label: str, action: str = "saved") -> str:
    if isinstance(exc, OSError | UnicodeError):
        return f"{asset_label} could not be {action}"
    return str(exc)

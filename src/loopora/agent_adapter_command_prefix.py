from __future__ import annotations

import os
import shlex

from loopora.branding import APP_HOME_ENV


def loopora_command_env_prefix(*, entry_source: str = "") -> str:
    bits: list[str] = []
    configured_home = os.environ.get(APP_HOME_ENV, "").strip()
    if configured_home:
        bits.append(f"{APP_HOME_ENV}={shlex.quote(configured_home)}")
    normalized_entry_source = str(entry_source or "").strip()
    if normalized_entry_source:
        bits.append(f"LOOPORA_AGENT_ENTRY_SOURCE={shlex.quote(normalized_entry_source)}")
    return " ".join(bits)


def prefix_loopora_command(command: str, *, entry_source: str = "") -> str:
    prefix = loopora_command_env_prefix(entry_source=entry_source)
    return f"{prefix} {command}" if prefix else command

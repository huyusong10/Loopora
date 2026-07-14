from __future__ import annotations

from pathlib import Path
import shlex

from loopora.agent_adapter_command_prefix import copyable_loopora_command


def copyable_recovery_archive_command(workdir: Path | str | None = None) -> str:
    workdir_arg = _recovery_workdir_arg(workdir)
    return copyable_loopora_command(f"loopora recovery create --workdir {workdir_arg}")


def recovery_archive_action(command: str, *, after_action: str = "") -> dict[str, object]:
    action: dict[str, object] = {
        "kind": "create_recovery_archive",
        "command": command,
        "private_content": True,
        "public_safe": False,
        "note": "Create and inspect a private exact-path archive before deleting useful local history.",
    }
    if after_action:
        action["after_action"] = after_action
    return action


def _recovery_workdir_arg(workdir: Path | str | None) -> str:
    if workdir is None or not str(workdir).strip():
        return "<project>"
    return shlex.quote(str(Path(workdir).expanduser().resolve(strict=False)))


__all__ = ["copyable_recovery_archive_command", "recovery_archive_action"]

from __future__ import annotations

import os
import re
import shlex
import sys
import tomllib
from collections.abc import Iterable
from pathlib import Path

from loopora.branding import APP_HOME_ENV, app_home_path

DEFAULT_LOOPORA_CLI_ENTRY = "loopora"
_ENV_ASSIGNMENT_TOKEN = re.compile(r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>.*)", re.DOTALL)
LOOPORA_HELP_COMMAND_PREFIXES = (
    "loopora orchestrations",
    "loopora diagnose",
    "loopora recovery",
    "loopora uninstall",
    "loopora bundles",
    "loopora prompts",
    "loopora doctor",
    "loopora support",
    "loopora --version",
    "loopora version",
    "loopora loops",
    "loopora start",
    "loopora roles",
    "loopora serve",
    "loopora agent",
    "loopora spec",
    "loopora init",
    "loopora run",
    "loopora fit",
    "loopora dev",
)


def normalize_loopora_cli_entry(cli_entry: str) -> str:
    tokens = shlex.split(str(cli_entry or "").strip() or DEFAULT_LOOPORA_CLI_ENTRY)
    return shell_join_loopora_command(tokens) or DEFAULT_LOOPORA_CLI_ENTRY


def shell_join_loopora_command(parts: Iterable[object]) -> str:
    rendered: list[str] = []
    before_command = True
    for raw_part in parts:
        part = str(raw_part)
        assignment = _ENV_ASSIGNMENT_TOKEN.fullmatch(part) if before_command else None
        if assignment:
            rendered.append(f"{assignment.group('name')}={shlex.quote(assignment.group('value'))}")
            continue
        before_command = False
        rendered.append(shlex.quote(part))
    return " ".join(rendered)


def current_loopora_cli_entry() -> str:
    argv0 = Path(str(sys.argv[0] or ""))
    argv0_name = argv0.name.lower()
    uv_prefix = "uv run " if os.environ.get("UV_RUN_RECURSION_DEPTH", "").strip() else ""
    if argv0_name in {"loopora", "loopora.exe"}:
        return f"{uv_prefix}loopora".strip()
    if argv0_name == "__main__.py" and argv0.parent.name == "loopora":
        return f"{uv_prefix}python -m loopora".strip()
    return DEFAULT_LOOPORA_CLI_ENTRY


def current_project_file_loopora_cli_entry() -> str:
    cli_entry = current_loopora_cli_entry()
    if not os.environ.get("UV_RUN_RECURSION_DEPTH", "").strip():
        return cli_entry
    source_root = loopora_source_checkout_root()
    if source_root is None:
        return cli_entry
    tokens = shlex.split(cli_entry)
    if tokens == ["uv", "run", "loopora"]:
        return f"uv --directory {shlex.quote(str(source_root))} run loopora"
    if tokens == ["uv", "run", "python", "-m", "loopora"]:
        return f"uv --directory {shlex.quote(str(source_root))} run python -m loopora"
    return cli_entry


def current_copyable_loopora_cli_entry() -> str:
    return prefix_loopora_command(current_project_file_loopora_cli_entry())


def loopora_source_checkout_root(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    candidates = (current, *current.parents)
    for candidate in candidates:
        pyproject = candidate / "pyproject.toml"
        source_package = candidate / "src" / "loopora"
        if not pyproject.is_file() or not source_package.is_dir():
            continue
        try:
            payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        project = payload.get("project")
        if isinstance(project, dict) and project.get("name") == "loopora":
            return candidate
    return None


def rewrite_loopora_command_entry(command: str, *, cli_entry: str = DEFAULT_LOOPORA_CLI_ENTRY) -> str:
    normalized_entry = normalize_loopora_cli_entry(cli_entry)
    if normalized_entry == DEFAULT_LOOPORA_CLI_ENTRY:
        return command
    if command == DEFAULT_LOOPORA_CLI_ENTRY:
        return normalized_entry
    if command.startswith(f"{DEFAULT_LOOPORA_CLI_ENTRY} "):
        return f"{normalized_entry} {command[len(DEFAULT_LOOPORA_CLI_ENTRY) + 1:]}"
    marker = f" {DEFAULT_LOOPORA_CLI_ENTRY} "
    if marker in command:
        return command.replace(marker, f" {normalized_entry} ", 1)
    suffix = f" {DEFAULT_LOOPORA_CLI_ENTRY}"
    if command.endswith(suffix):
        return f"{command[: -len(suffix)]} {normalized_entry}"
    return command


def rewrite_loopora_help_commands(help_text: str) -> str:
    cli_entry = current_project_file_loopora_cli_entry()
    if cli_entry == DEFAULT_LOOPORA_CLI_ENTRY:
        return help_text
    adapted = help_text
    for command in LOOPORA_HELP_COMMAND_PREFIXES:
        adapted = _rewrite_loopora_help_command_occurrences(adapted, command, cli_entry=cli_entry)
    return adapted


def _rewrite_loopora_help_command_occurrences(help_text: str, command: str, *, cli_entry: str) -> str:
    replacement = rewrite_loopora_command_entry(command, cli_entry=cli_entry)
    if replacement == command or command not in help_text:
        return help_text
    entry_prefix_len = max(0, len(cli_entry) - len(DEFAULT_LOOPORA_CLI_ENTRY))
    parts: list[str] = []
    cursor = 0
    for match in re.finditer(re.escape(command), help_text):
        command_start = match.start()
        entry_start = command_start - entry_prefix_len
        already_rewritten = (
            entry_start >= 0
            and help_text[entry_start : command_start + len(DEFAULT_LOOPORA_CLI_ENTRY)] == cli_entry
        )
        parts.append(help_text[cursor:command_start])
        parts.append(command if already_rewritten else replacement)
        cursor = match.end()
    parts.append(help_text[cursor:])
    return "".join(parts)


def copyable_loopora_command(command: str, *, entry_source: str = "") -> str:
    return prefix_loopora_command(
        rewrite_loopora_command_entry(command, cli_entry=current_project_file_loopora_cli_entry()),
        entry_source=entry_source,
    )


def loopora_command_env_prefix(*, entry_source: str = "") -> str:
    bits: list[str] = []
    configured_home = os.environ.get(APP_HOME_ENV, "").strip()
    if configured_home:
        bits.append(f"{APP_HOME_ENV}={shlex.quote(str(app_home_path()))}")
    normalized_entry_source = str(entry_source or "").strip()
    if normalized_entry_source:
        bits.append(f"LOOPORA_AGENT_ENTRY_SOURCE={shlex.quote(normalized_entry_source)}")
    return " ".join(bits)


def prefix_loopora_command(command: str, *, entry_source: str = "") -> str:
    prefix = loopora_command_env_prefix(entry_source=entry_source)
    return f"{prefix} {command}" if prefix else command

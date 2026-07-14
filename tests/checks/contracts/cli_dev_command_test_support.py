from __future__ import annotations

from pathlib import Path
import shlex
import tarfile
from zipfile import ZipFile

from loopora import agent_adapter_command_prefix
from loopora.agent_adapter_templates import managed_templates
from loopora.cli_dev_commands import DEV_COMMAND_ERROR_SCHEMA_VERSION
from loopora.dev_check_command_projection import dev_check_default_fast_command
from loopora.dev_check_command_projection import dev_check_focused_command
from loopora.dev_check_command_projection import dev_check_list_command as projected_dev_check_list_command


def result_error_text(result) -> str:
    try:
        return result.stderr
    except ValueError:
        return result.output


def dev_check_command(workdir: Path) -> str:
    return dev_check_default_fast_command(workdir)


def dev_check_list_command(workdir: Path, changed_files: list[str] | None = None) -> str:
    return projected_dev_check_list_command(workdir, changed_files=changed_files)


def cli_dev_check_command(workdir: Path, args: str = "", changed_files: list[str] | None = None) -> str:
    command = agent_adapter_command_prefix.copyable_loopora_command(f"loopora dev check{f' {args}' if args else ''}")
    return command_with_workdir(command_with_changed_files(command, changed_files), workdir)


def focused_dev_check_command(workdir: Path, selection: str, changed_files: list[str] | None = None) -> str:
    return dev_check_focused_command(selection, workdir=workdir, changed_files=changed_files)


def cli_focused_dev_check_command(workdir: Path, selection: str, changed_files: list[str] | None = None) -> str:
    focused_args = " ".join(f"--focused {shlex.quote(token)}" for token in selection.replace(",", " ").split())
    command = agent_adapter_command_prefix.copyable_loopora_command(f"loopora dev check {focused_args}")
    return command_with_workdir(command_with_changed_files(command, changed_files), workdir)


def focused_command_targets(command: str) -> tuple[Path, ...]:
    return tuple(Path(part) for part in shlex.split(command) if part.startswith("tests/"))


def command_with_changed_files(command: str, changed_files: list[str] | None) -> str:
    paths = sorted(path for path in list(changed_files or []) if path.strip())
    if not paths:
        return command
    args = " ".join(f"--changed-file {shlex.quote(path)}" for path in paths)
    return f"{command} {args}"


def command_with_workdir(command: str, workdir: Path) -> str:
    resolved = workdir.resolve()
    if resolved == Path.cwd().resolve():
        return command
    return f"{command} --workdir {shlex.quote(str(resolved))}"


def dev_workdir_error_payload(command: str) -> dict:
    return {
        "ready": False,
        "status": "error",
        "error": "workdir does not exist",
        "dev_command_error": {
            "schema_version": DEV_COMMAND_ERROR_SCHEMA_VERSION,
            "command": command,
            "state": "blocked_by_workdir",
        },
    }


def create_reset_fixture(tmp_path: Path, *, include_wal: bool = False, include_unmanaged: bool = False) -> dict[str, Path]:
    workdir = tmp_path / "project"
    home = tmp_path / "home"
    workdir.mkdir()
    home.mkdir()
    paths = {
        "workdir": workdir,
        "home": home,
        "db": home / "app.db",
        "wal": home / "app.db-wal",
        "state": workdir / ".loopora" / "runs" / "run_old" / "state.json",
        "managed": workdir / ".codex" / "agents" / "loopora-builder.toml",
        "unmanaged": workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md",
    }
    paths["db"].write_text("legacy-db", encoding="utf-8")
    if include_wal:
        paths["wal"].write_text("wal", encoding="utf-8")
    paths["state"].parent.mkdir(parents=True)
    paths["state"].write_text("{}", encoding="utf-8")
    paths["managed"].parent.mkdir(parents=True)
    paths["managed"].write_text(managed_templates("codex")[".codex/agents/loopora-builder.toml"], encoding="utf-8")
    if include_unmanaged:
        paths["unmanaged"].parent.mkdir(parents=True)
        paths["unmanaged"].write_text("# user-owned file\n", encoding="utf-8")
    return paths


def write_package_artifacts(
    root: Path,
    *,
    include_entry_points: bool = True,
    include_module_entry: bool = True,
    include_forbidden_artifacts: bool = False,
    metadata_text: str = "",
) -> None:
    source_provenance_text = '{"revision": "0123456789ab", "schema_version": 1, "tree_status": "clean"}\n'
    output_dir = root / "tmp" / "package-check"
    output_dir.mkdir(parents=True, exist_ok=True)
    module_entry = root / "src" / "loopora" / "__main__.py"
    write_text(module_entry, "from loopora.cli import app\n\napp()\n")
    with ZipFile(output_dir / "loopora-0.1.0-py3-none-any.whl", "w") as wheel:
        wheel.writestr("loopora-0.1.0.dist-info/METADATA", metadata_text or package_metadata_text())
        if include_entry_points:
            wheel.writestr("loopora-0.1.0.dist-info/entry_points.txt", "[console_scripts]\nloopora = loopora.cli:app\n")
        if include_module_entry:
            wheel.writestr("loopora/__main__.py", module_entry.read_text(encoding="utf-8"))
        wheel.writestr("loopora/_build_provenance.json", source_provenance_text)
        if include_forbidden_artifacts:
            wheel.writestr("tests/private.py", "private\n")
    with tarfile.open(output_dir / "loopora-0.1.0.tar.gz", "w:gz") as sdist:
        placeholder = root / "pyproject.toml"
        write_text(placeholder, pyproject_text())
        sdist.add(placeholder, arcname="loopora-0.1.0/pyproject.toml")
        setup_file = root / "setup.py"
        write_text(setup_file, "from setuptools import setup\n\nsetup()\n")
        sdist.add(setup_file, arcname="loopora-0.1.0/setup.py")
        if include_module_entry:
            sdist.add(module_entry, arcname="loopora-0.1.0/src/loopora/__main__.py")
        source_provenance = root / "src" / "loopora" / "_build_provenance.json"
        write_text(source_provenance, source_provenance_text)
        sdist.add(source_provenance, arcname="loopora-0.1.0/src/loopora/_build_provenance.json")
        if include_forbidden_artifacts:
            private = root / "tests" / "private.py"
            write_text(private, "private\n")
            sdist.add(private, arcname="loopora-0.1.0/tests/private.py")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def package_metadata_text() -> str:
    return """Metadata-Version: 2.4
Name: loopora
Version: 0.1.0
Summary: Evidence-governed Loops for long-running AI Agent tasks.
Author: Loopora contributors
Maintainer: Loopora maintainers
Keywords: ai-agents,agent-workflows,evidence,human-in-the-loop,local-first,long-running-agents
Project-URL: Homepage, https://github.com/huyusong10/Loopora
Project-URL: Changelog, https://github.com/huyusong10/Loopora/blob/dev/CHANGELOG.md
Project-URL: Community, https://github.com/huyusong10/Loopora/blob/dev/CODE_OF_CONDUCT.md
Project-URL: Documentation, https://github.com/huyusong10/Loopora/blob/dev/README.md
Project-URL: Governance, https://github.com/huyusong10/Loopora/blob/dev/GOVERNANCE.md
Project-URL: Issues, https://github.com/huyusong10/Loopora/issues
Project-URL: Repository, https://github.com/huyusong10/Loopora
Project-URL: Security, https://github.com/huyusong10/Loopora/security/policy
Project-URL: Support, https://github.com/huyusong10/Loopora/blob/dev/SUPPORT.md
Requires-Python: >=3.11
Requires-Dist: fastapi>=0.115.0
Requires-Dist: typer>=0.12.0
Description-Content-Type: text/markdown"""


def pyproject_text() -> str:
    return """
[project]
name = "loopora"
version = "0.1.0"
description = "Evidence-governed Loops for long-running AI Agent tasks."
readme = "README.md"
requires-python = ">=3.11"
dependencies = ["fastapi>=0.115.0", "typer>=0.12.0"]
authors = [{ name = "Loopora contributors" }]
maintainers = [{ name = "Loopora maintainers" }]
keywords = ["ai-agents", "agent-workflows", "evidence", "human-in-the-loop", "local-first", "long-running-agents"]
classifiers = []
[project.urls]
Homepage = "https://github.com/huyusong10/Loopora"
Changelog = "https://github.com/huyusong10/Loopora/blob/dev/CHANGELOG.md"
Community = "https://github.com/huyusong10/Loopora/blob/dev/CODE_OF_CONDUCT.md"
Documentation = "https://github.com/huyusong10/Loopora/blob/dev/README.md"
Governance = "https://github.com/huyusong10/Loopora/blob/dev/GOVERNANCE.md"
Repository = "https://github.com/huyusong10/Loopora"
Issues = "https://github.com/huyusong10/Loopora/issues"
Security = "https://github.com/huyusong10/Loopora/security/policy"
Support = "https://github.com/huyusong10/Loopora/blob/dev/SUPPORT.md"
[project.scripts]
loopora = "loopora.cli:app"
"""

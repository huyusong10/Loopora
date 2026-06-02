from __future__ import annotations

import ast

from kernel_architecture_test_support import REPO_ROOT


FORBIDDEN_CORE_IMPORT_PREFIXES = (
    "fastapi",
    "typer",
    "loopora.web",
    "loopora.web_route",
    "loopora.cli",
    "loopora.agent_adapter",
    "loopora.agent_native",
    "loopora.service",
)


def test_kernel_events_and_projections_do_not_depend_on_surfaces_or_adapters() -> None:
    offenders: list[tuple[str, str]] = []
    for directory in ("src/loopora/kernel", "src/loopora/events", "src/loopora/projections", "src/loopora/runners"):
        for path in sorted((REPO_ROOT / directory).glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    offenders.extend(
                        (str(path.relative_to(REPO_ROOT)), alias.name)
                        for alias in node.names
                        if alias.name.startswith(FORBIDDEN_CORE_IMPORT_PREFIXES)
                    )
                elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(FORBIDDEN_CORE_IMPORT_PREFIXES):
                    offenders.append((str(path.relative_to(REPO_ROOT)), node.module))

    assert offenders == []

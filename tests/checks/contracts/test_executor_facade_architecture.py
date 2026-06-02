from __future__ import annotations

import ast

from executor_architecture_test_support import REPO_ROOT


def test_executor_facade_is_public_compatibility_layer_only() -> None:
    offenders: list[tuple[str, str]] = []
    for path in sorted((REPO_ROOT / "src" / "loopora").rglob("*.py")):
        if path.name == "executor.py":
            continue
        relative = str(path.relative_to(REPO_ROOT))
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "loopora.executor":
                offenders.extend((relative, alias.name) for alias in node.names)
            if isinstance(node, ast.Import):
                offenders.extend(
                    (relative, alias.name)
                    for alias in node.names
                    if alias.name == "loopora.executor" or alias.name.startswith("loopora.executor.")
                )

    assert offenders == []

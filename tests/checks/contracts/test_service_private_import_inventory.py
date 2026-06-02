from __future__ import annotations

import ast

from service_architecture_test_support import (
    REPO_ROOT,
    SERVICE_PRIVATE_IMPORT_ALLOWLIST,
    design_contracts_source,
)


def test_service_private_helper_imports_do_not_grow_without_inventory() -> None:
    assert not SERVICE_PRIVATE_IMPORT_ALLOWLIST
    offenders: list[tuple[str, str, str]] = []
    for path in sorted((REPO_ROOT / "src" / "loopora").glob("service*.py")):
        relative = str(path.relative_to(REPO_ROOT))
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module or not node.module.startswith("loopora.service"):
                continue
            offenders.extend(
                (relative, node.module, alias.name)
                for alias in node.names
                if alias.name.startswith("_") and (relative, node.module, alias.name) not in SERVICE_PRIVATE_IMPORT_ALLOWLIST
            )

    assert offenders == []


def test_service_boundary_inventory_documents_private_import_retirement() -> None:
    inventory = design_contracts_source()

    assert "Service-to-service private helper imports are retired" in inventory
    assert "LooporaServiceRuntime" in inventory
    assert "AgentNativeService" in inventory
    assert "ProjectionService" in inventory
    assert "AlignmentService" in inventory
    assert "service_alignment_context_factory.py" in inventory
    assert "service_alignment.py" in inventory
    assert all(name in inventory for name in ("alignment_traceability_terms.py", "alignment_traceability_categories.py"))
    assert "remaining extraction target is small compatibility helpers in `service_alignment.py`" not in inventory

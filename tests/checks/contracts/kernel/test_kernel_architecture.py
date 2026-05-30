from __future__ import annotations

import ast
from pathlib import Path

from loopora.events import CORE_EVENT_AGGREGATE_TYPES, CORE_EVENT_TYPES


REPO_ROOT = Path(__file__).resolve().parents[4]
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


def test_event_replay_projection_modules_are_split_by_read_model() -> None:
    projection_dir = REPO_ROOT / "src" / "loopora" / "projections"

    assert (projection_dir / "evidence_ledger.py").exists()
    assert (projection_dir / "evidence_coverage.py").exists()
    assert (projection_dir / "run_snapshot.py").exists()
    assert (projection_dir / "current_step.py").exists()
    assert (projection_dir / "loop_definition.py").exists()
    assert (projection_dir / "task_verdict.py").exists()
    assert (projection_dir / "audit_timeline.py").exists()


def test_core_event_schema_excludes_surface_observability_events() -> None:
    surface_events = {
        "WebPageOpened",
        "AgentCommandRendered",
        "CliJsonPrinted",
        "HostTraceObserved",
        "TodoUpdated",
        "AdapterCheckPassed",
        "StatuslineRead",
    }

    assert CORE_EVENT_TYPES.isdisjoint(surface_events)


def test_core_event_schema_binds_event_types_to_aggregate_families() -> None:
    assert set(CORE_EVENT_AGGREGATE_TYPES) == CORE_EVENT_TYPES
    assert CORE_EVENT_AGGREGATE_TYPES["LoopActivated"] == "loop"
    assert CORE_EVENT_AGGREGATE_TYPES["RunStarted"] == "run"
    assert CORE_EVENT_AGGREGATE_TYPES["StepInstructionIssued"] == "run"
    assert CORE_EVENT_AGGREGATE_TYPES["EvidenceAccepted"] == "run"
    assert CORE_EVENT_AGGREGATE_TYPES["VerdictIssued"] == "run"
    assert CORE_EVENT_AGGREGATE_TYPES["IterationStarted"] == "run"

"""Measure Loopora's repository-level complexity budget.

The default mode reports every metric. ``--enforce`` exits non-zero while any
accepted target in ``design/complexity-budget.md`` is unmet.
"""

from __future__ import annotations

import argparse
import ast
from collections.abc import Iterable
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import subprocess
import sys
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src" / "loopora"
CONTRACT_ROOT = PROJECT_ROOT / "tests" / "checks" / "contracts"
DESIGN_ROOT = PROJECT_ROOT / "design"
PYPROJECT = PROJECT_ROOT / "pyproject.toml"

STRUCTURAL_MIRROR_MARKERS = (
    "loopora_source(",
    "read_text(",
    "ast.parse(",
    "design_contracts_source(",
    "service_boundaries_source(",
)


@dataclass(frozen=True)
class Budget:
    production_files: int = 600
    production_lines: int = 100_000
    modules_per_kloc: float = 6.0
    root_modules: int = 450
    thin_module_share: float = 0.25
    import_data_only_share: float = 0.08
    import_cycles: int = 0
    visible_root_commands: int = 8
    root_help_lines: int = 32
    runtime_dependencies: int = 7
    contract_files: int = 400
    contract_lines: int = 80_000
    structural_mirror_share: float = 0.15
    design_lines: int = 900
    readme_lines: int = 600
    source_bytes: int = 8 * 1024 * 1024


@dataclass(frozen=True)
class Metrics:
    production_files: int
    production_lines: int
    modules_per_kloc: float
    root_modules: int
    thin_modules: int
    thin_module_share: float
    import_data_only_modules: int
    import_data_only_share: float
    import_cycles: int
    largest_import_cycle: int
    visible_root_commands: int
    root_help_lines: int
    runtime_dependencies: int
    contract_files: int
    contract_lines: int
    structural_mirror_files: int
    structural_mirror_lines: int
    structural_mirror_share: float
    design_lines: int
    readme_lines: int
    source_bytes: int


@dataclass(frozen=True)
class Check:
    metric: str
    value: int | float
    target: int | float
    passed: bool
    display_value: str
    display_target: str


def _python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def _module_name(path: Path) -> str:
    relative = path.relative_to(SOURCE_ROOT).with_suffix("")
    parts = list(relative.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(("loopora", *parts)) if parts else "loopora"


def _absolute_import_base(node: ast.ImportFrom, current_module: str) -> str:
    if not node.level:
        return node.module or ""
    package_parts = current_module.split(".")[:-1]
    keep = max(0, len(package_parts) - node.level + 1)
    prefix = package_parts[:keep]
    return ".".join((*prefix, node.module)) if node.module else ".".join(prefix)


def _longest_module_prefix(name: str, modules: set[str]) -> str | None:
    candidates = [module for module in modules if name == module or name.startswith(f"{module}.")]
    return max(candidates, key=len, default=None)


def _import_targets(node: ast.AST, current_module: str, modules: set[str]) -> set[str]:
    targets: set[str] = set()
    if isinstance(node, ast.Import):
        for alias in node.names:
            target = _longest_module_prefix(alias.name, modules)
            if target:
                targets.add(target)
        return targets
    if not isinstance(node, ast.ImportFrom):
        return targets
    base = _absolute_import_base(node, current_module)
    alias_targets = {candidate for alias in node.names if (candidate := _longest_module_prefix(f"{base}.{alias.name}", modules))}
    if alias_targets:
        targets.update(alias_targets)
    elif target := _longest_module_prefix(base, modules):
        targets.add(target)
    return targets


def _strongly_connected_components(graph: dict[str, set[str]]) -> list[list[str]]:  # noqa: C901 - Tarjan traversal is one stateful algorithm.
    index = 0
    indices: dict[str, int] = {}
    low_links: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        low_links[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in graph[node]:
            if target not in graph:
                continue
            if target not in indices:
                visit(target)
                low_links[node] = min(low_links[node], low_links[target])
            elif target in on_stack:
                low_links[node] = min(low_links[node], indices[target])
        if low_links[node] != indices[node]:
            return
        component: list[str] = []
        while True:
            target = stack.pop()
            on_stack.remove(target)
            component.append(target)
            if target == node:
                break
        components.append(component)

    for node in graph:
        if node not in indices:
            visit(node)
    return components


def _source_structure(paths: list[Path]) -> tuple[int, int, int, int]:
    modules = {_module_name(path) for path in paths}
    graph: dict[str, set[str]] = {}
    import_data_only = 0
    for path in paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        module = _module_name(path)
        graph[module] = set().union(*(_import_targets(node, module, modules) for node in ast.walk(tree))) - {module}
        statements = [
            node
            for node in tree.body
            if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str))
        ]
        if statements and all(isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign)) for node in statements):
            import_data_only += 1
    cycles = [component for component in _strongly_connected_components(graph) if len(component) > 1]
    return import_data_only, len(cycles), max((len(component) for component in cycles), default=0), len(graph)


def _visible_root_commands_and_help_lines() -> tuple[int, int]:
    from loopora.cli import app

    command = [sys.executable, "-m", "loopora", "--help"]
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        env={**dict(__import__("os").environ), "NO_COLOR": "1", "COLUMNS": "120"},
    )
    lines = result.stdout.splitlines()
    visible_commands = sum(command_info.hidden is not True for command_info in app.registered_commands)
    visible_commands += sum(group.hidden is not True for group in app.registered_groups)
    return visible_commands, len(lines)


def _tree_bytes(root: Path) -> int:
    return sum(
        path.stat().st_size
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    )


def measure() -> Metrics:
    source_paths = _python_files(SOURCE_ROOT)
    source_line_counts = [_line_count(path) for path in source_paths]
    production_lines = sum(source_line_counts)
    import_data_only, import_cycles, largest_import_cycle, production_files = _source_structure(source_paths)

    contract_paths = _python_files(CONTRACT_ROOT)
    contract_line_counts = {path: _line_count(path) for path in contract_paths}
    structural_paths = [
        path
        for path in contract_paths
        if any(marker in path.read_text(encoding="utf-8") for marker in STRUCTURAL_MIRROR_MARKERS)
    ]
    contract_lines = sum(contract_line_counts.values())
    structural_lines = sum(contract_line_counts[path] for path in structural_paths)

    visible_commands, help_lines = _visible_root_commands_and_help_lines()
    with PYPROJECT.open("rb") as handle:
        pyproject = tomllib.load(handle)
    design_paths = [*DESIGN_ROOT.glob("*.md"), *DESIGN_ROOT.glob("decisions/*.md")]

    return Metrics(
        production_files=production_files,
        production_lines=production_lines,
        modules_per_kloc=round(production_files / (production_lines / 1000), 2),
        root_modules=sum(path.parent == SOURCE_ROOT for path in source_paths),
        thin_modules=sum(line_count <= 80 for line_count in source_line_counts),
        thin_module_share=round(sum(line_count <= 80 for line_count in source_line_counts) / production_files, 4),
        import_data_only_modules=import_data_only,
        import_data_only_share=round(import_data_only / production_files, 4),
        import_cycles=import_cycles,
        largest_import_cycle=largest_import_cycle,
        visible_root_commands=visible_commands,
        root_help_lines=help_lines,
        runtime_dependencies=len(pyproject["project"]["dependencies"]),
        contract_files=len(contract_paths),
        contract_lines=contract_lines,
        structural_mirror_files=len(structural_paths),
        structural_mirror_lines=structural_lines,
        structural_mirror_share=round(structural_lines / contract_lines, 4),
        design_lines=sum(_line_count(path) for path in design_paths),
        readme_lines=_line_count(PROJECT_ROOT / "README.md") + _line_count(PROJECT_ROOT / "README.zh-CN.md"),
        source_bytes=_tree_bytes(SOURCE_ROOT),
    )


def checks(metrics: Metrics, budget: Budget) -> list[Check]:
    percent_metrics = {"thin_module_share", "import_data_only_share", "structural_mirror_share"}
    byte_metrics = {"source_bytes"}
    ignored_metrics = {"thin_modules", "import_data_only_modules", "largest_import_cycle", "structural_mirror_files", "structural_mirror_lines"}
    results: list[Check] = []
    for metric, target in asdict(budget).items():
        if metric in ignored_metrics:
            continue
        value = getattr(metrics, metric)
        if metric in percent_metrics:
            display_value = f"{value:.1%}"
            display_target = f"<= {target:.0%}"
        elif metric in byte_metrics:
            display_value = f"{value / 1024 / 1024:.2f} MiB"
            display_target = f"<= {target / 1024 / 1024:.0f} MiB"
        else:
            display_value = f"{value:,}" if isinstance(value, int) else str(value)
            display_target = f"<= {target:,}" if isinstance(target, int) else f"<= {target}"
        results.append(Check(metric, value, target, value <= target, display_value, display_target))
    return results


def _render(metrics: Metrics, results: Iterable[Check]) -> None:
    lines = [
        "Loopora complexity budget",
        f"production: {metrics.production_files:,} files / {metrics.production_lines:,} lines / {metrics.modules_per_kloc} modules per KLOC",
        f"fragmentation: {metrics.thin_modules:,} thin; {metrics.import_data_only_modules:,} import/data-only",
        f"contract evidence: {metrics.contract_files:,} files / {metrics.contract_lines:,} lines",
        f"structural mirrors: {metrics.structural_mirror_files:,} files / {metrics.structural_mirror_lines:,} lines",
        "",
    ]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"{status:4} {result.metric}: {result.display_value} (target {result.display_target})")
    sys.stdout.write("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--enforce", action="store_true", help="Exit non-zero while any accepted target is unmet.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable metrics and checks.")
    args = parser.parse_args()

    metrics = measure()
    results = checks(metrics, Budget())
    if args.json:
        sys.stdout.write(json.dumps({"metrics": asdict(metrics), "checks": [asdict(result) for result in results]}, indent=2, sort_keys=True) + "\n")
    else:
        _render(metrics, results)
    return 1 if args.enforce and any(not result.passed for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())

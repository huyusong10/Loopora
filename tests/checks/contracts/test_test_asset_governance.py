from __future__ import annotations

import ast
from pathlib import Path
import re


CONTRACT_ROOT = Path(__file__).resolve().parent
PROBE_ROOT = CONTRACT_ROOT.parents[1] / "probes" / "real_environment"

MAX_CONTRACT_TEST_FILE_LINES = 800

LEGACY_DIRECT_ASSERTION_ALLOWLIST = {
    "agent_adapter_expected.py",
    "agent_native_v3_helpers.py",
}


def _python_files(*roots: Path) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(sorted(root.rglob("*.py")))
    return files


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_contract_tests_do_not_use_wildcard_imports() -> None:
    offenders: list[str] = []
    for path in _python_files(CONTRACT_ROOT, PROBE_ROOT):
        offenders.extend(
            f"{path.relative_to(CONTRACT_ROOT.parents[2])}:{node.lineno}"
            for node in ast.walk(_tree(path))
            if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names)
        )

    assert offenders == []


def test_v3_envelope_assertion_has_one_canonical_helper() -> None:
    definitions: list[str] = []
    for path in _python_files(CONTRACT_ROOT):
        definitions.extend(
            str(path.relative_to(CONTRACT_ROOT))
            for node in ast.walk(_tree(path))
            if isinstance(node, ast.FunctionDef) and node.name == "assert_agent_v3_envelope"
        )

    assert definitions == ["agent_native_v3_helpers.py"]


def test_raw_legacy_is_only_asserted_through_diagnostic_helpers() -> None:
    direct_raw_legacy = re.compile(r"\\[\\s*['\\\"]raw['\\\"]\\s*\\]\\s*\\[\\s*['\\\"]legacy['\\\"]|raw\\.legacy")
    offenders: list[str] = []
    for path in _python_files(CONTRACT_ROOT):
        if path.name in LEGACY_DIRECT_ASSERTION_ALLOWLIST:
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if direct_raw_legacy.search(line):
                offenders.append(f"{path.relative_to(CONTRACT_ROOT)}:{line_number}")

    assert offenders == []


def test_contract_test_files_stay_within_size_budget() -> None:
    offenders: list[str] = []
    for path in _python_files(CONTRACT_ROOT):
        line_count = sum(1 for _line in path.open(encoding="utf-8"))
        if line_count > MAX_CONTRACT_TEST_FILE_LINES:
            offenders.append(
                f"{path.relative_to(CONTRACT_ROOT)} has {line_count} lines, budget {MAX_CONTRACT_TEST_FILE_LINES}"
            )

    assert offenders == []


def test_long_stdout_or_output_assertions_do_not_grow() -> None:
    offenders: list[str] = []
    for path in _python_files(CONTRACT_ROOT):
        source = path.read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(source, filename=str(path))):
            if not isinstance(node, ast.Assert):
                continue
            statement = ast.get_source_segment(source, node) or ""
            if "stdout" not in statement and "output" not in statement:
                continue
            if any(isinstance(child, ast.Constant) and isinstance(child.value, str) and len(child.value) >= 100 for child in ast.walk(node)):
                offenders.append(f"{path.relative_to(CONTRACT_ROOT)}:{node.lineno}")

    assert offenders == []

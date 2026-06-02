from __future__ import annotations

import ast
from pathlib import Path
import re
import tokenize
import tomllib


CONTRACT_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = CONTRACT_ROOT.parents[2]
PROBE_ROOT = PROJECT_ROOT / "tests" / "probes" / "real_environment"
PYPROJECT = PROJECT_ROOT / "pyproject.toml"

MAX_CONTRACT_TEST_FILE_LINES = 800
MAX_INLINE_STDOUT_ASSERTION_LITERAL_LENGTH = 100
MAX_CONTRACT_TEST_FILES = 650
MAX_CONTRACT_SUPPORT_FILES = 80

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


def _ruff_per_file_ignores() -> dict[str, list[str]]:
    with PYPROJECT.open("rb") as handle:
        pyproject = tomllib.load(handle)
    return pyproject["tool"]["ruff"]["lint"].get("per-file-ignores", {})


def test_contract_tests_do_not_use_wildcard_imports() -> None:
    offenders: list[str] = []
    for path in _python_files(CONTRACT_ROOT, PROBE_ROOT):
        offenders.extend(
            f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}"
            for node in ast.walk(_tree(path))
            if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names)
        )

    assert offenders == []


def test_contract_tests_do_not_keep_wildcard_import_lint_ignores() -> None:
    offenders = [
        f"{pattern}: {', '.join(sorted(set(ignores) & {'F403', 'F405'}))}"
        for pattern, ignores in _ruff_per_file_ignores().items()
        if pattern.replace("\\", "/").startswith("tests/checks/contracts/")
        and set(ignores) & {"F403", "F405"}
    ]

    assert offenders == []


def test_source_lint_per_file_ignores_stay_limited_to_cli_argument_boundaries() -> None:
    offenders: list[str] = []
    for pattern, ignores in _ruff_per_file_ignores().items():
        normalized = pattern.replace("\\", "/")
        if not normalized.startswith("src/loopora/"):
            continue
        if set(ignores) != {"PLR0913"} or not normalized.startswith("src/loopora/cli_"):
            offenders.append(f"{pattern}: {', '.join(ignores)}")

    assert offenders == []


def test_print_lint_exceptions_stay_limited_to_operator_scripts() -> None:
    allowed = {
        "tests/probes/real_environment/run_real_probes.py",
        "tests/reviews/run.py",
    }
    offenders = [
        f"{pattern}: {', '.join(ignores)}"
        for pattern, ignores in _ruff_per_file_ignores().items()
        if "T201" in ignores and pattern.replace("\\", "/") not in allowed
    ]

    assert offenders == []


def test_default_lint_selects_targeted_style_naming_exception_assertion_and_type_rules() -> None:
    with PYPROJECT.open("rb") as handle:
        pyproject = tomllib.load(handle)

    selected = set(pyproject["tool"]["ruff"]["lint"]["select"])

    expected_rules = {
        "A",
        "ASYNC",
        "C4",
        "DTZ",
        "ERA",
        "EXE",
        "FA",
        "FAST",
        "FURB",
        "G",
        "ICN",
        "ISC",
        "LOG",
        "N",
        "PGH",
        "PLC0206",
        "PLE",
        "PLR0402",
        "PLR1711",
        "PTH",
        "PT",
        "PYI",
        "RSE",
        "RUF100",
        "SLOT",
        "T20",
        "TID",
        "W",
        "YTT",
    }

    assert expected_rules <= selected


def test_noqa_directives_explain_their_stable_exception_boundary() -> None:
    offenders: list[str] = []
    for path in _python_files(PROJECT_ROOT / "src" / "loopora", CONTRACT_ROOT, PROBE_ROOT):
        with path.open("rb") as handle:
            comments = tokenize.tokenize(handle.readline)
            for comment in comments:
                if comment.type != tokenize.COMMENT:
                    continue
                if "# noqa:" not in comment.string:
                    continue
                explanation_count = comment.string.partition("# noqa:")[2].count(" - ")
                if explanation_count != 1:
                    offenders.append(f"{path.relative_to(PROJECT_ROOT)}:{comment.start[0]}")

    assert offenders == []


def test_pytest_uses_strict_config_marker_validation_and_unraisable_warning_guard() -> None:
    with PYPROJECT.open("rb") as handle:
        pyproject = tomllib.load(handle)

    pytest_options = pyproject["tool"]["pytest"]["ini_options"]
    addopts = pytest_options["addopts"]
    filterwarnings = set(pytest_options["filterwarnings"])

    assert "--strict-config" in addopts
    assert "--strict-markers" in addopts
    assert "error::pytest.PytestUnraisableExceptionWarning" in filterwarnings


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
        with path.open(encoding="utf-8") as handle:
            line_count = sum(1 for _line in handle)
        if line_count > MAX_CONTRACT_TEST_FILE_LINES:
            offenders.append(
                f"{path.relative_to(CONTRACT_ROOT)} has {line_count} lines, budget {MAX_CONTRACT_TEST_FILE_LINES}"
            )

    assert offenders == []


def test_contract_test_file_count_stays_within_asset_budget() -> None:
    test_files = sorted(CONTRACT_ROOT.rglob("test_*.py"))

    assert len(test_files) <= MAX_CONTRACT_TEST_FILES


def test_contract_support_file_count_stays_within_asset_budget() -> None:
    support_files = sorted(
        path
        for path in CONTRACT_ROOT.rglob("*.py")
        if path.name.endswith("_support.py") or path.name.endswith("_test_support.py")
    )

    assert len(support_files) <= MAX_CONTRACT_SUPPORT_FILES


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
            if any(isinstance(child, ast.Constant) and isinstance(child.value, str) and len(child.value) >= MAX_INLINE_STDOUT_ASSERTION_LITERAL_LENGTH for child in ast.walk(node)):
                offenders.append(f"{path.relative_to(CONTRACT_ROOT)}:{node.lineno}")

    assert offenders == []

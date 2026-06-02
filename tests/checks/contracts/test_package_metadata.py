from __future__ import annotations

import tomllib
from pathlib import Path

import loopora


ROOT = Path(__file__).resolve().parents[3]


def test_package_metadata_supports_public_discovery_without_license_claim() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert set(project["keywords"]) >= {
        "ai-agents",
        "agent-workflows",
        "evidence",
        "fastapi",
        "local-first",
    }
    assert set(project["classifiers"]) >= {
        "Development Status :: 3 - Alpha",
        "Framework :: FastAPI",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
    }
    assert project["urls"] == {
        "Homepage": "https://github.com/huyusong10/Loopora",
        "Repository": "https://github.com/huyusong10/Loopora",
        "Issues": "https://github.com/huyusong10/Loopora/issues",
        "Security": "https://github.com/huyusong10/Loopora/security/policy",
    }

    assert "license" not in project
    assert not any(str(classifier).startswith("License ::") for classifier in project["classifiers"])


def test_runtime_version_matches_project_metadata() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert loopora.__version__ == project["version"]

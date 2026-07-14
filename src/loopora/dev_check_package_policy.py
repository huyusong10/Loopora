from __future__ import annotations

from pathlib import Path

PACKAGE_BUILD_OUTPUT_DIR = Path("tmp/package-check")
PACKAGE_BUILD_LOCK_TIMEOUT_SECONDS = 20 * 60
PACKAGE_BUILD_LOCK_STALE_SECONDS = 30 * 60
PACKAGE_BUILD_LOCK_POLL_SECONDS = 0.1
GENERATED_PACKAGE_METADATA_DIRS = (Path("src/loopora.egg-info"),)
PACKAGE_RUNTIME_ASSET_ROOTS = (
    Path("templates"),
    Path("static"),
    Path("assets/alignment"),
    Path("assets/demo"),
    Path("assets/logo"),
    Path("assets/prompts"),
    Path("assets/spec_practices"),
    Path("assets/system_prompts"),
)
PACKAGE_RUNTIME_ENTRY_FILES = (Path("__main__.py"),)
PACKAGE_SDIST_PUBLIC_FILES = (
    Path("pyproject.toml"),
    Path("setup.py"),
    Path("MANIFEST.in"),
    Path("README.md"),
    Path("README.zh-CN.md"),
    Path("HUMAN-SHAPED-LOOP.md"),
    Path("HUMAN-SHAPED-LOOP.zh-CN.md"),
    Path("CONTRIBUTING.md"),
    Path("CODE_OF_CONDUCT.md"),
    Path("CHANGELOG.md"),
    Path("GOVERNANCE.md"),
    Path("SECURITY.md"),
    Path("SUPPORT.md"),
)
PACKAGE_SDIST_PUBLIC_ASSET_ROOTS = (Path("assets/diagrams"), Path("design"))
PACKAGE_FORBIDDEN_DISTRIBUTION_PREFIXES = ("tests/", ".github/", "tmp/", ".loopora/")
PACKAGE_PUBLIC_DESCRIPTION_TERMS = ("evidence", "loop", "long-running", "agent")
PACKAGE_PUBLIC_KEYWORDS = (
    "ai-agents",
    "agent-workflows",
    "evidence",
    "human-in-the-loop",
    "local-first",
    "long-running-agents",
)
PACKAGE_PUBLIC_AUTHOR = "Loopora contributors"
PACKAGE_PUBLIC_MAINTAINER = "Loopora maintainers"
PACKAGE_PUBLIC_URLS = {
    "Changelog": "https://github.com/huyusong10/Loopora/blob/dev/CHANGELOG.md",
    "Community": "https://github.com/huyusong10/Loopora/blob/dev/CODE_OF_CONDUCT.md",
    "Documentation": "https://github.com/huyusong10/Loopora/blob/dev/README.md",
    "Governance": "https://github.com/huyusong10/Loopora/blob/dev/GOVERNANCE.md",
    "Homepage": "https://github.com/huyusong10/Loopora",
    "Issues": "https://github.com/huyusong10/Loopora/issues",
    "Repository": "https://github.com/huyusong10/Loopora",
    "Security": "https://github.com/huyusong10/Loopora/security/policy",
    "Support": "https://github.com/huyusong10/Loopora/blob/dev/SUPPORT.md",
}

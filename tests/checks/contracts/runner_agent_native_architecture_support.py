from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src" / "loopora"


def source(*parts: str) -> str:
    return (SRC_ROOT / Path(*parts)).read_text(encoding="utf-8")


def agent_native_runtime_source() -> str:
    names = (
        "service_agent_native.py",
        "service_agent_native_claim.py",
        "service_agent_native_iteration.py",
        "service_agent_native_submit.py",
    )
    return "\n".join(source(name) for name in names)


def agent_native_claim_source() -> str:
    return source("service_agent_native_claim.py")

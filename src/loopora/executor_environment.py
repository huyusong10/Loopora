from __future__ import annotations

import os

from loopora.branding import FAKE_DELAY_ENV, FAKE_EXECUTOR_ENV
from loopora.executor_fake import FakeCodexExecutor
from loopora.executor_real import RealCodexExecutor
from loopora.executor_types import CodexExecutor


def executor_from_environment() -> CodexExecutor:
    scenario = os.environ.get(FAKE_EXECUTOR_ENV, "").strip()
    if scenario:
        delay = float(os.environ.get(FAKE_DELAY_ENV, "0").strip())
        return FakeCodexExecutor(scenario=scenario, role_delay=delay)
    return RealCodexExecutor()

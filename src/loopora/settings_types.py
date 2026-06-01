from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AppSettings:
    max_concurrent_runs: int = 2
    polling_interval_seconds: float = 0.5
    stop_grace_period_seconds: float = 2.0
    role_idle_timeout_seconds: float = 300.0

from __future__ import annotations

from collections.abc import Callable

from loopora.db import LooporaRepository
from loopora.executor import CodexExecutor, executor_from_environment
from loopora.service_app import LooporaAppServices, _LooporaServiceRuntime
from loopora.service_prompts import (
    CHALLENGER_SCHEMA,
    CHECK_PLANNER_SCHEMA,
    GENERATOR_SCHEMA,
    TESTER_SCHEMA,
    VERIFIER_SCHEMA,
)
from loopora.service_types import LooporaError
from loopora.settings import AppSettings, configure_logging, db_path, load_settings
from loopora.strategy_source import (
    STRATEGY_SOURCE_ARCHETYPES,
    StrategySourceError,
    normalize_strategy_role_models,
)

LOOP_ROLE_NAMES = STRATEGY_SOURCE_ARCHETYPES

__all__ = [
    "CHALLENGER_SCHEMA",
    "CHECK_PLANNER_SCHEMA",
    "GENERATOR_SCHEMA",
    "LOOP_ROLE_NAMES",
    "TESTER_SCHEMA",
    "VERIFIER_SCHEMA",
    "LooporaAppServices",
    "LooporaService",
    "create_service",
    "normalize_role_models",
]


def normalize_role_models(role_models: dict | None) -> dict[str, str]:
    try:
        return normalize_strategy_role_models(role_models)
    except StrategySourceError as exc:
        raise LooporaError(str(exc)) from exc


class LooporaService:
    _process_active_runs = _LooporaServiceRuntime._process_active_runs
    _process_active_runs_lock = _LooporaServiceRuntime._process_active_runs_lock

    def __init__(
        self,
        repository: LooporaRepository,
        settings: AppSettings,
        executor_factory: Callable[[], CodexExecutor] | None = None,
    ) -> None:
        self.app_services = LooporaAppServices.create(
            repository=repository,
            settings=settings,
            executor_factory=executor_factory or executor_from_environment,
        )

    def __getattr__(self, name: str):
        return getattr(self.app_services.runtime, name)

    def __setattr__(self, name: str, value) -> None:
        if name == "app_services" or "app_services" not in self.__dict__:
            object.__setattr__(self, name, value)
            return
        runtime = self.app_services.runtime
        if hasattr(runtime, name):
            setattr(runtime, name, value)
            return
        object.__setattr__(self, name, value)


def create_service(executor_factory: Callable[[], CodexExecutor] | None = None) -> LooporaService:
    configure_logging()
    return LooporaService(
        repository=LooporaRepository(db_path()),
        settings=load_settings(),
        executor_factory=executor_factory,
    )

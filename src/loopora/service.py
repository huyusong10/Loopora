from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable

from loopora.branding import app_home_path
from loopora.db import LooporaRepository
from loopora.diagnostics import get_logger, log_exception
from loopora.executor_environment import executor_from_environment
from loopora.executor_types import CodexExecutor
from loopora.service_app import LooporaAppServices, LooporaServiceRuntime
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
LOCAL_APP_STATE_OPEN_ERROR = (
    "Loopora local App state could not be opened; "
    "run `loopora doctor --workdir <project>` to inspect App state, "
    "or set LOOPORA_HOME to a new empty directory for a disposable preview."
)
logger = get_logger(__name__)

__all__ = [
    "CHALLENGER_SCHEMA",
    "CHECK_PLANNER_SCHEMA",
    "GENERATOR_SCHEMA",
    "LOCAL_APP_STATE_OPEN_ERROR",
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


def _local_app_state_open_error(exc: OSError | sqlite3.Error) -> LooporaError:
    log_exception(
        logger,
        "service.create.local_app_state_open_failed",
        "Local App state could not be opened",
        error=exc,
        level=logging.INFO,
    )
    return LooporaError(LOCAL_APP_STATE_OPEN_ERROR)


class LooporaService:
    _process_active_runs = LooporaServiceRuntime._process_active_runs
    _process_active_runs_lock = LooporaServiceRuntime._process_active_runs_lock

    def __init__(
        self,
        repository: LooporaRepository,
        settings: AppSettings,
        executor_factory: Callable[[], CodexExecutor] | None = None,
        *,
        apply_startup_repairs: bool = True,
    ) -> None:
        self.app_services = LooporaAppServices.create(
            repository=repository,
            settings=settings,
            executor_factory=executor_factory or executor_from_environment,
            apply_startup_repairs=apply_startup_repairs,
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


def create_service(
    executor_factory: Callable[[], CodexExecutor] | None = None,
    *,
    apply_startup_repairs: bool = True,
    storage_read_only: bool = False,
) -> LooporaService:
    try:
        if storage_read_only and apply_startup_repairs:
            raise LooporaError("read-only service construction cannot apply startup repairs")
        if not storage_read_only:
            configure_logging()
        database = app_home_path() / "app.db" if storage_read_only else db_path()
        return LooporaService(
            repository=LooporaRepository(database, read_only=storage_read_only),
            settings=load_settings(read_only=storage_read_only),
            executor_factory=executor_factory,
            apply_startup_repairs=apply_startup_repairs,
        )
    except LooporaError:
        raise
    except (OSError, sqlite3.Error) as exc:
        raise _local_app_state_open_error(exc) from exc

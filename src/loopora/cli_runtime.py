from __future__ import annotations

from collections.abc import Callable
from typing import Any

from loopora.service import create_service as _default_create_service

ServiceFactory = Callable[..., Any]
WorkerSpawner = Callable[[Any, dict], dict]

_runtime_hooks: dict[str, Any] = {
    "service_factory": _default_create_service,
    "worker_spawner": None,
}


def set_service_factory(factory: ServiceFactory) -> None:
    _runtime_hooks["service_factory"] = factory


def set_worker_spawner(spawner: WorkerSpawner) -> None:
    _runtime_hooks["worker_spawner"] = spawner


def get_service(*, apply_startup_repairs: bool = True, storage_read_only: bool = False) -> Any:
    factory = _runtime_hooks["service_factory"]
    if apply_startup_repairs and not storage_read_only:
        return factory()
    return factory(
        apply_startup_repairs=apply_startup_repairs,
        storage_read_only=storage_read_only,
    )


def spawn_background_worker(service: Any, run: dict) -> dict:
    spawner = _runtime_hooks["worker_spawner"]
    if spawner is None:
        raise RuntimeError("CLI worker spawner is not configured")
    return spawner(service, run)

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from bundle_lifecycle_test_support import _bundle_yaml, _has_cleanup_record
from loopora.service import LooporaError
from loopora.settings import configure_logging
import loopora.service_cleanup_diagnostics as cleanup_diagnostics


def test_bundle_failed_import_cleanup_logs_and_preserves_original_error(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    configure_logging()
    original_create_role_definition = service.create_role_definition

    def fail_create_role_definition(*_args, **_kwargs):
        raise LooporaError("forced role import failure")

    def fail_rmtree(path: Path) -> None:
        raise OSError(f"cannot remove {Path(path).name}")

    service.create_role_definition = fail_create_role_definition
    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_rmtree)

    with caplog.at_level(logging.WARNING, logger="loopora.service_bundle_assets"), pytest.raises(LooporaError, match="forced role import failure"):
        service.import_bundle_text(_bundle_yaml(sample_workdir))

    service.create_role_definition = original_create_role_definition
    assert _has_cleanup_record(caplog, operation="bundle_failed_import_cleanup", resource_type="path")


def test_bundle_failed_import_cleanup_diagnostic_failure_preserves_original_error(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    original_create_role_definition = service.create_role_definition

    def fail_create_role_definition(*_args, **_kwargs):
        raise LooporaError("forced role import failure")

    def fail_rmtree(path: Path) -> None:
        raise OSError(f"cannot remove {Path(path).name}")

    def fail_log_event(*_args, **_kwargs) -> None:
        raise RuntimeError("cleanup log sink down")

    service.create_role_definition = fail_create_role_definition
    monkeypatch.setattr(cleanup_diagnostics.shutil, "rmtree", fail_rmtree)
    monkeypatch.setattr(cleanup_diagnostics, "log_event", fail_log_event)
    try:
        with pytest.raises(LooporaError, match="forced role import failure"):
            service.import_bundle_text(_bundle_yaml(sample_workdir))
    finally:
        service.create_role_definition = original_create_role_definition


def test_bundle_import_rollback_diagnostics_preserve_original_error_for_unexpected_cleanup_failure(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
    caplog,
) -> None:
    service = service_factory(scenario="success")
    configure_logging()

    def fail_after_graph_creation(*_args, **_kwargs):
        raise LooporaError("forced import failure after graph creation")

    def fail_delete_loop(*_args, **_kwargs):
        raise RuntimeError("rollback loop deletion failed")

    monkeypatch.setattr(service, "derive_bundle_from_loop", fail_after_graph_creation)
    monkeypatch.setattr(service, "delete_loop", fail_delete_loop)

    with (
        caplog.at_level(logging.WARNING, logger="loopora.service_bundle_assets"),
        pytest.raises(
            LooporaError,
            match="forced import failure after graph creation",
        ),
    ):
        service.import_bundle_text(_bundle_yaml(sample_workdir))

    assert _has_cleanup_record(caplog, operation="bundle_import_rollback", resource_type="loop")

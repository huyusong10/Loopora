from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager, suppress
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import time

from loopora.dev_check_package_policy import (
    GENERATED_PACKAGE_METADATA_DIRS,
    PACKAGE_BUILD_LOCK_POLL_SECONDS,
    PACKAGE_BUILD_LOCK_STALE_SECONDS,
    PACKAGE_BUILD_LOCK_TIMEOUT_SECONDS,
    PACKAGE_BUILD_OUTPUT_DIR,
)
from loopora.service_types import LooporaError


@contextmanager
def package_build_lock(root: Path) -> Iterator[None]:
    lock_dir = package_build_lock_dir(root)
    deadline = time.monotonic() + PACKAGE_BUILD_LOCK_TIMEOUT_SECONDS
    acquired = False
    while not acquired:
        try:
            lock_dir.mkdir(mode=0o700, parents=True)
            write_package_build_lock_owner(lock_dir, root)
            acquired = True
        except FileExistsError:
            if package_build_lock_is_stale(lock_dir):
                shutil.rmtree(lock_dir, ignore_errors=True)
                continue
            if time.monotonic() >= deadline:
                raise LooporaError(
                    "package_build is waiting on another Loopora dev check for this workdir; rerun after that package-build step finishes"
                ) from None
            time.sleep(PACKAGE_BUILD_LOCK_POLL_SECONDS)
    try:
        yield
    finally:
        shutil.rmtree(lock_dir, ignore_errors=True)


def package_build_lock_dir(root: Path) -> Path:
    identity = str(root.resolve(strict=False)).encode("utf-8")
    digest = hashlib.sha256(identity).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"loopora-package-check-{digest}.lockdir"


def write_package_build_lock_owner(lock_dir: Path, root: Path) -> None:
    with suppress(OSError):
        (lock_dir / "owner").write_text(f"pid={os.getpid()}\nworkdir={root.resolve(strict=False)}\n", encoding="utf-8")


def package_build_lock_is_stale(lock_dir: Path) -> bool:
    try:
        lock_age = time.time() - lock_dir.stat().st_mtime
    except OSError:
        return False
    return lock_age > PACKAGE_BUILD_LOCK_STALE_SECONDS


def prepare_package_build_dir(root: Path) -> None:
    package_dir = root / PACKAGE_BUILD_OUTPUT_DIR
    cleanup_package_build_output(root)
    package_dir.mkdir(parents=True, exist_ok=True)
    cleanup_generated_package_metadata(root)


def cleanup_package_build_output(root: Path) -> None:
    shutil.rmtree(root / PACKAGE_BUILD_OUTPUT_DIR, ignore_errors=True)


def cleanup_generated_package_metadata(root: Path) -> None:
    for relative_path in GENERATED_PACKAGE_METADATA_DIRS:
        shutil.rmtree(root / relative_path, ignore_errors=True)

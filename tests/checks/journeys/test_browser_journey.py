from __future__ import annotations

import socket
import threading
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

import pytest
import uvicorn

from loopora.db import LooporaRepository
from loopora.executor import FakeCodexExecutor
from loopora.service import LooporaService
from loopora.settings import AppSettings
from loopora.web import build_app

playwright = pytest.importorskip("playwright.sync_api")
pytestmark = pytest.mark.journey


def _reserve_local_socket() -> tuple[str, int, socket.socket]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()
        return host, port, sock
    except OSError as exc:  # pragma: no cover - environment dependent
        sock.close()
        if isinstance(exc, PermissionError) or getattr(exc, "errno", None) in {1, 13}:
            pytest.skip(f"local TCP listeners are unavailable in this environment: {exc}")
        raise


@contextmanager
def _serve_app(app):
    host, port, sock = _reserve_local_socket()
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="warning", ws="none"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    base_url = f"http://{host}:{port}"
    deadline = time.time() + 15
    last_error: OSError | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/", timeout=0.5) as response:
                if response.status == 200:
                    break
        except OSError as exc:  # pragma: no cover - startup timing dependent
            last_error = exc
            time.sleep(0.05)
    else:  # pragma: no cover - environment dependent
        server.should_exit = True
        thread.join(timeout=5)
        sock.close()
        raise RuntimeError(f"app server did not start within 15s: {last_error}")

    try:
        yield base_url
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        sock.close()


@contextmanager
def _launch_chromium():
    with playwright.sync_playwright() as driver:
        try:
            browser = driver.chromium.launch(headless=True)
        except playwright.Error as exc:  # pragma: no cover - environment dependent
            pytest.skip(f"Playwright browser launch is unavailable: {exc}")
        try:
            yield browser
        finally:
            browser.close()


def _service(tmp_path: Path) -> LooporaService:
    return LooporaService(
        repository=LooporaRepository(tmp_path / "app.db"),
        settings=AppSettings(max_concurrent_runs=2, polling_interval_seconds=0.05, stop_grace_period_seconds=0.2),
        executor_factory=lambda: FakeCodexExecutor(scenario="success"),
    )


def _create_loop(service: LooporaService, spec_path: Path, workdir: Path) -> dict:
    return service.create_loop(
        name="Browser Journey Loop",
        spec_path=spec_path,
        workdir=workdir,
        model="",
        reasoning_effort="",
        max_iters=1,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )


def _assert_no_horizontal_overflow(page) -> None:
    metrics = page.evaluate(
        """() => ({
          documentWidth: document.documentElement.scrollWidth,
          viewportWidth: document.documentElement.clientWidth,
          bodyWidth: document.body.scrollWidth,
        })"""
    )
    assert metrics["documentWidth"] <= metrics["viewportWidth"] + 1
    assert metrics["bodyWidth"] <= metrics["viewportWidth"] + 1


def test_browser_current_core_surfaces_render_without_overflow(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "web-workdir"
    workdir.mkdir()
    spec_path = tmp_path / "spec.md"
    spec_path.write_text(
        "# Task\n\nKeep the Web surface reachable.\n\n# Done When\n\n- Current pages remain usable.\n",
        encoding="utf-8",
    )
    loop = _create_loop(service, spec_path, workdir)
    run = service.rerun(loop["id"])

    with _serve_app(build_app(service=service)) as base_url, _launch_chromium() as browser:
        page = browser.new_page(viewport={"width": 390, "height": 844})
        for path, testid in (
            ("/", "home-workbench"),
            ("/loops/new", "loop-create-choice-page"),
            ("/loops/new/bundle", "alignment-start-form"),
            ("/loops/new/manual", "manual-compose-section"),
            ("/tools", "agent-adapters-panel"),
            ("/tutorial", "tutorial-page"),
            (f"/loops/{loop['id']}", "loop-detail-page"),
            (f"/runs/{run['id']}", "run-detail-page"),
        ):
            page.goto(f"{base_url}{path}", wait_until="domcontentloaded")
            page.get_by_test_id(testid).wait_for(state="visible", timeout=10_000)
            _assert_no_horizontal_overflow(page)

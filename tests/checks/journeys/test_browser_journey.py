from __future__ import annotations

import socket
import textwrap
import threading
import time
import urllib.request
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

import pytest
import uvicorn

import loopora.executor_runtime_readiness as executor_readiness_module
from loopora import agent_adapter_command_prefix
from loopora.bundles import bundle_to_yaml
from loopora.db import LooporaRepository
from loopora.executor import FakeCodexExecutor, RoleRequest
from loopora.executor_real import RealCodexExecutor
from loopora.service import LooporaService
from loopora.service_agent_adapters import AgentBundleCandidateRequest
from loopora.settings import AppSettings
from loopora.start_guidance import start_guidance_payload
from loopora.web import build_app

playwright = pytest.importorskip("playwright.sync_api")
pytestmark = pytest.mark.journey


CALCULATOR_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Calculator</title>
    <style>
      body { font-family: sans-serif; display: grid; place-items: center; min-height: 100vh; margin: 0; background: #f5efe8; }
      .calc { width: 280px; padding: 18px; border-radius: 16px; background: #1f1a14; color: #fff8ed; }
      [data-testid="display"] { width: 100%; margin-bottom: 12px; padding: 14px; border: none; border-radius: 12px; font-size: 1.8rem; text-align: right; box-sizing: border-box; }
      .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
      button { min-height: 52px; border: none; border-radius: 12px; font-size: 1rem; cursor: pointer; }
      .op { background: #f0b35d; }
      .eq { background: #57ba8a; }
      .clear { background: #ea8a7f; }
    </style>
  </head>
  <body>
    <main class="calc">
      <input data-testid="display" value="0" readonly aria-label="display" />
      <div class="grid">
        <button class="clear" type="button">C</button>
        <button type="button">(</button>
        <button type="button">)</button>
        <button class="op" type="button">/</button>
        <button type="button">7</button>
        <button type="button">8</button>
        <button type="button">9</button>
        <button class="op" type="button">*</button>
        <button type="button">4</button>
        <button type="button">5</button>
        <button type="button">6</button>
        <button class="op" type="button">-</button>
        <button type="button">1</button>
        <button type="button">2</button>
        <button type="button">3</button>
        <button class="op" type="button">+</button>
        <button type="button">0</button>
        <button type="button">.</button>
        <button class="eq" type="button">=</button>
      </div>
    </main>
    <script>
      const display = document.querySelector('[data-testid="display"]');
      let expression = '';
      document.querySelectorAll('button').forEach((button) => {
        button.addEventListener('click', () => {
          const value = button.textContent.trim();
          if (value === 'C') {
            expression = '';
            display.value = '0';
          } else if (value === '=') {
            expression = String(Function(`return (${expression || '0'})`)());
            display.value = expression;
          } else {
            expression += value;
            display.value = expression;
          }
        });
      });
    </script>
  </body>
</html>
"""


class CalculatorPrototypeExecutor(FakeCodexExecutor):
    def _build_payload(self, request: RoleRequest) -> dict:
        if request.role == "generator":
            (request.workdir / "index.html").write_text(CALCULATOR_HTML, encoding="utf-8")
            return {
                "attempted": "Created a browser-ready calculator prototype.",
                "abandoned": "Skipped backend features and history storage.",
                "assumption": "A single-file calculator is enough for the prototype goal.",
                "summary": "Added a static calculator app with clickable buttons and a live display.",
                "changed_files": ["index.html"],
            }
        if request.role_archetype == "inspector":
            return {
                "execution_summary": {"total_checks": 2, "passed": 2, "failed": 0, "errored": 0},
                "check_results": [
                    {"id": "check_001", "title": "Basic addition works", "status": "passed"},
                    {"id": "check_002", "title": "Clear resets the display", "status": "passed"},
                ],
                "dynamic_checks": [],
                "tester_observations": "The generated calculator is ready for browser verification.",
            }
        if request.role == "verifier":
            step_instruction_context = request.extra_context.get("step_instruction_context") if isinstance(request.extra_context, dict) else {}
            evidence_refs = [
                str(item.get("id"))
                for item in list((step_instruction_context.get("evidence") or {}).get("items") or [])
                if isinstance(item, dict) and str(item.get("id") or "").strip()
            ][-3:]
            return {
                "passed": True,
                "composite_score": 1.0,
                "metric_scores": {"check_pass_rate": {"value": 1.0, "threshold": 0.9, "passed": True}},
                "hard_constraint_violations": [],
                "failed_check_ids": [],
                "priority_failures": [],
                "feedback_to_generator": "The prototype satisfies the requested calculator scope.",
                "evidence_refs": evidence_refs,
                "evidence_claims": [],
            }
        return super()._build_payload(request)


def _skip_if_local_listener_unavailable(exc: OSError) -> None:
    if isinstance(exc, PermissionError) or getattr(exc, "errno", None) in {1, 13}:
        pytest.skip(f"local TCP listeners are unavailable in this environment: {exc}")
    raise exc


def _reserve_local_socket() -> tuple[str, int, socket.socket]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()
        return host, port, sock
    except OSError as exc:  # pragma: no cover - environment dependent
        sock.close()
        _skip_if_local_listener_unavailable(exc)
        raise


@contextmanager
def serve_directory(path: Path):
    handler = partial(SimpleHTTPRequestHandler, directory=str(path))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    except OSError as exc:  # pragma: no cover - environment dependent
        _skip_if_local_listener_unavailable(exc)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@contextmanager
def serve_app(app):
    host, port, sock = _reserve_local_socket()
    config = uvicorn.Config(app, host=host, port=port, log_level="warning", ws="none")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    base_url = f"http://{host}:{port}"
    deadline = time.time() + 15
    last_error = None
    ready = False

    while time.time() < deadline:
        if not thread.is_alive() and not server.started:
            last_error = RuntimeError("uvicorn server thread exited before startup")
            break
        try:
            with urllib.request.urlopen(f"{base_url}/", timeout=0.5) as response:
                if response.status == 200:
                    ready = True
                    break
        except OSError as exc:  # pragma: no cover - startup timing dependent
            last_error = exc
            time.sleep(0.05)

    if not ready:  # pragma: no cover - environment dependent
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
def launch_chromium(**kwargs):
    with playwright.sync_playwright() as playwright_driver:
        try:
            browser = playwright_driver.chromium.launch(**kwargs)
        except playwright.Error as exc:  # pragma: no cover - environment dependent
            pytest.skip(f"Playwright browser launch is unavailable: {exc}")
        try:
            yield browser
        finally:
            browser.close()


def _service(tmp_path: Path, *, executor_factory=None) -> LooporaService:
    repository = LooporaRepository(tmp_path / "app.db")
    settings = AppSettings(max_concurrent_runs=2, polling_interval_seconds=0.05, stop_grace_period_seconds=0.2)
    return LooporaService(
        repository=repository,
        settings=settings,
        executor_factory=executor_factory or (lambda: FakeCodexExecutor(scenario="success")),
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
          docW: document.documentElement.scrollWidth,
          clientW: document.documentElement.clientWidth,
          bodyW: document.body.scrollWidth,
        })"""
    )
    assert metrics["docW"] <= metrics["clientW"] + 1
    assert metrics["bodyW"] <= metrics["clientW"] + 1


def _assert_alignment_intro_precedes_form(page) -> None:
    metrics = page.evaluate(
        """() => {
          const intro = document.querySelector("#alignment-empty-state");
          const form = document.querySelector("#alignment-start-form");
          if (!intro || !form) {
            return {present: false};
          }
          const introRect = intro.getBoundingClientRect();
          const formRect = form.getBoundingClientRect();
          return {
            present: true,
            introBottom: introRect.bottom,
            formTop: formRect.top,
          };
        }"""
    )
    assert metrics["present"] is True
    assert metrics["introBottom"] <= metrics["formTop"] + 1


def _assert_alignment_progressive_first_turn(page) -> None:
    state = page.evaluate(
        """() => ({
          detailsOpen: document.querySelector('[data-testid="alignment-judgment-details"]')?.open,
          taskVisible: Boolean(document.querySelector('[data-testid="alignment-task-goal-input"]')?.offsetParent),
          optionalVisible: Boolean(document.querySelector('[data-testid="alignment-loopora-fit-reason-input"]')?.offsetParent),
          replyVisible: Boolean(document.querySelector('[data-testid="alignment-message-input"]')?.offsetParent),
          startLabel: document.querySelector('[data-testid="alignment-send-button"]')?.textContent.trim(),
        })"""
    )
    assert state == {
        "detailsOpen": False,
        "taskVisible": True,
        "optionalVisible": False,
        "replyVisible": False,
        "startLabel": "Start conversation",
    }

    page.get_by_test_id("alignment-judgment-details").locator("summary").click()
    metrics = page.evaluate(
        """() => {
          const ids = [
            "alignment-direct-path-check-input",
            "alignment-fake-done-risk-input",
            "alignment-required-evidence-input",
          ];
          return ids.map((id) => {
            const element = document.querySelector(`[data-testid="${id}"]`);
            return element ? {
              id,
              present: true,
              clientHeight: element.clientHeight,
              scrollHeight: element.scrollHeight,
            } : {id, present: false};
          });
        }"""
    )
    for item in metrics:
        assert item["present"] is True
        assert item["scrollHeight"] <= item["clientHeight"] + 1, item


def _assert_alignment_fit_entry_phase(page, *, phase: str, known_count: int, missing_count: int, mobile: bool = False) -> None:
    state = page.evaluate(
        """() => {
          const panel = document.querySelector('[data-testid="loop-alignment-panel"]');
          const summary = document.querySelector('[data-testid="alignment-entry-handoff-summary"]');
          return {
            phase: panel?.dataset.alignmentEntryPhase,
            detailsOpen: document.querySelector('[data-testid="alignment-judgment-details"]')?.open,
            examplesHidden: document.querySelector('[data-alignment-entry-task-only]')?.hidden,
            summaryHidden: summary?.hidden,
            summaryPhase: summary?.dataset.entryPhase,
            knownCount: summary?.dataset.knownCount,
            missingCount: summary?.dataset.missingCount,
          };
        }"""
    )
    assert state == {
        "phase": phase,
        "detailsOpen": False,
        "examplesHidden": True,
        "summaryHidden": False,
        "summaryPhase": phase,
        "knownCount": str(known_count),
        "missingCount": str(missing_count),
    }
    if mobile:
        page.set_viewport_size({"width": 390, "height": 844})
        _assert_no_horizontal_overflow(page)
        mobile_state = page.evaluate(
            """() => {
              const sidebar = document.querySelector('[data-testid="alignment-history-panel"]');
              const startButton = document.querySelector('[data-testid="alignment-send-button"]');
              const rect = startButton?.getBoundingClientRect();
              return {
                sidebarHidden: sidebar ? getComputedStyle(sidebar).display === "none" : false,
                primaryActionInViewport: Boolean(
                  rect && rect.top >= 0 && rect.bottom <= window.innerHeight
                ),
              };
            }"""
        )
        assert mobile_state == {"sidebarHidden": True, "primaryActionInViewport": True}
        page.set_viewport_size({"width": 1280, "height": 900})


def _assert_input_placeholder_fits(page, testid: str) -> None:
    metrics = page.evaluate(
        """(testid) => {
          const element = document.querySelector(`[data-testid="${testid}"]`);
          if (!element) {
            return {present: false};
          }
          const style = getComputedStyle(element);
          const canvas = document.createElement("canvas");
          const context = canvas.getContext("2d");
          context.font = style.font;
          const placeholderWidth = context.measureText(element.placeholder || "").width;
          const availableWidth = element.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
          return {
            present: true,
            placeholder: element.placeholder,
            placeholderWidth,
            availableWidth,
          };
        }""",
        testid,
    )
    assert metrics["present"] is True
    assert metrics["placeholderWidth"] <= metrics["availableWidth"] + 1, metrics


def test_browser_tests_do_not_use_nested_sync_api_entrypoint() -> None:
    forbidden = "playwright.sync_api" + ".sync_playwright"
    assert forbidden not in Path(__file__).read_text(encoding="utf-8")


def test_local_listener_error_classification() -> None:
    with pytest.raises(pytest.skip.Exception, match="local TCP listeners are unavailable"):
        _skip_if_local_listener_unavailable(PermissionError("blocked"))
    with pytest.raises(OSError, match="boom"):
        _skip_if_local_listener_unavailable(OSError("boom"))


def test_browser_calculator_loop_runs_and_generated_app_works(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text(
        textwrap.dedent(
            """
            # Task

            开发一个计算器。

            # Done When

            - 用户点击 7、+、5、= 后显示 12。
            - 用户点击 C 后显示重置为 0。
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    workdir = tmp_path / "calculator-workdir"
    workdir.mkdir()
    service = _service(tmp_path, executor_factory=lambda: CalculatorPrototypeExecutor(scenario="success"))

    loop = _create_loop(service, spec_path, workdir)
    run = service.rerun(loop["id"])

    assert run["status"] == "succeeded"
    assert service.get_run(run["id"])["task_verdict"]["status"] in {"passed", "passed_with_residual_risk"}
    with serve_directory(workdir) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page()
        page.goto(f"{base_url}/index.html")
        page.get_by_role("button", name="7").click()
        page.get_by_role("button", name="+").click()
        page.get_by_role("button", name="5").click()
        page.get_by_role("button", name="=").click()
        assert page.locator('[data-testid="display"]').input_value() == "12"
        page.get_by_role("button", name="C").click()
        assert page.locator('[data-testid="display"]').input_value() == "0"


def test_browser_core_web_surfaces_render_without_overflow(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "web-workdir"
    workdir.mkdir()
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep the web surface reachable.\n", encoding="utf-8")
    loop = _create_loop(service, spec_path, workdir)
    run = service.rerun(loop["id"])

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 390, "height": 844})
        for path, testid in (
            ("/", "home-workbench"),
            ("/same-agent", "agent-adapters-panel"),
            ("/loops/new/bundle", "alignment-start-form"),
            ("/loops/new/manual", "manual-compose-section"),
            (f"/loops/{loop['id']}", "loop-detail-page"),
            (f"/runs/{run['id']}", "run-detail-page"),
        ):
            page.goto(f"{base_url}{path}", wait_until="domcontentloaded")
            page.get_by_test_id(testid).wait_for(state="visible", timeout=10_000)
            _assert_no_horizontal_overflow(page)
            if path == "/same-agent":
                _assert_input_placeholder_fits(page, "agent-adapter-workdir")

        for viewport in (
            {"width": 390, "height": 844},
            {"width": 768, "height": 900},
            {"width": 1280, "height": 900},
        ):
            page.set_viewport_size(viewport)
            page.goto(f"{base_url}/loops/new/bundle", wait_until="domcontentloaded")
            page.get_by_test_id("alignment-start-form").wait_for(state="visible", timeout=10_000)
            _assert_no_horizontal_overflow(page)
            _assert_alignment_intro_precedes_form(page)
            _assert_alignment_progressive_first_turn(page)
            _assert_no_horizontal_overflow(page)


def test_browser_same_agent_legacy_tools_alias_canonicalizes_without_losing_state(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "same-agent-target"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page()
        page.goto(
            f"{base_url}/tools?workdir={quote(resolved_workdir, safe='')}#agent-adapters-panel",
            wait_until="domcontentloaded",
        )
        page.get_by_test_id("agent-adapters-panel").wait_for(state="visible", timeout=10_000)
        page.wait_for_function("() => location.pathname === '/same-agent'", timeout=10_000)

        nav = page.evaluate(
            """() => ({
              pathname: location.pathname,
              workdir: new URL(location.href).searchParams.get("workdir"),
              hash: location.hash,
            })"""
        )

    assert nav == {
        "pathname": "/same-agent",
        "workdir": resolved_workdir,
        "hash": "#agent-adapters-panel",
    }


def test_browser_fit_guide_legacy_tutorial_alias_canonicalizes_without_losing_state(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "fit-guide-target"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page()
        page.goto(
            f"{base_url}/tutorial?workdir={quote(resolved_workdir, safe='')}#tutorial-decision-tree-panel",
            wait_until="domcontentloaded",
        )
        page.get_by_test_id("tutorial-decision-tree-panel").wait_for(state="visible", timeout=10_000)
        page.wait_for_function("() => location.pathname === '/fit-guide'", timeout=10_000)

        nav = page.evaluate(
            """() => ({
              pathname: location.pathname,
              workdir: new URL(location.href).searchParams.get("workdir"),
              hash: location.hash,
            })"""
        )

    assert nav == {
        "pathname": "/fit-guide",
        "workdir": resolved_workdir,
        "hash": "#tutorial-decision-tree-panel",
    }


def test_browser_fit_guide_starts_at_task_and_partial_review_continues_to_web(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "progressive-fit-project"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())
    task = "Migrate payment callbacks while proving idempotency, replay, and rollback."

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(
            f"{base_url}/fit-guide?workdir={quote(resolved_workdir, safe='')}",
            wait_until="domcontentloaded",
        )
        task_input = page.get_by_test_id("tutorial-fit-task-input")
        task_input.wait_for(state="visible", timeout=10_000)
        initial = page.evaluate(
            """() => {
              const task = document.querySelector('[data-testid="tutorial-fit-task-input"]');
              const direct = document.querySelector('[data-testid="tutorial-fit-prefer-direct-input"]');
              const detail = document.querySelector('[data-testid="tutorial-fit-detail-fields"]');
              const draft = document.querySelector('.tutorial-fit-task-pane--draft');
              return {
                taskTop: task?.getBoundingClientRect().top,
                taskBottom: task?.getBoundingClientRect().bottom,
                directBottom: direct?.closest('label')?.getBoundingClientRect().bottom,
                detailFieldsVisible: Array.from(detail?.querySelectorAll('[data-fit-draft-field]') || [])
                  .some((node) => !node.closest('.tutorial-fit-task-field')?.hidden),
                draftHidden: draft?.hidden,
                overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
              };
            }"""
        )
        assert initial["taskTop"] < 360
        assert initial["taskBottom"] < 500
        assert initial["directBottom"] < 600
        assert initial["detailFieldsVisible"] is False
        assert initial["draftHidden"] is True
        assert initial["overflow"] <= 1

        task_input.fill(task)
        assert page.get_by_test_id("tutorial-fit-loopora-fit-reason-input").is_visible()
        assert page.get_by_test_id("tutorial-fit-task-draft").is_visible()
        assert page.get_by_test_id("tutorial-fit-task-copy").is_disabled()
        assert page.get_by_test_id("tutorial-fit-task-use-web").get_attribute("aria-disabled") != "true"

        page.set_viewport_size({"width": 390, "height": 844})
        _assert_no_horizontal_overflow(page)
        page.set_viewport_size({"width": 1280, "height": 720})
        page.get_by_test_id("tutorial-fit-task-use-web").click()
        page.wait_for_function(
            """task => location.pathname === '/loops/new/bundle'
              && document.querySelector('[data-testid="alignment-task-goal-input"]')?.value === task""",
            arg=task,
            timeout=10_000,
        )
        assert page.get_by_test_id("alignment-loopora-fit-reason-input").input_value() == ""
        assert page.get_by_test_id("alignment-send-button").is_enabled()
        _assert_alignment_fit_entry_phase(page, phase="partial", known_count=1, missing_count=4)


def _assert_installed_entries_do_not_guess_an_ambiguous_host(page) -> None:
    page.get_by_test_id("agent-host-codex").check()
    page.get_by_test_id("agent-adapter-install-codex").click()
    page.wait_for_function(
        """() => document.querySelector('[data-agent-host-status="codex"]')?.textContent === 'Installed'""",
        timeout=10_000,
    )
    page.reload(wait_until="domcontentloaded")
    page.get_by_test_id("agent-readiness-title").wait_for(state="visible", timeout=10_000)
    page.wait_for_function(
        """() => document.querySelector('[data-testid="agent-readiness-title"]')?.textContent
          === 'Codex can start Loopora'""",
        timeout=10_000,
    )
    assert page.get_by_test_id("agent-host-codex").is_checked()

    page.get_by_test_id("agent-host-claude").check()
    page.get_by_test_id("agent-adapter-install-claude").click()
    page.wait_for_function(
        """() => document.querySelector('[data-agent-host-status="claude"]')?.textContent === 'Installed'""",
        timeout=10_000,
    )
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function(
        """() => document.querySelector('[data-testid="agent-readiness-title"]')?.textContent
          === 'Choose the Agent you are using now'""",
        timeout=10_000,
    )
    assert not page.get_by_test_id("agent-host-codex").is_checked()
    assert not page.get_by_test_id("agent-host-claude").is_checked()
    assert page.get_by_test_id("agent-adapter-grid").is_hidden()


def _select_explicit_codex_host(page, target: Path) -> None:
    assert page.get_by_test_id("agent-readiness-copy-install").count() == 0
    assert page.get_by_test_id("agent-readiness-copy-readiness").count() == 0
    assert page.get_by_test_id("agent-readiness-copy-public").count() == 1
    assert page.get_by_test_id("agent-adapter-grid").is_hidden()
    assert not page.get_by_test_id("agent-host-codex").is_checked()
    assert not page.get_by_test_id("agent-host-claude").is_checked()
    assert not page.get_by_test_id("agent-host-opencode").is_checked()
    assert not any((target / root).exists() for root in (".agents", ".claude", ".opencode"))
    assert page.get_by_test_id("agent-adapter-install-codex").is_disabled()
    assert page.get_by_test_id("agent-adapter-install-claude").is_disabled()

    page.get_by_test_id("agent-host-codex").check()
    page.wait_for_function(
        """() => document.querySelector('[data-testid="agent-readiness-title"]')?.textContent
            === 'Codex needs its project entry'
          && !document.querySelector('[data-testid="agent-adapter-install-codex"]')?.disabled""",
        timeout=10_000,
    )
    assert page.get_by_test_id("agent-adapter-grid").is_visible()
    assert page.get_by_test_id("agent-host-codex").is_checked()
    assert page.get_by_test_id("agent-adapter-codex").is_visible()
    assert page.get_by_test_id("agent-adapter-claude").is_hidden()
    assert page.get_by_test_id("agent-adapter-opencode").is_hidden()
    assert page.get_by_test_id("agent-adapter-install-codex").is_enabled()
    assert page.get_by_test_id("agent-adapter-install-claude").is_disabled()
    assert page.get_by_test_id("agent-readiness-copy-readiness").count() == 1


def test_browser_tools_requires_explicit_target_and_host_before_copying_agent_commands(tmp_path: Path) -> None:
    service = _service(tmp_path)
    target = tmp_path / "same-agent explicit target"
    target.mkdir()
    resolved_target = str(target.resolve())

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page()
        page.goto(f"{base_url}/same-agent", wait_until="domcontentloaded")
        page.get_by_test_id("agent-readiness-title").wait_for(state="visible", timeout=10_000)

        assert page.get_by_test_id("agent-readiness-copy-install").count() == 0
        assert page.get_by_test_id("agent-readiness-copy-readiness").count() == 0
        assert page.get_by_test_id("agent-readiness-copy-public").count() == 0
        assert page.get_by_test_id("agent-adapter-use-server-workdir").is_hidden()
        for testid in (
            "agent-adapter-install-codex",
            "agent-adapter-uninstall-codex",
            "agent-adapter-install-claude",
            "agent-adapter-uninstall-claude",
            "agent-adapter-install-opencode",
            "agent-adapter-uninstall-opencode",
        ):
            assert page.get_by_test_id(testid).is_disabled()
        support_state = page.locator("[data-testid='tools-support-panel']").evaluate(
            """(panel) => ({
              next: panel.dataset.supportNextActionKinds.split(",").filter(Boolean),
              ready: panel.dataset.supportReadyNextActionKinds.split(",").filter(Boolean),
              blocked: panel.dataset.supportBlockedNextActionKinds.split(",").filter(Boolean),
              targetNoteHidden: panel.querySelector("[data-support-target-required-note]")?.hidden,
            })"""
        )
        assert "choose_workdir_for_public_report" in support_state["next"]
        assert "choose_workdir_for_public_report" in support_state["ready"]
        assert "run_public_issue_bundle" in support_state["blocked"]
        assert "run_public_issue_bundle" not in support_state["ready"]
        assert "run_public_doctor_report" in support_state["blocked"]
        assert "run_public_doctor_report" not in support_state["ready"]
        assert support_state["targetNoteHidden"] is False

        page.get_by_test_id("agent-adapter-workdir").fill(resolved_target)
        page.wait_for_function(
            """() => document.querySelector('[data-testid="agent-readiness-title"]')?.textContent
                === 'Choose the Agent you are using now'
              && document.querySelector('[data-testid="agent-readiness-copy-public"]')""",
            timeout=10_000,
        )
        support_state = page.locator("[data-testid='tools-support-panel']").evaluate(
            """(panel) => ({
              next: panel.dataset.supportNextActionKinds.split(",").filter(Boolean),
              ready: panel.dataset.supportReadyNextActionKinds.split(",").filter(Boolean),
              blocked: panel.dataset.supportBlockedNextActionKinds.split(",").filter(Boolean),
              targetNoteHidden: panel.querySelector("[data-support-target-required-note]")?.hidden,
            })"""
        )

        _select_explicit_codex_host(page, target)

        page.get_by_test_id("agent-host-claude").check()
        assert page.get_by_test_id("agent-adapter-codex").is_hidden()
        assert page.get_by_test_id("agent-adapter-claude").is_visible()
        assert page.get_by_test_id("agent-adapter-install-claude").is_enabled()
        assert page.get_by_test_id("agent-adapter-install-codex").is_disabled()
        assert "choose_workdir_for_public_report" not in support_state["next"]
        assert "run_public_issue_bundle" in support_state["ready"]
        assert "run_public_issue_bundle" not in support_state["blocked"]
        assert "run_public_doctor_report" in support_state["ready"]
        assert "run_public_doctor_report" not in support_state["blocked"]
        assert support_state["targetNoteHidden"] is True

        _assert_installed_entries_do_not_guess_an_ambiguous_host(page)


def test_browser_support_page_syncs_public_report_to_global_workdir(tmp_path: Path) -> None:
    service = _service(tmp_path)
    target = tmp_path / "support synced target"
    target.mkdir()
    resolved_target = str(target.resolve())
    requested_urls: list[str] = []

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page()
        page.route(
            "**/api/diagnostics/public-issue-bundle?*",
            lambda route: (
                requested_urls.append(route.request.url),
                route.fulfill(status=200, content_type="text/plain", body="public bundle for synced target"),
            ),
        )
        page.goto(f"{base_url}/support", wait_until="domcontentloaded")
        page.get_by_test_id("support-page").wait_for(state="visible", timeout=10_000)
        page.evaluate(
            """() => {
              window.__looporaCopiedSupportBundle = "";
              window.LooporaUI.writeTextToClipboard = async (value) => {
                window.__looporaCopiedSupportBundle = value;
              };
            }"""
        )
        page.evaluate(
            """target => window.LooporaUI.syncWorkdirContext(target, {syncUrl: true, urlParam: "workdir"})""",
            resolved_target,
        )
        page.wait_for_function(
            """target => document.querySelector('[data-testid="support-target-workdir-input"]')?.value === target
              && document.querySelector('[data-testid="support-public-report-link"]')?.dataset.supportCopyPublicReport === 'true'
              && new URL(
                document.querySelector('[data-testid="tools-support-panel"]')?.dataset.supportPublicReportUrl || "",
                location.origin
              ).searchParams.get("workdir") === target""",
            arg=resolved_target,
            timeout=10_000,
        )
        support_state = page.evaluate(
            """() => {
              const panel = document.querySelector('[data-testid="tools-support-panel"]');
              const issueCommand = document.querySelector('[data-testid="tools-support-copy-public-issue-bundle-command"]');
              const fallbackCommand = document.querySelector('[data-testid="tools-support-copy-public-report-command"]');
              return {
                urlWorkdir: new URL(location.href).searchParams.get("workdir"),
                heroRequired: document.querySelector('[data-testid="support-hero-target-context"]')?.dataset.supportTargetProjectRequired,
                heroText: document.querySelector('[data-testid="support-hero-target-context"]')?.textContent.replace(/\\s+/g, " ").trim(),
                targetStatus: document.querySelector('[data-testid="support-target-status"]')?.textContent || "",
                publicReportUrl: panel?.dataset.supportPublicReportUrl || "",
                publicReportWorkdir: new URL(panel?.dataset.supportPublicReportUrl || "", location.origin).searchParams.get("workdir"),
                targetNoteHidden: panel?.querySelector("[data-support-target-required-note]")?.hidden,
                stateNoteHidden: panel?.querySelector("[data-support-target-state-note]")?.hidden,
                issueDisabled: issueCommand?.disabled,
                fallbackDisabled: fallbackCommand?.disabled,
                issueCommand: issueCommand?.dataset.supportCommandCopy || "",
                fallbackCommand: fallbackCommand?.dataset.supportCommandCopy || "",
              };
            }"""
        )
        assert support_state["urlWorkdir"] == resolved_target
        assert support_state["heroRequired"] == "false"
        assert "selected, pending refresh" in support_state["heroText"]
        assert "Current Web target synced" in support_state["targetStatus"]
        assert support_state["publicReportWorkdir"] == resolved_target
        assert support_state["targetNoteHidden"] is True
        assert support_state["stateNoteHidden"] is False
        assert support_state["issueDisabled"] is False
        assert support_state["fallbackDisabled"] is False
        assert "<project-dir>" not in support_state["issueCommand"]
        assert "<project-dir>" not in support_state["fallbackCommand"]
        assert resolved_target in support_state["issueCommand"]
        assert resolved_target in support_state["fallbackCommand"]

        page.get_by_test_id("support-public-report-link").click()
        page.wait_for_function("() => window.__looporaCopiedSupportBundle", timeout=10_000)
        assert page.evaluate("() => window.__looporaCopiedSupportBundle") == "public bundle for synced target"
        assert len(requested_urls) == 1
        assert parse_qs(urlparse(requested_urls[0]).query)["workdir"] == [resolved_target]


def test_browser_home_first_run_actions_track_global_workdir_change(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_workdir = tmp_path / "home first run source"
    target_workdir = tmp_path / "home first run target"
    source_workdir.mkdir()
    target_workdir.mkdir()
    resolved_source = str(source_workdir.resolve())
    resolved_target = str(target_workdir.resolve())

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/?workdir={quote(resolved_source, safe='')}", wait_until="domcontentloaded")
        page.get_by_test_id("home-first-run-actions").wait_for(state="visible", timeout=10_000)

        initial_state = page.evaluate(
            """() => ({
              currentUrl: new URL(location.href).searchParams.get("workdir"),
              fitGuide: new URL(document.querySelector('[data-testid="home-fit-guide-link"]').href).searchParams.get("workdir"),
              compose: new URL(document.querySelector('[data-testid="home-compose-loop-link"]').href).searchParams.get("alignment_workdir"),
              tools: new URL(document.querySelector('[data-testid="home-agent-entry-link"]').href).searchParams.get("workdir"),
            })"""
        )
        assert initial_state == {
            "currentUrl": resolved_source,
            "fitGuide": resolved_source,
            "compose": resolved_source,
            "tools": resolved_source,
        }
        assert page.get_by_test_id("home-activity-section").count() == 0
        assert page.get_by_test_id("home-saved-loops-section").count() == 0
        page.set_viewport_size({"width": 390, "height": 844})
        _assert_no_horizontal_overflow(page)

        page.evaluate(
            """target => window.LooporaUI.syncWorkdirContext(target, {syncUrl: true, urlParam: "workdir"})""",
            resolved_target,
        )
        page.wait_for_function(
            """target => new URL(document.querySelector('[data-testid="home-fit-guide-link"]').href).searchParams.get("workdir") === target
              && new URL(document.querySelector('[data-testid="home-compose-loop-link"]').href).searchParams.get("alignment_workdir") === target
              && new URL(document.querySelector('[data-testid="home-agent-entry-link"]').href).searchParams.get("workdir") === target
              && new URL(location.href).searchParams.get("workdir") === target""",
            arg=resolved_target,
            timeout=10_000,
        )
        switched_state = page.evaluate(
            """() => ({
              global: document.querySelector('[data-testid="global-workdir-context"] code')?.textContent || "",
              fitGuide: new URL(document.querySelector('[data-testid="home-fit-guide-link"]').href).searchParams.get("workdir"),
              compose: new URL(document.querySelector('[data-testid="home-compose-loop-link"]').href).searchParams.get("alignment_workdir"),
              tools: new URL(document.querySelector('[data-testid="home-agent-entry-link"]').href).searchParams.get("workdir"),
            })"""
        )
        assert switched_state == {
            "global": resolved_target,
            "fitGuide": resolved_target,
            "compose": resolved_target,
            "tools": resolved_target,
        }


def test_browser_home_returning_actions_track_global_workdir_change(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_workdir = tmp_path / "home returning source"
    target_workdir = tmp_path / "home returning target"
    source_workdir.mkdir()
    target_workdir.mkdir()
    spec_path = tmp_path / "returning-spec.md"
    spec_path.write_text("# Task\n\nReview an existing Loop with weak evidence.\n", encoding="utf-8")
    loop = _create_loop(service, spec_path, source_workdir)
    run = service.start_run(loop["id"])
    service.repository.update_run(
        run["id"],
        status="succeeded",
        summary_md="# Loopora Run Summary\n\nCoverage still needs direct evidence.",
        task_verdict={
            "status": "insufficient_evidence",
            "source": "gatekeeper",
            "summary": "Coverage still needs direct evidence.",
        },
    )
    resolved_source = str(source_workdir.resolve())
    resolved_target = str(target_workdir.resolve())

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/?workdir={quote(resolved_source, safe='')}", wait_until="domcontentloaded")
        page.get_by_test_id("home-returning-actions").wait_for(state="visible", timeout=10_000)
        page.get_by_test_id("home-returning-attention-link").wait_for(state="visible", timeout=10_000)
        page.get_by_test_id("loop-card").first.wait_for(state="attached", timeout=10_000)

        initial_state = page.evaluate(
            """() => ({
              currentUrl: new URL(location.href).searchParams.get("workdir"),
              attention: new URL(document.querySelector('[data-testid="home-returning-attention-link"]').href).searchParams.get("workdir"),
              activeRow: new URL(document.querySelector('[data-testid="home-active-loop"]').href).searchParams.get("workdir"),
              card: new URL(document.querySelector('[data-testid="loop-card"]').dataset.openCard, location.origin).searchParams.get("workdir"),
              cardLink: new URL(document.querySelector('[data-testid="loop-card"] .loop-card-link').href).searchParams.get("workdir"),
              compose: new URL(document.querySelector('[data-testid="home-returning-compose-link"]').href).searchParams.get("workdir"),
              fitGuide: new URL(document.querySelector('[data-testid="home-returning-fit-link"]').href).searchParams.get("workdir"),
            })"""
        )
        assert initial_state == {
            "currentUrl": resolved_source,
            "attention": resolved_source,
            "activeRow": resolved_source,
            "card": resolved_source,
            "cardLink": resolved_source,
            "compose": resolved_source,
            "fitGuide": resolved_source,
        }

        page.evaluate(
            """target => window.LooporaUI.syncWorkdirContext(target, {syncUrl: true, urlParam: "workdir"})""",
            resolved_target,
        )
        page.wait_for_function(
            """target => ["home-returning-attention-link", "home-active-loop", "home-returning-compose-link", "home-returning-fit-link"].every((testid) => (
                new URL(document.querySelector(`[data-testid="${testid}"]`).href).searchParams.get("workdir") === target
              ))
              && new URL(document.querySelector('[data-testid="loop-card"]').dataset.openCard, location.origin).searchParams.get("workdir") === target
              && new URL(document.querySelector('[data-testid="loop-card"] .loop-card-link').href).searchParams.get("workdir") === target
              && new URL(location.href).searchParams.get("workdir") === target""",
            arg=resolved_target,
            timeout=10_000,
        )
        switched_state = page.evaluate(
            """() => ({
              global: document.querySelector('[data-testid="global-workdir-context"] code')?.textContent || "",
              attention: new URL(document.querySelector('[data-testid="home-returning-attention-link"]').href).searchParams.get("workdir"),
              activeRow: new URL(document.querySelector('[data-testid="home-active-loop"]').href).searchParams.get("workdir"),
              card: new URL(document.querySelector('[data-testid="loop-card"]').dataset.openCard, location.origin).searchParams.get("workdir"),
              cardLink: new URL(document.querySelector('[data-testid="loop-card"] .loop-card-link').href).searchParams.get("workdir"),
              compose: new URL(document.querySelector('[data-testid="home-returning-compose-link"]').href).searchParams.get("workdir"),
              fitGuide: new URL(document.querySelector('[data-testid="home-returning-fit-link"]').href).searchParams.get("workdir"),
            })"""
        )
        assert switched_state == {
            "global": resolved_target,
            "attention": resolved_target,
            "activeRow": resolved_target,
            "card": resolved_target,
            "cardLink": resolved_target,
            "compose": resolved_target,
            "fitGuide": resolved_target,
        }


def test_browser_bundles_import_form_tracks_global_workdir_change(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_workdir = tmp_path / "bundles source target"
    target_workdir = tmp_path / "bundles switched target"
    source_workdir.mkdir()
    target_workdir.mkdir()
    resolved_source = str(source_workdir.resolve())
    resolved_target = str(target_workdir.resolve())

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/bundles?workdir={quote(resolved_source, safe='')}", wait_until="domcontentloaded")
        page.get_by_test_id("bundle-import-form").wait_for(state="visible", timeout=10_000)
        initial_state = page.evaluate(
            """() => ({
              currentUrl: new URL(location.href).searchParams.get("workdir"),
              importAction: new URL(document.querySelector('[data-testid="bundle-import-form"]').action).searchParams.get("workdir"),
              createImport: new URL(document.querySelector('[data-testid="bundles-create-loop-import-link"]').href).searchParams.get("workdir"),
              composeLoop: new URL(document.querySelector('[data-testid="bundles-compose-loop-link"]').href).searchParams.get("workdir"),
            })"""
        )
        assert initial_state == {
            "currentUrl": resolved_source,
            "importAction": resolved_source,
            "createImport": resolved_source,
            "composeLoop": resolved_source,
        }

        page.evaluate(
            """target => window.LooporaUI.syncWorkdirContext(target, {syncUrl: true, urlParam: "workdir"})""",
            resolved_target,
        )
        page.wait_for_function(
            """target => new URL(document.querySelector('[data-testid="bundle-import-form"]').action).searchParams.get("workdir") === target
              && new URL(location.href).searchParams.get("workdir") === target""",
            arg=resolved_target,
            timeout=10_000,
        )
        switched_state = page.evaluate(
            """() => ({
              global: document.querySelector('[data-testid="global-workdir-context"] code')?.textContent || "",
              importAction: new URL(document.querySelector('[data-testid="bundle-import-form"]').action).searchParams.get("workdir"),
              createImport: new URL(document.querySelector('[data-testid="bundles-create-loop-import-link"]').href).searchParams.get("workdir"),
              composeLoop: new URL(document.querySelector('[data-testid="bundles-compose-loop-link"]').href).searchParams.get("workdir"),
            })"""
        )
        assert switched_state == {
            "global": resolved_target,
            "importAction": resolved_target,
            "createImport": resolved_target,
            "composeLoop": resolved_target,
        }


def test_browser_bundles_derive_form_tracks_global_workdir_change(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_workdir = tmp_path / "derive source target"
    target_workdir = tmp_path / "derive switched target"
    source_workdir.mkdir()
    target_workdir.mkdir()
    spec_path = tmp_path / "derive-spec.md"
    spec_path.write_text("# Task\n\nExport this Loop as a reusable plan.\n", encoding="utf-8")
    loop = _create_loop(service, spec_path, source_workdir)
    resolved_source = str(source_workdir.resolve())
    resolved_target = str(target_workdir.resolve())

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/bundles?workdir={quote(resolved_source, safe='')}", wait_until="domcontentloaded")
        page.get_by_test_id("bundle-derive-form").wait_for(state="visible", timeout=10_000)
        initial_state = page.evaluate(
            """() => ({
              currentUrl: new URL(location.href).searchParams.get("workdir"),
              deriveAction: new URL(document.querySelector('[data-testid="bundle-derive-form"]').action).searchParams.get("workdir"),
              importAction: new URL(document.querySelector('[data-testid="bundle-import-form"]').action).searchParams.get("workdir"),
              loopOption: document.querySelector('[data-testid="bundle-derive-loop-select"] option[value]:not([value=""])')?.value || "",
            })"""
        )
        assert initial_state == {
            "currentUrl": resolved_source,
            "deriveAction": resolved_source,
            "importAction": resolved_source,
            "loopOption": loop["id"],
        }

        page.evaluate(
            """target => window.LooporaUI.syncWorkdirContext(target, {syncUrl: true, urlParam: "workdir"})""",
            resolved_target,
        )
        page.wait_for_function(
            """target => new URL(document.querySelector('[data-testid="bundle-derive-form"]').action).searchParams.get("workdir") === target
              && new URL(location.href).searchParams.get("workdir") === target""",
            arg=resolved_target,
            timeout=10_000,
        )
        switched_state = page.evaluate(
            """() => ({
              global: document.querySelector('[data-testid="global-workdir-context"] code')?.textContent || "",
              deriveAction: new URL(document.querySelector('[data-testid="bundle-derive-form"]').action).searchParams.get("workdir"),
              importAction: new URL(document.querySelector('[data-testid="bundle-import-form"]').action).searchParams.get("workdir"),
              createImport: new URL(document.querySelector('[data-testid="bundles-create-loop-import-link"]').href).searchParams.get("workdir"),
              composeLoop: new URL(document.querySelector('[data-testid="bundles-compose-loop-link"]').href).searchParams.get("workdir"),
            })"""
        )
        assert switched_state == {
            "global": resolved_target,
            "deriveAction": resolved_target,
            "importAction": resolved_target,
            "createImport": resolved_target,
            "composeLoop": resolved_target,
        }


def test_browser_bundle_cards_track_global_workdir_change(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_workdir = tmp_path / "bundle card source target"
    target_workdir = tmp_path / "bundle card switched target"
    source_workdir.mkdir()
    target_workdir.mkdir()
    spec_path = tmp_path / "bundle-card-spec.md"
    spec_path.write_text("# Task\n\nReuse this reviewed Plan File from the card body.\n", encoding="utf-8")
    loop = _create_loop(service, spec_path, source_workdir)
    imported = service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="Browser Card Plan",
                description="A reusable plan listed as a clickable card.",
                collaboration_summary="Card body should preserve the selected project context.",
            )
        )
    )
    bundle = imported
    card_selector = f'[data-testid="bundle-exchange-item-{bundle["id"]}"]'
    resolved_source = str(source_workdir.resolve())
    resolved_target = str(target_workdir.resolve())

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/bundles?workdir={quote(resolved_source, safe='')}", wait_until="domcontentloaded")
        page.locator(card_selector).wait_for(state="visible", timeout=10_000)
        initial_state = page.evaluate(
            """selector => {
              const card = document.querySelector(selector);
              return {
                currentUrl: new URL(location.href).searchParams.get("workdir"),
                card: new URL(card.dataset.openCard, location.origin).searchParams.get("workdir"),
                cardLink: new URL(card.querySelector(".loop-card-link").href).searchParams.get("workdir"),
              };
            }""",
            arg=card_selector,
        )
        assert initial_state == {
            "currentUrl": resolved_source,
            "card": resolved_source,
            "cardLink": resolved_source,
        }

        page.evaluate(
            """target => window.LooporaUI.syncWorkdirContext(target, {syncUrl: true, urlParam: "workdir"})""",
            resolved_target,
        )
        page.wait_for_function(
            """([selector, target]) => {
              const card = document.querySelector(selector);
              return new URL(card.dataset.openCard, location.origin).searchParams.get("workdir") === target
                && new URL(card.querySelector(".loop-card-link").href).searchParams.get("workdir") === target
                && new URL(location.href).searchParams.get("workdir") === target;
            }""",
            arg=[card_selector, resolved_target],
            timeout=10_000,
        )
        switched_state = page.evaluate(
            """selector => {
              const card = document.querySelector(selector);
              return {
                global: document.querySelector('[data-testid="global-workdir-context"] code')?.textContent || "",
                card: new URL(card.dataset.openCard, location.origin).searchParams.get("workdir"),
                cardLink: new URL(card.querySelector(".loop-card-link").href).searchParams.get("workdir"),
              };
            }""",
            arg=card_selector,
        )
        assert switched_state == {
            "global": resolved_target,
            "card": resolved_target,
            "cardLink": resolved_target,
        }


def _assert_bundle_detail_review_posture(page, *, compact: bool) -> None:
    state = page.evaluate(
        """() => {
          const review = document.querySelector('[data-testid="bundle-review-surface"]');
          const judgment = document.querySelector('[data-testid="bundle-judgment-grid"]');
          const repair = document.querySelector('[data-testid="bundle-review-repair-state"]');
          const reviewBody = judgment || repair;
          const decision = document.querySelector('[data-testid="bundle-run-decision"]');
          const scope = document.querySelector('[data-testid="bundle-review-task-scope"]');
          const management = document.querySelector('[data-testid="bundle-plan-management"]');
          return {
            activeView: review?.dataset.activeReviewView,
            tabCount: review?.querySelectorAll('[role="tab"]').length,
            heroActions: document.querySelectorAll('.bundle-detail-hero a, .bundle-detail-hero button').length,
            decisionAfterReview: decision?.getBoundingClientRect().top >= reviewBody?.getBoundingClientRect().bottom,
            reviewStartsInViewport: review?.getBoundingClientRect().top < innerHeight,
            scopeStartsInViewport: scope?.getBoundingClientRect().top < innerHeight,
            managementOpen: management?.open,
            overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth,
          };
        }"""
    )
    assert state["activeView"] == "judgment"
    assert state["tabCount"] == 3
    assert state["heroActions"] == 0
    assert state["decisionAfterReview"] is True
    assert state["reviewStartsInViewport"] is True
    assert state["managementOpen"] is False
    assert state["overflowX"] is False
    if compact:
        assert state["scopeStartsInViewport"] is True


def test_browser_bundle_detail_expert_exits_track_global_workdir_change(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_workdir = tmp_path / "bundle detail source target"
    target_workdir = tmp_path / "bundle detail switched target"
    source_workdir.mkdir()
    target_workdir.mkdir()
    spec_path = tmp_path / "bundle-detail-spec.md"
    spec_path.write_text("# Task\n\nTune a reviewed Plan File from detail exits.\n", encoding="utf-8")
    loop = _create_loop(service, spec_path, source_workdir)
    bundle = service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="Browser Detail Plan",
                description="A reusable plan with linked expert assets.",
                collaboration_summary="Detail exits should preserve the selected project context.",
            )
        )
    )
    role_definition_id = bundle["role_definitions"][0]["id"]
    resolved_source = str(source_workdir.resolve())
    resolved_target = str(target_workdir.resolve())

    def state_script() -> str:
        return f"""() => {{
          const targetState = (href) => {{
            const url = new URL(href, location.origin);
            const nested = new URL(url.searchParams.get("return_to") || "/", location.origin);
            return [url.searchParams.get("workdir"), nested.searchParams.get("workdir")];
          }};
          return {{
            global: document.querySelector('[data-testid="global-workdir-context"] code')?.textContent || "",
            replace: targetState(document.querySelector('[data-testid="bundle-replace-yaml-link"]').href),
            orchestration: targetState(document.querySelector('[data-testid="bundle-orchestration-edit-link"]').href),
            role: targetState(document.querySelector('[data-testid="bundle-role-edit-link-{role_definition_id}"]').href),
          }};
        }}"""

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/bundles/{bundle['id']}?workdir={quote(resolved_source, safe='')}", wait_until="domcontentloaded")
        page.get_by_test_id("bundle-review-surface").wait_for(state="visible", timeout=10_000)
        _assert_bundle_detail_review_posture(page, compact=False)
        assert page.get_by_test_id("bundle-review-repair-state").is_visible()
        assert page.get_by_test_id("bundle-improve-chat-button").get_attribute("class") == "primary-button"
        assert page.get_by_test_id("bundle-start-run-button").get_attribute("class") == "secondary-button"

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(page.url, wait_until="domcontentloaded")
        mobile.get_by_test_id("bundle-review-surface").wait_for(state="visible", timeout=10_000)
        _assert_bundle_detail_review_posture(mobile, compact=True)
        mobile.close()

        page.locator('[data-bundle-review-tab="workflow"]').click()
        assert page.get_by_test_id("bundle-review-workflow-panel").is_visible()
        assert page.get_by_test_id("bundle-review-workflow-steps").locator(":scope > li").count() == 3
        page.locator('[data-bundle-review-tab="contract"]').click()
        assert page.get_by_test_id("bundle-review-contract-panel").is_visible()
        page.get_by_test_id("bundle-review-contract-panel").locator("[data-open-bundle-management]").click()
        assert page.get_by_test_id("bundle-plan-management").get_attribute("open") == ""
        page.get_by_test_id("bundle-replace-yaml-link").wait_for(state="visible", timeout=10_000)
        page.get_by_test_id("bundle-orchestration-edit-link").wait_for(state="attached", timeout=10_000)
        page.get_by_test_id(f"bundle-role-edit-link-{role_definition_id}").wait_for(state="attached", timeout=10_000)
        initial_state = page.evaluate(state_script())
        assert initial_state == {
            "global": resolved_source,
            "replace": [resolved_source, None],
            "orchestration": [resolved_source, resolved_source],
            "role": [resolved_source, resolved_source],
        }

        page.evaluate(
            """target => window.LooporaUI.syncWorkdirContext(target, {syncUrl: true, urlParam: "workdir"})""",
            resolved_target,
        )
        page.wait_for_function(
            f"""target => {{
              const replace = document.querySelector('[data-testid="bundle-replace-yaml-link"]');
              const orchestration = document.querySelector('[data-testid="bundle-orchestration-edit-link"]');
              const role = document.querySelector('[data-testid="bundle-role-edit-link-{role_definition_id}"]');
              const nestedTarget = (href) => {{
                const url = new URL(href, location.origin);
                return new URL(url.searchParams.get("return_to") || "/", location.origin).searchParams.get("workdir");
              }};
              return new URL(replace.href).searchParams.get("workdir") === target
                && new URL(orchestration.href).searchParams.get("workdir") === target
                && nestedTarget(orchestration.href) === target
                && new URL(role.href).searchParams.get("workdir") === target
                && nestedTarget(role.href) === target
                && new URL(location.href).searchParams.get("workdir") === target;
            }}""",
            arg=resolved_target,
            timeout=10_000,
        )
        switched_state = page.evaluate(state_script())
        assert switched_state == {
            "global": resolved_target,
            "replace": [resolved_target, None],
            "orchestration": [resolved_target, resolved_target],
            "role": [resolved_target, resolved_target],
        }


def test_browser_asset_editors_track_global_workdir_change(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_workdir = tmp_path / "asset editor source target"
    target_workdir = tmp_path / "asset editor switched target"
    source_workdir.mkdir()
    target_workdir.mkdir()
    resolved_source = str(source_workdir.resolve())
    resolved_target = str(target_workdir.resolve())
    return_to = f"/loops/new/manual?workdir={quote(resolved_source, safe='')}#manual-loop-form"
    builtin_role = next(item for item in service.list_role_definitions() if item.get("source") == "builtin")
    builtin_orchestration = next(item for item in service.list_orchestrations() if item.get("source") == "builtin")

    def editor_state_script(testid: str, link_targets: tuple[tuple[str, bool], ...]) -> str:
        link_testids_js = ", ".join(f'"{item[0]}"' for item in link_targets)
        return f"""() => {{
          const form = document.querySelector('[data-testid="{testid}"]');
          const action = new URL(form.action);
          const actionReturnTo = new URL(action.searchParams.get("return_to"), location.origin);
          const apiAction = new URL(form.dataset.apiAction, location.origin);
          const datasetReturnTo = new URL(form.dataset.returnTo, location.origin);
          const linkTargets = Object.fromEntries([{link_testids_js}].map((linkTestid) => {{
            const link = document.querySelector(`[data-testid="${{linkTestid}}"]`);
            const url = new URL(link.href, location.origin);
            const nested = new URL(url.searchParams.get("return_to") || "/", location.origin);
            return [linkTestid, [url.searchParams.get("workdir"), nested.searchParams.get("workdir")]];
          }}));
          return {{
            global: document.querySelector('[data-testid="global-workdir-context"] code')?.textContent || "",
            actionWorkdir: action.searchParams.get("workdir"),
            actionReturnToWorkdir: actionReturnTo.searchParams.get("workdir"),
            apiActionWorkdir: apiAction.searchParams.get("workdir"),
            datasetReturnToWorkdir: datasetReturnTo.searchParams.get("workdir"),
            linkTargets,
          }};
        }}"""

    editor_cases: tuple[tuple[str, str, tuple[tuple[str, bool], ...]], ...] = (
        (f"/roles/{builtin_role['id']}/edit", "role-definition-editor-form", (("role-definition-cancel-link", False),)),
        (
            f"/orchestrations/{builtin_orchestration['id']}/edit",
            "orchestration-editor-form",
            (
                ("orchestration-manage-roles-link", True),
                ("orchestration-create-from-preset-link", True),
                ("orchestration-cancel-link", False),
            ),
        ),
    )
    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        for path, testid, link_targets in editor_cases:
            page.goto(
                f"{base_url}{path}?workdir={quote(resolved_source, safe='')}&return_to={quote(return_to, safe='')}",
                wait_until="domcontentloaded",
            )
            page.get_by_test_id(testid).wait_for(state="visible", timeout=10_000)
            page.wait_for_function("() => Boolean(window.LooporaUI?.syncWorkdirContext)", timeout=10_000)
            initial_state = page.evaluate(editor_state_script(testid, link_targets))
            assert initial_state == {
                "global": resolved_source,
                "actionWorkdir": resolved_source,
                "actionReturnToWorkdir": resolved_source,
                "apiActionWorkdir": resolved_source,
                "datasetReturnToWorkdir": resolved_source,
                "linkTargets": {
                    link_testid: [resolved_source, resolved_source if has_nested_return else None] for link_testid, has_nested_return in link_targets
                },
            }

            page.evaluate(
                """target => window.LooporaUI.syncWorkdirContext(target, {syncUrl: true, urlParam: "workdir"})""",
                resolved_target,
            )
            page.wait_for_function(
                f"""target => {{
                  const form = document.querySelector('[data-testid="{testid}"]');
                  return new URL(form.action).searchParams.get("workdir") === target
                    && new URL(form.dataset.apiAction, location.origin).searchParams.get("workdir") === target
                    && new URL(form.dataset.returnTo, location.origin).searchParams.get("workdir") === target
                    && Array.from(document.querySelectorAll("[data-workdir-context-link]")).some((link) => new URL(link.href, location.origin).searchParams.get("workdir") === target)
                    && new URL(location.href).searchParams.get("workdir") === target;
                }}""",
                arg=resolved_target,
                timeout=10_000,
            )
            switched_state = page.evaluate(editor_state_script(testid, link_targets))
            assert switched_state == {
                "global": resolved_target,
                "actionWorkdir": resolved_target,
                "actionReturnToWorkdir": resolved_target,
                "apiActionWorkdir": resolved_target,
                "datasetReturnToWorkdir": resolved_target,
                "linkTargets": {
                    link_testid: [resolved_target, resolved_target if has_nested_return else None] for link_testid, has_nested_return in link_targets
                },
            }


def test_browser_asset_catalog_entry_points_track_global_workdir_change(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_workdir = tmp_path / "asset catalog source target"
    target_workdir = tmp_path / "asset catalog switched target"
    source_workdir.mkdir()
    target_workdir.mkdir()
    resolved_source = str(source_workdir.resolve())
    resolved_target = str(target_workdir.resolve())
    return_to = f"/loops/new/manual?workdir={quote(resolved_source, safe='')}#manual-loop-form"

    def catalog_state_script(create_testid: str, empty_create_testid: str, empty_template_testid: str) -> str:
        return f"""() => {{
          const targetState = (href) => {{
            const url = new URL(href, location.origin);
            const nested = new URL(url.searchParams.get("return_to") || "/", location.origin);
            return [url.searchParams.get("workdir"), nested.searchParams.get("workdir")];
          }};
          const card = document.querySelector('[data-workdir-context-open-card="workdir"]');
          const cardLink = card.querySelector(".loop-card-link");
          return {{
            global: document.querySelector('[data-testid="global-workdir-context"] code')?.textContent || "",
            create: targetState(document.querySelector('[data-testid="{create_testid}"]').href),
            emptyCreate: targetState(document.querySelector('[data-testid="{empty_create_testid}"]').href),
            emptyTemplate: targetState(document.querySelector('[data-testid="{empty_template_testid}"]').href),
            card: targetState(card.dataset.openCard),
            cardLink: targetState(cardLink.href),
          }};
        }}"""

    catalog_cases = (
        ("/roles", "role-definitions-page", "create-role-definition-link", "role-definitions-empty-create-link", "role-definitions-empty-template-link"),
        ("/orchestrations", "orchestrations-page", "create-orchestration-link", "orchestrations-empty-create-link", "orchestrations-empty-template-link"),
    )
    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        for path, page_testid, create_testid, empty_create_testid, empty_template_testid in catalog_cases:
            page.goto(
                f"{base_url}{path}?workdir={quote(resolved_source, safe='')}&return_to={quote(return_to, safe='')}",
                wait_until="domcontentloaded",
            )
            page.get_by_test_id(page_testid).wait_for(state="visible", timeout=10_000)
            page.wait_for_function("() => Boolean(window.LooporaUI?.syncWorkdirContext)", timeout=10_000)
            initial_state = page.evaluate(catalog_state_script(create_testid, empty_create_testid, empty_template_testid))
            assert initial_state == {
                "global": resolved_source,
                "create": [resolved_source, resolved_source],
                "emptyCreate": [resolved_source, resolved_source],
                "emptyTemplate": [resolved_source, resolved_source],
                "card": [resolved_source, resolved_source],
                "cardLink": [resolved_source, resolved_source],
            }

            page.evaluate(
                """target => window.LooporaUI.syncWorkdirContext(target, {syncUrl: true, urlParam: "workdir"})""",
                resolved_target,
            )
            page.wait_for_function(
                f"""target => {{
                  const href = document.querySelector('[data-testid="{create_testid}"]').href;
                  const card = document.querySelector('[data-workdir-context-open-card="workdir"]');
                  return new URL(href).searchParams.get("workdir") === target
                    && new URL(card.dataset.openCard, location.origin).searchParams.get("workdir") === target
                    && new URL(location.href).searchParams.get("workdir") === target;
                }}""",
                arg=resolved_target,
                timeout=10_000,
            )
            switched_state = page.evaluate(catalog_state_script(create_testid, empty_create_testid, empty_template_testid))
            assert switched_state == {
                "global": resolved_target,
                "create": [resolved_target, resolved_target],
                "emptyCreate": [resolved_target, resolved_target],
                "emptyTemplate": [resolved_target, resolved_target],
                "card": [resolved_target, resolved_target],
                "cardLink": [resolved_target, resolved_target],
            }


def _tutorial_fit_review_inputs() -> dict[str, str]:
    return {
        "task": "Create a release readiness checklist for first-time open-source maintainers.",
        "loopora_fit_reason": "The checklist needs multi-round evidence governance and release-gate review.",
        "direct_path_check": "Direct Agent work or hard checks alone would miss cross-round release-gate judgment.",
        "fake_done_risks": ("A long checklist that does not say which evidence proves done; missing rollback or ownership."),
        "required_evidence": "Maintainer can copy the brief, run the checks, and see one clear release gate.",
        "judgment_tradeoffs": ("Prefer fewer durable checks over broad process ceremony; keep it reversible for small projects."),
    }


def _open_generated_incomplete_fit_review(page, *, base_url: str, workdir: Path, task: str) -> None:
    review_action = start_guidance_payload({"task": task}, workdir=workdir)["review_actions"][0]
    review_url = urlparse(review_action["open_url"])
    page.goto(
        f"{base_url}{review_url.path}?{review_url.query}#{review_url.fragment}",
        wait_until="domcontentloaded",
    )
    page.get_by_test_id("tutorial-fit-task-review").wait_for(state="visible", timeout=10_000)
    assert page.get_by_test_id("tutorial-fit-task-input").input_value() == task
    assert urlparse(page.url).fragment == ""


def _fill_tutorial_fit_review(page, inputs: dict[str, str]) -> str:
    page.get_by_test_id("tutorial-fit-task-input").fill(inputs["task"])
    page.get_by_test_id("tutorial-fit-loopora-fit-reason-input").fill(inputs["loopora_fit_reason"])
    if direct_path_check := inputs.get("direct_path_check"):
        page.get_by_test_id("tutorial-fit-direct-path-check-input").fill(direct_path_check)
    page.get_by_test_id("tutorial-fit-fake-done-risks-input").fill(inputs["fake_done_risks"])
    page.get_by_test_id("tutorial-fit-required-evidence-input").fill(inputs["required_evidence"])
    page.get_by_test_id("tutorial-fit-judgment-tradeoffs-input").fill(inputs["judgment_tradeoffs"])
    draft = page.get_by_test_id("tutorial-fit-task-draft").input_value()
    assert inputs["task"] in draft
    assert inputs["loopora_fit_reason"] in draft
    assert inputs.get("direct_path_check", "") in draft
    assert inputs["judgment_tradeoffs"] in draft
    assert page.get_by_test_id("tutorial-fit-task-copy").is_enabled()
    return draft


def _assert_tutorial_fit_completion_command_cleared_for_complete(page) -> None:
    assert page.get_by_test_id("tutorial-fit-completion-command").input_value() == ""
    assert page.get_by_test_id("tutorial-fit-completion-command-copy").is_disabled()


def _assert_tools_received_session_only_fit_handoff(page, *, storage_key: str, inputs: dict[str, str], draft: str, workdir: str) -> None:
    page.wait_for_function("() => location.pathname === '/same-agent'", timeout=10_000)
    page.get_by_test_id("agent-adapter-draft-handoff").wait_for(state="visible", timeout=10_000)
    nav = page.evaluate(
        """() => ({
          pathname: location.pathname,
          workdir: new URL(location.href).searchParams.get("workdir"),
          paramNames: Array.from(new URL(location.href).searchParams.keys()),
        })"""
    )
    assert nav == {"pathname": "/same-agent", "workdir": workdir, "paramNames": ["workdir"]}

    stored = page.evaluate("(key) => JSON.parse(sessionStorage.getItem(key))", storage_key)
    assert stored["schema_version"] == 1
    assert stored["source"] == "tutorial_fit_review"
    assert stored["source_workdir"] == workdir
    assert stored["inputs"] == inputs
    assert stored["missing_first_task_input_ids"] == []
    assert stored["ready_for_loopora_plan_message"] is True
    assert stored["review_completion_command"] == ""
    assert stored["primary_first_task_message_state"]["completed_review"] is True
    assert stored["primary_first_task_message_state"]["copy_allowed"] is True
    assert stored["primary_first_task_message"] == draft
    assert stored["draft_first_task_message"] == draft


def _install_and_assert_fit_handoff_merges_into_adapter(page, *, draft: str, storage_key: str) -> None:
    copy_button = page.get_by_test_id("agent-draft-handoff-copy")
    assert copy_button.get_attribute("data-agent-draft-handoff-copy") == draft
    assert copy_button.get_attribute("aria-label") == "Copy the reviewed handoff for after setup is ready"
    assert page.get_by_test_id("agent-draft-handoff-title").text_content() == "Reviewed handoff; finish setup first"
    assert page.get_by_test_id("agent-draft-handoff-state").text_content().strip() == "Setup first"
    page.evaluate(
        """() => {
          window.__looporaCopiedText = null;
          Object.defineProperty(navigator, "clipboard", {
            value: {writeText: async (text) => { window.__looporaCopiedText = text; }},
            configurable: true,
          });
        }"""
    )
    copy_button.click()
    page.wait_for_function("() => window.__looporaCopiedText !== null", timeout=10_000)
    assert page.evaluate("() => window.__looporaCopiedText") == draft

    _assert_no_horizontal_overflow(page)
    page.get_by_test_id("agent-host-codex").check()
    install_button = page.get_by_test_id("agent-adapter-install-codex")
    install_button.wait_for(state="visible", timeout=10_000)
    page.wait_for_function(
        """() => !document.querySelector('[data-testid="agent-adapter-install-codex"]')?.disabled""",
        timeout=10_000,
    )
    install_button.click()
    page.wait_for_function(
        """(draft) => document
          .querySelector('[data-testid="agent-adapter-copy-first-task-example"]')
          ?.getAttribute("data-agent-adapter-command-copy") === draft""",
        arg=draft,
        timeout=10_000,
    )
    assert page.get_by_test_id("agent-adapter-draft-handoff").is_hidden()
    assert page.get_by_test_id("agent-adapter-copy-first-task-example").get_attribute("data-agent-adapter-command-copy") == draft
    assert page.get_by_test_id("agent-adapter-copy-first-task-example").get_attribute("aria-label") == ("Copy one-message /loopora-plan handoff")
    flow_order = page.evaluate(
        """() => Array.from(document.querySelector('[data-testid="agent-adapter-handoff-flow"]').children)
          .map((element) => element.getAttribute("data-testid") || element.className)"""
    )
    assert flow_order == [
        "agent-adapter-first-task-example",
        "agent-adapter-copy-first-task-example",
        "agent-adapter-command-then",
        "agent-adapter-copy-loop",
    ]
    assert page.get_by_test_id("agent-adapter-copy-gen").count() == 0
    assert page.get_by_test_id("agent-adapter-copy-loop").locator("span").first.text_content() == "2"

    page.evaluate("() => { window.__looporaCopiedText = null; }")
    page.get_by_test_id("agent-adapter-copy-first-task-example").click()
    page.wait_for_function("() => window.__looporaCopiedText !== null", timeout=10_000)
    assert page.evaluate("() => window.__looporaCopiedText") == draft

    page.get_by_test_id("agent-adapter-clear-first-task-example").click()
    page.wait_for_function(
        """(key) => sessionStorage.getItem(key) === null
          && !document.querySelector('[data-testid="agent-adapter-copy-first-task-example"]')
          && document.querySelector('[data-testid="agent-adapter-copy-gen"]')
            ?.getAttribute("data-agent-adapter-command-copy") === "/loopora-plan"
          && document.querySelector('[data-testid="agent-adapter-first-task-orientation-example"]')
          && document.querySelector('[data-testid="agent-adapter-copy-loop"] span')?.textContent === "2"
          && document.activeElement === document.querySelector('[data-testid="agent-adapter-workdir"]') """,
        arg=storage_key,
        timeout=10_000,
    )
    assert page.get_by_test_id("agent-adapter-draft-handoff").is_hidden()
    assert "/loopora-plan" in page.get_by_test_id("agent-adapter-first-task-orientation-example").text_content()


def _assert_mobile_fit_handoff_stays_merged(
    page,
    *,
    workdir: str,
    storage_key: str,
    inputs: dict[str, str],
    draft: str,
) -> None:
    mobile_payload = {
        "schema_version": 1,
        "source": "tutorial_fit_review",
        "source_workdir": workdir,
        "inputs": inputs,
        "draft_first_task_message": draft,
        "saved_at": "2026-01-01T00:00:00.000Z",
    }
    page.set_viewport_size({"width": 390, "height": 844})
    page.evaluate(
        """([key, payload]) => sessionStorage.setItem(key, JSON.stringify(payload))""",
        [storage_key, mobile_payload],
    )
    base_url = page.evaluate("() => location.origin")
    page.goto(f"{base_url}/same-agent?workdir={quote(workdir, safe='')}", wait_until="domcontentloaded")
    page.wait_for_function(
        """(draft) => document
          .querySelector('[data-testid="agent-adapter-copy-first-task-example"]')
          ?.getAttribute("data-agent-adapter-command-copy") === draft
          && document.querySelector('[data-testid="agent-adapter-draft-handoff"]')?.hidden""",
        arg=draft,
        timeout=10_000,
    )
    _assert_no_horizontal_overflow(page)


def _store_tutorial_fit_handoff(page, *, storage_key: str, inputs: dict[str, str], draft: str, workdir: str) -> None:
    payload = {
        "schema_version": 1,
        "source": "tutorial_fit_review",
        "source_workdir": workdir,
        "inputs": inputs,
        "draft_first_task_message": draft,
        "saved_at": "2026-01-01T00:00:00.000Z",
    }
    page.evaluate(
        """([key, payload]) => sessionStorage.setItem(key, JSON.stringify(payload))""",
        [storage_key, payload],
    )


def _assert_create_choice_reviewed_phase(page, *, task: str, judgment_count: int) -> None:
    phase = page.evaluate(
        """() => ({
          fitPromptHidden: document.querySelector('[data-testid="loop-create-fit-review"]')?.hidden,
          reviewOpen: document.querySelector('[data-testid="loop-create-tutorial-handoff-review"]')?.open,
          reviewCount: document.querySelector('[data-testid="loop-create-tutorial-handoff-review-count"]')?.textContent || "",
        })"""
    )
    assert phase == {"fitPromptHidden": True, "reviewOpen": False, "reviewCount": f"{judgment_count} items"}
    review = page.get_by_test_id("loop-create-tutorial-handoff-review")
    review.locator("summary").click()
    page.get_by_test_id("loop-create-tutorial-handoff-inputs").wait_for(state="visible", timeout=10_000)
    assert task in page.get_by_test_id("loop-create-tutorial-handoff-inputs").text_content()
    page.set_viewport_size({"width": 390, "height": 844})
    _assert_no_horizontal_overflow(page)
    page.set_viewport_size({"width": 1280, "height": 900})


def _tutorial_direct_handoff_link_state(page) -> dict:
    return page.evaluate(
        """() => {
          const linkState = (testid) => {
            const link = document.querySelector(`[data-testid="${testid}"]`);
            return {
              ariaDisabled: link?.getAttribute("aria-disabled"),
              classDisabled: link?.classList.contains("is-disabled"),
              handoffDisabled: link?.dataset.fitHandoffDisabled,
              hrefPresent: link?.hasAttribute("href"),
              pointerEvents: link ? getComputedStyle(link).pointerEvents : "",
              tabIndex: link?.getAttribute("tabindex"),
            };
          };
          return {
            tools: linkState("tutorial-fit-task-use-tools"),
            web: linkState("tutorial-fit-task-use-web"),
            choice: linkState("tutorial-web-compose-link"),
            setup: linkState("tutorial-agent-entry-link"),
            expert: linkState("tutorial-manual-compose-link"),
            navChoice: linkState("nav-compose-link"),
            navSetup: linkState("nav-tools-link"),
          };
        }"""
    )


def _assert_tutorial_direct_routes_blocked(page) -> None:
    assert _tutorial_direct_handoff_link_state(page) == {
        "tools": {"ariaDisabled": "true", "classDisabled": True, "handoffDisabled": "true", "hrefPresent": False, "pointerEvents": "none", "tabIndex": "-1"},
        "web": {"ariaDisabled": "true", "classDisabled": True, "handoffDisabled": "true", "hrefPresent": False, "pointerEvents": "none", "tabIndex": "-1"},
        "choice": {"ariaDisabled": "true", "classDisabled": True, "handoffDisabled": "true", "hrefPresent": False, "pointerEvents": "none", "tabIndex": "-1"},
        "setup": {"ariaDisabled": "true", "classDisabled": True, "handoffDisabled": "true", "hrefPresent": False, "pointerEvents": "none", "tabIndex": "-1"},
        "expert": {"ariaDisabled": "true", "classDisabled": True, "handoffDisabled": "true", "hrefPresent": False, "pointerEvents": "none", "tabIndex": "-1"},
        "navChoice": {
            "ariaDisabled": "true",
            "classDisabled": True,
            "handoffDisabled": "true",
            "hrefPresent": False,
            "pointerEvents": "none",
            "tabIndex": "-1",
        },
        "navSetup": {"ariaDisabled": "true", "classDisabled": True, "handoffDisabled": "true", "hrefPresent": False, "pointerEvents": "none", "tabIndex": "-1"},
    }
    page.set_viewport_size({"width": 390, "height": 844})
    _assert_no_horizontal_overflow(page)
    page.set_viewport_size({"width": 1280, "height": 900})


def _alignment_direct_handoff_state(page) -> dict[str, object]:
    return page.evaluate(
        """() => {
          const bridge = document.querySelector('[data-testid="alignment-tutorial-handoff-bridge"]');
          const sendButton = document.querySelector('[data-testid="alignment-send-button"]');
          const copyButton = document.querySelector('[data-testid="alignment-tutorial-handoff-copy-completion"]');
          const linkState = (testid) => {
            const node = document.querySelector(`[data-testid="${testid}"]`);
            return {
              ariaDisabled: node?.getAttribute("aria-disabled"),
              classDisabled: node?.classList.contains("is-disabled"),
              directBlocked: node?.dataset.directPathBlocked,
              hrefPresent: node?.hasAttribute("href"),
              tabIndex: node?.getAttribute("tabindex"),
            };
          };
          return {
            title: document.querySelector('[data-testid="alignment-tutorial-handoff-bridge"] h3')?.textContent || "",
            warning: bridge?.classList.contains("is-warning"),
            useSourceCount: document.querySelectorAll('[data-testid="alignment-tutorial-handoff-use-source"]').length,
            prefillCount: document.querySelectorAll('[data-testid="alignment-tutorial-handoff-prefill"]').length,
            finishCount: document.querySelectorAll('[data-testid="alignment-tutorial-handoff-finish-link"]').length,
            copyDirectLabel: copyButton?.textContent.trim() || "",
            sendDisabled: sendButton?.disabled,
            sendAction: sendButton?.dataset.action,
            importPath: linkState("alignment-path-import"),
            manualPath: linkState("alignment-path-manual"),
            newSession: {
              disabled: document.querySelector('[data-testid="alignment-new-session-button"]')?.disabled,
              ariaDisabled: document.querySelector('[data-testid="alignment-new-session-button"]')?.getAttribute("aria-disabled"),
              directBlocked: document.querySelector('[data-testid="alignment-new-session-button"]')?.dataset.directPathBlocked,
              tabIndex: document.querySelector('[data-testid="alignment-new-session-button"]')?.getAttribute("tabindex"),
            },
          };
        }"""
    )


def _assert_alignment_direct_handoff_blocks_web_compose(
    page,
    *,
    base_url: str,
    workdir: str,
    command: str,
    source_workdir: str | None = None,
) -> None:
    page.goto(f"{base_url}/loops/new/bundle?alignment_workdir={quote(workdir, safe='')}", wait_until="domcontentloaded")
    page.get_by_test_id("alignment-tutorial-handoff-bridge").wait_for(state="visible", timeout=10_000)

    if source_workdir and source_workdir != workdir:
        wrong_target_state = _alignment_direct_handoff_state(page)
        assert wrong_target_state["title"] == "Fit Guide judgment belongs to another project"
        assert wrong_target_state["warning"] is True
        assert wrong_target_state["useSourceCount"] == 1
        assert wrong_target_state["prefillCount"] == 0
        assert wrong_target_state["finishCount"] == 0
        assert wrong_target_state["copyDirectLabel"] == "Copy direct-path command"
        for route_state in (wrong_target_state["importPath"], wrong_target_state["manualPath"]):
            assert route_state["ariaDisabled"] != "true"
            assert route_state["classDisabled"] is False
            assert route_state["directBlocked"] != "true"
            assert route_state["hrefPresent"] is True
        assert wrong_target_state["newSession"]["directBlocked"] != "true"
        assert wrong_target_state["newSession"]["ariaDisabled"] != "true"

        page.evaluate(
            """() => {
              window.__looporaCopiedDirectDecision = "";
              window.LooporaUI.writeTextToClipboard = async (value) => {
                window.__looporaCopiedDirectDecision = value;
              };
            }"""
        )
        page.get_by_test_id("alignment-tutorial-handoff-copy-completion").click()
        assert page.evaluate("() => window.__looporaCopiedDirectDecision") == command

        page.get_by_test_id("alignment-tutorial-handoff-use-source").click()
        page.wait_for_function(
            """source => document.querySelector('[data-testid="alignment-workdir"]')?.value === source
              && document.querySelector('[data-testid="alignment-tutorial-handoff-bridge"] h3')?.textContent === 'Direct path selected'""",
            arg=source_workdir,
            timeout=10_000,
        )

    assert _alignment_direct_handoff_state(page) == {
        "title": "Direct path selected",
        "warning": False,
        "useSourceCount": 0,
        "prefillCount": 0,
        "finishCount": 0,
        "copyDirectLabel": "Copy direct-path command",
        "sendDisabled": True,
        "sendAction": "send",
        "importPath": {
            "ariaDisabled": "true",
            "classDisabled": True,
            "directBlocked": "true",
            "hrefPresent": False,
            "tabIndex": "-1",
        },
        "manualPath": {
            "ariaDisabled": "true",
            "classDisabled": True,
            "directBlocked": "true",
            "hrefPresent": False,
            "tabIndex": "-1",
        },
        "newSession": {
            "disabled": True,
            "ariaDisabled": "true",
            "directBlocked": "true",
            "tabIndex": "-1",
        },
    }
    blocked_navigation = page.evaluate(
        """() => {
          for (const testid of ["alignment-path-import", "alignment-path-manual", "alignment-new-session-button"]) {
            document.querySelector(`[data-testid="${testid}"]`)
              ?.dispatchEvent(new MouseEvent("click", {bubbles: true, cancelable: true}));
          }
          return {
            path: location.pathname,
            error: document.querySelector("#alignment-error")?.textContent || "",
            bridgeVisible: !document.querySelector('[data-testid="alignment-tutorial-handoff-bridge"]')?.hidden,
          };
        }"""
    )
    assert blocked_navigation["path"] == "/loops/new/bundle"
    assert "Direct path is selected" in blocked_navigation["error"]
    assert blocked_navigation["bridgeVisible"] is True
    page.evaluate(
        """() => {
          window.__looporaCopiedDirectDecision = "";
          window.LooporaUI.writeTextToClipboard = async (value) => {
            window.__looporaCopiedDirectDecision = value;
          };
        }"""
    )
    page.get_by_test_id("alignment-tutorial-handoff-copy-completion").click()
    assert page.evaluate("() => window.__looporaCopiedDirectDecision") == command
    page.evaluate("() => document.querySelector('[data-testid=\"alignment-start-form\"]').requestSubmit()")
    error_text = page.locator("#alignment-error").text_content()
    assert "Direct path is selected" in str(error_text)


def _assert_create_choice_direct_handoff_blocks_loopora_starts(
    page,
    *,
    base_url: str,
    workdir: str,
    source_workdir: str,
    command: str,
) -> None:
    page.goto(f"{base_url}/loops/new?workdir={quote(workdir, safe='')}", wait_until="domcontentloaded")
    page.get_by_test_id("loop-create-tutorial-handoff").wait_for(state="visible", timeout=10_000)
    choice_state = page.evaluate(
        """() => ({
          title: document.querySelector("[data-create-choice-handoff-title]")?.textContent || "",
          warning: document.querySelector('[data-testid="loop-create-tutorial-handoff"]')?.classList.contains("is-warning"),
          useSourceHidden: document.querySelector('[data-testid="loop-create-tutorial-handoff-use-source"]')?.hidden,
          toolsHidden: document.querySelector('[data-testid="loop-create-tutorial-handoff-tools-link"]')?.hidden,
          copyDirectHidden: document.querySelector('[data-testid="loop-create-tutorial-handoff-copy-direct"]')?.hidden,
          handoffWebDisabled: document.querySelector('[data-testid="loop-create-tutorial-handoff-web-link"]')?.getAttribute("aria-disabled"),
          setupDisabled: document.querySelector('[data-testid="loop-create-agent-link"]')?.getAttribute("aria-disabled"),
          setupHrefPresent: document.querySelector('[data-testid="loop-create-agent-link"]')?.hasAttribute("href"),
          setupPointerEvents: getComputedStyle(document.querySelector('[data-testid="loop-create-agent-link"]')).pointerEvents,
          importDisabled: document.querySelector('[data-testid="loop-create-import-link"]')?.getAttribute("aria-disabled"),
          manualDisabled: document.querySelector('[data-testid="loop-create-manual-link"]')?.getAttribute("aria-disabled"),
          importHrefPresent: document.querySelector('[data-testid="loop-create-import-link"]')?.hasAttribute("href"),
          manualHrefPresent: document.querySelector('[data-testid="loop-create-manual-link"]')?.hasAttribute("href"),
          importPointerEvents: getComputedStyle(document.querySelector('[data-testid="loop-create-import-link"]')).pointerEvents,
          manualPointerEvents: getComputedStyle(document.querySelector('[data-testid="loop-create-manual-link"]')).pointerEvents,
          webHrefPresent: document.querySelector('[data-testid="loop-create-bundle-link"]')?.hasAttribute("href"),
          handoffWebHrefPresent: document.querySelector('[data-testid="loop-create-tutorial-handoff-web-link"]')?.hasAttribute("href"),
          fitPromptHidden: document.querySelector('[data-testid="loop-create-fit-review"]')?.hidden,
          reviewOpen: document.querySelector('[data-testid="loop-create-tutorial-handoff-review"]')?.open,
        })"""
    )
    assert choice_state == {
        "title": "Fit review belongs to another target project",
        "warning": True,
        "useSourceHidden": False,
        "toolsHidden": False,
        "copyDirectHidden": False,
        "handoffWebDisabled": "false",
        "setupDisabled": "false",
        "setupHrefPresent": True,
        "setupPointerEvents": "auto",
        "importDisabled": "false",
        "manualDisabled": "false",
        "importHrefPresent": True,
        "manualHrefPresent": True,
        "importPointerEvents": "auto",
        "manualPointerEvents": "auto",
        "webHrefPresent": True,
        "handoffWebHrefPresent": True,
        "fitPromptHidden": False,
        "reviewOpen": True,
    }
    page.evaluate(
        """() => {
          window.__looporaCopiedDirectDecision = "";
          window.LooporaUI.writeTextToClipboard = async (value) => {
            window.__looporaCopiedDirectDecision = value;
          };
        }"""
    )
    page.get_by_test_id("loop-create-tutorial-handoff-copy-direct").click()
    assert page.evaluate("() => window.__looporaCopiedDirectDecision") == command

    page.get_by_test_id("loop-create-tutorial-handoff-use-source").click()
    page.wait_for_function(
        """source => new URL(location.href).searchParams.get("workdir") === source
          && document.querySelector("[data-create-choice-handoff-title]")?.textContent === "Direct path selected" """,
        arg=source_workdir,
        timeout=10_000,
    )
    choice_state = page.evaluate(
        """() => ({
          title: document.querySelector("[data-create-choice-handoff-title]")?.textContent || "",
          warning: document.querySelector('[data-testid="loop-create-tutorial-handoff"]')?.classList.contains("is-warning"),
          useSourceHidden: document.querySelector('[data-testid="loop-create-tutorial-handoff-use-source"]')?.hidden,
          toolsHidden: document.querySelector('[data-testid="loop-create-tutorial-handoff-tools-link"]')?.hidden,
          copyDirectHidden: document.querySelector('[data-testid="loop-create-tutorial-handoff-copy-direct"]')?.hidden,
          handoffWebDisabled: document.querySelector('[data-testid="loop-create-tutorial-handoff-web-link"]')?.getAttribute("aria-disabled"),
          setupDisabled: document.querySelector('[data-testid="loop-create-agent-link"]')?.getAttribute("aria-disabled"),
          setupHrefPresent: document.querySelector('[data-testid="loop-create-agent-link"]')?.hasAttribute("href"),
          setupPointerEvents: getComputedStyle(document.querySelector('[data-testid="loop-create-agent-link"]')).pointerEvents,
          importDisabled: document.querySelector('[data-testid="loop-create-import-link"]')?.getAttribute("aria-disabled"),
          manualDisabled: document.querySelector('[data-testid="loop-create-manual-link"]')?.getAttribute("aria-disabled"),
          importHrefPresent: document.querySelector('[data-testid="loop-create-import-link"]')?.hasAttribute("href"),
          manualHrefPresent: document.querySelector('[data-testid="loop-create-manual-link"]')?.hasAttribute("href"),
          importPointerEvents: getComputedStyle(document.querySelector('[data-testid="loop-create-import-link"]')).pointerEvents,
          manualPointerEvents: getComputedStyle(document.querySelector('[data-testid="loop-create-manual-link"]')).pointerEvents,
          webHrefPresent: document.querySelector('[data-testid="loop-create-bundle-link"]')?.hasAttribute("href"),
          handoffWebHrefPresent: document.querySelector('[data-testid="loop-create-tutorial-handoff-web-link"]')?.hasAttribute("href"),
          fitPromptHidden: document.querySelector('[data-testid="loop-create-fit-review"]')?.hidden,
          reviewOpen: document.querySelector('[data-testid="loop-create-tutorial-handoff-review"]')?.open,
        })"""
    )
    assert choice_state == {
        "title": "Direct path selected",
        "warning": False,
        "useSourceHidden": True,
        "toolsHidden": True,
        "copyDirectHidden": False,
        "handoffWebDisabled": "true",
        "setupDisabled": "true",
        "setupHrefPresent": False,
        "setupPointerEvents": "none",
        "importDisabled": "true",
        "manualDisabled": "true",
        "importHrefPresent": False,
        "manualHrefPresent": False,
        "importPointerEvents": "none",
        "manualPointerEvents": "none",
        "webHrefPresent": False,
        "handoffWebHrefPresent": False,
        "fitPromptHidden": True,
        "reviewOpen": False,
    }
    blocked_clicks = page.evaluate(
        """() => {
          window.__looporaRouteBlockedFeedback = [];
          window.LooporaUI.showAppFeedback = (message, kind) => {
            window.__looporaRouteBlockedFeedback.push({message, kind, path: location.pathname});
          };
          for (const testid of [
            "loop-create-bundle-link",
            "loop-create-agent-link",
            "loop-create-import-link",
            "loop-create-manual-link",
          ]) {
            document.querySelector(`[data-testid="${testid}"]`)?.click();
          }
          return {
            path: location.pathname,
            feedback: window.__looporaRouteBlockedFeedback,
          };
        }"""
    )
    assert blocked_clicks["path"] == "/loops/new"
    assert len(blocked_clicks["feedback"]) == 4
    assert all(item["kind"] == "error" and "Direct path is selected" in item["message"] for item in blocked_clicks["feedback"])
    page.evaluate(
        """() => {
          window.__looporaCopiedDirectDecision = "";
          window.LooporaUI.writeTextToClipboard = async (value) => {
            window.__looporaCopiedDirectDecision = value;
          };
        }"""
    )
    page.get_by_test_id("loop-create-tutorial-handoff-copy-direct").click()
    assert page.evaluate("() => window.__looporaCopiedDirectDecision") == command


def _assert_tools_direct_handoff_blocks_same_agent_setup(
    page,
    *,
    command: str,
    source_workdir: str,
    target_workdir: str,
) -> None:
    tools_state = page.evaluate(
        """() => {
          const buttonState = (testid) => {
            const button = document.querySelector(`[data-testid="${testid}"]`);
            return {
              disabled: button?.disabled,
              ariaDisabled: button?.getAttribute("aria-disabled"),
              directDisabled: button?.dataset.agentAdapterDirectPathDisabled,
              titleMentionsDirectBlock: (button?.getAttribute("title") || "").includes("same-Agent setup is disabled"),
            };
          };
          return {
            title: document.querySelector('[data-testid="agent-draft-handoff-title"]')?.textContent || "",
            state: document.querySelector('[data-testid="agent-draft-handoff-state"]')?.textContent.trim() || "",
            warning: document.querySelector('[data-testid="agent-adapter-draft-handoff"]')?.classList.contains("is-warning"),
            useSourceCount: document.querySelectorAll('[data-testid="agent-draft-handoff-use-source"]').length,
            currentWorkdirCount: document.querySelectorAll('[data-testid="agent-draft-handoff-current-workdir"]').length,
            copyDirectCount: document.querySelectorAll('[data-testid="agent-draft-handoff-copy-direct-decision"]').length,
            install: buttonState("agent-adapter-install-codex"),
            uninstall: buttonState("agent-adapter-uninstall-codex"),
          };
        }"""
    )
    assert tools_state["title"] == "Brief belongs to another target project"
    assert tools_state["state"] == "Different target"
    assert tools_state["warning"] is True
    assert tools_state["useSourceCount"] == 1
    assert tools_state["currentWorkdirCount"] == 1
    assert tools_state["copyDirectCount"] == 1
    for button_state in (tools_state["install"], tools_state["uninstall"]):
        assert button_state["directDisabled"] != "true"
        assert button_state["titleMentionsDirectBlock"] is False

    page.evaluate(
        """() => {
          window.__looporaCopiedDirectDecision = "";
          window.LooporaUI.writeTextToClipboard = async (value) => {
            window.__looporaCopiedDirectDecision = value;
          };
        }"""
    )
    page.get_by_test_id("agent-draft-handoff-copy-direct-decision").click()
    assert page.evaluate("() => window.__looporaCopiedDirectDecision") == command

    assert page.get_by_test_id("agent-adapter-workdir").input_value() == target_workdir
    page.get_by_test_id("agent-draft-handoff-use-source").click()
    page.wait_for_function(
        """source => document.querySelector('[data-testid="agent-adapter-workdir"]')?.value === source
          && document.querySelector('[data-testid="agent-draft-handoff-title"]')?.textContent === 'Direct path selected'""",
        arg=source_workdir,
        timeout=10_000,
    )
    tools_state = page.evaluate(
        """() => {
          const buttonState = (testid) => {
            const button = document.querySelector(`[data-testid="${testid}"]`);
            return {
              disabled: button?.disabled,
              ariaDisabled: button?.getAttribute("aria-disabled"),
              directDisabled: button?.dataset.agentAdapterDirectPathDisabled,
              titleMentionsDirectBlock: (button?.getAttribute("title") || "").includes("same-Agent setup is disabled"),
            };
          };
          return {
            title: document.querySelector('[data-testid="agent-draft-handoff-title"]')?.textContent || "",
            state: document.querySelector('[data-testid="agent-draft-handoff-state"]')?.textContent.trim() || "",
            warning: document.querySelector('[data-testid="agent-adapter-draft-handoff"]')?.classList.contains("is-warning"),
            useSourceCount: document.querySelectorAll('[data-testid="agent-draft-handoff-use-source"]').length,
            currentWorkdirCount: document.querySelectorAll('[data-testid="agent-draft-handoff-current-workdir"]').length,
            copyDirectCount: document.querySelectorAll('[data-testid="agent-draft-handoff-copy-direct-decision"]').length,
            install: buttonState("agent-adapter-install-codex"),
            uninstall: buttonState("agent-adapter-uninstall-codex"),
          };
        }"""
    )
    assert tools_state == {
        "title": "Direct path selected",
        "state": "Direct path",
        "warning": False,
        "useSourceCount": 0,
        "currentWorkdirCount": 0,
        "copyDirectCount": 1,
        "install": {
            "disabled": True,
            "ariaDisabled": "true",
            "directDisabled": "true",
            "titleMentionsDirectBlock": True,
        },
        "uninstall": {
            "disabled": True,
            "ariaDisabled": "true",
            "directDisabled": "true",
            "titleMentionsDirectBlock": True,
        },
    }
    page.evaluate(
        """() => {
          window.__looporaCopiedDirectDecision = "";
          window.LooporaUI.writeTextToClipboard = async (value) => {
            window.__looporaCopiedDirectDecision = value;
          };
        }"""
    )
    page.get_by_test_id("agent-draft-handoff-copy-direct-decision").click()
    assert page.evaluate("() => window.__looporaCopiedDirectDecision") == command
    mutation_calls: list[str] = []

    def record_install_mutation(route) -> None:
        mutation_calls.append(route.request.url)
        route.fulfill(status=418, content_type="application/json", body='{"error":"unexpected mutation"}')

    page.route("**/api/agent-adapters/codex/install", record_install_mutation)
    page.evaluate(
        """() => document.querySelector('[data-testid="agent-adapter-install-codex"]')
          .dispatchEvent(new MouseEvent("click", {bubbles: true, cancelable: true}))"""
    )
    page.wait_for_timeout(100)
    page.unroute("**/api/agent-adapters/codex/install", record_install_mutation)
    assert mutation_calls == []
    assert "Direct path is selected" in str(page.locator("#agent-adapter-status").text_content())


def _assert_manual_direct_handoff_blocks_import_and_manual(page, *, base_url: str, workdir: str, source_workdir: str, command: str) -> None:
    page.goto(f"{base_url}/loops/new/manual?workdir={quote(workdir, safe='')}", wait_until="domcontentloaded")
    page.get_by_test_id("manual-direct-handoff-bridge").wait_for(state="visible", timeout=10_000)
    direct_state = page.evaluate(
        r"""() => {
          const linkState = (testid) => {
            const link = document.querySelector(`[data-testid="${testid}"]`);
            return {
              ariaDisabled: link?.getAttribute("aria-disabled"),
              classDisabled: link?.classList.contains("is-disabled"),
              directBlocked: link?.dataset.directPathBlocked,
              hrefPresent: link?.hasAttribute("href"),
              tabIndex: link?.getAttribute("tabindex"),
            };
          };
          return {
            title: document.querySelector('[data-testid="manual-direct-handoff-bridge"] h3')?.textContent || "",
            copyLabel: document.querySelector('[data-testid="manual-direct-handoff-copy"]')?.textContent.trim() || "",
            meta: (document.querySelector('[data-testid="manual-direct-handoff-meta"]')?.textContent || "").replace(/\s+/g, " ").trim(),
            saveDisabled: document.querySelector('#save-loop-button')?.disabled,
            importDisabled: document.querySelector('[data-testid="bundle-import-submit-button"]')?.disabled,
            previewImportDisabled: document.querySelector('[data-testid="bundle-preview-import-button"]')?.disabled,
            manualBlocked: document.querySelector('[data-testid="loop-create-form"]')?.dataset.directPathBlocked,
            importBlocked: document.querySelector('[data-testid="loop-bundle-import-form"]')?.dataset.directPathBlocked,
            chatPath: linkState("alignment-path-chat"),
            importPath: linkState("alignment-path-import"),
            manualPath: linkState("alignment-path-manual"),
            newConversation: linkState("alignment-new-session-button"),
          };
        }"""
    )
    assert direct_state["title"] == "Direct-path decision belongs to another project"
    assert direct_state["copyLabel"] == "Copy direct-path command"
    assert direct_state["meta"] == (
        f"Source: {source_workdir} Current: {workdir} Goal: One small README typo "
        "Direct-path reason: One existing smoke test and one human review fully judge this task."
    )
    assert (direct_state["saveDisabled"], direct_state["importDisabled"], direct_state["previewImportDisabled"]) == (False, False, False)
    assert (direct_state["manualBlocked"], direct_state["importBlocked"]) == ("false", "false")
    for route_state in (direct_state["chatPath"], direct_state["importPath"], direct_state["manualPath"], direct_state["newConversation"]):
        assert route_state["ariaDisabled"] != "true"
        assert route_state["classDisabled"] is False
        assert route_state["directBlocked"] != "true"
        assert route_state["hrefPresent"] is True
    page.evaluate(
        """() => {
          window.__looporaCopiedDirectDecision = "";
          window.LooporaUI.writeTextToClipboard = async (value) => {
            window.__looporaCopiedDirectDecision = value;
          };
        }"""
    )
    page.get_by_test_id("manual-direct-handoff-copy").click()
    assert page.evaluate("() => window.__looporaCopiedDirectDecision") == command

    page.get_by_test_id("manual-direct-handoff-use-source").click()
    page.get_by_test_id("manual-direct-handoff-bridge").wait_for(state="visible", timeout=10_000)
    assert page.locator("#workdir-input").input_value() == source_workdir
    same_target_state = page.evaluate(
        r"""() => {
          const linkState = (testid) => {
            const link = document.querySelector(`[data-testid="${testid}"]`);
            return {
              ariaDisabled: link?.getAttribute("aria-disabled"),
              classDisabled: link?.classList.contains("is-disabled"),
              directBlocked: link?.dataset.directPathBlocked,
              hrefPresent: link?.hasAttribute("href"),
              tabIndex: link?.getAttribute("tabindex"),
            };
          };
          return {
            title: document.querySelector('[data-testid="manual-direct-handoff-bridge"] h3')?.textContent || "",
            saveDisabled: document.querySelector('#save-loop-button')?.disabled,
            importDisabled: document.querySelector('[data-testid="bundle-import-submit-button"]')?.disabled,
            previewImportDisabled: document.querySelector('[data-testid="bundle-preview-import-button"]')?.disabled,
            manualBlocked: document.querySelector('[data-testid="loop-create-form"]')?.dataset.directPathBlocked,
            importBlocked: document.querySelector('[data-testid="loop-bundle-import-form"]')?.dataset.directPathBlocked,
            chatPath: linkState("alignment-path-chat"),
            importPath: linkState("alignment-path-import"),
            manualPath: linkState("alignment-path-manual"),
            newConversation: linkState("alignment-new-session-button"),
          };
        }"""
    )
    assert same_target_state == {
        "title": "Direct path selected",
        "saveDisabled": True,
        "importDisabled": True,
        "previewImportDisabled": True,
        "manualBlocked": "true",
        "importBlocked": "true",
        "chatPath": {
            "ariaDisabled": "true",
            "classDisabled": True,
            "directBlocked": "true",
            "hrefPresent": False,
            "tabIndex": "-1",
        },
        "importPath": {
            "ariaDisabled": "true",
            "classDisabled": True,
            "directBlocked": "true",
            "hrefPresent": False,
            "tabIndex": "-1",
        },
        "manualPath": {
            "ariaDisabled": "true",
            "classDisabled": True,
            "directBlocked": "true",
            "hrefPresent": False,
            "tabIndex": "-1",
        },
        "newConversation": {
            "ariaDisabled": "true",
            "classDisabled": True,
            "directBlocked": "true",
            "hrefPresent": False,
            "tabIndex": "-1",
        },
    }
    blocked_navigation = page.evaluate(
        """() => {
          for (const testid of ["alignment-path-chat", "alignment-path-import", "alignment-path-manual", "alignment-new-session-button"]) {
            document.querySelector(`[data-testid="${testid}"]`)
              ?.dispatchEvent(new MouseEvent("click", {bubbles: true, cancelable: true}));
          }
          return {
            path: location.pathname,
            error: document.querySelector("#form-error")?.textContent || "",
            bridgeVisible: !document.querySelector('[data-testid="manual-direct-handoff-bridge"]')?.hidden,
          };
        }"""
    )
    assert blocked_navigation["path"] == "/loops/new/manual"
    assert "Direct path is selected" in blocked_navigation["error"]
    assert blocked_navigation["bridgeVisible"] is True
    page.evaluate(
        """() => document.querySelector('[data-testid="loop-create-form"]')
          .dispatchEvent(new Event("submit", {bubbles: true, cancelable: true}))"""
    )
    assert "Direct path is selected" in str(page.locator("#form-error").text_content())
    page.evaluate(
        """() => document.querySelector('[data-testid="loop-bundle-import-form"]')
          .dispatchEvent(new Event("submit", {bubbles: true, cancelable: true}))"""
    )
    assert "Direct path is selected" in str(page.locator("#bundle-import-error").text_content())
    page.get_by_test_id("manual-direct-handoff-clear").click()
    page.get_by_test_id("manual-direct-handoff-bridge").wait_for(state="hidden", timeout=10_000)
    assert page.evaluate(
        """() => ({
          saveDisabled: document.querySelector('#save-loop-button')?.disabled,
          importDisabled: document.querySelector('[data-testid="bundle-import-submit-button"]')?.disabled,
          manualBlocked: document.querySelector('[data-testid="loop-create-form"]')?.dataset.directPathBlocked,
          importBlocked: document.querySelector('[data-testid="loop-bundle-import-form"]')?.dataset.directPathBlocked,
          chatHref: document.querySelector('[data-testid="alignment-path-chat"]')?.hasAttribute("href"),
          importHref: document.querySelector('[data-testid="alignment-path-import"]')?.hasAttribute("href"),
          manualHref: document.querySelector('[data-testid="alignment-path-manual"]')?.hasAttribute("href"),
          activeId: document.activeElement?.id || "",
        })"""
    ) == {
        "saveDisabled": False,
        "importDisabled": False,
        "manualBlocked": "false",
        "importBlocked": "false",
        "chatHref": True,
        "importHref": True,
        "manualHref": True,
        "activeId": "workdir-input",
    }


def test_browser_tutorial_fit_review_handoff_reaches_tools_session_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "handoff target project"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())
    storage_key = "loopora:tutorial-fit-handoff:v1"
    inputs = _tutorial_fit_review_inputs()
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    source_entry = agent_adapter_command_prefix.current_copyable_loopora_cli_entry()

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(
            f"{base_url}/tutorial?alignment_workdir={quote(resolved_workdir, safe='')}#tutorial-decision-tree-panel",
            wait_until="domcontentloaded",
        )
        page.get_by_test_id("tutorial-fit-task-review").wait_for(state="visible", timeout=10_000)

        page.get_by_test_id("tutorial-fit-task-input").fill(inputs["task"])
        partial_command = page.get_by_test_id("tutorial-fit-completion-command").input_value()
        assert partial_command.startswith(f"{source_entry} fit --workdir '")
        assert resolved_workdir in partial_command
        assert " --task " in partial_command
        assert "<how this could look done while core risk remains unproven>" in partial_command
        assert "<tests, probes, artifacts, browser/API proof, or reviewer-readable evidence>" in partial_command
        assert "<scope, rollback, residual-risk, or fail-closed rules>" in partial_command

        draft = _fill_tutorial_fit_review(page, inputs)
        _assert_tutorial_fit_completion_command_cleared_for_complete(page)
        assert page.evaluate("(key) => sessionStorage.getItem(key)", storage_key) is None

        page.get_by_test_id("tutorial-fit-task-use-tools").click()
        _assert_tools_received_session_only_fit_handoff(
            page,
            storage_key=storage_key,
            inputs=inputs,
            draft=draft,
            workdir=resolved_workdir,
        )
        _install_and_assert_fit_handoff_merges_into_adapter(page, draft=draft, storage_key=storage_key)
        _assert_mobile_fit_handoff_stays_merged(
            page,
            workdir=resolved_workdir,
            storage_key=storage_key,
            inputs=inputs,
            draft=draft,
        )


def test_browser_tutorial_fit_command_tracks_global_workdir_change(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_workdir = tmp_path / "fit command source"
    target_workdir = tmp_path / "fit command target"
    source_workdir.mkdir()
    target_workdir.mkdir()
    resolved_source = str(source_workdir.resolve())
    resolved_target = str(target_workdir.resolve())

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/fit-guide?workdir={quote(resolved_source, safe='')}#tutorial-decision-tree-panel", wait_until="domcontentloaded")
        page.get_by_test_id("tutorial-fit-task-review").wait_for(state="visible", timeout=10_000)

        page.get_by_test_id("tutorial-fit-task-input").fill("Retarget visible Fit Guide commands")
        initial_command = page.get_by_test_id("tutorial-fit-completion-command").input_value()
        assert f"--workdir '{resolved_source}'" in initial_command
        assert resolved_target not in initial_command

        page.evaluate(
            """target => window.LooporaUI.syncWorkdirContext(target, {syncUrl: true, urlParam: "workdir"})""",
            resolved_target,
        )
        page.wait_for_function(
            """target => document.querySelector('[data-testid="tutorial-fit-completion-command"]')?.value.includes(`--workdir '${target}'`)
              && document.querySelector('[data-testid="tutorial-fit-task-review"]')?.dataset.currentWorkdir === target
              && new URL(location.href).searchParams.get("workdir") === target""",
            arg=resolved_target,
            timeout=10_000,
        )
        retargeted_state = page.evaluate(
            """() => ({
              command: document.querySelector('[data-testid="tutorial-fit-completion-command"]')?.value || "",
              global: document.querySelector('[data-testid="global-workdir-context"] code')?.textContent || "",
              toolsHrefWorkdir: new URL(document.querySelector('[data-testid="tutorial-fit-task-use-tools"]').href).searchParams.get("workdir"),
              webHrefWorkdir: new URL(document.querySelector('[data-testid="tutorial-fit-task-use-web"]').href).searchParams.get("workdir"),
              actionWebHrefWorkdir: new URL(document.querySelector('[data-testid="tutorial-web-compose-link"]').href).searchParams.get("workdir"),
              actionToolsHrefWorkdir: new URL(document.querySelector('[data-testid="tutorial-agent-entry-link"]').href).searchParams.get("workdir"),
              manualHrefWorkdir: new URL(document.querySelector('[data-testid="tutorial-manual-compose-link"]').href).searchParams.get("workdir"),
              flowsHrefWorkdir: new URL(document.querySelector('[data-testid="tutorial-workflow-examples-link"]').href).searchParams.get("workdir"),
            })"""
        )
        assert f"--workdir '{resolved_target}'" in retargeted_state["command"]
        assert resolved_source not in retargeted_state["command"]
        assert retargeted_state["global"] == resolved_target
        for href_key in (
            "toolsHrefWorkdir",
            "webHrefWorkdir",
            "actionWebHrefWorkdir",
            "actionToolsHrefWorkdir",
            "manualHrefWorkdir",
            "flowsHrefWorkdir",
        ):
            assert retargeted_state[href_key] == resolved_target


def test_browser_tutorial_direct_path_requires_reviewable_input(tmp_path: Path) -> None:
    service, cli_entry = _service(tmp_path), agent_adapter_command_prefix.current_copyable_loopora_cli_entry()
    source_workdir = tmp_path / "direct source project"
    target_workdir = tmp_path / "direct target project"
    source_workdir.mkdir()
    target_workdir.mkdir()
    resolved_source = str(source_workdir.resolve())
    resolved_target = str(target_workdir.resolve())
    storage_key = "loopora:tutorial-fit-handoff:v1"

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/tutorial?workdir={quote(resolved_source, safe='')}#tutorial-decision-tree-panel", wait_until="domcontentloaded")
        page.get_by_test_id("tutorial-fit-task-review").wait_for(state="visible", timeout=10_000)

        page.get_by_test_id("tutorial-fit-prefer-direct-input").check()
        command, status = (
            page.get_by_test_id("tutorial-fit-completion-command").input_value(),
            page.get_by_test_id("tutorial-fit-task-status").text_content(),
        )
        assert page.get_by_test_id("tutorial-fit-task-draft").input_value() == ""
        assert page.get_by_test_id("tutorial-fit-task-copy").is_disabled()
        assert page.get_by_test_id("tutorial-fit-completion-command-copy").is_enabled()
        assert "--prefer-direct" in command
        assert f"--workdir '{resolved_source}'" in command
        assert "--task '<task goal>'" not in command
        assert "--direct-path '<what direct Agent, /goal, hard checks, or project process is enough>'" in command
        assert "Add a direct-path reason" in str(status)
        _assert_tutorial_direct_routes_blocked(page)
        blocked_handoff = page.evaluate(
            """() => {
              window.__looporaTutorialBlockedFeedback = [];
              window.LooporaUI.showAppFeedback = (message, kind) => {
                window.__looporaTutorialBlockedFeedback.push({message, kind, path: location.pathname});
              };
              for (const testid of ["tutorial-fit-task-use-tools", "tutorial-fit-task-use-web", "tutorial-web-compose-link", "tutorial-agent-entry-link", "tutorial-manual-compose-link", "nav-compose-link", "nav-tools-link"]) {
                document.querySelector(`[data-testid="${testid}"]`)
                  ?.dispatchEvent(new MouseEvent("click", {bubbles: true, cancelable: true}));
              }
              return {
                path: location.pathname,
                feedback: window.__looporaTutorialBlockedFeedback,
              };
            }"""
        )
        assert blocked_handoff["path"] == "/fit-guide"
        assert len(blocked_handoff["feedback"]) == 7
        assert all(item["kind"] == "warning" and "Direct path is selected" in item["message"] for item in blocked_handoff["feedback"])
        assert page.evaluate("(key) => sessionStorage.getItem(key)", storage_key) is None

        direct_task = "One small README typo"
        direct_reason = "One existing smoke test and one human review fully judge this task."
        page.get_by_test_id("tutorial-fit-task-input").fill(direct_task)
        assert (
            page.get_by_test_id("tutorial-fit-completion-command").input_value(),
            "Add a direct-path reason" in str(page.get_by_test_id("tutorial-fit-task-status").text_content()),
            page.evaluate("(key) => sessionStorage.getItem(key)", storage_key),
        ) == (
            f"{cli_entry} fit --workdir '{resolved_source}' --prefer-direct --task '{direct_task}' --direct-path '<what direct Agent, /goal, hard checks, or project process is enough>'",
            True,
            None,
        )
        page.get_by_test_id("tutorial-fit-direct-path-check-input").fill(direct_reason)
        command = page.get_by_test_id("tutorial-fit-completion-command").input_value()
        assert command == f"{cli_entry} fit --workdir '{resolved_source}' --prefer-direct --task '{direct_task}' --direct-path '{direct_reason}'"
        page.evaluate(
            """() => {
              window.__looporaCopiedDirectDecision = "";
              window.LooporaUI.writeTextToClipboard = async (value) => {
                window.__looporaCopiedDirectDecision = value;
              };
            }"""
        )
        page.get_by_test_id("tutorial-fit-completion-command-copy").click()
        assert page.evaluate("() => window.__looporaCopiedDirectDecision") == command
        stored = page.evaluate("(key) => JSON.parse(sessionStorage.getItem(key))", storage_key)
        assert stored["fit_decision"] == "prefer_direct_path"
        assert stored["setup_command_blockers"] == ["prefer_direct_path"]
        assert stored["source_workdir"] == resolved_source
        assert stored["inputs"] == {"task": direct_task, "direct_path_check": direct_reason}
        assert stored["primary_first_task_message"] == ""

        page.goto(f"{base_url}/same-agent?workdir={quote(resolved_target, safe='')}", wait_until="domcontentloaded")
        page.get_by_test_id("agent-adapter-draft-handoff").wait_for(state="visible", timeout=10_000)
        _assert_tools_direct_handoff_blocks_same_agent_setup(
            page,
            command=command,
            source_workdir=resolved_source,
            target_workdir=resolved_target,
        )

        _assert_create_choice_direct_handoff_blocks_loopora_starts(
            page,
            base_url=base_url,
            workdir=resolved_target,
            source_workdir=resolved_source,
            command=command,
        )

        _assert_alignment_direct_handoff_blocks_web_compose(
            page,
            base_url=base_url,
            workdir=resolved_target,
            command=command,
            source_workdir=resolved_source,
        )
        _assert_manual_direct_handoff_blocks_import_and_manual(
            page,
            base_url=base_url,
            workdir=resolved_target,
            source_workdir=resolved_source,
            command=command,
        )


def test_browser_alignment_direct_path_reason_only_handoff_blocks_web_conversation(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "direct reason only web target"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())
    storage_key = "loopora:tutorial-fit-handoff:v1"
    direct_reason = "A focused smoke test and reviewer pass fully judge this README typo."
    command = f"loopora fit --workdir '{resolved_workdir}' --prefer-direct --direct-path '{direct_reason}'"
    payload = {
        "schema_version": 1,
        "source": "tutorial_fit_review",
        "source_workdir": resolved_workdir,
        "inputs": {"direct_path_check": direct_reason},
        "prefer_direct_path": True,
        "fit_decision": "prefer_direct_path",
        "setup_command_blockers": ["prefer_direct_path"],
        "route_preview_blockers": ["prefer_direct_path"],
        "primary_first_task_message": "",
        "draft_first_task_message": "",
        "direct_decision_command": command,
    }

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/tutorial?workdir={quote(resolved_workdir, safe='')}", wait_until="domcontentloaded")
        page.evaluate(
            """([key, value]) => window.sessionStorage.setItem(key, JSON.stringify(value))""",
            [storage_key, payload],
        )

        _assert_alignment_direct_handoff_blocks_web_compose(
            page,
            base_url=base_url,
            workdir=resolved_workdir,
            command=command,
        )
        visible_context = page.evaluate(
            r"""() => ({
              summary: (document.querySelector('[data-testid="alignment-tutorial-handoff-inputs"]')?.textContent || "").replace(/\s+/g, " ").trim(),
              meta: (document.querySelector('[data-testid="alignment-tutorial-handoff-meta"]')?.textContent || "").replace(/\s+/g, " ").trim(),
            })"""
        )
        assert "Direct-path decision" in visible_context["summary"]
        assert direct_reason in visible_context["summary"]
        assert "Missing" not in visible_context["meta"]


def test_browser_alignment_tutorial_handoff_clear_restores_task_focus(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "alignment clear handoff target"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())
    storage_key = "loopora:tutorial-fit-handoff:v1"
    command = f"loopora fit --workdir '{resolved_workdir}' --prefer-direct --direct-path 'Direct review is enough.'"
    payload = {
        "schema_version": 1,
        "source": "tutorial_fit_review",
        "source_workdir": resolved_workdir,
        "inputs": {"task": "Keep direct path recoverable.", "direct_path_check": "Direct review is enough."},
        "missing_first_task_input_ids": [],
        "ready_for_loopora_plan_message": False,
        "prefer_direct_path": True,
        "fit_decision": "prefer_direct_path",
        "review_completion_command": command,
        "direct_decision_command": command,
        "draft_first_task_message": "",
        "saved_at": "2026-01-01T00:00:00.000Z",
    }

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/tutorial", wait_until="domcontentloaded")
        page.evaluate(
            """([key, payload]) => sessionStorage.setItem(key, JSON.stringify(payload))""",
            [storage_key, payload],
        )

        page.goto(
            f"{base_url}/loops/new/bundle?alignment_workdir={quote(resolved_workdir, safe='')}",
            wait_until="domcontentloaded",
        )
        page.get_by_test_id("alignment-tutorial-handoff-bridge").wait_for(state="visible", timeout=10_000)
        page.get_by_test_id("alignment-tutorial-handoff-clear").click()
        page.wait_for_function(
            """(key) => document.querySelector('[data-testid="alignment-tutorial-handoff-bridge"]')?.hidden
              && sessionStorage.getItem(key) === null
              && document.activeElement === document.querySelector('[data-testid="alignment-task-goal-input"]')
              && !document.querySelector('[data-testid="alignment-send-button"]')?.disabled""",
            arg=storage_key,
            timeout=10_000,
        )


def test_browser_tutorial_fit_review_handoff_prefills_web_compose(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "web handoff target project"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())
    storage_key = "loopora:tutorial-fit-handoff:v1"
    inputs = _tutorial_fit_review_inputs()

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(
            f"{base_url}/tutorial?alignment_workdir={quote(resolved_workdir, safe='')}#tutorial-decision-tree-panel",
            wait_until="domcontentloaded",
        )
        page.get_by_test_id("tutorial-fit-task-review").wait_for(state="visible", timeout=10_000)
        draft = _fill_tutorial_fit_review(page, inputs)

        page.get_by_test_id("tutorial-web-compose-link").click()
        page.wait_for_function("() => location.pathname === '/loops/new'", timeout=10_000)
        page.get_by_test_id("loop-create-tutorial-handoff").wait_for(state="visible", timeout=10_000)
        assert inputs["task"] in page.get_by_test_id("loop-create-tutorial-handoff").text_content()
        _assert_create_choice_reviewed_phase(page, task=inputs["task"], judgment_count=len(inputs))

        page.get_by_test_id("loop-create-tutorial-handoff-finish-link").click()
        page.wait_for_function("() => location.pathname === '/fit-guide'", timeout=10_000)
        page.get_by_test_id("tutorial-fit-task-review").wait_for(state="visible", timeout=10_000)
        assert page.get_by_test_id("tutorial-fit-task-input").input_value() == inputs["task"]
        assert page.get_by_test_id("tutorial-fit-loopora-fit-reason-input").input_value() == inputs["loopora_fit_reason"]
        assert page.get_by_test_id("tutorial-fit-required-evidence-input").input_value() == inputs["required_evidence"]

        page.get_by_test_id("tutorial-web-compose-link").click()
        page.wait_for_function("() => location.pathname === '/loops/new'", timeout=10_000)
        page.get_by_test_id("loop-create-tutorial-handoff").wait_for(state="visible", timeout=10_000)
        page.get_by_test_id("loop-create-tutorial-handoff-web-link").click()
        page.wait_for_function("() => location.pathname === '/loops/new/bundle'", timeout=10_000)
        page.get_by_test_id("alignment-start-form").wait_for(state="visible", timeout=10_000)
        nav = page.evaluate(
            """() => ({
              pathname: location.pathname,
              workdir: new URL(location.href).searchParams.get("workdir") || new URL(location.href).searchParams.get("alignment_workdir"),
              paramNames: Array.from(new URL(location.href).searchParams.keys()),
            })"""
        )
        assert nav == {"pathname": "/loops/new/bundle", "workdir": resolved_workdir, "paramNames": ["alignment_workdir"]}
        assert page.get_by_test_id("alignment-task-goal-input").input_value() == inputs["task"]
        assert page.get_by_test_id("alignment-loopora-fit-reason-input").input_value() == inputs["loopora_fit_reason"]
        assert page.get_by_test_id("alignment-direct-path-check-input").input_value() == inputs["direct_path_check"]
        assert page.get_by_test_id("alignment-fake-done-risk-input").input_value() == inputs["fake_done_risks"]
        assert page.get_by_test_id("alignment-required-evidence-input").input_value() == inputs["required_evidence"]
        assert page.get_by_test_id("alignment-judgment-tradeoffs-input").input_value() == inputs["judgment_tradeoffs"]
        assert page.get_by_test_id("alignment-message-input").input_value() == ""
        _assert_alignment_fit_entry_phase(page, phase="reviewed", known_count=len(inputs), missing_count=0, mobile=True)
        stored = page.evaluate("(key) => JSON.parse(sessionStorage.getItem(key))", storage_key)
        assert stored["draft_first_task_message"] == draft
        assert stored["source_workdir"] == resolved_workdir
        assert stored["inputs"] == inputs

        page.get_by_test_id("alignment-workdir").evaluate(
            """(element) => {
              element.value = "";
              element.dispatchEvent(new Event("input", {bubbles: true}));
              element.dispatchEvent(new Event("change", {bubbles: true}));
            }"""
        )
        page.wait_for_function(
            """() => !new URL(location.href).searchParams.get("alignment_workdir")
              && !new URL(location.href).searchParams.get("workdir")
              && document.querySelector('[data-testid="global-workdir-context"]')?.hidden""",
            timeout=10_000,
        )
        cleared_context = page.evaluate(
            """() => {
              const param = (testid, name) => new URL(
                document.querySelector(`[data-testid="${testid}"]`).href
              ).searchParams.get(name);
              return {
                currentWorkdir: new URL(location.href).searchParams.get("workdir"),
                currentAlignmentWorkdir: new URL(location.href).searchParams.get("alignment_workdir"),
                navCompose: param("nav-compose-link", "workdir"),
                chat: param("alignment-path-chat", "alignment_workdir"),
                importPath: param("alignment-path-import", "workdir"),
                manual: param("alignment-path-manual", "workdir"),
              };
            }"""
        )
        assert cleared_context == {
            "currentWorkdir": None,
            "currentAlignmentWorkdir": None,
            "navCompose": None,
            "chat": None,
            "importPath": None,
            "manual": None,
        }
        _assert_no_horizontal_overflow(page)


def test_browser_tutorial_fit_review_handoff_sets_context_on_bare_web_compose(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "bare web handoff project"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())
    storage_key = "loopora:tutorial-fit-handoff:v1"
    inputs = _tutorial_fit_review_inputs()
    draft = (
        "/loopora-plan\n\nLoopora fit: "
        f"{inputs['loopora_fit_reason']}; Goal: {inputs['task']}; Fake-done risks: {inputs['fake_done_risks']}; "
        f"Required evidence: {inputs['required_evidence']}; "
        f"Judgment tradeoffs: {inputs['judgment_tradeoffs']}."
    )

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/tutorial", wait_until="domcontentloaded")
        _store_tutorial_fit_handoff(page, storage_key=storage_key, inputs=inputs, draft=draft, workdir=resolved_workdir)

        page.goto(f"{base_url}/loops/new/bundle", wait_until="domcontentloaded")
        page.wait_for_function(
            """([workdir, task]) => new URL(location.href).searchParams.get('workdir') === workdir
              && document.querySelector('[data-testid="global-workdir-context"] code')?.textContent === workdir
              && document.querySelector('[data-testid="alignment-task-goal-input"]')?.value === task""",
            arg=[resolved_workdir, inputs["task"]],
            timeout=10_000,
        )
        link_context = page.evaluate(
            """() => {
              const param = (testid, name) => new URL(
                document.querySelector(`[data-testid="${testid}"]`).href
              ).searchParams.get(name);
              return {
                navCompose: param("nav-compose-link", "workdir"),
                chat: param("alignment-path-chat", "alignment_workdir"),
                importPath: param("alignment-path-import", "workdir"),
                manual: param("alignment-path-manual", "workdir"),
              };
            }"""
        )
        assert link_context == {
            "navCompose": resolved_workdir,
            "chat": resolved_workdir,
            "importPath": resolved_workdir,
            "manual": resolved_workdir,
        }
        _assert_no_horizontal_overflow(page)


def test_browser_web_composer_workdir_edits_sync_visible_context_and_peer_links(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "web composer target with spaces"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(f"{base_url}/loops/new/bundle", wait_until="domcontentloaded")
        context = page.get_by_test_id("global-workdir-context")
        assert context.is_hidden()

        page.get_by_test_id("alignment-workdir-chip").click()
        workdir_input = page.get_by_test_id("alignment-workdir")
        workdir_input.wait_for(state="visible", timeout=10_000)
        workdir_input.fill(resolved_workdir)

        page.wait_for_function(
            """(workdir) => {
              const context = document.querySelector('[data-testid="global-workdir-context"]');
              return document.activeElement === document.querySelector('[data-testid="alignment-workdir"]')
                && !context.hidden
                && context.querySelector("code")?.textContent === workdir;
            }""",
            arg=resolved_workdir,
            timeout=10_000,
        )
        link_context = page.evaluate(
            """() => {
              const param = (testid, name) => new URL(
                document.querySelector(`[data-testid="${testid}"]`).href
              ).searchParams.get(name);
              const historyList = document.querySelector('[data-testid="alignment-history-list"]');
              const historyStart = new URL(historyList.dataset.historyEmptyStartHref, window.location.origin);
              return {
                currentUrl: new URL(window.location.href).searchParams.get("workdir"),
                navCompose: param("nav-compose-link", "workdir"),
                chat: param("alignment-path-chat", "alignment_workdir"),
                importPath: param("alignment-path-import", "workdir"),
                manual: param("alignment-path-manual", "workdir"),
                historyEmptyStart: historyStart.searchParams.get("alignment_workdir"),
                historyDatasetDeclaration: historyList.dataset.workdirContextDatasetUrls,
              };
            }"""
        )
        assert link_context == {
            "currentUrl": resolved_workdir,
            "navCompose": resolved_workdir,
            "chat": resolved_workdir,
            "importPath": resolved_workdir,
            "manual": resolved_workdir,
            "historyEmptyStart": resolved_workdir,
            "historyDatasetDeclaration": "historyEmptyStartHref:alignment_workdir",
        }


def test_browser_tutorial_fit_review_handoff_stays_visible_for_web_target_mismatch(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_workdir = tmp_path / "web source project"
    target_workdir = tmp_path / "web different target"
    source_workdir.mkdir()
    target_workdir.mkdir()
    resolved_source = str(source_workdir.resolve())
    resolved_target = str(target_workdir.resolve())
    storage_key = "loopora:tutorial-fit-handoff:v1"
    inputs = _tutorial_fit_review_inputs()
    draft = (
        "/loopora-plan\n\nLoopora fit: "
        f"{inputs['loopora_fit_reason']}; Goal: {inputs['task']}; Fake-done risks: {inputs['fake_done_risks']}; "
        f"Required evidence: {inputs['required_evidence']}; "
        f"Judgment tradeoffs: {inputs['judgment_tradeoffs']}."
    )

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/tutorial", wait_until="domcontentloaded")
        _store_tutorial_fit_handoff(
            page,
            storage_key=storage_key,
            inputs=inputs,
            draft=draft,
            workdir=resolved_source,
        )

        page.goto(f"{base_url}/loops/new?workdir={quote(resolved_target, safe='')}", wait_until="domcontentloaded")
        page.get_by_test_id("loop-create-tutorial-handoff").wait_for(state="visible", timeout=10_000)
        choice_disabled_state = page.evaluate(
            """() => {
              const state = (testid) => {
                const link = document.querySelector(`[data-testid="${testid}"]`);
                return {
                  ariaDisabled: link?.getAttribute("aria-disabled"),
                  classDisabled: link?.classList.contains("is-disabled"),
                  pointerEvents: link ? getComputedStyle(link).pointerEvents : "",
                  tabIndex: link?.getAttribute("tabindex"),
                };
              };
              return {
                bridge: state("loop-create-tutorial-handoff-web-link"),
                primary: state("loop-create-bundle-link"),
                finishVisible: Boolean(document.querySelector('[data-testid="loop-create-tutorial-handoff-finish-link"]')),
                sourceVisible: !document.querySelector('[data-testid="loop-create-tutorial-handoff-use-source"]')?.hidden,
                toolsVisible: Boolean(document.querySelector('[data-testid="loop-create-tutorial-handoff-tools-link"]')),
                fitPromptVisible: !document.querySelector('[data-testid="loop-create-fit-review"]')?.hidden,
                reviewOpen: document.querySelector('[data-testid="loop-create-tutorial-handoff-review"]')?.open,
              };
            }"""
        )
        assert choice_disabled_state == {
            "bridge": {
                "ariaDisabled": "false",
                "classDisabled": False,
                "pointerEvents": "auto",
                "tabIndex": None,
            },
            "primary": {
                "ariaDisabled": "false",
                "classDisabled": False,
                "pointerEvents": "auto",
                "tabIndex": None,
            },
            "finishVisible": True,
            "sourceVisible": True,
            "toolsVisible": True,
            "fitPromptVisible": True,
            "reviewOpen": True,
        }
        page.get_by_test_id("loop-create-bundle-link").click()
        page.wait_for_function("() => location.pathname === '/loops/new/bundle'", timeout=10_000)
        page.get_by_test_id("alignment-tutorial-handoff-bridge").wait_for(state="visible", timeout=10_000)
        meta = page.get_by_test_id("alignment-tutorial-handoff-meta").text_content()
        assert resolved_source in meta
        assert resolved_target in meta
        assert page.get_by_test_id("alignment-tutorial-handoff-bridge").evaluate("node => node.classList.contains('is-warning')")
        copy_draft = page.get_by_test_id("alignment-tutorial-handoff-copy-draft")
        assert copy_draft.get_attribute("data-tutorial-handoff-copy-draft") == draft
        assert page.get_by_test_id("alignment-task-goal-input").input_value() == ""

        page.evaluate(
            """() => {
              window.__looporaCopiedText = null;
              Object.defineProperty(navigator, "clipboard", {
                value: {writeText: async (text) => { window.__looporaCopiedText = text; }},
                configurable: true,
              });
            }"""
        )
        copy_draft.click()
        page.wait_for_function("() => window.__looporaCopiedText !== null", timeout=10_000)
        assert page.evaluate("() => window.__looporaCopiedText") == draft

        assert page.get_by_test_id("alignment-tutorial-handoff-prefill").count() == 0
        page.get_by_test_id("alignment-tutorial-handoff-use-source").click()
        page.wait_for_function(
            """source => document.querySelector('[data-testid="alignment-workdir"]')?.value === source
              && document.querySelector('[data-testid="alignment-task-goal-input"]')?.value === ''
              && (new URL(location.href).searchParams.get('workdir') === source
                || new URL(location.href).searchParams.get('alignment_workdir') === source)
              && document.querySelector('[data-testid="alignment-tutorial-handoff-prefill"]')""",
            arg=resolved_source,
            timeout=10_000,
        )
        switched_context = page.evaluate(
            """() => {
              const param = (testid, name) => new URL(
                document.querySelector(`[data-testid="${testid}"]`).href
              ).searchParams.get(name);
              return {
                global: document.querySelector('[data-testid="global-workdir-context"] code')?.textContent,
                navCompose: param("nav-compose-link", "workdir"),
                chat: param("alignment-path-chat", "alignment_workdir"),
                manual: param("alignment-path-manual", "workdir"),
              };
            }"""
        )
        assert switched_context == {
            "global": resolved_source,
            "navCompose": resolved_source,
            "chat": resolved_source,
            "manual": resolved_source,
        }
        page.get_by_test_id("alignment-tutorial-handoff-prefill").click()
        page.wait_for_function(
            """([source, task]) => document.querySelector('[data-testid="alignment-workdir"]')?.value === source
              && document.querySelector('[data-testid="alignment-task-goal-input"]')?.value === task
              && document.querySelector('[data-testid="alignment-tutorial-handoff-bridge"]')?.hidden""",
            arg=[resolved_source, inputs["task"]],
            timeout=10_000,
        )
        assert page.get_by_test_id("alignment-fake-done-risk-input").input_value() == inputs["fake_done_risks"]
        assert page.get_by_test_id("alignment-direct-path-check-input").input_value() == inputs["direct_path_check"]
        assert page.get_by_test_id("alignment-required-evidence-input").input_value() == inputs["required_evidence"]
        assert page.get_by_test_id("alignment-judgment-tradeoffs-input").input_value() == inputs["judgment_tradeoffs"]
        _assert_no_horizontal_overflow(page)


def test_browser_tutorial_fit_review_handoff_accepts_tmp_alias_for_web_target(tmp_path: Path) -> None:
    service = _service(tmp_path)
    storage_key = "loopora:tutorial-fit-handoff:v1"
    inputs = _tutorial_fit_review_inputs()
    source_workdir = "/private/tmp/loopora-alias-project"
    target_workdir = "/tmp/loopora-alias-project"
    draft = (
        "/loopora-plan\n\nLoopora fit: "
        f"{inputs['loopora_fit_reason']}; Goal: {inputs['task']}; Fake-done risks: {inputs['fake_done_risks']}; "
        f"Required evidence: {inputs['required_evidence']}; "
        f"Judgment tradeoffs: {inputs['judgment_tradeoffs']}."
    )

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/tutorial", wait_until="domcontentloaded")
        _store_tutorial_fit_handoff(
            page,
            storage_key=storage_key,
            inputs=inputs,
            draft=draft,
            workdir=source_workdir,
        )

        page.goto(f"{base_url}/loops/new/bundle?workdir={quote(target_workdir, safe='')}", wait_until="domcontentloaded")
        page.wait_for_function(
            """([target, task]) => document.querySelector('[data-testid="alignment-workdir"]')?.value === target
              && document.querySelector('[data-testid="alignment-task-goal-input"]')?.value === task
              && document.querySelector('[data-testid="alignment-tutorial-handoff-bridge"]')?.hidden""",
            arg=[target_workdir, inputs["task"]],
            timeout=10_000,
        )
        assert page.get_by_test_id("alignment-fake-done-risk-input").input_value() == inputs["fake_done_risks"]
        assert page.get_by_test_id("alignment-direct-path-check-input").input_value() == inputs["direct_path_check"]
        assert page.get_by_test_id("alignment-required-evidence-input").input_value() == inputs["required_evidence"]
        assert page.get_by_test_id("alignment-judgment-tradeoffs-input").input_value() == inputs["judgment_tradeoffs"]


def _assert_incomplete_fit_review_blocks_same_agent_setup(
    page,
    *,
    storage_key: str,
    draft: str,
    completion_command: str,
) -> None:
    page.get_by_test_id("tutorial-fit-task-use-tools").click()
    page.wait_for_function("() => location.pathname === '/same-agent'", timeout=10_000)
    stored = page.evaluate("(key) => JSON.parse(sessionStorage.getItem(key))", storage_key)
    assert stored["ready_for_loopora_plan_message"] is False
    assert stored["primary_first_task_message_state"]["completed_review"] is False
    assert stored["primary_first_task_message_state"]["status"] == "preview_only_until_review_inputs_complete"
    assert stored["missing_first_task_input_ids"] == [
        "loopora_fit_reason",
        "fake_done_risks",
        "required_evidence",
        "judgment_tradeoffs",
    ]
    assert stored["review_completion_command"] == completion_command

    page.wait_for_function(
        """() => Array.from(document.querySelectorAll('[data-agent-adapter-status]'))
          .some((node) => node.dataset.agentAdapterState && node.dataset.agentAdapterState !== 'refreshing')""",
        timeout=10_000,
    )
    page.get_by_test_id("agent-adapter-draft-handoff").wait_for(state="visible", timeout=10_000)
    assert "is-warning" in page.get_by_test_id("agent-adapter-draft-handoff").get_attribute("class")
    assert page.get_by_test_id("agent-draft-handoff-copy").count() == 0
    copy_completion = page.get_by_test_id("agent-draft-handoff-copy-completion")
    assert copy_completion.get_attribute("data-agent-draft-handoff-copy-completion") == completion_command
    missing_text = page.get_by_test_id("agent-draft-handoff-missing-inputs").text_content()
    assert all(label in missing_text for label in ("Fake done", "Fit reason", "Evidence", "Tradeoffs"))

    install_button = page.get_by_test_id("agent-adapter-install-codex")
    uninstall_button = page.get_by_test_id("agent-adapter-uninstall-codex")
    assert install_button.is_disabled()
    assert install_button.get_attribute("data-agent-adapter-fit-review-disabled") == "true"
    assert "Fit Review is incomplete" in str(install_button.get_attribute("title"))
    assert uninstall_button.is_enabled()
    assert uninstall_button.get_attribute("data-agent-adapter-fit-review-disabled") is None
    assert page.get_by_test_id("agent-readiness-title").text_content() == "Finish the current task's Fit Review"
    assert page.get_by_test_id("agent-readiness-pill").text_content() == "Review incomplete"
    assert "old entry may still be uninstalled" in page.get_by_test_id("agent-readiness-detail").text_content()
    assert page.get_by_test_id("agent-readiness-copy-plan").count() == 0
    assert page.get_by_test_id("agent-readiness-copy-run").count() == 0
    assert page.get_by_test_id("agent-readiness-copy-readiness").count() == 1
    assert page.get_by_test_id("agent-adapter-handoff").is_hidden()
    assert page.get_by_test_id("agent-adapter-copy-gen").count() == 0
    assert page.get_by_test_id("agent-adapter-copy-loop").count() == 0
    first_task_value = page.evaluate(
        """() => document
          .querySelector('[data-testid="agent-adapter-copy-first-task-example"]')
          ?.getAttribute("data-agent-adapter-command-copy") || ''"""
    )
    assert first_task_value != draft

    mutation_calls: list[str] = []

    def record_install_mutation(route) -> None:
        mutation_calls.append(route.request.url)
        route.fulfill(status=418, content_type="application/json", body='{"error":"unexpected mutation"}')

    page.route("**/api/agent-adapters/codex/install", record_install_mutation)
    page.evaluate(
        """() => document.querySelector('[data-testid="agent-adapter-install-codex"]')
          .dispatchEvent(new MouseEvent("click", {bubbles: true, cancelable: true}))"""
    )
    page.wait_for_timeout(100)
    page.unroute("**/api/agent-adapters/codex/install", record_install_mutation)
    assert mutation_calls == []
    assert "Fit Review is incomplete" in str(page.locator("#agent-adapter-status").text_content())

    page.evaluate(
        """() => {
          window.__looporaCopiedText = null;
          Object.defineProperty(navigator, "clipboard", {
            value: {writeText: async (text) => { window.__looporaCopiedText = text; }},
            configurable: true,
          });
        }"""
    )
    copy_completion.click()
    page.wait_for_function("() => window.__looporaCopiedText !== null", timeout=10_000)
    assert page.evaluate("() => window.__looporaCopiedText") == completion_command


def test_browser_incomplete_tutorial_fit_review_keeps_agent_recovery_and_allows_web_clarification(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "incomplete handoff project"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())
    storage_key = "loopora:tutorial-fit-handoff:v1"
    inputs = _tutorial_fit_review_inputs()
    service.install_agent_adapter("codex", workdir=workdir)

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        _open_generated_incomplete_fit_review(
            page,
            base_url=base_url,
            workdir=workdir,
            task=inputs["task"],
        )
        draft = page.get_by_test_id("tutorial-fit-task-draft").input_value()
        completion_command = page.get_by_test_id("tutorial-fit-completion-command").input_value()
        assert "<how this could look done while core risk remains unproven>" in draft
        assert "<how this could look done while core risk remains unproven>" in completion_command
        assert f"--workdir '{resolved_workdir}'" in completion_command
        assert page.get_by_test_id("tutorial-fit-task-copy").is_disabled()
        assert page.get_by_test_id("tutorial-fit-completion-command-copy").is_enabled()
        _assert_incomplete_fit_review_blocks_same_agent_setup(
            page,
            storage_key=storage_key,
            draft=draft,
            completion_command=completion_command,
        )

        page.goto(f"{base_url}/loops/new?workdir={quote(resolved_workdir, safe='')}", wait_until="domcontentloaded")
        page.get_by_test_id("loop-create-tutorial-handoff").wait_for(state="visible", timeout=10_000)
        assert page.get_by_test_id("loop-create-bundle-link").get_attribute("aria-disabled") == "false"
        assert "can continue in conversation" in page.get_by_test_id("loop-create-tutorial-handoff").text_content()

        page.get_by_test_id("loop-create-bundle-link").click()
        page.wait_for_function(
            """task => location.pathname === '/loops/new/bundle'
              && document.querySelector('[data-testid="alignment-task-goal-input"]')?.value === task
              && document.querySelector('[data-testid="alignment-tutorial-handoff-bridge"]')?.hidden""",
            arg=inputs["task"],
            timeout=10_000,
        )
        assert page.get_by_test_id("alignment-loopora-fit-reason-input").input_value() == ""
        assert page.get_by_test_id("alignment-send-button").is_enabled()
        _assert_alignment_fit_entry_phase(page, phase="partial", known_count=1, missing_count=4)


def test_browser_tutorial_fit_review_draft_follows_current_language(tmp_path: Path) -> None:
    service = _service(tmp_path)
    cli_entry = agent_adapter_command_prefix.current_copyable_loopora_cli_entry()

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/tutorial#tutorial-decision-tree-panel", wait_until="domcontentloaded")
        page.get_by_test_id("tutorial-fit-task-review").wait_for(state="visible", timeout=10_000)

        page.evaluate("() => window.LooporaUI.setLocale('zh')")
        page.get_by_test_id("tutorial-fit-task-input").fill("迁移账单回调，同时保住幂等性和回滚证据")

        draft = page.get_by_test_id("tutorial-fit-task-draft").input_value()
        completion_command = page.get_by_test_id("tutorial-fit-completion-command").input_value()
        assert draft.startswith("/loopora-plan\n\nLoopora 适配：<命中的强适配信号")
        assert "伪完成风险：<看起来完成但核心风险未证明的方式>" in draft
        assert completion_command.startswith(f"{cli_entry} fit --language zh --task ")
        assert "<测试、probe、artifact、浏览器/API 证据或可审查摘要>" in completion_command

        page.evaluate("() => window.LooporaUI.setLocale('en')")
        page.wait_for_function(
            """() => document
              .querySelector('[data-testid="tutorial-fit-task-draft"]')
              ?.value
              .startsWith('/loopora-plan\\n\\nLoopora fit:')""",
            timeout=10_000,
        )
        english_command = page.get_by_test_id("tutorial-fit-completion-command").input_value()
        assert english_command.startswith(f"{cli_entry} fit --task ")
        assert "--language zh" not in english_command
        assert "<how this could look done while core risk remains unproven>" in english_command


def test_browser_tools_fit_handoff_keeps_chinese_summary_and_completion_command(tmp_path: Path) -> None:
    service = _service(tmp_path)
    cli_entry = agent_adapter_command_prefix.current_copyable_loopora_cli_entry()
    storage_key = "loopora:tutorial-fit-handoff:v1"

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/tutorial#tutorial-decision-tree-panel", wait_until="domcontentloaded")
        page.get_by_test_id("tutorial-fit-task-review").wait_for(state="visible", timeout=10_000)

        page.evaluate("() => window.LooporaUI.setLocale('zh')")
        page.get_by_test_id("tutorial-fit-task-input").fill("迁移账单回调，同时保住幂等性和回滚证据")
        draft = page.get_by_test_id("tutorial-fit-task-draft").input_value()
        completion_command = page.get_by_test_id("tutorial-fit-completion-command").input_value()
        assert completion_command.startswith(f"{cli_entry} fit --language zh --task ")

        page.get_by_test_id("tutorial-fit-task-use-tools").click()
        page.wait_for_function("() => location.pathname === '/same-agent'", timeout=10_000)
        page.get_by_test_id("agent-adapter-draft-handoff").wait_for(state="visible", timeout=10_000)

        stored = page.evaluate("(key) => JSON.parse(sessionStorage.getItem(key))", storage_key)
        assert stored["language"] == "zh"
        assert stored["draft_first_task_message"] == draft
        assert stored["review_completion_command"] == completion_command

        inputs_text = page.get_by_test_id("agent-draft-handoff-inputs").text_content()
        assert "目标" in inputs_text
        assert "迁移账单回调" in inputs_text
        assert "Goal" not in inputs_text
        assert page.get_by_test_id("agent-draft-handoff-copy").count() == 0
        assert page.get_by_test_id("agent-draft-handoff-copy-completion").get_attribute("data-agent-draft-handoff-copy-completion") == completion_command


def test_browser_tutorial_fit_review_handoff_waits_for_explicit_target(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_workdir = tmp_path / "source project"
    source_workdir.mkdir()
    resolved_source = str(source_workdir.resolve())
    storage_key = "loopora:tutorial-fit-handoff:v1"
    inputs = _tutorial_fit_review_inputs()

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        draft = (
            "/loopora-plan\n\nLoopora fit: "
            f"{inputs['loopora_fit_reason']}; Goal: {inputs['task']}; Fake-done risks: {inputs['fake_done_risks']}; "
            f"Required evidence: {inputs['required_evidence']}; "
            f"Judgment tradeoffs: {inputs['judgment_tradeoffs']}."
        )
        page.goto(f"{base_url}/tutorial", wait_until="domcontentloaded")
        _store_tutorial_fit_handoff(
            page,
            storage_key=storage_key,
            inputs=inputs,
            draft=draft,
            workdir=resolved_source,
        )

        page.goto(f"{base_url}/same-agent", wait_until="domcontentloaded")
        page.wait_for_function(
            """(source) => {
              const draftCard = document.querySelector('[data-testid="agent-adapter-draft-handoff"]');
              const sourceText = document.querySelector('[data-testid="agent-draft-handoff-source-workdir"]')?.textContent || "";
              const targetText = document.querySelector('[data-testid="agent-draft-handoff-current-workdir"]')?.textContent || "";
              return document.querySelector('[data-testid="agent-adapter-workdir"]')?.value === ""
                && draftCard
                && !draftCard.hidden
                && draftCard.classList.contains("is-warning")
                && sourceText.includes(source)
                && targetText.includes("-")
                && document.querySelector('[data-testid="agent-draft-handoff-use-source"]')
                && !document.querySelector('[data-testid="agent-adapter-copy-first-task-example"]');
            }""",
            arg=resolved_source,
            timeout=10_000,
        )
        assert page.get_by_test_id("agent-draft-handoff-copy").count() == 0

        use_source_button = page.get_by_test_id("agent-draft-handoff-use-source")
        use_source_button.scroll_into_view_if_needed()
        use_source_button.click()
        page.wait_for_function(
            """(source) => document.querySelector('[data-testid="agent-adapter-workdir"]')?.value === source
              && document.querySelector('[data-testid="global-workdir-context"] code')?.textContent === source
              && new URL(document.querySelector('[data-testid="nav-compose-link"]').href).searchParams.get("workdir") === source
              && !document.querySelector('[data-testid="agent-adapter-draft-handoff"]')?.classList.contains("is-warning")""",
            arg=resolved_source,
            timeout=10_000,
        )
        assert page.get_by_test_id("agent-draft-handoff-copy").get_attribute("data-agent-draft-handoff-copy") == draft


def test_browser_tutorial_fit_review_handoff_stays_separate_for_different_target(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_workdir = tmp_path / "source project"
    target_workdir = tmp_path / "different target project"
    source_workdir.mkdir()
    target_workdir.mkdir()
    resolved_source = str(source_workdir.resolve())
    resolved_target = str(target_workdir.resolve())
    storage_key = "loopora:tutorial-fit-handoff:v1"
    inputs = _tutorial_fit_review_inputs()

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(
            f"{base_url}/tutorial?workdir={quote(resolved_source, safe='')}#tutorial-decision-tree-panel",
            wait_until="domcontentloaded",
        )
        page.get_by_test_id("tutorial-fit-task-review").wait_for(state="visible", timeout=10_000)

        draft = _fill_tutorial_fit_review(page, inputs)
        page.get_by_test_id("tutorial-fit-task-use-tools").click()
        _assert_tools_received_session_only_fit_handoff(
            page,
            storage_key=storage_key,
            inputs=inputs,
            draft=draft,
            workdir=resolved_source,
        )

        workdir_input = page.get_by_test_id("agent-adapter-workdir")
        workdir_input.fill(resolved_target)
        page.wait_for_function(
            """([source, target]) => {
              const draftCard = document.querySelector('[data-testid="agent-adapter-draft-handoff"]');
              const sourceText = document.querySelector('[data-testid="agent-draft-handoff-source-workdir"]')?.textContent || "";
              const targetText = document.querySelector('[data-testid="agent-draft-handoff-current-workdir"]')?.textContent || "";
              return document.querySelector('[data-testid="agent-adapter-workdir"]')?.value === target
                && draftCard
                && !draftCard.hidden
                && draftCard.classList.contains("is-warning")
                && sourceText.includes(source)
                && targetText.includes(target)
                && !document.querySelector('[data-testid="agent-adapter-copy-first-task-example"]');
            }""",
            arg=[resolved_source, resolved_target],
            timeout=10_000,
        )
        assert page.get_by_test_id("agent-adapter-handoff").is_hidden()
        assert page.get_by_test_id("agent-draft-handoff-copy").count() == 0
        assert resolved_source in page.get_by_test_id("agent-draft-handoff-source-workdir").text_content()
        assert resolved_target in page.get_by_test_id("agent-draft-handoff-current-workdir").text_content()
        assert page.get_by_test_id("agent-draft-handoff-state").is_visible()
        assert page.evaluate("(key) => JSON.parse(sessionStorage.getItem(key)).source_workdir", storage_key) == resolved_source

        use_source_button = page.get_by_test_id("agent-draft-handoff-use-source")
        use_source_button.scroll_into_view_if_needed()
        use_source_button.click()
        page.wait_for_function(
            """(source) => {
              const draftCard = document.querySelector('[data-testid="agent-adapter-draft-handoff"]');
              return document.querySelector('[data-testid="agent-adapter-workdir"]')?.value === source
                && document.querySelector('[data-testid="global-workdir-context"] code')?.textContent === source
                && new URL(document.querySelector('[data-testid="nav-compose-link"]').href).searchParams.get("workdir") === source
                && draftCard
                && !draftCard.hidden
                && !draftCard.classList.contains("is-warning")
                && !document.querySelector('[data-testid="agent-draft-handoff-current-workdir"]');
            }""",
            arg=resolved_source,
            timeout=10_000,
        )
        assert page.get_by_test_id("agent-draft-handoff-copy").get_attribute("data-agent-draft-handoff-copy") == draft


def test_browser_tutorial_handoff_without_source_does_not_target_explicit_project(tmp_path: Path) -> None:
    service = _service(tmp_path)
    target_workdir = tmp_path / "explicit target project"
    target_workdir.mkdir()
    resolved_target = str(target_workdir.resolve())
    storage_key = "loopora:tutorial-fit-handoff:v1"
    inputs = _tutorial_fit_review_inputs()
    draft = (
        "/loopora-plan\n\nLoopora fit: "
        f"{inputs['loopora_fit_reason']}; Goal: {inputs['task']}; Fake-done risks: {inputs['fake_done_risks']}; "
        f"Required evidence: {inputs['required_evidence']}; "
        f"Judgment tradeoffs: {inputs['judgment_tradeoffs']}."
    )
    payload = {
        "schema_version": 1,
        "source": "tutorial_fit_review",
        "inputs": inputs,
        "draft_first_task_message": draft,
        "missing_first_task_input_ids": [],
        "ready_for_loopora_plan_message": True,
        "saved_at": "2026-01-01T00:00:00.000Z",
    }

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/tutorial", wait_until="domcontentloaded")
        page.evaluate(
            """([key, payload]) => sessionStorage.setItem(key, JSON.stringify(payload))""",
            [storage_key, payload],
        )

        page.goto(f"{base_url}/loops/new?workdir={quote(resolved_target, safe='')}", wait_until="domcontentloaded")
        page.get_by_test_id("loop-create-tutorial-handoff").wait_for(state="visible", timeout=10_000)
        choice_state = page.evaluate(
            """() => ({
              webDisabled: document.querySelector('[data-testid="loop-create-bundle-link"]')?.getAttribute("aria-disabled"),
              handoffWebDisabled: document.querySelector('[data-testid="loop-create-tutorial-handoff-web-link"]')?.getAttribute("aria-disabled"),
              useSourceHidden: document.querySelector('[data-testid="loop-create-tutorial-handoff-use-source"]')?.hidden,
            })"""
        )
        assert choice_state == {"webDisabled": "false", "handoffWebDisabled": "false", "useSourceHidden": True}

        page.goto(
            f"{base_url}/loops/new/bundle?alignment_workdir={quote(resolved_target, safe='')}",
            wait_until="domcontentloaded",
        )
        page.get_by_test_id("alignment-tutorial-handoff-bridge").wait_for(state="visible", timeout=10_000)
        alignment_state = page.evaluate(
            """() => ({
              workdirInput: document.querySelector('[data-testid="alignment-workdir"]')?.value,
              taskGoal: document.querySelector('[data-testid="alignment-task-goal-input"]')?.value,
              prefillCount: document.querySelectorAll('[data-testid="alignment-tutorial-handoff-prefill"]').length,
              useSourceCount: document.querySelectorAll('[data-testid="alignment-tutorial-handoff-use-source"]').length,
              copyDraft: document.querySelector('[data-testid="alignment-tutorial-handoff-copy-draft"]')?.getAttribute("data-tutorial-handoff-copy-draft"),
            })"""
        )
        assert alignment_state == {
            "workdirInput": resolved_target,
            "taskGoal": "",
            "prefillCount": 0,
            "useSourceCount": 0,
            "copyDraft": draft,
        }

        page.goto(f"{base_url}/same-agent?workdir={quote(resolved_target, safe='')}", wait_until="domcontentloaded")
        page.get_by_test_id("agent-adapter-draft-handoff").wait_for(state="visible", timeout=10_000)
        tools_state = page.evaluate(
            """() => ({
              target: document.querySelector('[data-testid="agent-adapter-workdir"]')?.value,
              warning: document.querySelector('[data-testid="agent-adapter-draft-handoff"]')?.classList.contains("is-warning"),
              copyCount: document.querySelectorAll('[data-testid="agent-draft-handoff-copy"]').length,
              useSourceCount: document.querySelectorAll('[data-testid="agent-draft-handoff-use-source"]').length,
              firstTask: document.querySelector('[data-testid="agent-adapter-copy-first-task-example"]')?.getAttribute("data-agent-adapter-command-copy") || "",
            })"""
        )
        assert tools_state == {
            "target": resolved_target,
            "warning": True,
            "copyCount": 0,
            "useSourceCount": 0,
            "firstTask": "",
        }


def test_browser_create_choice_surfaces_workdir_context_and_preserves_peer_links(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "target project with spaces"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(
            f"{base_url}/loops/new?workdir={quote(resolved_workdir, safe='')}",
            wait_until="domcontentloaded",
        )
        context = page.get_by_test_id("global-workdir-context")
        context.wait_for(state="visible", timeout=10_000)

        assert resolved_workdir in context.text_content()
        _assert_no_horizontal_overflow(page)
        link_context = page.evaluate(
            """() => {
              const param = (testid, name) => new URL(
                document.querySelector(`[data-testid="${testid}"]`).href
              ).searchParams.get(name);
              return {
                agent: param("loop-create-agent-link", "workdir"),
                bundle: param("loop-create-bundle-link", "alignment_workdir"),
                importPath: param("loop-create-import-link", "workdir"),
                manual: param("loop-create-manual-link", "workdir"),
              };
            }"""
        )
        assert link_context == {
            "agent": resolved_workdir,
            "bundle": resolved_workdir,
            "importPath": resolved_workdir,
            "manual": resolved_workdir,
        }


def test_browser_create_choice_routes_track_global_workdir_change(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_workdir = tmp_path / "create choice source"
    target_workdir = tmp_path / "create choice target"
    source_workdir.mkdir()
    target_workdir.mkdir()
    resolved_source = str(source_workdir.resolve())
    resolved_target = str(target_workdir.resolve())

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/loops/new?workdir={quote(resolved_source, safe='')}", wait_until="domcontentloaded")
        page.get_by_test_id("loop-create-choice-page").wait_for(state="visible", timeout=10_000)

        initial_state = page.evaluate(
            """() => {
              const workdir = (testid) => new URL(document.querySelector(`[data-testid="${testid}"]`).href).searchParams.get("workdir");
              const alignmentWorkdir = (testid) => new URL(document.querySelector(`[data-testid="${testid}"]`).href).searchParams.get("alignment_workdir");
              return {
                currentUrl: new URL(location.href).searchParams.get("workdir"),
                fitGuide: workdir("loop-create-fit-guide-link"),
                agent: workdir("loop-create-agent-link"),
                importPath: workdir("loop-create-import-link"),
                manual: workdir("loop-create-manual-link"),
                bundle: alignmentWorkdir("loop-create-bundle-link"),
                handoffWeb: alignmentWorkdir("loop-create-tutorial-handoff-web-link"),
              };
            }"""
        )
        assert initial_state == {
            "currentUrl": resolved_source,
            "fitGuide": resolved_source,
            "agent": resolved_source,
            "importPath": resolved_source,
            "manual": resolved_source,
            "bundle": resolved_source,
            "handoffWeb": resolved_source,
        }

        page.evaluate(
            """target => window.LooporaUI.syncWorkdirContext(target, {syncUrl: true, urlParam: "workdir"})""",
            resolved_target,
        )
        page.wait_for_function(
            """target => {
              const workdir = (testid) => new URL(document.querySelector(`[data-testid="${testid}"]`).href).searchParams.get("workdir");
              const alignmentWorkdir = (testid) => new URL(document.querySelector(`[data-testid="${testid}"]`).href).searchParams.get("alignment_workdir");
              return new URL(location.href).searchParams.get("workdir") === target
                && workdir("loop-create-fit-guide-link") === target
                && workdir("loop-create-agent-link") === target
                && workdir("loop-create-import-link") === target
                && workdir("loop-create-manual-link") === target
                && alignmentWorkdir("loop-create-bundle-link") === target
                && alignmentWorkdir("loop-create-tutorial-handoff-web-link") === target;
            }""",
            arg=resolved_target,
            timeout=10_000,
        )
        switched_state = page.evaluate(
            """() => {
              const workdir = (testid) => new URL(document.querySelector(`[data-testid="${testid}"]`).href).searchParams.get("workdir");
              const alignmentWorkdir = (testid) => new URL(document.querySelector(`[data-testid="${testid}"]`).href).searchParams.get("alignment_workdir");
              return {
                global: document.querySelector('[data-testid="global-workdir-context"] code')?.textContent || "",
                fitGuide: workdir("loop-create-fit-guide-link"),
                agent: workdir("loop-create-agent-link"),
                importPath: workdir("loop-create-import-link"),
                manual: workdir("loop-create-manual-link"),
                bundle: alignmentWorkdir("loop-create-bundle-link"),
                handoffWeb: alignmentWorkdir("loop-create-tutorial-handoff-web-link"),
              };
            }"""
        )
        assert switched_state == {
            "global": resolved_target,
            "fitGuide": resolved_target,
            "agent": resolved_target,
            "importPath": resolved_target,
            "manual": resolved_target,
            "bundle": resolved_target,
            "handoffWeb": resolved_target,
        }


def test_browser_manual_expert_links_and_route_datasets_track_global_workdir_change(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_workdir = tmp_path / "manual expert source"
    target_workdir = tmp_path / "manual expert target"
    source_workdir.mkdir()
    target_workdir.mkdir()
    resolved_source = str(source_workdir.resolve())
    resolved_target = str(target_workdir.resolve())

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/loops/new/manual?workdir={quote(resolved_source, safe='')}", wait_until="domcontentloaded")
        page.get_by_test_id("loop-create-form").wait_for(state="visible", timeout=10_000)

        state_script = """() => {
          const hrefParam = (testid, name) => new URL(document.querySelector(`[data-testid="${testid}"]`).href).searchParams.get(name);
          const returnToContext = (testid) => {
            const url = new URL(document.querySelector(`[data-testid="${testid}"]`).href);
            const returnTo = new URL(url.searchParams.get("return_to"), window.location.origin);
            return {
              workdir: url.searchParams.get("workdir"),
              returnToPath: returnTo.pathname,
              returnToWorkdir: returnTo.searchParams.get("workdir"),
              returnToHash: returnTo.hash,
            };
          };
          const datasetParam = (key, name) => {
            const shell = document.querySelector('[data-testid="loop-compose-shell"]');
            return new URL(shell.dataset[key], window.location.origin).searchParams.get(name);
          };
          const shell = document.querySelector('[data-testid="loop-compose-shell"]');
          const historyList = document.querySelector('[data-testid="alignment-history-list"]');
          const historyStart = new URL(historyList.dataset.historyEmptyStartHref, window.location.origin);
          return {
            currentUrl: new URL(location.href).searchParams.get("workdir"),
            global: document.querySelector('[data-testid="global-workdir-context"] code')?.textContent || "",
            guidance: hrefParam("manual-spec-web-guidance-link", "alignment_workdir"),
            roles: returnToContext("manual-roles-link"),
            flows: returnToContext("manual-orchestrations-link"),
            fitGuide: hrefParam("manual-fit-guide-link", "workdir"),
            cancel: hrefParam("manual-cancel-link", "workdir"),
            composeImport: datasetParam("composeImportHref", "workdir"),
            composeManual: datasetParam("composeManualHref", "workdir"),
            tutorialFit: datasetParam("tutorialFitHref", "workdir"),
            datasetDeclaration: shell.dataset.workdirContextDatasetUrls,
            historyEmptyStart: historyStart.searchParams.get("alignment_workdir"),
            historyDatasetDeclaration: historyList.dataset.workdirContextDatasetUrls,
          };
        }"""
        initial_state = page.evaluate(state_script)
        expected_source = {
            "currentUrl": resolved_source,
            "global": resolved_source,
            "guidance": resolved_source,
            "roles": {
                "workdir": resolved_source,
                "returnToPath": "/loops/new/manual",
                "returnToWorkdir": resolved_source,
                "returnToHash": "#manual-loop-form",
            },
            "flows": {
                "workdir": resolved_source,
                "returnToPath": "/loops/new/manual",
                "returnToWorkdir": resolved_source,
                "returnToHash": "#manual-loop-form",
            },
            "fitGuide": resolved_source,
            "cancel": resolved_source,
            "composeImport": resolved_source,
            "composeManual": resolved_source,
            "tutorialFit": resolved_source,
            "datasetDeclaration": "composeImportHref:workdir composeManualHref:workdir tutorialFitHref:workdir",
            "historyEmptyStart": resolved_source,
            "historyDatasetDeclaration": "historyEmptyStartHref:alignment_workdir",
        }
        assert initial_state == expected_source

        page.evaluate(
            """target => window.LooporaUI.syncWorkdirContext(target, {syncUrl: true, urlParam: "workdir"})""",
            resolved_target,
        )
        page.wait_for_function(
            """target => {
              const hrefParam = (testid, name) => new URL(document.querySelector(`[data-testid="${testid}"]`).href).searchParams.get(name);
              const datasetParam = (key, name) => {
                const shell = document.querySelector('[data-testid="loop-compose-shell"]');
                return new URL(shell.dataset[key], window.location.origin).searchParams.get(name);
              };
              const historyStart = new URL(
                document.querySelector('[data-testid="alignment-history-list"]').dataset.historyEmptyStartHref,
                window.location.origin
              );
              return new URL(location.href).searchParams.get("workdir") === target
                && document.querySelector('[data-testid="global-workdir-context"] code')?.textContent === target
                && hrefParam("manual-spec-web-guidance-link", "alignment_workdir") === target
                && hrefParam("manual-roles-link", "workdir") === target
                && hrefParam("manual-orchestrations-link", "workdir") === target
                && hrefParam("manual-fit-guide-link", "workdir") === target
                && hrefParam("manual-cancel-link", "workdir") === target
                && datasetParam("composeImportHref", "workdir") === target
                && datasetParam("composeManualHref", "workdir") === target
                && datasetParam("tutorialFitHref", "workdir") === target
                && historyStart.searchParams.get("alignment_workdir") === target;
            }""",
            arg=resolved_target,
            timeout=10_000,
        )
        switched_state = page.evaluate(state_script)
        assert switched_state == {
            **expected_source,
            "currentUrl": resolved_target,
            "global": resolved_target,
            "guidance": resolved_target,
            "roles": {
                "workdir": resolved_target,
                "returnToPath": "/loops/new/manual",
                "returnToWorkdir": resolved_target,
                "returnToHash": "#manual-loop-form",
            },
            "flows": {
                "workdir": resolved_target,
                "returnToPath": "/loops/new/manual",
                "returnToWorkdir": resolved_target,
                "returnToHash": "#manual-loop-form",
            },
            "fitGuide": resolved_target,
            "cancel": resolved_target,
            "composeImport": resolved_target,
            "composeManual": resolved_target,
            "tutorialFit": resolved_target,
            "historyEmptyStart": resolved_target,
        }


def test_browser_create_choice_tutorial_handoff_tools_link_preserves_source_workdir(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_workdir = tmp_path / "source project"
    target_workdir = tmp_path / "different target project"
    source_workdir.mkdir()
    target_workdir.mkdir()
    resolved_source = str(source_workdir.resolve())
    resolved_target = str(target_workdir.resolve())
    storage_key = "loopora:tutorial-fit-handoff:v1"
    inputs = _tutorial_fit_review_inputs()
    draft = (
        "/loopora-plan\n\nLoopora fit: "
        f"{inputs['loopora_fit_reason']}; Goal: {inputs['task']}; Fake-done risks: {inputs['fake_done_risks']}; "
        f"Required evidence: {inputs['required_evidence']}; "
        f"Judgment tradeoffs: {inputs['judgment_tradeoffs']}."
    )

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/tutorial", wait_until="domcontentloaded")
        _store_tutorial_fit_handoff(
            page,
            storage_key=storage_key,
            inputs=inputs,
            draft=draft,
            workdir=resolved_source,
        )

        page.goto(
            f"{base_url}/loops/new?workdir={quote(resolved_target, safe='')}",
            wait_until="domcontentloaded",
        )
        page.get_by_test_id("loop-create-tutorial-handoff").wait_for(state="visible", timeout=10_000)
        handoff_links = page.evaluate(
            """() => {
              const hrefWorkdir = (testid) => new URL(document.querySelector(`[data-testid="${testid}"]`).href).searchParams.get("workdir");
              const webStart = document.querySelector('[data-testid="loop-create-bundle-link"]');
              return {
                finish: hrefWorkdir("loop-create-tutorial-handoff-finish-link"),
                tools: hrefWorkdir("loop-create-tutorial-handoff-tools-link"),
                source: hrefWorkdir("loop-create-tutorial-handoff-use-source"),
                webDisabled: webStart?.getAttribute("aria-disabled"),
              };
            }"""
        )
        assert handoff_links == {
            "finish": resolved_source,
            "tools": resolved_source,
            "source": resolved_source,
            "webDisabled": "false",
        }

        page.get_by_test_id("loop-create-tutorial-handoff-tools-link").click()
        page.wait_for_function(
            """([source, draft]) => location.pathname === "/same-agent"
              && document.querySelector('[data-testid="agent-adapter-workdir"]')?.value === source
              && document
                .querySelector('[data-testid="agent-draft-handoff-copy"]')
                ?.getAttribute("data-agent-draft-handoff-copy") === draft
              && !document.querySelector('[data-testid="agent-adapter-draft-handoff"]')?.classList.contains("is-warning")""",
            arg=[resolved_source, draft],
            timeout=10_000,
        )


def test_browser_create_choice_tutorial_handoff_web_links_use_source_when_target_is_blank(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_workdir = tmp_path / "source project"
    source_workdir.mkdir()
    resolved_source = str(source_workdir.resolve())
    storage_key = "loopora:tutorial-fit-handoff:v1"
    inputs = _tutorial_fit_review_inputs()
    draft = (
        "/loopora-plan\n\nLoopora fit: "
        f"{inputs['loopora_fit_reason']}; Goal: {inputs['task']}; Fake-done risks: {inputs['fake_done_risks']}; "
        f"Required evidence: {inputs['required_evidence']}; "
        f"Judgment tradeoffs: {inputs['judgment_tradeoffs']}."
    )

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/tutorial", wait_until="domcontentloaded")
        _store_tutorial_fit_handoff(
            page,
            storage_key=storage_key,
            inputs=inputs,
            draft=draft,
            workdir=resolved_source,
        )

        page.goto(f"{base_url}/loops/new", wait_until="domcontentloaded")
        page.get_by_test_id("loop-create-tutorial-handoff").wait_for(state="visible", timeout=10_000)
        web_links = page.evaluate(
            """() => {
              const alignmentWorkdir = (testid) => new URL(document.querySelector(`[data-testid="${testid}"]`).href).searchParams.get("alignment_workdir");
              const workdir = (testid) => new URL(document.querySelector(`[data-testid="${testid}"]`).href).searchParams.get("workdir");
              return {
                bridgeAlignment: alignmentWorkdir("loop-create-tutorial-handoff-web-link"),
                primaryAlignment: alignmentWorkdir("loop-create-bundle-link"),
                bridgeWorkdir: workdir("loop-create-tutorial-handoff-web-link"),
                primaryWorkdir: workdir("loop-create-bundle-link"),
              };
            }"""
        )
        assert web_links == {
            "bridgeAlignment": resolved_source,
            "primaryAlignment": resolved_source,
            "bridgeWorkdir": None,
            "primaryWorkdir": None,
        }

        page.get_by_test_id("loop-create-bundle-link").click()
        page.wait_for_function(
            """([source, task]) => location.pathname === "/loops/new/bundle"
              && new URL(location.href).searchParams.get("alignment_workdir") === source
              && document.querySelector('[data-testid="alignment-task-goal-input"]')?.value === task""",
            arg=[resolved_source, inputs["task"]],
            timeout=10_000,
        )


def test_browser_create_choice_clear_tutorial_handoff_restores_unscoped_web_links(tmp_path: Path) -> None:
    service = _service(tmp_path)
    source_workdir = tmp_path / "source project"
    source_workdir.mkdir()
    resolved_source = str(source_workdir.resolve())
    storage_key = "loopora:tutorial-fit-handoff:v1"
    inputs = _tutorial_fit_review_inputs()
    draft = (
        "/loopora-plan\n\nLoopora fit: "
        f"{inputs['loopora_fit_reason']}; Goal: {inputs['task']}; Fake-done risks: {inputs['fake_done_risks']}; "
        f"Required evidence: {inputs['required_evidence']}; "
        f"Judgment tradeoffs: {inputs['judgment_tradeoffs']}."
    )

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/tutorial", wait_until="domcontentloaded")
        _store_tutorial_fit_handoff(
            page,
            storage_key=storage_key,
            inputs=inputs,
            draft=draft,
            workdir=resolved_source,
        )

        page.goto(f"{base_url}/loops/new", wait_until="domcontentloaded")
        page.get_by_test_id("loop-create-tutorial-handoff").wait_for(state="visible", timeout=10_000)
        assert (
            page.evaluate(
                """() => new URL(document.querySelector('[data-testid="loop-create-bundle-link"]').href)
              .searchParams.get("alignment_workdir")"""
            )
            == resolved_source
        )

        page.get_by_test_id("loop-create-tutorial-handoff-clear").click()
        page.get_by_test_id("loop-create-tutorial-handoff").wait_for(state="hidden", timeout=10_000)
        web_links = page.evaluate(
            """() => {
              const hrefState = (testid) => {
                const url = new URL(document.querySelector(`[data-testid="${testid}"]`).href);
                return {
                  path: url.pathname,
                  alignmentWorkdir: url.searchParams.get("alignment_workdir"),
                  workdir: url.searchParams.get("workdir"),
                };
              };
              return {
                primary: hrefState("loop-create-bundle-link"),
                bridge: hrefState("loop-create-tutorial-handoff-web-link"),
                storedDraft: sessionStorage.getItem("loopora:tutorial-fit-handoff:v1"),
                activeTestId: document.activeElement?.dataset.testid || "",
                fitPromptVisible: !document.querySelector('[data-testid="loop-create-fit-review"]')?.hidden,
              };
            }"""
        )
        assert web_links == {
            "primary": {"path": "/loops/new/bundle", "alignmentWorkdir": None, "workdir": None},
            "bridge": {"path": "/loops/new/bundle", "alignmentWorkdir": None, "workdir": None},
            "storedDraft": None,
            "activeTestId": "loop-create-bundle-link",
            "fitPromptVisible": True,
        }

        page.get_by_test_id("loop-create-bundle-link").click()
        page.wait_for_function(
            """() => location.pathname === "/loops/new/bundle"
              && !new URL(location.href).searchParams.get("alignment_workdir")
              && !new URL(location.href).searchParams.get("workdir")
              && document.querySelector('[data-testid="alignment-task-goal-input"]')?.value === ''""",
            timeout=10_000,
        )


def test_browser_manual_workdir_edits_sync_visible_context_and_peer_links(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "manual target with spaces"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(f"{base_url}/loops/new/manual", wait_until="domcontentloaded")
        context = page.get_by_test_id("global-workdir-context")
        assert context.is_hidden()

        workdir_input = page.locator("#workdir-input")
        workdir_input.fill(resolved_workdir)

        page.wait_for_function(
            """(workdir) => {
              const context = document.querySelector('[data-testid="global-workdir-context"]');
              return document.activeElement === document.querySelector("#workdir-input")
                && !context.hidden
                && context.querySelector("code")?.textContent === workdir;
            }""",
            arg=resolved_workdir,
            timeout=10_000,
        )
        link_context = page.evaluate(
            """() => {
              const param = (testid, name) => new URL(
                document.querySelector(`[data-testid="${testid}"]`).href
              ).searchParams.get(name);
              const actionParam = (selector, name) => new URL(
                document.querySelector(selector).action
              ).searchParams.get(name);
              const returnToContext = (selector) => {
                const url = new URL(document.querySelector(selector).href);
                const returnTo = new URL(url.searchParams.get("return_to"), window.location.origin);
                return {
                  workdir: url.searchParams.get("workdir"),
                  returnToPath: returnTo.pathname,
                  returnToWorkdir: returnTo.searchParams.get("workdir"),
                  returnToHash: returnTo.hash,
                };
              };
              return {
                currentUrl: new URL(window.location.href).searchParams.get("workdir"),
                navCompose: param("nav-compose-link", "workdir"),
                chat: param("alignment-path-chat", "alignment_workdir"),
                importPath: param("alignment-path-import", "workdir"),
                manual: param("alignment-path-manual", "workdir"),
                manualAction: actionParam("#new-loop-form", "workdir"),
                importAction: actionParam("#bundle-import-form-fields", "workdir"),
                roles: returnToContext('a[href^="/roles"][href*="return_to"]'),
                flows: returnToContext('a[href^="/orchestrations"][href*="return_to"]'),
              };
            }"""
        )
        assert link_context == {
            "currentUrl": resolved_workdir,
            "navCompose": resolved_workdir,
            "chat": resolved_workdir,
            "importPath": resolved_workdir,
            "manual": resolved_workdir,
            "manualAction": resolved_workdir,
            "importAction": resolved_workdir,
            "roles": {
                "workdir": resolved_workdir,
                "returnToPath": "/loops/new/manual",
                "returnToWorkdir": resolved_workdir,
                "returnToHash": "#manual-loop-form",
            },
            "flows": {
                "workdir": resolved_workdir,
                "returnToPath": "/loops/new/manual",
                "returnToWorkdir": resolved_workdir,
                "returnToHash": "#manual-loop-form",
            },
        }

        workdir_input.fill("")
        page.wait_for_function(
            """() => !new URL(window.location.href).searchParams.get("workdir")
              && document.activeElement === document.querySelector("#workdir-input")
              && document.querySelector('[data-testid="global-workdir-context"]')?.hidden""",
            timeout=10_000,
        )
        cleared_context = page.evaluate(
            """() => {
              const param = (testid, name) => new URL(
                document.querySelector(`[data-testid="${testid}"]`).href
              ).searchParams.get(name);
              const actionParam = (selector, name) => new URL(
                document.querySelector(selector).action
              ).searchParams.get(name);
              const returnToContext = (selector) => {
                const url = new URL(document.querySelector(selector).href);
                const returnTo = new URL(url.searchParams.get("return_to"), window.location.origin);
                return {
                  workdir: url.searchParams.get("workdir"),
                  returnToWorkdir: returnTo.searchParams.get("workdir"),
                };
              };
              return {
                currentUrl: new URL(window.location.href).searchParams.get("workdir"),
                navCompose: param("nav-compose-link", "workdir"),
                chat: param("alignment-path-chat", "alignment_workdir"),
                importPath: param("alignment-path-import", "workdir"),
                manual: param("alignment-path-manual", "workdir"),
                manualAction: actionParam("#new-loop-form", "workdir"),
                importAction: actionParam("#bundle-import-form-fields", "workdir"),
                roles: returnToContext('a[href^="/roles"][href*="return_to"]'),
                flows: returnToContext('a[href^="/orchestrations"][href*="return_to"]'),
              };
            }"""
        )
        assert cleared_context == {
            "currentUrl": None,
            "navCompose": None,
            "chat": None,
            "importPath": None,
            "manual": None,
            "manualAction": None,
            "importAction": None,
            "roles": {"workdir": None, "returnToWorkdir": None},
            "flows": {"workdir": None, "returnToWorkdir": None},
        }


def test_browser_delete_confirmation_keeps_keyboard_focus_inside_modal(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create_role_definition(
        name="Keyboard Reviewer",
        description="Review keyboard safety for dangerous actions.",
        posture_notes="Keep destructive confirmation accessible.",
        archetype="builder",
        prompt_markdown=textwrap.dedent(
            """\
            ---
            version: 1
            archetype: builder
            ---

            Review keyboard safety for dangerous actions.
            """
        ),
        executor_kind="codex",
        executor_mode="preset",
        model="",
        reasoning_effort="",
    )

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(f"{base_url}/roles", wait_until="domcontentloaded")
        delete_button = page.get_by_test_id("delete-role-definition-button").first
        delete_button.focus()
        delete_button.click()

        page.wait_for_function(
            """() => !document.querySelector("#confirm-modal")?.hidden
              && document.activeElement === document.querySelector("#confirm-modal-cancel")""",
            timeout=10_000,
        )
        page.wait_for_function(
            """() => document.querySelector("#confirm-modal-confirm")
              && !document.querySelector("#confirm-modal-confirm").disabled""",
            timeout=10_000,
        )
        page.locator("#confirm-modal-cancel").focus()
        page.keyboard.press("Shift+Tab")
        page.wait_for_function(
            """() => document.activeElement === document.querySelector("#confirm-modal-confirm")""",
            timeout=10_000,
        )
        page.keyboard.press("Tab")
        page.wait_for_function(
            """() => document.activeElement === document.querySelector("#confirm-modal-cancel")""",
            timeout=10_000,
        )

        page.get_by_test_id("nav-tools-link").focus()
        page.keyboard.press("Tab")
        page.wait_for_function(
            """() => document.activeElement === document.querySelector("#confirm-modal-cancel")""",
            timeout=10_000,
        )

        page.keyboard.press("Escape")
        page.wait_for_function(
            """() => document.querySelector("#confirm-modal")?.hidden
              && document.activeElement === document.querySelector('[data-testid="delete-role-definition-button"]')""",
            timeout=10_000,
        )


def test_browser_asset_nav_menu_supports_keyboard_navigation(tmp_path: Path) -> None:
    service = _service(tmp_path)

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/", wait_until="domcontentloaded")
        page.get_by_test_id("nav-resource-toggle").focus()
        page.keyboard.press("ArrowDown")
        page.wait_for_function(
            """() => document.querySelector('[data-testid="nav-resource-toggle"]')?.getAttribute("aria-expanded") === "true"
              && !document.querySelector('[data-testid="nav-resource-panel"]')?.hidden
              && document.activeElement === document.querySelector('[data-testid="nav-menu-bundles-link"]')""",
            timeout=10_000,
        )

        page.keyboard.press("ArrowDown")
        page.wait_for_function(
            """() => document.activeElement === document.querySelector('[data-testid="nav-menu-roles-link"]')""",
            timeout=10_000,
        )
        page.keyboard.press("End")
        page.wait_for_function(
            """() => document.activeElement === document.querySelector('[data-testid="nav-menu-orchestrations-link"]')""",
            timeout=10_000,
        )
        page.keyboard.press("Escape")
        page.wait_for_function(
            """() => document.querySelector('[data-testid="nav-resource-toggle"]')?.getAttribute("aria-expanded") === "false"
              && document.querySelector('[data-testid="nav-resource-panel"]')?.hidden
              && document.activeElement === document.querySelector('[data-testid="nav-resource-toggle"]')""",
            timeout=10_000,
        )

        page.keyboard.press("Enter")
        page.wait_for_function(
            """() => document.querySelector('[data-testid="nav-resource-toggle"]')?.getAttribute("aria-expanded") === "true"
              && document.activeElement === document.querySelector('[data-testid="nav-menu-bundles-link"]')""",
            timeout=10_000,
        )
        page.get_by_test_id("nav-tools-link").focus()
        page.wait_for_function(
            """() => document.querySelector('[data-testid="nav-resource-toggle"]')?.getAttribute("aria-expanded") === "false"
              && document.querySelector('[data-testid="nav-resource-panel"]')?.hidden""",
            timeout=10_000,
        )


def test_browser_help_tooltip_is_accessible_and_dismissible(tmp_path: Path) -> None:
    service = _service(tmp_path)

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/roles", wait_until="domcontentloaded")

        page.get_by_test_id("builtin-role-templates-tip").focus()
        page.wait_for_function(
            """() => {
              const tip = document.querySelector('[data-testid="builtin-role-templates-tip"]');
              const tooltip = document.querySelector("#help-floating-tooltip");
              return Boolean(tip && tooltip && !tooltip.hidden
                && tooltip.id === "help-floating-tooltip"
                && tooltip.getAttribute("role") === "tooltip"
                && tip.getAttribute("aria-describedby") === tooltip.id
                && tooltip.textContent.trim().length > 0);
            }""",
            timeout=10_000,
        )

        page.keyboard.press("Escape")
        page.wait_for_function(
            """() => {
              const tip = document.querySelector('[data-testid="builtin-role-templates-tip"]');
              const tooltip = document.querySelector("#help-floating-tooltip");
              return Boolean(tip && tooltip?.hidden
                && !tip.hasAttribute("aria-describedby")
                && document.activeElement === tip);
            }""",
            timeout=10_000,
        )

        page.get_by_test_id("builtin-role-templates-tip").click()
        page.wait_for_function(
            """() => {
              const tip = document.querySelector('[data-testid="builtin-role-templates-tip"]');
              const tooltip = document.querySelector("#help-floating-tooltip");
              return Boolean(tip && tooltip && !tooltip.hidden
                && tip.getAttribute("aria-describedby") === tooltip.id);
            }""",
            timeout=10_000,
        )
        page.evaluate(
            """() => {
              const target = document.createElement("button");
              target.type = "button";
              target.dataset.testid = "tooltip-outside-target";
              target.textContent = "outside";
              target.style.position = "fixed";
              target.style.inset = "4px auto auto 4px";
              target.style.zIndex = "10000";
              document.body.append(target);
            }"""
        )
        page.get_by_test_id("tooltip-outside-target").click()
        page.wait_for_function(
            """() => {
              const tip = document.querySelector('[data-testid="builtin-role-templates-tip"]');
              const tooltip = document.querySelector("#help-floating-tooltip");
              return Boolean(tip && tooltip?.hidden && !tip.hasAttribute("aria-describedby"));
            }""",
            timeout=10_000,
        )


def test_browser_manual_explicit_workdir_ignores_stale_browser_draft(tmp_path: Path) -> None:
    service = _service(tmp_path)
    stale_workdir = tmp_path / "stale draft project"
    target_workdir = tmp_path / "explicit target project"
    stale_workdir.mkdir()
    target_workdir.mkdir()
    resolved_stale = str(stale_workdir.resolve())
    resolved_target = str(target_workdir.resolve())

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/loops/new/manual", wait_until="domcontentloaded")
        page.evaluate(
            """(workdir) => localStorage.setItem(
              "loopora:new-loop-draft:v2",
              JSON.stringify({workdir, spec_path: `${workdir}/stale-spec.md`})
            )""",
            resolved_stale,
        )

        page.goto(
            f"{base_url}/loops/new/manual?workdir={quote(resolved_target, safe='')}",
            wait_until="domcontentloaded",
        )
        page.get_by_test_id("loop-create-form").wait_for(state="visible", timeout=10_000)
        preserved_context = page.evaluate(
            """() => ({
              workdirInput: document.querySelector("#workdir-input")?.value,
              specInput: document.querySelector("#spec-path-input")?.value,
              restoreDraft: document.querySelector("#new-loop-form")?.dataset.restoreDraft,
              context: document.querySelector('[data-testid="global-workdir-context"] code')?.textContent,
              currentUrl: new URL(location.href).searchParams.get("workdir"),
              manualAction: new URL(document.querySelector("#new-loop-form").action).searchParams.get("workdir"),
              importAction: new URL(document.querySelector("#bundle-import-form-fields").action).searchParams.get("workdir"),
            })"""
        )
        assert preserved_context == {
            "workdirInput": resolved_target,
            "specInput": "",
            "restoreDraft": "false",
            "context": resolved_target,
            "currentUrl": resolved_target,
            "manualAction": resolved_target,
            "importAction": resolved_target,
        }


def test_browser_web_compose_explicit_workdir_ignores_stale_alignment_session(tmp_path: Path) -> None:
    service = _service(tmp_path)
    target_workdir = tmp_path / "explicit web compose target"
    target_workdir.mkdir()
    resolved_target = str(target_workdir.resolve())
    stale_session_hits: list[str] = []

    def record_stale_session(route) -> None:
        stale_session_hits.append(route.request.url)
        route.fulfill(status=500, content_type="application/json", body='{"error":"stale session should not load"}')

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.route("**/api/alignments/sessions/stale-session-id", record_stale_session)
        page.goto(f"{base_url}/loops/new/bundle", wait_until="domcontentloaded")
        page.evaluate("""() => localStorage.setItem("loopora:alignment-session:v1", "stale-session-id")""")

        page.goto(
            f"{base_url}/loops/new/bundle?alignment_workdir={quote(resolved_target, safe='')}",
            wait_until="domcontentloaded",
        )
        page.get_by_test_id("alignment-start-form").wait_for(state="visible", timeout=10_000)
        page.wait_for_function(
            """target => document.querySelector('[data-testid="alignment-workdir"]')?.value === target
              && new URL(location.href).searchParams.get("alignment_workdir") === target""",
            arg=resolved_target,
            timeout=10_000,
        )
        preserved_context = page.evaluate(
            """() => ({
              workdirInput: document.querySelector('[data-testid="alignment-workdir"]')?.value,
              taskGoal: document.querySelector('[data-testid="alignment-task-goal-input"]')?.value,
              message: document.querySelector('[data-testid="alignment-message-input"]')?.value,
              context: document.querySelector('[data-testid="global-workdir-context"] code')?.textContent,
              currentUrl: new URL(location.href).searchParams.get("alignment_workdir"),
              navCompose: new URL(document.querySelector('[data-testid="nav-compose-link"]').href).searchParams.get("workdir"),
              manualPath: new URL(document.querySelector('[data-testid="alignment-path-manual"]').href).searchParams.get("workdir"),
            })"""
        )
        assert stale_session_hits == []
        assert preserved_context == {
            "workdirInput": resolved_target,
            "taskGoal": "",
            "message": "",
            "context": resolved_target,
            "currentUrl": resolved_target,
            "navCompose": resolved_target,
            "manualPath": resolved_target,
        }


def test_browser_web_compose_first_transcript_includes_optional_direct_path(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "web direct path transcript target"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())
    inputs = _tutorial_fit_review_inputs()

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(
            f"{base_url}/loops/new/bundle?alignment_workdir={quote(resolved_workdir, safe='')}",
            wait_until="domcontentloaded",
        )
        page.get_by_test_id("alignment-start-form").wait_for(state="visible", timeout=10_000)
        page.get_by_test_id("alignment-task-goal-input").fill(inputs["task"])
        page.get_by_test_id("alignment-judgment-details").locator("summary").click()
        page.get_by_test_id("alignment-loopora-fit-reason-input").fill(inputs["loopora_fit_reason"])
        page.get_by_test_id("alignment-direct-path-check-input").fill(inputs["direct_path_check"])
        page.get_by_test_id("alignment-fake-done-risk-input").fill(inputs["fake_done_risks"])
        page.get_by_test_id("alignment-required-evidence-input").fill(inputs["required_evidence"])
        page.get_by_test_id("alignment-judgment-tradeoffs-input").fill(inputs["judgment_tradeoffs"])
        page.get_by_test_id("alignment-send-button").click()
        page.wait_for_function(
            """workdir => new URL(location.href).searchParams.get("alignment_session_id")
              && document.querySelector('[data-testid="alignment-workdir"]')?.value === workdir""",
            arg=resolved_workdir,
            timeout=10_000,
        )
        session_id = page.evaluate("""() => new URL(location.href).searchParams.get("alignment_session_id")""")
        session = service.get_alignment_session(session_id)
        events = service.list_alignment_events(session_id)
        first_message = session["transcript"][0]["content"]

    assert "Direct-path check:\nDirect Agent work or hard checks alone" in first_message
    assert inputs["task"] in first_message
    assert inputs["judgment_tradeoffs"] in first_message
    assert [event["event_type"] for event in events[:2]] == ["alignment_session_created", "alignment_user_message"]
    assert events[1]["payload"]["content"] == first_message


def test_browser_web_compose_starts_from_task_only_then_becomes_a_reply_composer(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "progressive web conversation target"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())
    task = "Refactor the billing permission boundary without exposing customer data."

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(
            f"{base_url}/loops/new/bundle?alignment_workdir={quote(resolved_workdir, safe='')}",
            wait_until="domcontentloaded",
        )
        page.get_by_test_id("alignment-start-form").wait_for(state="visible", timeout=10_000)
        assert page.get_by_test_id("alignment-judgment-details").get_attribute("open") is None
        assert page.get_by_test_id("alignment-message-input").is_hidden()
        assert page.get_by_test_id("alignment-send-button").text_content().strip() == "Start conversation"

        page.get_by_test_id("alignment-task-goal-input").fill(task)
        page.get_by_test_id("alignment-send-button").click()
        page.wait_for_function(
            """() => new URL(location.href).searchParams.get('alignment_session_id')
              && !document.querySelector('[data-testid="alignment-judgment-brief"]')?.offsetParent
              && document.querySelector('[data-testid="alignment-message-input"]')?.offsetParent""",
            timeout=10_000,
        )
        session_id = page.evaluate("() => new URL(location.href).searchParams.get('alignment_session_id')")
        session = service.get_alignment_session(session_id)

    assert session["transcript"][0]["content"] == task


def test_browser_web_compose_projects_user_cancellation_as_stopped_not_failed(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "cancelled alignment target"
    workdir.mkdir()
    session = service.create_alignment_session(
        workdir=workdir,
        message="Preserve this task after I stop the Agent.",
        start_immediately=False,
    )
    service.repository.update_alignment_session(
        session["id"],
        status="failed",
        stop_requested=True,
        error_message="Cancelled by user.",
    )

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/loops/new/bundle?alignment_session_id={session['id']}", wait_until="domcontentloaded")
        page.wait_for_function(
            """() => document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === "cancelled"
              && document.querySelector('[data-testid="alignment-cancelled-focus-reply-button"]')?.offsetParent""",
            timeout=10_000,
        )
        page.locator('[data-testid="alignment-history-panel"] summary').click()
        history_item = page.locator(f'[data-testid="alignment-history-item"][data-session-id="{session["id"]}"]')

        assert page.get_by_test_id("alignment-status-pill").text_content().strip() == "Stopped"
        assert "The conversation was stopped" in page.locator(".alignment-failure-card.is-cancelled").text_content()
        assert "Stopped · codex" in history_item.text_content()
        assert "Failed" not in history_item.text_content()

        page.set_viewport_size({"width": 390, "height": 844})
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function(
            """() => document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === 'cancelled'""",
            timeout=10_000,
        )
        mobile_recovery = page.evaluate(
            """() => {
              const scroll = document.querySelector('.bundle-chat-scroll')?.getBoundingClientRect();
              const card = document.querySelector('.alignment-failure-card.is-cancelled')?.getBoundingClientRect();
              return {
                scrollTop: scroll?.top,
                scrollBottom: scroll?.bottom,
                cardTop: card?.top,
                cardBottom: card?.bottom,
                composerVisible: Boolean(document.querySelector('.alignment-composer-box')?.offsetParent),
              };
            }"""
        )
        assert mobile_recovery["cardTop"] >= mobile_recovery["scrollTop"] - 1
        assert mobile_recovery["cardBottom"] <= mobile_recovery["scrollBottom"] + 1
        assert mobile_recovery["composerVisible"] is False

        page.get_by_test_id("alignment-cancelled-focus-reply-button").click()
        assert page.get_by_test_id("alignment-message-input").is_visible()
        assert page.get_by_test_id("alignment-message-input").evaluate("element => document.activeElement === element") is True


def test_browser_web_compose_new_conversation_keeps_active_session(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "active alignment target"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())
    session = service.create_alignment_session(
        workdir=workdir,
        message="Create a release proof checklist.",
        start_immediately=False,
    )
    service.repository.update_alignment_session(session["id"], status="running")

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/loops/new/bundle?alignment_session_id={session['id']}", wait_until="domcontentloaded")
        page.wait_for_function(
            """([sessionId, workdir]) => new URL(location.href).searchParams.get("alignment_session_id") === sessionId
              && document.querySelector('[data-testid="alignment-workdir"]')?.value === workdir
              && document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === "running"
              && document.querySelector('[data-testid="alignment-send-button"]')?.dataset.action === "cancel" """,
            arg=[session["id"], resolved_workdir],
            timeout=10_000,
        )

        page.get_by_test_id("alignment-new-session-button").click()
        page.wait_for_function(
            """sessionId => document.querySelector('#alignment-error')?.textContent
              && new URL(location.href).searchParams.get("alignment_session_id") === sessionId
              && document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === "running" """,
            arg=session["id"],
            timeout=10_000,
        )
        preserved_state = page.evaluate(
            """() => ({
              sessionId: new URL(location.href).searchParams.get("alignment_session_id"),
              workdir: document.querySelector('[data-testid="alignment-workdir"]')?.value,
              status: document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status,
              sendAction: document.querySelector('[data-testid="alignment-send-button"]')?.dataset.action,
              error: document.querySelector('#alignment-error')?.textContent || "",
            })"""
        )
        assert preserved_state == {
            "sessionId": session["id"],
            "workdir": resolved_workdir,
            "status": "running",
            "sendAction": "cancel",
            "error": "The Agent is running; stop the current conversation before starting a new one.",
        }


def test_browser_web_compose_history_open_keeps_active_session(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "active history target"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())
    idle_session = service.create_alignment_session(
        workdir=workdir,
        message="Review the older idle plan.",
        start_immediately=False,
    )
    active_session = service.create_alignment_session(
        workdir=workdir,
        message="Create a release proof checklist.",
        start_immediately=False,
    )
    service.repository.update_alignment_session(active_session["id"], status="running")

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/loops/new/bundle?alignment_session_id={active_session['id']}", wait_until="domcontentloaded")
        page.wait_for_function(
            """([sessionId, workdir]) => new URL(location.href).searchParams.get("alignment_session_id") === sessionId
              && document.querySelector('[data-testid="alignment-workdir"]')?.value === workdir
              && document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === "running" """,
            arg=[active_session["id"], resolved_workdir],
            timeout=10_000,
        )

        page.locator('[data-testid="alignment-history-panel"] summary').click()
        page.locator(f'[data-testid="alignment-history-item"][data-session-id="{idle_session["id"]}"] [data-testid="alignment-history-open"]').click()
        page.wait_for_function(
            """sessionId => document.querySelector('#alignment-error')?.textContent
              && new URL(location.href).searchParams.get("alignment_session_id") === sessionId
              && document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === "running" """,
            arg=active_session["id"],
            timeout=10_000,
        )
        preserved_state = page.evaluate(
            """() => ({
              sessionId: new URL(location.href).searchParams.get("alignment_session_id"),
              workdir: document.querySelector('[data-testid="alignment-workdir"]')?.value,
              status: document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status,
              error: document.querySelector('#alignment-error')?.textContent || "",
            })"""
        )
        assert preserved_state == {
            "sessionId": active_session["id"],
            "workdir": resolved_workdir,
            "status": "running",
            "error": "The Agent is running; stop the current conversation before opening another chat.",
        }


def test_browser_web_compose_path_links_keep_active_session(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "active compose path target"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())
    session = service.create_alignment_session(
        workdir=workdir,
        message="Keep the running Web conversation attached.",
        start_immediately=False,
    )
    service.repository.update_alignment_session(session["id"], status="running")

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/loops/new/bundle?alignment_session_id={session['id']}", wait_until="domcontentloaded")
        page.wait_for_function(
            """([sessionId, workdir]) => new URL(location.href).searchParams.get("alignment_session_id") === sessionId
              && document.querySelector('[data-testid="alignment-workdir"]')?.value === workdir
              && document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === "running"
              && new URL(document.querySelector('[data-testid="alignment-path-manual"]')?.href || location.href).searchParams.get("workdir") === workdir """,
            arg=[session["id"], resolved_workdir],
            timeout=10_000,
        )
        manual_link = page.evaluate(
            """() => {
              const url = new URL(document.querySelector('[data-testid="alignment-path-manual"]').href);
              return {
                path: url.pathname,
                workdir: url.searchParams.get("workdir"),
                sessionId: url.searchParams.get("alignment_session_id"),
              };
            }"""
        )
        assert manual_link == {
            "path": "/loops/new/manual",
            "workdir": resolved_workdir,
            "sessionId": None,
        }
        nav_link = page.evaluate(
            """() => {
              const url = new URL(document.querySelector('[data-testid="nav-compose-link"]').href);
              return {
                path: url.pathname,
                workdir: url.searchParams.get("workdir"),
                sessionId: url.searchParams.get("alignment_session_id"),
              };
            }"""
        )
        assert nav_link == {
            "path": "/loops/new",
            "workdir": resolved_workdir,
            "sessionId": None,
        }

        page.get_by_test_id("alignment-path-manual").click()
        page.wait_for_function(
            """sessionId => document.querySelector('#alignment-error')?.textContent
              && new URL(location.href).searchParams.get("alignment_session_id") === sessionId
              && location.pathname === "/loops/new/bundle"
              && document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === "running" """,
            arg=session["id"],
            timeout=10_000,
        )
        preserved_state = page.evaluate(
            """() => ({
              path: location.pathname,
              sessionId: new URL(location.href).searchParams.get("alignment_session_id"),
              workdir: document.querySelector('[data-testid="alignment-workdir"]')?.value,
              status: document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status,
              error: document.querySelector('#alignment-error')?.textContent || "",
            })"""
        )
        assert preserved_state == {
            "path": "/loops/new/bundle",
            "sessionId": session["id"],
            "workdir": resolved_workdir,
            "status": "running",
            "error": "The Agent is running; stop the current conversation before switching composition paths.",
        }

        page.get_by_test_id("nav-compose-link").click()
        page.wait_for_function(
            """sessionId => document.querySelector('#alignment-error')?.textContent?.includes("composer start")
              && new URL(location.href).searchParams.get("alignment_session_id") === sessionId
              && location.pathname === "/loops/new/bundle"
              && document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === "running" """,
            arg=session["id"],
            timeout=10_000,
        )
        preserved_state = page.evaluate(
            """() => ({
              path: location.pathname,
              sessionId: new URL(location.href).searchParams.get("alignment_session_id"),
              workdir: document.querySelector('[data-testid="alignment-workdir"]')?.value,
              status: document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status,
              error: document.querySelector('#alignment-error')?.textContent || "",
            })"""
        )
        assert preserved_state == {
            "path": "/loops/new/bundle",
            "sessionId": session["id"],
            "workdir": resolved_workdir,
            "status": "running",
            "error": "The Agent is running; stop the current conversation before returning to the composer start.",
        }


def test_browser_global_project_scope_switches_and_clears_startup_default(tmp_path: Path) -> None:
    service = _service(tmp_path)
    startup_workdir = tmp_path / "scope startup project"
    other_workdir = tmp_path / "scope other project"
    startup_workdir.mkdir()
    other_workdir.mkdir()
    spec_path = tmp_path / "scope-spec.md"
    spec_path.write_text("# Task\n\nKeep project scope explicit.\n", encoding="utf-8")
    _create_loop(service, spec_path, startup_workdir)
    _create_loop(service, spec_path, other_workdir)
    startup_resolved = str(startup_workdir.resolve())
    other_resolved = str(other_workdir.resolve())

    app = build_app(service=service, startup_workdir=startup_resolved)
    with serve_app(app) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(f"{base_url}/", wait_until="domcontentloaded")
        page.wait_for_function(
            """workdir => document.querySelector('[data-testid="global-workdir-context"] code')?.textContent === workdir
              && document.querySelectorAll('[data-testid="loop-card"]').length === 1""",
            arg=startup_resolved,
            timeout=10_000,
        )

        page.get_by_test_id("global-project-scope-toggle").click()
        page.get_by_test_id("global-project-scope-workdir").fill(other_resolved)
        page.get_by_test_id("global-project-scope-submit").click()
        page.wait_for_function(
            """workdir => location.pathname === '/'
              && new URL(location.href).searchParams.get('workdir') === workdir
              && document.querySelector('[data-testid="global-workdir-context"] code')?.textContent === workdir
              && document.querySelectorAll('[data-testid="loop-card"]').length === 1""",
            arg=other_resolved,
            timeout=10_000,
        )
        assert other_resolved in page.get_by_test_id("loop-card").inner_text()

        page.get_by_test_id("global-project-scope-toggle").click()
        page.get_by_test_id("global-project-scope-all").click()
        page.wait_for_function(
            """() => location.pathname === '/'
              && new URL(location.href).searchParams.get('project_scope') === 'all'
              && document.querySelector('[data-testid="global-workdir-context"]')?.hidden
              && !document.querySelector('[data-project-scope-all-state]')?.hidden
              && document.querySelectorAll('[data-project-scope-option][aria-current="true"]').length === 1
              && document.querySelectorAll('[data-testid="loop-card"]').length === 2""",
            timeout=10_000,
        )

        page.get_by_test_id("nav-tutorial-link").click()
        page.wait_for_function(
            """() => location.pathname === '/fit-guide'
              && new URL(location.href).searchParams.get('project_scope') === 'all'
              && document.querySelector('[data-testid="global-workdir-context"]')?.hidden""",
            timeout=10_000,
        )
        _assert_no_horizontal_overflow(page)


def test_browser_global_project_scope_waits_for_active_web_conversation(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "active scope project"
    other_workdir = tmp_path / "blocked scope project"
    workdir.mkdir()
    other_workdir.mkdir()
    resolved_workdir = str(workdir.resolve())
    other_resolved = str(other_workdir.resolve())
    session = service.create_alignment_session(
        workdir=workdir,
        message="Keep the running conversation attached while project scope changes are considered.",
        start_immediately=False,
    )
    service.repository.update_alignment_session(session["id"], status="running")

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/loops/new/bundle?alignment_session_id={session['id']}", wait_until="domcontentloaded")
        page.wait_for_function(
            """([sessionId, workdir]) => new URL(location.href).searchParams.get('alignment_session_id') === sessionId
              && document.querySelector('[data-testid="alignment-workdir"]')?.value === workdir
              && document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === 'running'""",
            arg=[session["id"], resolved_workdir],
            timeout=10_000,
        )

        page.get_by_test_id("global-project-scope-toggle").click()
        page.get_by_test_id("global-project-scope-workdir").fill(other_resolved)
        page.get_by_test_id("global-project-scope-submit").click()
        page.wait_for_function(
            """sessionId => location.pathname === '/loops/new/bundle'
              && new URL(location.href).searchParams.get('alignment_session_id') === sessionId
              && document.querySelector('#alignment-error')?.textContent?.includes('switching target projects')""",
            arg=session["id"],
            timeout=10_000,
        )
        assert page.get_by_test_id("alignment-workdir").input_value() == resolved_workdir


def test_browser_same_agent_scope_switch_stays_on_setup_and_keeps_host_in_first_view(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "same agent scoped setup"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(f"{base_url}/same-agent?project_scope=all", wait_until="domcontentloaded")
        page.get_by_test_id("global-project-scope-toggle").click()
        page.get_by_test_id("global-project-scope-workdir").fill(resolved_workdir)
        page.get_by_test_id("global-project-scope-submit").click()
        page.wait_for_function(
            """workdir => location.pathname === '/same-agent'
              && new URL(location.href).searchParams.get('workdir') === workdir
              && document.querySelector('[data-testid="agent-adapter-workdir"]')?.value === workdir
              && document.querySelector('[data-testid="agent-host-selector"]')?.getBoundingClientRect().height > 0""",
            arg=resolved_workdir,
            timeout=10_000,
        )

        layout = page.evaluate(
            """() => {
              const rect = (testid) => document.querySelector(`[data-testid="${testid}"]`)?.getBoundingClientRect();
              const target = rect('agent-adapter-target');
              const host = rect('agent-host-selector');
              const panel = rect('agent-adapters-panel');
              const routes = rect('tools-route-actions');
              return {
                panelTop: panel?.top,
                sameSetupRow: Math.abs((target?.top || 0) - (host?.top || 0)) <= 24,
                hostInFirstView: host?.bottom <= window.innerHeight,
                routesAfterSetup: routes?.top >= panel?.bottom,
                overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth,
              };
            }"""
        )
        assert layout["sameSetupRow"] is True
        assert layout["hostInFirstView"] is True
        assert layout["routesAfterSetup"] is True
        assert layout["overflowX"] is False
        assert layout["panelTop"] < 300


def test_browser_web_compose_path_links_wait_for_pending_active_session(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "pending active compose path target"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())
    session = service.create_alignment_session(
        workdir=workdir,
        message="Keep pending restore attached before navigation.",
        start_immediately=False,
    )
    service.repository.update_alignment_session(session["id"], status="running")
    delayed_session_reads: list[str] = []

    def delay_session_restore(route) -> None:
        if f"/api/alignments/sessions/{session['id']}" in route.request.url and "/stream" not in route.request.url:
            delayed_session_reads.append(route.request.url)
            time.sleep(0.35)
        route.continue_()

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.route("**/api/alignments/sessions/**", delay_session_restore)
        page.goto(f"{base_url}/loops/new/bundle?alignment_session_id={session['id']}", wait_until="domcontentloaded")

        page.get_by_test_id("alignment-path-manual").click()
        page.wait_for_function(
            """([sessionId, workdir]) => document.querySelector('#alignment-error')?.textContent
              && new URL(location.href).searchParams.get("alignment_session_id") === sessionId
              && location.pathname === "/loops/new/bundle"
              && document.querySelector('[data-testid="alignment-workdir"]')?.value === workdir
              && document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === "running" """,
            arg=[session["id"], resolved_workdir],
            timeout=10_000,
        )
        preserved_state = page.evaluate(
            """() => ({
              path: location.pathname,
              sessionId: new URL(location.href).searchParams.get("alignment_session_id"),
              status: document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status,
              error: document.querySelector('#alignment-error')?.textContent || "",
            })"""
        )
        assert delayed_session_reads
        assert preserved_state == {
            "path": "/loops/new/bundle",
            "sessionId": session["id"],
            "status": "running",
            "error": "The Agent is running; stop the current conversation before switching composition paths.",
        }


def test_browser_global_compose_returns_to_same_target_active_session(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "global return active target"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())
    other_workdir = tmp_path / "other global return target"
    other_workdir.mkdir()
    other_resolved_workdir = str(other_workdir.resolve())
    session = service.create_alignment_session(
        workdir=workdir,
        message="Keep the active Web conversation recoverable from peer pages.",
        start_immediately=False,
    )
    service.repository.update_alignment_session(session["id"], status="running")

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/loops/new/bundle?alignment_session_id={session['id']}", wait_until="domcontentloaded")
        page.wait_for_function(
            """([sessionId, workdir]) => new URL(location.href).searchParams.get("alignment_session_id") === sessionId
              && document.querySelector('[data-testid="alignment-workdir"]')?.value === workdir
              && document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === "running" """,
            arg=[session["id"], resolved_workdir],
            timeout=10_000,
        )

        page.get_by_test_id("nav-loops-link").click()
        page.wait_for_function(
            """([sessionId, workdir]) => location.pathname === "/"
              && new URL(location.href).searchParams.get("workdir") === workdir
              && document.querySelector('[data-testid="home-active-loop"]')?.href.includes(`alignment_session_id=${sessionId}`)
              && document.querySelector('[data-testid="home-active-loop-attention-reason"]')?.dataset.attentionReasonKind === "alignment_active"
              && document.querySelector('[data-testid="home-active-loop-action"]')?.dataset.attentionActionKind === "resume_alignment_session" """,
            arg=[session["id"], resolved_workdir],
            timeout=10_000,
        )
        home_attention = page.evaluate(
            """() => ({
              href: new URL(document.querySelector('[data-testid="home-active-loop"]').href).pathname,
              sessionId: new URL(document.querySelector('[data-testid="home-active-loop"]').href).searchParams.get("alignment_session_id"),
              workdir: new URL(document.querySelector('[data-testid="home-active-loop"]').href).searchParams.get("workdir"),
              reason: document.querySelector('[data-testid="home-active-loop-attention-reason"]')?.dataset.attentionReasonKind,
              action: document.querySelector('[data-testid="home-active-loop-action"]')?.dataset.attentionActionKind,
              text: document.querySelector('[data-testid="home-active-loop"]')?.textContent || "",
            })"""
        )
        assert home_attention["href"] == "/loops/new/bundle"
        assert home_attention["sessionId"] == session["id"]
        assert home_attention["workdir"] == resolved_workdir
        assert home_attention["reason"] == "alignment_active"
        assert home_attention["action"] == "resume_alignment_session"
        assert "Keep the active Web conversation recoverable from peer pages." in home_attention["text"]

        page.goto(f"{base_url}/loops/new?workdir={quote(resolved_workdir)}", wait_until="domcontentloaded")
        page.wait_for_function(
            """workdir => location.pathname === "/loops/new"
              && new URL(location.href).searchParams.get("workdir") === workdir
              && document.querySelector('[data-testid="loop-create-existing-choice"]')?.dataset.existingWorkState === "available"
              && document.querySelector('[data-testid="loop-create-existing-attention-link"]') """,
            arg=resolved_workdir,
            timeout=10_000,
        )
        create_choice_existing = page.evaluate(
            """() => {
              const linkElement = document.querySelector('[data-testid="loop-create-existing-attention-link"]');
              const link = new URL(linkElement.href);
              return {
                state: document.querySelector('[data-testid="loop-create-existing-choice"]')?.dataset.existingWorkState,
                attentionPath: link.pathname,
                attentionSessionId: link.searchParams.get("alignment_session_id"),
                attentionWorkdir: link.searchParams.get("workdir"),
                attentionHash: link.hash,
                action: linkElement.dataset.existingActionKind,
                emptyVisible: Boolean(document.querySelector('[data-testid="loop-create-existing-empty-state"]')),
              };
            }"""
        )
        assert create_choice_existing == {
            "state": "available",
            "attentionPath": "/loops/new/bundle",
            "attentionSessionId": session["id"],
            "attentionWorkdir": resolved_workdir,
            "attentionHash": "",
            "action": "resume_alignment_session",
            "emptyVisible": False,
        }

        page.get_by_test_id("nav-tools-link").click()
        page.wait_for_function(
            """workdir => location.pathname === "/same-agent"
              && new URL(location.href).searchParams.get("workdir") === workdir
              && new URL(document.querySelector('[data-testid="nav-compose-link"]')?.href || location.href).searchParams.get("workdir") === workdir
              && !new URL(document.querySelector('[data-testid="nav-compose-link"]')?.href || location.href).searchParams.get("alignment_session_id") """,
            arg=resolved_workdir,
            timeout=10_000,
        )

        page.get_by_test_id("nav-compose-link").click()
        page.wait_for_function(
            """([sessionId, workdir]) => location.pathname === "/loops/new/bundle"
              && new URL(location.href).searchParams.get("alignment_session_id") === sessionId
              && document.querySelector('[data-testid="alignment-workdir"]')?.value === workdir
              && document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === "running" """,
            arg=[session["id"], resolved_workdir],
            timeout=10_000,
        )
        restored_state = page.evaluate(
            """() => ({
              path: location.pathname,
              sessionId: new URL(location.href).searchParams.get("alignment_session_id"),
              workdir: document.querySelector('[data-testid="alignment-workdir"]')?.value,
              status: document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status,
              localSession: localStorage.getItem("loopora:alignment-session:v1"),
            })"""
        )
        assert restored_state == {
            "path": "/loops/new/bundle",
            "sessionId": session["id"],
            "workdir": resolved_workdir,
            "status": "running",
            "localSession": session["id"],
        }

        page.goto(f"{base_url}/same-agent?workdir={quote(other_resolved_workdir)}", wait_until="domcontentloaded")
        page.wait_for_function(
            """workdir => location.pathname === "/same-agent"
              && new URL(location.href).searchParams.get("workdir") === workdir
              && new URL(document.querySelector('[data-testid="nav-compose-link"]')?.href || location.href).searchParams.get("workdir") === workdir """,
            arg=other_resolved_workdir,
            timeout=10_000,
        )
        page.get_by_test_id("nav-compose-link").click()
        page.wait_for_function(
            """workdir => location.pathname === "/loops/new"
              && new URL(location.href).searchParams.get("workdir") === workdir
              && !new URL(location.href).searchParams.get("alignment_session_id") """,
            arg=other_resolved_workdir,
            timeout=10_000,
        )
        fresh_target_state = page.evaluate(
            """() => ({
              path: location.pathname,
              sessionId: new URL(location.href).searchParams.get("alignment_session_id"),
              workdir: new URL(location.href).searchParams.get("workdir"),
              context: document.querySelector('[data-testid="global-workdir-context"] code')?.textContent || "",
              localSession: localStorage.getItem("loopora:alignment-session:v1"),
            })"""
        )
        assert fresh_target_state == {
            "path": "/loops/new",
            "sessionId": None,
            "workdir": other_resolved_workdir,
            "context": other_resolved_workdir,
            "localSession": session["id"],
        }


def test_browser_global_compose_rebinds_active_session_after_dynamic_target_change(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "dynamic active return target"
    workdir.mkdir()
    resolved_workdir = str(workdir.resolve())
    session = service.create_alignment_session(
        workdir=workdir,
        message="Return to this active Web conversation after choosing the target in-page.",
        start_immediately=False,
    )
    service.repository.update_alignment_session(session["id"], status="running")

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"{base_url}/loops/new/bundle?alignment_session_id={session['id']}", wait_until="domcontentloaded")
        page.wait_for_function(
            """([sessionId, workdir]) => new URL(location.href).searchParams.get("alignment_session_id") === sessionId
              && document.querySelector('[data-testid="alignment-workdir"]')?.value === workdir
              && localStorage.getItem("loopora:alignment-session:v1") === sessionId""",
            arg=[session["id"], resolved_workdir],
            timeout=10_000,
        )

        page.goto(f"{base_url}/same-agent", wait_until="domcontentloaded")
        page.wait_for_function(
            """() => location.pathname === "/same-agent"
              && !new URL(location.href).searchParams.get("workdir")
              && !new URL(document.querySelector('[data-testid="nav-compose-link"]')?.href || location.href).searchParams.get("workdir")""",
            timeout=10_000,
        )
        page.evaluate(
            """target => window.LooporaUI.syncWorkdirContext(target, {syncUrl: true, urlParam: "workdir"})""",
            resolved_workdir,
        )
        page.wait_for_function(
            """workdir => new URL(location.href).searchParams.get("workdir") === workdir
              && new URL(document.querySelector('[data-testid="nav-compose-link"]')?.href || location.href).searchParams.get("workdir") === workdir""",
            arg=resolved_workdir,
            timeout=10_000,
        )

        page.get_by_test_id("nav-compose-link").click()
        page.wait_for_function(
            """([sessionId, workdir]) => location.pathname === "/loops/new/bundle"
              && new URL(location.href).searchParams.get("alignment_session_id") === sessionId
              && document.querySelector('[data-testid="alignment-workdir"]')?.value === workdir
              && document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === "running" """,
            arg=[session["id"], resolved_workdir],
            timeout=10_000,
        )


def test_browser_tools_rejects_relative_agent_target_after_stale_blank_refresh(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    service = _service(tmp_path)
    relative_workdir = Path("relative-project")
    relative_workdir.mkdir()
    resolved_workdir = str(relative_workdir.resolve())

    def delay_blank_target_response(route) -> None:
        if "?" not in route.request.url:
            time.sleep(0.45)
        route.continue_()

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page()
        page.route("**/api/diagnostics/doctor**", delay_blank_target_response)
        page.route("**/api/agent-adapters**", delay_blank_target_response)

        page.goto(f"{base_url}/same-agent", wait_until="domcontentloaded")
        workdir_input = page.get_by_test_id("agent-adapter-workdir")
        workdir_input.wait_for(state="visible", timeout=10_000)
        workdir_input.fill(str(relative_workdir))
        raw_preference_values = page.evaluate(
            """() => Object.entries(window.localStorage)
              .filter(([key]) => key.startsWith("loopora:tools:agent-adapter-workdir"))
              .map(([, value]) => value)"""
        )
        assert str(relative_workdir) not in raw_preference_values

        page.wait_for_function(
            """(relative) => document.querySelector('[data-testid="agent-adapter-workdir"]')?.value === relative
              && !new URL(location.href).searchParams.get("workdir")
              && document.querySelector('[data-testid="global-workdir-context"]')?.hidden""",
            arg=str(relative_workdir),
            timeout=10_000,
        )
        relative_context = page.evaluate(
            """() => {
              const nav = new URL(document.querySelector('[data-testid="nav-compose-link"]').href);
              const fit = new URL(document.querySelector('[data-testid="tools-fit-guide-link"]').href);
              return {
                currentUrl: new URL(location.href).searchParams.get("workdir"),
                navWorkdir: nav.searchParams.get("workdir"),
                fitWorkdir: fit.searchParams.get("workdir"),
                preferences: Object.entries(window.localStorage)
                  .filter(([key]) => key.startsWith("loopora:tools:agent-adapter-workdir"))
                  .map(([, value]) => value),
              };
            }"""
        )
        assert relative_context == {
            "currentUrl": None,
            "navWorkdir": None,
            "fitWorkdir": None,
            "preferences": [],
        }

        workdir_input.fill(resolved_workdir)
        page.wait_for_function(
            """(expected) => document.querySelector('[data-testid="agent-adapter-workdir"]')?.value === expected
              && new URL(location.href).searchParams.get("workdir") === expected
              && Object.entries(window.localStorage)
                .filter(([key]) => key.startsWith("loopora:tools:agent-adapter-workdir"))
                .some(([, value]) => value === expected)""",
            arg=resolved_workdir,
            timeout=10_000,
        )
        preference_values = page.evaluate(
            """() => Object.entries(window.localStorage)
              .filter(([key]) => key.startsWith("loopora:tools:agent-adapter-workdir"))
              .map(([, value]) => value)"""
        )
        link_context = page.evaluate(
            """() => {
              const nav = new URL(document.querySelector('[data-testid="nav-compose-link"]').href);
              const fit = new URL(document.querySelector('[data-testid="tools-fit-guide-link"]').href);
              return {
                currentUrl: new URL(location.href).searchParams.get("workdir"),
                navWorkdir: nav.searchParams.get("workdir"),
                fitWorkdir: fit.searchParams.get("workdir"),
                fitPath: fit.pathname,
                fitHash: fit.hash,
              };
            }"""
        )
        assert resolved_workdir in preference_values
        assert link_context == {
            "currentUrl": resolved_workdir,
            "navWorkdir": resolved_workdir,
            "fitWorkdir": resolved_workdir,
            "fitPath": "/fit-guide",
            "fitHash": "#tutorial-decision-tree-panel",
        }

        workdir_input.fill("")
        page.wait_for_function(
            """() => !new URL(location.href).searchParams.get("workdir")
              && document.querySelector('[data-testid="global-workdir-context"]')?.hidden""",
            timeout=10_000,
        )
        cleared_context = page.evaluate(
            """() => {
              const nav = new URL(document.querySelector('[data-testid="nav-compose-link"]').href);
              const fit = new URL(document.querySelector('[data-testid="tools-fit-guide-link"]').href);
              const context = document.querySelector('[data-testid="global-workdir-context"]');
              return {
                currentUrl: new URL(location.href).searchParams.get("workdir"),
                navWorkdir: nav.searchParams.get("workdir"),
                fitWorkdir: fit.searchParams.get("workdir"),
                fitPath: fit.pathname,
                fitHash: fit.hash,
                contextHidden: context?.hidden,
                preferences: Object.entries(window.localStorage)
                  .filter(([key]) => key.startsWith("loopora:tools:agent-adapter-workdir"))
                  .map(([, value]) => value),
              };
            }"""
        )
        assert cleared_context == {
            "currentUrl": None,
            "navWorkdir": None,
            "fitWorkdir": None,
            "fitPath": "/fit-guide",
            "fitHash": "#tutorial-decision-tree-panel",
            "contextHidden": True,
            "preferences": [],
        }


def test_browser_tools_freeform_agent_target_replaces_stale_context_until_resolved(tmp_path: Path) -> None:
    service = _service(tmp_path)
    old_workdir = tmp_path / "old target"
    new_workdir = tmp_path / "new target"
    old_workdir.mkdir()
    new_workdir.mkdir()
    resolved_old = str(old_workdir.resolve())
    resolved_new = str(new_workdir.resolve())
    encoded_new = quote(resolved_new, safe="")

    def delay_new_target_response(route) -> None:
        if encoded_new in route.request.url:
            time.sleep(0.45)
        route.continue_()

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page()
        page.route("**/api/diagnostics/doctor**", delay_new_target_response)
        page.route("**/api/agent-adapters**", delay_new_target_response)

        page.goto(f"{base_url}/same-agent?workdir={quote(resolved_old, safe='')}", wait_until="domcontentloaded")
        page.wait_for_function(
            """(oldTarget) => document.querySelector('[data-testid="agent-adapter-workdir"]')?.value === oldTarget
              && document.querySelector('[data-testid="global-workdir-context"] code')?.textContent === oldTarget
              && new URL(document.querySelector('[data-testid="nav-compose-link"]').href).searchParams.get("workdir") === oldTarget""",
            arg=resolved_old,
            timeout=10_000,
        )

        page.get_by_test_id("agent-adapter-workdir").fill(resolved_new)
        page.wait_for_function(
            """(newTarget) => new URL(location.href).searchParams.get("workdir") === newTarget
              && document.querySelector('[data-testid="global-workdir-context"] code')?.textContent === newTarget
              && new URL(document.querySelector('[data-testid="nav-compose-link"]').href).searchParams.get("workdir") === newTarget
              && new URL(document.querySelector('[data-testid="tools-fit-guide-link"]').href).searchParams.get("workdir") === newTarget""",
            arg=resolved_new,
            timeout=10_000,
        )
        pending_preferences = page.evaluate(
            """() => Object.entries(window.localStorage)
              .filter(([key]) => key.startsWith("loopora:tools:agent-adapter-workdir"))
              .map(([, value]) => value)"""
        )
        assert resolved_old not in pending_preferences
        assert resolved_new not in pending_preferences

        page.wait_for_function(
            """(newTarget) => document.querySelector('[data-testid="agent-adapter-workdir"]')?.value === newTarget
              && document.querySelector('[data-testid="global-workdir-context"] code')?.textContent === newTarget
              && new URL(location.href).searchParams.get("workdir") === newTarget
              && new URL(document.querySelector('[data-testid="nav-compose-link"]').href).searchParams.get("workdir") === newTarget""",
            arg=resolved_new,
            timeout=10_000,
        )


def test_browser_agent_native_handoff_stays_on_loopora_loop_path(tmp_path: Path) -> None:
    service = _service(tmp_path)
    workdir = tmp_path / "agent-native-workdir"
    workdir.mkdir()
    (workdir / "progress.md").write_text("# Progress\n\nInitial state.\n", encoding="utf-8")
    bundle_file = tmp_path / "agent-bundle.yml"
    bundle_file.write_text(FakeCodexExecutor._alignment_bundle_yaml(str(workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=workdir,
            message=(
                "Ship the focused starter experience. The primary user flow must work end to end, "
                "use project-owned evidence, avoid happy-path claim only, keep a clear handoff, "
                "and let GateKeeper reject weak proof."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=workdir, entry_source="codex_project_skill", execute_async=False)

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page()
        page.goto(f"{base_url}/loops/{started['run']['loop_id']}", wait_until="domcontentloaded")
        page.get_by_test_id("loop-agent-entry-copy-command").wait_for(state="visible", timeout=10_000)
        assert "/loopora-run" in page.text_content("body")
        assert page.locator('form[action^="/api/loops/"]').count() == 0

        page.goto(f"{base_url}/runs/{started['run']['id']}", wait_until="domcontentloaded")
        page.get_by_test_id("agent-handoff-copy-submit").wait_for(state="visible", timeout=10_000)
        assert "/loopora-run" in page.text_content("body")


def _create_browser_agreement_ready_session(
    tmp_path: Path,
    *,
    workdir_name: str,
) -> tuple[LooporaService, dict]:
    service = _service(
        tmp_path,
        executor_factory=lambda: FakeCodexExecutor(scenario="success", role_delay=1.5),
    )
    workdir = tmp_path / workdir_name
    workdir.mkdir()
    created = service.create_alignment_session(
        workdir=workdir,
        message=(
            "Build a focused evidence-backed starter experience. Verify the primary journey end to end, "
            "reject happy-path-only proof, and keep unresolved evidence gaps visible."
        ),
        start_immediately=False,
    )
    service.start_alignment_session_async(created["id"])
    deadline = time.time() + 10
    agreement_session = service.get_alignment_session(created["id"])
    while agreement_session["status"] != "waiting_user" and time.time() < deadline:
        time.sleep(0.05)
        agreement_session = service.get_alignment_session(created["id"])
    assert agreement_session["status"] == "waiting_user"
    assert agreement_session["alignment_stage"] == "agreement_ready"
    return service, created


def _assert_ready_decision_surface(page) -> None:
    state = page.evaluate(
        """() => {
          const scroll = document.querySelector('#alignment-scroll-region');
          const header = document.querySelector('[data-testid="alignment-ready-preview"] .alignment-artifact-head');
          const save = document.querySelector('[data-testid="alignment-import-save-button"]');
          const run = document.querySelector('[data-testid="alignment-import-run-button"]');
          const scrollRect = scroll.getBoundingClientRect();
          const headerRect = header.getBoundingClientRect();
          const saveRect = save.getBoundingClientRect();
          const runRect = run.getBoundingClientRect();
          return {
            activeTab: document.querySelector('[data-preview-tab][aria-selected="true"]')?.dataset.previewTab,
            reviewHidden: document.querySelector('[data-preview-panel="review"]')?.hidden,
            specHidden: document.querySelector('[data-preview-panel="spec"]')?.hidden,
            headerInView: headerRect.top >= scrollRect.top - 24 && headerRect.top < scrollRect.bottom,
            saveInView: saveRect.top >= scrollRect.top && saveRect.bottom <= scrollRect.bottom,
            runInView: runRect.top >= scrollRect.top && runRect.bottom <= scrollRect.bottom,
            composerDisplay: getComputedStyle(document.querySelector('.alignment-composer-box')).display,
            saveDescription: document.querySelector('#alignment-ready-save-description')?.textContent.trim(),
            runDescription: document.querySelector('#alignment-ready-run-description')?.textContent.trim(),
          };
        }"""
    )
    assert state["activeTab"] == "review"
    assert state["reviewHidden"] is False
    assert state["specHidden"] is True
    assert state["headerInView"] is True
    assert state["saveInView"] is True
    assert state["runInView"] is True
    assert state["composerDisplay"] == "none"
    assert "Does not start a Run" in state["saveDescription"]
    assert "first Web Run immediately" in state["runDescription"]


def test_browser_agreement_ready_opens_on_reviewable_judgment_boundary(tmp_path: Path) -> None:
    service, created = _create_browser_agreement_ready_session(
        tmp_path,
        workdir_name="agreement-review-workdir",
    )

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        url = f"{base_url}/loops/new/bundle?alignment_session_id={created['id']}"
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(url, wait_until="domcontentloaded")
        review = page.get_by_test_id("alignment-agreement-review")
        review.wait_for(state="visible", timeout=10_000)
        desktop_state = page.evaluate(
            """() => {
              const scroll = document.querySelector('#alignment-scroll-region');
              const review = document.querySelector('[data-testid="alignment-agreement-review"]');
              const options = [...document.querySelectorAll('[data-testid="alignment-decision-option"]')];
              const scrollRect = scroll.getBoundingClientRect();
              const reviewRect = review.getBoundingClientRect();
              return {
                reviewOffset: reviewRect.top - scrollRect.top,
                optionCount: options.length,
                optionsInView: options.every((option) => option.getBoundingClientRect().bottom <= scrollRect.bottom + 1),
                detailsOpen: document.querySelector('[data-testid="alignment-agreement-details"]')?.open,
                overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth
                  || scroll.scrollWidth > scroll.clientWidth,
              };
            }"""
        )
        assert 0 <= desktop_state["reviewOffset"] <= 16
        assert desktop_state["optionCount"] == 2
        assert desktop_state["optionsInView"] is True
        assert desktop_state["detailsOpen"] is False
        assert desktop_state["overflowX"] is False
        key_judgments = page.get_by_test_id("alignment-agreement-key-judgments")
        full_agreement = page.get_by_test_id("alignment-agreement-details")
        assert key_judgments.locator('[data-agreement-field="success_surface"]').count() == 1
        assert key_judgments.locator('[data-agreement-field="fake_done_risks"]').count() == 1
        assert key_judgments.locator('[data-agreement-field="evidence_preferences"]').count() == 0
        assert full_agreement.locator('[data-agreement-field="evidence_preferences"]').count() == 1
        assert full_agreement.locator('[data-agreement-field="judgment_tradeoffs"]').count() == 1

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(url, wait_until="domcontentloaded")
        mobile.get_by_test_id("alignment-agreement-review").wait_for(state="visible", timeout=10_000)
        mobile.get_by_test_id("alignment-decision-option").first.scroll_into_view_if_needed()
        assert mobile.get_by_test_id("alignment-decision-option").first.is_visible()
        mobile.get_by_test_id("alignment-agreement-details").locator("summary").click()
        assert mobile.locator('[data-agreement-field="local_governance"]').is_visible()
        assert (
            mobile.evaluate(
                """() => document.documentElement.scrollWidth <= document.documentElement.clientWidth
              && document.querySelector('#alignment-scroll-region').scrollWidth
                <= document.querySelector('#alignment-scroll-region').clientWidth"""
            )
            is True
        )


def test_browser_confirmed_agreement_stays_visible_through_ready_and_repair(tmp_path: Path) -> None:
    service, created = _create_browser_agreement_ready_session(
        tmp_path,
        workdir_name="agreement-transition-workdir",
    )

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        url = f"{base_url}/loops/new/bundle?alignment_session_id={created['id']}"
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(url, wait_until="domcontentloaded")
        page.get_by_test_id("alignment-agreement-review").wait_for(state="visible", timeout=10_000)
        page.locator('[data-testid="alignment-decision-option"][data-option-id="confirm_agreement"]').click()
        handoff = page.get_by_test_id("alignment-agreement-handoff")
        handoff.wait_for(state="visible", timeout=10_000)
        compiling_state = page.evaluate(
            """() => {
              const scroll = document.querySelector('#alignment-scroll-region');
              const handoff = document.querySelector('[data-testid="alignment-agreement-handoff"]');
              const scrollRect = scroll.getBoundingClientRect();
              const handoffRect = handoff.getBoundingClientRect();
              return {
                status: document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status,
                mode: handoff.dataset.agreementMode,
                offset: handoffRect.top - scrollRect.top,
                staleOptions: document.querySelectorAll('[data-testid="alignment-decision-option"]').length,
                genericWorkingCards: document.querySelectorAll('[data-testid="alignment-working-card"]').length,
                rawAgreementVisible: [...document.querySelectorAll('.alignment-message > p')]
                  .some((item) => item.textContent.includes('Please confirm this working agreement')),
              };
            }"""
        )
        assert compiling_state["status"] in {"running", "validating", "repairing"}
        assert compiling_state["mode"] == "compiling"
        assert 0 <= compiling_state["offset"] <= 16
        assert compiling_state["staleOptions"] == 0
        assert compiling_state["genericWorkingCards"] == 0
        assert compiling_state["rawAgreementVisible"] is False

        page.wait_for_function(
            """() => document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === 'ready'
              && document.querySelector('[data-testid="alignment-agreement-handoff"]')?.dataset.agreementMode === 'compiled'
              && !document.querySelector('#alignment-ready-preview')?.hidden""",
            timeout=15_000,
        )
        assert page.get_by_test_id("alignment-review-gate").is_visible()
        assert page.get_by_test_id("alignment-decision-option").count() == 0

        service.repository.update_alignment_session(
            created["id"],
            status="failed",
            alignment_stage="compiling",
            error_message="The candidate plan needs repair before READY.",
        )
        page.reload(wait_until="domcontentloaded")
        failed_handoff = page.get_by_test_id("alignment-agreement-handoff")
        failed_handoff.wait_for(state="visible", timeout=10_000)
        assert failed_handoff.get_attribute("data-agreement-mode") == "repair"
        assert page.get_by_test_id("alignment-repair-failure-button").is_visible()
        assert page.get_by_test_id("alignment-ready-actions").is_hidden()
        assert page.get_by_test_id("alignment-message-input").is_visible()
        assert page.get_by_test_id("alignment-preview-tab-review").get_attribute("aria-selected") == "true"
        assert page.get_by_test_id("alignment-decision-option").count() == 0
        assert page.locator(".alignment-message > p").filter(has_text="Please confirm this working agreement").count() == 0


def test_browser_web_conversation_blocks_missing_executor_before_session_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workdir = tmp_path / "executor-readiness-workdir"
    workdir.mkdir()
    service = _service(tmp_path, executor_factory=RealCodexExecutor)
    monkeypatch.setattr(
        executor_readiness_module.shutil,
        "which",
        lambda command: "/usr/local/bin/claude" if command == "claude" else None,
    )

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(f"{base_url}/loops/new/bundle?alignment_workdir={quote(str(workdir.resolve()))}")
        page.wait_for_function(
            """() => document.querySelector('[data-testid="alignment-executor-readiness"]')
              ?.dataset.readinessKind === 'executable_not_found'""",
            timeout=10_000,
        )
        assert page.get_by_test_id("alignment-send-button").is_disabled()
        assert "Claude Code" in str(page.get_by_test_id("alignment-executor-readiness").text_content())

        page.get_by_test_id("alignment-task-goal-input").fill("Ship callback retries with evidence for idempotency and rollback.")
        page.locator("#alignment-start-form").evaluate("form => form.requestSubmit()")
        page.get_by_test_id("alignment-tools-menu").wait_for(state="visible", timeout=10_000)
        assert "not available" in str(page.locator("#alignment-error").text_content())
        assert service.list_alignment_sessions() == []

        service.executor_factory = lambda: FakeCodexExecutor(scenario="success")
        page.get_by_test_id("alignment-executor-kind").select_option("claude")
        page.wait_for_function(
            """() => document.querySelector('[data-testid="alignment-executor-readiness"]')
              ?.dataset.readinessKind === 'managed_runtime'
              && !document.querySelector('[data-testid="alignment-send-button"]')?.disabled""",
            timeout=10_000,
        )
        page.get_by_test_id("alignment-send-button").click()
        page.wait_for_function(
            """() => document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === 'waiting_user'""",
            timeout=10_000,
        )
        assert service.list_alignment_sessions()[0]["executor_kind"] == "claude"


def test_browser_failed_generation_preserves_task_and_retries_without_fake_plan_repair(tmp_path: Path) -> None:
    class FailBeforePlanExecutor(FakeCodexExecutor):
        def execute(self, request, emit_event, should_stop, set_child_pid):
            del request, emit_event, should_stop, set_child_pid
            raise OSError("simulated missing local executor")

    workdir = tmp_path / "failed-generation-workdir"
    workdir.mkdir()
    service = _service(tmp_path, executor_factory=FailBeforePlanExecutor)
    task = "Migrate payment callbacks and prove idempotency, retries, and rollback."

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(f"{base_url}/loops/new/bundle?alignment_workdir={quote(str(workdir.resolve()))}")
        page.get_by_test_id("alignment-task-goal-input").fill(task)
        page.get_by_test_id("alignment-send-button").click()
        page.wait_for_function(
            """() => document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === 'failed'
              && document.querySelector('[data-testid="alignment-retry-generation-button"]')?.offsetParent
              && document.querySelector('[data-testid="alignment-ready-preview"]')?.hidden === true""",
            timeout=10_000,
        )

        failed_state = page.evaluate(
            """() => ({
              text: document.querySelector('[data-testid="alignment-chat"]')?.textContent || '',
              candidateRepair: Boolean(document.querySelector('[data-testid="alignment-repair-failure-button"]')),
              executorKind: document.querySelector('[data-testid="alignment-executor-kind"]')?.value,
            })"""
        )
        assert "did not produce a Plan File" in failed_state["text"]
        assert "Fix the Plan File" not in failed_state["text"]
        assert failed_state["candidateRepair"] is False
        assert failed_state["executorKind"] == "codex"

        page.goto(f"{base_url}/?workdir={quote(str(workdir.resolve()))}")
        assert page.get_by_test_id("home-active-loop-attention-reason").get_attribute("data-attention-reason-kind") == "alignment_generation_failed"
        assert page.get_by_test_id("home-active-loop-action").get_attribute("data-attention-action-kind") == "retry_alignment_generation"

        page.get_by_test_id("home-active-loop").click()
        page.get_by_test_id("alignment-retry-generation-button").wait_for(state="visible")
        service.executor_factory = lambda: FakeCodexExecutor(scenario="success")
        page.get_by_test_id("alignment-retry-generation-button").click()
        page.wait_for_function(
            """() => document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === 'waiting_user'""",
            timeout=10_000,
        )

        session_id = parse_qs(urlparse(page.url).query)["alignment_session_id"][0]
        session = service.get_alignment_session(session_id)
        assert [entry["content"] for entry in session["transcript"] if entry["role"] == "user"] == [task]
        assert "alignment_generation_retry_requested" in {event["event_type"] for event in service.list_alignment_events(session_id)}


def test_browser_ready_review_can_save_a_loop_without_starting_a_run(tmp_path: Path) -> None:
    service, created = _create_browser_agreement_ready_session(
        tmp_path,
        workdir_name="ready-save-only-workdir",
    )

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(
            f"{base_url}/loops/new/bundle?alignment_session_id={created['id']}",
            wait_until="domcontentloaded",
        )
        page.locator('[data-testid="alignment-decision-option"][data-option-id="confirm_agreement"]').click()
        page.wait_for_function(
            """() => document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === 'ready'
              && !document.querySelector('[data-testid="alignment-import-save-button"]')?.hidden""",
            timeout=15_000,
        )
        save_button = page.get_by_test_id("alignment-import-save-button")
        run_button = page.get_by_test_id("alignment-import-run-button")
        assert save_button.is_disabled()
        assert run_button.is_disabled()
        _assert_ready_decision_surface(page)

        page.get_by_test_id("alignment-preview-tab-spec").click()
        assert page.get_by_test_id("alignment-spec-preview").is_visible()
        page.get_by_test_id("alignment-source-sync-button").click()
        page.wait_for_function(
            """() => document.querySelector('[data-preview-tab="spec"]')?.getAttribute('aria-selected') === 'true'
              && !document.querySelector('[data-preview-panel="spec"]')?.hidden""",
            timeout=10_000,
        )
        page.get_by_test_id("alignment-preview-tab-spec").press("Home")
        assert page.get_by_test_id("alignment-preview-tab-review").get_attribute("aria-selected") == "true"

        page.get_by_test_id("alignment-revise-preview-button").click()
        assert page.get_by_test_id("alignment-revise-preview-button").get_attribute("aria-expanded") == "true"
        assert page.get_by_test_id("alignment-message-input").is_visible()
        assert "revise this Loop preview" in page.get_by_test_id("alignment-message-input").input_value()
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function(
            """() => document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === 'ready'
              && document.querySelector('.alignment-composer-box')
              && getComputedStyle(document.querySelector('.alignment-composer-box')).display === 'none'""",
            timeout=10_000,
        )

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(page.url, wait_until="domcontentloaded")
        mobile.wait_for_function(
            """() => document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === 'ready'
              && !document.querySelector('[data-testid="alignment-ready-actions"]')?.hidden""",
            timeout=10_000,
        )
        mobile_save = mobile.get_by_test_id("alignment-import-save-button")
        mobile_run = mobile.get_by_test_id("alignment-import-run-button")
        mobile_state = mobile.evaluate(
            """() => {
              const scroll = document.querySelector('#alignment-scroll-region');
              const actions = document.querySelector('[data-testid="alignment-ready-actions"]');
              const scrollRect = scroll.getBoundingClientRect();
              const actionRect = actions.getBoundingClientRect();
              return {
                activeTab: document.querySelector('[data-preview-tab][aria-selected="true"]')?.dataset.previewTab,
                sidebarDisplay: getComputedStyle(document.querySelector('[data-testid="alignment-history-panel"]')).display,
                composerDisplay: getComputedStyle(document.querySelector('.alignment-composer-box')).display,
                actionsInDecisionViewport: actionRect.top < scrollRect.bottom && actionRect.bottom > scrollRect.top,
              };
            }"""
        )
        assert mobile_state == {
            "activeTab": "review",
            "sidebarDisplay": "none",
            "composerDisplay": "none",
            "actionsInDecisionViewport": True,
        }
        mobile_save.scroll_into_view_if_needed()
        assert mobile_save.is_visible()
        assert mobile_run.is_visible()
        assert (
            mobile.evaluate(
                """() => document.documentElement.scrollWidth <= document.documentElement.clientWidth
              && document.querySelector('#alignment-scroll-region').scrollWidth
                <= document.querySelector('#alignment-scroll-region').clientWidth"""
            )
            is True
        )
        mobile.get_by_test_id("alignment-revise-preview-button").click()
        assert mobile.get_by_test_id("alignment-message-input").is_visible()
        assert (
            mobile.evaluate(
                """() => getComputedStyle(
              document.querySelector('[data-testid="alignment-history-panel"]')
            ).display"""
            )
            == "grid"
        )

        page.get_by_test_id("alignment-review-confirm-checkbox").check()
        assert save_button.is_enabled()
        assert run_button.is_enabled()
        save_button.click()
        page.wait_for_url("**/loops/*", timeout=10_000)

        loop_id = urlparse(page.url).path.rsplit("/", 1)[-1]
        session = service.get_alignment_session(created["id"])
        loop = service.get_loop(loop_id)
        assert session["status"] == "imported"
        assert session["linked_loop_id"] == loop_id
        assert session["linked_run_id"] == ""
        assert loop["runs"] == []
        assert page.get_by_test_id("loop-history-empty-start-run-button").is_visible()


def test_browser_agent_entry_ready_review_keeps_run_handoff_in_same_agent(tmp_path: Path) -> None:
    service, created = _create_browser_agreement_ready_session(
        tmp_path,
        workdir_name="ready-agent-entry-workdir",
    )

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(
            f"{base_url}/loops/new/bundle?alignment_session_id={created['id']}",
            wait_until="domcontentloaded",
        )
        page.locator('[data-testid="alignment-decision-option"][data-option-id="confirm_agreement"]').click()
        page.wait_for_function(
            """() => document.querySelector('[data-testid="alignment-status-pill"]')?.dataset.status === 'ready'
              && !document.querySelector('[data-testid="alignment-ready-actions"]')?.hidden""",
            timeout=15_000,
        )

        session = service.get_alignment_session(created["id"])
        bundle_path = session["bundle_path"]
        service.repository.append_alignment_event(
            created["id"],
            "agent_candidate_received",
            {
                "candidate_origin": "agent_entry",
                "requires_web_alignment": True,
                "adapter": "codex",
                "entry_source": "codex_project_skill",
                "host_context_id": "thread-ready-review",
                "source_path": bundle_path,
                "has_candidate_yaml": True,
                "candidate_sha256": "candidate-sha",
                "candidate_bytes": 42,
            },
        )
        service.repository.append_alignment_event(
            created["id"],
            "agent_candidate_ready_content",
            {
                "candidate_origin": "agent_entry",
                "ready_candidate_sha256": "ready-sha",
                "ready_candidate_bytes": 84,
            },
        )
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function(
            """() => document.querySelector('[data-testid="alignment-ready-preview"]')?.dataset.launchMode === 'agent-entry'
              && !document.querySelector('[data-testid="alignment-ready-actions"]')?.hidden""",
            timeout=10_000,
        )

        assert page.get_by_test_id("alignment-ready-save-action").is_hidden()
        assert page.get_by_test_id("alignment-import-save-button").is_hidden()
        assert page.get_by_test_id("alignment-ready-run-action").is_visible()
        assert page.get_by_test_id("alignment-review-gate").is_hidden()
        assert "Continue in the same Agent" in page.locator("#alignment-ready-run-title").text_content()
        assert "Web will not start a Run" in page.locator("#alignment-ready-run-description").text_content()
        assert "/loopora-run" in page.get_by_test_id("alignment-import-run-button").text_content()
        assert page.get_by_test_id("alignment-preview-tab-review").get_attribute("aria-selected") == "true"


def _run_phase_dom_state(page) -> dict:
    return page.evaluate(
        """() => {
          const grid = document.querySelector('.run-judgment-grid');
          const progress = document.querySelector('[data-testid="run-progress-panel"]');
          const takeaways = document.querySelector('[data-testid="run-takeaway-panel"]');
          const evidence = document.querySelector('[data-testid="takeaway-evidence-strip"]');
          const decision = document.querySelector('[data-testid="run-result-decision"]');
          const labels = [...document.querySelectorAll('.takeaway-evidence-label')].map((node) => node.textContent.trim());
          return {
            phase: grid?.dataset.runPhase,
            progressOpen: progress?.open,
            progressBeforeEvidence: progress?.getBoundingClientRect().top < takeaways?.getBoundingClientRect().top,
            outcome: document.querySelector('#takeaway-outcome-title')?.textContent.trim(),
            labels,
            improveActions: document.querySelectorAll('[data-testid="run-improve-chat-button"]').length,
            resultDecisionState: decision?.dataset.resultDecisionState || "",
            decisionAfterEvidence: decision && evidence
              ? decision.getBoundingClientRect().top >= evidence.getBoundingClientRect().bottom
              : null,
            heroResultActions: document.querySelectorAll(
              '.hero-run-detail [data-testid="run-accept-result-button"], '
              + '.hero-run-detail [data-testid="run-rerun-button"], '
              + '.hero-run-detail [data-testid="run-improve-chat-button"]'
            ).length,
            exportMenu: Boolean(document.querySelector('[data-testid="run-export-menu"]')),
            takeawayInViewport: takeaways?.getBoundingClientRect().top < window.innerHeight,
            overflowX: document.documentElement.scrollWidth > document.documentElement.clientWidth,
          };
        }"""
    )


def _assert_active_run_decision_state(page) -> None:
    state = _run_phase_dom_state(page)
    assert state["phase"] == "active"
    assert state["progressOpen"] is True
    assert state["progressBeforeEvidence"] is True
    assert state["outcome"] in {"等待证据收束", "Evidence pending"}
    assert any(label in {"必需证据", "Required evidence"} for label in state["labels"])
    assert any(label in {"建议跟进", "Advisory follow-up"} for label in state["labels"])
    assert state["improveActions"] == 0
    assert state["resultDecisionState"] == ""
    assert state["decisionAfterEvidence"] is None
    assert state["heroResultActions"] == 0
    assert state["exportMenu"] is True
    assert state["overflowX"] is False


def _assert_passing_run_decision_state(page) -> None:
    state = _run_phase_dom_state(page)
    assert state["phase"] == "terminal"
    assert state["progressBeforeEvidence"] is False
    assert state["outcome"] not in {"等待证据收束", "Evidence pending"}
    assert state["improveActions"] == 1
    assert state["resultDecisionState"] == "passing"
    assert state["decisionAfterEvidence"] is True
    assert state["heroResultActions"] == 0
    assert state["takeawayInViewport"] is True
    assert any(label in {"必需依据", "Required basis"} for label in state["labels"])
    assert any(label in {"建议跟进", "Advisory follow-up"} for label in state["labels"])
    assert any(label in {"证据来源", "Evidence sources"} for label in state["labels"])
    assert not any(label in {"证明强度", "Proof strength"} for label in state["labels"])
    assert state["overflowX"] is False


def _assert_run_export_menu(page) -> None:
    page.get_by_test_id("run-export-menu").locator("summary").click()
    state = page.evaluate(
        """() => {
          const menu = document.querySelector('.run-export-menu-actions');
          const rect = menu.getBoundingClientRect();
          return {
            open: document.querySelector('[data-testid="run-export-menu"]')?.open,
            display: getComputedStyle(menu).display,
            insideViewport: rect.left >= 0 && rect.right <= window.innerWidth,
          };
        }"""
    )
    assert state == {"open": True, "display": "grid", "insideViewport": True}


def _assert_unresolved_run_decision(page, service, run_id: str) -> None:
    service.repository.update_run(
        run_id,
        task_verdict={
            "status": "insufficient_evidence",
            "source": "gatekeeper",
            "summary": "Required evidence remains unproven.",
        },
    )
    page.reload(wait_until="domcontentloaded")
    state = _run_phase_dom_state(page)
    assert state["resultDecisionState"] == "unresolved"
    assert state["improveActions"] == 1
    assert state["heroResultActions"] == 0
    assert page.get_by_test_id("run-improve-chat-button").get_attribute("class") == "primary-button"
    assert page.get_by_test_id("run-accept-result-button").get_attribute("class") == "secondary-button"


def _assert_recorded_run_decision(page) -> None:
    state = _run_phase_dom_state(page)
    assert state["resultDecisionState"] == "recorded"
    assert state["heroResultActions"] == 0
    assert page.get_by_test_id("run-result-decision").get_by_test_id("run-accepted-result-state").is_visible()


def _assert_recorded_loop_advisory_posture(page) -> None:
    recorded_state = page.get_by_test_id("loop-recorded-result-state")
    assert recorded_state.is_visible()
    assert recorded_state.get_by_test_id("loop-recorded-required-basis").is_visible()
    assert recorded_state.get_by_test_id("loop-recorded-advisory-summary").is_visible()
    assert recorded_state.get_by_test_id("loop-open-recorded-advisory-link").is_visible()
    advisory_button = recorded_state.get_by_test_id("loop-start-run-button")
    assert advisory_button.get_attribute("data-recorded-follow-up") == "advisory"
    assert advisory_button.get_attribute("class") == "secondary-button"
    assert page.get_by_test_id("loop-primary-actions").count() == 0


def _start_recorded_advisory_follow_up(page, service, *, run_id: str, advisory_open: int) -> str:
    current_url = urlparse(page.url)
    page.goto(f"{current_url.scheme}://{current_url.netloc}/runs/{run_id}", wait_until="domcontentloaded")
    page.get_by_test_id("run-recorded-advisory-rerun-button").click()
    page.wait_for_url(lambda url: f"/runs/{run_id}" not in url, timeout=10_000)
    page.get_by_test_id("run-continuation-state").wait_for(state="visible", timeout=10_000)
    continued_run_id = urlparse(page.url).path.rsplit("/", 1)[-1]
    continuation = service.run_continuation_state(continued_run_id)
    assert continuation["reason"] == "recorded_advisory_follow_up"
    assert continuation["previous_run_id"] == run_id
    assert continuation["focus_kind"] == "advisory"
    assert continuation["focus_target_count"] == advisory_open
    assert len(continuation["focus_targets"]) == advisory_open
    assert page.get_by_test_id("run-continuation-previous-run-link").is_visible()

    deadline = time.time() + 20
    while service.get_run(continued_run_id)["status"] not in {"succeeded", "failed", "stopped"} and time.time() < deadline:
        time.sleep(0.05)
    assert service.get_run(continued_run_id)["status"] == "succeeded"
    page.reload(wait_until="domcontentloaded")
    continuation_banner = page.get_by_test_id("run-continuation-state")
    assert continuation_banner.get_attribute("data-continuation-outcome") == "no_progress"
    assert str(advisory_open) in continuation_banner.text_content()

    page.goto(f"{current_url.scheme}://{current_url.netloc}/", wait_until="domcontentloaded")
    attention_reason = page.get_by_test_id("home-active-loop-attention-reason")
    assert attention_reason.get_attribute("data-attention-reason-kind") == "advisory_follow_up_no_progress"
    assert page.get_by_test_id("home-active-loop-action").get_attribute("data-attention-action-kind") == "review_advisory_follow_up"
    return continued_run_id


def test_browser_first_run_keeps_progress_primary_until_evidence_is_final(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LOOPORA_HOME", str(tmp_path / "app-home"))
    service = _service(
        tmp_path,
        executor_factory=lambda: FakeCodexExecutor(scenario="success", role_delay=1.5),
    )
    workdir = tmp_path / "first-run-phase-workdir"
    workdir.mkdir()
    bundle = service.import_bundle_text(FakeCodexExecutor._alignment_bundle_yaml(str(workdir.resolve())))

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(f"{base_url}/loops/{bundle['loop_id']}", wait_until="domcontentloaded")
        page.get_by_test_id("loop-start-run-button").click()
        page.wait_for_url("**/runs/*", timeout=10_000)
        page.wait_for_function(
            """() => document.querySelector('.run-judgment-grid')?.dataset.runPhase === 'active'
              && document.querySelector('[data-testid="run-progress-panel"]')?.open
              && document.querySelector('#takeaway-outcome-title')?.textContent.trim()""",
            timeout=10_000,
        )
        run_id = urlparse(page.url).path.rsplit("/", 1)[-1]
        _assert_active_run_decision_state(page)

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(page.url, wait_until="domcontentloaded")
        mobile.get_by_test_id("run-progress-panel").wait_for(state="visible", timeout=10_000)
        _assert_active_run_decision_state(mobile)

        deadline = time.time() + 20
        run = service.get_run(run_id)
        while run["status"] not in {"succeeded", "failed", "stopped"} and time.time() < deadline:
            time.sleep(0.05)
            run = service.get_run(run_id)
        assert run["status"] == "succeeded"
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function(
            """() => document.querySelector('.run-judgment-grid')?.dataset.runPhase === 'terminal'
              && document.querySelector('#takeaway-outcome-title')?.textContent.trim()""",
            timeout=10_000,
        )
        _assert_passing_run_decision_state(page)

        mobile.reload(wait_until="domcontentloaded")
        mobile.wait_for_function(
            "() => document.querySelector('.run-judgment-grid')?.dataset.runPhase === 'terminal'",
            timeout=10_000,
        )
        _assert_passing_run_decision_state(mobile)
        _assert_run_export_menu(page)
        _assert_unresolved_run_decision(page, service, run_id)


def test_browser_recorded_pass_preserves_optional_advisory_follow_up_and_reopens(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LOOPORA_HOME", str(tmp_path / "app-home"))
    service = _service(tmp_path)
    workdir = tmp_path / "recorded-follow-up-workdir"
    workdir.mkdir()
    bundle = service.import_bundle_text(FakeCodexExecutor._alignment_bundle_yaml(str(workdir.resolve())))
    run = service.start_run(bundle["loop_id"])
    service.start_run_async(run["id"])
    deadline = time.time() + 20
    while service.get_run(run["id"])["status"] not in {"succeeded", "failed", "stopped"} and time.time() < deadline:
        time.sleep(0.05)
    assert service.get_run(run["id"])["status"] == "succeeded"

    with serve_app(build_app(service=service)) as base_url, launch_chromium(headless=True) as browser:
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(f"{base_url}/runs/{run['id']}", wait_until="domcontentloaded")
        page.get_by_test_id("run-accept-result-button").click()
        page.get_by_test_id("run-accepted-result-state").wait_for(state="visible", timeout=10_000)
        _assert_recorded_run_decision(page)

        acceptance_state = service.run_result_acceptance_state(run["id"])
        required_basis = acceptance_state["recorded_coverage_target_basis"]["required"]
        advisory_basis = acceptance_state["recorded_coverage_target_basis"]["advisory"]
        assert acceptance_state["accepted"] is True
        assert required_basis["covered"] == required_basis["total"] > 0
        assert advisory_basis["open"] > 0
        assert page.get_by_test_id("run-recorded-advisory-rerun-button").is_visible()

        page.goto(f"{base_url}/loops/{bundle['loop_id']}", wait_until="domcontentloaded")
        _assert_recorded_loop_advisory_posture(page)

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(page.url, wait_until="domcontentloaded")
        _assert_recorded_loop_advisory_posture(mobile)
        assert mobile.evaluate("() => document.documentElement.scrollWidth <= document.documentElement.clientWidth") is True

        encoded_workdir = quote(str(workdir.resolve()), safe="")
        page.goto(f"{base_url}/?workdir={encoded_workdir}", wait_until="domcontentloaded")
        recorded_note = page.get_by_test_id("home-recent-loop-recorded-result")
        assert recorded_note.is_visible()
        assert str(advisory_basis["open"]) in recorded_note.text_content()
        assert page.get_by_test_id("home-active-loop").count() == 0

        _start_recorded_advisory_follow_up(
            page,
            service,
            run_id=run["id"],
            advisory_open=advisory_basis["open"],
        )

        page.goto(f"{base_url}/runs/{run['id']}", wait_until="domcontentloaded")
        page.get_by_test_id("run-reopen-recorded-result-button").click()
        page.get_by_test_id("run-accept-result-button").wait_for(state="visible", timeout=10_000)
        assert page.get_by_test_id("run-accepted-result-state").count() == 0
        assert page.get_by_test_id("run-recorded-advisory-rerun-button").count() == 0
        assert page.get_by_test_id("run-rerun-button").is_visible()
        assert service.run_result_acceptance_state(run["id"])["accepted"] is False

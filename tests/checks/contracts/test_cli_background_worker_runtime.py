from __future__ import annotations

import errno
import json
import os
from pathlib import Path
import socket

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from loopora import cli, cli_run_support
from loopora import cli_demo_commands
from loopora.branding import APP_HOME_ENV
from loopora.demo_environment import DemoEnvironment, seeded_demo_environment
from loopora.service_types import LooporaError
from loopora.serve_browser_open import schedule_browser_open, serve_browser_url
from loopora.web_url_utils import with_query_params

from cli_first_use_docs_test_support import complete_fit_review_cli_args, result_error_text


def _contains_cjk(value: object) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(value or ""))


def _assert_demo_web_paths(environment: DemoEnvironment, task_verdict: dict, outside_workdir: Path) -> None:
    playground_workdir = environment.playground_workdir
    real_task_command = 'loopora start --workdir "$PWD" --language zh'
    demo_app = cli_demo_commands.build_app(
        service=environment.service,
        startup_workdir=str(environment.workdir),
        demo_mode=True,
        demo_evidence_path=environment.run_path,
        demo_playground_workdir=str(playground_workdir),
        demo_workdir_root=str(environment.root),
        demo_real_task_command=real_task_command,
    )
    client = TestClient(demo_app)
    response = client.get(environment.run_path)
    home_response = client.get(with_query_params("/", workdir=str(playground_workdir)))
    playground_href = with_query_params("/loops/new/bundle", alignment_workdir=str(playground_workdir))
    run_response = client.get(f"/api/runs/{environment.run['id']}")
    ordinary_response = TestClient(cli_demo_commands.build_app(service=environment.service)).get(environment.run_path)
    outside_response = client.post("/api/alignments/sessions", json={"message": "real task", "workdir": str(outside_workdir)})
    demo_css = client.get("/static/app.css").text
    run_projection = run_response.json()["web_projection"]
    assert response.status_code == client.get(playground_href).status_code == run_response.status_code == 200
    assert 'data-testid="demo-mode-banner"' in response.text
    assert f'href="{environment.run_path}" data-testid="demo-evidence-link"' in response.text
    assert f'href="{playground_href}" data-testid="demo-playground-link"' in response.text
    assert f'href="{playground_href}" data-testid="home-compose-loop-link"' in home_response.text
    assert f'data-demo-playground-workdir="{playground_workdir}"' in response.text
    assert f'href="{with_query_params("/loops/new", workdir=str(playground_workdir))}" data-testid="nav-compose-link"' in response.text
    assert f'href="{with_query_params("/fit-guide", workdir=str(playground_workdir))}" data-testid="nav-tutorial-link"' in response.text
    assert 'data-testid="global-project-scope-toggle"' not in response.text
    assert 'data-testid="demo-real-task-copy"' in response.text
    assert real_task_command.replace('"', "&#34;") in response.text
    assert 'id="alignment-workdir"' in client.get(playground_href).text
    assert "readonly" in client.get(playground_href).text
    assert "模拟 executor" in response.text
    assert run_projection["task_verdict"]["summary"] == task_verdict["summary"]
    assert _contains_cjk(run_projection["task_verdict"]["summary"])
    assert 'data-testid="demo-mode-banner"' not in ordinary_response.text
    assert 'data-testid="global-project-scope-toggle"' in ordinary_response.text
    assert outside_response.status_code == 400
    assert not (outside_workdir / ".loopora").exists()
    assert all(term in demo_css for term in ("@media (max-width: 720px)", ".demo-mode-banner", ".demo-mode-banner-actions"))


def test_seeded_demo_runs_real_core_in_isolation_and_marks_web_as_simulated(monkeypatch, tmp_path: Path) -> None:
    normal_home = tmp_path / "normal-home"
    monkeypatch.setenv(APP_HOME_ENV, str(normal_home))

    with seeded_demo_environment(language="zh-CN") as environment:
        temporary_root = environment.root
        playground_workdir = environment.playground_workdir
        assert environment.run["status"] == "succeeded"
        assert environment.run["task_verdict"]["status"] == "passed"
        assert environment.app_home != normal_home
        assert playground_workdir.parent == temporary_root
        assert playground_workdir != environment.workdir
        assert playground_workdir.is_dir()
        assert not list(playground_workdir.iterdir())
        run_dir = Path(environment.run["runs_dir"])
        assert run_dir.resolve().is_relative_to(environment.workdir.resolve())
        compiled_spec = json.loads((run_dir / "contract" / "compiled_spec.json").read_text(encoding="utf-8"))
        coverage = json.loads((run_dir / "evidence" / "coverage.json").read_text(encoding="utf-8"))
        task_verdict = json.loads((run_dir / "evidence" / "task_verdict.json").read_text(encoding="utf-8"))
        builder = json.loads((run_dir / "builder_output.json").read_text(encoding="utf-8"))
        inspector = json.loads((run_dir / "inspector_output.json").read_text(encoding="utf-8"))
        gatekeeper = json.loads((run_dir / "gatekeeper_verdict.json").read_text(encoding="utf-8"))
        handoffs = [json.loads(path.read_text(encoding="utf-8")) for path in run_dir.glob("iterations/iter_*/steps/*/handoff.json")]
        assert all(_contains_cjk(compiled_spec["checks"][0][field]) for field in ("when", "expect", "fail_if"))
        assert all(_contains_cjk(target["label"]) for target in coverage["targets"])
        assert all(_contains_cjk(target["reason"]) for target in coverage["targets"])
        assert _contains_cjk(coverage["summary"]["reason"])
        assert all(_contains_cjk(builder[field]) for field in ("attempted", "abandoned", "assumption", "summary"))
        assert _contains_cjk(inspector["tester_observations"])
        assert all(_contains_cjk(item["notes"]) for item in inspector["check_results"])
        assert _contains_cjk(gatekeeper["decision_summary"])
        assert _contains_cjk(gatekeeper["feedback_to_builder"])
        assert _contains_cjk(task_verdict["summary"])
        assert handoffs
        assert all(_contains_cjk(handoff["summary"]) for handoff in handoffs)
        assert all(_contains_cjk(handoff["recommended_next_action"]) for handoff in handoffs)
        assert all("Out-of-scope or unfinished note" not in handoff["summary"] for handoff in handoffs)
        _assert_demo_web_paths(environment, task_verdict, tmp_path)

    assert not temporary_root.exists()
    assert not playground_workdir.exists()
    assert not normal_home.exists()
    assert os.environ[APP_HOME_ENV] == str(normal_home)


@pytest.mark.parametrize(
    ("language", "terminal_terms"),
    [
        (
            "en",
            (
                "mode: isolated temporary App state with a simulated executor",
                "result: succeeded / task verdict passed",
                "browser: http://127.0.0.1:9137/runs/run_",
                "try creating a Loop: http://127.0.0.1:9137/loops/new/bundle?alignment_workdir=",
                'real task: after stopping Demo, run this from the target project: loopora start --workdir "$PWD" --language en',
                "lifecycle: keep this command running; press Ctrl-C to stop and delete all demo data",
            ),
        ),
        (
            "zh",
            (
                "模式：使用模拟 executor 的隔离临时 App 状态",
                "结果：运行成功 / 任务裁决通过",
                "浏览器：http://127.0.0.1:9137/runs/run_",
                "试着创建 Loop：http://127.0.0.1:9137/loops/new/bundle?alignment_workdir=",
                '真实任务：停止 Demo 后，在目标项目目录运行：loopora start --workdir "$PWD" --language zh',
                "生命周期：保持此命令运行；按 Ctrl-C 停止并删除全部 Demo 数据",
            ),
        ),
    ],
)
def test_cli_demo_opens_completed_run_and_cleans_temporary_state(
    monkeypatch,
    tmp_path: Path,
    language: str,
    terminal_terms: tuple[str, ...],
) -> None:
    normal_home = tmp_path / "normal-home"
    calls: dict[str, object] = {}
    monkeypatch.setenv(APP_HOME_ENV, str(normal_home))
    monkeypatch.setattr(cli_demo_commands, "_available_demo_port", lambda _port: 9137)
    monkeypatch.setattr(cli_demo_commands, "schedule_browser_open_if_requested", lambda url: calls.update(browser_url=url))

    def fake_uvicorn_run(app, **kwargs):
        calls["app"] = app
        calls["kwargs"] = kwargs
        calls["temporary_root"] = Path(app.state.startup_workdir).parent
        calls["playground_workdir"] = Path(app.state.demo_playground_workdir)
        calls["playground_exists_during_run"] = calls["playground_workdir"].is_dir()
        run_id = str(calls["browser_url"]).rsplit("/", 1)[-1]
        calls["run"] = app.state.service.get_run(run_id)

    monkeypatch.setattr(cli_demo_commands.uvicorn, "run", fake_uvicorn_run)

    help_result = CliRunner().invoke(cli.app, ["--help"])
    result = CliRunner().invoke(cli.app, ["demo", "--open", "--language", language, "--port", "9137"])

    assert help_result.stdout.index("demo") < help_result.stdout.index("serve")
    assert result.exit_code == 0, result.output
    assert all(term in result.stdout for term in terminal_terms)
    assert str(calls["browser_url"]).startswith("http://127.0.0.1:9137/runs/run_")
    assert calls["kwargs"] == {"host": "127.0.0.1", "port": 9137, "log_level": "info", "access_log": False}
    assert calls["app"].state.demo_mode is True
    assert calls["app"].state.demo_evidence_path == f"/runs/{calls['run']['id']}"
    assert calls["playground_exists_during_run"] is True
    assert calls["playground_workdir"].parent == calls["temporary_root"]
    assert calls["run"]["status"] == "succeeded"
    assert not calls["temporary_root"].exists()
    assert not calls["playground_workdir"].exists()
    assert not normal_home.exists()


def test_cli_run_supports_command_mode_background_and_role_models(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    calls: dict[str, object] = {}

    class FakeService:
        def create_loop(self, **kwargs):
            calls["create_loop"] = kwargs
            return {"id": "loop_cmd", "name": kwargs["name"], "workdir": str(kwargs["workdir"])}

        def start_run(self, loop_id: str):
            calls["start_run"] = loop_id
            return {
                "id": "run_cmd",
                "status": "queued",
                "runs_dir": str(tmp_path / "runs" / "run_cmd"),
                "workdir": str(workdir),
            }

        def rerun(self, loop_id: str, *, background: bool = False):
            raise AssertionError(f"background CLI path should not call service.rerun(): {loop_id=} {background=}")

    monkeypatch.setattr(cli, "create_service", FakeService)

    def fake_spawn_background_worker(_service, run: dict):
        calls["spawned_run_id"] = run["id"]
        return run

    monkeypatch.setattr(cli, "_spawn_background_worker", fake_spawn_background_worker)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "run",
            "--spec",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--executor",
            "codex",
            "--executor-mode",
            "command",
            "--command-cli",
            "codex",
            "--command-arg",
            "exec",
            "--command-arg",
            "--json",
            "--command-arg",
            "--output-schema",
            "--command-arg",
            "{schema_path}",
            "--command-arg",
            "--output-last-message",
            "--command-arg",
            "{output_path}",
            "--command-arg",
            "--model",
            "--command-arg",
            "{model}",
            "--command-arg",
            "{prompt}",
            "--model",
            "gpt-5.4-mini",
            "--role-model",
            "generator=gpt-5.4",
            "--role-model",
            "verifier=gpt-5.4-mini",
            "--background",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert calls["start_run"] == "loop_cmd"
    assert calls["spawned_run_id"] == "run_cmd"
    assert calls["create_loop"]["executor_mode"] == "command"
    assert calls["create_loop"]["command_cli"] == "codex"
    assert "{schema_path}" in calls["create_loop"]["command_args_text"]
    assert "{model}" in calls["create_loop"]["command_args_text"]
    assert calls["create_loop"]["role_models"] == {
        "builder": "gpt-5.4",
        "gatekeeper": "gpt-5.4-mini",
    }


def test_cli_serve_loopback_auth_summary_matches_protection_without_printing_token(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: dict[str, object] = {}
    secret_token = "local-secret-token"

    def fake_build_app(**kwargs):
        calls["build_app"] = kwargs
        return object()

    def fake_uvicorn_run(app, **kwargs) -> None:
        calls["uvicorn_app"] = app
        calls["uvicorn"] = kwargs

    monkeypatch.setattr("loopora.cli_serve_commands.build_app", fake_build_app)
    monkeypatch.setattr("loopora.cli_serve_commands.uvicorn.run", fake_uvicorn_run)

    result = CliRunner().invoke(
        cli.app,
        [
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            "9762",
            "--auth-token",
            secret_token,
            "--workdir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert all(
        fragment in result.stdout
        for fragment in (
            "Loopora Web: http://127.0.0.1:9762",
            "fit guide: http://127.0.0.1:9762/fit-guide",
            "create: http://127.0.0.1:9762/loops/new",
            "auth: enabled",
        )
    )
    assert "auth: disabled" not in result.stdout
    assert secret_token not in result.stdout
    assert calls["build_app"] == {
        "bind_host": "127.0.0.1",
        "bind_port": 9762,
        "auth_token": secret_token,
        "startup_workdir": str(tmp_path),
    }


def test_cli_serve_open_waits_for_local_service_and_preserves_generated_page(monkeypatch, tmp_path: Path) -> None:
    calls: dict[str, object] = {}
    open_path = "/fit-guide?workdir=%2Fproject#fit-review=%7B%22task%22%3A%22Ship%22%7D"

    monkeypatch.setattr("loopora.cli_serve_commands.build_app", lambda **_kwargs: object())
    monkeypatch.setattr("loopora.cli_serve_commands.uvicorn.run", lambda _app, **_kwargs: None)
    monkeypatch.setattr(
        "loopora.cli_serve_commands.schedule_browser_open_if_requested",
        lambda url: calls.update(browser_url=url),
    )

    result = CliRunner().invoke(
        cli.app,
        ["serve", "--open", "--open-path", open_path, "--workdir", str(tmp_path), "--port", "9763", "--language", "zh-CN"],
    )

    expected_url = f"http://127.0.0.1:9763{open_path}"
    assert result.exit_code == 0, result.stdout
    assert calls["browser_url"] == expected_url
    assert f"浏览器：正在打开 {expected_url}" in result.stdout
    assert "生命周期：保持此命令运行；按 Ctrl-C 停止 Web" in result.stdout
    assert "下一步：先从适用性判断开始" in result.stdout
    assert "language=" not in str(calls["browser_url"])


def test_cli_serve_open_reuses_matching_existing_web_without_starting(monkeypatch, tmp_path: Path) -> None:
    calls: dict[str, object] = {}
    open_path = "/loops/new?alignment_session_id=align_ready"

    def responds(base_url: str, *, expected_app_home: str, auth_token: str) -> bool:
        calls["probe"] = (base_url, expected_app_home, auth_token)
        return True

    monkeypatch.setattr("loopora.cli_serve_commands.loopora_web_responds", responds)
    monkeypatch.setattr("loopora.cli_serve_commands.open_browser_now", lambda url: calls.update(browser_url=url))
    monkeypatch.setattr(
        "loopora.cli_serve_commands.build_app",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("reused Web must not build another app")),
    )
    monkeypatch.setattr(
        "loopora.cli_serve_commands.uvicorn.run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("reused Web must not start uvicorn")),
    )
    monkeypatch.setattr(
        "loopora.cli_serve_output.probe_web_bind",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("matching Web must be checked before bind recovery")),
    )

    result = CliRunner().invoke(
        cli.app,
        ["serve", "--open", "--open-path", open_path, "--workdir", str(tmp_path), "--port", "9763", "--language", "中文"],
    )

    expected_url = f"http://127.0.0.1:9763{open_path}"
    assert result.exit_code == 0, result.stdout
    assert calls["browser_url"] == expected_url
    assert calls["probe"][0] == "http://127.0.0.1:9763"
    assert calls["probe"][2] == ""
    assert "Loopora Web：已复用 http://127.0.0.1:9763" in result.stdout
    assert f"目标项目：{tmp_path}" in result.stdout
    assert f"浏览器：正在打开 {expected_url}" in result.stdout
    assert "现有服务仍由原终端持有" in result.stdout
    assert "保持此命令运行" not in result.stdout


def test_cli_serve_chinese_workdir_recovery_preserves_commands_and_neutral_json(tmp_path: Path) -> None:
    target = tmp_path / "missing project"
    runner = CliRunner()
    plain = runner.invoke(
        cli.app,
        ["serve", "--open", "--workdir", str(target), "--port", "9763", "--language", "zh-CN"],
    )
    structured = runner.invoke(
        cli.app,
        ["serve", "--open", "--workdir", str(target), "--port", "9763", "--language", "中文", "--json"],
    )

    assert plain.exit_code == structured.exit_code == 1
    assert all(term in plain.stdout for term in ("Web 启动受阻", "项目目录状态：不存在", "创建目标项目目录", "目标可用后确认就绪", "重试 Web 启动"))
    command_lines = [line for line in plain.stdout.splitlines() if "loopora doctor" in line or "loopora serve" in line]
    assert len(command_lines) == 2
    assert all(line.endswith("--language zh") for line in command_lines)
    payload = json.loads(structured.stdout)
    assert payload["workdir_state"]["status"] == "missing"
    assert "language" not in payload
    assert "--language" not in structured.stdout
    assert not target.exists()


def test_cli_start_and_fit_reuse_matching_default_web_service(monkeypatch, tmp_path: Path) -> None:
    def occupied(_host: str, _port: int) -> None:
        raise OSError(errno.EADDRINUSE, "in use")

    def no_alternate_needed(**_kwargs):
        raise AssertionError("matching Web should keep the requested port")

    monkeypatch.setattr("loopora.web_bind_preflight.probe_web_bind", occupied)
    monkeypatch.setattr("loopora.web_bind_preflight.next_available_web_port", no_alternate_needed)
    monkeypatch.setattr("loopora.start_guidance_actions.matching_configured_web_service", lambda *_args: True)
    monkeypatch.setattr("loopora.fit_guidance_web_route.matching_configured_web_service", lambda *_args: True)

    review_args = complete_fit_review_cli_args()
    start_json = CliRunner().invoke(cli.app, ["start", "--language", "zh-CN", "--workdir", str(tmp_path), *review_args, "--json"])
    start_plain = CliRunner().invoke(cli.app, ["start", "--workdir", str(tmp_path), *review_args, "--details"])
    fit_json = CliRunner().invoke(cli.app, ["fit", "--language", "中文", "--workdir", str(tmp_path), *review_args, "--json"])
    start_payload = json.loads(start_json.stdout)
    fit_payload = json.loads(fit_json.stdout)
    start_web = next(action for action in start_payload["route_actions_after_strong_fit"] if action["kind"] == "open_web_creation_choices")
    fit_web = next(action for action in fit_payload["next_actions"] if action["kind"] == "open_web_creation_choices")

    assert (start_json.exit_code, start_plain.exit_code, fit_json.exit_code) == (0, 0, 0)
    assert start_payload["start_guidance_summary"]["web_route_preflight_status"] == "matching_service_reusable"
    assert fit_payload["fit_guidance_summary"]["web_route_preflight_status"] == "matching_service_reusable"
    for action in (start_web, fit_web):
        assert action["port"] == action["requested_port"] == 8742
        assert action["suggested_port"] is None
        assert action["start_blocked_reason"] == ""
        assert "--port 8742" in action["command"]
        assert action["command"].endswith("--language zh")
    assert "A matching Loopora Web service is already running on port 8742; this route reuses it." in start_plain.stdout


def test_cli_diagnose_doctor_treats_matching_running_web_as_ready(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(tmp_path)])
    assert install.exit_code == 0, result_error_text(install)
    monkeypatch.setattr("loopora.diagnose_doctor_web_state.matching_configured_web_service", lambda *_args: True)
    monkeypatch.setattr(
        "loopora.diagnose_doctor.next_available_web_port",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("matching running Web needs no alternate port")),
    )
    occupied = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    occupied.bind(("127.0.0.1", 0))
    occupied.listen(1)
    port = int(occupied.getsockname()[1])
    args = ["doctor", "--workdir", str(tmp_path), "--web-host", "127.0.0.1", "--web-port", str(port)]

    try:
        json_result = runner.invoke(cli.app, [*args, "--json"])
        plain = runner.invoke(cli.app, args)
        strict = runner.invoke(cli.app, [*args, "--strict"])
    finally:
        occupied.close()

    payload = json.loads(json_result.stdout)
    assert (json_result.exit_code, plain.exit_code, strict.exit_code) == (0, 0, 0)
    assert (payload["status"], payload["ready"], payload["strict_ready"]) == ("ready", True, True)
    assert payload["web"]["already_running"] is True
    assert payload["web"]["start_available"] is True
    assert payload["web"]["start_blocked_reason"] == ""
    assert payload["web"]["port"] == payload["web"]["requested_port"] == port
    assert payload["web"]["suggested_port"] is None
    assert payload["diagnose_doctor_summary"]["web_access_mode"] == "open_existing"
    web_action = payload["next_action_items"][-1]
    assert (web_action["kind"], web_action["operation"], web_action["already_running"]) == (
        "start_web",
        "open_existing",
        True,
    )
    assert any("Open the existing Loopora Web service" in step for step in payload["next_steps"])
    assert f"web: http://127.0.0.1:{port} (running; loopback local default)" in plain.stdout
    assert "readiness summary: same-Agent project entry and App state are ready; Web is running." in plain.stdout
    assert f"web open: {payload['web']['start_command']}" in plain.stdout
    assert "web start unavailable" not in plain.stdout
    assert "strict readiness: yes" in strict.stdout


@pytest.mark.parametrize("open_path", ["https://example.com/", "//example.com/path", "fit-guide"])
def test_serve_browser_open_rejects_external_or_non_relative_paths(open_path: str) -> None:
    with pytest.raises(ValueError, match="relative Web path"):
        serve_browser_url(host="127.0.0.1", port=8742, open_path=open_path)


def test_serve_browser_open_waits_until_port_is_ready() -> None:
    opened: list[str] = []
    thread = schedule_browser_open(
        "http://127.0.0.1:8742/?workdir=%2Fproject",
        timeout_seconds=0.2,
        ready_probe=lambda _host, _port: True,
        opener=opened.append,
    )
    thread.join(timeout=1)

    assert opened == ["http://127.0.0.1:8742/?workdir=%2Fproject"]


def test_cli_loops_rerun_background_spawns_worker(monkeypatch, tmp_path: Path) -> None:
    calls: dict[str, object] = {}

    class FakeService:
        def start_next_run(self, loop_id: str):
            calls["start_next_run"] = loop_id
            return {
                "id": "run_background",
                "status": "queued",
                "runs_dir": str(tmp_path / "runs" / "run_background"),
                "workdir": str(tmp_path / "workdir"),
            }

        def rerun(self, loop_id: str, *, background: bool = False):
            raise AssertionError(f"background CLI path should not call service.rerun(): {loop_id=} {background=}")

    monkeypatch.setattr(cli, "create_service", FakeService)

    def fake_spawn_background_worker(_service, run: dict):
        calls["spawned"] = run["id"]
        return run

    monkeypatch.setattr(cli, "_spawn_background_worker", fake_spawn_background_worker)
    runner = CliRunner()

    result = runner.invoke(cli.app, ["loops", "rerun", "loop_saved", "--background"])

    assert result.exit_code == 0, result.stdout
    assert calls["start_next_run"] == "loop_saved"
    assert calls["spawned"] == "run_background"


def test_background_worker_spawn_failure_marks_run_failed_without_os_error(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    run_dir = tmp_path / "runs" / "run_failed_spawn"
    private_path = tmp_path / "private" / "blocked"
    updates: list[dict] = []
    events: list[dict] = []

    class FakeRepository:
        def update_run(self, run_id: str, **payload):
            assert run_id == "run_failed_spawn"
            updates.append(payload)

    class FakeService:
        repository = FakeRepository()

        def append_run_event(self, run_id: str, event_type: str, payload: dict):
            assert run_id == "run_failed_spawn"
            events.append({"event_type": event_type, "payload": payload})

    def fail_popen(*_args, **_kwargs):
        raise OSError(f"permission denied: {private_path}")

    monkeypatch.setattr(cli_run_support.subprocess, "Popen", fail_popen)

    with pytest.raises(LooporaError, match=cli_run_support.BACKGROUND_WORKER_START_ERROR) as exc_info:
        cli_run_support.spawn_background_worker(
            FakeService(),
            {
                "id": "run_failed_spawn",
                "runs_dir": str(run_dir),
                "workdir": str(workdir),
            },
        )

    assert str(exc_info.value) == cli_run_support.BACKGROUND_WORKER_START_ERROR
    assert updates[0]["status"] == "failed"
    assert updates[0]["error_message"] == cli_run_support.BACKGROUND_WORKER_START_ERROR
    assert cli_run_support.BACKGROUND_WORKER_START_ERROR in updates[0]["summary_md"]
    assert events == [
        {
            "event_type": "run_aborted",
            "payload": {
                "role": None,
                "attempts": 1,
                "degraded": False,
                "error": cli_run_support.BACKGROUND_WORKER_START_ERROR,
            },
        }
    ]
    encoded = f"{exc_info.value}\n{updates[0]}\n{events}"
    assert "permission denied" not in encoded
    assert str(private_path) not in encoded


def test_cli_run_background_spawn_failure_returns_failed_run_identity_json(monkeypatch, tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.md"
    spec_path.write_text("# Task\n\nKeep going.\n", encoding="utf-8")
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    private_path = tmp_path / "private" / "thread-start"

    class FakeService:
        def create_loop(self, **kwargs):
            return {"id": "loop_failed_spawn", "name": kwargs["name"], "workdir": str(kwargs["workdir"])}

        def start_run(self, loop_id: str):
            assert loop_id == "loop_failed_spawn"
            return {
                "id": "run_failed_spawn",
                "status": "queued",
                "runs_dir": str(tmp_path / "runs" / "run_failed_spawn"),
                "workdir": str(workdir),
            }

        def get_run(self, run_id: str):
            assert run_id == "run_failed_spawn"
            return {
                "id": run_id,
                "status": "failed",
                "error_message": cli_run_support.BACKGROUND_WORKER_START_ERROR,
                "runs_dir": str(tmp_path / "runs" / "run_failed_spawn"),
                "task_verdict": {"status": "not_evaluated", "source": "run_status"},
            }

        def rerun(self, loop_id: str, *, background: bool = False):
            raise AssertionError(f"background CLI path should not call service.rerun(): {loop_id=} {background=}")

    def fail_spawn_background_worker(_service, _run: dict):
        raise LooporaError(cli_run_support.BACKGROUND_WORKER_START_ERROR)

    monkeypatch.setattr(cli, "create_service", FakeService)
    monkeypatch.setattr(cli, "_spawn_background_worker", fail_spawn_background_worker)

    result = CliRunner().invoke(
        cli.app,
        [
            "run",
            "--spec",
            str(spec_path),
            "--workdir",
            str(workdir),
            "--background",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert next(iter(payload)) == "cli_run_start_recovery_summary"
    summary = payload["cli_run_start_recovery_summary"]
    assert summary == {
        "ready": False,
        "run_recovery": "retry_run_start",
        "run_start_error": cli_run_support.BACKGROUND_WORKER_START_ERROR,
        "run_id": "run_failed_spawn",
        "loop_id": "loop_failed_spawn",
        "next_action_kinds": ["retry_cli_run_start"],
        "next_action_ready_kinds": ["retry_cli_run_start"],
        "next_action_ready_now_kinds": ["retry_cli_run_start"],
        "next_action_ready_after_actions": {},
        "next_action_blocked_kinds": [],
        "next_action_command_blockers": {},
    }
    assert payload["status"] == "error"
    assert payload["error"] == cli_run_support.BACKGROUND_WORKER_START_ERROR
    assert payload["run_start_error"] == cli_run_support.BACKGROUND_WORKER_START_ERROR
    assert payload["run_recovery"] == "retry_run_start"
    assert payload["loop"]["id"] == "loop_failed_spawn"
    assert payload["run"]["id"] == "run_failed_spawn"
    assert payload["run"]["status"] == "failed"
    assert payload["run"]["status_label"] == "run_start_failed"
    assert payload["run"]["run_recovery"] == "retry_run_start"
    assert payload["run"]["error_message"] == cli_run_support.BACKGROUND_WORKER_START_ERROR
    assert payload["run"]["task_verdict"]["status"] == "not_evaluated"
    assert payload["next_actions"][0]["kind"] == "retry_cli_run_start"
    assert payload["next_action_ready_now_kinds"] == ["retry_cli_run_start"]
    assert payload["next_action_ready_after_actions"] == {}
    assert "--background" in payload["next_actions"][0]["command"]
    assert payload["run"]["next_actions"] == [{"kind": "retry_run_start", "command": payload["next_actions"][0]["command"]}]
    assert (
        payload["run"]["next_action_kinds"],
        payload["run"]["next_action_ready_now_kinds"],
        payload["run"]["next_action_ready_after_actions"],
    ) == (["retry_run_start"], ["retry_run_start"], {})
    assert summary["next_action_kinds"] == [payload["next_actions"][0]["kind"]]
    assert str(private_path) not in result.stdout


def test_cli_loops_rerun_background_spawn_failure_prints_failed_run_identity(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    class FakeService:
        def start_next_run(self, loop_id: str):
            assert loop_id == "loop_saved"
            return {
                "id": "run_failed_rerun",
                "status": "queued",
                "runs_dir": str(tmp_path / "runs" / "run_failed_rerun"),
                "workdir": str(workdir),
            }

        def get_run(self, run_id: str):
            assert run_id == "run_failed_rerun"
            return {
                "id": run_id,
                "status": "failed",
                "error_message": cli_run_support.BACKGROUND_WORKER_START_ERROR,
                "runs_dir": str(tmp_path / "runs" / "run_failed_rerun"),
                "task_verdict": {"status": "not_evaluated", "source": "run_status"},
            }

        def rerun(self, loop_id: str, *, background: bool = False):
            raise AssertionError(f"background CLI path should not call service.rerun(): {loop_id=} {background=}")

    def fail_spawn_background_worker(_service, _run: dict):
        raise LooporaError(cli_run_support.BACKGROUND_WORKER_START_ERROR)

    monkeypatch.setattr(cli, "create_service", FakeService)
    monkeypatch.setattr(cli, "_spawn_background_worker", fail_spawn_background_worker)

    result = CliRunner().invoke(cli.app, ["loops", "rerun", "loop_saved", "--background"])

    assert result.exit_code == 1
    assert "run: run_failed_rerun" in result.stdout
    assert "run_status: failed" in result.stdout
    assert "task_verdict: not_evaluated" in result.stdout
    assert f"run_start_error: {cli_run_support.BACKGROUND_WORKER_START_ERROR}" in result.stderr
    assert "retry: " in result.stderr
    assert "loopora loops rerun loop_saved --background" in result.stderr


def test_cli_loops_rerun_background_spawn_failure_returns_recovery_summary_json(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    class FakeService:
        def start_next_run(self, loop_id: str):
            assert loop_id == "loop_saved"
            return {
                "id": "run_failed_rerun",
                "loop_id": loop_id,
                "status": "queued",
                "runs_dir": str(tmp_path / "runs" / "run_failed_rerun"),
                "workdir": str(workdir),
            }

        def get_run(self, run_id: str):
            assert run_id == "run_failed_rerun"
            return {
                "id": run_id,
                "loop_id": "loop_saved",
                "status": "failed",
                "error_message": cli_run_support.BACKGROUND_WORKER_START_ERROR,
                "runs_dir": str(tmp_path / "runs" / "run_failed_rerun"),
                "task_verdict": {"status": "not_evaluated", "source": "run_status"},
            }

        def rerun(self, loop_id: str, *, background: bool = False):
            raise AssertionError(f"background CLI path should not call service.rerun(): {loop_id=} {background=}")

    def fail_spawn_background_worker(_service, _run: dict):
        raise LooporaError(cli_run_support.BACKGROUND_WORKER_START_ERROR)

    monkeypatch.setattr(cli, "create_service", FakeService)
    monkeypatch.setattr(cli, "_spawn_background_worker", fail_spawn_background_worker)

    result = CliRunner().invoke(cli.app, ["loops", "rerun", "loop_saved", "--background", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert next(iter(payload)) == "cli_run_start_recovery_summary"
    assert payload["cli_run_start_recovery_summary"] == {
        "ready": False,
        "run_recovery": "retry_run_start",
        "run_start_error": cli_run_support.BACKGROUND_WORKER_START_ERROR,
        "run_id": "run_failed_rerun",
        "loop_id": "loop_saved",
        "next_action_kinds": ["retry_cli_run_start"],
        "next_action_ready_kinds": ["retry_cli_run_start"],
        "next_action_ready_now_kinds": ["retry_cli_run_start"],
        "next_action_ready_after_actions": {},
        "next_action_blocked_kinds": [],
        "next_action_command_blockers": {},
    }
    assert payload["run"]["id"] == "run_failed_rerun"
    assert payload["run"]["status_label"] == "run_start_failed"
    assert payload["run"]["run_recovery"] == "retry_run_start"
    assert payload["run"]["next_action_ready_now_kinds"] == ["retry_run_start"]
    assert payload["next_actions"][0]["kind"] == "retry_cli_run_start"
    assert payload["next_action_ready_now_kinds"] == ["retry_cli_run_start"]
    assert "loopora loops rerun loop_saved --background --json" in payload["next_actions"][0]["command"]

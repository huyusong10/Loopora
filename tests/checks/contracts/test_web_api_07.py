from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

import loopora.web as web_module
from loopora.web import build_app


def test_api_role_definition_rejects_custom_executor_preset_mode(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/role-definitions",
        json={
            "name": "Custom Wrapper",
            "description": "Wrapper role.",
            "archetype": "custom",
            "prompt_markdown": """---
version: 1
archetype: custom
---

Observe and summarize.
""",
            "executor_kind": "custom",
            "executor_mode": "preset",
            "command_cli": "wrapper",
            "command_args_text": "--output\n{output_path}\n{prompt}\n",
            "model": "",
            "reasoning_effort": "",
        },
    )

    assert response.status_code == 400
    assert "only supports command mode" in response.json()["error"]

def test_api_role_definition_rejects_unsafe_prompt_ref(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/role-definitions",
        json={
            "name": "Escaping Builder",
            "description": "Should fail when prompt_ref escapes the asset root.",
            "archetype": "builder",
            "prompt_ref": "../escape.md",
            "prompt_markdown": """---
version: 1
archetype: builder
---

Keep prompt refs inside prompts/.
""",
            "executor_kind": "codex",
            "executor_mode": "preset",
            "model": "gpt-5.4-mini",
            "reasoning_effort": "medium",
        },
    )

    assert response.status_code == 400
    assert "prompt_ref must be a safe relative path" in response.json()["error"]

def test_api_spec_init_validate_and_delete_loop(service_factory, tmp_path: Path, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    spec_path = tmp_path / "created-spec.md"
    init_response = client.post(
        "/api/specs/init",
        json={"path": str(spec_path), "locale": "en", "workflow_preset": "build_first"},
    )
    assert init_response.status_code == 201
    assert spec_path.exists()
    created_text = spec_path.read_text(encoding="utf-8")
    assert "delete `# Done When`" in created_text
    assert "preserve existing user files" in created_text
    assert "# Task" in created_text
    assert "# Done When" in created_text
    assert "# Guardrails" in created_text
    assert "# Role Notes" in created_text
    assert "## Builder Notes" in created_text
    assert "## Inspector Notes" in created_text
    assert "## GateKeeper Notes" in created_text
    assert "## Guide Notes" in created_text

    duplicate_init_response = client.post(
        "/api/specs/init",
        json={"path": str(spec_path), "locale": "en", "workflow_preset": "build_first"},
    )
    assert duplicate_init_response.status_code == 409
    assert "already exists" in duplicate_init_response.json()["error"]

    strategy_alias_path = tmp_path / "created-spec-strategy-alias.md"
    strategy_alias_response = client.post(
        "/api/specs/init",
        json={"path": str(strategy_alias_path), "locale": "en", "strategy_preset": "inspect_first"},
    )
    assert strategy_alias_response.status_code == 201
    assert "## Inspector Notes" in strategy_alias_path.read_text(encoding="utf-8")

    validate_response = client.get("/api/specs/validate", params={"path": str(spec_path)})
    assert validate_response.status_code == 200
    assert validate_response.json()["ok"] is True
    assert validate_response.json()["check_mode"] == "specified"

    loop = service.create_loop(
        name="Delete Me",
        spec_path=spec_path,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="xhigh",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )

    delete_response = client.delete(f"/api/loops/{loop['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["id"] == loop["id"]
    assert service.list_loops() == []

def test_api_spec_template_accepts_strategy_json_mapping(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/specs/template",
        json={
            "locale": "en",
            "strategy_json": {
                "version": 1,
                "roles": [
                    {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
                    {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
                ],
                "steps": [
                    {"id": "build", "role_id": "builder"},
                    {"id": "gate", "role_id": "gatekeeper", "on_pass": "finish_run"},
                ],
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "# Task" in payload["content"]
    assert "## Builder Notes" in payload["content"]
    assert "## GateKeeper Notes" in payload["content"]
    assert [item["role_name"] for item in payload["role_note_sections"]] == ["Builder", "GateKeeper"]
    assert "<h1>Task</h1>" in payload["rendered_html"]

def test_api_spec_template_and_init_reject_invalid_workflow_json(
    tmp_path: Path,
    service_factory,
) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))
    invalid_workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
        ],
        "controls": [
            {
                "id": "bad_repair",
                "when": {"signal": "step_failed", "after": "0s"},
                "call": {"role_id": "builder"},
            }
        ],
    }

    template_response = client.post("/api/specs/template", json={"workflow_json": invalid_workflow})
    assert template_response.status_code == 400
    assert "controls may only call Inspector" in template_response.json()["error"]

    spec_path = tmp_path / "invalid-workflow-template.md"
    init_response = client.post(
        "/api/specs/init",
        json={"path": str(spec_path), "locale": "en", "workflow_json": invalid_workflow},
    )
    assert init_response.status_code == 400
    assert "controls may only call Inspector" in init_response.json()["error"]
    assert not spec_path.exists()

def test_api_spec_validate_reports_auto_generated_check_mode(tmp_path: Path, service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    spec_path = tmp_path / "exploratory-spec.md"
    spec_path.write_text(
        "# Task\n\nExplore a promising prototype direction.\n\n# Guardrails\n\n- Stay focused.\n",
        encoding="utf-8",
    )

    validate_response = client.get("/api/specs/validate", params={"path": str(spec_path)})
    assert validate_response.status_code == 200
    payload = validate_response.json()
    assert payload["ok"] is True
    assert payload["check_mode"] == "auto_generated"
    assert payload["check_count"] == 0

def test_api_spec_validate_rejects_legacy_headings(tmp_path: Path, service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    spec_path = tmp_path / "legacy-spec.md"
    spec_path.write_text("# Goal\n\nLegacy format.\n", encoding="utf-8")

    response = client.get("/api/specs/validate", params={"path": str(spec_path)})

    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert "legacy spec headings" in response.json()["error"]

def test_api_spec_preview_returns_rendered_read_only_markdown(tmp_path: Path, service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    spec_path = tmp_path / "preview-spec.md"
    spec_path.write_text(
        "# Task\n\nShip a preview.\n\n# Done When\n\n- Render headings\n- Escape <script>alert('xss')</script>\n\n```js\nconsole.log('ok')\n```\n",
        encoding="utf-8",
    )

    preview_response = client.get("/api/specs/preview", params={"path": str(spec_path)})

    assert preview_response.status_code == 200
    payload = preview_response.json()
    assert payload["ok"] is True
    assert payload["path"] == str(spec_path.resolve())
    assert "# Task" in payload["content"]
    assert "<h1>Task</h1>" in payload["rendered_html"]
    assert "<script>" not in payload["rendered_html"]
    assert "&lt;script&gt;alert" in payload["rendered_html"]
    assert 'class="language-js"' in payload["rendered_html"]
    assert "console.log" in payload["rendered_html"]

def test_api_spec_document_returns_content_rendering_and_validation(tmp_path: Path, service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    spec_path = tmp_path / "editable-spec.md"
    spec_path.write_text(
        "# Task\n\nKeep editing local.\n\n# Done When\n\n- The disk file updates after save.\n- The rendered preview updates too.\n",
        encoding="utf-8",
    )

    response = client.get("/api/specs/document", params={"path": str(spec_path)})

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["path"] == str(spec_path.resolve())
    assert payload["content"].startswith("# Task")
    assert "<h1>Task</h1>" in payload["rendered_html"]
    assert payload["validation"]["ok"] is True
    assert payload["validation"]["check_count"] == 2
    assert payload["validation"]["check_mode"] == "specified"

def test_api_spec_document_save_writes_file_and_returns_validation(tmp_path: Path, service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    spec_path = tmp_path / "editable-spec.md"
    spec_path.write_text("# Task\n\nInitial\n", encoding="utf-8")

    response = client.put(
        "/api/specs/document",
        json={
            "path": str(spec_path),
            "content": "# Task\r\n\r\nSaved copy.\r\n\r\n# Done When\r\n\r\n- The file matches the editor after save.\r\n",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["content"] == "# Task\n\nSaved copy.\n\n# Done When\n\n- The file matches the editor after save.\n"
    assert spec_path.read_text(encoding="utf-8") == payload["content"]
    assert payload["validation"]["ok"] is True
    assert payload["validation"]["check_count"] == 1
    assert "<h1>Done When</h1>" in payload["rendered_html"]

def test_api_spec_document_endpoints_reject_non_markdown_paths(tmp_path: Path, service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    non_spec_path = tmp_path / "not-a-spec.txt"
    non_spec_path.write_text("# Task\n\nSensitive but parseable local text.\n", encoding="utf-8")

    for endpoint in ("/api/specs/validate", "/api/specs/preview", "/api/specs/document"):
        response = client.get(endpoint, params={"path": str(non_spec_path)})
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is False
        assert "Markdown file" in payload["error"]
        assert "Sensitive but parseable" not in json.dumps(payload, ensure_ascii=False)

    save_response = client.put(
        "/api/specs/document",
        json={"path": str(non_spec_path), "content": "# Task\n\nOverwritten\n"},
    )
    assert save_response.status_code == 200
    assert save_response.json()["ok"] is False
    assert "Markdown file" in save_response.json()["error"]
    assert "Sensitive but parseable" in non_spec_path.read_text(encoding="utf-8")

    init_response = client.post("/api/specs/init", json={"path": str(tmp_path / "created.txt"), "locale": "en"})
    assert init_response.status_code == 400
    assert "Markdown file" in init_response.json()["error"]

def test_api_spec_document_endpoints_reject_oversized_markdown(tmp_path: Path, service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    oversized_path = tmp_path / "oversized-spec.md"
    oversized_path.write_text("# Task\n\n" + ("x" * 1_000_001), encoding="utf-8")

    for endpoint in ("/api/specs/validate", "/api/specs/preview", "/api/specs/document"):
        response = client.get(endpoint, params={"path": str(oversized_path)})
        assert response.status_code == 200
        assert response.json()["ok"] is False
        assert "too large" in response.json()["error"]

    save_response = client.put(
        "/api/specs/document",
        json={"path": str(tmp_path / "new-spec.md"), "content": "# Task\n\n" + ("x" * 1_000_001)},
    )
    assert save_response.status_code == 200
    assert save_response.json()["ok"] is False
    assert "too large" in save_response.json()["error"]
    assert not (tmp_path / "new-spec.md").exists()

def test_api_spec_document_endpoints_reject_binary_markdown(tmp_path: Path, service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    binary_path = tmp_path / "binary-spec.md"
    binary_path.write_bytes(b"# Task\n\n\x00binary-like content\n")

    for endpoint in ("/api/specs/validate", "/api/specs/preview", "/api/specs/document"):
        response = client.get(endpoint, params={"path": str(binary_path)})
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is False
        assert "text markdown" in payload["error"]
        assert "binary-like content" not in json.dumps(payload, ensure_ascii=False)

    save_path = tmp_path / "save-target.md"
    save_path.write_text("# Task\n\nKeep this text.\n", encoding="utf-8")

    save_response = client.put(
        "/api/specs/document",
        json={"path": str(save_path), "content": "# Task\n\n\u0000binary-like content\n"},
    )
    assert save_response.status_code == 200
    assert save_response.json()["ok"] is False
    assert "text markdown" in save_response.json()["error"]
    assert save_path.read_text(encoding="utf-8") == "# Task\n\nKeep this text.\n"

def test_api_spec_document_endpoints_reject_non_utf8_markdown(tmp_path: Path, service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    invalid_path = tmp_path / "invalid-spec.md"
    invalid_path.write_bytes(b"# Task\n\n\xff\n")

    for endpoint in ("/api/specs/validate", "/api/specs/preview", "/api/specs/document"):
        response = client.get(endpoint, params={"path": str(invalid_path)})
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is False
        assert "UTF-8 encoded Markdown" in payload["error"]

def test_api_markdown_render_can_strip_prompt_front_matter(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.post(
        "/api/markdown/render",
        json={
            "markdown": "---\nversion: 1\narchetype: builder\n---\n\n# Prompt Body\n\nShip the change.\n",
            "strip_front_matter": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "<h1>Prompt Body</h1>" in payload["rendered_html"]
    assert "version: 1" not in payload["rendered_html"]
    assert "archetype: builder" not in payload["rendered_html"]
    assert "Ship the change." in payload["rendered_html"]

def test_logo_assets_are_served(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.get("/logo/logo.svg")
    assert response.status_code == 200
    assert "image/svg+xml" in response.headers["content-type"]

def test_network_mode_requires_auth_token_and_sets_cookie(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    unauthorized = client.get("/")
    assert unauthorized.status_code == 401
    assert "Auth token required" in unauthorized.text

    unsupported_header = client.get("/", headers={"X-Other-Token": "secret-token"})
    assert unsupported_header.status_code == 401

    bearer_authorized = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token")).get(
        "/api/loops",
        headers={"Authorization": "Bearer secret-token"},
    )
    assert bearer_authorized.status_code == 200

    custom_header_authorized = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token")).get(
        "/api/loops",
        headers={"X-Loopora-Token": "secret-token"},
    )
    assert custom_header_authorized.status_code == 200

    authorized = client.get("/?token=secret-token")
    assert authorized.status_code == 200
    assert client.cookies.get("loopora_auth") == "secret-token"

    api_response = client.get("/api/loops")
    assert api_response.status_code == 200

def test_network_mode_auth_page_uses_request_locale_and_shared_styles(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    unauthorized = client.get("/", headers={"Accept-Language": "zh-CN;q=0.1,en-US;q=0.9"})

    assert unauthorized.status_code == 401
    assert re.search(r'<html\s+lang="en"\s+data-locale="en"\s+data-theme="light"\s*>', unauthorized.text)
    assert "loopora:theme" in unauthorized.text
    assert "loopora:locale" in unauthorized.text
    assert "/static/app.css?v=" in unauthorized.text
    assert "<style>" not in unauthorized.text
    assert 'data-testid="auth-card"' in unauthorized.text
    assert 'data-testid="auth-copy-stack"' in unauthorized.text
    assert "Loopora · Auth token required" in unauthorized.text
    assert "Auth token required" in unauthorized.text
    assert "需要访问令牌" in unauthorized.text
    assert "X-Loopora-Token" in unauthorized.text
    assert "X-Other-Token" not in unauthorized.text
    assert 'class="auth-logo" src="/logo/logo-with-text-horizontal.svg" alt="" aria-hidden="true"' in unauthorized.text

    unauthenticated_css = client.get("/static/app.css")
    assert unauthenticated_css.status_code == 200
    assert "text/css" in unauthenticated_css.headers["content-type"]
    assert ".auth-shell {" in unauthenticated_css.text
    unauthenticated_logo = client.get("/logo/logo.svg")
    assert unauthenticated_logo.status_code == 200
    assert "image/svg+xml" in unauthenticated_logo.headers["content-type"]

    css = client.get("/static/app.css?token=secret-token")
    assert css.status_code == 200
    assert ".auth-shell {" in css.text
    assert ".auth-card {" in css.text
    assert ".auth-copy-stack {" in css.text
    assert '[data-theme="dark"] .auth-card {' in css.text
    assert 'html[data-theme="dark"] .auth-logo {' in css.text

def test_preferred_locale_from_accept_language_respects_q_values_and_supported_locales() -> None:
    assert web_module._preferred_locale_from_accept_language("zh-CN;q=0.1,en-US;q=0.9") == "en"
    assert web_module._preferred_locale_from_accept_language("en-US;q=0.1,zh-CN;q=0.9") == "zh"
    assert web_module._preferred_locale_from_accept_language("fr-FR,zh-CN;q=0.8,en-US;q=0.6") == "zh"
    assert web_module._preferred_locale_from_accept_language("fr-FR,de-DE;q=0.8") == "en"
    assert web_module._preferred_locale_from_accept_language("en-US;q=0,zh-CN;q=0.6") == "zh"
    assert web_module._preferred_locale_from_accept_language("zh_CN;q=0.7,en-US;q=0.4") == "zh"
    assert web_module._preferred_locale_from_accept_language("zh-CN;q=bad,en-US;q=0.4") == "en"
    assert web_module._preferred_locale_from_accept_language("zh-CN;q=nan,en-US;q=0.4") == "en"
    assert web_module._preferred_locale_from_accept_language("zh-CN;q=inf,en-US;q=0.4") == "en"
    assert web_module._preferred_locale_from_accept_language("zh-CN;q=1.5,en-US;q=0.4") == "en"
    assert web_module._preferred_locale_from_accept_language("zh-CN;q=-0.1,en-US;q=0.4") == "en"

def test_network_mode_disables_native_dialog_endpoints(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    response = client.get("/api/system/pick-directory?token=secret-token")
    assert response.status_code == 405

    post_response = client.post(
        "/api/system/pick-directory?token=secret-token",
        json={"start_path": "/tmp"},
    )
    assert post_response.status_code == 400
    assert "native dialogs are disabled in network mode" in post_response.json()["error"]

    reveal = client.post("/api/system/reveal-path?token=secret-token", json={"path": "/tmp"})
    assert reveal.status_code == 400
    assert "native dialogs are disabled in network mode" in reveal.json()["error"]

from __future__ import annotations

import json
from pathlib import Path


from loopora.bundles import bundle_to_yaml, load_bundle_text
from loopora.executor import FakeCodexExecutor
from loopora.executor_fake_payloads import alignment_bundle_yaml
import loopora.service_alignment as alignment_module

from alignment_test_support import (
    _wait_for_status,
    _confirm_alignment_agreement,
    _bundle_invocation_dir,
    _assert_run_succeeds_and_joins,
    _assert_alignment_preview_control_summary,
)

def test_alignment_prompt_assets_separate_run_status_from_task_verdict() -> None:
    root = Path(__file__).resolve().parents[3]
    asset_dir = root / "src" / "loopora" / "assets" / "alignment"
    playbook = (asset_dir / "alignment-playbook.md").read_text(encoding="utf-8")
    primer = (asset_dir / "product-primer.md").read_text(encoding="utf-8")

    main_workflow = "`compose Loop -> run Loop -> automatic iteration with evidence -> run status, task verdict, and result`"
    assert main_workflow in playbook
    assert main_workflow in primer
    assert "`Loop -> run -> automatic iteration -> evidence -> run status + task verdict + result`" in primer
    assert "The task verdict projection should be easy to map into stable buckets" in primer

    for path in sorted(asset_dir.glob("*.md")):
        source = path.read_text(encoding="utf-8")
        assert "evidence verdict and result" not in source, path.name
        assert "The evidence verdict should" not in source, path.name

def test_alignment_fake_bundle_keeps_runtime_judgment_surfaces_visible(sample_workdir: Path) -> None:
    bundle_text = alignment_bundle_yaml(str(sample_workdir.resolve()))

    assert "Execution Strategy, Judgment Tradeoffs, Local Governance, and Residual Risk" in bundle_text
    assert "sequencing drift, lowered tradeoffs, local-governance gaps" in bundle_text
    assert "prove the task contract, execution strategy, judgment tradeoffs, local governance when present" in bundle_text
    assert "Intermediate control points measure weak evidence and fake-done drift" in bundle_text
    assert "trigger a continue / correct / halt decision" in bundle_text
    assert "keep the required evidence target explicit" in bundle_text
    assert "Treat status-only checkpoints as insufficient" in bundle_text

def test_alignment_service_writes_validates_previews_imports_and_runs(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a focused starter experience.",
    )
    session = _confirm_alignment_agreement(service, created["id"])

    bundle_path = Path(session["bundle_path"])
    artifact_root = sample_workdir / ".loopora" / "alignment_sessions" / session["id"]
    assert bundle_path == artifact_root / "artifacts" / "bundle.yml"
    assert bundle_path.exists()
    assert session["validation"]["ok"] is True
    assert (artifact_root / "manifest.json").exists()
    assert (artifact_root / "conversation" / "transcript.jsonl").exists()
    assert (artifact_root / "agreement" / "current.json").exists()
    assert (artifact_root / "artifacts" / "validation.json").exists()
    assert (artifact_root / "events" / "events.jsonl").exists()
    invocation_dir = artifact_root / "invocations" / "0001"
    assert (invocation_dir / "prompt.md").exists()
    assert (invocation_dir / "schema.json").exists()
    assert (invocation_dir / "output.json").exists()
    assert (invocation_dir / "stdout.log").exists()
    assert (invocation_dir / "stderr.log").exists()
    bundle_invocation_dir = _bundle_invocation_dir(artifact_root)
    assert bundle_invocation_dir != invocation_dir
    invocation_output = json.loads((invocation_dir / "output.json").read_text(encoding="utf-8"))
    assert "bundle_yaml" not in invocation_output
    assert invocation_output["bundle_written"] is False
    invocation_output = json.loads((bundle_invocation_dir / "output.json").read_text(encoding="utf-8"))
    assert "bundle_yaml" not in invocation_output
    assert invocation_output["bundle_written"] is True
    assert invocation_output["bundle_path"] == str(bundle_path)
    manifest = json.loads((artifact_root / "manifest.json").read_text(encoding="utf-8"))
    assert "transcript" not in manifest
    assert "validation" not in manifest
    assert "working_agreement" not in manifest
    assert "Build a focused starter experience." in (artifact_root / "conversation" / "transcript.jsonl").read_text(encoding="utf-8")
    assert session["alignment_stage"] == "ready"

    preview = service.get_alignment_bundle(session["id"])
    assert preview["ok"] is True
    assert preview["bundle"]["loop"]["workdir"] == str(sample_workdir.resolve())
    assert preview["workflow_preview"]["roles"][0]["name"] == "Focused Builder"
    _assert_alignment_preview_control_summary(preview)
    assert "Ship the focused starter experience" in preview["spec_rendered_html"]

    imported = service.import_alignment_bundle(session["id"], start_immediately=True)
    assert imported["bundle"]["loop_id"]
    assert imported["run"]["id"]
    final_session = service.get_alignment_session(session["id"])
    assert final_session["status"] == "running_loop"
    assert final_session["linked_bundle_id"] == imported["bundle"]["id"]
    assert final_session["linked_loop_id"] == imported["bundle"]["loop_id"]
    assert final_session["linked_run_id"] == imported["run"]["id"]
    _assert_run_succeeds_and_joins(service, imported["run"]["id"])

def test_alignment_manifest_and_session_summary_redact_transcript_preview_secrets(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Start from --token MANIFEST_TOKEN_SECRET_MARKER and Cookie: sid=MANIFEST_COOKIE_SECRET_MARKER.",
        start_immediately=False,
    )
    artifact_root = Path(session["artifact_dir"])
    manifest = json.loads((artifact_root / "manifest.json").read_text(encoding="utf-8"))
    listed = service.list_alignment_sessions()[0]
    transcript_text = (artifact_root / "conversation" / "transcript.jsonl").read_text(encoding="utf-8")

    for payload in (json.dumps(manifest, ensure_ascii=False), json.dumps(listed, ensure_ascii=False)):
        assert "MANIFEST_TOKEN_SECRET_MARKER" not in payload
        assert "MANIFEST_COOKIE_SECRET_MARKER" not in payload
        assert "<secret omitted>" in payload

    assert "MANIFEST_TOKEN_SECRET_MARKER" in transcript_text
    assert "MANIFEST_COOKIE_SECRET_MARKER" in transcript_text

def test_alignment_manifest_redacts_error_message_preview_secrets(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a Loop later.",
        start_immediately=False,
    )

    service.repository.update_alignment_session(
        session["id"],
        status="failed",
        error_message="provider failed with Authorization: Bearer MANIFEST_ERROR_SECRET_MARKER",
    )
    service._write_alignment_manifest(service.get_alignment_session(session["id"]))

    manifest = json.loads((Path(session["artifact_dir"]) / "manifest.json").read_text(encoding="utf-8"))
    assert "MANIFEST_ERROR_SECRET_MARKER" not in json.dumps(manifest, ensure_ascii=False)
    assert manifest["error_message"] == "provider failed with Authorization: <secret omitted>"

def test_alignment_invocation_output_debug_artifact_redacts_sensitive_values(tmp_path: Path) -> None:
    invocation_dir = tmp_path / "invocations" / "0001"
    invocation_dir.mkdir(parents=True)
    bundle_path = tmp_path / "artifacts" / "bundle.yml"
    bundle_yaml = "version: 1\nmetadata:\n  name: OUTPUT_BUNDLE_SECRET_MARKER\n"

    alignment_module.ServiceAlignmentMixin._finalize_alignment_invocation_files(
        invocation_dir,
        {
            "assistant_message": "Use --x-loopora-token OUTPUT_ARG_SECRET_MARKER",
            "diagnostics": {
                "error": "Authorization: Bearer OUTPUT_AUTH_SECRET_MARKER",
                "headers": {"Cookie": "sid=OUTPUT_COOKIE_SECRET_MARKER"},
                "auth_token": "OUTPUT_FIELD_SECRET_MARKER",
            },
            "prompt": "OUTPUT_PROMPT_SECRET_MARKER",
            "bundle_yaml": bundle_yaml,
        },
        bundle_path,
    )

    output = json.loads((invocation_dir / "output.json").read_text(encoding="utf-8"))
    output_text = json.dumps(output, ensure_ascii=False)

    assert "bundle_yaml" not in output
    assert output["bundle_written"] is True
    assert output["bundle_path"] == str(bundle_path)
    assert output["bundle_bytes"] == len(bundle_yaml.encode("utf-8"))
    assert output["bundle_sha256"]
    assert output["diagnostics"]["headers"]["Cookie"] == "<secret omitted>"
    assert output["diagnostics"]["auth_token"] == "<secret omitted>"
    assert output["prompt"] == "<prompt omitted>"
    for secret in (
        "OUTPUT_ARG_SECRET_MARKER",
        "OUTPUT_AUTH_SECRET_MARKER",
        "OUTPUT_COOKIE_SECRET_MARKER",
        "OUTPUT_FIELD_SECRET_MARKER",
        "OUTPUT_PROMPT_SECRET_MARKER",
        "OUTPUT_BUNDLE_SECRET_MARKER",
    ):
        assert secret not in output_text

def test_alignment_workdir_context_redacts_user_controlled_option_labels(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["metadata"]["name"] = "Imported --token CONTEXT_LABEL_TOKEN_SECRET_MARKER"
    bundle["metadata"]["description"] = "Authorization: Bearer CONTEXT_LABEL_AUTH_SECRET_MARKER"
    bundle["loop"]["name"] = "Cookie: sid=CONTEXT_LABEL_COOKIE_SECRET_MARKER"

    service.import_bundle_text(bundle_to_yaml(bundle))

    context = service.get_alignment_workdir_context(sample_workdir)
    context_text = json.dumps(context, ensure_ascii=False)

    assert "CONTEXT_LABEL_TOKEN_SECRET_MARKER" not in context_text
    assert "CONTEXT_LABEL_AUTH_SECRET_MARKER" not in context_text
    assert "CONTEXT_LABEL_COOKIE_SECRET_MARKER" not in context_text
    assert "<secret omitted>" in context_text

def test_alignment_import_string_false_does_not_start_run(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a focused starter experience.",
    )
    session = _confirm_alignment_agreement(service, created["id"])

    imported = service.import_alignment_bundle(session["id"], start_immediately="false")

    assert imported["run"] is None
    assert imported["session"]["status"] == "imported"
    assert imported["session"]["linked_run_id"] == ""
    events = service.list_alignment_events(session["id"])
    assert any(event["event_type"] == "alignment_imported" for event in events)
    assert not any(event["event_type"] == "alignment_run_started" for event in events)

def test_alignment_executor_events_redact_sensitive_values_before_persistence(
    service_factory,
    sample_workdir: Path,
) -> None:
    class SensitiveAlignmentExecutor(FakeCodexExecutor):
        def execute(self, request, emit_event, _should_stop, set_child_pid) -> dict:
            set_child_pid(None)
            emit_event(
                "codex_event",
                {
                    "type": "command",
                    "message": ("codex exec --token leak-command-token\nAuthorization: Bearer leak-bearer-token\nCookie: sid=leak-cookie-token"),
                    "auth_token": "leak-field-token",
                    "prompt": "leak-prompt-body",
                    "json_schema": {"secret": "leak-schema-body"},
                },
            )
            payload = self._alignment_agreement_response()
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = SensitiveAlignmentExecutor
    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Create an alignment session with sensitive executor output.",
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    persisted_events = service.list_alignment_events(session["id"])
    artifact_events = (Path(session["artifact_dir"]) / "events" / "events.jsonl").read_text(encoding="utf-8")
    stdout_text = (Path(session["artifact_dir"]) / "invocations" / "0001" / "stdout.log").read_text(encoding="utf-8")
    persisted_session = json.dumps(service.get_alignment_session(session["id"]), ensure_ascii=False)
    persisted_events_text = json.dumps(persisted_events, ensure_ascii=False)

    for text in (persisted_session, persisted_events_text, artifact_events, stdout_text):
        assert "leak-command-token" not in text
        assert "leak-bearer-token" not in text
        assert "leak-cookie-token" not in text
        assert "leak-field-token" not in text
        assert "leak-prompt-body" not in text
        assert "leak-schema-body" not in text
    assert any(event["event_type"] == "alignment_waiting_user" for event in persisted_events)

def test_alignment_repository_redacts_sensitive_values_before_db_and_artifact(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Create a local alignment event sink.",
        start_immediately=False,
    )

    event = service.repository.append_alignment_event(
        session["id"],
        "alignment_failed",
        {
            "message": "OPENAI_API_KEY=leak-env-token",
            "error": "Authorization: Bearer leak-error-token",
            "headers": {"Cookie": "sid=leak-cookie-token"},
            "auth_token": "leak-field-token",
            "prompt": "leak-prompt-body",
            "json_schema": {"secret": "leak-schema-body"},
            "bundle_yaml": "leak-bundle-body",
        },
    )
    listed = service.list_alignment_events(session["id"])[-1]
    artifact_events = (Path(session["artifact_dir"]) / "events" / "events.jsonl").read_text(encoding="utf-8")

    for text in (json.dumps(event, ensure_ascii=False), json.dumps(listed, ensure_ascii=False), artifact_events):
        assert "leak-env-token" not in text
        assert "leak-error-token" not in text
        assert "leak-cookie-token" not in text
        assert "leak-field-token" not in text
        assert "leak-prompt-body" not in text
        assert "leak-schema-body" not in text
        assert "leak-bundle-body" not in text
    assert listed["payload"]["auth_token"] == "<secret omitted>"
    assert listed["payload"]["prompt_omitted"] is True
    assert listed["payload"]["json_schema_omitted"] is True
    assert listed["payload"]["bundle_yaml_omitted"] is True

def test_alignment_service_waits_for_user_question(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="alignment_question")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="I need help shaping this task.",
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert session["transcript"][-1]["role"] == "assistant"
    assert "推荐" in session["transcript"][-1]["content"]
    options = session["transcript"][-1]["decision_options"]
    assert len(options) >= 2
    assert options[0]["recommended"] is True
    assert "优先阻断假完成" in options[0]["label"]
    assert options[0]["user_reply"]
    assert not Path(session["bundle_path"]).exists()
    assert session["native_resume_available"] is True
    assert session["executor_session_ref"]["session_id"]

def test_alignment_event_cursor_requires_integer_sequence(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a focused starter experience.",
    )
    service.repository.append_alignment_event(session["id"], "alignment_status_checked", {"status": "idle"})

    events = service.list_alignment_events(session["id"])
    assert len(events) >= 2
    first_id = events[0]["id"]

    assert [event["id"] for event in service.list_alignment_events(session["id"], after_id=True, limit=2)] == [
        event["id"] for event in events[:2]
    ]
    assert [event["id"] for event in service.list_alignment_events(session["id"], after_id=str(first_id), limit=2)] == [
        event["id"] for event in events[:2]
    ]
    assert service.list_alignment_events(session["id"], limit=True) == []

def test_alignment_repair_attempts_require_integer_sequence(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="Build a focused starter experience.",
    )

    updated = service.repository.update_alignment_session(session["id"], repair_attempts="2")

    assert updated["repair_attempts"] == 0
    assert alignment_module.ServiceAlignmentMixin._alignment_repair_attempts({"repair_attempts": None}) == 0
    assert alignment_module.ServiceAlignmentMixin._alignment_repair_attempts({"repair_attempts": "1"}, invalid_default=1) == 1
    assert alignment_module.ServiceAlignmentMixin._alignment_invocation_dir(sample_workdir, "2", repair=False).name == "0001"

def test_alignment_session_start_immediately_string_false_does_not_start(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_question")

    session = service.create_alignment_session(
        workdir=sample_workdir,
        message="I need help shaping this task.",
        start_immediately="false",
    )

    assert session["status"] == "idle"
    assert session["transcript"][-1]["role"] == "user"
    assert not Path(session["bundle_path"]).exists()
    events = service.list_alignment_events(session["id"])
    assert not any(event["event_type"] == "alignment_waiting_user" for event in events)

def test_alignment_service_keeps_not_fit_gate_in_dialogue(service_factory, sample_workdir: Path) -> None:
    service = service_factory(scenario="alignment_not_fit")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Just run one obvious one-off edit.",
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert "一次 Agent 执行加一次人工 review" in session["transcript"][-1]["content"]
    assert session["transcript"][-1]["decision_options"][0]["recommended"] is True
    assert "Skip Loop" in session["transcript"][-1]["decision_options"][0]["label"]
    assert session["alignment_stage"] == "clarifying"

def test_alignment_service_keeps_blocked_not_fit_output_in_dialogue(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_not_fit_without_needs_user_input")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="Just run one obvious one-off edit.",
    )
    session = _wait_for_status(service, created["id"], "waiting_user")

    assert not Path(session["bundle_path"]).exists()
    assert session["error_message"] == ""
    assert "反复出现的判断或新证据" in session["transcript"][-1]["content"]
    assert session["transcript"][-1]["decision_options"][0]["recommended"] is True
    assert session["alignment_stage"] == "clarifying"
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_waiting_user" for event in events)
    assert not any(event["event_type"] == "alignment_failed" for event in events)

def test_alignment_service_reframes_mechanical_configuration_questions(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_mechanical_question")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="请帮我编排一个长期任务。",
    )
    session = _wait_for_status(service, created["id"], "waiting_user")
    assistant_message = session["transcript"][-1]["content"]

    assert "配置两个 Inspector" not in assistant_message
    assert "推荐" in assistant_message
    assert session["transcript"][-1]["decision_options"][0]["recommended"] is True
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_question_reframed"
        and {"mechanical_configuration_question", "missing_recommended_decision_options"}.issubset(set(event["payload"].get("issues", [])))
        for event in events
    )

def test_alignment_service_reframes_generic_preference_questions(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_generic_preference_question")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="请帮我编排一个长期任务。",
    )
    session = _wait_for_status(service, created["id"], "waiting_user")
    assistant_message = session["transcript"][-1]["content"]

    assert "你有什么偏好" not in assistant_message
    assert "推荐" in assistant_message
    assert session["transcript"][-1]["decision_options"][0]["recommended"] is True
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_question_reframed"
        and {"generic_alignment_question", "missing_recommended_decision_options"}.issubset(set(event["payload"].get("issues", [])))
        for event in events
    )

def test_alignment_service_reframes_clarifying_questionnaires(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_questionnaire_overload")

    created = service.create_alignment_session(
        workdir=sample_workdir,
        message="请帮我编排一个长期任务。",
    )
    session = _wait_for_status(service, created["id"], "waiting_user")
    assistant_message = session["transcript"][-1]["content"]

    assert "1. 你想完成什么任务" not in assistant_message
    assert "推荐" in assistant_message
    assert session["transcript"][-1]["decision_options"][0]["recommended"] is True
    events = service.list_alignment_events(created["id"])
    assert any(
        event["event_type"] == "alignment_question_reframed"
        and {"questionnaire_overload", "missing_recommended_decision_options"}.issubset(set(event["payload"].get("issues", [])))
        for event in events
    )

def test_alignment_visible_decision_options_require_choice_set_and_recommendation() -> None:
    session = {"transcript": [{"role": "user", "content": "Build a governed starter experience."}]}
    non_boolean_needs_user_input = alignment_module.ServiceAlignmentMixin._visible_alignment_decision_options(
        session,
        {
            "needs_user_input": "false",
            "alignment_phase": "clarifying",
            "decision_options": [
                {
                    "id": "evidence_path",
                    "label": "Evidence path",
                    "description": "Prefer proof.",
                    "recommended": True,
                    "user_reply": "Use the evidence path.",
                },
                {
                    "id": "speed_path",
                    "label": "Speed path",
                    "description": "Prefer speed.",
                    "recommended": False,
                    "user_reply": "Use the speed path.",
                },
            ],
        },
        has_bundle=False,
    )
    single_option = alignment_module.ServiceAlignmentMixin._visible_alignment_decision_options(
        session,
        {
            "needs_user_input": True,
            "alignment_phase": "clarifying",
            "decision_options": [
                {
                    "id": "only_choice",
                    "label": "Only one path",
                    "description": "This should not be displayed as a real choice.",
                    "recommended": True,
                    "user_reply": "Use the only path.",
                }
            ],
        },
        has_bundle=False,
    )
    no_recommendation = alignment_module.ServiceAlignmentMixin._visible_alignment_decision_options(
        session,
        {
            "needs_user_input": True,
            "alignment_phase": "clarifying",
            "decision_options": [
                {"id": "slow", "label": "Go slow", "description": "More evidence.", "user_reply": "Go slow."},
                {"id": "fast", "label": "Go fast", "description": "More speed.", "user_reply": "Go fast."},
            ],
        },
        has_bundle=False,
    )
    missing_description = alignment_module.ServiceAlignmentMixin._visible_alignment_decision_options(
        session,
        {
            "needs_user_input": True,
            "alignment_phase": "clarifying",
            "decision_options": [
                {
                    "id": "evidence_path",
                    "label": "Evidence path",
                    "recommended": True,
                    "user_reply": "Use the evidence path.",
                },
                {
                    "id": "speed_path",
                    "label": "Speed path",
                    "description": "Prefer speed.",
                    "recommended": False,
                    "user_reply": "Use the speed path.",
                },
            ],
        },
        has_bundle=False,
    )
    string_recommendation = alignment_module.ServiceAlignmentMixin._visible_alignment_decision_options(
        session,
        {
            "needs_user_input": True,
            "alignment_phase": "clarifying",
            "decision_options": [
                {
                    "id": "evidence_path",
                    "label": "Evidence path",
                    "description": "Prefer proof.",
                    "recommended": "true",
                    "user_reply": "Use the evidence path.",
                },
                {
                    "id": "speed_path",
                    "label": "Speed path",
                    "description": "Prefer speed.",
                    "recommended": "false",
                    "user_reply": "Use the speed path.",
                },
            ],
        },
        has_bundle=False,
    )
    valid_options = alignment_module.ServiceAlignmentMixin._visible_alignment_decision_options(
        session,
        {
            "needs_user_input": True,
            "alignment_phase": "clarifying",
            "decision_options": [
                {
                    "id": "evidence_path",
                    "label": "Evidence path",
                    "description": "Prefer proof.",
                    "recommended": True,
                    "user_reply": "Use the evidence path.",
                },
                {
                    "id": "speed_path",
                    "label": "Speed path",
                    "description": "Prefer speed.",
                    "recommended": False,
                    "user_reply": "Use the speed path.",
                },
            ],
        },
        has_bundle=False,
    )

    assert non_boolean_needs_user_input == []
    assert [option["id"] for option in single_option] == ["evidence_first", "speed_first", "add_judgment"]
    assert [option["id"] for option in no_recommendation] == ["evidence_first", "speed_first", "add_judgment"]
    assert [option["id"] for option in missing_description] == ["evidence_first", "speed_first", "add_judgment"]
    assert [option["id"] for option in string_recommendation] == ["evidence_first", "speed_first", "add_judgment"]
    assert [option["id"] for option in valid_options] == ["evidence_path", "speed_path"]

def test_alignment_missing_items_are_stable_ids_only() -> None:
    missing = alignment_module.ServiceAlignmentMixin._normalize_alignment_missing_items(
        [
            "success_surface",
            "success_surface",
            "role_posture",
            "raw model prose should not become a chip",
            {"bad": "shape"},
        ]
    )

    assert missing == ["success_surface", "role_posture"]

def test_alignment_clarifying_question_rewrite_requires_boolean_need() -> None:
    non_boolean_issues = alignment_module.ServiceAlignmentMixin._alignment_clarifying_question_issues(
        {
            "needs_user_input": "true",
            "assistant_message": "What roles do you want?",
            "decision_options": [],
        }
    )
    boolean_issues = alignment_module.ServiceAlignmentMixin._alignment_clarifying_question_issues(
        {
            "needs_user_input": True,
            "assistant_message": "What roles do you want?",
            "decision_options": [],
        }
    )

    assert non_boolean_issues == []
    assert "generic_alignment_question" in boolean_issues

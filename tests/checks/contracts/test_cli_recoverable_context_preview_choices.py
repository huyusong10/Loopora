from __future__ import annotations

from agent_adapter_test_support import cli_agent_adapter_commands, cli_agent_runtime_support


def test_cli_recoverable_context_omits_run_commands_for_not_ready_choice(capsys) -> None:
    cli_agent_adapter_commands._print_recoverable_context_choices(
        {
            "confidence": "ambiguous",
            "choices": [
                {
                    "action": "preview_not_ready",
                    "label_en": "Resume Agent run: not ready preview",
                    "option_id": "agent_run:align_pending",
                    "alignment_session_id": "align_pending",
                    "choice_status": "not_ready",
                    "choice_hint_en": "Not runnable yet; return to /loopora-plan or Web review before selecting it.",
                    "runnable": False,
                    "alignment_status": "idle",
                    "updated_at": "2026-05-19T20:28:10Z",
                    "preview_url": "http://127.0.0.1:8749/loops/new/bundle?alignment_session_id=align_pending",
                    "preview_path": "/loops/new/bundle?alignment_session_id=align_pending",
                    "next_slash_command": "/loopora-run option:agent_run:align_pending",
                    "next_cli_command": "loopora agent codex run --source-option-id agent_run:align_pending",
                    "next_plan_command": "/loopora-plan",
                }
            ],
        }
    )

    output = capsys.readouterr().out

    assert "choice_status: not_ready" in output
    assert "runnable: false" in output
    assert "alignment_status: idle" in output
    assert "updated_at: 2026-05-19T20:28:10Z" in output
    assert "preview_url: http://127.0.0.1:8749/loops/new/bundle?alignment_session_id=align_pending" in output
    assert "preview_path: /loops/new/bundle?alignment_session_id=align_pending" in output
    assert "next_plan_command: /loopora-plan" in output
    assert "next_loop_command:" not in output
    assert "next_cli_command:" not in output
    assert "selection_hint: no runnable contexts are available" in output
    assert "next: no runnable choice is available; return to /loopora-plan or Web review" in output
    assert "next: for a runnable choice" not in output


def test_cli_recoverable_context_attaches_preview_urls_to_choices(monkeypatch) -> None:
    result = {
        "context_resolution": {
            "choices": [
                {
                    "action": "preview_not_ready",
                    "label_en": "Review unfinished preview",
                    "option_id": "agent_run:align_pending",
                    "runnable": False,
                    "preview_path": "/loops/new/bundle?alignment_session_id=align_pending",
                }
            ]
        }
    }

    monkeypatch.setattr(
        cli_agent_runtime_support,
        "ensure_local_web_service",
        lambda: {"base_url": "http://127.0.0.1:8749"},
    )

    cli_agent_adapter_commands._attach_recoverable_context_preview_urls(result, no_web=False)

    choice = result["context_resolution"]["choices"][0]
    assert result["web"]["base_url"] == "http://127.0.0.1:8749"
    assert choice["preview_url"] == "http://127.0.0.1:8749/loops/new/bundle?alignment_session_id=align_pending"
    assert cli_agent_adapter_commands._recoverable_context_choice_summary(choice)["preview_url"] == choice["preview_url"]

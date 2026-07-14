from __future__ import annotations

from executor_architecture_test_support import design_contracts_source, loopora_source


def test_real_executor_uses_dedicated_session_and_output_helpers() -> None:
    real_source = loopora_source("executor_real.py")
    session_source = loopora_source("executor_session_refs.py")
    output_source = loopora_source("executor_output_parsing.py")
    command_args_source = loopora_source("executor_command_args.py")
    command_events_source = loopora_source("executor_command_events.py")
    result_files_source = loopora_source("executor_result_files.py")
    process_runner_source = loopora_source("executor_process_runner.py")
    opencode_stream_source = loopora_source("executor_opencode_stream.py")
    contracts_source = design_contracts_source()

    assert "from loopora.executor_session_refs import" in real_source
    assert "from loopora.executor_provider_flows import RealExecutorProviderFlowMixin" in real_source
    assert "class RealCodexExecutor(RealExecutorProviderFlowMixin, CodexExecutor)" in real_source
    assert "def ensure_resume_session_ref" in session_source
    assert "def write_executor_schema_file" in result_files_source
    assert "def read_executor_json_object_output" in result_files_source
    assert "read_executor_output_text" in result_files_source
    assert "read_executor_output_text" not in real_source
    assert "from loopora.executor_output_parsing import parse_structured_output_from_text" in real_source
    assert "def parse_structured_output_from_text" in output_source
    assert "from loopora.executor_opencode_stream import" in real_source
    assert "def handle_opencode_record" in opencode_stream_source
    assert "from loopora.executor_process_runner import" in real_source
    assert "def run_executor_process" in process_runner_source
    assert "from loopora.executor_command_events import build_command_event_payload" in process_runner_source
    assert "def build_command_event_payload" in command_events_source
    assert "COMMAND_EVENT_PREVIEW_LIMIT" in command_events_source
    assert "def build_command_event_payload" not in command_args_source
    assert "build_command_event_payload" in process_runner_source
    assert "ProcessStreamStoppedError" in process_runner_source
    assert "build_command_event_payload" not in real_source
    assert "ProcessStreamContext" not in real_source
    assert "def read_executor_output_text" in result_files_source
    assert "def read_executor_output_text" not in command_args_source
    assert "from loopora.executor_result_files import EXECUTOR_OUTPUT_MAX_BYTES" in opencode_stream_source
    assert "EXECUTOR_OUTPUT_MAX_BYTES" in opencode_stream_source
    assert "EXECUTOR_OUTPUT_MAX_BYTES" not in real_source
    assert "write_text(json.dumps(request.output_schema" not in real_source
    assert "request.output_path.write_text" not in real_source
    assert "candidate.find" not in real_source
    assert "executor_result_files.py" in contracts_source
    assert "executor_output_parsing.py" in contracts_source
    assert "executor_opencode_stream.py" in contracts_source
    assert "executor_provider_flows.py" in contracts_source
    assert "executor_process_runner.py" in contracts_source
    assert "executor_command_events.py" in contracts_source


def test_real_executor_provider_flows_have_dedicated_boundary() -> None:
    real_source = loopora_source("executor_real.py")
    provider_flows_source = loopora_source("executor_provider_flows.py")
    result_files_source = loopora_source("executor_result_files.py")
    contracts_source = design_contracts_source()

    assert "class RealExecutorProviderFlowMixin" in provider_flows_source
    for marker in ("def _execute_codex", "def _execute_claude", "def _execute_opencode", "def _execute_custom"):
        assert marker in provider_flows_source
        assert marker not in real_source
    assert "from loopora.executor_result_files import" in provider_flows_source
    assert "ensure_resume_session_ref" in provider_flows_source
    assert "write_executor_json_output" in provider_flows_source
    assert "read_executor_json_object_output" in provider_flows_source
    assert provider_flows_source.count("self._raise_for_unsuccessful_process(") == 4
    assert "raise ExecutionStopped" in provider_flows_source
    assert "def read_executor_json_object_output" in result_files_source
    assert "executor_provider_flows.py" in contracts_source

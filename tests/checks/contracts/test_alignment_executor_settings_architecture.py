from __future__ import annotations

from service_architecture_test_support import design_contracts_source, loopora_source


def test_alignment_executor_settings_have_dedicated_boundary() -> None:
    requests_source = loopora_source("service_alignment_requests.py")
    settings_source = loopora_source("service_alignment_executor_settings.py")
    session_creation_source = loopora_source("service_alignment_session_creation.py")
    contracts_source = design_contracts_source()

    assert "from loopora.service_alignment_executor_settings import" in requests_source
    assert "from loopora.service_alignment_executor_settings import normalize_alignment_executor_settings" in session_creation_source
    for marker in (
        "class AlignmentExecutorSettingsRequest",
        "def default_alignment_executor_settings",
        "def alignment_executor_settings_from_raw",
        "def normalize_alignment_executor_settings",
        "validate_command_args_text",
    ):
        assert marker in settings_source
        assert marker not in requests_source
    assert "service_alignment_executor_settings.py" in contracts_source

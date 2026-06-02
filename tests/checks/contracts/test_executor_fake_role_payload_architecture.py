from __future__ import annotations

from executor_architecture_test_support import design_contracts_source, loopora_source


def test_fake_executor_role_payloads_have_dedicated_boundary() -> None:
    fake_payloads_source = loopora_source("executor_fake_payloads.py")
    role_payloads_source = loopora_source("executor_fake_role_payloads.py")
    builder_payloads_source = loopora_source("executor_fake_builder_payloads.py")
    verifier_payloads_source = loopora_source("executor_fake_verifier_payloads.py")
    contracts_source = design_contracts_source()

    assert "from loopora.executor_fake_role_payloads import" in fake_payloads_source
    assert "from loopora.executor_fake_builder_payloads import" in role_payloads_source
    assert "from loopora.executor_fake_verifier_payloads import" in role_payloads_source
    for marker in (
        "def fake_payload_context",
        "def fake_role_payload",
    ):
        assert marker in role_payloads_source
        assert marker not in fake_payloads_source
    for marker in ("def fake_builder_payload", "def fake_check_planner_payload", "def fake_tester_payload"):
        assert marker in builder_payloads_source
        assert marker not in fake_payloads_source + role_payloads_source + verifier_payloads_source
    for marker in ("def fake_verifier_payload", "def fake_challenger_payload", "def fake_custom_payload"):
        assert marker in verifier_payloads_source
        assert marker not in fake_payloads_source + role_payloads_source + builder_payloads_source
    for marker in (
        "def build_fake_payload",
        "def _clear_workdir_for_destructive_fake",
    ):
        assert marker in fake_payloads_source
        assert marker not in role_payloads_source
    assert "executor_fake_role_payloads.py" in contracts_source
    assert "executor_fake_builder_payloads.py" in contracts_source
    assert "executor_fake_verifier_payloads.py" in contracts_source

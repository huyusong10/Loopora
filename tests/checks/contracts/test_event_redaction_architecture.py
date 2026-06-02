from __future__ import annotations

from pathlib import Path


def test_event_redaction_secret_helpers_have_dedicated_boundary() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    event_source = (repo_root / "src/loopora/event_redaction.py").read_text(encoding="utf-8")
    codex_source = (repo_root / "src/loopora/event_redaction_codex.py").read_text(encoding="utf-8")
    secrets_source = (repo_root / "src/loopora/event_redaction_secrets.py").read_text(encoding="utf-8")
    design_source = (repo_root / "design/contracts.md").read_text(encoding="utf-8")

    assert "from loopora.event_redaction_secrets import" in event_source
    assert "from loopora.event_redaction_codex import" in event_source
    for marker in (
        "def redact_secret_text",
        "def key_is_secret",
        "_SECRET_ARG_PATTERN",
        "_ENV_SECRET_PATTERN",
        "_BEARER_SECRET_PATTERN",
        "_HEADER_SECRET_PATTERN",
    ):
        assert marker in secrets_source
        assert marker not in event_source
    for marker in (
        "def redact_codex_event_payload",
        "def _redact_codex_item",
        "_CODEX_PASSTHROUGH_KEYS",
        "MAX_CODEX_ITEM_TEXT_LENGTH",
    ):
        assert marker in codex_source
        assert marker not in event_source
    assert "event_redaction_secrets.py" in design_source
    assert "event_redaction_codex.py" in design_source

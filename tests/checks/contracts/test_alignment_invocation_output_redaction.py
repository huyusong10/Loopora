from __future__ import annotations

import json
from pathlib import Path

from loopora.service_alignment_artifacts import finalize_alignment_invocation_files


def test_alignment_invocation_output_debug_artifact_redacts_sensitive_values(tmp_path: Path) -> None:
    invocation_dir = tmp_path / "invocations" / "0001"
    invocation_dir.mkdir(parents=True)
    bundle_path = tmp_path / "artifacts" / "bundle.yml"
    bundle_yaml = "version: 1\nmetadata:\n  name: OUTPUT_BUNDLE_SECRET_MARKER\n"

    finalize_alignment_invocation_files(
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

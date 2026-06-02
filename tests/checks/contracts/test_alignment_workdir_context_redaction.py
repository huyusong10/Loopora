from __future__ import annotations

import json
from pathlib import Path

from loopora.bundles import bundle_to_yaml, load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml


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

from __future__ import annotations

import json
from pathlib import Path

from bundle_derive_test_support import create_manual_loop


def test_derive_bundle_uses_saved_loop_spec_snapshot(
    service_factory,
    sample_spec_file: Path,
    sample_spec_text: str,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_manual_loop(service, spec_path=sample_spec_file, workdir=sample_workdir)
    sample_spec_file.write_text(
        "# Task\n\nThis external source file changed after loop creation.\n",
        encoding="utf-8",
    )

    derived = service.derive_bundle_from_loop(loop["id"], name="Derived From Saved Snapshot")

    assert derived["spec"]["markdown"] == sample_spec_text.strip()


def test_derive_bundle_normalizes_saved_loop_workflow_before_projection(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = create_manual_loop(service, spec_path=sample_spec_file, workdir=sample_workdir)
    workflow = json.loads(json.dumps(loop["workflow_json"]))
    workflow["steps"][0]["inherit_session"] = "false"
    with service.repository.transaction() as connection:
        connection.execute(
            "UPDATE loop_definitions SET workflow_json = ? WHERE id = ?",
            (json.dumps(workflow, ensure_ascii=False), loop["id"]),
        )

    derived = service.derive_bundle_from_loop(loop["id"], name="Derived From Saved Snapshot")

    assert derived["workflow"]["steps"][0]["inherit_session"] is False

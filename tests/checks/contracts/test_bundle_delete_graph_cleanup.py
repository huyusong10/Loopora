from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from bundle_lifecycle_test_support import _bundle_yaml
from loopora.branding import state_dir_for_workdir
from loopora.service import LooporaError


def test_bundle_delete_cleans_imported_group_but_keeps_unrelated_assets(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    manual_role = service.create_role_definition(
        name="Manual Builder",
        description="Unrelated role",
        archetype="builder",
        prompt_markdown=dedent(
            """\
            ---
            version: 1
            archetype: builder
            ---

            Keep going.
            """
        ),
    )
    manual_orchestration = service.create_orchestration(
        name="Manual Flow",
        workflow={"preset": "build_first"},
    )
    manual_loop = service.create_loop(
        name="Manual Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4",
        reasoning_effort="medium",
        max_iters=3,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        orchestration_id=manual_orchestration["id"],
    )

    other_workdir = sample_workdir.parent / "bundle-workdir"
    other_workdir.mkdir()
    imported = service.import_bundle_text(_bundle_yaml(other_workdir))

    deleted = service.delete_bundle(imported["id"])

    assert deleted == {"id": imported["id"], "deleted": True}
    assert service.get_role_definition(manual_role["id"])["name"] == "Manual Builder"
    assert service.get_orchestration(manual_orchestration["id"])["name"] == "Manual Flow"
    assert service.get_loop(manual_loop["id"])["name"] == "Manual Loop"
    with pytest.raises(LooporaError, match="unknown bundle"):
        service.get_bundle(imported["id"])


def test_bundle_delete_keeps_managed_dir_and_records_when_graph_delete_fails(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    bundle_dir = service._bundle_dir(imported["id"])
    assert bundle_dir.exists()
    loop_id = imported["loop_id"]
    orchestration_id = imported["orchestration_id"]
    role_definition_ids = list(imported["role_definition_ids"])

    def fail_delete_bundle_graph(bundle_id: str) -> bool:
        if bundle_id == imported["id"]:
            raise LooporaError("bundle graph delete failed")
        return True

    monkeypatch.setattr(service.repository, "delete_bundle_graph", fail_delete_bundle_graph)
    with pytest.raises(LooporaError, match="bundle graph delete failed"):
        service.delete_bundle(imported["id"])

    assert bundle_dir.exists()
    assert service.repository.get_bundle(imported["id"]) is not None
    assert service.repository.get_loop(loop_id) is not None
    assert service.repository.get_orchestration(orchestration_id) is not None
    assert all(service.repository.get_role_definition(role_id) is not None for role_id in role_definition_ids)


def test_bundle_delete_does_not_remove_current_directory_loop_artifact_for_blank_saved_workdir(
    monkeypatch,
    tmp_path: Path,
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    imported = service.import_bundle_text(_bundle_yaml(sample_workdir))
    loop_id = imported["loop_id"]
    wrong_cwd = tmp_path / "wrong-cwd"
    fake_loop_dir = state_dir_for_workdir(wrong_cwd) / "loops" / loop_id
    fake_loop_dir.mkdir(parents=True)
    sentinel = fake_loop_dir / "sentinel.txt"
    sentinel.write_text("must survive\n", encoding="utf-8")
    with service.repository.transaction() as connection:
        connection.execute("UPDATE loop_definitions SET workdir = ? WHERE id = ?", ("", loop_id))
    monkeypatch.chdir(wrong_cwd)

    deleted = service.delete_bundle(imported["id"])

    assert deleted == {"id": imported["id"], "deleted": True}
    assert sentinel.read_text(encoding="utf-8") == "must survive\n"

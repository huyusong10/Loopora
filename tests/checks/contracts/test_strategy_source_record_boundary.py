from __future__ import annotations

from types import SimpleNamespace

from typer.testing import CliRunner

from loopora import cli
from loopora import cli_spec_support
from loopora.agent_native_runtime_context import agent_native_run_context
from loopora.asset_catalog import StrategyTemplateAssetCatalog
from loopora.db import LooporaRepository
from loopora.service_bundle_assets import ServiceBundleAssetMixin
from loopora.service_bundle_graph_preflight import BundleGraphLinks, preflight_bundle_graph_delete
from loopora.service_loop_records import ServiceLoopRecordMixin
from loopora.service_orchestration_assets import _strategy_source_counts
from loopora.strategy_source import strategy_source_from_record
from loopora.utils import write_json
from loopora.web_inputs import _orchestration_form_values_from_record, _orchestration_payload_from_mapping


def test_strategy_source_record_boundary_prefers_projection_over_storage_alias() -> None:
    strategy_source = {"roles": [{"id": "builder"}], "steps": [{"id": "build"}]}
    stale_storage_source = {"roles": [], "steps": []}

    assert strategy_source_from_record({"strategy_source": strategy_source, "workflow_json": stale_storage_source}) == strategy_source
    assert strategy_source_from_record({"workflow_json": stale_storage_source}) == stale_storage_source
    assert strategy_source_from_record({}) is None


def test_run_record_strategy_snapshot_prefers_projection_without_legacy_default() -> None:
    service = ServiceLoopRecordMixin()

    snapshot = service._strategy_source_snapshot_from_record(
        {"strategy_source": {"preset": "inspect_first"}, "workflow_json": {"preset": "build_first"}}
    )

    assert snapshot["preset"] == "inspect_first"
    assert service._strategy_source_snapshot_from_record({}) == {}
    assert service._normalized_strategy_source_from_record(
        {"strategy_source": {"preset": "inspect_first"}, "workflow_json": {"preset": "build_first"}}
    )["preset"] == "inspect_first"


def test_bundle_graph_preflight_uses_strategy_source_record_boundary_for_role_refs() -> None:
    class FakeRepository:
        def get_bundle_asset_owner(self, _asset_type: str, _asset_id: str) -> str:
            return "bundle_strategy"

        def get_orchestration(self, _orchestration_id: str) -> dict:
            return {
                "strategy_source": {"roles": [{"role_definition_id": "fresh_role"}], "steps": []},
                "workflow_json": {"roles": [{"role_definition_id": "stale_role"}], "steps": []},
            }

        def list_loops(self) -> list[dict]:
            return []

        def get_role_definition(self, role_definition_id: str) -> dict:
            return {"id": role_definition_id}

        def list_orchestrations(self) -> list[dict]:
            return []

    paths = preflight_bundle_graph_delete(
        FakeRepository(),
        {"id": "bundle_strategy"},
        BundleGraphLinks(loop_id="", orchestration_id="orch_strategy", role_definition_ids=["fresh_role"]),
    )

    assert paths == []


def test_agent_native_run_context_prefers_strategy_source_record_boundary(tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    layout = SimpleNamespace(
        contract_strategy_source_path=tmp_path / "strategy_source.json",
        contract_workflow_path=tmp_path / "workflow.json",
        run_contract_path=tmp_path / "run_contract.json",
    )
    write_json(layout.run_contract_path, {"id": "contract"})

    context = agent_native_run_context(
        {
            "id": "run_strategy",
            "runs_dir": str(run_dir),
            "strategy_source": {"preset": "inspect_first"},
            "workflow_json": {"preset": "build_first"},
            "compiled_spec_json": {},
            "max_role_retries": 1,
            "completion_mode": "gatekeeper",
        },
        {},
        layout=layout,
        executor=object(),
        prompt_files={},
    )

    assert context.strategy_source["preset"] == "inspect_first"


def test_cli_orchestration_list_counts_strategy_source_record_boundary(monkeypatch) -> None:
    class FakeService:
        def list_orchestrations(self) -> list[dict]:
            return [
                {
                    "id": "orch_strategy",
                    "name": "Strategy",
                    "source": "custom",
                    "strategy_source": {"roles": ["builder", "gatekeeper"], "steps": ["build"]},
                    "workflow_json": {"roles": [], "steps": []},
                }
            ]

    monkeypatch.setattr(cli, "create_service", FakeService)

    result = CliRunner().invoke(cli.app, ["orchestrations", "list"])

    assert result.exit_code == 0, result.stdout
    assert "roles=2" in result.stdout
    assert "steps=1" in result.stdout


def test_surface_strategy_source_inputs_prefer_projection_over_storage_alias(monkeypatch) -> None:
    record = {
        "name": "Strategy Form",
        "description": "",
        "strategy_source": {
            "preset": "inspect_first",
            "roles": [{"id": "builder", "archetype": "builder"}],
            "steps": [{"id": "build", "role_id": "builder"}],
        },
        "workflow_json": {"preset": "build_first", "roles": [], "steps": []},
    }

    class FakeService:
        def get_orchestration(self, orchestration_id: str) -> dict:
            assert orchestration_id == "orch_strategy"
            return record

    monkeypatch.setattr(cli_spec_support, "get_service", FakeService)

    form_values = _orchestration_form_values_from_record(record)
    cli_strategy_source = cli_spec_support.resolve_spec_template_strategy_source(
        orchestration_id="orch_strategy",
        strategy_preset="",
        strategy_file=None,
    )

    assert '"preset": "inspect_first"' in str(form_values["strategy_json"])
    assert form_values["workflow_json"] == form_values["strategy_json"]
    assert cli_strategy_source and cli_strategy_source["preset"] == "inspect_first"
    assert _strategy_source_counts(record) == (1, 1)


def test_orchestration_payload_uses_strategy_source_boundary_name() -> None:
    payload = _orchestration_payload_from_mapping({"name": "Strategy Payload", "strategy_source": {"preset": "inspect_first"}})

    assert payload["strategy_source"] == {"preset": "inspect_first"}
    assert "workflow" not in payload


def test_asset_catalog_orchestration_decoration_prefers_strategy_source_record_boundary(tmp_path) -> None:
    catalog = StrategyTemplateAssetCatalog(LooporaRepository(tmp_path / "app.db"))
    decorated = catalog._decorate_orchestration(
        {
            "id": "orch_strategy",
            "name": "Strategy",
            "workflow_json": {"roles": [], "steps": []},
            "strategy_source": {
                "roles": [{"id": "builder", "archetype": "builder"}, {"id": "inspector", "archetype": "inspector"}],
                "steps": [
                    {"id": "build", "role_id": "builder", "parallel_group": "review"},
                    {"id": "inspect", "role_id": "inspector", "parallel_group": "review"},
                ],
            },
        },
        source="custom",
    )

    assert decorated["parallel_groups"] == ["review"]
    assert decorated["parallel_group_count"] == 1


def test_bundle_snapshot_refresh_prefers_strategy_source_record_boundary() -> None:
    class FakeAssetCatalog:
        def resolve_orchestration_input(self, *, orchestration_id: str, workflow: dict, prompt_files: dict, role_models: dict) -> dict:
            return {
                "id": orchestration_id,
                "name": "Strategy",
                "workflow": workflow,
                "prompt_files": prompt_files,
                "role_models": role_models,
            }

    class FakeService(ServiceBundleAssetMixin):
        asset_catalog = FakeAssetCatalog()

        def get_orchestration(self, _orchestration_id: str) -> dict:
            return {
                "id": "orch_strategy",
                "name": "Strategy",
                "strategy_source": {"roles": [{"id": "fresh"}], "steps": [{"id": "fresh_step", "role_id": "fresh"}]},
                "workflow_json": {"roles": [{"id": "stale"}], "steps": []},
                "prompt_files_json": {"fresh.md": "body"},
            }

        def _refresh_bundle_role_snapshots(self, *, workflow: dict, prompt_files: dict, role_definition_ids: list[str]) -> tuple[dict, dict[str, str]]:
            assert role_definition_ids == ["role_fresh"]
            return workflow, dict(prompt_files)

        def _asset_call(self, callback, *args, **kwargs):
            return callback(*args, **kwargs)

    resolved = FakeService()._resolve_bundle_orchestration_for_snapshot(
        {"id": "bundle_strategy", "orchestration_id": "orch_strategy", "role_definition_ids": ["role_fresh"]},
        role_models={"fresh": "gpt-5.4"},
    )

    assert resolved["workflow"]["roles"][0]["id"] == "fresh"
    assert resolved["refreshed_workflow"]["roles"][0]["id"] == "fresh"

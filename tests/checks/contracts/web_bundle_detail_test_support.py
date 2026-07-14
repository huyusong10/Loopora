from __future__ import annotations

from pathlib import Path

from loopora.bundles import bundle_to_yaml
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_agent_adapters import AgentBundleCandidateRequest


def create_bundle_detail_loop(service, *, sample_spec_file: Path, sample_workdir: Path, name: str) -> dict:
    return service.create_loop(
        name=name,
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )


def import_derived_bundle(
    service,
    loop_id: str,
    *,
    name: str,
    description: str,
    collaboration_summary: str,
) -> dict:
    return service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop_id,
                name=name,
                description=description,
                collaboration_summary=collaboration_summary,
            )
        )
    )


def import_agent_first_bundle(service, *, tmp_path: Path, sample_workdir: Path) -> dict:
    bundle_file = tmp_path / "agent-first-bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Prepare an Agent-native plan file.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    return service.import_alignment_bundle(generated["session"]["id"], start_immediately=False)

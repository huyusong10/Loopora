from __future__ import annotations

from agent_bundle_candidates_test_support import (
    AgentBundleCandidateRequest,
    Path,
    TestClient,
    alignment_bundle_yaml,
    build_app,
    pytest,
    yaml,
)


def test_agent_bundle_candidate_rejects_task_context_mismatch(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Build a governed refund self-service flow with authorization, audit, and payment failure evidence.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert generated["requires_web_alignment"] is False
    assert generated["requires_candidate_repair"] is True
    assert generated["ready_candidate_sha256"] == ""
    assert generated["ready_candidate_bytes"] == 0
    assert generated["binding"]["requires_web_alignment"] is False
    assert generated["binding"]["requires_candidate_repair"] is True
    assert generated["binding"]["ready_candidate_sha256"] == ""
    assert generated["binding"]["ready_candidate_bytes"] == 0
    assert generated["session"].get("agent_entry_review", {}) == {}
    assert "host Agent task summary" in generated["session"]["error_message"]
    assert "refund" in generated["session"]["error_message"]
    assert "audit" in generated["session"]["error_message"]
    candidate_event = next(
        event for event in service.list_alignment_events(generated["session"]["id"]) if event["event_type"] == "agent_candidate_received"
    )
    assert candidate_event["payload"]["requires_candidate_repair"] is False
    assert candidate_event["payload"]["ready_candidate_sha256"] == ""
    assert candidate_event["payload"]["ready_candidate_bytes"] == 0
    assert any(
        event["event_type"] == "alignment_bundle_sync_failed"
        and "host Agent task summary" in event["payload"].get("error", "")
        for event in service.list_alignment_events(generated["session"]["id"])
    )


def test_agent_bundle_candidate_repair_session_keeps_web_plan_previewable(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Build a governed refund self-service flow with authorization, audit, and payment failure evidence.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["requires_candidate_repair"] is True
    client = TestClient(build_app(service=service))
    response = client.get(f"/api/alignments/sessions/{generated['session']['id']}/bundle")

    assert response.status_code == 200
    preview = response.json()
    assert preview["ok"] is True
    assert preview["session"]["status"] == "failed"
    assert preview["source_path"] == generated["session"]["bundle_path"]
    assert preview["validation"]["ok"] is False
    assert "host Agent task summary" in preview["validation"]["error"]
    assert preview["control_summary"]["coverage"]["target_count"] >= preview["control_summary"]["coverage"]["check_count"]
    assert preview["traceability"] == preview["control_summary"]["traceability"]


def test_agent_bundle_candidate_rejects_host_summary_that_says_loopora_not_fit(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    (sample_workdir / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
    (sample_workdir / "design").mkdir(exist_ok=True)
    (sample_workdir / "design" / "README.md").write_text("# Design\n", encoding="utf-8")
    (sample_workdir / "tests").mkdir(exist_ok=True)
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Fix a README typo. One Agent pass plus one human review is enough, "
                "and later rounds will create no new evidence."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "Loopora is not fit" in generated["session"]["error_message"]
    assert any(
        event["event_type"] == "alignment_bundle_sync_failed"
        and "Loopora is not fit" in event["payload"].get("error", "")
        for event in service.list_alignment_events(generated["session"]["id"])
    )


def test_agent_bundle_candidate_rejects_chinese_host_summary_that_says_loopora_not_fit(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="修一个 README 错字。一次 Agent 执行加人工 review 已经足够，后续不会产生新证据。",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert generated["requires_candidate_repair"] is True
    assert "Loopora is not fit" in generated["session"]["error_message"]


def test_agent_bundle_candidate_rejects_chinese_benchmark_only_host_summary(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="现有基准已经完全覆盖这次判断，直接跑基准就够了，不需要 Loopora。",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert generated["requires_candidate_repair"] is True
    assert "Loopora is not fit" in generated["session"]["error_message"]


def test_agent_bundle_candidate_rejects_chinese_no_loop_host_summary(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="不用 Loopora，直接让 Agent 做完再人工看一眼就行。",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert generated["requires_candidate_repair"] is True
    assert "Loopora is not fit" in generated["session"]["error_message"]


def test_agent_bundle_candidate_rejects_chinese_single_round_host_summary(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="这个任务跑一遍就行，不需要多轮，之后我人工确认即可。",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert generated["requires_candidate_repair"] is True
    assert "Loopora is not fit" in generated["session"]["error_message"]


@pytest.mark.parametrize(
    "message",
    [
        "这是一次性任务，不要长期循环。直接处理完即可。",
        "This is a one-off task; no Loopora loop is needed.",
        "There is no need for a Loopora loop here; just answer directly.",
        "A direct answer is enough; no future iteration will add proof.",
        "Just fix it once and I will review it manually.",
        "The stable proof harness already fully captures the judgment.",
        "现有契约测试已经完全覆盖这次判断，直接跑测试就够了。",
    ],
)
def test_agent_bundle_candidate_rejects_one_off_host_summary_variants(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
    message: str,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=message,
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert generated["requires_candidate_repair"] is True
    assert generated["loopora_fit_contradiction"] is True
    assert generated["binding"]["loopora_fit_contradiction"] is True
    assert "Loopora is not fit" in generated["session"]["error_message"]
    candidate_event = next(
        event for event in service.list_alignment_events(generated["session"]["id"]) if event["event_type"] == "agent_candidate_received"
    )
    assert candidate_event["payload"]["loopora_fit_contradiction"] is True


def test_agent_bundle_candidate_rejects_governance_markers_without_runtime_responsibilities(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["collaboration_summary"] += " AGENTS.md, design/README.md, design/, and tests/ are project-local governance markers."
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build the focused starter experience while following AGENTS.md, design/README.md, design/, "
                "and tests/ as runtime governance inputs."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "project-local governance markers" in generated["session"]["error_message"]
    assert "Builder reading" in generated["session"]["error_message"]


def test_agent_bundle_candidate_uses_workdir_snapshot_for_governance_markers(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    (sample_workdir / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
    (sample_workdir / "design").mkdir(exist_ok=True)
    (sample_workdir / "design" / "README.md").write_text("# Design\n", encoding="utf-8")
    (sample_workdir / "tests").mkdir(exist_ok=True)

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build the focused starter experience in the target workdir with small, maintainable changes "
                "that preserve the primary user flow."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "project-local governance markers" in generated["session"]["error_message"]

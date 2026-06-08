from __future__ import annotations

from agent_bundle_candidates_test_support import CliRunner, Path, _invoke_codex_plan, json, yaml


def test_cli_agent_plan_prompt_asset_ownership_rounds_use_contract_parallel_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-prompt-asset-ownership",
    }
    task_message = (
        "Plan a governed Loop to migrate all fixed system/developer prompt bodies out of Python code into versioned "
        "prompt assets. Success must prove Agent Native managed entries, role-agent instructions, Claude session "
        "additional context, runtime role prefixes, output contracts, alignment compiler main system prompt, shared "
        "proof/residual-risk guidance, and role metadata descriptions are selected from assets rather than hardcoded "
        "strings. The system prompt asset tree must not branch by user language or use locale-specific refs; Python may "
        "only select asset refs and pass structured runtime values. Fake done is moving only one prompt, leaving "
        "descriptions or dispatch snippets inline, putting language-specific .zh/.en system prompt files under "
        "system_prompts, or weakening tests to allow hardcoded long instruction strings."
    )

    first_summary = _invoke_prompt_asset_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_prompt_asset_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: treat prompt asset ownership as a contract-first migration. Start with Prompt Surface "
            "Contract Inspector reading design/contracts.md, existing prompt ownership tests, system_prompt_assets.py, "
            "Agent Native adapter templates, runtime role prompt surfaces, alignment guidance, and Strategy Source prompt "
            "asset boundaries. Builder then moves remaining fixed system/developer prompt bodies and role metadata "
            "instruction strings into system_prompts assets without adding language-specific branches. Run Prompt Asset "
            "Ownership Inspector and Runtime Prompt Rendering Inspector in parallel: Ownership Inspector verifies no long "
            "system-style instruction bodies remain in Python prompt/contract modules and no .zh/.en locale refs exist "
            "under system_prompts; Rendering Inspector verifies managed entries, role agents, headless/runtime prompts, "
            "alignment compiler prompt, Claude additional context, residual-risk/proof guidance, and role descriptions "
            "render unchanged and reject unresolved placeholders. GateKeeper must fail closed on inline prompt bodies, "
            "locale-specific system prompt assets, weakened tests, missing static asset refs, or user-editable Strategy "
            "Source presets leaking into fixed system prompt loading."
        ),
        env=env,
    )
    _assert_prompt_asset_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_prompt_asset_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this prompt asset ownership contract-first parallel evidence direction.",
        env=env,
    )
    _assert_prompt_asset_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _prompt_asset_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_prompt_asset_bundle(bundle_text)


def test_cli_agent_plan_chinese_prompt_asset_request_keeps_system_prompts_locale_neutral(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-prompt-asset-locale-neutral",
    }
    task_message = (
        "请规划一个 governed Loop：把所有固定 system/developer prompt body 从 Python 代码硬编码迁移到 "
        "system_prompts 资产里。成功必须证明 Agent Native managed entries、role-agent instructions、Claude "
        "session additional context、runtime role prefixes、output contracts、alignment compiler main system prompt、"
        "shared proof/residual-risk guidance 和 role metadata descriptions 都只从资产加载。系统提示词不应该按用户语言"
        "区分，不能新增 .zh/.en 或中文/英文分支；代码只能选择 asset refs 并传入结构化 runtime values。"
    )

    first_summary = _invoke_prompt_asset_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_prompt_asset_plan_round(
        runner,
        sample_workdir,
        message=(
            "补充判断：使用 Prompt Surface Contract Inspector 先读取 design/contracts.md、prompt ownership tests、"
            "system_prompt_assets.py、Agent Native adapter templates、runtime role prompt surfaces 和 alignment guidance，"
            "固定所有 fixed system prompt surface 与 locale-neutral system_prompt asset rules。Prompt Asset Builder 只能"
            "基于该 handoff 迁移剩余固定 prompt body，不能添加语言分支。Prompt Asset Ownership Inspector 与 "
            "Runtime Prompt Rendering Inspector 并行检查：前者验证 Python prompt/contract modules 没有 long "
            "system-style instruction bodies 且 system_prompts 下没有 .zh/.en locale refs；后者验证 managed entries、"
            "role agents、runtime/alignment/shared prompts、role descriptions 能渲染且拒绝 unresolved placeholders。"
            "GateKeeper 必须对 inline prompt bodies、locale-specific system prompt assets、弱化测试、缺少 static asset refs "
            "或 Strategy Source leakage fail closed。"
        ),
        env=env,
    )
    _assert_prompt_asset_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_prompt_asset_plan_round(
        runner,
        sample_workdir,
        message="确认；使用这条 locale-neutral system prompt asset ownership 方向。",
        env=env,
    )
    _assert_prompt_asset_ready_round(third_summary, first_summary["alignment_session_id"])
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    assert "确认；使用这条 locale-neutral system prompt asset ownership 方向" not in ready_projection_text
    bundle_text = _prompt_asset_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_prompt_asset_bundle(bundle_text)
    assert "locale-neutrality" in bundle_text
    assert "locale-i18n" not in bundle_text


def _invoke_prompt_asset_plan_round(
    runner: CliRunner,
    sample_workdir: Path,
    *,
    message: str,
    env: dict[str, str],
) -> dict:
    result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=message,
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    assert result.exit_code == 0, result.stdout
    return json.loads(result.stdout)["summary"]


def _assert_prompt_asset_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Prompt Surface Contract Inspector" in agreement_text
    assert "Prompt Asset Ownership Inspector" in agreement_text
    assert "Runtime Prompt Rendering Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "task anchor through an evidence-first repair Loop" not in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text


def _assert_prompt_asset_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in (
        "system/developer prompt",
        "role metadata",
        "system_prompt",
        "Strategy Source",
    ):
        assert term in ready_projection_text
    assert "Confirm; use this prompt asset ownership" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _prompt_asset_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_prompt_asset_bundle(bundle_text: str) -> None:
    workflow = yaml.safe_load(bundle_text)["workflow"]
    assert workflow["preset"] == "prompt-asset-ownership-contract-parallel-rendering"
    assert [step["id"] for step in workflow["steps"]] == [
        "prompt_surface_contract_inspection_step",
        "prompt_asset_builder_step",
        "prompt_asset_ownership_inspection_step",
        "runtime_prompt_rendering_inspection_step",
        "prompt_asset_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["prompt_surface_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "prompt_asset_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "prompt_asset_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "prompt_surface_contract_inspection_step",
        "prompt_asset_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "prompt_surface_contract_inspection_step",
        "prompt_asset_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "prompt_surface_contract_inspection_step",
        "prompt_asset_builder_step",
        "prompt_asset_ownership_inspection_step",
        "runtime_prompt_rendering_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "prompt-asset-ownership",
        "system-prompt-loading",
        "locale-neutrality",
        "runtime-rendering",
        "placeholder-safety",
        "static-asset-refs",
        "strategy-source-boundary",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "permission-auth" not in gatekeeper_verifies
    assert "locale-i18n" not in gatekeeper_verifies
    assert "Prompt Asset Ownership Workflow Notes" in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Confirm; use this prompt asset ownership" not in bundle_text
    assert "authorization and negative permission proof" not in bundle_text
    assert "locale formatting, translations" not in bundle_text

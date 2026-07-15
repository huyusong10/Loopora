from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from loopora.run_artifact_layout import RunArtifactLayout


RUN_ARTIFACT_SPECS = (
    {
        "id": "summary",
        "relative_path": "summary.md",
        "label_zh": "运行摘要",
        "label_en": "Summary",
        "description_zh": "当前运行的摘要结论。",
        "description_en": "The current run summary.",
    },
    {
        "id": "original-spec",
        "relative_path": "contract/spec.md",
        "label_zh": "原始 Loop 契约",
        "label_en": "Original spec",
        "description_zh": "这次运行开始时冻结保存的原始 Markdown 契约。",
        "description_en": "The original Markdown spec snapshot frozen at the start of this run.",
    },
    {
        "id": "compiled-spec",
        "relative_path": "contract/compiled_spec.json",
        "label_zh": "编译后契约",
        "label_en": "Compiled spec",
        "description_zh": "本次运行实际使用的任务、检查项、边界、流程意图、角色姿态、假完成风险、证据偏好、执行策略、判断取舍、本地治理责任和残余风险。",
        "description_en": "The Task, checks, Guardrails, workflow intent, role posture, Success Surface, Fake Done, Evidence Preferences, Execution Strategy, Judgment Tradeoffs, Local Governance, and Residual Risk used by this run.",
    },
    {
        "id": "strategy-source",
        "relative_path": "contract/strategy_source.json",
        "label_zh": "策略源",
        "label_en": "Strategy source",
        "description_zh": "这次运行冻结下来的策略源定义。",
        "description_en": "The strategy source definition frozen for this run.",
    },
    {
        "id": "workflow-manifest",
        "relative_path": "contract/workflow.json",
        "label_zh": "流程清单",
        "label_en": "Workflow manifest",
        "description_zh": "兼容旧读取方的策略源镜像。",
        "description_en": "A strategy source mirror kept for legacy readers.",
    },
    {
        "id": "run-contract",
        "relative_path": "contract/run_contract.json",
        "label_zh": "运行契约",
        "label_en": "Run contract",
        "description_zh": "本次运行冻结的完整运行时契约与稳定引用。",
        "description_en": "The frozen runtime contract and stable references for this run.",
    },
    {
        "id": "latest-state",
        "relative_path": "context/latest_state.json",
        "label_zh": "最新状态索引",
        "label_en": "Latest state",
        "description_zh": "当前运行的最新步骤、角色和轮次引用索引。",
        "description_en": "The latest step, role, and iteration references for this run.",
    },
    {
        "id": "latest-iteration-summary",
        "relative_path": "context/latest_iteration_summary.json",
        "label_zh": "最新轮次摘要",
        "label_en": "Latest iteration summary",
        "description_zh": "最近一轮的结构化摘要与得分信息。",
        "description_en": "The latest iteration summary and score details.",
    },
    {
        "id": "timeline-events",
        "relative_path": "timeline/events.jsonl",
        "label_zh": "事件时间线",
        "label_en": "Timeline events",
        "description_zh": "运行事件流的规范时间线。",
        "description_en": "The canonical event timeline for this run.",
    },
    {
        "id": "timeline-iterations",
        "relative_path": "timeline/iterations.jsonl",
        "label_zh": "轮次时间线",
        "label_en": "Timeline iterations",
        "description_zh": "每轮结构化摘要的规范时间线。",
        "description_en": "The canonical iteration summary timeline for this run.",
    },
    {
        "id": "timeline-metrics",
        "relative_path": "timeline/metrics.jsonl",
        "label_zh": "指标时间线",
        "label_en": "Timeline metrics",
        "description_zh": "每轮分数与停滞信息的规范时间线。",
        "description_en": "The canonical metric timeline for this run.",
    },
    {
        "id": "evidence-ledger",
        "relative_path": "evidence/ledger.jsonl",
        "label_zh": "证据账本",
        "label_en": "Evidence ledger",
        "description_zh": "本次运行的规范证据账本，记录证明了什么、没证明什么，以及结论对应的追查材料。",
        "description_en": "The canonical evidence ledger for this run: what was proven, what remains unproven, and which artifacts support each claim.",
    },
    {
        "id": "evidence-coverage",
        "relative_path": "evidence/coverage.json",
        "label_zh": "证据覆盖投影",
        "label_en": "Evidence coverage",
        "description_zh": "从运行契约与证据账本重算得到的覆盖投影，用于追溯收束结论。",
        "description_en": "A derived coverage projection rebuilt from the run contract and evidence ledger for tracing closure decisions.",
    },
    {
        "id": "evidence-manifest",
        "relative_path": "evidence/manifest.json",
        "label_zh": "证据清单",
        "label_en": "Evidence manifest",
        "description_zh": "从证据账本和覆盖投影派生的 claim、producer、proof artifact 与可复验状态索引。",
        "description_en": "A derived claim, producer, proof artifact, and verification-state index rebuilt from the evidence ledger and coverage projection.",
    },
    {
        "id": "task-verdict",
        "relative_path": "evidence/task_verdict.json",
        "label_zh": "Loop 裁决",
        "label_en": "Task verdict",
        "description_zh": "终态 Loop 裁决，说明证据是否足以支持通过、拒绝或保留残余风险。",
        "description_en": "The final task verdict explaining whether evidence supports a pass, rejection, or accepted residual risk.",
    },
)

STEP_ARTIFACT_FILENAMES = {
    "step_instruction_context.json",
    "prompt.md",
    "output.raw.json",
    "output.normalized.json",
    "handoff.json",
    "metadata.json",
}


def list_run_artifacts(run: dict) -> list[dict]:
    from loopora.run_artifact_layout import RunArtifactLayout

    layout = RunArtifactLayout(Path(run["runs_dir"]))
    artifacts: list[dict] = []
    for artifact in RUN_ARTIFACT_SPECS:
        path = layout.run_dir / artifact["relative_path"]
        artifacts.append(
            {
                **artifact,
                "filename": artifact["relative_path"],
                "path": str(path),
                "available": _is_available_run_artifact_path(layout, path),
            }
        )
    if layout.contract_prompts_dir.exists():
        for prompt_path in sorted(
            path for path in layout.contract_prompts_dir.rglob("*.md") if _is_available_run_artifact_path(layout, path)
        ):
            relative_path = layout.relative(prompt_path)
            artifacts.append(
                {
                    "id": f"prompt-{artifact_slug(relative_path)}",
                    "filename": relative_path,
                    "relative_path": relative_path,
                    "label_zh": f"提示词 · {prompt_path.name}",
                    "label_en": f"Prompt · {prompt_path.name}",
                    "description_zh": "这次运行冻结保存的角色提示词 Markdown。",
                    "description_en": "The role prompt Markdown frozen for this run.",
                    "path": str(prompt_path),
                    "available": True,
                }
            )
    if layout.iterations_dir.exists():
        for artifact_path in sorted(layout.iterations_dir.rglob("*")):
            if artifact_path.name not in STEP_ARTIFACT_FILENAMES or not _is_available_run_artifact_path(layout, artifact_path):
                continue
            relative_path = layout.relative(artifact_path)
            label_prefix = "Step prompt" if artifact_path.name == "prompt.md" else "Step artifact"
            label_prefix_zh = "步骤提示词" if artifact_path.name == "prompt.md" else "步骤产物"
            artifacts.append(
                {
                    "id": f"step-{artifact_slug(relative_path)}",
                    "filename": relative_path,
                    "relative_path": relative_path,
                    "label_zh": f"{label_prefix_zh} · {relative_path}",
                    "label_en": f"{label_prefix} · {relative_path}",
                    "description_zh": "按步骤冻结保存的上下文、提示词、元数据或输出快照。",
                    "description_en": "A step-scoped context, prompt, metadata, or output snapshot.",
                    "path": str(artifact_path),
                    "available": True,
                }
            )
    return artifacts


def _is_available_run_artifact_path(layout: RunArtifactLayout, path: Path) -> bool:
    try:
        resolved_root = layout.run_dir.resolve()
        resolved_path = path.resolve()
    except (OSError, RuntimeError):
        return False
    return resolved_path.is_relative_to(resolved_root) and resolved_path.is_file()


def artifact_slug(relative_path: str) -> str:
    return relative_path.replace("/", "-").replace("\\", "-").replace(".", "-")

from __future__ import annotations

from dataclasses import asdict, dataclass

EXECUTOR_KINDS = ("codex", "claude", "opencode", "custom")
CLAUDE_DEFAULT_MODEL = ""
OPENCODE_DEFAULT_MODEL = ""
EXECUTOR_KIND_ALIASES = {
    "codex": "codex",
    "openai-codex": "codex",
    "claude": "claude",
    "claudecode": "claude",
    "claude-code": "claude",
    "claude_code": "claude",
    "opencode": "opencode",
    "open-code": "opencode",
    "open_code": "opencode",
    "custom": "custom",
}
EXECUTOR_MODES = ("preset", "command")


@dataclass(frozen=True, slots=True)
class ExecutorProfile:
    key: str
    label: str
    label_zh: str
    cli_name: str
    default_model: str
    model_placeholder_zh: str
    model_placeholder_en: str
    model_help_zh: str
    model_help_en: str
    effort_label_zh: str
    effort_label_en: str
    effort_help_zh: str
    effort_help_en: str
    effort_options: tuple[str, ...]
    effort_default: str
    effort_optional: bool = False
    preset_effort_visible: bool = True
    command_only: bool = False
    command_required_placeholders: tuple[str, ...] = ("{prompt}",)
    command_args_template: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


EXECUTOR_PROFILES: dict[str, ExecutorProfile] = {
    "codex": ExecutorProfile(
        key="codex",
        label="Codex",
        label_zh="Codex",
        cli_name="codex",
        default_model="",
        model_placeholder_zh="留空使用 Codex CLI 当前默认模型，或填完整模型名",
        model_placeholder_en="Leave blank to use the current Codex CLI default, or enter a full model name",
        model_help_zh="使用本机 Codex CLI。默认留空更稳妥，让 Codex CLI 跟随当前默认模型；只有需要固定模型时再填写。",
        model_help_en="Uses the local Codex CLI. Leaving the model blank lets Codex CLI use its current default; set a value only when you need to pin a model.",
        effort_label_zh="推理强度",
        effort_label_en="Reasoning effort",
        effort_help_zh="留空使用 Codex CLI 当前默认推理强度；只有需要固定时再选择 low、medium、high 或 xhigh。",
        effort_help_en="Leave blank to use the current Codex CLI default reasoning effort; set low, medium, high, or xhigh only when you need to pin it.",
        effort_options=("", "low", "medium", "high", "xhigh"),
        effort_default="",
        effort_optional=True,
        command_required_placeholders=("{prompt}", "{output_path}", "{schema_path}"),
        command_args_template=(
            "exec",
            "--json",
            "--skip-git-repo-check",
            "--cd",
            "{workdir}",
            "--sandbox",
            "{sandbox}",
            "--output-schema",
            "{schema_path}",
            "--output-last-message",
            "{output_path}",
            "{prompt}",
        ),
    ),
    "claude": ExecutorProfile(
        key="claude",
        label="Claude Code",
        label_zh="Claude Code",
        cli_name="claude",
        default_model=CLAUDE_DEFAULT_MODEL,
        model_placeholder_zh="留空使用 Claude Code 当前默认模型，或填 sonnet / opus / 完整模型名",
        model_placeholder_en="Leave blank to use the current Claude Code default, or enter sonnet / opus / a full model name",
        model_help_zh="使用本机 Claude Code CLI。默认留空更稳妥，让 Claude Code 跟随当前默认模型；只有需要固定模型时再填写。",
        model_help_en="Uses the local Claude Code CLI. Leaving the model blank lets Claude Code use its current default; set a value only when you need to pin a model.",
        effort_label_zh="推理强度",
        effort_label_en="Effort",
        effort_help_zh="留空使用 Claude Code 当前默认推理强度；只有需要固定时再选择 low、medium、high 或 max。旧的 xhigh 会自动映射为 max。",
        effort_help_en="Leave blank to use the current Claude Code default effort; set low, medium, high, or max only when you need to pin it. Legacy xhigh is mapped to max.",
        effort_options=("", "low", "medium", "high", "max"),
        effort_default="",
        effort_optional=True,
        command_required_placeholders=("{prompt}", "{json_schema}"),
        command_args_template=(
            "--setting-sources",
            "user,project,local",
            "-p",
            "--output-format",
            "stream-json",
            "--include-partial-messages",
            "--no-session-persistence",
            "--permission-mode",
            "bypassPermissions",
            "--json-schema",
            "{json_schema}",
            "{prompt}",
        ),
    ),
    "opencode": ExecutorProfile(
        key="opencode",
        label="OpenCode",
        label_zh="OpenCode",
        cli_name="opencode",
        default_model=OPENCODE_DEFAULT_MODEL,
        model_placeholder_zh="留空使用 OpenCode 当前默认模型，或填 provider/model",
        model_placeholder_en="Leave blank to use the current OpenCode default, or enter provider/model",
        model_help_zh="使用本机 OpenCode CLI。默认留空更稳妥，让 OpenCode 跟随当前默认模型；只有需要固定模型时再填写。",
        model_help_en="Uses the local OpenCode CLI. Leaving the model blank lets OpenCode use its current default; set a value only when you need to pin a model.",
        effort_label_zh="Variant（可选）",
        effort_label_en="Variant (optional)",
        effort_help_zh="OpenCode 走 provider-specific variant。可留空使用默认，也可以填 high、max、minimal、xhigh 等。",
        effort_help_en="OpenCode uses provider-specific variants. Leave it blank for the default, or set values like high, max, minimal, or xhigh.",
        effort_options=("", "high", "max", "minimal", "low", "medium", "xhigh", "none"),
        effort_default="",
        effort_optional=True,
        command_required_placeholders=("{prompt}",),
        command_args_template=(
            "run",
            "--format",
            "json",
            "--dir",
            "{workdir}",
            "--dangerously-skip-permissions",
            "{prompt}",
        ),
    ),
    "custom": ExecutorProfile(
        key="custom",
        label="Custom Command",
        label_zh="自定义命令",
        cli_name="",
        default_model="",
        model_placeholder_zh="直接命令模式下不再单独配置模型；如有需要，请把模型写进命令参数里",
        model_placeholder_en="Model is not configured separately in direct-command mode; put it in the command arguments if needed",
        model_help_zh="自定义执行工具只支持直接命令模式。Loopora 不会为它自动拼预设命令。",
        model_help_en="Custom execution tools only support direct-command mode. Loopora does not assemble a preset command for them.",
        effort_label_zh="推理强度",
        effort_label_en="Reasoning effort",
        effort_help_zh="自定义命令不提供固定推理强度选项；如有需要，请把对应参数直接写进命令里。",
        effort_help_en="Custom commands do not offer a fixed reasoning selector; pass any equivalent setting directly in the command.",
        effort_options=("",),
        effort_default="",
        effort_optional=True,
        preset_effort_visible=False,
        command_only=True,
        command_required_placeholders=("{prompt}", "{output_path}"),
    ),
}

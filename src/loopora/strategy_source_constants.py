from __future__ import annotations

from pathlib import Path

ARCHETYPES = ("builder", "inspector", "gatekeeper", "guide", "custom")
STRATEGY_SOURCE_VERSION = 1
LEGACY_ROLE_TO_ARCHETYPE = {
    "generator": "builder",
    "tester": "inspector",
    "verifier": "gatekeeper",
    "challenger": "guide",
    "builder": "builder",
    "inspector": "inspector",
    "gatekeeper": "gatekeeper",
    "guide": "guide",
    "custom": "custom",
}
ARCHETYPE_DISPLAY = {
    "builder": {"zh": "构建者", "en": "Builder"},
    "inspector": {"zh": "巡检者", "en": "Inspector"},
    "gatekeeper": {"zh": "守门者", "en": "GateKeeper"},
    "guide": {"zh": "引导者", "en": "Guide"},
    "custom": {"zh": "自定义角色", "en": "Custom Role"},
}
ARCHETYPE_DISPLAY_ALIASES = {
    "builder": {"构建者", "建造者", "generator", "builder"},
    "inspector": {"巡检者", "tester", "inspector"},
    "gatekeeper": {"守门者", "守门人", "verifier", "gatekeeper"},
    "guide": {"引导者", "向导", "challenger", "guide"},
    "custom": {"自定义角色", "custom role", "custom"},
}
LEGACY_ROLE_BY_ARCHETYPE = {
    "builder": "generator",
    "inspector": "tester",
    "gatekeeper": "verifier",
    "guide": "challenger",
}
PROMPT_FILES = {
    "builder": "builder.md",
    "inspector": "inspector.md",
    "gatekeeper": "gatekeeper.md",
    "gatekeeper-benchmark": "gatekeeper-benchmark.md",
    "guide": "guide.md",
    "custom": "custom.md",
}
PROMPT_ASSET_DIR = Path(__file__).parent / "assets" / "prompts"
SPEC_PRACTICE_ASSET_DIR = Path(__file__).parent / "assets" / "spec_practices"
ROLE_EXECUTION_FIELDS = (
    "executor_kind",
    "executor_mode",
    "command_cli",
    "command_args_text",
    "model",
    "reasoning_effort",
)
ROLE_POSTURE_FIELDS = ("posture_notes",)

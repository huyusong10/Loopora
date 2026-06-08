from __future__ import annotations

from loopora.system_prompt_assets import load_system_prompt_asset

PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE = load_system_prompt_asset("shared/proof-command-output.md").strip()

INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE = load_system_prompt_asset("shared/inspector-primary-proof.md").strip()

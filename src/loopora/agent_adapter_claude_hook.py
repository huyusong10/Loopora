from __future__ import annotations

"""Claude Code session-context hook assets."""

from loopora.system_prompt_assets import load_system_prompt_asset

CLAUDE_SETTINGS_RELATIVE_PATH = ".claude/settings.json"
CLAUDE_SESSION_HOOK_RELATIVE_PATH = ".claude/hooks/loopora-session-context.py"
CLAUDE_SESSION_CONTEXT_RELATIVE_PATH = ".claude/hooks/loopora-session-context.additional-context.md"
CLAUDE_SESSION_HOOK_SETTINGS_REF = ".claude/settings.json#hooks.SessionStart.loopora"
CLAUDE_SESSION_HOOK_COMMAND = 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/loopora-session-context.py"'
CLAUDE_SESSION_HOOK_GROUP = {
    "matcher": "startup|resume|clear|compact",
    "hooks": [
        {
            "type": "command",
            "command": CLAUDE_SESSION_HOOK_COMMAND,
            "timeout": 5,
        }
    ],
}


def claude_session_additional_context() -> str:
    return load_system_prompt_asset("agent_native/claude-session-additional-context.md").strip() + "\n"


def claude_session_hook_script(*, marker: str, version: int) -> str:
    return f"""#!/usr/bin/env python3
# {marker} version={version} file=loopora-session-context
from __future__ import annotations

import json
import os
import shlex
import sys


def _read_additional_context() -> str:
    context_path = os.path.join(os.path.dirname(__file__), "loopora-session-context.additional-context.md")
    try:
        with open(context_path, encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return (
            f"Loopora Claude session context asset is missing at {{context_path}}; "
            "run `loopora init claude --check` to restore managed files."
        )


def _main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{{}}")
    except json.JSONDecodeError:
        payload = {{}}
    if not isinstance(payload, dict):
        payload = {{}}

    session_id = str(payload.get("session_id") or "").strip()
    transcript_path = str(payload.get("transcript_path") or "").strip()
    context_id = session_id or transcript_path
    env_file = os.environ.get("CLAUDE_ENV_FILE", "").strip()
    if env_file and context_id:
        with open(env_file, "a", encoding="utf-8") as handle:
            handle.write(f"export CLAUDE_SESSION_ID={{shlex.quote(context_id)}}\\n")
            handle.write(f"export LOOPORA_AGENT_SESSION_ID={{shlex.quote(context_id)}}\\n")
        if transcript_path:
            with open(env_file, "a", encoding="utf-8") as handle:
                handle.write(f"export LOOPORA_CLAUDE_TRANSCRIPT_PATH={{shlex.quote(transcript_path)}}\\n")

    additional_context = _read_additional_context()
    output = {{
        "hookSpecificOutput": {{
            "hookEventName": "SessionStart",
            "additionalContext": additional_context,
        }}
    }}
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
"""

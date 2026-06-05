from __future__ import annotations

"""Claude Code session-context hook assets."""

CLAUDE_SETTINGS_RELATIVE_PATH = ".claude/settings.json"
CLAUDE_SESSION_HOOK_RELATIVE_PATH = ".claude/hooks/loopora-session-context.py"
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


def claude_session_hook_script(*, marker: str, version: int) -> str:
    return f"""#!/usr/bin/env python3
# {marker} version={version} file=loopora-session-context
from __future__ import annotations

import json
import os
import shlex
import sys


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

    additional_context = (
        "Loopora managed Agent entries are already project-local for this workspace. "
        "If the user asks for /loopora-plan, /loopora-run, or both phases, do not perform entry-discovery or "
        "availability preflight probes. Forbidden probes include binary/PATH checks (`which loopora`, "
        "`command -v loopora`, `type loopora`, `echo $PATH`), help/version/init/check probes (`loopora --version`, "
        "`loopora --help`, `loopora init claude`, `loopora agent claude check`), parent-directory inspection, broad "
        "project/file discovery, directory walks, and shell-filtered listings such as `find`, `ls ... | head`, "
        "`head`, `tail`, `sed`, `jq`, `grep`, or `wc`. "
        "Use exact known project paths (`.claude/skills/loopora-plan/SKILL.md`, "
        "`.claude/skills/loopora-plan/references/loopora-plan-contract.md`, "
        "`.claude/skills/loopora-run/SKILL.md`, and "
        "`.claude/skills/loopora-run/references/loopora-run-contract.md`) plus the host Read tool when managed "
        "references are needed; do not inspect `$HOME/.claude` or run `find /` to locate entries. The explicit "
        "`loopora agent claude plan/run ... --json --compact-json` command is the capability check. "
        "Do not run the combined preflight `which loopora && loopora --version`, directory-listing preflights such "
        "as `ls`, or any PATH/help/init/check probe after reading the managed entries. "
        "For /loopora-plan, author the candidate file under .loopora/agent_inbox/claude/ first, then run "
        "`LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan --workdir \\\"$PWD\\\" "
        "--context-id \\\"$CLAUDE_SESSION_ID\\\" --message \\\"<task summary>\\\" --bundle-file <candidate> "
        "--entry-source claude_project_skill --json --compact-json` as the first Loopora command. "
        "For /loopora-run, run the managed run command and dispatch roles only after Loopora Core returns next_step. "
        "If preserving managed JSON or runtime snapshots, write them under the workdir, not `/tmp`."
    )
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

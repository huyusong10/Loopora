from __future__ import annotations

from loopora.kernel import ActorRef


def agent_runner_actor(adapter: str) -> ActorRef:
    normalized_adapter = str(adapter or "").strip()
    return ActorRef(
        kind="agent",
        id=normalized_adapter,
        display_name=normalized_adapter,
        adapter=normalized_adapter,
    )

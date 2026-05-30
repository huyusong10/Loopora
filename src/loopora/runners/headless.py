from __future__ import annotations

from loopora.kernel import ActorRef


def headless_runner_actor() -> ActorRef:
    return ActorRef(kind="runner", id="headless", display_name="Headless Runner")

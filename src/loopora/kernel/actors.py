from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActorRef:
    kind: str
    id: str
    display_name: str = ""
    adapter: str = ""

    @classmethod
    def system(cls) -> ActorRef:
        return cls(kind="system", id="loopora", display_name="Loopora")

    @classmethod
    def verdict_engine(cls) -> ActorRef:
        return cls(kind="system", id="verdict-engine", display_name="Verdict Engine")

    def to_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "id": self.id,
            "display_name": self.display_name,
            "adapter": self.adapter,
        }

    @classmethod
    def from_dict(cls, payload: object) -> ActorRef:
        if not isinstance(payload, dict):
            return cls.system()
        return cls(
            kind=str(payload.get("kind") or "system"),
            id=str(payload.get("id") or "loopora"),
            display_name=str(payload.get("display_name") or ""),
            adapter=str(payload.get("adapter") or ""),
        )

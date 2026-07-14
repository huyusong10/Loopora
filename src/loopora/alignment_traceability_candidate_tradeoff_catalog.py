from __future__ import annotations

"""Agent-candidate traceability tradeoff category catalogs."""

TRADEOFF_MARKER_PATTERNS = (
    r"\b(?:proof|evidence|verify|verification)\b.{0,80}\b(?:over|before|rather than|instead of)\b.{0,80}\b(?:speed|fast|quick|polish|ui|narrative|story)\b",
    r"\b(?:speed|fast|quick|polish|ui|narrative|story)\b.{0,80}\b(?:wait|after|behind|until|rather than|instead of)\b.{0,80}\b(?:proof|evidence|verify|verification)\b",
    r"\b(?:strict|blocking|block|reject|fail closed)\b.{0,80}\b(?:over|before|rather than|instead of|beats?)\b.{0,80}\b(?:pragmatic|pragmatism|progress)\b",
    r"\b(?:pragmatic|pragmatism|progress)\b.{0,80}\b(?:wait|after|behind|until|rather than|instead of)\b.{0,80}\b(?:strict|blocking|block|reject|fail closed)\b",
    r"\b(?:prioriti[sz]e|prefer)\b.{0,80}\b(?:proof|evidence|verify|verification|blocking|fail closed)\b",
    r"\b(?:block|reject|fail closed)\b.{0,80}\b(?:fake[- ]?done|fake completion|polished-looking|narrative)\b",
    r"(?:优先|先).{0,24}(?:证明|证据|验证|阻断)",
    r"(?:证明|证据|验证|阻断).{0,24}(?:优先|先于|高于)",
    r"(?:严格|阻断|拒绝).{0,20}(?:优先|先于|高于).{0,20}(?:务实|推进|进度)",
    r"(?:务实|推进|进度).{0,20}(?:等|让位|后于).{0,20}(?:严格|阻断|拒绝)",
    r"(?:先别|不要|别).{0,16}(?:美化|润色|打磨|漂亮|界面)",
    r"(?:阻断|拒绝).{0,20}(?:假完成|漂亮叙事|证据不足)",
)


TRADEOFF_CATEGORY_PATTERNS = (
    (
        "proof/evidence",
        r"\b(?:proof|prove|proven|evidence|verify|verification)\b|证明|证据|验证|已证明",
    ),
    (
        "speed/polish",
        r"\b(?:speed|fast|quick|polish|ui|narrative|story|pretty|polished-looking)\b|速度|快速|美化|润色|打磨|界面|漂亮|叙事",
    ),
    (
        "blocking/fake-completion",
        r"\b(?:block|blocking|reject|fail closed|fake[- ]?done|fake completion|unproven|weak)\b|阻断|拒绝|假完成|未证明|弱证据|证据不足",
    ),
    (
        "pragmatic/progress",
        r"\b(?:pragmatic|pragmatism|progress)\b|务实|推进|进度",
    ),
)

__all__ = (
    "TRADEOFF_CATEGORY_PATTERNS",
    "TRADEOFF_MARKER_PATTERNS",
)

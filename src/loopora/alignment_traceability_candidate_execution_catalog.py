from __future__ import annotations

"""Agent-candidate traceability execution-strategy category catalogs."""

EXECUTION_STRATEGY_MARKER_PATTERNS = (
    r"\b(?:execution strategy|next round|next pass|priority|priorities)\b",
    r"\b(?:first|before|then|after|defer|prioriti[sz]e|start with|do not start|don't start|avoid)\b",
    r"(?:执行策略|下一轮|下一步|优先级|优先|先|再|然后|之后|暂缓|推迟|先别|不要先|别先)",
)


EXECUTION_STRATEGY_CATEGORY_PATTERNS = (
    (
        "repair/root-cause",
        r"\b(?:root[- ]?cause|regression|failure|failing|bug)\b|根因|故障|失败|回归|缺陷",
    ),
    (
        "evidence/proof",
        r"\b(?:proof|prove|proven|evidence|verify|verification|audit|test|tests)\b|证明|证据|验证|审计|测试|已证明",
    ),
    (
        "scope/narrow",
        r"\b(?:scope|narrow|focused|focus|small|minimal|limit|bounded)\b|范围|收窄|聚焦|小而|最小|有限",
    ),
    (
        "expand/breadth",
        r"\b(?:expand|expansion|broaden|broad|breadth|new feature|dashboard|report)\b|扩展|扩大|铺开|宽泛|新功能|看板|报表",
    ),
    (
        "polish/ui",
        r"\b(?:polish|ui|visual|pretty|styling|copy|narrative|story)\b|美化|打磨|润色|界面|视觉|文案|叙事|漂亮",
    ),
)

__all__ = (
    "EXECUTION_STRATEGY_CATEGORY_PATTERNS",
    "EXECUTION_STRATEGY_MARKER_PATTERNS",
)

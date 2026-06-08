from __future__ import annotations

"""Regex pattern catalogs for bundle-control trace mining."""

TRADEOFF_PATTERNS = (
    r"\bprefer\b.{0,120}\b(over|rather than|instead of|before|to)\b",
    r"\b(rather than|instead of)\b",
    r"\b(reject|block|fail closed)\b.{0,120}\b(when|if|over|rather than|instead|weak|speed|proof|evidence|fake[- ]done)\b",
    r"\b(proof|evidence)\b.{0,80}\b(before|over|beats?|wins?|must beat|higher than|above)\b.{0,80}\b(speed|polish|surface|breadth|completion|progress)\b",
    r"\b(speed|polish|surface completeness|progress)\b.{0,80}\b(loses?|must lose|rejected|blocked)\b.{0,80}\b(proof|evidence)\b",
    r"\b(strict|blocking|block|reject|fail closed)\b.{0,80}\b(before|over|beats?|wins?|rather than|instead of)\b.{0,80}\b(pragmatic|pragmatism|progress)\b",
    r"\b(pragmatic|pragmatism|progress)\b.{0,80}\b(loses?|must lose|wait|after|behind|rather than|instead of)\b.{0,80}\b(strict|blocking|block|reject|fail closed)\b",
    r"\bpreferir\b.{0,120}\b(?:sobre|antes que|frente a)\b",
    r"\bvelocidad\b.{0,80}\b(?:pierde|cede|debe perder)\b.{0,80}\b(?:evidencia|prueba|bloqueo|estricto)\b",
    r"\b(?:bloquear|rechazar|fallar cerrado|falla cerrado)\b.{0,120}\b(?:evidencia|prueba|falso terminado|no probado|débil)\b",
    r"(优先|先).{0,80}(而不是|不是|先于|高于|超过|证明|证据|阻断|拒绝)",
    r"(而不是|先于|高于)",
    r"(拒绝|阻断|失败关闭).{0,80}(速度|美化|漂亮|证据|证明|假完成|未证明|薄弱|不足)",
    r"(证据|证明).{0,80}(优先|先于|高于).{0,80}(速度|进度|美化|漂亮|完整)",
    r"(严格|阻断|拒绝).{0,80}(优先|先于|高于|超过|胜过).{0,80}(务实|推进|进度)",
    r"(务实|推进|进度).{0,80}(让位|低于|后于|等待).{0,80}(严格|阻断|拒绝)",
)

HIGH_SIGNAL_TRADEOFF_PATTERNS = (
    r"\b(proof|evidence)\b.{0,80}\b(before|over|beats?|wins?|must beat|higher than|above)\b.{0,80}\b(speed|polish|surface|breadth|completion|progress)\b",
    r"\b(speed|polish|surface completeness|progress)\b.{0,80}\b(loses?|must lose|rejected|blocked)\b.{0,80}\b(proof|evidence)\b",
    r"\b(strict|blocking|block|reject|fail closed)\b.{0,80}\b(before|over|beats?|wins?|rather than|instead of)\b.{0,80}\b(pragmatic|pragmatism|progress)\b",
    r"\b(pragmatic|pragmatism|progress)\b.{0,80}\b(loses?|must lose|wait|after|behind|rather than|instead of)\b.{0,80}\b(strict|blocking|block|reject|fail closed)\b",
    r"\b(reject|block|fail closed)\b.{0,120}\b(weak|proof|evidence|fake[- ]done|unproven|completion)\b",
    r"\bvelocidad\b.{0,80}\b(?:pierde|cede|debe perder)\b.{0,80}\b(?:evidencia|prueba|bloqueo|estricto)\b",
    r"\b(?:bloquear|rechazar|fallar cerrado|falla cerrado)\b.{0,120}\b(?:evidencia|prueba|falso terminado|no probado|débil)\b",
    r"(证据|证明).{0,80}(优先|先于|高于).{0,80}(速度|进度|美化|漂亮|完整)",
    r"(严格|阻断|拒绝).{0,80}(优先|先于|高于|超过|胜过).{0,80}(务实|推进|进度)",
    r"(务实|推进|进度).{0,80}(让位|低于|后于|等待).{0,80}(严格|阻断|拒绝)",
    r"(拒绝|阻断|失败关闭).{0,80}(假完成|未证明|薄弱|不足)",
)

EXECUTION_STRATEGY_PATTERNS = (
    r"\b(?:execution\s+priorit(?:y|ies)|order\s+of\s+attack|priority\s+order)\b.{0,140}\b(?:build|implement|prove|proof|evidence|repair|fix|narrow|scope|expand|polish|closure|gatekeeper|inspect|review)\b",
    r"\b(?:build|implement|prove|proof|evidence|repair|fix|narrow|scope|expand|polish|inspect|review)\b.{0,140}\b(?:execution\s+priorit(?:y|ies)|order\s+of\s+attack|priority\s+order)\b",
    r"\b(?:first|next|then|before|after|defer|postpone|hold off|delay|pause|prioriti[sz]e)\b.{0,120}\b(?:build|prove|evidence|repair|fix|narrow|scope|expand|polish|closure|gatekeeper|inspect|review)\b",
    r"\b(?:build|prove|gather|collect|repair|fix|narrow|scope|expand|polish|inspect|review)\b.{0,120}\b(?:first|next|then|before|after|defer|postpone|hold off|delay|pause|prioriti[sz]e)\b",
    r"\b(?:root cause|primary flow|focused slice|smallest real flow|direct proof|evidence gap|weak proof)\b.{0,120}\b(?:first|before|defer|repair|narrow|expand|polish)\b",
    r"\b(?:future|later|next)\s+(?:rounds?|iterations?|passes?)\b.{0,120}\b(?:build|prove|evidence|repair|narrow|expand|defer|polish)\b",
    r"\b(?:construir|implementar|probar|reparar|acotar|ampliar|diferir|inspeccionar|revisar)\b.{0,140}\b(?:primero|despu[eé]s|luego|antes|priorizar|prioridad|estrategia|ejecuci[oó]n)\b",
    r"\b(?:primero|despu[eé]s|luego|antes|priorizar|prioridad|estrategia|ejecuci[oó]n)\b.{0,140}\b(?:construir|implementar|probar|evidencia|reparar|acotar|ampliar|diferir|inspeccionar|revisar)\b",
    r"\b(?:cierre real m[ií]nimo|ruta negativa|evidencia d[eé]bil|brecha de evidencia)\b.{0,120}\b(?:primero|reparar|acotar|inspeccionar|cerrar)\b",
    r"(?:先|首先|下一轮|下一步|再|然后|之后|暂缓|推迟|先别|不要先|优先).{0,80}(?:构建|实现|证明|取证|证据|修复|根因|收窄|范围|扩展|打磨|美化|裁决)",
    r"(?:构建|实现|证明|取证|证据|修复|根因|收窄|范围|扩展|打磨|美化|裁决).{0,80}(?:先|首先|下一轮|下一步|再|然后|之后|暂缓|推迟|先别|不要先|优先)",
)

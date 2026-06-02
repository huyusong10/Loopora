from __future__ import annotations

"""Traceability category classifiers for alignment agreement and Agent candidates."""

import re

from loopora.alignment_traceability_risk_categories import (
    agent_candidate_evidence_preference_categories as agent_candidate_evidence_preference_categories,
    agent_candidate_fake_done_categories as agent_candidate_fake_done_categories,
)


def agent_candidate_tradeoff_categories(task_text: str) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    explicit_tradeoff_markers = (
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
    if not any(re.search(pattern, text, re.IGNORECASE) for pattern in explicit_tradeoff_markers):
        return []
    category_patterns = (
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
    return [(label, pattern) for label, pattern in category_patterns if re.search(pattern, text, re.IGNORECASE)]


def agent_candidate_has_labeled_execution_strategy(task_text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:execution strategy|priority|priorities|priority order|next round|next pass)\b|执行策略|优先级|下一轮|下一步",
            str(task_text or ""),
            re.IGNORECASE,
        )
    )


def agent_candidate_execution_strategy_categories(task_text: str, *, require_explicit_marker: bool = True) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    explicit_strategy_markers = (
        r"\b(?:execution strategy|next round|next pass|priority|priorities)\b",
        r"\b(?:first|before|then|after|defer|prioriti[sz]e|start with|do not start|don't start|avoid)\b",
        r"(?:执行策略|下一轮|下一步|优先级|优先|先|再|然后|之后|暂缓|推迟|先别|不要先|别先)",
    )
    if require_explicit_marker and not any(re.search(pattern, text, re.IGNORECASE) for pattern in explicit_strategy_markers):
        return []
    category_patterns = (
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
    return [(label, pattern) for label, pattern in category_patterns if re.search(pattern, text, re.IGNORECASE)]


def agent_candidate_residual_risk_policy_categories(
    task_text: str,
    *,
    require_explicit_marker: bool = True,
) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    explicit_policy_markers = (
        r"\bresidual risks?\b",
        r"\bremaining risks?\b",
        r"残余风险",
        r"剩余风险",
    )
    if require_explicit_marker and not any(re.search(pattern, text, re.IGNORECASE) for pattern in explicit_policy_markers):
        return []
    no_acceptance_pattern = (
        r"\b(?:no|none|zero)\b.{0,60}\b(?:accepted|acceptable|allowed)?\s*residual risks?\b"
        r"|\b(?:do not|don't|cannot|can't|must not|never)\b.{0,60}\baccept\b.{0,60}\bresidual risks?\b"
        r"|(?:不接受|不能接受|不可接受|不允许).{0,24}残余风险"
        r"|残余风险.{0,24}(?:不接受|不能接受|不可接受|不允许)"
    )
    categories: list[tuple[str, str]] = [
        ("residual-risk", r"\bresidual risks?\b|\bremaining risks?\b|残余风险|剩余风险"),
    ]
    if re.search(no_acceptance_pattern, text, re.IGNORECASE):
        categories.append(
            (
                "no-accepted-residual-risk",
                (
                    r"\b(?:no|none|zero)\b.{0,80}\b(?:accepted|acceptable|allowed)?\s*residual risks?\b"
                    r"|\b(?:do not|don't|cannot|can't|must not|never)\b.{0,80}\baccept\b.{0,80}\bresidual risks?\b"
                    r"|(?:不接受|不能接受|不可接受|不允许).{0,30}残余风险"
                    r"|残余风险.{0,30}(?:不接受|不能接受|不可接受|不允许)"
                ),
            )
        )
        return categories
    category_patterns = (
        (
            "acceptance",
            r"\b(?:accept|accepted|acceptable|allow|allowed|carry)\b|接受|可接受|允许|带着走",
            (
                r"(?:\bresidual risks?\b|残余风险|剩余风险).{0,160}"
                r"(?:\b(?:accept|accepted|acceptable|allow|allowed|carry)\b|接受|可接受|允许|带着走)"
                r"|(?:\b(?:accept|accepted|acceptable|allow|allowed|carry)\b|接受|可接受|允许|带着走)"
                r".{0,160}(?:\bresidual risks?\b|残余风险|剩余风险)"
            ),
        ),
        (
            "owner/follow-up",
            (
                r"\b(?:owner|owned|assignee|follow[- ]?up|followup|ticket|tracked|tracking|"
                r"revisit|monitor|mitigation)\b|负责人|负责|接手|接管|后续|跟进|工单|跟踪|追踪|监控|缓解"
            ),
            (
                r"(?:\bresidual risks?\b|残余风险|剩余风险).{0,180}"
                r"(?:\b(?:owner|owned|assignee|follow[- ]?up|followup|ticket|tracked|tracking|"
                r"revisit|monitor|mitigation)\b|负责人|负责|接手|接管|后续|跟进|工单|跟踪|追踪|监控|缓解)"
                r"|(?:\b(?:owner|owned|assignee|follow[- ]?up|followup|ticket|tracked|tracking|"
                r"revisit|monitor|mitigation)\b|负责人|负责|接手|接管|后续|跟进|工单|跟踪|追踪|监控|缓解)"
                r".{0,180}(?:\bresidual risks?\b|残余风险|剩余风险)"
            ),
        ),
        (
            "fail-closed",
            r"\b(?:fail closed|must block|must fail|block|blocking|reject)\b|失败关闭|必须阻断|必须失败|阻断|拒绝",
            (
                r"(?:\bresidual risks?\b|残余风险|剩余风险).{0,180}"
                r"(?:\b(?:fail closed|must block|must fail|block|blocking|reject)\b|失败关闭|必须阻断|必须失败|阻断|拒绝)"
                r"|(?:\b(?:fail closed|must block|must fail|block|blocking|reject)\b|失败关闭|必须阻断|必须失败|阻断|拒绝)"
                r".{0,180}(?:\bresidual risks?\b|残余风险|剩余风险)"
            ),
        ),
    )
    categories.extend(
        (label, bundle_pattern)
        for label, task_pattern, bundle_pattern in category_patterns
        if re.search(task_pattern, text, re.IGNORECASE)
    )
    return categories


def agent_candidate_success_surface_categories(task_text: str, *, require_explicit_marker: bool = True) -> list[tuple[str, str]]:
    text = str(task_text or "").strip()
    if not text:
        return []
    explicit_success_markers = (
        r"\bsuccess\s+(?:means|requires|is)\b",
        r"\bdone when\b",
        r"\bcomplete when\b",
        r"\bacceptance criteria\b",
        r"\bto pass\b.{0,80}\b(?:must|needs?|should|requires?)\b",
        r"\b(?:must|needs?|should|requires?)\b.{0,80}\b(?:pass|succeed|be complete|be done)\b",
        r"成功(?:标准|意味着|要求|面)",
        r"完成(?:标准|条件|时)",
        r"验收(?:标准|条件)",
    )
    if require_explicit_marker and not any(re.search(pattern, text, re.IGNORECASE) for pattern in explicit_success_markers):
        return []
    categories: list[tuple[str, str]] = [
        (
            "success/done-when",
            r"\b(?:success|done when|acceptance criteria|complete when|completion criteria)\b|成功|完成标准|验收",
        ),
    ]
    category_patterns = (
        (
            "actor/user-facing-outcome",
            r"\b(?:user|customer|admin|operator|buyer|merchant|support)\b|用户|客户|管理员|运营|买家|商家|客服",
        ),
        (
            "notification/message",
            r"\b(?:notification|notify|email|message|receipt|alert)\b|通知|邮件|消息|回执|提醒",
        ),
        (
            "audit/log",
            r"\b(?:audit|auditing|audit[- ]?log|log|logs|ledger|trace|recorded|records?)\b|审计|日志|账本|记录|追踪",
        ),
        (
            "permission/auth",
            r"\b(?:permission|permissions|authorization|auth|access|role)\b|权限|授权|访问|角色",
        ),
        (
            "payment/refund/billing",
            r"\b(?:payment|payments|refund|refunds|billing|invoice|checkout)\b|支付|退款|账单|发票|结账",
        ),
        (
            "data/export/report",
            r"\b(?:data|export|download|csv|report|dashboard)\b|数据|导出|下载|报表|看板",
        ),
        (
            "accessibility/a11y",
            r"\b(?:accessibility|a11y|screen[- ]?reader|keyboard|aria|focus|wcag)\b|无障碍|可访问|读屏|屏幕阅读器|键盘|焦点",
        ),
        (
            "locale/i18n",
            r"\b(?:locale|locali[sz]ation|i18n|translation|language|chinese|english)\b|多语言|国际化|本地化|翻译|语言|中文|英文|英语",
        ),
    )
    categories.extend((label, pattern) for label, pattern in category_patterns if re.search(pattern, text, re.IGNORECASE))
    return categories


from __future__ import annotations

import re

from loopora.alignment_readiness_rules import has_any_marker
from loopora.service_alignment_decision_option_normalization import alignment_has_recommended_decision_options


def alignment_clarifying_question_issues(output: dict) -> list[str]:
    if output.get("needs_user_input") is not True:
        return []
    message = str(output.get("assistant_message", "") or "").strip()
    if not message:
        return []
    normalized = message.lower()
    issues: list[str] = []
    mechanical_terms = (
        "yaml",
        "bundle",
        "spec",
        "role_definition",
        "role definition",
        "role_definition_key",
        "workflow",
        "parallel_group",
        "parallel group",
        "controls",
        "builder",
        "inspector",
        "gatekeeper",
        "guide",
        "配置",
        "方案文件",
        "角色",
        "工作流",
        "并行组",
    )
    config_verbs = (
        "configure",
        "set up",
        "select",
        "choose",
        "use",
        "enable",
        "add",
        "want",
        "配置",
        "选择",
        "要不要",
        "是否需要",
        "启用",
        "添加",
        "扮演",
    )
    task_risk_terms = (
        "risk",
        "afraid",
        "worry",
        "fake",
        "evidence",
        "proof",
        "trust",
        "block",
        "strict",
        "done",
        "residual",
        "progress",
        "drift",
        "风险",
        "怕",
        "担心",
        "假完成",
        "证据",
        "证明",
        "信任",
        "阻断",
        "严格",
        "完成",
        "残余",
        "进展",
        "偏差",
    )
    has_mechanics = has_any_marker(normalized, mechanical_terms)
    has_config = has_any_marker(normalized, config_verbs)
    has_task_risk = has_any_marker(normalized, task_risk_terms)
    if has_mechanics and has_config and not has_task_risk:
        issues.append("mechanical_configuration_question")
    if alignment_questionnaire_overload(message):
        issues.append("questionnaire_overload")
    generic_patterns = (
        "do you want high quality",
        "what are your preferences",
        "what preferences do you have",
        "tell me your preferences",
        "what do you prefer",
        "what quality level do you want",
        "what is your preferred collaboration style",
        "what roles do you want",
        "what role should i play",
        "你要高质量吗",
        "你有什么偏好",
        "你的偏好是什么",
        "你想要什么质量",
        "你希望质量怎么样",
        "你喜欢什么风格",
        "你希望我扮演什么角色",
        "你想要哪些角色",
    )
    if has_any_marker(normalized, generic_patterns):
        issues.append("generic_alignment_question")
    internal_alignment_terms = (
        "readiness_evidence",
        "alignment_stage",
        "alignment_phase",
        "agreement_summary",
        "evidence_buckets",
    )
    if has_any_marker(normalized, internal_alignment_terms) or (
        "evidence buckets" in normalized
        and not has_any_marker(
            normalized,
            (
                "proven",
                "weak",
                "unproven",
                "blocking",
                "residual",
                "已证明",
                "弱证据",
                "未证明",
                "阻断",
                "残余",
            ),
        )
    ):
        issues.append("internal_alignment_term_question")
    if not alignment_has_recommended_decision_options(output):
        issues.append("missing_recommended_decision_options")
    return issues


def alignment_questionnaire_overload(message: str) -> bool:
    question_marks = message.count("?") + message.count("？")
    if question_marks >= 4:
        return True
    question_lines = 0
    question_line_re = re.compile(r"^\s*(?:[-*]|\d+[.)、]|[一二三四五六七八九十]+[、.])\s*")
    question_cues = (
        "?",
        "？",
        "请说明",
        "请描述",
        "请列出",
        "what ",
        "which ",
        "whether ",
        "how ",
        "do you ",
        "would you ",
    )
    for line in message.splitlines():
        normalized_line = line.strip().lower()
        if question_line_re.match(normalized_line) and has_any_marker(normalized_line, question_cues):
            question_lines += 1
    return question_lines >= 3

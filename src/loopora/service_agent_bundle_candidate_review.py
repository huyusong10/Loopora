from __future__ import annotations

from loopora.service_alignment_language import alignment_prefers_chinese
from loopora.service_alignment_transcript import AlignmentTranscriptContext, alignment_notice_appender


class ServiceAgentBundleCandidateReviewMixin:
    def _append_missing_agent_candidate_message(self, session: dict, *, loopora_fit_contradiction: bool) -> dict:
        append_notice_message = alignment_notice_appender(AlignmentTranscriptContext(repository=self.repository, get_session=self.get_alignment_session))
        return append_notice_message(
            session["id"],
            _missing_agent_candidate_notice(session, loopora_fit_contradiction=loopora_fit_contradiction),
        )


def _missing_agent_candidate_notice(session: dict, *, loopora_fit_contradiction: bool) -> str:
    if alignment_prefers_chinese(session):
        if loopora_fit_contradiction:
            return (
                "Loopora 已把这次 /loopora-plan 打开为 Web review：宿主 Agent 没有提交候选方案文件，"
                "而任务摘要已经说明这更像一次性处理、直接回答、不需要后续新证据，"
                "或稳定 benchmark / proof harness 已足够裁决的工作，"
                "所以这里不会伪装成可运行 Loop。若你仍想把范围改成可治理的长期 Loop，"
                "请先补充为什么需要后续证据、handoff 或 GateKeeper 裁决。"
            )
        return (
            "Loopora 已把这次 /loopora-plan 打开为 Web review：宿主 Agent 没有提交候选方案文件，"
            "所以这里不会伪装成可运行 Loop。请继续确认或补充成功标准、伪完成风险、证据预期、"
            "Loopora fit、执行策略、判断取舍、残余风险和本地治理责任，然后再生成可审查的 Loop 预览。"
        )
    if loopora_fit_contradiction:
        return (
            "Loopora opened this /loopora-plan result as Web review because the host Agent did not submit "
            "a candidate plan file, and the task summary says this is closer to a one-off fix, direct answer, "
            "benchmark/test-harness-only path, or work where later rounds add no new evidence. This is not a runnable Loop yet. If you still "
            "want to reshape it into a governed Loop, first explain what later evidence, handoffs, or "
            "GateKeeper judgment would add."
        )
    return (
        "Loopora opened this /loopora-plan result as Web review because the host Agent did not submit "
        "a candidate plan file, so this is not a runnable Loop yet. Continue by confirming or filling "
        "in the success criteria, fake-done risks, evidence expectations, Loopora fit, execution strategy, "
        "judgment tradeoffs, residual-risk policy, and local governance responsibilities before "
        "generating a reviewable Loop preview."
    )

from __future__ import annotations

from pathlib import Path

from alignment_test_support import _wait_for_status


TASK = (
    "我要做退款后台修复。成功必须证明普通客服只能看到自己有权限的订单，"
    "退款失败会回滚，audit log 能追踪操作者和原因。"
)
ADJUSTMENT = "确认，但要调整：GateKeeper 不能接受截图或口头总结，必须看到命令输出、审计日志或测试 artifact 才能通过。"
ADJUSTMENT_BODY = "GateKeeper 不能接受截图或口头总结，必须看到命令输出、审计日志或测试 artifact 才能通过"


def test_alignment_mixed_confirmation_plus_adjustment_updates_agreement_without_polluting_anchor(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    created = service.create_alignment_session(workdir=sample_workdir, message=TASK)
    first_agreement = _wait_for_status(service, created["id"], "waiting_user")

    assert first_agreement["alignment_stage"] == "agreement_ready"
    service.append_alignment_message(created["id"], ADJUSTMENT)
    adjusted = _wait_for_status(service, created["id"], "waiting_user")

    assert adjusted["alignment_stage"] == "agreement_ready"
    assert not Path(adjusted["bundle_path"]).exists()
    assert ADJUSTMENT not in adjusted["working_agreement"]["summary"]
    assert "确认，但要调整" not in adjusted["transcript"][-1]["content"]
    assert ADJUSTMENT_BODY in adjusted["working_agreement"]["summary"]
    assert ADJUSTMENT_BODY in adjusted["transcript"][-1]["content"]

    service.append_alignment_message(created["id"], "确认，采用这份调整后的工作协议。")
    ready = _wait_for_status(service, created["id"], "ready")
    bundle_text = Path(ready["bundle_path"]).read_text(encoding="utf-8")

    assert ready["validation"]["ok"] is True
    assert ADJUSTMENT not in bundle_text
    assert "确认，但要调整" not in bundle_text
    assert ADJUSTMENT_BODY in bundle_text

from __future__ import annotations

from compacted_contract_support import assert_contains_all
from loopora.alignment_guidance import load_alignment_guidance_assets


def test_alignment_examples_require_dispute_chargeback_lifecycle_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "Dispute chargeback lifecycle example",
            "chargeback lifecycle",
            "representment evidence submission deadline",
            "不能把“dispute webhook 改 UI 状态”“Stripe dashboard 看 won/lost”“保存 provider dispute id”或“happy-path close”当成 chargeback lifecycle 完成",
            "payment/dispute-chargeback-lifecycle",
            "Dispute Contract Inspector",
            "Dispute Evidence Inspector",
            "provider fixtures + evidence deadline + ledger/refund overlap 证据优先",
        ),
    )

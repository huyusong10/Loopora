from __future__ import annotations

from compacted_contract_support import assert_contains_all
from loopora.alignment_guidance import load_alignment_guidance_assets


def test_alignment_examples_require_kyc_aml_sanctions_screening_evidence() -> None:
    assets = load_alignment_guidance_assets()

    assert_contains_all(
        assets.examples,
        (
            "KYC AML sanctions screening example",
            "KYC/KYB and AML sanctions screening",
            "sanctions/PEP/adverse media/watchlist screening",
            "不能把“provider sandbox 返回 approved”“UI 显示 verified”“只存 provider status”或“happy-path webhook 通过”当成 KYC/KYB and AML sanctions screening 完成",
            "compliance/kyc-aml-sanctions-screening",
            "Compliance Contract Inspector",
            "KYC Evidence Inspector",
            "sanctions/PEP + document negatives + payout hold ledger 证据优先",
        ),
    )

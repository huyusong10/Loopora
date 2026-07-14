from __future__ import annotations

from loopora.bundle_io import bundle_to_yaml, load_bundle_text
from loopora.executor_alignment_bundle_base_fixture import alignment_bundle_yaml
from loopora.executor_alignment_bundle_governance_fixture import alignment_bundle_governance_sentence as _local_governance_bundle_sentence
from loopora.executor_alignment_bundle_localized_variants import alignment_chinese_bundle_yaml
from loopora.executor_alignment_bundle_refund_assets import apply_alignment_refund_bundle_fixture
from loopora.executor_alignment_bundle_task_roles import _apply_refund_repair_roles


def alignment_refund_repair_bundle_yaml(workdir: str) -> str:
    bundle = load_bundle_text(alignment_bundle_yaml(workdir))
    _apply_refund_repair_bundle(bundle, workdir=workdir, locale="en")
    return bundle_to_yaml(bundle)


def alignment_chinese_refund_repair_bundle_yaml(workdir: str) -> str:
    bundle = load_bundle_text(alignment_chinese_bundle_yaml(workdir))
    _apply_refund_repair_bundle(bundle, workdir=workdir, locale="zh")
    return bundle_to_yaml(bundle)


def _apply_refund_repair_bundle(bundle: dict, *, workdir: str, locale: str) -> None:
    local_governance_sentence = _local_governance_bundle_sentence(workdir, locale=locale)
    apply_alignment_refund_bundle_fixture(
        bundle,
        locale=locale,
        local_governance_sentence=local_governance_sentence,
    )
    _apply_refund_repair_roles(bundle, prefers_chinese=locale == "zh")

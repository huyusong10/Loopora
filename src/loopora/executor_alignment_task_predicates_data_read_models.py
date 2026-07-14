from __future__ import annotations

import re

from loopora.executor_alignment_task_predicates_data_cross_domain import is_data_residency_task
from loopora.executor_alignment_task_predicates_data_lifecycle import is_data_lifecycle_deletion_retention_task


def is_cache_invalidation_consistency_task(task: str) -> bool:
    text = str(task or "")
    if is_data_lifecycle_deletion_retention_task(text) or is_data_residency_task(text):
        return False
    if not re.search(r"cache|CDN|Redis|read[- ]?model|TTL|缓存|回源|失效", text, re.IGNORECASE):
        return False
    if not re.search(r"price|pricing|old\s+price|商品|价格|旧价", text, re.IGNORECASE):
        return False
    if not re.search(
        r"invalidation|invalidate|purge|refresh|refetch|TTL|stale|cache[- ]?key|缓存失效|刷新|回源|旧价",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"price|pricing|PDP|cart|checkout|API|商品|价格|购物车|下单|旧价",
        r"cache|CDN|Redis|read[- ]?model|cache[- ]?key|缓存|缓存\s*key",
        r"invalidation|invalidate|purge|refresh|refetch|TTL|stale|回源|失效|刷新",
        r"old\s+price|checkout|payment|cannot\s+checkout|旧价|下单|支付",
        r"region|currency|locale|key\s+isolation|地区|区域|货币|币种|串",
        r"rollback|roll\s+back|cleanup|恢复旧价|回滚|清理",
        r"audit|invalidation\s+event|actor|monitoring|alert|审计|监控|告警",
        r"database[- ]?update|manual\s+refresh|single[- ]?cache[- ]?layer|docs[- ]?only|数据库|手动刷新|单层|文档",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5

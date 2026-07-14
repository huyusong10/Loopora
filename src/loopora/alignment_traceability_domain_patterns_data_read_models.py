from __future__ import annotations

"""Cache and search read-model consistency domain-risk patterns."""

CACHE_INVALIDATION_CONSISTENCY_PATTERN = (
    r"(?:(?:\b(?:cache|caches|cached|caching|cdn|edge[- ]?cache|redis|read[- ]?model|read[- ]?models|"
    r"materiali[sz]ed[- ]?view)\b|缓存|CDN|边缘缓存|Redis|读模型|物化视图).{0,220}"
    r"(?:\b(?:invalidate|invalidated|invalidation|cache[- ]?flush|flush|purge|ttl|freshness|fresh|stale|"
    r"stale[- ]?(?:cache|read|reads|data)|read[- ]?your[- ]?writes|read[- ]?after[- ]?write|"
    r"origin[- ]?fetch|refetch|revalidate|cache[- ]?key|cache[- ]?keys|key[- ]?isolation|"
    r"eventual[- ]?consistency|consistency|write[- ]?through)\b|"
    r"失效|刷新|清理缓存|缓存清理|过期|回源|重新验证|陈旧|旧价|旧状态|读写一致|写后读|最终一致|"
    r"缓存\s*key|缓存键|key\s*隔离|缓存隔离|一致性)"
    r"|(?:\b(?:invalidate|invalidated|invalidation|cache[- ]?flush|flush|purge|ttl|freshness|fresh|stale|"
    r"stale[- ]?(?:cache|read|reads|data)|read[- ]?your[- ]?writes|read[- ]?after[- ]?write|"
    r"origin[- ]?fetch|refetch|revalidate|cache[- ]?key|cache[- ]?keys|key[- ]?isolation|"
    r"eventual[- ]?consistency|consistency|write[- ]?through)\b|"
    r"失效|刷新|清理缓存|缓存清理|过期|回源|重新验证|陈旧|旧价|旧状态|读写一致|写后读|最终一致|"
    r"缓存\s*key|缓存键|key\s*隔离|缓存隔离|一致性).{0,220}"
    r"(?:\b(?:cache|caches|cached|caching|cdn|edge[- ]?cache|redis|read[- ]?model|read[- ]?models|"
    r"materiali[sz]ed[- ]?view)\b|缓存|CDN|边缘缓存|Redis|读模型|物化视图))"
)


SEARCH_INDEX_CONSISTENCY_PATTERN = (
    r"(?:(?:\b(?:search[- ]?index(?:es)?|full[- ]?text[- ]?search|knowledge[- ]?base[- ]?search|"
    r"document[- ]?index(?:es)?|indexer|indexing|reindex(?:ing)?|re-index(?:ing)?|"
    r"search[- ]?results?|vector[- ]?index(?:es)?)\b|"
    r"全文搜索|知识库搜索|搜索索引|文档索引|索引重建|重建索引|增量索引|搜索结果).{0,260}"
    r"(?:\b(?:acl|tenant[- ]?acl|permission[- ]?filter(?:ing)?|access[- ]?filter(?:ing)?|"
    r"authorization[- ]?filter(?:ing)?|incremental[- ]?(?:indexing|sync)|create/update/delete|"
    r"created?/updated?/deleted?|deleted[- ]?document(?:s)?|stale[- ]?index|index[- ]?(?:lag|freshness)|"
    r"reindex[- ]?(?:run|backfill)|backfill|watermark|cursor|retry|pagination|stable[- ]?sort(?:ing)?|"
    r"sort[- ]?order|result[- ]?leak(?:age)?)\b|"
    r"ACL|权限过滤|租户\s*ACL|增量同步|增量更新|新建|更新|删除文档|已删除文档|无权限文档|"
    r"索引延迟|索引滞后|陈旧索引|索引新鲜度|回填|水位|游标|失败重试|分页稳定|排序稳定|结果泄露)"
    r"|(?:\b(?:acl|tenant[- ]?acl|permission[- ]?filter(?:ing)?|access[- ]?filter(?:ing)?|"
    r"authorization[- ]?filter(?:ing)?|incremental[- ]?(?:indexing|sync)|create/update/delete|"
    r"created?/updated?/deleted?|deleted[- ]?document(?:s)?|stale[- ]?index|index[- ]?(?:lag|freshness)|"
    r"reindex[- ]?(?:run|backfill)|backfill|watermark|cursor|retry|pagination|stable[- ]?sort(?:ing)?|"
    r"sort[- ]?order|result[- ]?leak(?:age)?)\b|"
    r"ACL|权限过滤|租户\s*ACL|增量同步|增量更新|新建|更新|删除文档|已删除文档|无权限文档|"
    r"索引延迟|索引滞后|陈旧索引|索引新鲜度|回填|水位|游标|失败重试|分页稳定|排序稳定|结果泄露).{0,260}"
    r"(?:\b(?:search[- ]?index(?:es)?|full[- ]?text[- ]?search|knowledge[- ]?base[- ]?search|"
    r"document[- ]?index(?:es)?|indexer|indexing|reindex(?:ing)?|re-index(?:ing)?|"
    r"search[- ]?results?|vector[- ]?index(?:es)?)\b|"
    r"全文搜索|知识库搜索|搜索索引|文档索引|索引重建|重建索引|增量索引|搜索结果))"
)


__all__ = (
    "CACHE_INVALIDATION_CONSISTENCY_PATTERN",
    "SEARCH_INDEX_CONSISTENCY_PATTERN",
)

from __future__ import annotations

"""Data import, upload, and collaborative consistency domain-risk patterns."""

FILE_UPLOAD_STORAGE_SAFETY_PATTERN = (
    r"(?:(?:\b(?:file[- ]?upload|upload(?:ed|ing)?|attachment[- ]?upload|object[- ]?storage|blob[- ]?storage|"
    r"s3|bucket|signed[- ]?url|presigned[- ]?url|pre[- ]?signed[- ]?url)\b|文件上传|上传文件|附件上传|"
    r"对象存储|存储桶|签名\s*URL|预签名|直链访问).{0,180}"
    r"(?:\b(?:mime|content[- ]?type|file[- ]?type|file[- ]?size|size[- ]?limit|malware|virus|"
    r"antivirus|scan(?:ned|ning)?|quarantine|unsafe[- ]?file|access[- ]?control|"
    r"direct[- ]?object[- ]?access|orphan(?:ed)?[- ]?upload|failed[- ]?upload[- ]?cleanup|"
    r"cleanup|storage[- ]?access)\b|MIME|content-type|文件类型|文件大小|大小限制|病毒|恶意文件|恶意|"
    r"扫描|隔离|访问控制|直链访问|孤儿文件|失败上传清理|清理)"
    r"|(?:\b(?:mime|content[- ]?type|file[- ]?type|file[- ]?size|size[- ]?limit|malware|virus|"
    r"antivirus|scan(?:ned|ning)?|quarantine|unsafe[- ]?file|access[- ]?control|"
    r"direct[- ]?object[- ]?access|orphan(?:ed)?[- ]?upload|failed[- ]?upload[- ]?cleanup|"
    r"cleanup|storage[- ]?access)\b|MIME|content-type|文件类型|文件大小|大小限制|病毒|恶意文件|恶意|"
    r"扫描|隔离|访问控制|直链访问|孤儿文件|失败上传清理|清理).{0,180}"
    r"(?:\b(?:file[- ]?upload|upload(?:ed|ing)?|attachment[- ]?upload|object[- ]?storage|blob[- ]?storage|"
    r"s3|bucket|signed[- ]?url|presigned[- ]?url|pre[- ]?signed[- ]?url)\b|文件上传|上传文件|附件上传|"
    r"对象存储|存储桶|签名\s*URL|预签名|直链访问))"
)


DATA_IMPORT_VALIDATION_IDEMPOTENCY_PATTERN = (
    r"(?:(?:\b(?:csv[- ]?import|data[- ]?import|bulk[- ]?import|customer[- ]?import|record[- ]?import|"
    r"row[- ]?import|import[- ]?job|importer)\b|CSV\s*导入|数据导入|批量导入|客户导入|记录导入|导入任务).{0,200}"
    r"(?:\b(?:field[- ]?mapping|column[- ]?mapping|schema[- ]?validation|type[- ]?validation|required[- ]?columns?|"
    r"malformed[- ]?rows?|bad[- ]?rows?|partial[- ]?failure|row[- ]?level[- ]?errors?|error[- ]?report|"
    r"import[- ]?preview|dry[- ]?run|idempotent[- ]?retry|dedupe|external[- ]?id|duplicate[- ]?rows?)\b|"
    r"字段映射|列映射|schema\s*校验|类型校验|必填列|坏行|错误行|部分失败|行级错误|错误报告|导入预览|"
    r"试跑|幂等重试|重复导入|去重|重复客户)"
    r"|(?:\b(?:field[- ]?mapping|column[- ]?mapping|schema[- ]?validation|type[- ]?validation|required[- ]?columns?|"
    r"malformed[- ]?rows?|bad[- ]?rows?|partial[- ]?failure|row[- ]?level[- ]?errors?|error[- ]?report|"
    r"import[- ]?preview|dry[- ]?run|idempotent[- ]?retry|dedupe|external[- ]?id|duplicate[- ]?rows?)\b|"
    r"字段映射|列映射|schema\s*校验|类型校验|必填列|坏行|错误行|部分失败|行级错误|错误报告|导入预览|"
    r"试跑|幂等重试|重复导入|去重|重复客户).{0,200}"
    r"(?:\b(?:csv[- ]?import|data[- ]?import|bulk[- ]?import|customer[- ]?import|record[- ]?import|"
    r"row[- ]?import|import[- ]?job|importer)\b|CSV\s*导入|数据导入|批量导入|客户导入|记录导入|导入任务))"
)


CONCURRENCY_CONFLICT_RESOLUTION_PATTERN = (
    r"(?:(?:\b(?:concurrent[- ]?edit(?:s|ing)?|collaborative[- ]?(?:document[- ]?)?edit(?:s|ing)?|multi[- ]?user[- ]?edit(?:s|ing)?|"
    r"offline[- ]?edit(?:ing)?|offline[- ]?sync|simultaneous[- ]?edit(?:ing)?|same[- ]?(?:document|record|note))\b|"
    r"\bsame[- ]?paragraph\b|协作(?:文档|编辑)|协同编辑|多人编辑|同时编辑|离线编辑|离线同步|同一(?:文档|记录|笔记|段落)).{0,200}"
    r"(?:\b(?:version[- ]?conflict|optimistic[- ]?lock(?:ing)?|base[- ]?version|etag|revision[- ]?check|"
    r"merge[- ]?conflict|conflict[- ]?resolution|safe[- ]?merge|silent[- ]?overwrite|"
    r"lost[- ]?update|replay[- ]?idempotenc(?:y|e)|resolved[- ]?by|merge[- ]?outcome)\b|"
    r"版本冲突|乐观锁|基础版本|版本检查|合并冲突|冲突解决|安全\s*merge|安全合并|静默覆盖|覆盖别人改动|"
    r"丢失更新|重放幂等|冲突提示|保留两边内容|resolved_by|merge outcome)"
    r"|(?:\b(?:version[- ]?conflict|optimistic[- ]?lock(?:ing)?|base[- ]?version|etag|revision[- ]?check|"
    r"merge[- ]?conflict|conflict[- ]?resolution|safe[- ]?merge|silent[- ]?overwrite|"
    r"lost[- ]?update|replay[- ]?idempotenc(?:y|e)|resolved[- ]?by|merge[- ]?outcome)\b|"
    r"版本冲突|乐观锁|基础版本|版本检查|合并冲突|冲突解决|安全\s*merge|安全合并|静默覆盖|覆盖别人改动|"
    r"丢失更新|重放幂等|冲突提示|保留两边内容|resolved_by|merge outcome).{0,200}"
    r"(?:\b(?:concurrent[- ]?edit(?:s|ing)?|collaborative[- ]?(?:document[- ]?)?edit(?:s|ing)?|multi[- ]?user[- ]?edit(?:s|ing)?|"
    r"offline[- ]?edit(?:ing)?|offline[- ]?sync|simultaneous[- ]?edit(?:ing)?|same[- ]?(?:document|record|note))\b|"
    r"\bsame[- ]?paragraph\b|协作(?:文档|编辑)|协同编辑|多人编辑|同时编辑|离线编辑|离线同步|同一(?:文档|记录|笔记|段落)))"
)


__all__ = (
    "CONCURRENCY_CONFLICT_RESOLUTION_PATTERN",
    "DATA_IMPORT_VALIDATION_IDEMPOTENCY_PATTERN",
    "FILE_UPLOAD_STORAGE_SAFETY_PATTERN",
)

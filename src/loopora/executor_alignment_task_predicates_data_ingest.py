from __future__ import annotations

import re

from loopora.executor_alignment_task_predicates_data_cross_domain import (
    is_authorization_policy_task,
    is_payment_webhook_ledger_task,
)


def is_data_import_validation_task(task: str) -> bool:
    text = str(task or "")
    if is_authorization_policy_task(text) or is_payment_webhook_ledger_task(text):
        return False
    if re.search(r"\bexport\b|download|report(?:ing)?|BI\s+report|导出|下载|报表", text, re.IGNORECASE) and not re.search(
        r"\bimport\b|upload|导入|上传",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"\b(?:import|bulk[- ]?import|data[- ]?import|customer[- ]?import|row[- ]?import|import[- ]?job|import[- ]?pipeline|CSV\s+(?:bulk\s+)?import|import\s+CSV|CSV\s+upload|upload(?:ed|ing)?\s+CSV)\b|批量导入|数据导入|客户导入|导入任务|导入流程|上传\s*CSV",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"mapping|schema|required|type\s+validation|row[- ]?level|partial[- ]?failure|bad[- ]?rows?|dry[- ]?run|preview|idempot(?:ent|ency)|dedupe|duplicate|external[-_ ]?id|PII|redact|audit|permission|字段映射|必填|类型|坏行|错误报告|部分失败|预览|幂等|去重|审计|权限|隐私",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"\b(?:import|bulk[- ]?import|data[- ]?import|customer[- ]?import|row[- ]?import|import[- ]?job|import[- ]?pipeline|CSV\s+(?:bulk\s+)?import|import\s+CSV|CSV\s+upload|upload(?:ed|ing)?\s+CSV)\b|批量导入|数据导入|客户导入|导入任务|导入流程|上传\s*CSV",
        r"field[- ]?mapping|mapping|column\s+mapping|字段映射|列映射",
        r"schema|required|type\s+validation|validation|必填|类型|校验|验证",
        r"dry[- ]?run|preview|import[- ]?preview|预览|试运行",
        r"mixed\s+good/bad|bad[- ]?rows?|invalid\s+rows?|row[- ]?level|error\s+report|坏行|错误行|行级|错误报告",
        r"partial[- ]?failure|isolation|all[- ]?or[- ]?nothing|部分失败|隔离|全有全无",
        r"idempot(?:ent|ency)|retry|idempotency\s+key|幂等|重试",
        r"dedupe|duplicate|external[-_ ]?id|reconciliation|去重|重复|外部\s*id|对账",
        r"PII|privacy|redact|permission|auth|tenant|隐私|脱敏|权限|授权|租户",
        r"audit|batch\s+(?:id|fields?|actor|source|counts?|reason|status)|monitoring|cleanup|审计|批次|监控|清理",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5


def is_file_upload_storage_safety_task(task: str) -> bool:
    text = str(task or "")
    if is_data_import_validation_task(text) or re.search(
        r"\bCSV\b|spreadsheet|row[- ]?level|field[- ]?mapping|external[-_ ]?id|批量导入|数据导入|字段映射",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"file\s+upload|upload(?:ed|ing)?\s+(?:file|PDF|image|object)|object\s+storage|stored\s+object|S3|bucket|signed\s+URL|presigned|文件上传|对象存储|上传文件|存储对象|签名\s*URL",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"MIME|content[- ]?type|sniff|size\s+limit|virus|malware|scan|quarantine|signed\s+URL|presigned|private\s+(?:bucket|object)|ACL|tenant|cleanup|orphan|audit|monitoring|MIME|内容类型|嗅探|大小限制|病毒|恶意|扫描|隔离|签名|私有|租户|清理|孤儿|审计|监控",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"file\s+upload|upload(?:ed|ing)?\s+(?:file|PDF|image|object)|object\s+storage|stored\s+object|S3|bucket|文件上传|对象存储|上传文件|存储对象",
        r"MIME|content[- ]?type|sniff|extension|spoof|内容类型|嗅探|扩展名|伪造",
        r"size\s+limit|oversize|large\s+file|大小限制|超大|大文件",
        r"virus|malware|scan|scanner|恶意|病毒|扫描",
        r"quarantine|before\s+serv(?:e|ing)|隔离|访问前|提供前",
        r"signed\s+URL|presigned|URL\s+permission|expiry|expires?|签名\s*URL|过期|权限",
        r"private\s+(?:bucket|object)|object\s+ACL|bucket\s+ACL|public\s+bucket|public[- ]?object|ACL|私有|公开桶|公开对象",
        r"tenant|cross[- ]?tenant|object[- ]?key|key\s+isolation|租户|跨租户|对象\s*key|隔离",
        r"failed\s+upload|cleanup|orphan|失败上传|清理|孤儿",
        r"audit|actor|object\s+id|content\s+hash|scan\s+verdict|reason|monitoring|alert|审计|哈希|扫描结果|原因|监控|告警",
        r"returned\s+URL|happy[- ]?path|browser\s+content[- ]?type|scan\s+follow[- ]?up|返回\s*URL|浏览器|后续",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 5

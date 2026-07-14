from __future__ import annotations

"""Backup, replication, and audit-integrity domain-risk patterns."""

BACKUP_RESTORE_RECOVERY_PATTERN = (
    r"(?:(?:\b(?:backup(?:s)?|backup[- ]?snapshot(?:s)?|database[- ]?snapshot(?:s)?|"
    r"db[- ]?snapshot(?:s)?|cross[- ]?region[- ]?snapshot(?:s)?|snapshot[- ]?(?:file|id)|"
    r"restore|restored|restoring|disaster[- ]?recovery|"
    r"point[- ]?in[- ]?time[- ]?recovery|pitr|rpo|rto|restore[- ]?drill|backup[- ]?job)\b|"
    r"备份|备份快照|数据库快照|跨区域快照|快照文件|快照\s*id|灾难恢复|容灾|"
    r"时间点恢复|恢复演练|备份任务|备份作业).{0,300}"
    r"(?:\b(?:restore[- ]?drill|point[- ]?in[- ]?time[- ]?recovery|pitr|rpo|rto|cross[- ]?region|"
    r"encryption[- ]?key|key[- ]?access|retention[- ]?policy|legal[- ]?hold|schema[- ]?migration|"
    r"isolated[- ]?environment|tenant[- ]?restore|full[- ]?(?:database|db)[- ]?restore|checksum|"
    r"row[- ]?count|application[- ]?smoke[- ]?test|backup[- ]?id|snapshot[- ]?id|restore[- ]?run|"
    r"key[- ]?id|failure[- ]?reason|replication[- ]?lag|expired[- ]?backup|"
    r"restore[- ]?permission|audit|monitor(?:ing)?|alert(?:ing|s)?)\b|"
    r"恢复演练|时间点恢复|跨区域|加密密钥|密钥访问|保留策略|法律保留|schema\s*迁移|"
    r"隔离环境|租户恢复|全量库恢复|校验和|行数|应用冒烟|备份\s*id|快照\s*id|"
    r"恢复任务|密钥\s*id|失败原因|复制延迟|过期备份|恢复权限|审计|监控|告警)"
    r"|(?:\b(?:restore[- ]?drill|point[- ]?in[- ]?time[- ]?recovery|pitr|rpo|rto|cross[- ]?region|"
    r"encryption[- ]?key|key[- ]?access|retention[- ]?policy|legal[- ]?hold|schema[- ]?migration|"
    r"isolated[- ]?environment|tenant[- ]?restore|full[- ]?(?:database|db)[- ]?restore|checksum|"
    r"row[- ]?count|application[- ]?smoke[- ]?test|backup[- ]?id|snapshot[- ]?id|restore[- ]?run|"
    r"key[- ]?id|failure[- ]?reason|replication[- ]?lag|expired[- ]?backup|"
    r"restore[- ]?permission|audit|monitor(?:ing)?|alert(?:ing|s)?)\b|"
    r"恢复演练|时间点恢复|跨区域|加密密钥|密钥访问|保留策略|法律保留|schema\s*迁移|"
    r"隔离环境|租户恢复|全量库恢复|校验和|行数|应用冒烟|备份\s*id|快照\s*id|"
    r"恢复任务|密钥\s*id|失败原因|复制延迟|过期备份|恢复权限|审计|监控|告警).{0,300}"
    r"(?:\b(?:backup(?:s)?|backup[- ]?snapshot(?:s)?|database[- ]?snapshot(?:s)?|"
    r"db[- ]?snapshot(?:s)?|cross[- ]?region[- ]?snapshot(?:s)?|snapshot[- ]?(?:file|id)|"
    r"restore|restored|restoring|disaster[- ]?recovery|"
    r"point[- ]?in[- ]?time[- ]?recovery|pitr|rpo|rto|restore[- ]?drill|backup[- ]?job)\b|"
    r"备份|备份快照|数据库快照|跨区域快照|快照文件|快照\s*id|灾难恢复|容灾|"
    r"时间点恢复|恢复演练|备份任务|备份作业))"
)


CDC_REPLICATION_CONSISTENCY_PATTERN = (
    r"(?:(?:\b(?:cdc|change[- ]?data[- ]?capture|logical[- ]?replication|streaming[- ]?replication|"
    r"replication|replicat(?:e|ed|ing)|replica(?:tion)?[- ]?connector|postgres(?:ql)?|source[- ]?table|"
    r"sync[- ]?job(?:s)?|"
    r"warehouse[- ]?sync|read[- ]?model(?:s)?|sync[- ]?connector)\b|CDC|变更数据捕获|逻辑复制|"
    r"流式复制|复制同步|同步任务|同步作业|同步连接器|数仓同步|读模型|源表|Postgres).{0,360}"
    r"(?:\b(?:snapshot[- ]?backfill|backfill|lsn|watermark|checkpoint|out[- ]?of[- ]?order|"
    r"duplicate[- ]?event(?:s)?|event[- ]?count|schema[- ]?evolution|column[- ]?rename|"
    r"delete[- ]?tombstone|tombstone|replay[- ]?from[- ]?checkpoint|checkpoint[- ]?replay|"
    r"source[- ]?row[- ]?count|checksum|warehouse[- ]?aggregate|aggregate[- ]?reconciliation|replication[- ]?lag|"
    r"stale[- ]?checkpoint|dlq|dead[- ]?letter|poison[- ]?(?:event|message)|sync[- ]?failure|"
    r"connector[- ]?version|failure[- ]?reason)\b|"
    r"快照回填|回填|水位|检查点|乱序事件|重复事件|事件数|schema\s*演进|列重命名|"
    r"删除墓碑|墓碑|从检查点重放|源表行数|源行数|校验和|聚合对账|复制延迟|陈旧检查点|"
    r"死信|毒丸事件|同步失败|连接器版本|失败原因)"
    r"|(?:\b(?:snapshot[- ]?backfill|backfill|lsn|watermark|checkpoint|out[- ]?of[- ]?order|"
    r"duplicate[- ]?event(?:s)?|event[- ]?count|schema[- ]?evolution|column[- ]?rename|"
    r"delete[- ]?tombstone|tombstone|replay[- ]?from[- ]?checkpoint|checkpoint[- ]?replay|"
    r"source[- ]?row[- ]?count|checksum|warehouse[- ]?aggregate|aggregate[- ]?reconciliation|replication[- ]?lag|"
    r"stale[- ]?checkpoint|dlq|dead[- ]?letter|poison[- ]?(?:event|message)|sync[- ]?failure|"
    r"connector[- ]?version|failure[- ]?reason)\b|"
    r"快照回填|回填|水位|检查点|乱序事件|重复事件|事件数|schema\s*演进|列重命名|"
    r"删除墓碑|墓碑|从检查点重放|源表行数|源行数|校验和|聚合对账|复制延迟|陈旧检查点|"
    r"死信|毒丸事件|同步失败|连接器版本|失败原因).{0,360}"
    r"(?:\b(?:cdc|change[- ]?data[- ]?capture|logical[- ]?replication|streaming[- ]?replication|"
    r"replication|replicat(?:e|ed|ing)|replica(?:tion)?[- ]?connector|postgres(?:ql)?|source[- ]?table|"
    r"sync[- ]?job(?:s)?|"
    r"warehouse[- ]?sync|read[- ]?model(?:s)?|sync[- ]?connector)\b|CDC|变更数据捕获|逻辑复制|"
    r"流式复制|复制同步|同步任务|同步作业|同步连接器|数仓同步|读模型|源表|Postgres))"
)


AUDIT_LOG_INTEGRITY_RETENTION_PATTERN = (
    r"(?:(?:\b(?:audit[- ]?trail|compliance[- ]?audit|security[- ]?audit[- ]?log|audit[- ]?log(?:s)?|"
    r"admin[- ]?audit[- ]?log(?:s)?|activity[- ]?log(?:s)?)\b|"
    r"合规审计|审计追踪|审计轨迹|审计日志|管理员审计|操作日志).{0,320}"
    r"(?:\b(?:append[- ]?only|immutable|tamper[- ]?evident|tamper[- ]?proof|hash[- ]?chain|"
    r"worm[- ]?storage|write[- ]?once[- ]?read[- ]?many|retention[- ]?policy|legal[- ]?hold|"
    r"before/after|before[- ]?after|before[- ]?and[- ]?after|reason[- ]?code|request[- ]?id|"
    r"user[- ]?agent|clock[- ]?skew|monotonic[- ]?timestamp|sequence[- ]?gap|gap[- ]?in[- ]?sequence|"
    r"siem|exporter|stale[- ]?exporter|logging[- ]?failure|log[- ]?integrity)\b|"
    r"追加写|只追加|不可变|不可篡改|防篡改|篡改可见|哈希链|WORM|一次写入多次读取|"
    r"保留策略|法律保留|前后差异|变更前后|原因码|请求\s*id|用户代理|时钟偏移|"
    r"时间戳单调|序列缺口|序号缺口|日志缺口|SIEM|导出器|导出延迟|日志失败|日志完整性)"
    r"|(?:\b(?:append[- ]?only|immutable|tamper[- ]?evident|tamper[- ]?proof|hash[- ]?chain|"
    r"worm[- ]?storage|write[- ]?once[- ]?read[- ]?many|retention[- ]?policy|legal[- ]?hold|"
    r"before/after|before[- ]?after|before[- ]?and[- ]?after|reason[- ]?code|request[- ]?id|"
    r"user[- ]?agent|clock[- ]?skew|monotonic[- ]?timestamp|sequence[- ]?gap|gap[- ]?in[- ]?sequence|"
    r"siem|exporter|stale[- ]?exporter|logging[- ]?failure|log[- ]?integrity)\b|"
    r"追加写|只追加|不可变|不可篡改|防篡改|篡改可见|哈希链|WORM|一次写入多次读取|"
    r"保留策略|法律保留|前后差异|变更前后|原因码|请求\s*id|用户代理|时钟偏移|"
    r"时间戳单调|序列缺口|序号缺口|日志缺口|SIEM|导出器|导出延迟|日志失败|日志完整性).{0,320}"
    r"(?:\b(?:audit[- ]?trail|compliance[- ]?audit|security[- ]?audit[- ]?log|audit[- ]?log(?:s)?|"
    r"admin[- ]?audit[- ]?log(?:s)?|activity[- ]?log(?:s)?)\b|"
    r"合规审计|审计追踪|审计轨迹|审计日志|管理员审计|操作日志))"
)


__all__ = (
    "AUDIT_LOG_INTEGRITY_RETENTION_PATTERN",
    "BACKUP_RESTORE_RECOVERY_PATTERN",
    "CDC_REPLICATION_CONSISTENCY_PATTERN",
)

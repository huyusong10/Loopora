from __future__ import annotations

import re


def is_prompt_asset_ownership_task(task: str) -> bool:
    text = str(task or "")
    if not re.search(
        r"system[-_ ]?prompts?|developer[-_ ]?prompts?|fixed\s+prompts?|prompt\s+assets?|system_prompt_assets|system_prompts|系统提示词|提示词资产|固定提示词",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"hardcod|inline|literal|asset(?:ize|s|ed)?|decoupl|migrat|ownership|locale|language[- ]?specific|branch|\\.zh|\\.en|硬编码|内联|解耦|迁移|资产|归属|语言分支|多语言",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"system[-_ ]?prompts?|developer[-_ ]?prompts?|fixed\s+prompts?|系统提示词|固定提示词",
        r"Agent\s+Native|managed\s+entries?|role[- ]?agent|Claude\s+session|runtime\s+(?:role\s+)?prefix|output\s+contracts?|alignment\s+compiler|role\s+metadata|托管入口|角色",
        r"system_prompt_assets|system_prompts|prompt\s+assets?|asset\s+refs?|load(?:ed|ing)?|render(?:ed|ing)?|提示词资产|资产引用",
        r"hardcod|inline|literal|Python|code|硬编码|内联|代码",
        r"locale|language[- ]?specific|\\.zh|\\.en|named\s+user\s+language|语言|多语言|中文|英文",
        r"test|AST|long[- ]?instruction|static\s+asset\s+refs?|unresolved\s+placeholders?|placeholder|测试|占位符",
        r"Strategy\s+Source|user[- ]?editable\s+presets?|preset\s+boundary|策略源|预设",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 4


def is_key_rotation_task(task: str) -> bool:
    text = str(task or "")
    if not re.search(
        r"\b(?:api[- ]?key|access[- ]?key|service[- ]?account[- ]?secret|client[- ]?secret|credential|kms[- ]?key)\b|API\s*key|访问密钥|服务账号密钥|客户端密钥|KMS\s*密钥",
        text,
        re.IGNORECASE,
    ):
        return False
    if not re.search(
        r"key[- ]?rotation|secret[- ]?rotation|rotat(?:e|ed|ion)|overlap[- ]?window|zero[- ]?downtime|compromised[- ]?key|revok|hash|kms[- ]?encrypt|last[- ]?used|stale[- ]?key|密钥轮换|密钥旋转|轮换|重叠窗口|无中断|撤销|吊销|哈希|KMS\s*加密|最后使用|陈旧密钥",
        text,
        re.IGNORECASE,
    ):
        return False
    markers = (
        r"\b(?:api[- ]?key|access[- ]?key|service[- ]?account[- ]?secret|client[- ]?secret|credential|kms[- ]?key)\b|API\s*key|访问密钥|服务账号密钥|客户端密钥|KMS\s*密钥",
        r"key[- ]?rotation|secret[- ]?rotation|rotat(?:e|ed|ion)|overlap[- ]?window|zero[- ]?downtime|轮换|重叠窗口|无中断",
        r"compromised[- ]?key|revok(?:e|ed|ing|ation)?|revoked[- ]?key|rollback|stale[- ]?key|被盗密钥|泄露密钥|撤销|吊销|失效|回滚|陈旧密钥",
        r"scope|tenant[- ]?binding|permission|auth|租户绑定|权限范围|密钥范围",
        r"hash(?:ed)?|kms[- ]?encrypt(?:ed|ion)|encrypted[- ]?storage|plaintext|secret\s+storage|哈希|哈希存储|KMS\s*加密|加密存储|明文",
        r"expiry|expires?|expiration|last[- ]?used|telemetry|rotation[- ]?schedule|key[- ]?id|过期|有效期|最后使用|使用遥测|轮换计划|密钥\s*id",
        r"audit|monitoring|alert|rotation[- ]?failure|stale[- ]?key|审计|监控|告警|轮换失败|陈旧密钥",
        r"new[- ]?key|env\s+var|happy[- ]?path|docs[- ]?only|UI|新\s*key|环境变量|文档",
    )
    return sum(1 for pattern in markers if re.search(pattern, text, re.IGNORECASE)) >= 4

# Task

收紧发布检查清单：只有构建、迁移、回滚和评审者可读证据都成立时，任务才允许完成。

# Done When

- 发布路径具备可复现的构建与迁移证据。
- 任务关闭前已经证明回滚能力。

# Guardrails

- 样例只展示证据治理，不实现真实发布系统。

# Success Surface

- 评审者可以检查 Loop、每轮执行、持久化证据和最终 GateKeeper 裁决。
- 薄弱或缺失证明保持可见，不会被成功的流程状态掩盖。

# Fake Done

- 只有构建通过不算发布证明；迁移或回滚未证明时不得完成。

# Evidence Preferences

- 优先持久化 Run 产物、结构化检查和被引用的上游证据，不接受角色自报作为完成证明。

# Residual Risk

轻微报告样式问题可以保留，但缺失回滚证明必须阻止关闭。

# Role Notes

## Builder Notes

完成有边界的改动，并留下可评审证明面。

## Inspector Notes

区分直接证明与看似合理的声明，并保持失败检查可见。

## GateKeeper Notes

只有必需检查与上游 evidence refs 支持任务裁决时才允许通过。

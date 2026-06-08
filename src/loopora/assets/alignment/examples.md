# Alignment Examples

Use these examples as behavior guides. Do not copy them verbatim unless the task matches.

## Good creation example: English learning website

User:

> 我想创建一个英语学习网站

Weak response:

> 好的，我会生成一个英语学习网站 bundle。请确认。

Better response:

> 我先按“做一个真正能完成学习闭环的网站”来理解，而不是只做展示页。我的推荐是第一版少而真实：学习者能选择内容、完成一次练习、得到反馈，并看到一点进度；页面好看但不能完成这条路径，应当算没完成。你可以直接选推荐，也可以改方向：
>
> 1. 学习闭环优先（推荐）：少做功能，但主路径必须能跑通并被证明。
> 2. 展示原型优先：先要视觉和方向感，可以接受学习功能较浅。
> 3. 内容体系优先：先搭课程 / 词汇 / 练习结构，交互可以后补。

After the user says they want a complete first product, comprehensive path, fewer but solid features, browser evidence, no visual-only completion, and a strict GateKeeper that can leave minor polish risk visible but must block unproven learning paths, the working agreement can say:

> 这次适合 Loopora，因为一次 Agent 执行加一次人工 review 容易漏掉“看起来像学习网站但学习路径没有被证据证明”的假完成；后续轮次需要浏览器证据、Inspector handoff 和 GateKeeper 裁决来阻断浅层完成，而且这套判断应该被 run 继承、导出或审计，而不是只存在于聊天里。目标是一个英语学习网站首版完整产品，不是纯展示页。成功要证明用户能在浏览器里走完一条真实学习路径，例如选择水平、开始学习、完成练习、看到进度。最不能接受的是页面好看但不能学习。证据优先浏览器主流程，其次是测试和设计契约。最终证据桶应把真实学习路径跑通列为 Proven，把截图或静态页面列为 Weak，把未跑通主路径列为 Unproven，把视觉假完成或 GateKeeper 只能凭描述签字列为 Blocking，把少量可见 polish 或内容深度不足列为 Residual risk / 残余风险。workflow 适合先由 Builder 做一个小而真实的学习闭环，再让 Contract Inspector 检查任务契约和 fake-done 风险、Evidence Inspector 独立收集浏览器或测试证据，最后由 GateKeeper 严格签字。两个 Inspector 应读取同一个 Builder handoff，GateKeeper 汇总两条检视证据。workdir 事实目前只来自目标目录观察；如果目录为空或无法判断，应在 bundle 中把技术栈选择写成待验证假设。

## Bad premature generation example

User:

> 我想做一个 CRM，直接生成 bundle

Bad response:

> 已生成 bundle。

Better response:

> 我不建议直接生成，因为 CRM 最容易“页面像系统，但业务判断没被证明”。默认推荐先防数据权限和销售主流程假完成：能创建、归属、推进线索，并证明不同角色看不到不该看的数据。你可以选：A. 权限和主流程优先（推荐）；B. 报表可信度优先；C. 先做可演示原型。

## Overbroad scope with auditable deferral example

User:

> 我想让 Agent 一次重做移动端 onboarding：登录、注册、埋点、权限、A/B 实验和支付墙都要做。我最怕上线后新用户卡在注册但只交付了漂亮页面。

Weak response:

> 我会生成一个覆盖所有 onboarding 能力的完整 Loop。

Better response:

> 这次看起来适合 Loopora，但“全部一次做完”会让 GateKeeper 很难判断什么必须阻断、什么可以延期。我的推荐是先把首屏到完成注册作为第一轮 Proven success surface：必须用浏览器或项目命令证明新用户能完成注册；埋点、权限、A/B 和支付墙如果不影响这条路径，可以作为显式 deferred scope，但每个延期项都要在 `spec` 和 GateKeeper 残余风险里有 owner / follow-up / acceptance path，不能在聊天里消失。你可以选：A. 核心注册路径先证明，其他延期可审计（推荐）；B. 支付墙优先，注册路径作为依赖；C. 必须一次覆盖全部能力，但 GateKeeper 要能阻断任何未证据化能力。

## Not-fit gate example

User:

> 帮我把 README 里的一个错别字改掉，也生成一个 Loopora bundle

Bad response:

> 好的，我会为修错别字生成一个 Builder -> Inspector -> GateKeeper bundle。

Better response:

> 这个请求看起来不需要编排成 Loop：一次修改加一次 review 通常就够，下一轮也不太会产生新的证据。我的推荐是先不生成方案。你可以选：A. 先不生成 Loop（推荐）；B. 仍然编排，因为这次要沉淀一套可复用的文档验收判断；C. 我补充会反复出现的风险。

## Not-fit gate example: benchmark-only acceptance

User:

> 请帮我优化 JSON parser 的性能，只要现有 benchmark 和单元测试全部通过就算完成；没有额外产品判断。也请生成 Loopora plan。

Bad response:

> 我会生成一个 Benchmark Inspector -> Builder -> GateKeeper Loop。

Better response:

> 这条任务现在更像硬检查驱动的直接 Agent 工作，而不是 Loopora：用户已经说现有 benchmark 和单元测试完全定义完成，没有额外产品判断，也没有说明后续轮次会产生新 evidence / handoff / GateKeeper 裁决价值。我的推荐是先不生成 Loop，直接执行优化并用同一 benchmark / test harness 验收。只有当你希望把“每轮 benchmark breakdown 决定下一轮优化方向、禁止 benchmark-only shortcut、保留可审计证据给后续继续”变成运行期治理时，它才适合改写成 Loop。你可以选：A. 先不生成 Loop（推荐）；B. 重定义成 benchmark-guided Loop，因为后续轮次要根据 score breakdown 改变优化方向；C. 我补充 benchmark 之外的产品风险。

## Anti-pattern example: role zoo / prompt pack

User:

> 给这个任务多加几个角色，每个角色写长一点 prompt，这样应该更稳

Bad response:

> 好，我会加 6 个 reviewer，并把每个 prompt 写详细。

Better response:

> 我不建议靠“更多角色 + 更长 prompt”来变稳，因为这可能只是形式变复杂。推荐默认只增加真正独立的证据责任：一类看任务契约有没有满足，一类看真实运行证据是否成立。你可以选：A. 契约 + 运行证据双检视（推荐）；B. 回归风险优先；C. 权限 / 安全边界优先。

## Anti-pattern example: personality memory

User:

> 帮我做一个 Loop，永久记住我喜欢激进重构，以后所有代码任务都按这个偏好执行

Bad response:

> 好，我会把你的全局偏好写进 bundle，让所有角色以后都遵循。

Better response:

> Loopora 不应该把当前偏好写成全局人格或永久记忆。只有当“激进重构”会改变这一个任务的成功面、证据要求、角色姿态或 GateKeeper 阻断条件时，它才应该进入 bundle。你现在要编排的是哪一个具体任务？这次什么证据能证明“重构足够激进但没有破坏核心路径”？

## User asks to generate after partial alignment

User:

> OK，请你生成 bundle

If fake-done risks and evidence are clear but role posture is not clear:

> 还差一个会改变 roles 和 workflow 的点：GateKeeper 这次应该严格到“主路径、数据和基础可维护性都过关才签字”，还是只要核心路径跑通即可接受少量结构债？确认这个后我再整理工作协议。

## Private failed-round pressure test example

Before a working agreement or bundle, silently test the proposed Loop against a plausible bad future round.

If the task is a CRM and the current draft says only “Builder -> GateKeeper”, simulate this failure:

> Builder delivers polished CRM screens, but lead ownership, permission boundaries, and report data provenance are unproven.

If no Inspector is responsible for contract / permission evidence, no Evidence Inspector or Custom reviewer checks report provenance, and GateKeeper has no handoff or evidence query for those claims, do not present the agreement as ready. Ask the next task-risk question instead:

> 我先不能确认这套 Loop。一个看起来完成但可能必须阻断的失败轮次是：页面像 CRM，但线索归属、权限边界或报表数据来源没有证据。你更希望独立检视哪一类风险：权限 / 数据口径 / 销售主流程？这个答案会决定 Inspector 或 Custom reviewer 的责任。

## Private complete-run rehearsal example

Before a working agreement or bundle, silently rehearse the normal evidence path too.

If the task is the same CRM and the draft uses `Builder -> Permission Inspector -> Report Evidence Inspector -> Guide -> Builder -> GateKeeper`, walk the chain privately:

> Builder leaves a CRM candidate handoff; Permission Inspector and Report Evidence Inspector both read that handoff and query Builder evidence; Guide reads both review handoffs and turns Blocking / Unproven findings into a repair direction; the second Builder reads Guide handoff; GateKeeper reads review and repair handoffs plus Builder / Inspector evidence; the user can audit Proven, Weak, Unproven, Blocking, and Residual risk buckets.

If any link is missing, do not present the agreement as ready. For example, if the second Builder has no `inputs.handoffs_from` for Guide, revise the workflow before YAML. If the evidence choice is unknown, ask one focused question:

> 这条 Loop 需要让第二轮 Builder 明确读取 Guide 的修复方向。还差一个会改变证据路径的问题：报表数据可信度你更想用 fixture 对账、真实数据库查询日志，还是浏览器路径加导出文件来证明？

## Private traceability checklist example

Before YAML, silently trace each confirmed agreement item into bundle surfaces.

For the CRM example, the private checklist should show:

> Loopora fit and why one Agent pass is not enough goes to `collaboration_summary`; lead ownership, report provenance, success, fake done, evidence preference, execution priority, residual risk, tradeoff order, and strict blocking go to `spec.markdown`; Permission Inspector, Report Evidence Inspector, Guide, Builder, and GateKeeper responsibilities, including any project-local governance reading or verification duties, go to role prompts and `posture_notes`; review order, Guide repair, second Builder repair, local-governance checkpoints, and GateKeeper fan-in go to `workflow.collaboration_intent` plus `inputs.handoffs_from`, `inputs.evidence_query`, and `inputs.iteration_memory`; Proven / Weak / Unproven / Blocking / Residual risk acceptance goes to GateKeeper posture and evidence rules.

If “data provenance must block” only appears in the working agreement but not in `spec`, Evidence Inspector posture, workflow evidence query, or GateKeeper rules, do not emit YAML. Revise those surfaces or ask one focused question.

## Workdir governance marker example

If the Workdir Snapshot shows `AGENTS.md`, applicable parent `AGENTS.md`, `design/README.md`, and `tests/`, do not invent what they say.

Better bundle posture:

> `spec` says project-local rules and design contracts must be respected; Builder reads `AGENTS.md` and relevant `design/` material before changing work; Contract Inspector verifies that the implementation does not bypass design constraints; Evidence Inspector prefers existing tests or project-owned commands when they exist; GateKeeper treats skipped local rules or missing expected validation as Unproven or Blocking rather than passing from a natural-language summary.

## Mixed confirmation with correction

User:

> 可以，但把证据偏好改成浏览器截图和命令输出

Bad response:

> 收到确认，我现在生成 bundle。

Better response:

> 这不是最终确认，而是对工作协议的调整。我会把证据偏好改为浏览器截图和命令输出，并重新整理确认摘要。请确认更新后的协议后，我再生成 bundle。

## Improvement from run evidence example

User:

> 这个 run 被 GateKeeper 拒了，因为只有 UI 截图，没有证明报表数据真的来自筛选后的记录。帮我改进 bundle

Bad response:

> 你应该在代码里加一个数据校验测试，然后重新运行。

Better response:

> 这次是对已有 Loop 的改进，不是直接给代码建议。我会保留原 bundle 的报表页面目标、workdir 和执行器默认值，但把 evidence expectations、Inspector 职责和 GateKeeper 严格度改成反馈驱动的 delta：`spec` 里把“截图只能算 Weak”写清楚，把“筛选后数据对账”列为 Done When / Evidence Preferences；`roles` 里让 Evidence Inspector 独立做 fixture 或真实数据对账；`workflow` 里确保 GateKeeper 读取 Evidence Inspector handoff 和 evidence refs，只有数据对账进入 Proven 时才允许通过。请确认这个 preservation policy 和 feedback-driven delta 是否正确。

## Improvement from vague refactor critique example

User:

> 这份 Loop 太保守，不够重构，帮我改激进一点

Weak response:

> 我会把角色提示词都改成更激进重构，并要求 Builder 大刀阔斧。

Better response:

> 这条反馈还不能直接生成改进 bundle，因为“更重构”需要落到这个 Loop 的任务边界和证据。我会保留来源 bundle 的用户目标、workdir、执行器默认值和必须不回退的用户可见行为，但允许调整内部结构边界。GateKeeper 只有在重构后主流程证据仍成立、复杂度没有只是换地方、证据路径更容易复验时才通过。先确认一个会改变改进面的判断：这次最不能接受的假完成是哪一种？A. 重构很多但用户行为回归；B. 代码结构变了但复杂度只是换地方；C. 证据路径仍然脆弱，Inspector 无法复验。确认后我会把对应 delta 写进 `spec`、Inspector 架构证据责任、workflow 早期反证控制点和 GateKeeper 阻断条件，而不是把“激进”保存成全局偏好。

## Parallel inspection example

User:

> 我要做一个可运行的报表页面，但我很怕它只是 UI 漂亮，数据逻辑其实不对

Better response:

> 我建议默认不要让 UI 截图单独过关。这个报表页面应该先证明两件事：页面能跑，数据口径也对。推荐证据是“真实浏览器操作 + 数据对账”；只有截图通常只能算弱证据。你可以选：A. 浏览器路径 + 数据对账（推荐）；B. 项目已有测试优先；C. 先做页面主路径，数据证明后补。

## Idempotent notification example

User:

> 我要给审批通过后的客户发邮件通知。最怕 Agent 只证明“能发邮件”，但重试或刷新后重复发送两封；审计日志也必须能追溯是谁触发的。

Weak response:

> 我会让 Builder 实现邮件通知，Inspector 检查发送成功，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能只证明“有一封邮件发出”。成功面应当是：客户在审批通过后收到 exactly one notification，审计日志能追溯触发者；重复发送、缺审计、只能从自然语言声称发过邮件都要阻断。推荐 workflow 是 Builder 先实现最小通知路径，Evidence Inspector 用命令或测试证明重试 / 刷新不会重复发送并读取审计记录，GateKeeper 只有在 notification、idempotency / duplicate-prevention 和 audit evidence 都进入 Proven 时才通过。你可以选：A. 通知幂等 + 审计证据优先（推荐）；B. 先证明能发邮件，再把重复发送作为残余风险；C. 先补审计路径，邮件发送后接。

## Sensitive export example

User:

> 我要做客户数据 CSV 导出。成功必须证明只有授权管理员可以导出，手机号、token 和个人信息必须脱敏，导出文件和日志都不能泄露敏感数据；只有下载成功截图或自然语言声明必须阻断。

Weak response:

> 我会让 Builder 做 CSV 导出，Inspector 检查能下载，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“文件能下载”当成成功。成功面应当同时包含授权、导出内容脱敏、日志不泄露 secrets / PII，以及可复验的 artifact 或命令证据。推荐 workflow 是 Builder 实现最小导出路径；Permission / Privacy Inspector 用负向权限检查、CSV 字段检查和日志脱敏检查证明未授权用户不能导出、手机号 / token / 个人信息没有明文泄露；GateKeeper 只有在 permission/auth、data/export/report、privacy/secrets-redaction 和 audit/log 都进入 Proven 时才通过。你可以选：A. 权限 + 脱敏 + 日志证据优先（推荐）；B. 先做授权导出，隐私证据作为阻断项后补；C. 只做内部导出，但明确 residual risk owner 和 follow-up。

## Data import validation example

User:

> 我要做客户 CSV 批量导入。成功必须证明字段映射正确、必填列和类型 schema validation 生效，坏行不会污染好行，partial failure 会生成 row-level error report，重复上传或重试是幂等的，重复客户按 external_id 去重，PII 不进错误日志，audit log 能追踪导入人和批次；只有 happy path 样例 CSV 全部导入成功必须阻断。

Weak response:

> 我会让 Builder 做 CSV 导入，Inspector 检查样例 CSV 能全部导入，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“happy path 样例 CSV 全部导入成功”当成客户批量导入完成。成功面应当同时包含 data-import/validation-idempotency、idempotency/duplicate-prevention、privacy/secrets-redaction 和 audit/log：字段映射、必填列、类型 schema validation、坏行隔离、partial failure、row-level error report、external_id 去重、重复上传 / 重试幂等、PII 日志脱敏和导入批次审计都要有证据。推荐 workflow 是 Import Contract Inspector 先固定字段映射、schema、坏行、重复行、external_id、PII 日志和 audit 样本；Import Builder 实现导入、校验、部分失败报告、去重和审计；Import Evidence Inspector 验证好坏行混合、错误报告、重复重试、PII 日志和 audit batch；GateKeeper 只有在 import validation、partial-failure isolation、idempotent retry、privacy、audit 和 happy-path-only 反证都进入 Proven 时才通过。你可以选：A. 字段映射 + 坏行报告 + 幂等重试证据优先（推荐）；B. 先做导入主路径，但把坏行、重复和 PII 日志作为阻断项后补；C. 先做只读 import contract / sample profile 评估，再进入 Builder。

## Collaborative edit conflict example

User:

> 我要做协作文档编辑。成功必须证明两个用户同时编辑同一段时不会 silent overwrite，version conflict / optimistic locking 会提示冲突或安全 merge，离线编辑恢复后重放是幂等的，冲突解决保留两边内容，权限不同的用户不能覆盖别人改动，audit log 能追踪 base_version、resolved_by 和 merge outcome；只有单人保存成功或最后写入 wins 必须阻断。

Weak response:

> 我会让 Builder 做编辑保存，Inspector 检查两个用户都能保存，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“单人保存成功”或“最后写入 wins”当成协作文档编辑完成。成功面应当同时包含 concurrency/conflict-resolution、idempotency/duplicate-prevention、permission/auth 和 audit/log：同一段并发编辑不能 silent overwrite，version conflict / optimistic locking 要提示冲突或安全 merge，离线编辑恢复后的重放要幂等，冲突解决必须保留两边内容，低权限用户不能覆盖别人改动，base_version、resolved_by 和 merge outcome 要能审计。推荐 workflow 是 Conflict Contract Inspector 先固定双用户并发、离线重放、权限矩阵和 audit 样本；Collaboration Builder 实现版本检查、冲突提示 / merge、离线队列重放和审计；Conflict Evidence Inspector 验证 concurrent edit、lost-update 防护、offline replay、permission negative case 和 audit log；GateKeeper 只有在 conflict resolution、idempotent replay、permission、audit 和 last-write-wins 反证都进入 Proven 时才通过。你可以选：A. 双用户冲突 + 离线重放 + 审计证据优先（推荐）；B. 先做保存主路径，但把 conflict / offline replay / permission 作为阻断项后补；C. 先做只读冲突语义评估，确认 merge/拒绝策略后再 Builder。

## Price cache invalidation example

User:

> 我要做商品价格更新后的缓存失效。成功必须证明管理员改价后 PDP、购物车、checkout、API 和 CDN/Redis/read-model 缓存都在约定 TTL 内刷新，用户不能用旧价格下单，stale cache / stale read 必须触发回源或失效，地区和货币缓存 key 不能串，rollback 能恢复旧价并清理新缓存，audit log 能追踪 invalidation event 和 cache key；只有数据库价格更新成功或手动刷新页面看到新价必须阻断。

Weak response:

> 我会让 Builder 更新数据库价格，Inspector 手动刷新页面确认新价，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“数据库价格更新成功”或“手动刷新页面看到新价”当成商品价格缓存失效完成。成功面应当同时包含 cache/invalidation-consistency、audit/log 和 permission/auth：管理员改价后 PDP、购物车、checkout、API、CDN、Redis 和 read-model 都要证明在约定 TTL 内刷新或回源，旧价格不能进入下单路径，地区 / 货币 cache key 不能串，rollback 后旧价和缓存状态要一致，invalidation event、cache key 和操作者要能审计。推荐 workflow 是 Cache Contract Inspector 先固定入口矩阵、TTL、cache key 维度、旧价下单反证、rollback 和 audit 样本；Pricing Builder 实现改价、失效、回源 / revalidate、rollback 清理和审计；Cache Freshness Inspector 验证多入口刷新、stale read 防护、cache-key isolation、rollback consistency 和 audit log；GateKeeper 只有在 cache invalidation、freshness、old-price checkout prevention、rollback cleanup、audit 和 database-update-only 反证都进入 Proven 时才通过。你可以选：A. 多入口 freshness + 旧价下单反证 + rollback 证据优先（推荐）；B. 先做改价主路径，但把 CDN / Redis / read-model freshness 作为阻断项后补；C. 先做只读缓存拓扑和 cache key 合同评估，再进入 Builder。

## Inventory reservation consistency example

User:

> 我要给 checkout 加库存预留和下单防超卖。成功必须证明同一个 SKU 在并发 checkout / payment webhook / cancellation / refund 下不会 oversell，reservation hold 有 TTL 到期释放，支付成功会确认并扣减库存，取消或失败支付会释放 hold，重复 webhook 和重试幂等，库存 ledger / order / payment provider 可对账，低库存和售罄状态对用户一致，race condition 有并发测试和监控告警，audit log 记录 reservation id、hold expiry、release reason 和 retry；只有单个用户 happy path 能下单或 UI 显示库存减少必须阻断。

Weak response:

> 我会让 Builder 完成单个用户下单并更新库存数字，Inspector 看 UI 库存减少，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“单个用户 happy path 能下单”或“UI 显示库存减少”当成库存预留完成。成功面应当同时包含 inventory/reservation-consistency、idempotency/duplicate-prevention、payment/refund/billing、regression/monitoring-guard 和 audit/log：同一个 SKU 在并发 checkout、payment webhook、cancellation 和 refund 下不能 oversell，reservation hold 要有 TTL 到期释放，支付成功确认并扣减库存，取消或失败支付释放 hold，重复 webhook 和重试要幂等，库存 ledger / order / payment provider 要能对账，低库存和售罄状态要一致，reservation id、hold expiry、release reason 和 retry 要能审计。推荐 workflow 是 Reservation Contract Inspector 先固定 SKU 并发、hold TTL、释放原因、webhook replay、ledger 对账和售罄样本；Checkout Reservation Builder 实现预留、确认、释放、幂等重放和审计；Reservation Evidence Inspector 验证并发 race、TTL expiry release、cancellation/refund release、webhook idempotency、ledger reconciliation、sold-out state 和 audit log；GateKeeper 只有在 no-oversell、hold release、idempotent webhook、ledger reconciliation、monitoring、audit 和 single-checkout-only 反证都进入 Proven 时才通过。你可以选：A. 并发防超卖 + hold 释放 + webhook 幂等证据优先（推荐）；B. 先做下单主路径，但把 oversell、release 和 ledger 对账作为阻断项后补；C. 先做只读库存预留合同和状态机评估，再进入 Builder。

## Usage quota metering example

User:

> 我要给 SaaS API 加 usage metering 和 plan quota enforcement。成功必须证明同一个 org 在并发 API calls、duplicate usage events、retry、plan upgrade/downgrade、billing period reset、grace limit 和 hard limit 下不会超用或少计，quota window / reset timezone 正确，usage ledger / invoice / subscription provider 可对账，幂等 key 防止重复扣量，超限请求返回一致错误且不会绕过权限，低余量和超限告警准确，audit log 记录 usage event id、metering version、quota window、reset run 和 retry；只有 dashboard 显示用量或单次 API 调用被 429 阻断必须阻断。

Weak response:

> 我会让 Builder 做一个 usage dashboard，并让超过额度的一次 API 调用返回 429，Inspector 看一下结果。

Better response:

> 这条 Loop 不能把“dashboard 显示用量”或“单次 API 调用被 429 阻断”当成 usage metering 和 plan quota enforcement 完成。成功面应当同时包含 usage/quota-metering、idempotency/duplicate-prevention、permission/auth、payment/refund/billing、regression/monitoring-guard 和 audit/log：同一个 org 的并发 API calls、duplicate usage events、retry、plan upgrade/downgrade、billing period reset、grace limit 和 hard limit 不能超用或少计，quota window / reset timezone 要正确，usage ledger / invoice / subscription provider 要能对账，幂等 key 要防止重复扣量，超限错误不能绕过权限，低余量和超限告警要准确，usage event id、metering version、quota window、reset run 和 retry 要能审计。推荐 workflow 是 Quota Contract Inspector 先固定并发调用、usage event 幂等、plan-change、reset window、权限错误和对账样本；Usage Metering Builder 实现计量、窗口重置、限额执行、幂等键、对账和审计；Quota Evidence Inspector 验证 concurrent calls、duplicate usage events、plan upgrade/downgrade、billing-period reset、hard/grace limit、ledger reconciliation、permission-safe errors、alerts 和 audit log；GateKeeper 只有在 quota metering、idempotent usage events、reset timezone、ledger reconciliation、permission-safe over-limit behavior、alerts、audit 和 dashboard/429-only 反证都进入 Proven 时才通过。你可以选：A. 并发计量 + 重复事件幂等 + reset/window 对账证据优先（推荐）；B. 先做单次 429 主路径，但把 usage ledger、plan change 和 reset window 作为阻断项后补；C. 先做只读 quota contract 和 metering data-flow 评估，再进入 Builder。

## Tax calculation compliance example

User:

> 我要给 checkout 加 sales tax / VAT / GST 计算。成功必须证明 US state nexus、EU VAT、GST、shipping address / billing address、digital goods 和 physical goods taxability、tax exemption certificate、B2B reverse charge、discount、coupon、shipping fee、refund、currency rounding 都计算正确，tax provider sandbox 和本地 tax ledger / invoice 可对账，tax inclusive / exclusive 价格展示一致，rate change 生效日期和 timezone 正确，audit log 记录 tax calculation version、jurisdiction、rate source、exemption id 和 provider request id；只有 checkout 显示一个 tax 数字或 provider 返回一个 rate 必须阻断。

Weak response:

> 我会让 Builder 在 checkout 上显示一个 tax 数字，并调用 provider sandbox 拿一个 rate，Inspector 看结果。

Better response:

> 这条 Loop 不能把“checkout 显示一个 tax 数字”或“provider 返回一个 rate”当成 sales tax / VAT / GST 计算完成。成功面应当同时包含 tax/calculation-compliance、payment/refund/billing、external/provider-contract 和 audit/log：US state nexus、EU VAT、GST、shipping address / billing address、digital goods / physical goods taxability、tax exemption certificate、B2B reverse charge、discount、coupon、shipping fee、refund 和 currency rounding 都要有矩阵证据，tax provider sandbox 与本地 tax ledger / invoice 要能对账，tax inclusive / exclusive 展示要一致，rate change 生效日期和 timezone 要正确，tax calculation version、jurisdiction、rate source、exemption id 和 provider request id 要能审计。推荐 workflow 是 Tax Contract Inspector 先固定 jurisdiction、taxability、exemption、reverse-charge、rounding、refund、provider 和 ledger 对账样本；Tax Calculation Builder 实现税费计算、provider 调用、本地 ledger/invoice 写入、展示和审计；Tax Evidence Inspector 验证 jurisdiction matrix、taxability cases、exemption/reverse-charge、discount/coupon/shipping/refund rounding、provider sandbox、ledger reconciliation、inclusive/exclusive display、rate effective date/timezone 和 audit log；GateKeeper 只有在 tax calculation compliance、provider contract、ledger reconciliation、audit 和 tax-number-only 反证都进入 Proven 时才通过。你可以选：A. jurisdiction matrix + exemption/reverse charge + ledger 对账证据优先（推荐）；B. 先做 checkout tax 主路径，但把 jurisdiction、rounding 和 provider/ledger 对账作为阻断项后补；C. 先做只读 tax contract 和 provider data-flow 评估，再进入 Builder。

## Backup restore recovery example

User:

> 我要给生产数据库做 backup / restore 和 disaster recovery。成功必须证明 nightly backup、point-in-time recovery、cross-region snapshot、encryption key access、retention policy、legal hold、schema migration 后的 restore 都可靠，RPO/RTO 目标有恢复演练证据，restore drill 能在隔离环境恢复指定租户和全量库，checksum / row count / application smoke test 证明数据完整，备份失败、过期、复制延迟和恢复失败有监控告警，restore 权限受控且 audit log 记录 backup id、snapshot id、restore run、operator、key id 和 failure reason；只有 backup job 显示成功、生成一个 snapshot 文件或 dashboard 绿色必须阻断。

Weak response:

> 我会让 Builder 配一个 nightly backup job，Inspector 看 dashboard 是绿色并确认生成了 snapshot 文件。

Better response:

> 这条 Loop 不能把“backup job 显示成功”“生成一个 snapshot 文件”或“dashboard 绿色”当成 backup / restore 和 disaster recovery 完成。成功面应当同时包含 backup/restore-recovery、permission/auth、regression/monitoring-guard 和 audit/log：nightly backup、point-in-time recovery、cross-region snapshot、encryption key access、retention policy、legal hold、schema migration 后的 restore 都要可靠，RPO/RTO 要有恢复演练证据，restore drill 要能在隔离环境恢复指定租户和全量库，checksum / row count / application smoke test 要证明数据完整，备份失败、过期、复制延迟和恢复失败要有监控告警，restore 权限和 backup id、snapshot id、restore run、operator、key id、failure reason 要能审计。推荐 workflow 是 Recovery Contract Inspector 先固定 RPO/RTO、PITR、跨区、密钥、保留/legal hold、租户/全量恢复和完整性样本；Backup Recovery Builder 实现备份、恢复演练、权限、监控和审计；Restore Evidence Inspector 验证 restore drill、PITR、tenant/full restore、checksum、row count、application smoke、failure alerts、permission 和 audit log；GateKeeper 只有在 restore recovery、RPO/RTO、data integrity、permission、monitoring、audit 和 backup-job-green-only 反证都进入 Proven 时才通过。你可以选：A. restore drill + PITR + checksum/row count 证据优先（推荐）；B. 先做 backup job 主路径，但把 restore drill 和 RPO/RTO 作为阻断项后补；C. 先做只读恢复合同和备份拓扑评估，再进入 Builder。

## Search index consistency example

User:

> 我要给知识库做全文搜索索引和重建。成功必须证明新建、更新、删除文档会增量同步到 search index，权限和 tenant ACL 变化会立刻从结果中过滤，reindex/backfill 可重跑且幂等，index lag / stale index 有监控告警，搜索结果不会泄露已删除或无权限文档，排序和分页稳定，audit log 记录 reindex run、watermark/cursor 和失败重试；只有本地搜索能返回一个公开文档必须阻断。

Weak response:

> 我会让 Builder 接一个搜索框，Inspector 检查本地搜索能返回一个公开文档，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“本地搜索能返回一个公开文档”当成全文搜索索引完成。成功面应当同时包含 search/index-consistency、permission/auth、access/tenant-isolation、idempotency/duplicate-prevention、regression/monitoring-guard 和 audit/log：新建、更新、删除文档要增量同步到 search index，权限和 tenant ACL 变化要立刻过滤结果，reindex/backfill 要可重跑且幂等，watermark/cursor 失败重试要能恢复，index lag / stale index 要有监控告警，已删除或无权限文档不能从搜索结果泄露，排序和分页要稳定，reindex run、watermark/cursor 和失败重试要能审计。推荐 workflow 是 Search Index Contract Inspector 先固定 create/update/delete、ACL、reindex/backfill、watermark/cursor、lag 监控和分页样本；Search Index Builder 实现增量同步、重建、过滤、重试和审计；Index Consistency Inspector 验证删除/权限负向样本、reindex 幂等、watermark/cursor recovery、stale index monitoring、pagination stability 和 audit log；GateKeeper 只有在 index consistency、ACL filtering、idempotent reindex、monitoring、audit 和 local-search-only 反证都进入 Proven 时才通过。你可以选：A. 增量索引 + ACL 负向 + reindex 幂等证据优先（推荐）；B. 先做搜索主路径，但把 ACL、删除和 reindex 作为阻断项后补；C. 先做只读索引合同和数据流评估，再进入 Builder。

## RAG grounding and tool safety example

User:

> 我要做企业知识库 RAG support chatbot。成功必须证明答案 grounded in retrieved source chunks，citation/source span 能回到文档版本，retrieval ACL / tenant filtering 正确，prompt injection in documents 不能让模型泄露系统提示词或调用未授权 tool，PII/secrets 要 redaction，hallucination 要 fallback/handoff，top-k recall、answer faithfulness、citation precision、no-answer behavior 和 multilingual queries 都在 eval set 里。假完成是只让一个 demo question answered、只看 answer looks plausible、只跑 embedding search、或只在 UI 显示 citations。证据要包含 golden Q&A eval set、negative prompt injection docs、permission-filtered retrieval cases、citation span verification、tool-call allowlist proof、PII leak tests、human review rubric 和 regression monitoring。

Weak response:

> 我会让 Builder 接一个向量搜索和聊天框，Inspector 看 demo question 能回答并且 UI 显示 citation，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“一个 demo question answered”“answer looks plausible”“embedding search 返回结果”或“UI 显示 citations”当成 RAG support chatbot 完成。成功面应当同时包含 ai/rag-grounding-tool-safety、evaluation/eval-set、quality/human-review、permission/auth、privacy/secrets-redaction、regression/monitoring-guard 和 resilience/retry-timeout：答案必须能回到 retrieved source chunks 和 document version，citation/source span 要可校验，retrieval ACL / tenant filtering 不能泄露无权限内容，prompt injection docs 不能泄露系统提示词或触发未授权 tool call，PII/secrets 要脱敏，hallucination 要 fallback/handoff，top-k recall、answer faithfulness、citation precision、no-answer behavior 和 multilingual queries 要进入 eval set。推荐 workflow 是 RAG Contract Inspector 先固定 golden Q&A、source span、权限过滤、prompt injection、tool allowlist、PII、fallback 和多语言样本；RAG Builder 实现检索、回答、引用、tool gating、redaction 和 fallback；Grounding Evidence Inspector 验证 citation span、permission-filtered retrieval、negative prompt injection docs、unauthorized tool-call blocking、PII leak tests、faithfulness/no-answer/multilingual eval 和 monitoring；GateKeeper 只有在 RAG grounding、tool safety、eval set、human review、permission、privacy、fallback/monitoring 和 demo/plausible/UI-citation-only 反证都进入 Proven 时才通过。你可以选：A. source span + prompt injection + permission-filtered retrieval 证据优先（推荐）；B. 先做聊天主路径，但把 tool safety、PII 和 no-answer 作为阻断项后补；C. 先做只读 RAG evaluation contract 和威胁模型，再进入 Builder。

## Long-chain RAG grounding workflow example

User:

> 我要做企业知识库 RAG support chatbot，文档 ingestion、retrieval ACL、answer grounding、tool gating、eval set 和 monitoring 都是独立阶段。最怕的是 UI 看起来能答一个问题，但 citation span、tenant filtering、prompt injection negative docs、PII redaction、no-answer fallback 和 human review rubric 都没有证据。

Weak response:

> 我会创建 RAG Builder、RAG Inspector、RAG GateKeeper；Builder 负责做完聊天功能，Inspector 检查有没有 citation，GateKeeper 最后判断。

Better response:

> 这类任务可能适合长链 workflow，但理由不是“RAG 很复杂所以多放角色”，而是 ingestion、retrieval ACL、answer/tool gating、eval/review 和 monitoring 各自产生不同 proof target 和 handoff。可以考虑 `RAG Contract Inspector -> Corpus Ingestion Builder -> Retrieval ACL Builder -> Answer Tooling Builder -> RAG Evaluation Inspector -> Evidence Hardening Builder -> GateKeeper`。Contract Inspector 先固定 document version、source span、tenant / permission cases、prompt injection docs、tool allowlist、PII 样本、no-answer 和 multilingual eval；Ingestion / Retrieval / Answer Builders 分别只推进一个阶段并留下 handoff；Evaluation Inspector 读取这些 handoff 和 Builder evidence，验证 citation span、permission-filtered retrieval、negative injection docs、unauthorized tool-call blocking、PII leak tests、faithfulness/no-answer/multilingual eval 和 monitoring；Evidence Hardening Builder 只补缺失 proof；GateKeeper 必须读取 contract、eval review、hardening handoff，并用 `inputs.evidence_query.verifies` 查询 grounding、tool safety、permission、privacy、eval-set、human-review 和 monitoring evidence。若某阶段不能产生独立证据或改变后续行动，应合并，避免 role zoo。

## CDC replication consistency example

User:

> 我要把 Postgres 订单数据通过 CDC 同步到 warehouse 和 read model。成功必须证明 snapshot backfill 和 streaming replication 不丢不重，LSN / watermark / checkpoint 正确推进，out-of-order 和 duplicate events 幂等，schema evolution / column rename / delete tombstone 处理正确，replay from checkpoint 能恢复，source row count、checksum、event count 和 warehouse aggregate reconciliation 一致，replication lag、stale checkpoint、DLQ / poison event 和 sync failure 有监控告警，权限过滤和 tenant id 不会串租户，audit log 记录 connector version、source table、LSN、watermark、replay run、failure reason；只有 sync job 绿色、抽样 row count 一致或 dashboard 显示 latest 必须阻断。

Weak response:

> 我会让 Builder 接 CDC sync job，Inspector 检查任务绿色、抽样 row count 一致和 dashboard latest，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“sync job 绿色”“抽样 row count 一致”或“dashboard 显示 latest”当成 CDC 同步完成。成功面应当同时包含 data/cdc-replication-consistency、idempotency/duplicate-prevention、permission/auth、access/tenant-isolation、regression/monitoring-guard、queue/failure-recovery 和 audit/log：snapshot backfill 与 streaming replication 都要证明不丢不重，LSN / watermark / checkpoint 要正确推进，out-of-order 和 duplicate events 要幂等，schema evolution / column rename / delete tombstone 要处理正确，checkpoint replay 要能恢复，source row count、checksum、event count 和 warehouse aggregate 要能对账，replication lag、stale checkpoint、DLQ / poison event 和 sync failure 要有监控告警，tenant id 与权限过滤不能串租户，connector version、source table、LSN、watermark、replay run 和 failure reason 要能审计。推荐 workflow 是 CDC Contract Inspector 先固定 backfill、streaming、LSN/watermark/checkpoint、schema/tombstone、tenant、DLQ 和 reconciliation 样本；CDC Sync Builder 实现复制、checkpoint、幂等、schema 处理、对账和审计；Replication Evidence Inspector 验证 backfill/streaming、乱序/重复事件、checkpoint replay、row/checksum/event/aggregate reconciliation、lag/DLQ/poison/failure alerts、tenant filtering 和 audit log；GateKeeper 只有在 CDC consistency、idempotency、tenant isolation、monitoring、queue recovery、audit 和 sync-job/dashboard-only 反证都进入 Proven 时才通过。你可以选：A. backfill + checkpoint + replay + reconciliation 证据优先（推荐）；B. 先做 sync job 主路径，但把 LSN/checkpoint、schema 和对账作为阻断项后补；C. 先做只读 CDC 合同和数据流评估，再进入 Builder。

## File upload storage safety example

User:

> 我要做用户文件上传到对象存储。成功必须证明 MIME / content-type sniffing、文件大小限制、virus / malware scan、quarantine、signed URL 权限、租户隔离、失败上传清理和 audit log 都可靠；只有 upload 返回 URL 或一个 happy path 文件上传成功必须阻断。

Weak response:

> 我会让 Builder 做文件上传，Inspector 检查能返回 URL，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“upload 返回 URL”或“一个 happy path 文件上传成功”当成对象存储上传完成。成功面应当同时包含 file-upload/storage-safety、permission/auth、access/tenant-isolation 和 audit/log：MIME / content-type sniffing、文件大小限制、virus / malware scan、quarantine、signed URL 权限、失败上传清理和跨租户负向访问都要有可复验证据。推荐 workflow 是 Upload Contract Inspector 先固定文件类型、大小、扫描 / 隔离、signed URL、租户隔离和失败清理样本；Upload Builder 实现最小上传、存储访问、扫描状态和审计路径；Storage Safety Inspector 验证 MIME spoofing、超大文件、恶意样本隔离、签名 URL 过期 / 越权、失败上传清理和 audit log；GateKeeper 只有在 upload safety、permission、tenant isolation、audit 和 returned-URL-only 反证都进入 Proven 时才通过。你可以选：A. MIME + malware scan + signed URL + cleanup 证据优先（推荐）；B. 先做上传主路径，但把扫描、隔离和失败清理作为阻断项后补；C. 先做只读对象存储访问与扫描策略评估，再进入 Builder。

## Notification deliverability example

User:

> 我要做 lifecycle campaign email。成功必须证明只给已订阅且符合偏好的用户发送，unsubscribe / preference center 生效，suppression list、bounce、complaint 不会继续发送，provider delivery event 能和本地 audit log 对账，中英文模板变量一致且 PII 不泄露；只有 provider accepted 或一个测试邮箱收到邮件必须阻断。

Weak response:

> 我会让 Builder 接邮件 provider，Inspector 检查一个测试邮箱收到邮件，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“provider accepted”或“一个测试邮箱收到邮件”当成 lifecycle campaign email 完成。成功面应当同时包含 notification/subscription-deliverability、notification/message、idempotency/duplicate-prevention、privacy/secrets-redaction、locale/i18n 和 audit/log：只有已订阅且符合偏好的用户能收到，unsubscribe / preference center 必须生效，suppression list、bounce、complaint 不能继续发送，provider delivery event 要能和本地 audit log 对账，中英文模板变量一致且 PII 不泄露。推荐 workflow 是 Notification Contract Inspector 先固定订阅偏好、退订、suppression、bounce/complaint、delivery event、template locale 和 PII 样本；Campaign Email Builder 实现发送、过滤和审计；Deliverability Evidence Inspector 验证 provider delivery / bounce / complaint 事件、本地 audit、模板变量、PII 和重复发送反证；GateKeeper 只有在 subscription-deliverability、privacy、locale、audit 和 provider-accepted-only 反证都进入 Proven 时才通过。你可以选：A. 订阅偏好 + suppression/bounce + delivery event 对账证据优先（推荐）；B. 先做发送主路径，但把退订、bounce/complaint 和 PII 作为阻断项后补；C. 先做只读 provider / preference 合同评估，再进入 Builder。

## Scheduled digest timezone example

User:

> 我要做 weekly digest 定时发送。成功必须证明每个用户按自己的 timezone 本地周一 09:00 收到，DST / 夏令时切换前后不会提前或延后，错过执行后 catch-up 只补一次，重试不会重复发送，取消订阅或禁用用户不会发送，audit log 能追踪 scheduled_at / sent_at；只有 cron expression 配好或本地触发一次必须阻断。

Weak response:

> 我会让 Builder 加一个 cron job，Inspector 检查本地触发一次，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“cron expression 配好”或“本地触发一次”当成 weekly digest 完成。成功面应当同时包含 schedule/timezone-recurrence、notification/subscription-deliverability、idempotency/duplicate-prevention 和 audit/log：每个用户要按自己的 timezone 本地周一 09:00 收到，DST / 夏令时边界不能提前或延后，missed run catch-up 只能补一次，重试不能重复发送，取消订阅或禁用用户不能收到，scheduled_at / sent_at 要能审计。推荐 workflow 是 Schedule Contract Inspector 先固定 timezone、DST、missed-run、catch-up、subscription 和 audit 样本；Digest Scheduler Builder 实现调度、发送、补偿、幂等和审计；Schedule Evidence Inspector 验证多时区、本地时间、DST 前后、错过执行补偿、重复触发、退订/禁用用户和 audit log；GateKeeper 只有在 timezone recurrence、catch-up idempotency、subscription filtering、audit 和 cron-only 反证都进入 Proven 时才通过。你可以选：A. 时区 + DST + catch-up + 幂等证据优先（推荐）；B. 先做 cron 主路径，但把 DST / missed run / duplicate send 作为阻断项后补；C. 先做只读 schedule contract 评估，确认时区和补偿语义后再 Builder。

## Migration rollback example

User:

> 我要把 billing 的 invoice 状态从旧 enum 迁到新的 state machine。成功必须证明历史 invoice 数据迁移后金额和状态不丢失，旧 API 和旧报表兼容，迁移可以回滚；只有单元测试通过但没有 dry-run、row-count/checksum 和 rollback proof 必须阻断。

Weak response:

> 我会让 Builder 做状态迁移，Inspector 跑测试，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“迁移代码写完”或“单元测试通过”当成成功。成功面应当同时包含 migration/rollback-integrity、compatibility/backward-compat 和 billing data proof：历史 invoice 金额与状态经过迁移 dry-run 后 row-count / checksum 对得上，rollback 路径可复验，旧 API / 旧报表仍能读取兼容状态。推荐 workflow 是 Builder 先实现最小迁移与兼容适配；Migration Integrity Inspector 读取迁移 artifact、dry-run 输出、row-count/checksum 和 rollback proof；Compatibility Inspector 验证旧 API / 旧报表兼容；GateKeeper 只有在数据完整性、回滚、向后兼容证据都进入 Proven 时才通过。你可以选：A. dry-run + checksum + rollback + 兼容证据优先（推荐）；B. 先实现迁移，回滚和兼容作为阻断项后补；C. 先做只读评估，确认迁移范围后再进入 Builder。

## AI quality evaluation example

User:

> 我要优化 help-center semantic search。成功必须证明 Top-5 结果质量提升，eval set 覆盖真实查询、负例和回归样本，人工评审要看 relevance 和 hallucination risk；只有一个 demo query 看起来更好或 benchmark 分数单点上涨必须阻断。

Weak response:

> 我会让 Builder 优化搜索，Inspector 看 benchmark 分数，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“一个 demo query 变好”或“单个 benchmark score 上涨”当成成功。成功面应当同时包含 evaluation/eval-set 和 quality/human-review：eval set 要覆盖真实查询、负例、回归样本和 Top-5 结果，人工评审要按 relevance、hallucination risk / groundedness 记录判断。推荐 workflow 是 Evaluation Baseline Inspector 先固定当前 eval set、review rubric 和 baseline 结果；Search Builder 只改排序 / 检索策略并留下变更与候选结果 artifact；Quality Inspector 比较 before/after、负例和回归样本，标出 Proven / Weak / Unproven；GateKeeper 只有在 eval-set coverage、人工评审质量证据和回归未退化都进入 Proven 时才通过。你可以选：A. eval set + 人工评审 + 回归样本优先（推荐）；B. 先扩 eval set，再进入 Builder；C. 只做 benchmark-guided Loop，但明确 benchmark 之外的人工质量风险由 GateKeeper 阻断。

## Incident remediation example

User:

> 我要修一个生产事故：checkout 偶发重复扣款。成功必须证明能复现或解释触发条件，找到 root cause，补 regression test，监控/告警能发现复发，发布或回滚路径清楚；只有 patch 了一个分支但没有 repro、root-cause proof 或 monitoring evidence 必须阻断。

Weak response:

> 我会让 Builder 修 checkout，Inspector 跑测试，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“打了一个 patch”或“现有测试通过”当成事故修复完成。成功面应当同时包含 incident/root-cause-repro 和 regression/monitoring-guard：先要能复现或解释触发条件，root cause 要能被证据连接到重复扣款，修复后必须有 regression test，监控 / 告警或运行手册能发现复发，发布 / 回滚路径清楚。推荐 workflow 是 Repro Inspector 先固定复现证据或触发条件；Incident Builder 修 root cause 并留下 patch / regression evidence；Monitoring Inspector 验证监控、告警或复发发现路径；GateKeeper 只有在 root-cause proof、regression guard、monitoring evidence 和 rollback / release handoff 都进入 Proven 时才通过。你可以选：A. 复现 + 根因 + 回归 + 监控证据优先（推荐）；B. 先止血 patch，但把 root cause 和 monitoring 作为阻断项后补；C. 先做只读事故分析，确认触发条件后再改代码。

## Feature flag rollout safety example

User:

> 我要把新版 checkout 放到 feature flag 后灰度发布。成功必须证明默认关闭，只有 beta cohort 命中，percentage rollout 稳定，用户不会在一次 session 内新旧体验来回跳，kill switch 能立即回退，rollback 不留脏状态，监控/告警能发现错误率和支付转化异常，audit log 记录谁改了 flag、cohort、percentage 和 kill switch；只有本地 flag 能打开新版 checkout 必须阻断。

Weak response:

> 我会让 Builder 加一个 feature flag，Inspector 检查本地开关能打开新版 checkout，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“本地 flag 能打开新版 checkout”当成灰度发布完成。成功面应当同时包含 release/feature-flag-rollout、experiment/assignment-consistency、regression/monitoring-guard、payment/refund/billing 和 audit/log：feature flag 默认关闭，beta cohort 和 percentage rollout 要稳定命中，同一用户 session 内不能新旧 checkout 来回跳，kill switch 要能立即回退，rollback 后不能留下脏状态，错误率 / 支付转化监控和告警阈值要有证据，flag、cohort、percentage 和 kill switch 变更要能审计。推荐 workflow 是 Rollout Contract Inspector 先固定 cohort、percentage、session consistency、kill switch、rollback、监控阈值和 audit 样本；Checkout Flag Builder 实现 flag、targeting、sticky exposure、kill switch 和 rollback 清理；Rollout Safety Inspector 验证默认关闭、cohort targeting、percentage stability、session exposure consistency、kill switch、rollback、monitoring / alert 和 audit log；GateKeeper 只有在 rollout safety、assignment consistency、monitoring、billing-impact 和 local-flag-only 反证都进入 Proven 时才通过。你可以选：A. cohort + kill switch + monitoring 证据优先（推荐）；B. 先接 feature flag 主路径，但把 kill switch / monitoring / rollback 作为阻断项后补；C. 先做只读 rollout contract 和风险矩阵，再进入 Builder。

## External provider resilience example

User:

> 我要接入一个第三方 shipping quote provider API。成功必须证明 sandbox provider contract 能返回真实 rate，signature/auth 处理正确，timeout、rate limit、retry/backoff 和 fallback 都有证据；只有 mock response 或 happy path API call 成功必须阻断。

Weak response:

> 我会让 Builder 接 API，Inspector 跑测试，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“mock response 通过”或“一次 happy path API call 成功”当成 provider 集成完成。成功面应当同时包含 external/provider-contract、permission/auth 和 resilience/retry-timeout：sandbox provider contract 要返回真实 rate，signature/auth 要有正负向证据，timeout、rate limit、retry/backoff、fallback 都要有可复验结果。推荐 workflow 是 Provider Contract Inspector 先固定 provider sandbox / contract proof 和可用凭据边界；Integration Builder 接入最小真实 quote path 并留下 contract probe、auth handling 和 fallback artifact；Resilience Inspector 验证 timeout、限流、retry/backoff 与 fallback；GateKeeper 只有在 provider contract、auth、resilience evidence 和 mock/happy-path 反证都进入 Proven 时才通过。你可以选：A. sandbox contract + auth + resilience 证据优先（推荐）；B. 先接最小 API，再把 resilience 作为阻断项后补；C. 先做只读 provider contract 探测，确认边界后再 Builder。

## Payment webhook reconciliation example

User:

> 我要接 Stripe subscription webhook。成功必须证明 webhook signature 验证、重复事件幂等、乱序 invoice.paid / customer.subscription.updated 不会把订阅状态写错，provider event replay 可以恢复本地 ledger，invoice 金额和订阅权限要能和 Stripe dashboard / fixture 对账；只有一个 webhook happy path 更新 invoice 状态或 mock event 通过必须阻断。

Weak response:

> 我会让 Builder 接收 Stripe webhook，Inspector 检查一个 mock invoice.paid 能更新 invoice 状态，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“一个 webhook happy path 更新 invoice 状态”或 mock event 通过当成订阅账单接入完成。成功面应当同时包含 webhook/signature-replay-ordering、billing/ledger-reconciliation、idempotency/duplicate-prevention、payment/refund/billing 和 audit/log：webhook signature 必须验证，重复事件必须幂等，乱序 invoice / subscription 事件不能写错订阅状态，provider event replay 要能恢复本地 ledger，invoice 金额、订阅权限和 Stripe dashboard / fixture 要能对账。推荐 workflow 是 Webhook Contract Inspector 先固定事件类型、签名、乱序/重放样本和 ledger 对账目标；Billing Webhook Builder 实现接收、幂等、状态写入和审计；Ledger Reconciliation Inspector 验证签名、重复/乱序/replay、ledger、invoice amount 和 entitlement sync；GateKeeper 只有在 webhook ordering、ledger reconciliation、idempotency、audit 和 mock/happy-path 反证都进入 Proven 时才通过。你可以选：A. 签名 + 乱序/replay + ledger 对账证据优先（推荐）；B. 先接收 webhook 主路径，但把重放、乱序和 ledger 对账作为阻断项后补；C. 先做只读事件合同评估，确认 provider 事件边界后再 Builder。

## Dispute chargeback lifecycle example

User:

> 我要做支付争议和 chargeback lifecycle。成功必须证明 provider dispute.created/updated/closed webhook、retrieval request、representment evidence submission deadline、issuer/acquirer reason code、provisional credit/debit、fee、win/loss、partial dispute、duplicate dispute、refund overlap、order fulfillment evidence、customer notification、merchant response SLA、ledger entries、invoice/balance adjustment、payout hold/release、audit trail 和 monitoring 都一致。假完成是只让一个 dispute webhook 改 UI 状态、只在 Stripe dashboard 看 won/lost、只保存 provider dispute id、或 happy-path close。证据要包含 provider fixture contract、signature/replay/out-of-order webhook cases、deadline scheduler proof、evidence package artifact、ledger reconciliation、refund/chargeback overlap negatives、notification delivery proof、merchant SLA cases、audit reason refs 和 failed/stale dispute alerts。

Weak response:

> 我会让 Builder 接一个 dispute webhook，Inspector 看 UI 状态变了、Stripe dashboard 显示 won/lost，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“dispute webhook 改 UI 状态”“Stripe dashboard 看 won/lost”“保存 provider dispute id”或“happy-path close”当成 chargeback lifecycle 完成。成功面应当同时包含 payment/dispute-chargeback-lifecycle、webhook/signature-replay-ordering、billing/ledger-reconciliation、payout/settlement-reconciliation、payment/refund/billing、notification/message、audit/log、audit/log-integrity-retention 和 regression/monitoring-guard：provider dispute.created/updated/closed、retrieval request、representment evidence submission deadline、issuer/acquirer reason code、provisional credit/debit、fee、win/loss、partial/duplicate dispute、refund overlap、order fulfillment evidence、customer notification、merchant response SLA、ledger entries、invoice/balance adjustment、payout hold/release、audit trail 和 monitoring 都要一致。推荐 workflow 是 Dispute Contract Inspector 先固定 provider fixtures、webhook signature/replay/order、deadline、reason code、refund overlap、ledger/payout 和 notification/SLA 样本；Chargeback Builder 实现争议状态机、证据包、deadline scheduler、通知、账本、payout hold/release 和审计；Dispute Evidence Inspector 验证 dispute created/updated/closed、out-of-order/replay、evidence package artifact、deadline scheduler、ledger reconciliation、refund/chargeback overlap negatives、notification delivery、merchant SLA、audit reason refs 和 failed/stale dispute alerts；GateKeeper 只有在 dispute lifecycle、webhook ordering、ledger/payout reconciliation、notification/SLA、audit、monitoring 和 dashboard/status/id-only 反证都进入 Proven 时才通过。你可以选：A. provider fixtures + evidence deadline + ledger/refund overlap 证据优先（推荐）；B. 先接 dispute webhook 主路径，但把 deadline、evidence package 和 payout hold 作为阻断项后补；C. 先做只读 dispute contract 和账务状态机评估，再进入 Builder。

## Marketplace payout settlement example

User:

> 我要做 marketplace seller payout。成功必须证明 order captured/refunded/chargeback 都进入 seller balance ledger，platform fee、tax、adjustment、hold/reserve 和 negative balance 正确计算，payout batch cutoff / timezone / currency / FX rounding 正确，provider transfer id、bank account、KYC hold、failed payout、retry 和 reversal 幂等，不会 double payout，Stripe/Adyen payout report、本地 ledger、invoice 和 bank statement 能对账，seller/tenant 访问不能串数据，audit log 记录 payout batch id、ledger entry id、provider transfer id、actor、failure reason，监控要发现 stuck payout、failed transfer 和 reconciliation mismatch；只有 Stripe dashboard 显示 paid、一笔 test payout 成功或 UI 显示余额减少必须阻断。

Weak response:

> 我会让 Builder 接一笔 Stripe test payout，Inspector 检查 Stripe dashboard 显示 paid、UI 余额减少，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“Stripe dashboard 显示 paid”“一笔 test payout 成功”或“UI 显示余额减少”当成 marketplace payout 完成。成功面应当同时包含 payout/settlement-reconciliation、billing/ledger-reconciliation、payment/refund/billing、idempotency/duplicate-prevention、access/tenant-isolation、permission/auth、regression/monitoring-guard 和 audit/log：order captured/refunded/chargeback 都要进入 seller balance ledger，platform fee、tax、adjustment、hold/reserve、negative balance、payout batch cutoff / timezone / currency / FX rounding 要正确，provider transfer id、bank account、KYC hold、failed payout、retry、reversal 要幂等且不能 double payout，Stripe/Adyen payout report、本地 ledger、invoice 和 bank statement 要能对账，seller/tenant 访问不能串数据，payout batch id、ledger entry id、provider transfer id、actor、failure reason 要能审计，stuck payout、failed transfer 和 reconciliation mismatch 要有监控告警。推荐 workflow 是 Payout Contract Inspector 先固定 seller balance、fee/tax/adjustment/hold、batch cutoff、currency/FX、provider transfer、KYC/negative balance、reversal 和访问样本；Payout Settlement Builder 实现账本、批次、转账、幂等和审计；Settlement Evidence Inspector 验证 captured/refund/chargeback、failed payout/retry/reversal、double-payout 负向、provider report / local ledger / invoice / bank statement reconciliation、tenant access 和 alert；GateKeeper 只有在 payout settlement、ledger reconciliation、idempotency、tenant isolation、monitoring、audit 和 test-payout/dashboard-only 反证都进入 Proven 时才通过。你可以选：A. seller ledger + payout batch + provider/bank 对账证据优先（推荐）；B. 先做 test payout 主路径，但把 ledger、reversal 和对账作为阻断项后补；C. 先做只读 settlement contract 和风险矩阵，再进入 Builder。

## KYC AML sanctions screening example

User:

> 我要做 marketplace seller onboarding 的 KYC/KYB and AML sanctions screening。成功必须证明 identity verification、business registry、beneficial owner、document OCR/liveness、address verification、sanctions/PEP/adverse media/watchlist screening、risk score、manual review queue、appeal/resubmission、periodic rescreening、provider webhook replay/out-of-order/idempotency、region retention、audit reason codes 和 payout hold/release 都一致。假完成是只让一个 provider sandbox 返回 approved、UI 显示 verified、只存 provider status、或只跑 happy-path webhook。证据要包含 provider contract fixtures、golden approved/rejected/manual-review cases、false positive/false negative sanctions samples、expired/fraudulent document negatives、manual review rubric、decision reason audit trail、webhook signature/replay/order proof、rescreening job proof、payout hold ledger reconciliation、privacy redaction 和 monitoring alerts。

Weak response:

> 我会让 Builder 接一个 provider sandbox，Inspector 检查 sandbox 返回 approved、UI 显示 verified，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“provider sandbox 返回 approved”“UI 显示 verified”“只存 provider status”或“happy-path webhook 通过”当成 KYC/KYB and AML sanctions screening 完成。成功面应当同时包含 compliance/kyc-aml-sanctions-screening、external/provider-contract、webhook/signature-replay-ordering、payout/settlement-reconciliation、billing/ledger-reconciliation、quality/human-review、audit/log、privacy/secrets-redaction、data-lifecycle/deletion-retention 和 regression/monitoring-guard：identity verification、business registry、beneficial owner、document OCR/liveness、address verification、sanctions/PEP/adverse media/watchlist、risk score、manual review queue、appeal/resubmission、periodic rescreening、provider webhook replay/out-of-order/idempotency、region retention、audit reason codes 和 payout hold/release 都要有证据。推荐 workflow 是 Compliance Contract Inspector 先固定 provider contract、approved/rejected/manual-review、false positive/false negative sanctions、expired/fraudulent document、manual review、rescreening、webhook 和 payout hold 样本；Onboarding Compliance Builder 实现核验、筛查、人审、复筛、webhook、冻结/放行、隐私和审计；KYC Evidence Inspector 验证 sanctions/PEP/adverse media/watchlist、证件负例、误报漏报、manual review rubric、decision reason audit、webhook replay/order、rescreening job、payout hold ledger reconciliation、privacy redaction 和 monitoring alerts；GateKeeper 只有在 KYC/AML screening、provider contract、webhook ordering、manual review、payout hold ledger、privacy、audit、monitoring 和 sandbox/UI/status-only 反证都进入 Proven 时才通过。你可以选：A. sanctions/PEP + document negatives + payout hold ledger 证据优先（推荐）；B. 先接 provider 主路径，但把误报漏报、复筛和 reason audit 作为阻断项后补；C. 先做只读合规合同和风险样本矩阵，再进入 Builder。

## MRR metric reconciliation example

User:

> 我要做 MRR dashboard。成功必须证明 MRR/ARR 指标口径固定，trial、coupon、discount、refund、proration、downgrade/upgrade、paused subscription 的处理正确，币种转换和汇率日期一致，月份 cutoff / timezone 正确，和 billing ledger / invoice / subscription provider 对账，historical backfill 不改旧月锁账，权限不同的用户只能看自己的 revenue segment，audit log 记录 metric definition version 和 backfill run；只有图表显示数字或 CSV 能导出必须阻断。

Weak response:

> 我会让 Builder 做收入看板，Inspector 检查图表能显示数字和 CSV 能导出，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“图表显示数字”或“CSV 能导出”当成 MRR dashboard 完成。成功面应当同时包含 reporting/metric-reconciliation、billing/ledger-reconciliation、payment/refund/billing、permission/auth、audit/log 和 data/export/report：MRR/ARR 指标口径和 metric definition version 要固定，trial / coupon / discount / refund / proration / downgrade / upgrade / paused subscription 的处理要可复验，币种转换、汇率日期、月份 cutoff 和 timezone 要一致，billing ledger / invoice / subscription provider 要对账，historical backfill 不能改旧月锁账，不同权限用户只能看自己的 revenue segment，backfill run 和口径版本要能审计。推荐 workflow 是 Metric Contract Inspector 先固定 MRR/ARR 口径、边界样本、FX 日期、cutoff、provider/ledger 对账和锁账规则；Revenue Dashboard Builder 实现指标查询、权限过滤、backfill 和审计；Metric Reconciliation Inspector 验证口径边界、汇率/cutoff、ledger/invoice/provider 对账、旧月锁账、权限分段和 audit log；GateKeeper 只有在 metric reconciliation、billing reconciliation、permission、audit 和 chart/CSV-only 反证都进入 Proven 时才通过。你可以选：A. 指标口径 + 对账 + 锁账回填证据优先（推荐）；B. 先做看板主路径，但把口径、对账和权限作为阻断项后补；C. 先做只读 metric contract 和历史数据评估，再进入 Builder。

## Tenant isolation example

User:

> 我要给 B2B SaaS 加 workspace sharing 权限。成功必须证明 tenant isolation：Org A 用户不能通过 UI、API 或 direct object ID 访问 Org B dashboard，owner/member/viewer 角色矩阵正确，audit log 记录越权尝试；只有 owner happy path 能打开 dashboard 必须阻断。

Weak response:

> 我会让 Builder 做权限判断，Inspector 检查 owner 能打开 dashboard，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“owner happy path 能打开”当成权限功能完成。成功面应当同时包含 access/tenant-isolation、permission/auth 和 audit/log：Org A / Org B 至少要有跨租户负向样本，UI、API 和 direct object ID 都要证明不能越权，owner/member/viewer 角色矩阵要覆盖允许与拒绝路径，audit log 要记录越权尝试。推荐 workflow 是 Access Matrix Inspector 先固定角色矩阵和跨租户测试样本；Permission Builder 实现 workspace sharing；Tenant Isolation Inspector 验证 UI/API/direct object ID 的负向访问和 audit evidence；GateKeeper 只有在 tenant isolation、role matrix、audit 和 happy-path 反证都进入 Proven 时才通过。你可以选：A. 跨租户负向证据 + 角色矩阵 + 审计优先（推荐）；B. 先做 owner/member/viewer 主流程，但把 direct object ID 和 audit 作为阻断项后补；C. 先做只读权限矩阵评估，再进入 Builder。

## Authorization policy consistency example

User:

> 我要重做企业后台的 RBAC/ABAC authorization policy engine。成功必须证明 role hierarchy、resource scope、team membership、owner/admin/viewer、deny-overrides-allow、field-level permissions、审批流、API endpoint enforcement、UI affordance、background job、export/report 和 audit log 都使用同一 policy decision；角色变更、组织迁移、SCIM/SSO group mapping、临时权限、policy version rollout 和 cache invalidation 都一致。假完成是只隐藏按钮、只加 middleware、只检查一个 admin role、或只让 happy-path endpoint 过。证据要包含 permission matrix contract、policy decision trace、negative authorization cases、cross-resource escalation attempts、cache stale/revocation proof、audit log immutable refs 和 migration rollback/compat proof。

Weak response:

> 我会让 Builder 加 middleware 和隐藏按钮，Inspector 跑一个 admin endpoint happy path，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“隐藏按钮”“加 middleware”或“一条 admin happy path 通过”当成 authorization policy engine 完成。成功面应当同时包含 access/authorization-policy-consistency、permission/auth、identity/provisioning-role-mapping、cache/invalidation-consistency、audit/log-integrity-retention、migration/rollback-integrity、compatibility/backward-compat、data/export/report 和 async/job-lifecycle：role hierarchy、resource scope、team membership、deny-overrides-allow、field-level permissions、审批流、API endpoint、UI affordance、background job、export/report 和 audit log 必须引用同一 policy decision，角色变更、SCIM/SSO group mapping、临时权限、policy version rollout、cache stale/revocation、negative authorization cases 和 cross-resource escalation 都要有可复验证据。推荐 workflow 是 Authorization Policy Contract Inspector 先固定 permission matrix、policy decision trace、role/resource/field 样本、SCIM/SSO 映射、cache/revocation 和负向授权；Policy Engine Builder 实现 PDP/PEP、API/UI/job/export/audit 统一决策和版本发布；Authorization Evidence Inspector 验证 deny-overrides-allow、字段权限、跨资源提权、缓存陈旧、撤销、导出/报表、审计不可变引用和迁移兼容；GateKeeper 只有在 authorization policy consistency、permission、identity mapping、cache invalidation、audit integrity、migration/compat 和 button/middleware/admin-only 反证都进入 Proven 时才通过。你可以选：A. permission matrix + policy decision trace + 负向授权证据优先（推荐）；B. 先做 API enforcement 主路径，但把 UI/job/export/audit 和 cache/revocation 作为阻断项后补；C. 先做只读 authorization policy contract 和迁移风险矩阵，再进入 Builder。

## Support impersonation break-glass example

User:

> 我要给 B2B SaaS 做 support impersonation / break-glass admin access。成功必须证明 support agent 只能在 approved ticket、customer consent、reason code 和 supervisor approval 下限时 impersonate 指定 tenant/user；session attribution 必须区分 actor、acting_as、on_behalf_of，不能共享 admin token 或绕过 MFA policy，PII 字段默认遮蔽，destructive actions 要阻断或 step-up approval，tenant isolation 不能串租户，audit log 不可篡改并记录 actor、target user、ticket id、reason、start/end、IP、user agent、viewed records、changes、export attempts；访问自动过期，revoke 立即生效，监控要发现 no-ticket impersonation、after-hours access、bulk record view、sensitive data view、export/download attempt 和 long-running session；只有 support 能登录客户账号、打开 feature flag、共享管理员 token 或 UI 显示 impersonating banner 必须阻断。

Weak response:

> 我会让 Builder 加一个 impersonate button 和 banner，Inspector 检查 support 能登录客户账号，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“support 能登录客户账号”“打开 feature flag”“共享管理员 token”或“UI 显示 impersonating banner”当成 support impersonation / break-glass access 完成。成功面应当同时包含 access/support-impersonation-breakglass、permission/auth、access/tenant-isolation、privacy/secrets-redaction、audit/log、audit/log-integrity-retention、auth/session-token-lifecycle、regression/monitoring-guard 和 data/export/report：approved ticket、customer consent、reason code、supervisor approval、限时会话、actor / acting_as / on_behalf_of 归因、MFA policy、PII masking、destructive action step-up、跨租户负向、不可篡改审计、自动过期、revoke、异常访问监控和 export/download attempt 都要有证据。推荐 workflow 是 Impersonation Contract Inspector 先固定审批、同意、reason、限时、归因、MFA、PII、破坏性动作和租户负向样本；Break-glass Builder 实现代理访问、授权校验、会话、遮蔽、审计和撤销；Access Evidence Inspector 验证 no-ticket、过期、revoke、MFA/step-up、敏感字段、跨租户、导出尝试、批量查看、长会话监控和 audit immutability；GateKeeper 只有在 impersonation governance、permission、tenant isolation、privacy、session lifecycle、monitoring、audit integrity 和 login/banner-only 反证都进入 Proven 时才通过。你可以选：A. 审批/同意 + 会话归因 + 撤销/审计证据优先（推荐）；B. 先做代理登录主路径，但把隐私、撤销和异常监控作为阻断项后补；C. 先做只读 break-glass policy 和风险矩阵，再进入 Builder。

## Data residency regional isolation example

User:

> 我要给企业客户做 data residency / regional isolation。成功必须证明 EU tenant 的 primary DB、object storage、search index、cache、queue、backup、logs、analytics export 和 third-party processor 都只落在 EU region，US tenant 只落在 US region，region routing / tenant residency policy / encryption key region 不能错，cross-region failover 不能把 EU 数据复制到 US，migration/backfill 不跨区，support/admin access、data export、audit log 和 observability trace 都不能泄露跨区数据，subprocessor allowlist 和 DPA 标记正确，监控要发现 cross-region egress、wrong-region write、stale residency policy 和 processor mismatch；只有 UI 显示 region=EU、配置 env var 或数据库 tenant 表有 region 字段必须阻断。

Weak response:

> 我会让 Builder 加一个 region selector 和 env var，Inspector 检查 UI 显示 region=EU、tenant 表有 region 字段，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“UI 显示 region=EU”“配置 env var”或“tenant 表有 region 字段”当成 data residency / regional isolation 完成。成功面应当同时包含 data/residency-regional-isolation、access/tenant-isolation、permission/auth、privacy/secrets-redaction、external/provider-contract、regression/monitoring-guard、backup/restore-recovery、search/index-consistency、analytics/event-integrity 和 audit/log：EU / US tenant 的 primary DB、object storage、search index、cache、queue、backup、logs、analytics export、third-party processor、subprocessor allowlist、DPA、region routing、tenant residency policy、encryption key region、failover、migration/backfill、support/admin access、data export、audit log 和 observability trace 都要有区域证据和错区反证。推荐 workflow 是 Residency Contract Inspector 先固定 EU/US 数据面、路由/策略/key region、failover、migration/backfill、processor/DPA、访问/export/observability 样本；Regional Isolation Builder 实现区域路由、存储/索引/队列/备份/日志/processor 边界和监控；Residency Evidence Inspector 验证 DB/storage/search/cache/queue/backup/logs/analytics/processor 的 region proof、wrong-region write、cross-region egress、processor mismatch 和 stale policy 告警；GateKeeper 只有在 residency evidence、wrong-region 负向、processor/DPA、tenant isolation、privacy、monitoring、audit 和 UI/env/tenant-field-only 反证都进入 Proven 时才通过。你可以选：A. 数据驻留边界 + wrong-region 负向 + processor/DPA 证据优先（推荐）；B. 先做区域路由主路径，但把 processor、failover 和 observability 作为阻断项后补；C. 先做只读 residency contract 和数据面清单评估，再进入 Builder。

## Accessibility checkout example

User:

> 我要重做 checkout modal。成功必须证明键盘用户可以完整下单，focus trap 不会丢焦点，screen reader / ARIA label、错误提示 announcement、WCAG contrast 都有证据；中英文界面操作语义一致；只有视觉截图或鼠标 happy path 通过必须阻断。

Weak response:

> 我会让 Builder 打磨 checkout modal，Inspector 看截图，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“视觉截图”或“鼠标 happy path 通过”当成 checkout modal 完成。成功面应当同时包含 accessibility/a11y、locale/i18n、browser/journey 和 command/test：键盘用户必须能完成下单，focus trap / focus order 不能丢焦点，screen reader / ARIA label、错误提示 announcement、WCAG contrast 要有证据，中英文界面操作语义要保持一致。推荐 workflow 是 Accessibility Contract Inspector 先固定键盘路径、焦点规则、读屏标签、错误播报、对比度和 locale parity 样本；Checkout Modal Builder 实现交互和视觉；Accessibility Evidence Inspector 用浏览器/axe/可访问性查询或项目测试验证 keyboard、focus、ARIA、announcement、contrast 和 locale parity；GateKeeper 只有在 a11y、locale parity、browser journey 和 screenshot-only 反证都进入 Proven 时才通过。你可以选：A. 键盘 + 读屏 + locale parity 证据优先（推荐）；B. 先做视觉和主流程，但把 keyboard / focus / ARIA / contrast 作为阻断项后补；C. 先做只读 accessibility audit，确认缺口后再 Builder。

## SSO identity assertion example

User:

> 我要给企业客户接 SAML/OIDC SSO。成功必须证明 IdP metadata 和 assertion signature 验证正确，tenant domain binding 防止 A 公司 assertion 登录 B 公司，JIT provisioning / SCIM 角色映射 owner / admin / member 正确，logout 和 session expiry 有证据，失败断言和伪造 assertion 会被审计；只有一个 Okta 测试用户能登录必须阻断。

Weak response:

> 我会让 Builder 接 Okta 登录，Inspector 检查一个测试用户能登录，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“一个 Okta 测试用户能登录”当成企业 SSO 完成。成功面应当同时包含 identity/sso-assertion、identity/provisioning-role-mapping、access/tenant-isolation、permission/auth 和 audit/log：IdP metadata、issuer / audience、assertion signature 要验证；tenant domain binding 要阻止 A 公司 assertion 登录 B 公司；JIT provisioning / SCIM、owner / admin / member role mapping 要覆盖允许与拒绝路径；logout / session expiry 和伪造 assertion audit 都要有证据。推荐 workflow 是 Identity Contract Inspector 先固定 IdP metadata、assertion、租户绑定、role mapping 和负向样本；SSO Builder 实现登录、provisioning 和 session；Identity Evidence Inspector 验证签名、租户绑定、JIT/SCIM、角色映射、logout/session expiry、伪造断言审计；GateKeeper 只有在 assertion、provisioning、tenant isolation、permission 和 audit 反证都进入 Proven 时才通过。你可以选：A. assertion + tenant binding + role mapping 证据优先（推荐）；B. 先接通 SSO 主路径，但把伪造断言、跨租户和 role mapping 作为阻断项后补；C. 先做只读 IdP/metadata/role mapping 评估，确认边界后再 Builder。

## API key rotation lifecycle example

User:

> 我要给客户 API key / service account secret 做 rotation。成功必须证明 old key 和 new key 有受控 overlap window，zero-downtime rotation 不影响现有调用，compromised key 能立即 revoke，revoked key 不能继续调用，key scope / tenant binding 正确，secret 只以 hash 或 KMS encrypted 形式存储，rotation schedule、expiry、last-used telemetry、audit log 记录 key id、actor、scope、tenant、created/rotated/revoked/failed reason；rollback 不能重新启用 revoked key，监控要能发现 rotation failure 和 stale key。只有 UI 显示生成了新 key、env var 改了或 happy path API call 成功必须阻断。

Weak response:

> 我会让 Builder 做生成新 API key 的 UI，Inspector 检查 env var 已改并跑一次 happy path API call，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“UI 显示生成了新 key”“env var 改了”或“一次 happy path API call 成功”当成 API key rotation 完成。成功面应当同时包含 security/key-rotation-lifecycle、privacy/secrets-redaction、permission/auth、regression/monitoring-guard 和 audit/log：old/new key overlap window、zero-downtime rotation、compromised-key revoke、revoked-key 负向调用、scope / tenant binding、hash 或 KMS encrypted storage、rotation schedule、expiry、last-used telemetry、rotation failure / stale-key monitoring、rollback 不重启 revoked key 和 key id / actor / scope / tenant / failed reason audit 都要有证据。推荐 workflow 是 Key Rotation Contract Inspector 先固定 overlap、revoke、scope、tenant、storage、expiry、telemetry、rollback 和 audit 样本；Secret Rotation Builder 实现 rotate/revoke/storage/telemetry/audit；Rotation Evidence Inspector 验证 old/new key calls、revoked-key denial、scope/tenant 负向样本、hash/KMS storage、expiry、last-used telemetry、failure alert、rollback safety 和 audit log；GateKeeper 只有在 key rotation lifecycle、privacy、permission、monitoring、audit 和 new-key-only 反证都进入 Proven 时才通过。你可以选：A. overlap + revoke + scope/tenant + storage 证据优先（推荐）；B. 先做生成新 key 主路径，但把 revoke、storage 和 audit 作为阻断项后补；C. 先做只读 key lifecycle threat model，确认轮换合同后再 Builder。

## Compliance audit trail example

User:

> 我要给管理员敏感操作做 compliance audit trail。成功必须证明 create/update/delete、permission change 和 failed attempt 都写入 append-only audit log，actor、subject、tenant、request id、IP、user agent、before/after diff 和 reason code 完整，PII/token 已脱敏，timestamp 单调且能处理 clock skew，tamper-evident hash chain 或 WORM storage 能证明日志不可改，retention policy 和 legal hold 生效，SIEM/export 对账成功，访问控制和 tenant isolation 防止跨租户看日志，重试不会漏记或重复记，logging failure、stale exporter 和 gap in sequence 有监控告警；只有数据库表里有一行记录、console log 打出来或 UI history 显示一条操作必须阻断。

Weak response:

> 我会让 Builder 给敏感操作写一条 audit_logs 表记录，Inspector 看 console log 和 UI history 有没有显示，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“数据库表里有一行记录”“console log 打出来”或“UI history 显示一条操作”当成 compliance audit trail 完成。成功面应当同时包含 audit/log-integrity-retention、audit/log、permission/auth、access/tenant-isolation、privacy/secrets-redaction、idempotency/duplicate-prevention、regression/monitoring-guard 和 data/export/report：create/update/delete、permission change 和 failed attempt 都要写入 append-only audit log；actor、subject、tenant、request id、IP、user agent、before/after diff 和 reason code 要完整；PII/token 要脱敏；timestamp 要单调并覆盖 clock skew；tamper-evident hash chain 或 WORM storage 要证明不可改；retention policy、legal hold、SIEM/export reconciliation、访问控制、tenant isolation、retry no-miss/no-duplicate、logging failure、stale exporter 和 sequence gap alert 都要有证据。推荐 workflow 是 Audit Contract Inspector 先固定事件矩阵、字段完整性、脱敏、append-only/hash-chain/WORM、retention/legal hold、SIEM/export、租户访问和失败告警样本；Audit Trail Builder 实现写入、完整性保护、脱敏、导出和告警；Audit Evidence Inspector 验证操作/失败样本、篡改负向、clock skew、retention/legal hold、SIEM/export 对账、跨租户访问负向、retry 幂等和 sequence gap alert；GateKeeper 只有在 audit integrity、permission、tenant isolation、privacy、idempotency、monitoring、export reconciliation 和 row/console/UI-history-only 反证都进入 Proven 时才通过。你可以选：A. append-only + tamper evidence + retention/export 证据优先（推荐）；B. 先做 audit log 写入主路径，但把篡改、留存和导出对账作为阻断项后补；C. 先做只读 audit trail 合同和威胁模型，再进入 Builder。

## Password reset token lifecycle example

User:

> 我要做 password reset。成功必须证明 reset token 是一次性且有 expiry，重复点击或 replay 不能改密码，token 只以 hash 存储，密码修改后旧 session / refresh token 全部失效，rate limit 和 enumeration resistance 生效，audit log 记录 request、consume、expired、replay blocked；只有邮件发出或 happy path 重置成功必须阻断。

Weak response:

> 我会让 Builder 发重置邮件，Inspector 检查用户能通过链接改密码，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“邮件发出”或“happy path 重置成功”当成 password reset 完成。成功面应当同时包含 auth/session-token-lifecycle、privacy/secrets-redaction、idempotency/duplicate-prevention、resilience/retry-timeout 和 audit/log：reset token 必须一次性、可过期、不可 replay，存储只能是 hash；密码修改后旧 session / refresh token 要失效；rate limit 和 enumeration resistance 要有正负向证据；request、consume、expired、replay blocked 都要可审计。推荐 workflow 是 Token Contract Inspector 先固定 token 生成、hash、expiry、single-use、replay、session revocation、rate limit、enumeration 和 audit 样本；Auth Builder 实现 reset token 生命周期和 session 失效；Token Lifecycle Inspector 验证重复点击、过期 token、replay、旧 session / refresh token、枚举防护、限流和 audit log；GateKeeper 只有在 token lifecycle、privacy、duplicate prevention、resilience 和 email/happy-path-only 反证都进入 Proven 时才通过。你可以选：A. token lifecycle + replay + session revocation 证据优先（推荐）；B. 先做重置主路径，但把 expiry / replay / session revocation 作为阻断项后补；C. 先做只读 auth threat model 和 token contract 评估，再进入 Builder。

## Data lifecycle deletion example

User:

> 我要做 GDPR account erasure。成功必须证明用户删除后主库、搜索索引、缓存和导出报表里都没有 PII，需要保留的审计 / 账务记录必须匿名化并说明 retention exception，备份或异步清理路径有证据；只有 settings 页面显示 deleted 或用户表软删除必须阻断。

Weak response:

> 我会让 Builder 做账号删除按钮，Inspector 检查 settings 页面显示 deleted，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“settings 页面显示 deleted”或“用户表软删除”当成 account erasure 完成。成功面应当同时包含 data-lifecycle/deletion-retention、privacy/secrets-redaction、audit/log 和 data/export/report：主库、搜索索引、缓存、导出报表都要证明没有 PII；需要保留的审计 / 账务记录必须匿名化并说明 retention exception；备份或异步清理路径要有可复验证据。推荐 workflow 是 Data Map Inspector 先固定 PII 扩散面和留存例外；Deletion Builder 实现删除、匿名化与清理路径；Lifecycle Evidence Inspector 验证主库 / 索引 / 缓存 / 导出 / 备份或异步清理证据；GateKeeper 只有在 deletion-retention、privacy、audit 和 export/report 反证都进入 Proven 时才通过。你可以选：A. PII 扩散面 + retention exception + 异步清理证据优先（推荐）；B. 先实现删除主流程，但把索引 / 缓存 / 备份作为阻断项后补；C. 先做只读数据地图，确认 PII 扩散面后再 Builder。

## Consent preference governance example

User:

> 我要做 GDPR/CCPA consent and preference center。成功必须证明 cookie consent、marketing opt-in、email/SMS/push preferences、tracking purposes 和 third-party vendor consent 都按 region 生效；consent version、policy version、purpose id、legal basis、source、timestamp、IP/user agent 和 withdrawal 都有 immutable audit log；用户 withdraw consent 后 analytics event、marketing campaign、data export 和 vendor sync 都立即停止或更新，double opt-in、unsubscribe、suppression list、DSAR export 和 deletion request 与 consent ledger 对账，未登录用户 cookie consent 能和登录后 account preference merge；监控要发现 consent drift、vendor mismatch、tracking without consent、stale preference cache 和 re-consent required；只有 cookie banner 显示、checkbox 保存成功或 localStorage 有 consent=true 必须阻断。

Weak response:

> 我会让 Builder 做 cookie banner 和 checkbox，Inspector 检查 localStorage 里有 consent=true，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“cookie banner 显示”“checkbox 保存成功”或 `localStorage consent=true` 当成 consent and preference center 完成。成功面应当同时包含 privacy/consent-preference-governance、privacy/secrets-redaction、notification/subscription-deliverability、analytics/event-integrity、external/provider-contract、audit/log、audit/log-integrity-retention、cache/invalidation-consistency 和 data/export/report：cookie、marketing、email/SMS/push、tracking purpose、vendor consent、region rules、version/purpose/legal basis、withdrawal、vendor sync、double opt-in、unsubscribe、suppression、DSAR export、deletion request、account preference merge、audit 和 drift/mismatch/tracking-without-consent alerts 都要有证据。推荐 workflow 是 Consent Contract Inspector 先固定 purposes、region rules、version/legal basis、withdrawal、vendor、marketing/tracking enforcement 和 audit ledger 样本；Preference Governance Builder 实现同意账本、偏好中心、同步、缓存失效和审计；Consent Evidence Inspector 验证 withdrawal 后 analytics/marketing/export/vendor 停止或更新、double opt-in/unsubscribe/suppression 对账、DSAR/deletion 对账、未登录 cookie 与账号偏好 merge、stale cache 和 vendor mismatch 告警；GateKeeper 只有在 consent governance、privacy、subscription deliverability、analytics enforcement、provider sync、audit integrity、cache invalidation 和 banner/checkbox/localStorage-only 反证都进入 Proven 时才通过。你可以选：A. purpose/version + withdrawal + vendor sync 证据优先（推荐）；B. 先做偏好中心主路径，但把 vendor、DSAR 和监控作为阻断项后补；C. 先做只读 consent data-flow 和政策矩阵，再进入 Builder。

## Analytics instrumentation example

User:

> 我要给移动端 onboarding 加 analytics instrumentation 和 A/B experiment exposure。成功必须证明 signup funnel 每一步事件 schema 正确，同一次用户路径不会重复上报，consent 拒绝时不发 PII，实验 assignment / exposure 一致，dashboard 或 warehouse 查询能和真实事件对账；只有按钮可点、console.log 或 mock analytics call 必须阻断。

Weak response:

> 我会让 Builder 给 continue button 加 click log，Inspector 检查按钮可点，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“按钮可点”、`console.log` 或 mock analytics call 当成 instrumentation 完成。成功面应当同时包含 analytics/event-integrity、experiment/assignment-consistency、idempotency/duplicate-prevention 和 privacy/secrets-redaction：signup funnel 每一步事件 schema / payload 要可复验，同一次用户路径不能重复上报，consent 拒绝时不能发 PII，experiment assignment 和 exposure 要一致，dashboard 或 warehouse 查询要能和真实事件对账。推荐 workflow 是 Instrumentation Contract Inspector 先固定事件 schema、实验分桶和 consent 边界；Tracking Builder 实现最小上报路径；Event Integrity Inspector 验证真实事件、去重、consent、warehouse / dashboard 对账和 experiment exposure；GateKeeper 只有在 event integrity、experiment consistency、privacy 和 duplicate-prevention 反证都进入 Proven 时才通过。你可以选：A. 事件 schema + 实验曝光 + 数仓对账证据优先（推荐）；B. 先做上报主路径，但把去重 / consent / dashboard 对账作为阻断项后补；C. 先做只读 instrumentation plan，确认事件合同后再 Builder。

## Async job queue example

User:

> 我要把大报表导出改成 async job queue。成功必须证明点击 export 后 job 被持久化入队，worker 会处理并生成文件，用户能看到 pending / running / succeeded / failed 状态，重试不会生成重复文件，失败会进入 dead-letter queue 或可恢复队列，断线刷新后状态仍能恢复；只有按钮显示 queued 或本地 happy path 生成文件必须阻断。

Weak response:

> 我会让 Builder 给 export 按钮加 queued 状态，Inspector 检查本地能生成文件，GateKeeper 最后判断。

Better response:

> 这条 Loop 不能把“按钮显示 queued”或“本地 happy path 生成文件”当成 async export 完成。成功面应当同时包含 async/job-lifecycle、queue/failure-recovery、idempotency/duplicate-prevention 和 data/export/report：export 后 job 要持久化入队，worker 要消费并生成文件，用户可见 pending / running / succeeded / failed 状态，刷新或断线后状态能恢复，重试不能生成重复文件，失败必须进入 dead-letter queue 或可恢复路径。推荐 workflow 是 Queue Contract Inspector 先固定 job lifecycle、状态模型、重试/死信和文件证据；Export Builder 实现异步导出与 worker 路径；Job Lifecycle Inspector 验证持久化入队、worker 消费、状态恢复、文件 artifact、重试去重和 dead-letter / recovery evidence；GateKeeper 只有在 job lifecycle、failure recovery、idempotency 和 export artifact 都进入 Proven 时才通过。你可以选：A. job lifecycle + worker + failure recovery 证据优先（推荐）；B. 先实现异步主路径，但把重试、刷新恢复和 dead-letter 作为阻断项后补；C. 先做只读队列设计评估，确认状态模型后再 Builder。

## Long-chain multi-Builder example

User:

> 我要让 Agent 大幅重构一个搜索系统，从查询改写、召回、排序到前端证据都要稳，最好拆细一点

Weak response:

> 我会创建很多角色：Builder 1、Builder 2、Builder 3、Inspector 1、Inspector 2、GateKeeper。

Better response:

> 这类任务可能适合长链 workflow，但不是因为“角色越多越稳”，而是因为每个阶段会产生不同证据边界。可以考虑 `Baseline Inspector -> Query Builder -> Retrieval Builder -> Ranking Builder -> Regression Inspector -> Evidence Hardening Builder -> GateKeeper`。Baseline Inspector 先固定当前失败和可重复证据；Query / Retrieval / Ranking Builder 分别只推进一个阶段并留下 handoff；Regression Inspector 读取这些阶段 handoff 和 Builder evidence，指出哪些 Proven / Weak / Unproven / Blocking；Evidence Hardening Builder 读取 Regression Inspector handoff，只补强缺失 proof，不继续扩大功能；GateKeeper 读取关键阶段 handoff 和 evidence 后裁决。这个长链仍然是一个线性 `workflow.steps`，不是嵌套 Loop 或任意分支。先确认一个会改变链条形状的问题：这次最怕哪一类假完成，排序指标看起来提升但召回变差、UI 结果看起来合理但证据不可复验，还是重构后复杂度只是换了地方？

If the user confirms the long-chain need, the agreement should say why each Builder is a phase boundary and why GateKeeper must fan in more than the final Builder:

> 长链成立的理由不是“5+ 角色”，而是查询改写、召回、排序和证据补强各自产生不同 artifact、proof target 和 handoff。后续 Builder 必须读取前序阶段或 review handoff；Regression Inspector 和 GateKeeper 必须查询 Builder / Inspector evidence，不能只看最后一轮自然语言摘要。若某个阶段没有独立证据或交接边界，应合并到相邻 Builder，避免 role zoo。

# Loopora Loop Kernel Refactor 说明书

> Status: Proposal
> Scope: pre-launch architecture reset
> Goal: preserve the core idea of **Human-Shaped Loop**, while rebuilding Loopora on a simpler, stronger internal foundation.

---

## 0. 一句话结论

Loopora 应该从“由多个平台对象共同驱动的系统”，重构为：

```text
一个 Event Core 驱动的 Loop Kernel，多个 Surface / Runner / Extension 只是投影或接入层。
```

对外，用户只需要理解：

```text
Loop → Evidence → Verdict → Next Gap
```

对内，系统只需要坚守：

```text
Command → Domain Event → Projection
```

也就是：

```text
人类判断进入 Loop Contract
Agent 行动产生 Evidence
Evidence 推动 Verdict
Verdict 决定继续、转向、阻断或关闭
所有事实由事件记录，所有界面由投影生成
```

这次重构不是功能收缩，而是底层语义收缩。平台化能力可以保留，但不能继续以 Bundle、Workflow、Role、Agent Native、Headless 等对象作为系统中心。系统中心只能是 **Loop**。

---

## 1. 为什么要大重构

当前 Loopora 已经有正确的思想，但内部结构正在向“平台对象堆叠”发展：

```text
Bundle
Spec
Workflow
Role Definition
Orchestration
Agent Native
Headless
Capsule
Context Packet
Coverage Target
Evidence Ledger
Task Verdict
Web Projection
CLI Projection
Adapter Protocol
```

这些对象各自有存在理由，但它们处在不同抽象层，却被混合进同一个运行逻辑中。结果是：

1. 新手路径暴露了过多平台细节。
2. Agent Native 不只是 Surface，而变成半个 Runtime。
3. Headless 和 Agent Native 有两套推进形态。
4. Bundle / Spec / Workflow 看起来像 Core 对象，而不是 Loop 的输入格式。
5. Context Packet 同时承担 Core 上下文、Agent 输入、Web/CLI 投影三种职责。
6. Runtime Service 逐渐变成历史功能混合体。

项目还没有上线，因此不必背负稳定性包袱。现在应该做一次更彻底的底座重构：

```text
把概念重新排序，把事实源重新定义，把运行模型重新统一。
```

---

## 2. 不变的核心思想

无论怎么重构，Loopora 的思想不能变。

Loopora 的核心不是多 Agent，不是 Prompt Pack，不是工作流编排器，也不是通用任务平台。

Loopora 的核心是：

> **把人类对长任务的判断，提前编译进一个可执行、可证据化、可裁决、可追踪的 Loop。**

Human-Shaped Loop 要保留。Loop 这个词要保留。

Human-Shaped Loop 表达的是：

```text
人不必在每一轮都回来纠偏，
但人的判断必须以结构形式持续影响每一轮。
```

普通长任务容易形成错误增强回路：

```text
目标 → Agent 执行 → 看起来更完整 → Agent 宣布完成
          ↑                         ↓
          └──── 未证明的早期假设被后续工作继续包装
```

Human-Shaped Loop 插入新的控制回路：

```text
Loop Contract → Agent Work → Evidence → Verdict → Next Gap
       ↑                                      ↓
       └──────────── 未证明或阻断风险拉回下一轮
```

核心判断是：

```text
运行结束 ≠ 任务完成
总结可信 ≠ 证据充分
看起来完成 ≠ 可接受完成
```

---

## 3. 对外概念模型

对外概念必须少。高级能力可以存在，但默认不能进入用户心智。

### 3.1 第一层：所有用户必须理解的概念

```text
Loop
Evidence
Verdict
```

解释：

```text
Loop      这次任务如何被持续判断
Evidence  每轮留下什么可复核材料
Verdict   基于证据决定继续、阻断、带风险通过或关闭
```

### 3.2 第二层：Loop 的人类可读内容

一个 Loop 应该被解释为一个任务判断契约，包含：

```text
Task
Done When
Fake Done
Evidence Needed
Blocking Risks
Residual Risk
```

这些不是平台对象，而是 Loop 的判断面。

建议对外称为：

```text
Loop Contract
```

它可以是 UI 中的卡片，也可以是 Markdown，也可以由 Web 对话生成。它不等同于内部 Bundle，也不等同于现在的 Spec。

### 3.3 第三层：高级用户才需要理解的概念

```text
Loop Strategy
Roles
Steps
Evidence Flow
Runner
Loopfile
```

解释：

```text
Loop Strategy  这个 Loop 如何运行
Roles          Builder / Inspector / Guide / GateKeeper 等职责
Steps          角色和动作顺序
Evidence Flow  哪些证据流向哪些判断点
Runner         当前 Agent、Headless worker、CI、未来远程执行器等
Loopfile       Loop 的导入导出格式
```

这里的关键词是 **Strategy**，而不是 Workflow。

Workflow 容易让用户以为 Loopora 是流程编排器；Strategy 更接近“为了控制这个任务的误差，我们选择怎样的执行结构”。

### 3.4 第四层：不应对新手暴露的内部概念

以下概念不删除，但从默认文档、默认 CLI、Agent 第一屏中下沉：

```text
Bundle
Spec
Orchestration
Role Definition
Agent Native
Headless
Capsule
Context Binding
Coverage Target
Submit Repair
Manifest Claim
Projection Cache
```

它们分别改为内部或高级表达：

| 当前概念 | 新定位 | 建议名称 |
|---|---|---|
| Bundle | Loop 的交换格式 | Loopfile |
| Spec | Loop Contract 的一种 source | Contract Source |
| Workflow | Loop Strategy 的一种 source | Strategy Source |
| Orchestration | 高级 Strategy Template | Strategy Template |
| Role Definition | Strategy 内角色模板 | Role Template |
| Agent Native | 当前 Agent 执行入口 | Agent Runner / Agent Surface |
| Headless | 自动执行入口 | Automation Runner |
| Capsule | Agent Surface 的 step 投影 | Agent Step View |
| Coverage Target | Evidence 要证明的目标 | Evidence Target |
| Context Binding | Surface 恢复机制 | Recovery Hint |

---

## 4. 内部重构目标

本次重构选择 **Event Core** 方案。

目标不是引入复杂事件溯源框架，而是建立一个足够小的领域事件核心：

```text
Command 负责表达意图
Event 负责记录事实
Projection 负责服务界面和查询
```

内部核心目标：

```text
1. Loop 是唯一产品主对象。
2. Event Log 是事实源。
3. Run Engine 是唯一推进器。
4. Headless 和 Agent 都只是 Runner。
5. Web、CLI、Agent 输出都只是 Projection。
6. Bundle、Spec、Workflow、Role Definition 都只是 Compiler Source。
7. Evidence、Coverage、Verdict 是纯领域逻辑。
```

---

## 5. 新内部架构总览

建议目标架构：

```text
┌────────────────────────────────────────────┐
│                 Surfaces                   │
│      Web / CLI / Agent / Automation API     │
└─────────────────────┬──────────────────────┘
                      │ Projection / Command
┌─────────────────────▼──────────────────────┐
│                 Runners                     │
│   AgentRunner / HeadlessRunner / CI Runner  │
└─────────────────────┬──────────────────────┘
                      │ claim / submit
┌─────────────────────▼──────────────────────┐
│                Run Engine                   │
│       claim_step / submit_step / advance    │
└─────────────────────┬──────────────────────┘
                      │ emits events
┌─────────────────────▼──────────────────────┐
│                Event Core                   │
│        append-only domain event stream      │
└─────────────────────┬──────────────────────┘
                      │ replay / project
┌─────────────────────▼──────────────────────┐
│              Loop Kernel                    │
│ Contract / Strategy / Evidence / Verdict    │
└─────────────────────▲──────────────────────┘
                      │ compile
┌─────────────────────┴──────────────────────┐
│               Loop Compiler                 │
│  Alignment / Markdown / Loopfile / Template │
└────────────────────────────────────────────┘
```

依赖方向：

```text
Surfaces → Runners → Run Engine → Event Core → Loop Kernel
Compiler → Loop Kernel
Projections ← Event Core
```

禁止反向依赖：

```text
Core 不依赖 Web
Core 不依赖 CLI
Core 不依赖 Agent adapter
Core 不依赖 FastAPI / Typer
Core 不依赖 Bundle YAML
Core 不依赖 Codex / Claude / OpenCode
```

---

## 6. Loop Kernel 的核心对象

Event Core 不是替代领域模型，而是记录领域变化。领域模型仍然必须小。

建议 Core 只保留以下对象。

### 6.1 LoopContract

表示这次任务如何被判断。

```python
@dataclass(frozen=True)
class LoopContract:
    id: str
    task: str
    done_when: list[DoneCriterion]
    guardrails: list[str]
    fake_done: list[str]
    evidence_needed: list[EvidenceExpectation]
    blocking_risks: list[str]
    residual_risk_policy: ResidualRiskPolicy
    evidence_targets: list[EvidenceTarget]
```

它回答：

```text
什么才算完成？
哪些看起来完成但必须失败？
哪些证据可信？
哪些风险阻断关闭？
哪些残余风险可接受，前提是什么？
```

### 6.2 LoopStrategy

表示这个 Loop 如何运行。

```python
@dataclass(frozen=True)
class LoopStrategy:
    id: str
    roles: list[RoleSpec]
    steps: list[StrategyStep]
    evidence_flow: EvidenceFlow
    iteration_policy: IterationPolicy
    finish_policy: FinishPolicy
```

它回答：

```text
谁先做？
谁检查？
谁裁决？
哪些证据流向哪里？
什么时候继续、转向、阻断、关闭？
```

注意：

```text
Workflow 是输入格式。
LoopStrategy 是 Core 对象。
```

### 6.3 LoopDefinition

表示一个可运行的 Loop。

```python
@dataclass(frozen=True)
class LoopDefinition:
    id: str
    name: str
    contract: LoopContract
    strategy: LoopStrategy
    runtime_defaults: RuntimeDefaults
    metadata: LoopMetadata
```

LoopDefinition 是 Compiler 的主要产物。

### 6.4 RunState

表示一次 Loop Run 的生命周期状态。

```python
@dataclass(frozen=True)
class RunState:
    id: str
    loop_id: str
    lifecycle_status: RunLifecycleStatus
    current_iteration: int
    current_step_id: str | None
    pending_actor: ActorRef | None
    stop_requested: bool
```

RunState 不包含 task pass/fail。任务是否完成由 Verdict 判断。

### 6.5 StepInstruction

表示下一步要做什么。

```python
@dataclass(frozen=True)
class StepInstruction:
    run_id: str
    step_id: str
    iteration: int
    role: RoleSpec
    objective: str
    contract_ref: str
    evidence_scope: EvidenceScope
    action_policy: ActionPolicy
    output_contract: StepOutputContract
```

所有执行入口都消费同一个 StepInstruction。

```text
Agent Capsule = StepInstruction 的 Agent 投影
Headless Prompt = StepInstruction 的 Headless 投影
Web Current Step = StepInstruction 的 Web 投影
CLI JSON = StepInstruction 的 CLI 投影
```

### 6.6 StepResult

表示一个 Step 的提交结果。

```python
@dataclass(frozen=True)
class StepResult:
    run_id: str
    step_id: str
    iteration: int
    actor: ActorRef
    status: StepResultStatus
    summary: str
    evidence_claims: list[EvidenceClaim]
    artifact_refs: list[ArtifactRef]
    blocking_items: list[str]
    residual_risks: list[str]
```

StepResult 可以来自 Headless executor，也可以来自当前 Agent，也可以来自未来远程 runner。

### 6.7 EvidenceEntry

表示被系统接受的证据事实。

```python
@dataclass(frozen=True)
class EvidenceEntry:
    id: str
    run_id: str
    source_step_id: str
    actor: ActorRef
    claim: str
    method: str
    result: str
    supports: list[EvidenceTargetRef]
    strength: EvidenceStrength
    artifact_refs: list[ArtifactRef]
    residual_risk: str | None
```

EvidenceEntry 是 append-only。

### 6.8 CoverageState

Coverage 是派生状态，不是事实源。

```python
@dataclass(frozen=True)
class CoverageState:
    run_id: str
    target_states: list[EvidenceTargetState]
    top_gaps: list[EvidenceGap]
```

Coverage 回答：

```text
哪些目标已经证明？
哪些只是弱证据？
哪些未证明？
哪些阻断？
```

### 6.9 Verdict

Verdict 是任务裁决。

```python
@dataclass(frozen=True)
class Verdict:
    run_id: str
    status: VerdictStatus
    source: VerdictSource
    summary: str
    buckets: VerdictBuckets
    next_gap: list[EvidenceGap]
```

状态建议收敛为：

```text
not_evaluated
continue_required
blocked
passed
passed_with_residual_risk
```

如果要兼容现有语义，可映射：

```text
insufficient_evidence → continue_required
failed                → blocked
```

---

## 7. Event Core

### 7.1 Event 不是日志

Event 不是调试日志，也不是 UI activity。

Event 是领域事实：

```text
发生过，并且系统后续判断必须承认它发生过。
```

调试日志、host trace、statusline、todo state、adapter health，不是 Domain Event，除非它们被显式提交并接受为 Evidence。

### 7.2 Event Envelope

所有事件使用统一 Envelope。

```python
@dataclass(frozen=True)
class EventEnvelope:
    event_id: str
    stream_id: str
    aggregate_type: str
    aggregate_id: str
    sequence: int
    event_type: str
    schema_version: int
    occurred_at: datetime
    actor: ActorRef
    correlation_id: str
    causation_id: str | None
    payload: dict
```

建议 stream 设计：

```text
loop:{loop_id}
run:{run_id}
evidence:{run_id}
```

也可以先统一放在 run stream，后续再拆。

### 7.3 Core Event Types

#### Loop events

```text
LoopDraftCreated
LoopContractCompiled
LoopStrategyCompiled
LoopReviewed
LoopActivated
LoopArchived
```

#### Run events

```text
RunCreated
RunStarted
RunPausedForActor
RunResumed
RunStopped
RunFailed
RunClosed
```

#### Step events

```text
StepPlanned
StepClaimed
StepInstructionIssued
StepSubmitted
StepSubmissionRejected
StepAccepted
StepCommitted
```

#### Evidence events

```text
EvidenceSubmitted
EvidenceAccepted
EvidenceRejected
EvidenceLinkedToTarget
CoverageRecomputed
```

#### Verdict events

```text
VerdictRequested
VerdictIssued
VerdictBlockedClosure
VerdictAllowedClosure
ResidualRiskAccepted
```

#### Iteration events

```text
IterationStarted
IterationCompleted
NextGapSelected
StrategyAdvanced
```

### 7.4 Surface events 不进入 Core

这些不是 Core Event：

```text
WebPageOpened
AgentCommandRendered
CliJsonPrinted
HostTraceObserved
TodoUpdated
AdapterCheckPassed
StatuslineRead
```

如果需要记录，可进入 diagnostics stream：

```text
diagnostic:{run_id}
```

但不能驱动 Verdict。

---

## 8. Commands

Command 表示用户或系统想做什么。Command 可以失败，Event 只能记录已发生事实。

核心 Command：

```python
CompileLoop(source) -> LoopCompiled events
ReviewLoop(loop_id, decision) -> LoopReviewed
StartRun(loop_id) -> RunStarted
ClaimStep(run_id, actor) -> StepInstructionIssued
SubmitStep(run_id, submission) -> StepAccepted / StepSubmissionRejected
AppendEvidence(run_id, evidence) -> EvidenceAccepted / EvidenceRejected
RequestVerdict(run_id) -> VerdictIssued
AdvanceRun(run_id) -> StepPlanned / RunClosed / RunPausedForActor
StopRun(run_id) -> RunStopped
```

建议核心服务：

```python
class LoopCompiler:
    def compile(self, source: LoopSource) -> LoopDefinition: ...

class RunEngine:
    def start(self, loop_id: str) -> RunState: ...
    def claim_step(self, run_id: str, actor: ActorRef) -> StepInstruction | RunComplete: ...
    def submit_step(self, run_id: str, submission: StepSubmission) -> SubmitOutcome: ...
    def advance(self, run_id: str) -> AdvanceOutcome: ...

class EvidenceEngine:
    def accept_step_result(self, result: StepResult) -> list[EvidenceEntry]: ...
    def build_coverage(self, contract: LoopContract, evidence: list[EvidenceEntry]) -> CoverageState: ...

class VerdictEngine:
    def judge(self, contract: LoopContract, coverage: CoverageState, gatekeeper_result: StepResult | None) -> Verdict: ...
```

---

## 9. Unified Run Engine

这是内部简化的关键。

### 9.1 现状要避免

不要再让 Agent Native 拥有一套独立推进逻辑。

不要再有：

```text
Headless workflow runtime
Agent Native runtime
Web-owned run runtime
CLI run runtime
```

### 9.2 新模型

只有一个 Run Engine。

不同执行方式只是 Runner。

```text
Run Engine 负责：
- 选择下一步
- 冻结 StepInstruction
- 接受 StepResult
- 写入 Evidence
- 更新 Coverage
- 生成 Verdict
- 决定继续或关闭

Runner 负责：
- 把 StepInstruction 交给某个执行主体
- 把执行结果提交回 Run Engine
```

### 9.3 Runner 类型

```text
AgentRunner       当前宿主 Agent，用户手动或半自动执行
HeadlessRunner    Loopora worker 自动调用 executor
CIRunner          CI / GitHub Actions / future remote runner
HumanRunner       人类手动补 evidence 或 verdict review
```

### 9.4 Headless 变成自动 Runner

```python
while True:
    instruction = engine.claim_step(run_id, actor=HeadlessActor())
    if instruction.complete:
        break
    prompt = headless_projection.render(instruction)
    result = executor.execute(prompt)
    engine.submit_step(run_id, result)
```

### 9.5 Agent Mode 变成外部 Runner

```python
instruction = engine.claim_step(run_id, actor=AgentActor(adapter="codex"))
view = agent_projection.render(instruction)
return view

# later
submission = agent_surface.parse_submission(...)
engine.submit_step(run_id, submission)
```

Agent Mode 不应该知道 workflow runtime 私有类。它不应该 commit workflow step。它只 claim 和 submit。

---

## 10. Compiler Pipeline

内部要明确：Bundle、Spec、Workflow、Role Definition 都不是 Core。

它们都是 Source。

### 10.1 输入来源

```text
Agent task message
Web alignment conversation
Markdown Loop Contract
Loopfile YAML
Strategy template
Existing Loop improvement
```

### 10.2 编译流程

```text
Source
  ↓
LoopDraft
  ↓
LoopContract
  ↓
LoopStrategy
  ↓
LoopDefinition
  ↓
LoopActivated
```

### 10.3 LoopDraft

允许不完整，适合 Web / Agent plan 阶段。

```python
@dataclass
class LoopDraft:
    task_text: str
    judgment_notes: list[str]
    candidate_done_when: list[str]
    candidate_fake_done: list[str]
    candidate_evidence: list[str]
    candidate_strategy_hint: str | None
```

### 10.4 LoopContractCompiler

负责把用户判断编译为契约。

```text
Task → task
Done When → done criteria
Fake Done → fake_done
Evidence Preferences → evidence_needed
Residual Risk → residual risk policy
```

### 10.5 StrategyCompiler

负责生成运行策略。

默认策略：

```text
Builder → Inspector → GateKeeper
```

但内部不应该把默认策略硬编码成产品真理。它只是默认 Strategy。

高级策略可以来自：

```text
Evidence First
Benchmark Gate
Repair Loop
Parallel Review
Custom Strategy
```

这些都编译成同一个 LoopStrategy。

### 10.6 Loopfile

Loopfile 是导入导出格式，不是核心对象。

```text
Loopfile YAML → parse → LoopDraft / LoopDefinition
LoopDefinition → export → Loopfile YAML
```

---

## 11. Projections

Projection 是从 Event Log 派生出来的读模型。

任何 Surface 只能读 Projection，不能把 Projection 当事实源。

### 11.1 核心 Projection

```text
LoopSummaryProjection
RunSnapshotProjection
CurrentStepProjection
EvidenceLedgerProjection
CoverageProjection
TaskVerdictProjection
AuditTimelineProjection
```

### 11.2 Surface Projection

```text
WebRunDetailProjection
AgentStepViewProjection
CliSummaryProjection
HeadlessPromptProjection
LoopfileExportProjection
```

### 11.3 StepInstruction 与 Projection 的关系

```text
StepInstruction 是 Core 对象
Agent Step View 是它的 Agent 投影
Headless Prompt 是它的 Headless 投影
Web Current Step 是它的 Web 投影
```

不再使用一个巨大 Context Packet 同时服务所有场景。

---

## 12. Artifact Store

Event payload 不应该塞大文本、大 prompt、大文件内容。

建议分离：

```text
Event Store     存领域事实和引用
Artifact Store  存 prompt、step view、agent output、reports、screenshots、logs、large JSON
Projection DB   存可重建的读模型缓存
```

ArtifactRef：

```python
@dataclass(frozen=True)
class ArtifactRef:
    kind: str
    label: str
    uri: str
    content_hash: str | None
    created_by_event_id: str
```

规则：

```text
Event 可以引用 Artifact
Artifact 不能独立改变领域状态
Artifact 丢失时，Core 状态仍应可解释，但证据强度可能下降
```

---

## 13. 数据存储建议

因为项目未上线，可以进行破坏性 schema reset。

建议最小 schema：

```sql
create table event_store (
  event_id text primary key,
  stream_id text not null,
  aggregate_type text not null,
  aggregate_id text not null,
  sequence integer not null,
  event_type text not null,
  schema_version integer not null,
  occurred_at text not null,
  actor_json text not null,
  correlation_id text not null,
  causation_id text,
  payload_json text not null,
  unique(stream_id, sequence)
);

create table projection_store (
  projection_name text not null,
  projection_key text not null,
  source_sequence integer not null,
  payload_json text not null,
  updated_at text not null,
  primary key(projection_name, projection_key)
);

create table artifact_index (
  artifact_id text primary key,
  run_id text,
  loop_id text,
  kind text not null,
  uri text not null,
  content_hash text,
  created_by_event_id text,
  created_at text not null
);
```

可以保留兼容 facade，但不需要迁移 v1/v2/v3 本地状态。

建议明确：

```text
pre-launch reset: old local state is disposable
```

如果需要保留历史，可写一次性 importer，而不是把旧 schema 永久带进新架构。

---

## 14. 状态机

### 14.1 Loop 状态

```text
draft
  ↓
ready
  ↓
active
  ↓
archived
```

含义：

```text
draft    还在生成或修改
ready    可运行，Contract 和 Strategy 已审查
active   已有 Run 使用
archived 不再作为默认选择
```

### 14.2 Run lifecycle 状态

```text
created
  ↓
running
  ↓
awaiting_actor
  ↓
evaluating
  ↓
running / awaiting_actor / closed / stopped / failed
```

注意：

```text
closed 只是 run lifecycle 关闭
任务是否 passed 看 Verdict
```

### 14.3 Step 状态

```text
planned
  ↓
claimed
  ↓
submitted
  ↓
accepted / rejected
  ↓
committed
```

### 14.4 Verdict 状态

```text
not_evaluated
continue_required
blocked
passed
passed_with_residual_risk
```

其中：

```text
continue_required 证据不足，需要下一轮
blocked           发现不能继续包装为完成的阻断风险
passed            证据足够，任务可关闭
passed_with_residual_risk 证据足够，但有已命名、已接受、可追踪残余风险
```

---

## 15. Evidence / Coverage / Verdict 纯领域规则

### 15.1 Evidence 是事实输入

Evidence 来自 StepResult，但不是所有 StepResult 都自动成为强证据。

规则：

```text
Agent summary 不是强证据
Host trace 不是强证据
Todo done 不是强证据
Statusline 不是强证据
Approval 不是强证据
只有被提交、接受、关联到 EvidenceTarget 的材料才进入证据层
```

### 15.2 Coverage 是派生状态

```python
coverage = build_coverage(contract, evidence_ledger)
```

Coverage 不能被 Surface 直接写入。

### 15.3 Verdict 是决策结果

```python
verdict = judge(contract, coverage, gatekeeper_result)
```

规则：

```text
required target 未覆盖 → 不能 passed
blocking target 存在 → blocked
残余风险无 owner/follow-up/acceptance path → continue_required 或 blocked
GateKeeper pass 不能覆盖证据缺失
```

### 15.4 Verdict 可以关闭任务，但不能伪造证据

GateKeeper 可以判断，但不能把没有证据的东西变成 Proven。

GateKeeper 输出也是一种判断证据，但必须引用上游 Evidence 或提供直接 measured evidence。

---

## 16. Human-Shaped Loop 在新架构中的位置

Human-Shaped Loop 不是文案层概念，而是架构约束。

它落实为四条机制：

### 16.1 Judgment enters before execution

```text
LoopContract 在 Run start 前冻结。
```

### 16.2 Evidence returns every round

```text
每个 StepResult 必须进入 EvidenceEngine，或明确被拒绝。
```

### 16.3 Verdict changes future action

```text
Verdict 的 next_gap 会影响下一步 StepInstruction。
```

### 16.4 Closure requires proof

```text
Run lifecycle 关闭不代表 task passed。
Task passed 只能来自 Verdict。
```

这四条就是 Human-Shaped Loop 的架构表达。

---

## 17. 目录结构建议

建议目标结构：

```text
src/loopora/
  kernel/
    contract.py
    strategy.py
    run_state.py
    step.py
    evidence.py
    coverage.py
    verdict.py
    policies.py
    errors.py

  events/
    envelope.py
    store.py
    schemas.py
    replay.py
    streams.py

  compiler/
    sources.py
    loop_compiler.py
    contract_compiler.py
    strategy_compiler.py
    semantic_lint.py
    loopfile.py
    markdown_contract.py
    alignment.py

  engine/
    run_engine.py
    step_engine.py
    evidence_engine.py
    verdict_engine.py
    advance_policy.py

  runners/
    base.py
    headless.py
    agent.py
    ci.py

  projections/
    run_snapshot.py
    current_step.py
    evidence_coverage.py
    task_verdict.py
    audit_timeline.py
    web.py
    cli.py
    agent.py

  surfaces/
    web/
    cli/
    agent_commands/

  adapters/
    codex.py
    claude.py
    opencode.py

  storage/
    sqlite_event_store.py
    artifact_store.py
    projection_store.py
```

旧 service mixins 可以先保留在：

```text
legacy/
compat/
```

但新代码不再向旧 mixin 添加逻辑。

---

## 18. 现有概念迁移表

| 当前对象 | 新架构位置 | 说明 |
|---|---|---|
| loop_definitions | LoopDefinition projection / event replay result | 不再是唯一事实源 |
| loop_runs | RunSnapshot projection | lifecycle 从 events 派生 |
| run_events | event_store | 升级为正式 Event Core |
| bundle_definitions | Loopfile import/export projection | 不是 Core |
| orchestration_definitions | Strategy Template source | 高级输入 |
| role_definitions | Role Template source | 高级输入 |
| alignment_sessions | LoopDraftSession projection | 辅助生成 Loop |
| compiled_spec_json | LoopContract | 进入 kernel |
| workflow_json | LoopStrategy | 进入 kernel |
| evidence_ledger | EvidenceAccepted events + projection | append-only |
| evidence_coverage | CoverageProjection | 派生 |
| task_verdict_json | TaskVerdictProjection | 派生，可缓存 |
| Agent Native state | RunState projection + AgentRunner recovery hints | 不再是独立 runtime |
| Capsule | AgentStepView projection | 不再是 Core |
| StepContextPacket | StepInstruction + Surface Projection | 拆分 |

---

## 19. 对外体验在新架构下如何保持简单

虽然内部使用 Event Core，但对外不能讲 Event Core。

### 19.1 README 第一心智

```text
Loopora turns long Agent tasks into Human-Shaped Loops.

A Loop keeps the same human judgment active across rounds:
what counts as done, what evidence is trusted, what fake-done states must fail,
and when the task can honestly close.
```

中文：

```text
Loopora 把长任务变成 Human-Shaped Loop。

一个 Loop 会把人的判断稳定地带过每一轮：
什么才算完成，什么证据可信，哪些假完成必须失败，以及什么时候任务可以诚实关闭。
```

### 19.2 Agent 输出

Agent 中只展示：

```text
Current Loop
Current Step
Evidence Needed
How to Submit
Verdict / Next Gap
Web Link
```

不展示：

```text
Agent Native
capsule
context binding
submit repair schema
coverage target internals
```

### 19.3 Web 输出

Web 展示：

```text
Loop Contract
Run Timeline
Evidence Buckets
Verdict
Next Gap
Advanced Strategy
```

Advanced Strategy 默认折叠。

---

## 20. 重构阶段建议

### Phase 0：语义冻结

先写新的 glossary 和不变量测试。

新增但不替换：

```text
kernel/*
events/*
```

把现有逻辑包装进新 API：

```text
compile_markdown_spec → LoopContract adapter
build_evidence_coverage_projection → CoverageEngine adapter
build_task_verdict → VerdictEngine adapter
```

### Phase 1：Event Store 最小落地

新增 `event_store`，先让新 Run 写核心事件，同时保留旧表兼容。

目标：

```text
每个 run 可以从 event_store replay 出 RunSnapshot
```

### Phase 2：LoopCompiler

把 Bundle / Spec / Workflow / Alignment 都统一编译为：

```text
LoopDefinition = LoopContract + LoopStrategy
```

完成后，Bundle / Spec / Workflow 退出 Core 语义。

### Phase 3：RunEngine

实现统一 API：

```python
start(loop_id)
claim_step(run_id, actor)
submit_step(run_id, submission)
advance(run_id)
snapshot(run_id)
```

先让 Headless 路径使用 RunEngine。

### Phase 4：AgentRunner 重写

Agent Mode 改成 Runner + Projection。

完成后应满足：

```text
Agent surface 不导入 workflow runtime 私有类
Agent surface 不直接 commit step
Agent surface 不维护独立运行状态
```

### Phase 5：拆 Projection

把 StepContextPacket 拆成：

```text
StepInstruction
AgentStepView
HeadlessPrompt
WebRunDetail
CliSummary
```

### Phase 6：清理旧 Runtime

当新路径稳定后，删除或隔离：

```text
service mixin 大混合体
legacy execution path
旧 bundle-as-domain 逻辑
旧 agent-native state machine
```

因为项目未上线，可以不做兼容迁移，只保留必要 importer。

---

## 21. 测试策略

### 21.1 Kernel tests

不依赖 FastAPI、Typer、Codex、Claude、OpenCode。

覆盖：

```text
Contract compile
Strategy compile
Evidence target build
Coverage build
Verdict judge
Residual risk policy
Fake done blocking
```

### 21.2 Event replay tests

验证：

```text
Event stream replay 能重建 RunSnapshot
Evidence projection 可重建
Verdict projection 可重建
重复 replay 幂等
```

### 21.3 Runner parity tests

同一个 StepResult：

```text
HeadlessRunner submit
AgentRunner submit
```

必须产生同样的：

```text
EvidenceEntry
CoverageState
Verdict
NextGap
```

### 21.4 Surface boundary tests

验证：

```text
Web projection 不能改变 Core state
CLI projection 不能改变 Core state
Agent projection 不能改变 Core state
Host trace 不会成为 Evidence
Todo done 不会成为 Evidence
```

### 21.5 Invariant tests

固定不变量：

```text
LoopContract run start 后冻结
Run closed 不等于 Verdict passed
Missing required evidence blocks pass
Blocked evidence target blocks pass
Unmanaged residual risk cannot pass
Surface event cannot affect Verdict
```

---

## 22. 设计禁区

为了防止重构再次复杂化，明确拒绝以下方向。

### 22.1 不做通用 DAG 引擎

LoopStrategy 可以表达步骤和证据流，但 Loopora 的核心不是 DAG。

### 22.2 不做 Role Zoo

角色只有在承担不同证据责任或行动责任时才有价值。

### 22.3 不做 Prompt Pack

Prompt 只是 Surface 输入的一部分，不是产品核心。

### 22.4 不让 Agent Native 成为 Runtime

Agent Mode 是 Runner / Surface，不是第二套运行核心。

### 22.5 不让 Bundle 成为 Domain

Bundle / Loopfile 是交换格式，不是事实源。

### 22.6 不让 Projection 写事实

Projection 只能从 Event 生成，不能反向修改领域状态。

### 22.7 不把 Host Observability 当 Evidence

Host trace、statusline、hook log、todo state、approval 都不是 task proof，除非显式提交并被 EvidenceEngine 接受。

---

## 23. 成功标准

重构完成后，应满足以下判断标准。

```text
1. Loop 是唯一产品主对象。
2. Bundle / Spec / Workflow / Role Definition 都只是 compiler source。
3. Headless 和 Agent 使用同一个 RunEngine。
4. Agent Surface 不再导入 workflow runtime 私有类型。
5. StepInstruction 是唯一下一步核心对象。
6. Capsule / Prompt / Web Card / CLI JSON 都是投影。
7. Evidence / Coverage / Verdict 可以由事件重建。
8. Run lifecycle status 与 task verdict 严格分离。
9. 新增 Runner 不需要改 Loop Kernel。
10. 新增 Surface 不需要改 Run Engine。
11. 新增 Strategy Template 不需要改 Evidence / Verdict 逻辑。
12. Core tests 不依赖任何具体 Agent adapter。
13. 用户默认路径不暴露 Agent Native / Headless / Capsule / Binding 等内部词。
```

---

## 24. 最终架构宣言

Loopora 的新底座应该坚持：

```text
Loop is the product object.
Event is the source of truth.
Evidence is the factual layer.
Verdict is the closure authority.
Surfaces are projections.
Runners are execution adapters.
Strategy is advanced, not mandatory.
```

中文：

```text
Loop 是产品对象。
Event 是事实源。
Evidence 是事实层。
Verdict 是关闭权。
Surface 只是投影。
Runner 只是执行接入。
Strategy 是高级能力，不是使用门槛。
```

这能同时保留两件事：

```text
低门槛：用户只理解 Loop。
高上限：平台可以扩展 Runner、Strategy、Surface、Loopfile、Automation。
```

核心思想不变：

> **Human-Shaped Loop 不是让人消失，而是让人的判断以更好的时间形状进入长期 Agent 任务。**


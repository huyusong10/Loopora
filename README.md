[简体中文](./README.zh-CN.md) | **English**

<p align="center">
  <img src="./src/loopora/assets/logo/logo-with-text-horizontal.svg" alt="Loopora" width="720" />
</p>

<p align="center">
  <a href="https://www.python.org/">
    <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white">
  </a>
  <a href="https://fastapi.tiangolo.com/">
    <img alt="FastAPI" src="https://img.shields.io/badge/web-FastAPI-009688?logo=fastapi&logoColor=white">
  </a>
  <img alt="Agent first" src="https://img.shields.io/badge/agent--first-loop-2563EB">
  <img alt="Local first" src="https://img.shields.io/badge/local--first-evidence-0D7C66">
  <img alt="Status" src="https://img.shields.io/badge/status-experimental-D66A36">
</p>

# Loopora

**Turn `/goal`-style long tasks into Human-shaped Loops with evidence and verdicts.**

In Coding Agents, persistent-goal mechanisms like `/goal` feel natural: give the Agent an objective, it remembers it, keeps pursuing across turns. This works for clear goals, low risk, simple completion judgment—"fix this error," "keep cleaning this module," "get this test suite green."

The hard part of complex tasks isn't just "keep the Agent going." It's judging after each round: did it actually do the right thing? Is evidence sufficient? Is risk acceptable? Should the next round pivot? Can this close now?

**Bare goals keep the task moving, but easily turn results into blind boxes**—the run looks more complete, but early drift, weak evidence, and fake completion get inherited too.

Loopora solves this layer. When a task tends to drift and isn't suited for bare `/goal`, first use `/loopora-plan` to turn the objective, completion criteria, fake-done patterns, evidence requirements, blocking risks, and next-round priorities into a reviewable Loop Bundle. Then use `/loopora-run` to let the Agent execute continuously within that Loop.

Loopora reduces error accumulation, makes each round return to the same judgment, letting long tasks run more steadily and healthily.

To understand the philosophy behind this approach, read [Human-Shaped Loop](./HUMAN-SHAPED-LOOP.md).

<p align="center">
  <img src="./assets/diagrams/loopora-overview.en.svg" alt="Loopora turns human task judgment into a plan file, runs the Agent loop, and shows evidence and verdicts in Web" width="1000" />
</p>

## From `/goal` To Loop

If you would normally write:

```text
/goal build the self-service refund flow until it is ready to ship
```

Loopora suggests splitting into two steps:

```text
/loopora-plan
/loopora-run
```

The difference isn't command length—it's the reviewable judgment structure added before the long run starts.

| With bare `/goal` | With Loopora |
| --- | --- |
| Goal is usually one sentence | Goal gets整理成完成标准、伪完成模式、证据要求和阻断风险 |
| Agent mainly keeps pursuing the objective | Each round carries task judgment, action boundaries, evidence gaps, output requirements |
| Process can look increasingly complete | Each round must report proven, weak evidence, unproven, blocking items, residual risk |
| Closure easily relies on Agent declaring done | Task verdict needs supporting evidence; missing required evidence blocks pass |
| Human needs to repeatedly return to correct drift | Human reviews Loop before run, inspects evidence during run, intervenes at key points |

Loopora doesn't reject `/goal`. It inherits `/goal`'s core intuition: long tasks should keep moving. But for high-risk, multi-round, evidence-sensitive work, before continuing, first define "how will we judge it actually done."

## When Loopora Replaces `/goal`

Loopora doesn't fit every task. It fits tasks where one Agent response looks smooth, but you worry后续会出现伪完成、证据不足或判断漂移.

| Situation | Recommendation |
| --- | --- |
| Goal is small, one Agent pass plus one human review enough | Use Agent or `/goal` directly, no need for Loopora |
| Stable tests, benchmarks, or proof scripts can directly judge | Prefer these硬性反馈 |
| Task needs multi-round execution, each round creates new evidence | Loopora starts adding value |
| Result may look done while core risk remains unproven | Strong fit for Loopora |
| You need to retain, review, reuse, or manage this judgment via Web | Strong fit for Loopora |

Typical examples: self-service refunds, billing permission refactors, cross-service payment callback issues, complex migrations, product tasks needing multi-round exploration while preserving judgment standards.

A simple test: if you expect to return in round 2, 3, or N asking "is evidence sufficient, is risk acceptable, where should next round focus, can this close now"—don't just run a bare goal; compile that judgment into a Loop.

## Quick Start

Currently only source install. You need:

- Python 3.11+
- `uv`
- At least one Coding Agent: Codex, Claude Code, or OpenCode

From Loopora repository root:

```bash
uv tool install --editable .
```

If uv says tool directory not on `PATH`, run once:

```bash
uv tool update-shell
```

Then restart shell.

Next, switch to the project where the Agent will work and install the Loopora entry:

```bash
cd /path/to/your/project
loopora init codex
```

Claude Code and OpenCode also supported:

```bash
loopora init claude
loopora init opencode
```

To only check whether project Agent entry is complete, still Loopora-managed, missing托管协议文件:

```bash
loopora init codex --check
```

`--check` only diagnoses—doesn't install, repair, or overwrite. Use Web for run status and details.

Then return to Agent and use two-stage entries for the current task:

```text
/loopora-plan
/loopora-run
```

For first use, invoke `/loopora-plan` inside your Agent and describe the task plus key judgments:

```text
I need to build a refund request backend:
- page submission is not completion
- must prove admin permission and refund eligibility
- payment failure must be traceable and handoff-ready
- audit trail must reconstruct a refund
```

Loopora优先使用当前 Agent 上下文里已经明确的判断. If key judgment insufficient to determine Loop structure, `/loopora-plan` will先追问一个聚焦问题 or open Web review to align—not替你编造判断. Later, if you want to tighten evidence, repair candidate plan, adjust role responsibilities, or improve Loop from run results, continue using `/loopora-plan`. After preview confirms, run `/loopora-run`—current Agent enters multi-round task under that Loop; intents like "continue," "resume," "patch evidence" also belong to `/loopora-run` stage.

<p align="center">
  <img src="./assets/diagrams/first-run-path.en.svg" alt="Loopora recommends generating and running a Loop inside the Agent while the Web UI observes and manages the evidence" width="1000" />
</p>

## How `/loopora-plan` Plans

`/loopora-plan` doesn't start execution immediately—it enters Loop planning stage: generate, revise, repair, or tighten一份可审查的任务方案. For first-use readers, think of it as Loop's portable form: turns a long objective into judgment structure后续运行绕不开. If run evidence shows evidence rules, verdict conditions, or role responsibilities are wrong, return to `/loopora-plan` or Web review—not让执行阶段偷偷改方案.

The plan must carry本任务的判断, not just task summary. Important task objects, risks, evidence expectations should enter task contract, Agent responsibilities, run flow.

This plan typically contains:

| Artifact | Purpose |
| --- | --- |
| Task contract | Clarifies goal, completion criteria, fake-done patterns, tradeoffs, blocking risks |
| Agent responsibilities | Clarifies what each round should focus on, avoid, deliver, verify |
| Execution strategy | Clarifies what next round should build, prove, repair, narrow, expand, defer |
| Run flow | Clarifies role order, when to inspect, where to return when evidence weak |
| Evidence rules | Clarifies which materials count as strong evidence, which are just self-report or weak |
| Verdict rules | Clarifies when to pass, block, continue, carry explicit residual risk |
| Web preview | Lets you review fit, risks, evidence expectations, responsibilities, closure conditions before run |

<p align="center">
  <img src="./assets/diagrams/plan-judgment-structure.en.svg" alt="A Loopora plan file carries task-local judgment through task contract, Agent responsibilities, execution strategy, run flow, evidence rules, and verdict rules" width="1000" />
</p>

The plan doesn't try to encode all human judgment. It only encodes the part that repeatedly affects this long task: what counts as done, what must be rejected, what evidence is sufficient, which gap comes next, when can task close.

At runtime, Loopora turns these reader-facing pieces into runnable plan: task contract, Agent responsibilities, step order, handoffs, evidence rules stay linked—so Loop can be reviewed before execution and audited after.

## How `/loopora-run` Advances

`/loopora-run` enters Loop run stage: start, continue, resume, or patch evidence gaps. Agent remains main executor: reads code, edits files, runs checks, explains results. Loopora keeps each round tied back to reviewed plan, required evidence, verdict rules—not让任务仅凭聊天记忆或裸目标继续推进. If you ask to change judgment standard during this stage, Agent should stop and route you back to `/loopora-plan` or Web review.

If current Agent session has exact Loopora binding, `/loopora-run` can resume directly. If workdir has recoverable Loopora runs but current Agent session differs or multiple candidates exist, Loopora should surface choices—not guess which to continue. To create fresh Loop rather than reuse old judgment, return to `/loopora-plan` or Web and explicitly choose fresh start.

Common recovery paths follow user intent:

| Situation | What Loopora should do |
| --- | --- |
| Current directory has no Loopora context yet | `/loopora-plan`默认创建新的候选 Loop |
| Current directory already has spec, candidate Loop, run, or evidence | `/loopora-plan`先展示可用来源; you can continue, improve, or explicitly start fresh |
| Work stopped halfway and you return to same Agent session | `/loopora-run`用精确绑定恢复同一个 run,不重新规划 |
| You return from different Agent session or several contexts recoverable | `/loopora-run`展示选择 with `option:<id>` recovery token; you can pick token, pick in Web, or return to `/loopora-plan fresh` |
| Previous run ended but evidence still insufficient | `/loopora-run`基于同一个 Loop启动下一轮,聚焦未证明的缺口 |
| Previous task verdict already passed | `/loopora-run`回放完成状态,不额外创建新 run |
| You explicitly want to recreate bundle | Use fresh path in `/loopora-plan`; old runs and evidence stay history, not current judgment |
| Local Agent binding or context card damaged | `/loopora-run`返回修复提示; run `loopora init <adapter> --check` first, then repair binding or use `/loopora-plan fresh` |
| Local file cleanup fails while deleting or replacing bundle | Record deletion can still complete, but Loopora returns `cleanup_warnings` with path and error to clean manually |

A single run roughly follows:

1. Loopora finds reviewed candidate Loop.
2. Agent executes per current round's goal and boundaries.
3. Agent submits work output, checks, explanations, evidence references.
4. Loopora reconciles: what proven, what weak evidence, what remains unproven.
5. Blocking risk can't be packaged as completion.
6. Insufficient evidence pulls next round back to concrete gap.
7. When task can close, Loopora produces reviewable task verdict and residual-risk summary.

That's the difference between Loopora and ordinary prompt or bare `/goal`: prompt mainly shapes next answer; bare goal mainly keeps Agent moving; Loopora keeps same judgment active across multiple rounds.

## Evidence, Tests, and CI

Loopora doesn't replace tests, CI, or benchmarks.相反, judgments that can be written as tests should first become tests; boundaries that can be proven via proof scripts, schemas, lint, type checks, or real external probes should优先成为强证据.

Loopora handles the layer around that evidence: when evidence is missing, failing, incomplete, or only proves part of the task, the Agent can't package run completion as task completion.

| Evidence Shape | What it means in Loopora |
| --- | --- |
| Tests, CI, benchmarks, proof scripts | Strongest machine evidence for stable contracts |
| Traceable artifacts, logs, screenshots, structured check results | Useful evidence, but must state what it proves |
| Independent checks or human review conclusions | Can help judgment, but not automatically hard proof |
| Agent's own summary | Readable explanation only; cannot support pass by itself |

If stable tests can fully judge the task, Loopora shouldn't make things heavier. Loopora fits long tasks that need tests and also need continuous judgment about evidence gaps, risk priority, and residual risk.

## Autonomy Boundary

Loopora aims to increase trusted autonomy, not unlimited authorization.

- It doesn't acquire new system permissions for Agent; what Agent can do still depends on host tool, workdir, local permissions.
- Loop's action strategy expresses whether current step is read-only, can write, or can issue final ruling.
- Within same run, worktree writes should have clear boundaries; parallel review shouldn't become多人同时修改同一片工作区.
- Task verdict doesn't replace final human approval—it gives human一份可审查的证据摘要、阻断项和残余风险说明.
- Local runs create evidence and artifacts; if task touches sensitive code, logs, or business data, handle per local project's security rules.

This boundary matters: Loopora's goal isn't让 Agent更敢于宣称完成—it's让它在没有证明时更难宣称完成.

## What Web Can Do

Web is the fuller observation and management surface. You can start Loop from Agent, or open Web anytime to inspect and manage. When started from Agent, `/loopora-plan` or `/loopora-run` returns Web link and自动启动或复用本地 Web 服务, CLI output reports status.

Start local Web service manually:

```bash
loopora serve --host 127.0.0.1 --port 8742
```

Open [http://127.0.0.1:8742](http://127.0.0.1:8742).

Web fits these scenarios:

| Scenario | What you can see or do |
| --- | --- |
| Review candidate Loop | Inspect task contract, Agent responsibilities, execution strategy, run flow, evidence rules, verdict rules |
| Observe run | See where Loop执行到何处、最近一轮发生了什么 |
| Inspect evidence | Separate proven, weak evidence, unproven, blockers, residual risk |
| Manage entries | Install or update Codex, Claude Code, OpenCode project entries |
| Adjust plans | Edit candidate plan when needed, or create Loop directly from Web |

Agent entry and Web entry aren't separate worlds. Even if Loop starts inside your Agent, it enters same local records, can be viewed and managed in Web.
# Human-Shaped Loop: Making Long Agent Tasks Run Without Repeated Human Monitoring

[简体中文](./HUMAN-SHAPED-LOOP.zh-CN.md) | **English**

This article explains the engineering thinking behind Loopora. For installation and usage, see [README](./README.md).

---

Loopora starts from a simple desire: not wanting to come back every round to correct drift.

But it's not that simple—either you can't be lazy, or it doesn't work:

- **Run `/goal` and let the Agent keep going**: You only know how far it drifted after it finishes. Tokens spent, result unpredictable, maybe everything needs to be rerun from scratch.
- **Write a massive PRD and let it follow along**: The Agent quickly declares success—the larger the PRD, the more scattered its attention, the less reliable the result. It tends to close tasks fast rather than proving item by item.

And if you don't take the lazy route? You watch every round, manually correct—still not good enough: the Agent fixes A and forgets B, patches B and loses C. Judgment gets scattered across rounds, lost between iterations. The same reminders repeat over and over:

- "Beyond the UI, the backend needs to be complete"
- "Did permissions and audit actually get done?"
- "Tests only cover the main path, what about edge cases?"
- "Patch the failure path"
- "Code is bloated, needs refactoring"

Different failure patterns, same root cause: **judgment has no stable position**. The Agent can't see persistent standards, so output drifts.

Can we turn judgment into structure that applies steady influence at fixed positions? That's Human-shaped Loop.

## 1. Why Long Agent Tasks Easily "Look Complete"

Self-service refund flow—customer admin requests refund from billing page, risky orders route to support. This task looks perfect for an Agent: UI, business rules, tests, edge cases, multi-round work.

User requests:

> Build a self-service refund flow. Make it safe, add tests, iterate until ready to ship.

Round one looks promising: page, form, status messages, mocked eligibility rules, passing main-path tests. The Agent replies:

> Refund flow fully implemented. All goals achieved.

For a demo, this is complete. But for production release?

**No.** Because:

- Permission boundary unverified—didn't prove only authorized admins can request refunds
- Business logic stubbed—eligibility checks use mocked rules, not real paths
- Edge cases uncovered—partial refunds, disputed orders, chargebacks, past-window refunds
- Failure path undesigned—when payment provider fails, what's the ledger state, how does support take over?
- Auditability unproven—can the audit trail let support, finance, compliance reconstruct the process?

Developer asks Agent to continue. Round two looks more product-like: more page states, fuller confirmation, summary mentions "authorization," "eligibility," "audit."

But problems remain: what did this round actually prove? Which risks were resolved versus merely mentioned? Where should next round focus?

Another pattern: Agent fixes A and forgets B, patches B and loses C, or drifts toward easier-to-report work—putting authorization in copy, keeping mocked rules, adding more main-path tests, then saying "security improved." Core risks get hidden behind more product-like surfaces and smoother summaries.

The problem isn't that the Agent isn't diligent. The problem is that correct judgment must be manually applied round by round.

## 2. When Humans Return, They're Asking the Same Few Things

Each human intervention looks different. But abstracted, only a few categories:

**Is this really complete?**
"This is just demo, backend needs to be complete"

**Which evidence is credible?**
"Tests pass, but edge cases?"

**Which risks can't be released?**
"Permissions not proven, can't close"

**Where should next round focus first?**
"Patch failure path first, don't polish UI"

**Can this honestly close now?**
"This risk can carry forward, but someone must own it"

Five categories, different concrete content per task, same shape: pull the Agent from "looks done" back to "actually delivered."

Since the shape is stable, can we extract these before the task starts and turn them into structure later rounds inherit automatically?

That's the core of Human-shaped Loop: **compile these five control signals into effective control points**.

## 3. The Real Problem: Final Feedback Is Too Slow

Why must humans keep returning?

The refund task's real difficulty isn't that the Agent isn't working hard—it's that **final feedback is too slow**.

Real production feedback, incident feedback, business quality feedback often appear long after the task finishes: unauthorized refunds surface during finance reconciliation, missing audit trails during compliance review, payment failure edges after production incidents. By then, early drift has already been reinforced by subsequent work—more pages, more tests, smoother summaries.

This "looks complete, real problems hidden deep" state is the norm for complex tasks.

Use cases, agile iteration, automated tests excel at shortening feedback distance: build a small slice, run a test, know quickly if it's right. They fit fast-feedback systems—change button copy, run test, know immediately.

But refund flows, permission refactors, cross-service payment callbacks are different: automated checks still matter, but they rarely replace final feedback by themselves.

When final feedback is too late, errors cascade, and "looks done" doesn't mean "actually done," tasks need **feedforward governance**—before final feedback arrives, define key risks upfront, construct intermediate feedback points, make these points capable of changing subsequent action direction.

Mature engineering processes have long known this. Design reviews, gates, staged rollouts, audit trails—all exist because final feedback is too slow, so decision-capable checkpoints must be inserted during execution. Loopora doesn't copy organizational processes; it compresses this governance capability into task-local, reviewable, discardable Agent Loops.

## 4. The Essence of Human-shaped Loop

**Human-shaped Loop turns human judgment into execution structure that shapes subsequent loops.**

This structure determines:
- What results will be accepted
- What evidence counts as sufficient
- What risks must be blocked
- Based on current evidence, how the next round turns
- How the task honestly closes

It's not writing more requirements upfront—that's a longer PRD. It's not making the model reflect more rounds—that's stronger self-checking. It's not replacing human judgment—that would detach the loop from human control.

It solves something else: make human judgment unavoidable material for subsequent work, instead of needing humans to keep emphasizing.

So Human-shaped Loop doesn't focus on "will the model work harder"—it focuses on "can human judgment be previewed, executed, evidenced, traced, and ruled upon."

## 5. What Loopora Does: Place Judgment Points That Change Action Upfront

Loopora doesn't wait for final failure to correct. Before the task starts, it places key risks, evidence standards, and closure rules into the loop.

Concretely:

**Before run: Compile judgment**
- Human describes task and key judgments
- Loopora extracts completion standards, fake-done patterns, evidence requirements, blocking risks
- Compiles into a reviewable Loop plan
- Human confirms, Loop stays stable

**During execution: Evidence-driven**
- Agent executes within Loop structure
- Each round's result is organized into evidence buckets: proven, weak evidence, unproven, blocking risk
- Evidence gaps automatically pull next round

**At closure: Honest ruling**
- Results clearly separate: what's proven, what's uncovered, what blocks closure
- Residual risks visible, named, owned
- System can finish running while task remains unproven—the two stay separate

For the refund task, Loop turns judgment into:

- Page submission is not completion
- Authorization, eligibility, payment failure, audit must have evidence
- Unauthorized refunds, missing audit trails must block
- Rare payment-provider edges can be residual risk, but must be visible, owned

Agent finishes round one—it can't just report "I finished." It must return to explicit criteria:

- What did this round prove?
- Evidence for authorized-admin path?
- Is refund eligibility real business path or still mocked?

Results organized into evidence buckets:

| Evidence Bucket | This Round's Reality |
| --- | --- |
| Proven | Page can submit, main-path tests pass |
| Weak evidence | Refund eligibility still from mocked rules |
| Unproven | Authorized-admin path, payment failure handling, audit trail |
| Blocking risk | Unauthorized refund path not proven safe, can't close |

Evidence insufficient—next round doesn't freely explore, but gets pulled back to key gaps.

## 6. When Is a Checkpoint Actually Useful

Control points themselves don't produce control capability.

A review, milestone, ruling point—if it only records status, it's just a checklist. Only when it can make the next round stop, change direction, or supply evidence does it have real control power.

Effective control points must satisfy three things:

**It measures key risks**—not vague "code quality," but "which fake completion pattern does this task fear most"

**It triggers real decisions**—not marking "needs attention," but blocking, redirecting, or closing

**It changes subsequent action direction**—where next round's attention goes, whether code writing can continue, whether evidence must be supplied first

In Loopora, "resource allocation" isn't human budget, but subsequent execution resources:

- Which gap next round's attention focuses on
- Whether workspace writes can continue, or read-only inspection is needed
- Whether evidence must be supplied before continuing
- Whether closure is blocked, exposing residual risk

Points that only measure, don't decide, don't redirect—those are recording rituals, not effective control points.

## 7. Why PRD, Tests, Use Cases, and Fixed Templates Don't Solve This

The previous analysis naturally raises a question: if we write finer PRDs and design fuller tests upfront, can the Agent just follow along?

Of course we should do that. Upfront clarification, detailed PRD, complete test plan—all significantly improve round-one quality.

But they improve opening quality, not judgment callbacks during execution.

In the real world, even the strongest engineering team can't foresee all problems upfront. Design docs state intent; execution generates new facts. Once multi-round execution begins, each round raises new questions:
- What code and flow did it actually change?
- Which hard parts did it bypass?
- Are new tests proving core risks, or only proving paths that are easier to pass?
- Did the summary turn "unproven" into "completed"?

These questions only appear after execution, can't be exhausted at design stage.

**PRD or prompt answers "what to do." Human-shaped Loop answers "is it proven, should it turn, can it close." Different layers.**

| PRD / prompt | Human-shaped Loop |
| --- | --- |
| Describes goals and constraints known before task starts | Turns judgment into control structure that keeps acting during execution |
| Reminds Agent what to care about | Requires each round to respond with evidence |
| Improves round-one quality | Controls error propagation across rounds |
| May be selectively quoted or locally satisfied | Records gaps, blockers, and residual risk |
| Only guidance, no hard constraint | No proof means no closure |

Judgments that can be written as tests, type checks, lint, proof scripts should be written first whenever possible. These are hard evidence, machine-adjudicable.

But some judgments can't be externalized or quantified as concrete metrics. For example:
- "Code is bloated, needs refactoring"—this is complexity perception, not testable
- "This plan is drifting toward easier-to-report work instead of touching the real hard part"—this is execution-direction judgment, needs human ruling
- "This risk can carry forward, but must be visible and owned"—this is residual-risk strategy, depends on team commitments and business environment

These judgments need to become structure, constraining subsequent action and final evaluation.

**Fixed team templates have similar limitations.**

PM Agent → Architect Agent → Engineer Agent → QA Agent is a specific form of Loop. It fits scenarios where task type, failure mode, and deliverables are all stable. For other scenarios:

- **Light tasks**: Fix button copy, extract a small function—wrapping PM, Architect, QA process is overkill, slows work
- **Heavy tasks**: Refund flow, data migration—fixed role names won't automatically know which fake-completion pattern this task fears most. "QA" might only check that the page works, tests pass, copy is complete, while missing authorization paths, refund eligibility, and audit trails

The essence of a fixed team template is that it presets role division and handoff order. It answers "who first, who next, who reviews whom." But it doesn't answer:
- What's the completion standard for this task?
- What evidence counts as sufficient?
- Which gap should pull the next round?
- When can the task honestly close?

These answers change with the task. Fixed templates can't adapt.

One sentence: fixed team templates are one form of Loopora, not the essence. Loopora's full capability is dynamically generating judgment structure per task—light tasks get light process, heavy tasks get heavy evidence.

## 8. When Loopora Is Worth Using

Loopora doesn't fit every complex task. The deciding factor isn't complexity—it's whether **final feedback is too slow, requiring intermediate judgment points during execution.**

Use cases, agile iteration, automated tests fit systems where feedback can be compressed enough: build a small slice, run a test, know immediately if it's right. Change button copy, fix a clear-stacktrace bug, extract a well-bounded function—these don't need Loop.

But refund flows, billing permissions, cross-service payment callbacks, data migrations are different. Real production feedback, incident feedback, business quality feedback often appears long after the task finishes. During that time, "looks done" gets continuously reinforced—more pages, more tests, smoother summaries—but core risks might never have been proven.

Common characteristics of these tasks:
- Final feedback too late, errors cascade
- "Looks done" doesn't mean "actually done"
- Evidence needs to accumulate and be traceable across rounds
- High rollback cost once risks surface

Engineering process has cost, but these tasks are worth it. Judgment sequence:

| Gate | If leaning "yes" | If leaning "no" |
| --- | --- | --- |
| Is one Agent pass plus one human review enough? | Doing it directly is cheaper | Keep judging |
| Is final feedback fast enough? | Use cases or direct Agent fit better | Keep judging |
| Can later rounds produce new evidence or intermediate rulings? | Keep judging | No need for Loop |
| Can the judgment stabilize into automatic checks? | Prefer tests first | Keep judging |
| Is there fake completion risk? | Loopora is more worthwhile | Simple loop might be enough |

Examples:
- **Usually not needed**: Generate campaign themes, fix bug with clear stacktrace, extract well-bounded function
- **Better fit**: Self-service refunds, billing permission refactor, cross-service payment callback issues

Key difference: whether humans need to repeatedly return after key rounds to judge evidence, risk, direction, and closure.

## 9. Can Stronger Models Solve the Judgment Problem?

Models should learn general capabilities: language, code, planning, tool use, reasoning patterns, broad aesthetics. These should transfer across users and tasks.

Stronger models of course make many things simpler—like more senior engineers, they can spot more risks upfront, write better first plans, make fewer basic mistakes.

But nobody cancels code review, tests, release gates, audit trails, or incident retrospectives just because the engineer is senior. This isn't distrust of individual ability—delivery judgment never lives only inside personal capability. Which risks are acceptable, what evidence counts as sufficient, when residual risk can ship—all depend on specific task, team commitments, and business environment, and must be explicitly exposed for debate.

That's why judgment in one task should usually be treated as local, temporary, debatable:

- This refund flow must be conservative, doesn't mean every product task must be
- This prototype can accept rough visuals, doesn't mean all prototypes can
- This benchmark is credible, doesn't mean all benchmarks are
- Accepting this residual risk now, doesn't mean it's a long-term preference

These judgments should be explicit, previewable, editable, disposable. They fit better in the Loop layer outside the Agent, not silently baked into model weights or long-term memory.

> Models learn general capability. Loops learn how this task should be judged.

## 10. Conclusion: Less Human Return, Not Human Disappearance

Future AI-human collaboration won't evolve only along the "smarter models" line.

Models will keep getting stronger, but complex tasks still need human judgment: what's worth doing, what counts as real completion, is evidence credible, is risk acceptable, when to continue, stop, or pivot.

This philosophy didn't spring from abstract AI theory. It's closer to learning from engineering management practices that proved useful: reviews, gates, evidence, traces, retrospectives, and a healthy distrust of "looks done." Loopora doesn't copy organizational process—it compresses these constraints into Agent-executable task structure.

Higher collaboration isn't pulling humans back into every step, nor pretending humans can fully leave. It's letting human judgment participate in a better temporal shape.

Human-in-the-loop puts humans inside execution.

Human-shaped Loop puts human judgment into prior loop structure.

**Loopora wants to raise not Agent freedom, but trusted autonomy. Autonomy isn't running without constraint—it's continuing within human judgment structure.**

When judgment, evidence, redirect, and closure are all externalized, humans can truly intervene less often. That's Loopora's version of laziness: not sacrificing quality to save effort, but raising trusted autonomy so the same judgment doesn't need to be repeated by hand.

This is Human-shaped Loop.

For installation and running Loopora, return to [README](./README.md). This article explains why this layer exists; README explains how to use it.
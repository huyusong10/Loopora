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

But refund flows, permission refactors, cross-service payment callbacks are different: automated checks still matter, but they rarely replace final feedback by themselves. When final feedback is too slow, errors cascade, and "looks done" doesn't mean "actually done," tasks need **feedforward governance**—before final feedback arrives, define key risks upfront, construct intermediate feedback points, make these points capable of changing subsequent action direction.

Mature engineering processes have long known this. Design reviews, gates, staged rollouts, audit trails—all exist because final feedback is too slow, so decision-capable checkpoints must be inserted during execution. Loopora doesn't copy organizational processes; it compresses this governance capability into task-local, reviewable, discardable Agent Loops.

## 4. What Loopora Does: Place Judgment Points That Change Action Upfront

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

## 5. When Is a Checkpoint Actually Useful

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

## 6. Relationship with PRD, Tests, Use Cases, Fixed Team Templates

**PRD and prompt**
Answer "what to do." Human-shaped Loop answers "is it proven, should it turn, can it close." Different layers.

PRD reminds Agent what to care about, but may be selectively quoted. Loop requires each round to respond with evidence.

**Tests and automated checks**
Judgments that can be written as tests, type checks, lint, proof scripts should be written first. These are hard evidence, machine-adjudicable.

Loopora handles the layer around that evidence: when evidence is missing, failing, or incomplete, the Agent can't package run completion as task completion.

**Use cases and agile**
Fit fast-feedback systems: build small slice, know immediately if it's right.

Loopora fits slow-feedback systems: final feedback too late, errors cascade, "looks done" doesn't mean "actually done."

**Fixed team templates**
PM Agent → Architect Agent → Engineer Agent → QA Agent is a specific form of Loop.

It answers "who first, who next, who reviews whom," but doesn't answer:
- What's the completion standard for this task?
- What evidence counts as sufficient?
- Which gap should pull the next round?

These answers change with the task. Fixed templates can't adapt.

One sentence: fixed team templates are one form of Loopora, not the essence.

## 7. When Loopora Is Worth Using

Loopora doesn't fit every complex task. The deciding factor isn't complexity—it's whether **final feedback is too slow, requiring intermediate judgment points during execution.**

Judgment sequence:

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

## 8. Can Stronger Models Solve the Judgment Problem?

Stronger models of course make many things simpler—like more senior engineers, they can spot more risks upfront, write better first plans.

But nobody cancels code review, tests, release gates, or audit trails just because the engineer is senior. This isn't distrust of individual ability—delivery judgment never lives only inside personal capability. Which risks are acceptable, what evidence counts as sufficient, when residual risk can ship—all depend on specific task, team commitments, and business environment, and must be explicitly exposed for debate.

That's why task judgment should be local, temporary, debatable:

- This refund flow must be conservative, doesn't mean every product task must be
- Accepting this residual risk now, doesn't mean it's a long-term preference

These judgments should be explicit, previewable, editable, disposable. They fit better in the Loop layer outside the Agent, not silently baked into model weights.

> Models learn general capability. Loops learn how this task should be judged.

## 9. Conclusion: Less Human Return, Not Human Disappearance

Future AI-human collaboration won't evolve only along the "smarter models" line.

Models will keep getting stronger, but complex tasks still need human judgment: what's worth doing, what counts as real completion, is evidence credible, is risk acceptable, when to continue, stop, or pivot.

This philosophy isn't from abstract AI theory. It's closer to learning from engineering management practices that proved useful: reviews, gates, evidence, traces, retrospectives, and a healthy distrust of "looks done."

Higher collaboration isn't pulling humans back into every step, nor pretending humans can fully leave. It's letting human judgment participate in a better temporal shape.

Human-in-the-loop puts humans inside execution.

Human-shaped Loop puts human judgment into prior loop structure.

**Loopora wants to raise not Agent freedom, but trusted autonomy. Autonomy isn't running without constraint—it's continuing within human judgment structure.**

When judgment, evidence, redirect, and closure are all externalized, humans can truly intervene less often. That's Loopora's version of laziness: not sacrificing quality to save effort, but raising trusted autonomy so the same judgment doesn't need to be repeated by hand.

This is Human-shaped Loop.

For installation and running Loopora, return to [README](./README.md).
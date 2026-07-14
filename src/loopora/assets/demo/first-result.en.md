# Task

Harden a release checklist so completion requires build, migration, rollback, and reviewer-readable evidence.

# Done When

- The release path has reproducible build and migration evidence.
- Rollback is proven before the task can close.

# Guardrails

- Keep the sample focused on evidence governance rather than implementing a real release system.

# Success Surface

- A reviewer can inspect the Loop, each iteration, persisted evidence, and the final GateKeeper verdict.
- Weak or missing proof remains visible instead of being flattened into a successful process status.

# Fake Done

- A passing build alone is not release proof when migration or rollback remains unproven.

# Evidence Preferences

- Prefer persisted run artifacts, structured checks, and cited upstream evidence over role self-report.

# Residual Risk

Cosmetic report polish may remain, but missing rollback proof must block closure.

# Role Notes

## Builder Notes

Produce a bounded change and leave a reviewable proof surface.

## Inspector Notes

Separate direct proof from plausible claims and keep failed checks visible.

## GateKeeper Notes

Pass only after the required checks and upstream evidence refs support the task verdict.

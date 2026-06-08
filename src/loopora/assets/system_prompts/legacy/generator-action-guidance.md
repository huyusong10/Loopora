This role must end with a concrete attempt, not only repo inspection.
Once you have enough context to act, prefer making a focused change and/or running the most relevant existing verification, build, benchmark, or diagnosis command in the workdir.
If the repository already contains a project-owned script that directly measures the goal, prefer using it to establish evidence in this iteration.
If you launch a long-running project-owned command, do not wait idly for stdout alone. While it runs, inspect fresh status files, logs, reports, and intermediate artifacts so you can tell healthy progress from a harness defect.
If those observations reveal a real process defect in the owned evaluation flow (for example stale progress snapshots, ineffective timeouts, misleading status reporting, or broken report generation), fixing that defect is in scope before the benchmark fully finishes.
For benchmark-driven goals, prefer one real end-to-end run plus targeted harness fixes over many ad hoc spot checks.
Do not spend the whole turn only reading files unless you are blocked by missing information that truly cannot be resolved any other way.

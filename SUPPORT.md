# Loopora Support

Loopora is experimental local-first software.
Support is best-effort with no guaranteed response time.
It follows the current development line plus release tags maintainers explicitly
mark as supported in [SECURITY.md](./SECURITY.md).

## Start Here

Use this page as the safe public reporting route.
It separates commands you run locally from material that is safe to paste in a
public issue.

**Terminal route**

- Run `loopora support` when you need the safe public reporting route from the
  terminal.
- It prints the redacted doctor command, issue-routing guidance, and
  private-reporting boundary without running diagnostics or changing files.
- Use `loopora support --workdir "$PWD" --public-issue-bundle` when you need one
  pasteable public issue bundle; this explicit mode runs only redacted public
  diagnostics for the supplied target.
- Use `loopora support --language zh` when you want human guidance in Chinese.
- Structured JSON keeps stable route kinds, command fields, and command execution blockers.

**Web route**

- In Web, open Support from top navigation or go to `/support`.
- When the page has a target project, copy the current public issue support
  bundle from that page; rendering the page does not run diagnostics.
- If you are already in Same-Agent Setup, the same "Support and safe reporting"
  panel is embedded there, and you should choose and refresh the target project
  before copying the public issue support bundle.

## Quick Decision

**Need readiness help?**
Run `loopora doctor --workdir "$PWD"` locally.
Use doctor output when you need readiness and recovery details.

**Need package/source identity?**
Use `loopora --version` for a compact package/source identity.
Use `loopora version --json` when tooling needs that identity as structured data.

**Need a public readiness report?**
For a public issue from a target project, prefer:

```sh
loopora support --workdir "$PWD" --public-issue-bundle
```

Bare `loopora support` marks the report command preview-only and prints a
target-project `loopora support --workdir "$PWD"` rerun command before the
public issue bundle or redacted report command becomes ready.
If a supplied target is missing or not a directory, the report command can still
produce redacted evidence while setup remains not ready.

If the issue involves a custom Web host or port, pass the same `--web-host` /
`--web-port` flags to support before copying the public issue bundle or public doctor command, or
opening the matching local Web Support page. That local Web Support URL can
include the target project context, so keep it local-only and paste the
redacted doctor output instead.
From a source checkout before install, run the preferred bundle directly while
your shell is in the Loopora checkout:

```sh
uv run loopora support --workdir <project-dir> --public-issue-bundle
```

After changing into the target project, keep the source checkout anchored:

```sh
uv --directory <Loopora checkout> run loopora support --workdir "$PWD" --public-issue-bundle
```

Use the underlying `doctor --public-json` report only when maintainers request
lower-level readiness evidence.

## Public Diagnostic Material Allowlist

Prefer pasting the public issue support bundle when readiness or environment
evidence matters. It includes compact package/source identity, a human-readable
readiness summary, and the underlying redacted doctor report JSON. Paste the
underlying public doctor or version output only when a template or maintainer
asks for that lower-level evidence.

Paste only:

- `loopora support --workdir "$PWD" --public-issue-bundle` output, including its human-readable readiness summary and redacted doctor JSON.
- `doctor --public-json` output when the underlying readiness report is requested.
- `loopora --version` output when compact identity is requested.
- `loopora version --json` output when structured identity is requested.

Keep local only:

- `loopora support --json`.
- Printed command lines.
- JSON command fields.
- Local Web Support URLs printed by support.

Run support commands locally.
In public issues, paste the public issue support bundle first when applicable,
or the requested redacted report/version output, not command lines that include
local checkout or project paths.
Treat `loopora support --json` as route metadata, not as a public issue attachment.
Its command fields may include local checkout or project paths.

## What To Include

- Loopora version or source revision/dirty state, usually from the public issue
  support bundle or a requested version output.
- Human-readable readiness summary from the public issue support bundle when
  setup, Web, same-Agent entry, or first-task handoff status matters.
- Operating system, Python version, and Agent host when relevant. The public
  issue support bundle normally covers OS and Python.
- Affected surface such as CLI, Web, Agent adapter files, `.loopora/`, run
  artifacts, evidence records, package contents, public docs, or diagnostics.
- Report scope, impact/workaround, and public readiness report status for bugs.
- Loopora fit, non-goals, adoption impact, success criteria, evidence, and
  compatibility risk for proposals.

Remove credentials, tokens, provider transcripts, private logs, local paths,
local command lines, and sensitive workspace data before posting publicly.
Also remove command lines that include checkout or project paths, plus run
artifacts or evidence records that expose private project details.

## Where To Go

**Reproducible defects**

Use the [GitHub Bug Report template][bug-report].
Include the report scope, impact/workaround, and public readiness report status.

**Product proposals**

Use the [GitHub Feature Request template][feature-request].
Explain Loopora fit, non-goals, adoption impact, success criteria, evidence, and
compatibility risk.
If the proposal depends on first-use, Web, readiness, package identity, or
environment behavior, include the public readiness report status and paste the
public issue support bundle first. Use the underlying `doctor --public-json`
output only when lower-level readiness evidence is requested; do not paste the
command line.

**Security vulnerabilities**

Start with [SECURITY.md](./SECURITY.md), then use
[GitHub private vulnerability reporting][private-security-report]
when available.
If the private channel is unavailable, a public issue only asking for a private reporting channel is the fallback.
Include no exploit details or sensitive data.

**Usage or setup questions**

Start with the README fit guidance and doctor output.
If the question exposes a reproducible setup blocker, file a bug report.
If it asks for new behavior, file a feature request.

## Scope

In scope:

- Loopora CLI/Web behavior.
- Managed Agent entry files.
- Local `.loopora/` state.
- Run artifacts and evidence records.
- Package contents, public docs, and diagnostics.

Out of scope:

- Third-party Agent host, provider CLI, browser, or operating system issues
  unless Loopora makes the issue worse.
- Debugging private projects or credentials in public.
- Unsupported local state migrations.
- Live incident response for deployments outside this repository.

[bug-report]: https://github.com/huyusong10/Loopora/issues/new?template=bug_report.yml
[feature-request]: https://github.com/huyusong10/Loopora/issues/new?template=feature_request.yml
[private-security-report]: https://github.com/huyusong10/Loopora/security/advisories/new

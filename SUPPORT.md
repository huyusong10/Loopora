# Support

Loopora is experimental local-first software. Support is best-effort and does not guarantee a response time.

## Questions and Bug Reports

Search existing GitHub issues first, then use the repository issue forms. Include the smallest reproducible example and describe expected versus actual behavior.

When environment evidence is relevant, the public diagnostic allowlist is:

```bash
loopora doctor --public-json --workdir "$PWD"
loopora --version
```

Review the output before posting it. Replace private project names or paths with placeholders if they are not already redacted.

Do not post:

- Web auth tokens, credentials, environment secrets, or session identifiers;
- private logs, prompts, model transcripts, evidence archives, or recovery archives;
- local command history, private repository contents, or absolute sensitive paths;
- unreviewed private Doctor output or raw App database files.

If the installed command is broken, run the same public Doctor command from a source checkout with `uv run loopora doctor ...`, then report that the fallback was used. Do not publish the checkout path.

## Security Issues

Follow [SECURITY.md](SECURITY.md). Use GitHub private vulnerability reporting when available:

<https://github.com/huyusong10/Loopora/security/advisories/new>

If private reporting is unavailable, open a public issue asking only for a private contact channel. Do not include exploit details or secrets.

## Scope

Useful reports identify the affected CLI, Web, Agent adapter, local state, run artifact, evidence, or distribution boundary. Third-party Agent hosts and provider CLIs remain owned by their projects unless Loopora makes the issue worse.

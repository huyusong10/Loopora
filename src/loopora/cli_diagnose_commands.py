from __future__ import annotations

import json
from typing import Annotated

import typer

from loopora.cli_common import get_service
from loopora.event_redaction_audit import audit_event_redaction

FixOption = Annotated[
    bool,
    typer.Option(
        "--fix",
        help="Rewrite DB and local event files that current redaction rules can safely repair.",
    ),
]


def register_diagnose_commands(app: typer.Typer) -> None:
    @app.command("event-redaction")
    def diagnose_event_redaction(
        *,
        fix: FixOption = False,
    ) -> None:
        service = get_service()
        report = audit_event_redaction(service.repository, fix=fix)
        typer.echo(json.dumps(report, ensure_ascii=False, indent=2))

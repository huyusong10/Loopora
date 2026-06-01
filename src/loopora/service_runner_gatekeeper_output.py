from __future__ import annotations

from loopora.runner_gatekeeper_output_validation import coerce_gatekeeper_output


class ServiceRunnerGatekeeperOutputMixin:
    def _coerce_gatekeeper_output(
        self,
        output: dict,
        *,
        evidence_context: dict | None = None,
        current_evidence_id: str = "",
        compiled_spec: dict | None = None,
    ) -> dict:
        return coerce_gatekeeper_output(
            output,
            evidence_context=evidence_context,
            current_evidence_id=current_evidence_id,
            compiled_spec=compiled_spec,
        )

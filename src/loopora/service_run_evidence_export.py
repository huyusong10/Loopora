from __future__ import annotations

from loopora.run_evidence_package import RunEvidencePackage, build_run_evidence_package


class ServiceRunEvidenceExportMixin:
    def build_run_evidence_package(self, run_id: str) -> RunEvidencePackage:
        return build_run_evidence_package(self.get_run(run_id))

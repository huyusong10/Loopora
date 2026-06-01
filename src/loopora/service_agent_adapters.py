from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_adapters import (
    agent_adapter_status,
    check_agent_adapter,
    install_agent_adapter,
    list_agent_adapter_statuses,
    uninstall_agent_adapter,
)
from loopora.agent_entry_run_projection import (
    agent_entry_loop_command as agent_entry_loop_command,
)
from loopora.service_agent_bundle_candidates import (
    AgentBundleCandidateRequest as AgentBundleCandidateRequest,
    ServiceAgentBundleCandidateMixin,
)
from loopora.service_agent_continuation import ServiceAgentContinuationMixin
from loopora.service_agent_entry_projection import ServiceAgentEntryProjectionMixin
from loopora.service_agent_loop_start import ServiceAgentLoopStartMixin


class ServiceAgentAdapterMixin(
    ServiceAgentLoopStartMixin,
    ServiceAgentContinuationMixin,
    ServiceAgentBundleCandidateMixin,
    ServiceAgentEntryProjectionMixin,
):
    def list_agent_adapters(self, *, workdir: Path | str | None = None) -> list[dict[str, Any]]:
        return list_agent_adapter_statuses(workdir or Path.cwd())

    def get_agent_adapter(self, adapter: str, *, workdir: Path | str | None = None) -> dict[str, Any]:
        return agent_adapter_status(adapter, workdir or Path.cwd())

    def check_agent_adapter(self, adapter: str, *, workdir: Path | str | None = None) -> dict[str, Any]:
        return check_agent_adapter(adapter, workdir or Path.cwd())

    def install_agent_adapter(self, adapter: str, *, workdir: Path | str | None = None) -> dict[str, Any]:
        return install_agent_adapter(adapter, workdir or Path.cwd())

    def uninstall_agent_adapter(self, adapter: str, *, workdir: Path | str | None = None) -> dict[str, Any]:
        return uninstall_agent_adapter(adapter, workdir or Path.cwd())

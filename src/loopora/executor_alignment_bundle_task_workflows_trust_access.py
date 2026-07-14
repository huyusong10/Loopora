from __future__ import annotations

"""Compatibility facade for trust access workflow bodies."""

from loopora.executor_alignment_bundle_task_workflows_trust_access_authorization import (
    _replace_authorization_policy_task_workflow as _replace_authorization_policy_task_workflow,
)
from loopora.executor_alignment_bundle_task_workflows_trust_access_breakglass import (
    _replace_support_impersonation_task_workflow as _replace_support_impersonation_task_workflow,
)
from loopora.executor_alignment_bundle_task_workflows_trust_access_identity import (
    _replace_auth_session_token_lifecycle_task_workflow as _replace_auth_session_token_lifecycle_task_workflow,
    _replace_identity_sso_task_workflow as _replace_identity_sso_task_workflow,
)

__all__ = (
    "_replace_auth_session_token_lifecycle_task_workflow",
    "_replace_authorization_policy_task_workflow",
    "_replace_identity_sso_task_workflow",
    "_replace_support_impersonation_task_workflow",
)

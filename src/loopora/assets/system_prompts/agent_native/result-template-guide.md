# Loopora Result Template Guide

In the main Agent/Orchestrator session, open the result template from `next_step.submit_hint.result_template_absolute_path` or `next_step.submit_hint.result_template_path`. Do not hand-write the wrapper from memory.

The template has three top-level blocks:

```json
{
  "loopora_host_dispatch": { "...": "pre-filled native dispatch proof" },
  "loopora_result_contract": { "...": "ignored on submit; use as the local fill guide" },
  "result": { "...": null }
}
```

Read `loopora_result_contract.step_id`, `.role`, `.action_policy`, `.required_coverage`, `.known_evidence_ids`, `.evidence_ref_contract`, `.evidence_rules`, `.role_dispatch`, `.native_todo`, `.native_trace_contract`, `.output_schema`, `.result_file_to_write`, and `.submit_command` before filling the file. Replace every `null` placeholder before submit, use empty arrays when the schema permits and there is no item to report, and remove optional placeholder fields you do not submit. The role agent returns raw wrapper JSON to the main session; the main session writes the result file and runs submit. The submitted filled file should contain exactly `loopora_host_dispatch` and `result`; use `loopora_result_contract` as the local template guide, then remove that helper block from the filled copy before submit.

If submit exits nonzero with `submit_repair=repair_result_json`, read the top-level `summary` first, report `repair_focus`, `result_file_to_repair`, `schema_lookup`, and `next_repair_step`; repair the filled copy and resubmit rather than continuing the run.

Preserve the template's `loopora_host_dispatch` except for `actual_agent` when the host-native role agent returned the same required target agent and a schema-shaped role output, and optional `native_trace` / `native_trace_ref` fields when the host exposes an official subagent/task trace. If the role call returns no wrapper or no structured output, stop before submit instead of constructing a role result from main-session observations. `target_agent` and `actual_agent` must both equal `next_step.role_dispatch.target_agent`, `inline` must be false, and `adapter` must be `{{adapter}}`.

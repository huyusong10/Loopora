from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GeneratorPromptRequest:
    compiled_spec: dict
    workdir: Path
    iter_id: int
    mode: str
    previous_generator_result: dict | None = None
    previous_tester_result: dict | None = None
    previous_verifier_result: dict | None = None
    previous_challenger_result: dict | None = None


def generator_prompt_request_from_args(
    request: GeneratorPromptRequest | dict,
    workdir: Path | None,
    iter_id: int | None,
    mode: str | None,
    feedback: dict[str, Any],
) -> GeneratorPromptRequest:
    if isinstance(request, GeneratorPromptRequest):
        if workdir is not None or iter_id is not None or mode is not None or feedback:
            raise TypeError("generator prompt request object cannot be combined with legacy prompt fields")
        return request
    if workdir is None or iter_id is None or mode is None:
        raise TypeError("legacy generator prompt calls require workdir, iter_id, and mode")
    fields = dict(feedback)
    prompt_request = GeneratorPromptRequest(
        compiled_spec=request,
        workdir=Path(workdir),
        iter_id=iter_id,
        mode=mode,
        previous_generator_result=fields.pop("previous_generator_result", None),
        previous_tester_result=fields.pop("previous_tester_result", None),
        previous_verifier_result=fields.pop("previous_verifier_result", None),
        previous_challenger_result=fields.pop("previous_challenger_result", None),
    )
    if fields:
        unexpected_fields = ", ".join(sorted(fields))
        raise TypeError(f"unexpected generator prompt fields: {unexpected_fields}")
    return prompt_request

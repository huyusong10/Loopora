from __future__ import annotations

from loopora.service_alignment_decision_options import visible_alignment_decision_options

DEFAULT_CLARIFYING_IDS = ["evidence_first", "speed_first", "add_judgment"]


def _option_ids(options: list[dict]) -> list[str]:
    return [option["id"] for option in options]


def _visible_option_ids(output: dict, *, has_bundle: bool = False, prefers_chinese: bool = False) -> list[str]:
    return _option_ids(
        visible_alignment_decision_options(output, has_bundle=has_bundle, prefers_chinese=prefers_chinese)
    )


def test_alignment_visible_decision_options_require_boolean_needs_user_input() -> None:
    assert (
        visible_alignment_decision_options(
            clarifying_output(*complete_custom_choices(), needs_user_input="false"),
            has_bundle=False,
            prefers_chinese=False,
        )
        == []
    )


def test_alignment_visible_decision_options_fall_back_when_custom_choice_set_is_incomplete() -> None:
    assert _visible_option_ids(
        clarifying_output(custom_choice("only_choice", recommended=True))
    ) == DEFAULT_CLARIFYING_IDS
    assert _visible_option_ids(
        clarifying_output(custom_choice("slow", recommended=None), custom_choice("fast", recommended=None))
    ) == DEFAULT_CLARIFYING_IDS


def test_alignment_visible_decision_options_fall_back_when_custom_choice_fields_are_invalid() -> None:
    assert _visible_option_ids(
        clarifying_output(custom_choice("evidence_path", description=None), custom_choice("speed_path", recommended=False))
    ) == DEFAULT_CLARIFYING_IDS
    assert _visible_option_ids(
        clarifying_output(custom_choice("evidence_path", recommended="true"), custom_choice("speed_path", recommended="false"))
    ) == DEFAULT_CLARIFYING_IDS


def test_alignment_visible_decision_options_accept_complete_custom_choice_set() -> None:
    assert _visible_option_ids(clarifying_output(*complete_custom_choices())) == ["evidence_path", "speed_path"]


def test_alignment_visible_decision_options_use_stage_specific_choice_sets() -> None:
    assert _visible_option_ids(
        {"alignment_phase": "blocked", "assistant_message": "Not a fit."},
        prefers_chinese=True,
    ) == ["skip_loop", "still_compile"]
    assert _visible_option_ids(
        {"needs_user_input": True, "alignment_phase": "agreement"},
        prefers_chinese=True,
    ) == ["confirm_agreement", "adjust_agreement"]


def complete_custom_choices() -> list[dict]:
    return [custom_choice("evidence_path", recommended=True), custom_choice("speed_path", recommended=False)]


def clarifying_output(*choices: dict, needs_user_input: object = True) -> dict:
    return {"needs_user_input": needs_user_input, "alignment_phase": "clarifying", "decision_options": list(choices)}


def custom_choice(choice_id: str, *, recommended: object = True, description: str | None = "Prefer proof.") -> dict:
    choice = {"id": choice_id, "label": choice_id.replace("_", " ").title(), "user_reply": f"Use {choice_id}."}
    if description is not None:
        choice["description"] = description
    if recommended is not None:
        choice["recommended"] = recommended
    return choice

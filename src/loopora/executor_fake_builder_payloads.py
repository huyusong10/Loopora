from __future__ import annotations

"""Fake Builder, Check Planner, and Inspector role payloads."""


def fake_builder_payload(iter_id: int) -> dict:
    return {
        "attempted": f"Iter {iter_id}: refine workdir against the frozen task contract",
        "abandoned": "Did not widen scope or lower Done When to make the iteration look complete.",
        "assumption": "The highest-impact gain is still the primary path with evidence Inspector can verify.",
        "summary": "Applied a focused change strategy and left the proof surface for Inspector and GateKeeper.",
        "changed_files": [],
        "proof_files": [],
        "proof_artifacts": [],
        "artifact_paths": [],
    }


def fake_check_planner_payload(compiled_spec: dict) -> dict:
    goal = (compiled_spec.get("goal") or "the prototype").strip()
    return {
        "checks": [
            {
                "title": "Goal alignment",
                "details": (
                    f"When: someone reviews the current prototype against the goal.\n"
                    f"Expect: the main flow clearly moves toward {goal}.\n"
                    "Fail if: the prototype feels unrelated, confusing, or incomplete in its primary direction."
                ),
                "when": "Someone evaluates the prototype as-is.",
                "expect": f"The main flow visibly supports {goal}.",
                "fail_if": "The current direction is confusing or disconnected from the goal.",
            },
            {
                "title": "Primary interaction holds together",
                "details": (
                    "When: a user follows the most obvious interaction path.\n"
                    "Expect: the path remains understandable from start to finish.\n"
                    "Fail if: the experience breaks, stalls, or loses its state."
                ),
                "when": "A user follows the most obvious path.",
                "expect": "The path stays understandable and coherent.",
                "fail_if": "The experience breaks, stalls, or loses its state.",
            },
            {
                "title": "Prototype safety",
                "details": (
                    "When: the user hits an incomplete or awkward edge in the prototype.\n"
                    "Expect: the interface still communicates what is happening.\n"
                    "Fail if: the prototype crashes, misleads the user, or becomes unusable."
                ),
                "when": "An incomplete or awkward edge appears.",
                "expect": "The interface still communicates clearly.",
                "fail_if": "The prototype crashes, misleads the user, or becomes unusable.",
            },
        ],
        "generation_notes": "Generated a compact exploratory check set because the spec did not provide explicit checks.",
    }


def fake_tester_payload(iter_id: int, checks: list[dict], check_count: int) -> dict:
    passed_checks = min(check_count, 1 + iter_id)
    total_checks = check_count
    results = []
    for index, check in enumerate(checks, start=1):
        status = "passed" if index <= passed_checks else "failed"
        results.append(
            {
                "id": check["id"],
                "title": check["title"],
                "status": status,
                "notes": _fake_check_notes(check, status),
            }
        )
    return {
        "execution_summary": {
            "total_checks": total_checks,
            "passed": passed_checks,
            "failed": max(total_checks - passed_checks, 0),
            "errored": 0,
            "total_duration_ms": 500 + iter_id * 25,
        },
        "check_results": results,
        "dynamic_checks": [],
        "tester_observations": (
            "Fake executor evaluated the compiled Markdown checks against the frozen run contract; "
            "passed checks move toward Proven only through traceable evidence, while failed checks stay "
            "Blocking or Unproven for GateKeeper."
        ),
        "coverage_results": [],
    }


def _fake_check_notes(check: dict, status: str) -> str:
    base = str(check.get("expect") or check.get("details") or "").strip()
    if status == "passed":
        suffix = "Fake evidence treats this as Proven only through the inspector evidence ledger."
    else:
        suffix = "This remains Blocking or Unproven until a later Builder repair produces new proof."
    return f"{base} {suffix}".strip()

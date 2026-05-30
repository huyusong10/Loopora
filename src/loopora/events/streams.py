from __future__ import annotations


def loop_stream_id(loop_id: str) -> str:
    return f"loop:{loop_id}"


def run_stream_id(run_id: str) -> str:
    return f"run:{run_id}"


def evidence_stream_id(run_id: str) -> str:
    return f"evidence:{run_id}"

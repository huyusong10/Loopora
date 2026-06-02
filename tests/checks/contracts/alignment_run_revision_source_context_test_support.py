from pathlib import Path


def create_revision_source_loop(
    service,
    sample_spec_file: Path,
    sample_workdir: Path,
    *,
    name: str,
) -> dict:
    return service.create_loop(
        name=name,
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )


__all__ = ["create_revision_source_loop"]

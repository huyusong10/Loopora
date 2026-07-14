from __future__ import annotations

from pathlib import Path

from loopora.local_workdir_artifacts import loop_artifact_dir_for_ready_workdir
from loopora.run_artifacts import RunArtifactLayout
from loopora.strategy_source import (
    StrategySourceError,
    load_strategy_prompt_file,
    resolve_strategy_prompt_files,
    strategy_prompt_asset_path,
)


class ServiceLoopPromptFileMixin:
    def _prompt_dir(self, base_dir: Path) -> Path:
        return base_dir / "prompts"

    def _run_artifact_layout(self, run_dir: Path) -> RunArtifactLayout:
        return RunArtifactLayout(run_dir)

    def _persist_prompt_files(self, base_dir: Path, prompt_files: dict[str, str]) -> None:
        prompt_dir = self._prompt_dir(base_dir)
        prompt_dir.mkdir(parents=True, exist_ok=True)
        for prompt_ref, markdown_text in sorted(prompt_files.items()):
            path = strategy_prompt_asset_path(prompt_dir, prompt_ref)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(markdown_text), encoding="utf-8")

    def _read_prompt_files(self, base_dir: Path, strategy_source: dict) -> dict[str, str]:
        prompt_files: dict[str, str] = {}
        for role in strategy_source.get("roles", []):
            prompt_ref = str(role.get("prompt_ref", "")).strip()
            if not prompt_ref or prompt_ref in prompt_files:
                continue
            path = strategy_prompt_asset_path(self._prompt_dir(base_dir), prompt_ref)
            try:
                prompt_exists = path.exists()
                if prompt_exists:
                    prompt_files[prompt_ref] = load_strategy_prompt_file(path)
            except StrategySourceError as exc:
                if "could not be read" in str(exc):
                    raise StrategySourceError(f"prompt artifact {prompt_ref} could not be read") from exc
                raise StrategySourceError(f"prompt artifact {prompt_ref}: {exc}") from exc
            except OSError as exc:
                raise StrategySourceError(f"prompt artifact {prompt_ref} could not be read") from exc
        return resolve_strategy_prompt_files(strategy_source, prompt_files)

    def _loop_prompt_artifact_dir(self, workdir: str, loop_id: str) -> Path | None:
        return loop_artifact_dir_for_ready_workdir(workdir, loop_id)

    def _read_prompt_files_for_loop(self, workdir: str, loop_id: str, strategy_source: dict) -> dict[str, str]:
        loop_dir = self._loop_prompt_artifact_dir(workdir, loop_id)
        if loop_dir is None:
            return resolve_strategy_prompt_files(strategy_source, {})
        return self._read_prompt_files(loop_dir, strategy_source)

    def _read_prompt_files_for_run(self, run: dict) -> dict[str, str]:
        strategy_source = self._normalized_strategy_source_from_record(run)
        layout = self._run_artifact_layout(Path(run["runs_dir"]))
        return self._read_prompt_files(layout.contract_dir, strategy_source)

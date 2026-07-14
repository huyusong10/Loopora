from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from loopora.branding import APP_HOME_ENV
from loopora.executor_fake import FakeCodexExecutor
from loopora.service import LooporaError, LooporaService, create_service
from loopora.workdir_inputs import restricted_workdir_scope


@dataclass(frozen=True, slots=True)
class DemoEnvironment:
    root: Path
    app_home: Path
    workdir: Path
    playground_workdir: Path
    service: LooporaService
    loop: dict
    run: dict

    @property
    def run_path(self) -> str:
        return f"/runs/{self.run['id']}"


@contextmanager
def seeded_demo_environment(*, language: str = "en") -> Iterator[DemoEnvironment]:
    normalized_language = normalize_demo_language(language)
    previous_app_home = os.environ.get(APP_HOME_ENV)
    with TemporaryDirectory(prefix="loopora-demo-") as temporary_root:
        root = Path(temporary_root)
        with restricted_workdir_scope(root):
            app_home = root / "app-home"
            workdir = root / "sample-project"
            playground_workdir = root / "playground"
            workdir.mkdir(parents=True)
            playground_workdir.mkdir(parents=True)
            os.environ[APP_HOME_ENV] = str(app_home)
            try:
                spec_path = _write_demo_project(root, workdir, language=normalized_language)
                service = create_service(
                    executor_factory=lambda: FakeCodexExecutor(
                        scenario="success",
                        display_language=normalized_language,
                    )
                )
                loop = service.create_loop(
                    name="发布证据样例" if normalized_language == "zh" else "Release evidence demo",
                    spec_path=spec_path,
                    workdir=workdir,
                    model="",
                    reasoning_effort="",
                    max_iters=3,
                    max_role_retries=1,
                    delta_threshold=0.005,
                    trigger_window=2,
                    regression_window=2,
                    role_models={},
                )
                run = service.rerun(loop["id"])
                if run.get("status") != "succeeded" or (run.get("task_verdict") or {}).get("status") != "passed":
                    raise LooporaError("the bundled demo did not produce its expected evidence-backed passing verdict")
                yield DemoEnvironment(
                    root=root,
                    app_home=app_home,
                    workdir=workdir,
                    playground_workdir=playground_workdir,
                    service=service,
                    loop=loop,
                    run=run,
                )
            finally:
                if previous_app_home is None:
                    os.environ.pop(APP_HOME_ENV, None)
                else:
                    os.environ[APP_HOME_ENV] = previous_app_home


def normalize_demo_language(value: str) -> str:
    normalized = str(value or "").strip().lower().replace("_", "-")
    if normalized in {"en", "en-us", "en-gb"}:
        return "en"
    if normalized in {"zh", "zh-cn", "zh-hans"}:
        return "zh"
    raise LooporaError("demo language must be en or zh")


def _write_demo_project(root: Path, workdir: Path, *, language: str) -> Path:
    asset = Path(__file__).parent / "assets" / "demo" / f"first-result.{language}.md"
    spec_path = root / "demo-spec.md"
    spec_path.write_text(asset.read_text(encoding="utf-8"), encoding="utf-8")
    progress = (
        "# 样例项目\n\n这是由 Loopora 隔离 Demo 创建的临时项目。\n"
        if language == "zh"
        else "# Sample project\n\nThis temporary project was created by the isolated Loopora demo.\n"
    )
    (workdir / "progress.md").write_text(progress, encoding="utf-8")
    return spec_path

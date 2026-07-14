from __future__ import annotations

import importlib.util
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.sdist import sdist as _sdist

ROOT = Path(__file__).resolve().parent
PROVENANCE_MODULE_PATH = ROOT / "src" / "loopora" / "package_source_provenance.py"


def _provenance_module():
    spec = importlib.util.spec_from_file_location("loopora_build_provenance", PROVENANCE_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Loopora package source provenance helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _source_provenance():
    module = _provenance_module()
    packaged_path = ROOT / "src" / "loopora" / module.SOURCE_PROVENANCE_FILENAME
    return module, module.package_source_provenance(source_root=ROOT, packaged_path=packaged_path)


class BuildPyWithSourceProvenance(_build_py):
    def run(self) -> None:
        super().run()
        module, provenance = _source_provenance()
        target = Path(self.build_lib) / "loopora" / module.SOURCE_PROVENANCE_FILENAME
        module.write_source_provenance(target, provenance)


class SdistWithSourceProvenance(_sdist):
    def make_release_tree(self, base_dir: str, files: list[str]) -> None:
        super().make_release_tree(base_dir, files)
        module, provenance = _source_provenance()
        target = Path(base_dir) / "src" / "loopora" / module.SOURCE_PROVENANCE_FILENAME
        module.write_source_provenance(target, provenance)


setup(cmdclass={"build_py": BuildPyWithSourceProvenance, "sdist": SdistWithSourceProvenance})

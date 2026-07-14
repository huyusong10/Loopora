from __future__ import annotations

from pathlib import Path

from loopora.service_alignment_workdir_snapshot import alignment_same_workdir, alignment_workdir_spec_candidates


WORKDIR_SPEC_CANDIDATE_LIMIT = 20


def test_alignment_workdir_spec_candidates_list_root_then_loop_specs_with_budget(tmp_path: Path) -> None:
    state_dir = tmp_path / ".loopora"
    root_spec = state_dir / "spec.md"
    loop_02_spec = state_dir / "loops" / "loop_02" / "spec.md"
    loop_01_spec = state_dir / "loops" / "loop_01" / "spec.md"
    root_spec.parent.mkdir(parents=True)
    loop_02_spec.parent.mkdir(parents=True)
    loop_01_spec.parent.mkdir(parents=True)
    root_spec.write_text("# Root spec\n", encoding="utf-8")
    loop_02_spec.write_text("# Loop 02 spec\n", encoding="utf-8")
    loop_01_spec.write_text("# Loop 01 spec\n", encoding="utf-8")
    (state_dir / "loops" / "loop_00").mkdir(parents=True)

    candidates = alignment_workdir_spec_candidates(state_dir)

    assert candidates[:3] == [root_spec, loop_01_spec, loop_02_spec]
    assert alignment_workdir_spec_candidates(tmp_path / "missing") == []


def test_alignment_workdir_spec_candidates_caps_source_budget(tmp_path: Path) -> None:
    state_dir = tmp_path / ".loopora"
    (state_dir / "loops").mkdir(parents=True)
    for index in range(25):
        spec_path = state_dir / "loops" / f"loop_{index:02d}" / "spec.md"
        spec_path.parent.mkdir()
        spec_path.write_text(f"# Loop {index}\n", encoding="utf-8")

    candidates = alignment_workdir_spec_candidates(state_dir)

    assert len(candidates) == WORKDIR_SPEC_CANDIDATE_LIMIT
    assert candidates[0] == state_dir / "loops" / "loop_00" / "spec.md"
    assert candidates[-1] == state_dir / "loops" / "loop_19" / "spec.md"


def test_alignment_workdir_spec_candidates_preserve_root_spec_when_loop_scan_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    state_dir = tmp_path / ".loopora"
    loops_dir = state_dir / "loops"
    root_spec = state_dir / "spec.md"
    root_spec.parent.mkdir(parents=True)
    loops_dir.mkdir()
    root_spec.write_text("# Root spec\n", encoding="utf-8")
    private_path = tmp_path / "private" / "loops"
    original_glob = Path.glob

    def fail_glob(path: Path, pattern: str):
        if path == loops_dir:
            raise OSError(f"permission denied: {private_path}")
        return original_glob(path, pattern)

    monkeypatch.setattr(Path, "glob", fail_glob)

    assert alignment_workdir_spec_candidates(state_dir) == [root_spec]


def test_alignment_workdir_spec_candidates_skip_unavailable_spec_paths(tmp_path: Path, monkeypatch) -> None:
    state_dir = tmp_path / ".loopora"
    root_spec = state_dir / "spec.md"
    good_spec = state_dir / "loops" / "loop_01" / "spec.md"
    unavailable_spec = state_dir / "loops" / "loop_02" / "spec.md"
    root_spec.parent.mkdir(parents=True)
    good_spec.parent.mkdir(parents=True)
    unavailable_spec.parent.mkdir(parents=True)
    root_spec.write_text("# Root spec\n", encoding="utf-8")
    good_spec.write_text("# Good spec\n", encoding="utf-8")
    unavailable_spec.write_text("# Unavailable spec\n", encoding="utf-8")
    private_path = tmp_path / "private" / "spec.md"
    original_is_file = Path.is_file

    def fail_is_file(path: Path) -> bool:
        if path == unavailable_spec:
            raise OSError(f"permission denied: {private_path}")
        return original_is_file(path)

    monkeypatch.setattr(Path, "is_file", fail_is_file)

    assert alignment_workdir_spec_candidates(state_dir) == [root_spec, good_spec]


def test_alignment_same_workdir_resolves_path_identity(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()

    assert alignment_same_workdir(root, root)
    assert alignment_same_workdir(root / ".." / "project", root)
    assert not alignment_same_workdir("", root)
    assert not alignment_same_workdir(tmp_path / "other", root)

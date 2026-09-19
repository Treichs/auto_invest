import pathlib
import runpy
import tomllib

from build_quantconnect_project import RUBRIC, ROOT, build, snapshot_source
from lean_adapter import rubric_hash
from settings import Ceilings, Settings, check_against_ceilings

EXPECTED = {
    "main.py", "lean_adapter.py", "settings.py", "settings_snapshot.py",
    *(f"rubric/{p.name}" for p in RUBRIC.glob("*.py")),
}


def test_build_writes_exactly_the_paste_ready_tree(tmp_path):
    out = tmp_path / "quantconnect"
    files = build(out)
    assert {p.relative_to(out).as_posix() for p in files} == EXPECTED
    assert len(files) == 13
    assert all(p.stat().st_size < 32 * 1024 for p in files)


def test_build_copies_the_rubric_byte_for_byte(tmp_path):
    out = tmp_path / "quantconnect"
    build(out)
    assert rubric_hash(out / "rubric") == rubric_hash(RUBRIC)
    for path in RUBRIC.glob("*.py"):
        assert (out / "rubric" / path.name).read_bytes() == path.read_bytes()
    assert (out / "settings.py").read_bytes() == (ROOT / "src" / "auto_invest" / "settings.py").read_bytes()


def test_snapshot_matches_the_toml_files_and_passes_the_ceiling_check(tmp_path):
    path = tmp_path / "settings_snapshot.py"
    path.write_text(snapshot_source())
    namespace = runpy.run_path(str(path))
    assert namespace["SETTINGS"] == tomllib.loads((ROOT / "config" / "settings.toml").read_text())
    assert namespace["CEILINGS"] == tomllib.loads((ROOT / "config" / "ceilings.toml").read_text())
    settings = Settings.model_validate(namespace["SETTINGS"])
    check_against_ceilings(settings, Ceilings.model_validate(namespace["CEILINGS"]))
    assert settings.candidate_interval_minutes == 5


def test_build_replaces_a_stale_tree(tmp_path):
    out = tmp_path / "quantconnect"
    out.mkdir()
    (out / "stale.py").write_text("x = 1\n")
    build(out)
    assert not (out / "stale.py").exists()

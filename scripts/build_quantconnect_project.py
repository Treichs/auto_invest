import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "auto_invest"
ADAPTER = PACKAGE / "adapters" / "lean"
RUBRIC = PACKAGE / "rubric"
CONFIG = ROOT / "config"
OUT = ROOT / "build" / "quantconnect"

sys.path[:0] = [str(PACKAGE), str(ADAPTER)]

from lean_adapter import rubric_hash


def snapshot_source() -> str:
    settings = tomllib.loads((CONFIG / "settings.toml").read_text())
    ceilings = tomllib.loads((CONFIG / "ceilings.toml").read_text())
    return f"SETTINGS = {settings!r}\nCEILINGS = {ceilings!r}\n"


def build(out: Path = OUT) -> list[Path]:
    if out.exists():
        shutil.rmtree(out)
    (out / "rubric").mkdir(parents=True)
    for name in ("main.py", "lean_adapter.py"):
        shutil.copyfile(ADAPTER / name, out / name)
    shutil.copyfile(PACKAGE / "settings.py", out / "settings.py")
    (out / "settings_snapshot.py").write_text(snapshot_source(), newline="\n")
    for path in sorted(RUBRIC.glob("*.py")):
        shutil.copyfile(path, out / "rubric" / path.name)
    return sorted(path for path in out.rglob("*") if path.is_file())


def main() -> None:
    files = build()
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT
    ).stdout.strip()
    print(f"wrote {len(files)} files to {OUT}")
    print(f"rubric sha256 {rubric_hash(RUBRIC)}")
    print(f"git commit {commit}")


if __name__ == "__main__":
    main()

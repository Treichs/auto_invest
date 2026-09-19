import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src" / "auto_invest"), str(ROOT / "src" / "auto_invest" / "adapters" / "lean")]

from lean_adapter import rejection_counts


def main(path: str) -> None:
    lines = [line for line in Path(path).read_text().splitlines() if line.strip()]
    counts = rejection_counts(lines)
    for key in sorted(counts, key=counts.get, reverse=True):
        print(f"{counts[key]:>7}  {key}")
    print(f"{len(lines):>7}  total")


if __name__ == "__main__":
    main(sys.argv[1])

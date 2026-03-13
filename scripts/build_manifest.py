#!/usr/bin/env python3
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.results_manifest import write_results_manifest


def main() -> int:
    target = write_results_manifest(REPO_ROOT / "docs" / "results")
    print(f"Manifesto atualizado em: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

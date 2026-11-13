"""collection → preprocessing을 순서대로 실행한다.

사용법: python run_all.py  (pipeline 디렉터리에서 실행, GitHub Actions의 매일 배치 진입점)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

STAGES = ["collection", "preprocessing"]


def main() -> None:
    root = Path(__file__).resolve().parent
    for stage in STAGES:
        subprocess.run([sys.executable, "run_all.py"], cwd=root / stage, check=True)


if __name__ == "__main__":
    main()

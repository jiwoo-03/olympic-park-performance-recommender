"""매칭 → 정제 → EDA를 순서대로 실행한다."""
from __future__ import annotations

import eda
import match_performances
import normalize_and_clean


def main() -> None:
    match_performances.main()
    normalize_and_clean.main()
    eda.main()


if __name__ == "__main__":
    main()

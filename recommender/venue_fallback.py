"""미분류 공연에 대한 보조 추천: 메인(장르 기반) 추천에서 제외된 공연 대신,
같은 장소(`venue_normalized`)에서 열리는 다른 예정 공연을 별도 섹션으로 보여준다.

메인 취향/조건 추천과 섞지 않는다 — 같은 장소라는 이유만으로 성격이 다른 공연이
끼어들 수 있기 때문이다(tasks/todo.md "0. 데이터 보강" 참고).
"""
from __future__ import annotations

import re
from datetime import date

import pandas as pd

_PERIOD_PATTERNS = [
    re.compile(r"(\d{4})-(\d{2})-(\d{2})\s*~\s*(\d{4})-(\d{2})-(\d{2})"),
    re.compile(r"(\d{4})(\d{2})(\d{2})\s+(\d{4})(\d{2})(\d{2})"),
]


def _parse_period_end(period: str) -> date | None:
    for pattern in _PERIOD_PATTERNS:
        m = pattern.search(period or "")
        if m:
            y2, mo2, d2 = int(m.group(4)), int(m.group(5)), int(m.group(6))
            try:
                return date(y2, mo2, d2)
            except ValueError:
                return None
    return None


def same_venue_fallback(
    df: pd.DataFrame,
    title: str,
    limit: int = 5,
    today: date | None = None,
) -> pd.DataFrame:
    """`title` 공연과 같은 `venue_normalized`를 가진, 아직 끝나지 않은 다른 공연을 반환한다."""
    today = today or date.today()
    matches = df[df["title"] == title]
    if matches.empty:
        return df.iloc[0:0]

    venue = matches.iloc[0]["venue_normalized"]
    if not venue:
        return df.iloc[0:0]

    candidates = df[(df["venue_normalized"] == venue) & (df["title"] != title)].copy()
    candidates["_period_end"] = candidates["period"].map(_parse_period_end)
    upcoming = candidates[candidates["_period_end"].isna() | (candidates["_period_end"] >= today)]
    return upcoming.drop(columns="_period_end").head(limit)

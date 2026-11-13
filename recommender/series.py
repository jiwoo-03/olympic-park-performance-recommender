"""반복 공연 시리즈 감지 + 다음 회차 예상 시기 추정 — 규칙 기반이다, ML 예측 모델이 아니다.

제목(연도 제거)이 같은 공연이 과거 여러 해에 걸쳐 일정 횟수 이상 열렸으면 "매년 비슷한
시기에 열리는 시리즈"로 보고, 가장 최근 회차의 날짜를 1년 뒤로 밀어 다음 회차를 추정한다.
공식 일정이 아니라 과거 패턴으로 추정한 것이므로, 쓰는 쪽(recommend.py)이 항상
`STATUS_PREDICTED`로 표시해야 한다.
"""
from __future__ import annotations

import re
from datetime import date

import pandas as pd

_YEAR_TOKEN_PATTERN = re.compile(r"(?<!\d)(19|20)\d{2}(?!\d)")
_NORMALIZE_PATTERN = re.compile(r"[\s\W_]+", flags=re.UNICODE)
_PERIOD_PATTERNS = [
    re.compile(r"(\d{4})-(\d{2})-(\d{2})\s*~\s*(\d{4})-(\d{2})-(\d{2})"),
    re.compile(r"(\d{4})(\d{2})(\d{2})\s+(\d{4})(\d{2})(\d{2})"),
]

MIN_OCCURRENCES = 3  # 이보다 적게 반복됐으면 "매년 열린다"고 보기엔 근거가 약하다
PREDICTED_MATCH_STATUS = "predicted"


def _normalize_title(title: str) -> str:
    without_year = _YEAR_TOKEN_PATTERN.sub("", title or "")
    return _NORMALIZE_PATTERN.sub("", without_year).lower()


def _parse_period(period: str) -> tuple[date | None, date | None]:
    for pattern in _PERIOD_PATTERNS:
        m = pattern.search(period or "")
        if m:
            y1, mo1, d1, y2, mo2, d2 = map(int, m.groups())
            try:
                return date(y1, mo1, d1), date(y2, mo2, d2)
            except ValueError:
                return None, None
    return None, None


def _latest_occurrence_per_series(df: pd.DataFrame, min_occurrences: int) -> pd.DataFrame:
    """매칭된 공연 중 min_occurrences회 이상 반복된 시리즈의 "가장 최근 회차" 행만
    모아서 돌려준다. 원래 df의 인덱스를 유지한다(나중에 같은 벡터를 재사용하기 위함)."""
    matched = df[df["match_status"] == "matched"].copy()
    matched["_norm_title"] = matched["title"].map(_normalize_title)
    matched["_start"] = matched["period"].map(lambda p: _parse_period(p)[0])
    matched = matched.dropna(subset=["_start"])

    counts = matched.groupby("_norm_title").size()
    recurring_titles = set(counts[counts >= min_occurrences].index)
    if not recurring_titles:
        return df.iloc[0:0]

    matched = matched[matched["_norm_title"].isin(recurring_titles)]
    latest_idx = matched.sort_values("_start").groupby("_norm_title").tail(1).index
    return df.loc[latest_idx]


def _predict_next_occurrence(latest_row: pd.Series, today: date) -> dict | None:
    """가장 최근 회차를 1년 뒤로 밀어 다음 회차를 추정한다. 이미 1년을 더 넘겨도 지난
    날짜면(2년 넘게 안 열렸으면) 시리즈가 끊겼을 수 있으니 예측하지 않는다."""
    start, end = _parse_period(latest_row["period"])
    if start is None or end is None:
        return None
    duration = end - start

    try:
        predicted_start = start.replace(year=start.year + 1)
    except ValueError:  # 2월 29일처럼 다음 해엔 없는 날짜
        predicted_start = start.replace(year=start.year + 1, day=28)
    if predicted_start < today:
        try:
            predicted_start = predicted_start.replace(year=predicted_start.year + 1)
        except ValueError:
            predicted_start = predicted_start.replace(year=predicted_start.year + 1, day=28)
    if predicted_start < today or (predicted_start - today).days > 365:
        return None

    predicted_end = predicted_start + duration
    predicted = latest_row.to_dict()
    predicted["title"] = latest_row["title"]
    predicted["period"] = f"{predicted_start.strftime('%Y%m%d')} {predicted_end.strftime('%Y%m%d')}"
    predicted["match_status"] = PREDICTED_MATCH_STATUS
    predicted["popularity_score"] = 0.0  # 아직 일어나지 않은 회차라 인기도 신호가 없음
    predicted["kopis_mt20id"] = ""
    return predicted


def build_predicted_rows(
    df: pd.DataFrame, today: date, min_occurrences: int = MIN_OCCURRENCES,
) -> list[tuple[int, dict]]:
    """(원본 행의 df 인덱스, 다음 회차 예상 행) 목록을 돌려준다.

    원본 인덱스를 같이 주는 이유: 예상 행은 벡터를 새로 계산하지 않고 원본 회차의
    벡터(장르·출연진·제목이 사실상 같음)를 그대로 재사용하기 때문이다.
    """
    latest = _latest_occurrence_per_series(df, min_occurrences)
    results = []
    for idx, row in latest.iterrows():
        predicted = _predict_next_occurrence(row, today)
        if predicted is not None:
            results.append((idx, predicted))
    return results

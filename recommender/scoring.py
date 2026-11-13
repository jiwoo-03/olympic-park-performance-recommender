"""추천 점수 계산 공통 유틸: 공연 기간 파싱, 종료 판별, 날짜 근접도, 최종 점수, MMR 재정렬.

최종 점수 = 취향 유사도×TASTE_WEIGHT + 인기도×POPULARITY_WEIGHT + 날짜 근접도×DATE_WEIGHT
(워크플로우 문서 6장). 가중치는 "3. 오프라인 평가" 단계에서 조정할 수 있게 상수로 뺐다.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

import numpy as np

_PERIOD_PATTERNS = [
    re.compile(r"(\d{4})-(\d{2})-(\d{2})\s*~\s*(\d{4})-(\d{2})-(\d{2})"),
    re.compile(r"(\d{4})(\d{2})(\d{2})\s+(\d{4})(\d{2})(\d{2})"),
]

TASTE_WEIGHT = 0.6
POPULARITY_WEIGHT = 0.2
DATE_WEIGHT = 0.2
DATE_PROXIMITY_HORIZON_DAYS = 30  # 이 안에 시작하면 근접도가 1에 가깝고, 멀어질수록 0에 가까움
MMR_LAMBDA = 0.7  # 1에 가까우면 관련성 위주, 0에 가까우면 다양성(장르 분산) 위주

# top_k에 상한을 두는 이유: 데이터가 쌓여 후보 풀이 커져도 top_k 자체엔 상한이 없어서,
# 호출하는 쪽(나중의 backend/ API 등)이 큰 값을 그대로 넘기면 그만큼 많은 결과를 긁어줄
# 위험이 있다. 추천 결과는 한 화면에 보여줄 분량이면 충분하므로 넉넉하게 20으로 clamp한다.
MAX_TOP_K = 20

# ---- 콘텐츠 우선 모드 ----
# 2026-11-12 기준, 매칭된 공연 중 "안 끝난" 공연이 뮤지컬·클래식·페스티벌·어린이에서
# 0건이라(워크플로우 문서 7장 리스크 1번 실측 확인, recommender/REPORT.md 참고) 날짜
# 확정 여부만으로 추천하면 사실상 콘서트만 나온다. 그래서 지금은:
#   True  — 취향 추천·비슷한 공연에서 날짜 확정 여부와 상관없이 콘텐츠(장르+출연진)로
#           추천하고, 결과마다 상태(STATUS_*)를 붙여 "확정인지/추정인지/과거 기록인지"를
#           구분해 보여준다. 반복 시리즈(series.py)는 다음 회차를 예측해 후보에 끼운다.
#   False — 원래 설계: 확정된 예정 공연만 추천한다.
# 한국체육산업개발이 실제 서비스로 채택해 미래 공연 일정이 충분히 들어오게 되면, 이 값을
# False로 바꾸는 것만으로 원래 설계로 되돌아간다(코드 변경 불필요).
# 조건 추천(condition_recommend)·콜드스타트(coldstart_recommend)는 이 스위치와 무관하게
# 항상 날짜 기반으로 동작한다 — "이 날짜/이번 주말에 뭐가 있나"를 묻는 기능에 아무 관련
# 없는 과거 공연을 끼워 넣으면 안 되기 때문이다.
CONTENT_FIRST_MODE = True

# 반복 시리즈(series.py)가 예측한 "다음 회차"를 추천 후보에 끼워 넣을지 여부.
# CONTENT_FIRST_MODE와는 독립된 스위치다 — 과거 공연을 "참고용"으로 보여주는 것과,
# 아직 확정 안 된 미래 일정을 "열릴 것으로 예상"처럼 보여주는 건 성격이 다르다는
# 사용자 판단으로 껐다(2026-11-12, tasks/todo.md "추가 기능 요청" 참고). True로 되돌리면
# `series.build_predicted_rows()`가 다시 후보 풀에 끼어든다(코드 변경 불필요).
INCLUDE_PREDICTED_SERIES = False

STATUS_CONFIRMED = "확정 예정"
STATUS_PREDICTED = "매년 반복 예상"
STATUS_HISTORICAL = "과거 유사 공연 — 참고용"


def parse_period(period: str) -> tuple[date | None, date | None]:
    for pattern in _PERIOD_PATTERNS:
        m = pattern.search(period or "")
        if m:
            y1, mo1, d1, y2, mo2, d2 = map(int, m.groups())
            try:
                return date(y1, mo1, d1), date(y2, mo2, d2)
            except ValueError:
                return None, None
    return None, None


def is_ended(period: str, today: date | None = None) -> bool:
    today = today or date.today()
    _, end = parse_period(period)
    return end is not None and end < today


def period_overlaps(period: str, start: date, end: date) -> bool:
    p_start, p_end = parse_period(period)
    if p_start is None or p_end is None:
        return False
    return p_start <= end and start <= p_end


def date_proximity_score(period: str, today: date | None = None) -> float:
    """공연 시작일이 오늘에 가까울수록 1에 가깝고, HORIZON_DAYS보다 멀면 0에 가깝다.
    이미 진행 중인 공연(오늘이 기간 안)은 가장 가까운 것으로 보고 1.0을 준다."""
    today = today or date.today()
    start, end = parse_period(period)
    if start is None:
        return 0.0
    if end is not None and start <= today <= end:
        return 1.0
    days_until = (start - today).days
    if days_until < 0:
        return 0.0
    return max(0.0, 1.0 - days_until / DATE_PROXIMITY_HORIZON_DAYS)


def final_score(taste_sim: float, popularity_score: float, period: str, today: date | None = None) -> float:
    return (
        TASTE_WEIGHT * taste_sim
        + POPULARITY_WEIGHT * (popularity_score or 0.0)
        + DATE_WEIGHT * date_proximity_score(period, today)
    )


def upcoming_weekend(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    days_to_sat = (5 - today.weekday()) % 7  # weekday(): 월=0 ... 토=5, 일=6
    saturday = today + timedelta(days=days_to_sat)
    return saturday, saturday + timedelta(days=1)


def cosine_sim(u: np.ndarray, v: np.ndarray) -> float:
    return float(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-9))


def cosine_sim_batch(matrix: np.ndarray, query: np.ndarray) -> np.ndarray:
    """matrix의 각 행과 query 하나의 코사인 유사도. query가 영벡터면 전부 0을 돌려준다."""
    query_norm = np.linalg.norm(query)
    if query_norm == 0:
        return np.zeros(matrix.shape[0])
    row_norms = np.linalg.norm(matrix, axis=1)
    return (matrix @ query) / (row_norms * query_norm + 1e-9)


def mmr_rerank(
    candidate_idx: list[int],
    relevance: dict[int, float],
    vectors: np.ndarray,
    top_k: int,
    lam: float = MMR_LAMBDA,
) -> list[int]:
    """관련성과 다양성(이미 뽑힌 것들과의 최대 유사도)을 함께 고려해 top_k개를 뽑는다.
    같은 장르·같은 아티스트 공연이 줄줄이 뽑히는 걸 막는다(6장 "MMR로 재정렬")."""
    selected: list[int] = []
    remaining = list(candidate_idx)
    while remaining and len(selected) < top_k:
        best_idx, best_mmr = None, float("-inf")
        for idx in remaining:
            max_sim = max((cosine_sim(vectors[idx], vectors[s]) for s in selected), default=0.0)
            mmr = lam * relevance[idx] - (1 - lam) * max_sim
            if mmr > best_mmr:
                best_idx, best_mmr = idx, mmr
        selected.append(best_idx)
        remaining.remove(best_idx)
    return selected

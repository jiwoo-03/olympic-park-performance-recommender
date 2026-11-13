"""추천 3종(MVP) + 콜드스타트: 취향 추천, 조건 추천, 비슷한 공연.

genre == "미분류"는 항상 메인 추천 후보에서 뺀다 — 장르 정보가 없어서 취향 유사도를
믿을 수 없기 때문이다(tasks/todo.md "0. 데이터 보강" 결정). 대신 `venue_fallback.py`가
같은 장소의 다른 공연을 별도 섹션으로 보여준다.

`scoring.CONTENT_FIRST_MODE`(현재 True)가 켜져 있으면 `taste_recommend`·
`similar_performances`는 날짜 확정 여부와 상관없이 콘텐츠로 추천하고, 결과마다
`status`(확정 예정/과거 유사 공연)를 붙인다. `scoring.INCLUDE_PREDICTED_SERIES`(현재
False)가 꺼져 있어서 `series.py`의 반복 시리즈 다음 회차 예측("매년 반복 예상")은
후보에 안 끼워진다(2026-11-12, 사용자 요청 — 아직 확정 안 된 미래 일정을 예상해서
보여주는 걸 빼기로 함). `condition_recommend`·`coldstart_recommend`는 이 스위치들과
무관하게 항상 날짜로 필터한다.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

import series
from common import PROCESSED_DIR, get_logger
from scoring import (
    CONTENT_FIRST_MODE,
    INCLUDE_PREDICTED_SERIES,
    MAX_TOP_K,
    STATUS_CONFIRMED,
    STATUS_HISTORICAL,
    STATUS_PREDICTED,
    cosine_sim_batch,
    final_score,
    is_ended,
    mmr_rerank,
    period_overlaps,
    upcoming_weekend,
)
from vectorize import GENRE_ORDER, NO_GENRE_SIGNAL

logger = get_logger("recommend")

# "가족" 동행이면 관람연령이 이보다 높은(성인 대상) 공연은 조건 추천에서 뺀다.
# 혼자/연인은 나이 제한을 두지 않는다.
FAMILY_MAX_AGE = 12
MMR_POOL_MULTIPLIER = 4  # MMR 재정렬 전, 관련성 상위 몇 배수를 후보 풀로 넘길지


def load_data() -> tuple[pd.DataFrame, np.ndarray]:
    df = pd.read_csv(PROCESSED_DIR / "performances.csv")
    vectors = np.load(PROCESSED_DIR / "performance_vectors.npz")["vectors"]
    if CONTENT_FIRST_MODE and INCLUDE_PREDICTED_SERIES:
        df, vectors = _augment_with_predicted_rows(df, vectors)
    return df, vectors


def _augment_with_predicted_rows(
    df: pd.DataFrame, vectors: np.ndarray, today: date | None = None,
) -> tuple[pd.DataFrame, np.ndarray]:
    """반복 시리즈의 다음 회차 예상 행을 df/vectors 끝에 덧붙인다. 예상 행의 벡터는
    원본 회차(장르·출연진·제목이 사실상 같음)의 벡터를 그대로 재사용한다."""
    today = today or date.today()
    predicted = series.build_predicted_rows(df, today)
    if not predicted:
        return df, vectors
    source_idx = [idx for idx, _ in predicted]
    new_rows = pd.DataFrame([row for _, row in predicted], columns=df.columns)
    df2 = pd.concat([df, new_rows], ignore_index=True)
    vectors2 = np.vstack([vectors, vectors[source_idx]])
    logger.info("반복 시리즈 다음 회차 예측 %d건 추가", len(predicted))
    return df2, vectors2


def _status_for(row: pd.Series, today: date) -> str:
    if row["match_status"] == series.PREDICTED_MATCH_STATUS:
        return STATUS_PREDICTED
    if not is_ended(row["period"], today):
        return STATUS_CONFIRMED
    return STATUS_HISTORICAL


def _with_status(result: pd.DataFrame, today: date | None) -> pd.DataFrame:
    if result.empty:
        return result.assign(status=[])
    today = today or date.today()
    return result.assign(status=result.apply(lambda r: _status_for(r, today), axis=1))


def _eligible_mask(
    df: pd.DataFrame, today: date | None = None, allow_historical: bool = False,
) -> pd.Series:
    today = today or date.today()
    not_unclassified = df["genre"] != "미분류"
    if allow_historical:
        return not_unclassified
    not_ended = ~df["period"].map(lambda p: is_ended(p, today))
    return not_ended & not_unclassified


def build_profile_vector(
    vectors: np.ndarray,
    favorite_genres: list[str] | None = None,
    favorite_idx: list[int] | None = None,
) -> np.ndarray:
    """온보딩 선택(장르)과 찜 목록(공연 인덱스)으로 사용자 프로필 벡터를 만든다.
    둘 다 없으면(또는 선택한 장르가 전부 `NO_GENRE_SIGNAL`이라 신호가 없으면) 영벡터를
    돌려주고, 호출하는 쪽에서 콜드스타트로 처리해야 한다.

    `NO_GENRE_SIGNAL`(예: "스포츠/기타")은 공연 벡터 쪽에서 원-핫 신호를 0으로 죽여둔
    장르다 — 프로필에서까지 그 칸에 1을 넣으면 모든 공연과의 유사도가 똑같이 0이 돼서
    "사용자가 분명히 취향을 골랐는데 인기도 순위(=다른 장르 추천과 우연히 동일)로
    조용히 대체되는" 문제가 생긴다(실제로 "스포츠/기타"를 고르면 "콘서트"와 완전히
    같은 결과가 나오는 버그로 발견됨). 그래서 이 장르는 애초에 원-핫에 반영하지 않는다."""
    parts = []
    if favorite_genres:
        genre_part = np.zeros(vectors.shape[1])
        for g in favorite_genres:
            if g in GENRE_ORDER and g not in NO_GENRE_SIGNAL:
                genre_part[GENRE_ORDER.index(g)] = 1.0
        if np.any(genre_part):
            parts.append(genre_part)
    if favorite_idx:
        parts.append(vectors[favorite_idx].mean(axis=0))
    if not parts:
        return np.zeros(vectors.shape[1])
    return np.mean(parts, axis=0)


def _score_candidates(
    df: pd.DataFrame, vectors: np.ndarray, candidate_idx: list[int], profile: np.ndarray, today: date | None,
) -> dict[int, float]:
    taste_sims = cosine_sim_batch(vectors[candidate_idx], profile)
    return {
        idx: final_score(taste_sims[pos], df.loc[idx, "popularity_score"], df.loc[idx, "period"], today)
        for pos, idx in enumerate(candidate_idx)
    }


def taste_recommend(
    df: pd.DataFrame,
    vectors: np.ndarray,
    favorite_genres: list[str] | None = None,
    favorite_idx: list[int] | None = None,
    top_k: int = 5,
    today: date | None = None,
) -> pd.DataFrame:
    """취향 추천: 온보딩 선택·찜 목록 → 사용자 프로필 벡터, 공연 벡터와 코사인 유사도.

    **지금은 API에서 안 쓴다** — 홈 화면 "추천 공연"은 장르 선택 UI를 없애고
    `bookable_top()`(장르 구분 없는 상위 N개)으로 바뀌었다(2026-11-12, 장르별 후보가
    적으면 엉뚱한 장르로 채워지는 문제가 있어서 폐기, tasks/todo.md 참고). 이 함수는
    오프라인 평가(`evaluate.py`, Precision@5 측정)에서만 계속 쓰이므로 원래 동작
    (`CONTENT_FIRST_MODE`를 따라 과거도 참고용으로 포함)을 그대로 유지한다."""
    top_k = min(top_k, MAX_TOP_K)
    profile = build_profile_vector(vectors, favorite_genres, favorite_idx)
    if not np.any(profile):
        logger.info("취향 정보 없음 — 콜드스타트(이번 주말 인기 공연)로 대체")
        return coldstart_recommend(df, top_k=top_k, today=today)

    candidate_idx = df.index[_eligible_mask(df, today, allow_historical=CONTENT_FIRST_MODE)].tolist()
    relevance = _score_candidates(df, vectors, candidate_idx, profile, today)

    pool = sorted(candidate_idx, key=lambda i: -relevance[i])[: top_k * MMR_POOL_MULTIPLIER]
    # MMR은 "다양성"까지 고려해 뽑는 순서라 뽑힌 순서 그대로 보여주면 관련성이 낮은 게
    # 먼저 나올 수 있다 — 어떤 top_k개를 뽑을지는 MMR이 정하고, 보여주는 순서는 항상
    # 점수가 높은 것부터 나오도록 뽑은 뒤에 다시 점수로 정렬한다.
    selected = mmr_rerank(pool, relevance, vectors, top_k=top_k)
    selected = sorted(selected, key=lambda i: -relevance[i])
    return _with_status(df.loc[selected], today)


def condition_recommend(
    df: pd.DataFrame,
    vectors: np.ndarray,
    start_date: date,
    end_date: date,
    companion: str | None = None,
    max_budget: int | None = None,
    favorite_genres: list[str] | None = None,
    favorite_idx: list[int] | None = None,
    top_k: int = 5,
    today: date | None = None,
) -> pd.DataFrame:
    """조건 추천: 날짜·동행 유형·예산으로 필터 후 취향 점수로 정렬. CONTENT_FIRST_MODE와
    무관하게 항상 날짜로 필터한다 — 특정 날짜를 묻는데 과거 공연을 보여주면 안 된다."""
    top_k = min(top_k, MAX_TOP_K)
    mask = _eligible_mask(df, today, allow_historical=False)
    mask &= df["period"].map(lambda p: period_overlaps(p, start_date, end_date))
    if companion == "가족":
        mask &= df["min_age"].fillna(0) <= FAMILY_MAX_AGE
    if max_budget is not None:
        mask &= df["price_min"].isna() | (df["price_min"] <= max_budget)

    candidate_idx = df.index[mask].tolist()
    if not candidate_idx:
        return _with_status(df.iloc[0:0], today)

    profile = build_profile_vector(vectors, favorite_genres, favorite_idx)
    relevance = _score_candidates(df, vectors, candidate_idx, profile, today)
    top_idx = sorted(candidate_idx, key=lambda i: -relevance[i])[:top_k]
    return _with_status(df.loc[top_idx], today)


def similar_performances(
    df: pd.DataFrame, vectors: np.ndarray, title: str, top_k: int = 5, today: date | None = None,
) -> pd.DataFrame:
    """비슷한 공연: 공연 1건 기준 장르+출연진+줄거리 임베딩 유사도 상위 5."""
    top_k = min(top_k, MAX_TOP_K)
    matches = df.index[df["title"] == title]
    if matches.empty:
        return _with_status(df.iloc[0:0], today)
    query_idx = matches[0]

    mask = _eligible_mask(df, today, allow_historical=CONTENT_FIRST_MODE)
    mask.loc[query_idx] = False  # 자기 자신은 결과에서 제외
    candidate_idx = df.index[mask].tolist()
    if not candidate_idx:
        return _with_status(df.iloc[0:0], today)

    sims = cosine_sim_batch(vectors[candidate_idx], vectors[query_idx])
    ranked = [idx for idx, _ in sorted(zip(candidate_idx, sims), key=lambda t: -t[1])[:top_k]]
    return _with_status(df.loc[ranked], today)


def coldstart_recommend(df: pd.DataFrame, top_k: int = 5, today: date | None = None) -> pd.DataFrame:
    """콜드스타트(온보딩 없이 진입): 이번 주말 인기 공연. 겹치는 예정 공연이 없으면
    전체 예정 공연 중 인기순으로 대체한다. CONTENT_FIRST_MODE와 무관하게 항상 날짜 기반."""
    top_k = min(top_k, MAX_TOP_K)
    today = today or date.today()
    saturday, sunday = upcoming_weekend(today)

    mask = _eligible_mask(df, today, allow_historical=False)
    weekend_mask = mask & df["period"].map(lambda p: period_overlaps(p, saturday, sunday))
    candidates = df[weekend_mask]
    if candidates.empty:
        candidates = df[mask]
    result = candidates.sort_values("popularity_score", ascending=False).head(top_k)
    return _with_status(result, today)


def bookable_top(df: pd.DataFrame, top_k: int = 3, today: date | None = None) -> pd.DataFrame:
    """장르 선택(온보딩) 없이, 지금 예매 가능한 공연 중 상위 top_k개를 보여준다
    (2026-11-12, 사용자 요청 — 장르별 추천은 데이터가 적은 장르에서 엉뚱한 장르로
    채워지는 문제가 있어 폐기하고, 장르 구분 없는 "상위 N개"로 단순화).
    `taste_recommend`와 달리 취향 유사도가 없으므로 인기도·날짜 근접도만으로 점수를
    매긴다(`final_score`의 taste_sim=0) — 과거·미분류는 `_eligible_mask`가 항상
    제외한다."""
    top_k = min(top_k, MAX_TOP_K)
    today = today or date.today()
    mask = _eligible_mask(df, today, allow_historical=False)
    candidates = df[mask]
    if candidates.empty:
        return _with_status(candidates, today)
    scores = candidates.apply(
        lambda r: final_score(0.0, r["popularity_score"], r["period"], today), axis=1,
    )
    top_idx = scores.sort_values(ascending=False).head(top_k).index
    return _with_status(df.loc[top_idx], today)

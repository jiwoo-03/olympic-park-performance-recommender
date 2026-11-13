"""recommend.py 핵심 함수 테스트. 실제 performances.csv 대신 작은 합성 DataFrame을
써서 날짜·장르 조합을 명시적으로 통제한다(실데이터는 매일 배치로 바뀌어서 테스트가
불안정해짐)."""
from datetime import date

import numpy as np
import pandas as pd
import pytest
from recommend import bookable_top, similar_performances
from scoring import STATUS_CONFIRMED, STATUS_HISTORICAL
from vectorize import GENRE_ORDER

TODAY = date(2026, 11, 12)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame([
        {"title": "콘서트 A", "genre": "콘서트", "match_status": "matched",
         "period": "20261115 20261116", "popularity_score": 0.9, "min_age": 0, "price_min": None},
        {"title": "콘서트 B", "genre": "콘서트", "match_status": "matched",
         "period": "20261120 20261121", "popularity_score": 0.5, "min_age": 0, "price_min": None},
        {"title": "콘서트 과거", "genre": "콘서트", "match_status": "matched",
         "period": "20260101 20260102", "popularity_score": 0.99, "min_age": 0, "price_min": None},
        {"title": "미분류 공연", "genre": "미분류", "match_status": "unmatched",
         "period": "20261116 20261117", "popularity_score": 0.99, "min_age": 0, "price_min": None},
        {"title": "뮤지컬 A", "genre": "뮤지컬", "match_status": "matched",
         "period": "20261118 20261119", "popularity_score": 0.3, "min_age": 0, "price_min": None},
    ])


@pytest.fixture
def sample_vectors() -> np.ndarray:
    dim = len(GENRE_ORDER)

    def onehot(genre: str) -> list[float]:
        v = [0.0] * dim
        v[GENRE_ORDER.index(genre)] = 1.0
        return v

    return np.array([
        onehot("콘서트"),  # 0: 콘서트 A
        onehot("콘서트"),  # 1: 콘서트 B
        onehot("콘서트"),  # 2: 콘서트 과거
        onehot("미분류"),  # 3: 미분류 공연
        onehot("뮤지컬"),  # 4: 뮤지컬 A
    ])


class TestBookableTop:
    def test_excludes_historical_and_unclassified(self, sample_df):
        result = bookable_top(sample_df, top_k=3, today=TODAY)
        assert set(result.index) == {0, 1, 4}
        assert "콘서트 과거" not in result["title"].values
        assert "미분류 공연" not in result["title"].values

    def test_all_results_are_confirmed_status(self, sample_df):
        result = bookable_top(sample_df, top_k=3, today=TODAY)
        assert all(result["status"] == STATUS_CONFIRMED)

    def test_ranked_by_final_score_descending(self, sample_df):
        result = bookable_top(sample_df, top_k=3, today=TODAY)
        # final_score는 인기도+날짜근접도만 반영(taste_sim=0) — 인기도 0.9인 "콘서트 A"가
        # 날짜도 더 가까우므로 1위여야 한다.
        assert result.iloc[0]["title"] == "콘서트 A"

    def test_top_k_respected(self, sample_df):
        result = bookable_top(sample_df, top_k=2, today=TODAY)
        assert len(result) == 2

    def test_empty_when_nothing_eligible(self):
        empty_df = pd.DataFrame(columns=["title", "genre", "match_status", "period", "popularity_score"])
        result = bookable_top(empty_df, today=TODAY)
        assert result.empty


class TestSimilarPerformances:
    def test_excludes_self_and_unclassified_but_includes_historical(self, sample_df, sample_vectors):
        # CONTENT_FIRST_MODE=True라서 "비슷한 공연"은 과거도 참고용으로 포함해야 한다.
        result = similar_performances(sample_df, sample_vectors, title="콘서트 A", today=TODAY)
        assert "콘서트 A" not in result["title"].values  # 자기 자신 제외
        assert "미분류 공연" not in result["title"].values  # 미분류는 항상 제외
        assert "콘서트 과거" in result["title"].values  # 과거는 참고용으로 포함
        historical_row = result[result["title"] == "콘서트 과거"].iloc[0]
        assert historical_row["status"] == STATUS_HISTORICAL

    def test_unknown_title_returns_empty(self, sample_df, sample_vectors):
        result = similar_performances(sample_df, sample_vectors, title="존재하지 않는 공연", today=TODAY)
        assert result.empty

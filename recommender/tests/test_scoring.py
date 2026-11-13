"""scoring.py 순수 함수 단위 테스트."""
from datetime import date

import numpy as np
import pytest
from scoring import (
    cosine_sim_batch,
    date_proximity_score,
    final_score,
    is_ended,
    period_overlaps,
)

TODAY = date(2026, 11, 12)


def test_is_ended_past():
    assert is_ended("20260101 20260102", TODAY) is True


def test_is_ended_future():
    assert is_ended("20261201 20261202", TODAY) is False


def test_is_ended_ongoing():
    assert is_ended("20261110 20261115", TODAY) is False


def test_period_overlaps_true():
    assert period_overlaps("20261110 20261115", date(2026, 11, 12), date(2026, 11, 12))


def test_period_overlaps_false():
    assert not period_overlaps("20261001 20261005", date(2026, 11, 12), date(2026, 11, 12))


def test_date_proximity_ongoing_is_max():
    assert date_proximity_score("20261110 20261115", TODAY) == 1.0


def test_date_proximity_far_future_near_zero():
    score = date_proximity_score("20270101 20270102", TODAY)
    assert 0.0 <= score < 0.1


def test_date_proximity_past_is_zero():
    assert date_proximity_score("20260101 20260102", TODAY) == 0.0


def test_final_score_weighted_sum():
    # TASTE_WEIGHT=0.6, POPULARITY_WEIGHT=0.2, DATE_WEIGHT=0.2 (scoring.py 상수)
    score = final_score(taste_sim=1.0, popularity_score=1.0, period="20261110 20261115", today=TODAY)
    assert score == pytest.approx(1.0)


def test_cosine_sim_batch_zero_query_returns_zeros():
    matrix = np.array([[1.0, 0.0], [0.0, 1.0]])
    query = np.zeros(2)
    result = cosine_sim_batch(matrix, query)
    assert np.all(result == 0.0)


def test_cosine_sim_batch_matches_exact():
    matrix = np.array([[1.0, 0.0], [0.0, 1.0]])
    query = np.array([1.0, 0.0])
    result = cosine_sim_batch(matrix, query)
    assert result[0] == pytest.approx(1.0)
    assert result[1] == pytest.approx(0.0)

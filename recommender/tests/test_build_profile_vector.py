"""build_profile_vector()의 NO_GENRE_SIGNAL 처리 회귀 테스트.

2026-11-12에 실제로 터졌던 버그: "스포츠/기타"를 선택해도 vectorize.py가 그 장르의
원-핫 신호를 0으로 죽여놓는데, build_profile_vector는 그걸 모르고 1을 넣어서 모든
공연과의 유사도가 0이 돼 "콘서트"와 완전히 동일한 결과가 나왔다. 이 테스트는 그
두 모듈의 기준이 계속 일치하는지 지킨다."""
import numpy as np
from recommend import build_profile_vector
from vectorize import GENRE_ORDER, NO_GENRE_SIGNAL


def _dummy_vectors(n_rows: int = 1) -> np.ndarray:
    return np.zeros((n_rows, len(GENRE_ORDER)))


def test_no_genre_signal_genres_produce_zero_profile():
    for genre in NO_GENRE_SIGNAL:
        profile = build_profile_vector(_dummy_vectors(), favorite_genres=[genre])
        assert not np.any(profile), f"{genre}는 NO_GENRE_SIGNAL인데 0벡터가 아님"


def test_normal_genres_produce_nonzero_profile_at_correct_index():
    for genre in GENRE_ORDER:
        if genre in NO_GENRE_SIGNAL or genre == "미분류":
            continue
        profile = build_profile_vector(_dummy_vectors(), favorite_genres=[genre])
        assert profile[GENRE_ORDER.index(genre)] == 1.0
        assert np.sum(profile) == 1.0


def test_no_favorites_at_all_returns_zero_vector():
    profile = build_profile_vector(_dummy_vectors(), favorite_genres=None, favorite_idx=None)
    assert not np.any(profile)


def test_favorite_idx_averages_vectors():
    vectors = np.array([[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
    profile = build_profile_vector(vectors, favorite_genres=None, favorite_idx=[0, 1])
    assert profile[0] == 0.5
    assert profile[1] == 0.5

"""classify_genre() 회귀 테스트.

2026-11-12에 실제로 터졌던 버그 2건을 고정한다:
1. KOPIS 매칭이 안 된 공연은 제목에 "콘서트"가 있어도 전부 "미분류"로 떨어졌음
   → 매칭 안 된 행 전용 키워드 폴백으로 구제.
2. 1번을 고치면서 처음엔 매칭된 공연에도 똑같이 적용했다가, KOPIS가 이미 "클래식"
   으로 정확히 분류해둔 공연("OOO 신년 콘서트")까지 덮어써버리는 회귀가 생겼음
   → 매칭 안 된 행(kopis_genre가 빈 경우)에만 적용하도록 범위를 좁혀서 해결.
   이 테스트는 그 회귀가 다시 생기지 않는지 지킨다.
"""
from normalize_and_clean import classify_genre


def test_unmatched_concert_title_is_rescued():
    assert classify_genre("2026 정승환 10주년 콘서트", "") == "콘서트"


def test_unmatched_with_no_keyword_stays_unclassified():
    assert classify_genre("아무 의미 없는 제목", "") == "미분류"


def test_matched_kopis_genre_is_not_overridden_by_concert_keyword():
    # 회귀 테스트: KOPIS가 이미 "클래식"으로 분류했으면, 제목에 "콘서트"가 있어도
    # 그대로 "클래식"이어야 한다(2026-11-12에 18건→9건으로 반토막 났던 버그).
    assert classify_genre("2026 신년 음악회 콘서트", "서양음악(클래식)") == "클래식"


def test_matched_kopis_genre_mapping():
    assert classify_genre("아무 제목", "대중음악") == "콘서트"
    assert classify_genre("아무 제목", "뮤지컬") == "뮤지컬"
    assert classify_genre("아무 제목", "아동") == "어린이"


def test_title_keyword_still_overrides_matched_for_festival_and_kids():
    # 페스티벌/어린이는 기존부터 매칭 공연에도 제목 키워드가 우선 적용되는 설계라
    # 그대로 유지돼야 한다(콘서트 폴백과 다르게 범위를 좁히지 않은 부분).
    assert classify_genre("2026 OO 페스티벌", "대중음악") == "페스티벌"
    assert classify_genre("어린이 OO 공연", "대중음악") == "어린이"


def test_matched_unmapped_kopis_genre_falls_back_to_sports_etc():
    assert classify_genre("아무 제목", "무용(서양/한국)") == "스포츠/기타"

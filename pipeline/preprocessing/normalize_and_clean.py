"""장르 통일, 요금·관람연령 정규화 → performances 정제 테이블 생성.

입력: data/processed/performances_matched.json (match_performances.py 산출물)
출력: data/processed/performances.csv

- 장르: KOPIS genrenm(세부 장르) + 제목 키워드를 콘서트·뮤지컬·클래식·페스티벌·
  어린이·스포츠/기타 6종으로 통일한다. KOPIS 매칭이 안 된 공연은 "미분류"로 남기고
  수기 라벨링 대상으로 표시한다(워크플로우 문서 7장 리스크 대응과 동일한 방침).
- 요금: "SR석 154,000원, R석 143,000원" 같은 문자열에서 숫자를 모두 추출해
  최저가/최고가로 정규화한다.
- 관람연령: "만 8세 이상"류 문자열에서 최소 나이를 추출한다. "전체관람가"는 0세.
- 장소: `venue`(KSPO 쪽 SPATIAL_COVERAGE/EVENT_SITE)에 흩어진 표기를 `venue_normalized`로
  정규화한다. 미분류 공연도 장소 기준 추천(같은 장소의 다른 공연)에 쓸 수 있도록 매칭 여부와
  무관하게 전체 행에 적용한다.
- 인기도: `data/raw/kopis/boxoffice.json`(collect_kopis_boxoffice.py 산출물, 최근 12개월
  전국 랭킹 상위 50건)을 `kopis_mt20id`로 조인해 `popularity_score`를 만든다. 랭킹에 한 번도
  안 잡힌 공연(미분류 전부 포함)은 0.0 — 전국 상위 50위 밖이라는 뜻이지 비호감이라는 뜻은
  아니므로, 이후 추천 로직에서 "모른다"가 아니라 "낮다"로 다루면 된다.
- 기간: 매칭된 공연은 KSPO 기간 대신 **KOPIS 기간을 우선** 쓴다. 두 소스가 다른 646건
  중 23건(3.6%)에서 날짜가 달랐는데, 종료일은 KOPIS가 KSPO보다 짧은 경우가 한 번도
  없었다(공연 연장을 KSPO 대관정보가 못 따라가는 경우가 있는 것으로 추정 — "백 번째
  리뷰" 사례, tasks/verification.md [2026-11-12] 참고). 그래서 "KOPIS 우선"과 "둘 중
  늦은 종료일"은 실질적으로 같은 결과를 내고, 더 단순한 "KOPIS 우선"으로 정했다.
- 예매처 링크: KOPIS의 `relates`(예매처명+URL 목록)를 `ticket_links` 컬럼에 JSON
  문자열로 담는다. CLAUDE.md 제약("예매는 직접 처리하지 않고 외부 예매처 링크로 연결")
  때문에 공연 상세 화면의 핵심 기능이라 빠뜨리면 안 된다(frontend 6단계 설계 중 발견한
  누락, tasks/todo.md 참고).
"""
from __future__ import annotations

import json
import re

import pandas as pd

from common import get_logger, load_processed_json, load_raw_json, save_processed_csv

logger = get_logger("normalize_and_clean")

GENRE_KEYWORDS_BY_TITLE = [
    ("페스티벌", ["페스티벌", "festival", "FESTIVAL"]),
    ("어린이", ["어린이", "키즈", "가족", "동화"]),
]

# kopis_genre가 아예 없는(= KOPIS 미매칭) 공연에 한해서만 적용하는 제목 키워드 보강
# 규칙("미분류" 대신 분류). KOPIS가 이미 장르를 알고 있는 매칭 공연에는 절대 적용하지
# 않는다 — 처음엔 GENRE_KEYWORDS_BY_TITLE에 같이 넣었다가, "OOO 신년 콘서트"처럼
# KOPIS가 이미 "클래식"으로 정확히 분류해둔 매칭 공연까지 제목의 "콘서트" 때문에
# 일반 콘서트로 잘못 덮어쓰는 회귀가 생겨서 분리했다(2026-11-12, 실측: 클래식
# 18건→9건으로 반토막 나는 걸 발견해서 되돌림). KOPIS 매칭이 안 된 공연은 장르
# 정보가 아예 없으니 덮어쓸 "정답"이 없어 이 규칙만 안전하게 적용 가능하다.
UNMATCHED_FALLBACK_KEYWORDS_BY_TITLE = [
    ("콘서트", ["콘서트", "concert", "CONCERT"]),
]

GENRE_MAP_FROM_KOPIS = {
    "대중음악": "콘서트",
    "뮤지컬": "뮤지컬",
    "서양음악(클래식)": "클래식",
    "한국음악(국악)": "클래식",
    "아동": "어린이",
}

PRICE_NUM_PATTERN = re.compile(r"([\d,]+)\s*원")
AGE_NUM_PATTERN = re.compile(r"(\d+)\s*세")
KOPIS_DATE_PATTERN = re.compile(r"(\d{4})\.(\d{2})\.(\d{2})")


def resolve_period(row: dict) -> str:
    """매칭된 공연은 KOPIS 쪽 기간을 우선 쓴다(위 모듈 설명 "기간" 참고). KOPIS 날짜가
    없거나 형식이 안 맞으면 KSPO 기간으로 그대로 둔다."""
    if row["match_status"] != "matched":
        return row["kspo_period"]
    from_m = KOPIS_DATE_PATTERN.match(row.get("kopis_prfpdfrom", "") or "")
    to_m = KOPIS_DATE_PATTERN.match(row.get("kopis_prfpdto", "") or "")
    if not from_m or not to_m:
        return row["kspo_period"]
    start = f"{from_m.group(1)}{from_m.group(2)}{from_m.group(3)}"
    end = f"{to_m.group(1)}{to_m.group(2)}{to_m.group(3)}"
    return f"{start} {end}"

# 순서가 우선순위다 — "티켓링크 라이브 아레나 (구 올림픽공원 핸드볼경기장)"처럼 긴 변형
# 표기가 많아 부분 문자열 포함 검사로 정규화한다. 좁은 키워드(핸드볼경기장)를 "올림픽홀" 같은
# 넓은 키워드보다 먼저 검사해야 오매칭이 안 생긴다.
VENUE_NORMALIZE_RULES: list[tuple[str, list[str]]] = [
    ("핸드볼경기장", ["핸드볼", "티켓링크"]),  # "티켓링크 라이브 아레나"는 핸드볼경기장의 개칭
    ("KSPO DOME", ["KSPODOME", "체조경기장"]),  # "체조경기장"은 KSPO DOME의 옛/별칭
    ("우리금융아트홀", ["우리금융아트", "우리금용아트홀"]),  # 뒤쪽은 "금용" 오타 표기 대응
    ("수변무대", ["수변무대"]),
    ("88잔디마당", ["88잔디마당"]),
    ("K-아트홀", ["K-아트홀", "K아트홀"]),
    ("뮤즈라이브", ["뮤즈라이브"]),
    ("올림픽홀", ["올림픽홀"]),
]


def normalize_venue(venue: str) -> str:
    v = (venue or "").upper().replace(" ", "")
    for canonical, keywords in VENUE_NORMALIZE_RULES:
        if any(kw.upper().replace(" ", "") in v for kw in keywords):
            return canonical
    return "기타" if venue else ""


def classify_genre(title: str, kopis_genre: str) -> str:
    for genre, keywords in GENRE_KEYWORDS_BY_TITLE:
        if any(kw in title for kw in keywords):
            return genre
    if kopis_genre in GENRE_MAP_FROM_KOPIS:
        return GENRE_MAP_FROM_KOPIS[kopis_genre]
    if not kopis_genre:
        for genre, keywords in UNMATCHED_FALLBACK_KEYWORDS_BY_TITLE:
            if any(kw in title for kw in keywords):
                return genre
        return "미분류"
    return "스포츠/기타"


def parse_price_range(pcseguidance: str) -> tuple[int | None, int | None]:
    if not pcseguidance:
        return None, None
    nums = [int(n.replace(",", "")) for n in PRICE_NUM_PATTERN.findall(pcseguidance)]
    if not nums:
        return None, None
    return min(nums), max(nums)


def build_popularity_map() -> dict[str, float]:
    """mt20id -> popularity_score(0~1). 랭킹(rnum)이 낮을수록(=1위에 가까울수록) 높은 점수.

    같은 공연이 여러 달 랭킹에 들면 그중 가장 좋았던(가장 낮은) 순위를 쓴다.
    """
    boxoffice = load_raw_json("kopis", "boxoffice.json")
    best_rank: dict[str, int] = {}
    for entry in boxoffice:
        mt20id = entry.get("mt20id", "")
        rank = int(entry.get("rnum", 0) or 0)
        if not mt20id or rank <= 0:
            continue
        if mt20id not in best_rank or rank < best_rank[mt20id]:
            best_rank[mt20id] = rank
    return {mt20id: round((51 - rank) / 50, 4) for mt20id, rank in best_rank.items()}


def parse_min_age(prfage: str) -> int | None:
    if not prfage:
        return None
    if "전체" in prfage:
        return 0
    m = AGE_NUM_PATTERN.search(prfage)
    return int(m.group(1)) if m else None


def main() -> None:
    data = load_processed_json("performances_matched.json")
    rows = data["results"]
    logger.info("정제 대상 %d건 (매칭 요약: %s)", len(rows), data["summary"])

    popularity_map = build_popularity_map()
    logger.info("박스오피스 인기도 매칭 가능 공연 %d건", len(popularity_map))

    records = []
    for row in rows:
        title = row["kspo_title"]
        kopis_genre = row.get("kopis_genrenm", "")
        genre = classify_genre(title, kopis_genre)
        price_min, price_max = parse_price_range(row.get("kopis_pcseguidance", ""))
        min_age = parse_min_age(row.get("kopis_prfage", ""))
        venue_normalized = normalize_venue(row["kspo_venue"])
        mt20id = row.get("kopis_mt20id", "")
        popularity_score = popularity_map.get(mt20id, 0.0)

        records.append({
            "title": title,
            "period": resolve_period(row),
            "venue": row["kspo_venue"],
            "venue_normalized": venue_normalized,
            "match_status": row["match_status"],
            "genre": genre,
            "kopis_mt20id": mt20id,
            "cast": row.get("kopis_prfcast", ""),
            "synopsis": row.get("kopis_sty", ""),
            "min_age": min_age,
            "price_min": price_min,
            "price_max": price_max,
            "popularity_score": popularity_score,
            "poster": row.get("kopis_poster", ""),
            "venue_kopis": row.get("kopis_fcltynm", ""),
            "ticket_links": json.dumps(row.get("kopis_relates", []), ensure_ascii=False),
        })

    df = pd.DataFrame.from_records(records)
    path = save_processed_csv(df, "performances.csv")
    logger.info("저장 완료: %s (%d행)", path, len(df))
    logger.info("장르 분포:\n%s", df["genre"].value_counts().to_string())
    logger.info("장소 정규화 분포:\n%s", df["venue_normalized"].value_counts().to_string())
    logger.info("인기도 신호 보유 공연: %d건 (popularity_score > 0)", (df["popularity_score"] > 0).sum())


if __name__ == "__main__":
    main()

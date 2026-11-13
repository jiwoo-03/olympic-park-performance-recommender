"""KSPO(한국체육산업개발) 공연과 KOPIS 공연을 공연명+기간+장소로 매칭한다.

- KSPO 측 "원본 카탈로그"로는 data/raw/integrated_performance/kspo_filtered.json
  (문체부 통합 공연정보 API 중 한국체육산업개발 제공 행만 모아둔 것)을 쓴다.
  data.go.kr의 KSPO 전용 "올림픽공원 대관정보" API(meta12/getKSCD0803)는 수집
  단계에서 401을 반환해 아직 쓸 수 없다 (pipeline/collection/REPORT.md 참고).
- KOPIS 측은 이미 올림픽공원 시설코드(FC001247)로 필터링된 목록이라 그 자체로
  "올림픽공원에서 열린 공연" 집합이다. 매칭의 목적은 KSPO 카탈로그 각 행에 KOPIS의
  장르·출연진·줄거리·요금·관람연령 같은 콘텐츠 특성을 붙이는 것이다.
- 매칭 키: 공연명(공백·특수문자 제거) 완전일치 → 실패 시 rapidfuzz 유사도(>=85) →
  기간 겹침으로 교차 검증. 기간이 겹치지 않으면 "제목만 비슷함"으로 따로 표시해
  오매칭을 피한다.
"""
from __future__ import annotations

import re
from datetime import date

from rapidfuzz import fuzz, process

from common import get_logger, load_raw_json, normalize_title, save_processed_json

logger = get_logger("match_performances")

FUZZY_SCORE_CUTOFF = 70  # 기간 겹침 교차 검증이 안전망이라 완전일치보다 느슨하게 둔다

# 한국체육산업개발이 넘기는 PERIOD는 실제로는 "YYYYMMDD YYYYMMDD"(공백 구분, 하이픈 없음)다.
# 다른 9개 기관은 "YYYY-MM-DD ~ YYYY-MM-DD" 형태라 두 패턴 모두 지원한다.
_PERIOD_PATTERNS = [
    re.compile(r"(\d{4})-(\d{2})-(\d{2})\s*~\s*(\d{4})-(\d{2})-(\d{2})"),
    re.compile(r"(\d{4})(\d{2})(\d{2})\s+(\d{4})(\d{2})(\d{2})"),
]

# 실제 공연이 아니라 대관 운영 상태를 나타내는 제목(한국체육산업개발 데이터에 다수 섞여 있음).
NOISE_TITLE_KEYWORDS = [
    "준비대관", "예약완료", "철거대관", "무대점검", "시설물 작업", "내부공사",
    "행사철거", "원상복구", "대관준비", "리허설",
]


def is_noise_title(title: str) -> bool:
    return any(kw in (title or "") for kw in NOISE_TITLE_KEYWORDS)


def _parse_kspo_period(period_str: str) -> tuple[date | None, date | None]:
    for pattern in _PERIOD_PATTERNS:
        m = pattern.search(period_str or "")
        if m:
            y1, m1, d1, y2, m2, d2 = map(int, m.groups())
            try:
                return date(y1, m1, d1), date(y2, m2, d2)
            except ValueError:
                return None, None
    return None, None


def _parse_kopis_date(date_str: str) -> date | None:
    # "2026.12.18"
    m = re.match(r"\s*(\d{4})\.(\d{2})\.(\d{2})", date_str or "")
    if not m:
        return None
    y, mo, d = map(int, m.groups())
    return date(y, mo, d)


def _periods_overlap(a_from: date | None, a_to: date | None, b_from: date | None, b_to: date | None) -> bool:
    if not all([a_from, a_to, b_from, b_to]):
        return False
    return a_from <= b_to and b_from <= a_to


def main() -> None:
    kspo_items_all = load_raw_json("integrated_performance", "kspo_filtered.json")["items"]
    kopis_items = load_raw_json("kopis", "performance_detail.json")

    kspo_items = [it for it in kspo_items_all if not is_noise_title(it.get("TITLE", ""))]
    noise_count = len(kspo_items_all) - len(kspo_items)
    logger.info(
        "KSPO(통합 공연정보) %d건 중 대관 운영성 제목(준비대관 등) %d건 제외 -> %d건 / KOPIS(올림픽공원) %d건",
        len(kspo_items_all), noise_count, len(kspo_items), len(kopis_items),
    )

    kopis_by_norm_title: dict[str, list[dict]] = {}
    kopis_titles_norm: list[str] = []
    for kopis in kopis_items:
        norm = normalize_title(kopis.get("prfnm", ""))
        kopis_by_norm_title.setdefault(norm, []).append(kopis)
        kopis_titles_norm.append(norm)

    results = []
    match_count = 0
    title_only_count = 0

    for kspo in kspo_items:
        kspo_title = kspo.get("TITLE", "")
        kspo_norm = normalize_title(kspo_title)
        k_from, k_to = _parse_kspo_period(kspo.get("PERIOD", ""))

        # 제목이 같아도(연례 공연 재공연 등) 다른 해 레코드일 수 있으므로, 유사 후보를
        # 점수 상위 몇 개까지 모아 그중 기간이 겹치는 것을 찾는다 — top-1만 보면 오래된
        # 동명 공연이 올해 공연보다 문자열이 더 비슷해 정답을 가리는 경우가 생긴다.
        exact_candidates = [(kspo_norm, 100.0, c) for c in kopis_by_norm_title.get(kspo_norm, [])]
        fuzzy_matches = (
            process.extract(kspo_norm, kopis_titles_norm, scorer=fuzz.ratio, score_cutoff=FUZZY_SCORE_CUTOFF, limit=5)
            if kopis_titles_norm else []
        )
        fuzzy_candidates = [
            (norm, score, c)
            for norm, score, _ in fuzzy_matches
            for c in kopis_by_norm_title.get(norm, [])
        ]
        ranked_candidates = sorted(exact_candidates + fuzzy_candidates, key=lambda t: -t[1])
        any_candidates = bool(ranked_candidates)

        matched_kopis = None
        match_method = None
        for norm, score, cand in ranked_candidates:
            c_from = _parse_kopis_date(cand.get("prfpdfrom", ""))
            c_to = _parse_kopis_date(cand.get("prfpdto", ""))
            if _periods_overlap(k_from, k_to, c_from, c_to):
                matched_kopis = cand
                match_method = "exact_title" if norm == kspo_norm else f"fuzzy({score:.0f})"
                break

        if matched_kopis:
            match_count += 1
            results.append({
                "kspo_title": kspo_title,
                "kspo_period": kspo.get("PERIOD", ""),
                "kspo_venue": kspo.get("SPATIAL_COVERAGE", "") or kspo.get("EVENT_SITE", ""),
                "match_status": "matched",
                "match_method": match_method,
                "kopis_mt20id": matched_kopis.get("mt20id", ""),
                "kopis_prfnm": matched_kopis.get("prfnm", ""),
                "kopis_genrenm": matched_kopis.get("genrenm", ""),
                "kopis_prfcast": matched_kopis.get("prfcast", ""),
                "kopis_prfage": matched_kopis.get("prfage", ""),
                "kopis_pcseguidance": matched_kopis.get("pcseguidance", ""),
                "kopis_poster": matched_kopis.get("poster", ""),
                "kopis_fcltynm": matched_kopis.get("fcltynm", ""),
                "kopis_relates": matched_kopis.get("relates", []),
                "kopis_sty": matched_kopis.get("sty", ""),
                "kopis_prfpdfrom": matched_kopis.get("prfpdfrom", ""),
                "kopis_prfpdto": matched_kopis.get("prfpdto", ""),
            })
        elif any_candidates:
            title_only_count += 1
            results.append({
                "kspo_title": kspo_title,
                "kspo_period": kspo.get("PERIOD", ""),
                "kspo_venue": kspo.get("SPATIAL_COVERAGE", "") or kspo.get("EVENT_SITE", ""),
                "match_status": "title_only_mismatch_period",
                "match_method": match_method,
            })
        else:
            results.append({
                "kspo_title": kspo_title,
                "kspo_period": kspo.get("PERIOD", ""),
                "kspo_venue": kspo.get("SPATIAL_COVERAGE", "") or kspo.get("EVENT_SITE", ""),
                "match_status": "unmatched",
                "match_method": None,
            })

    total = len(kspo_items)
    summary = {
        "total_kspo_raw": len(kspo_items_all),
        "noise_title_excluded": noise_count,
        "total_kspo": total,
        "matched": match_count,
        "title_only_mismatch_period": title_only_count,
        "unmatched": total - match_count - title_only_count,
        "match_rate": round(match_count / total, 4) if total else 0.0,
    }
    logger.info("매칭 결과: %s", summary)

    save_processed_json({"summary": summary, "results": results}, "performances_matched.json")


if __name__ == "__main__":
    main()

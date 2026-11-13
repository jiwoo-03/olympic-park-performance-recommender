"""문화체육관광부_공연 정보(통합) API 수집 (data.go.kr 15056881, 실제 엔드포인트는
문화공공데이터광장 API_CCA_144).

이 API는 10개 기관(한국체육산업개발 포함)의 공연을 한 목록에 섞어 반환하고 기관으로
거르는 서버 파라미터가 없다. 전체 약 5~6만 건을 모두 저장하면 raw 용량이 과도해지므로,
모든 페이지를 순회하되 CNTC_INSTT_NM(제공기관)에 "한국체육산업개발"이 포함된 행만
저장한다 — 장르 통일·정제 같은 가공은 하지 않으므로 여전히 "원본" 데이터다.
"""
from __future__ import annotations

import time
import xml.etree.ElementTree as ET

from common import PERFORMANCE_INTEGRATED_API_KEY, get_logger, http_session, save_raw_json

logger = get_logger("collect_integrated_performance")

URL = "https://api.kcisa.kr/openapi/API_CCA_144/request"
ROWS_PER_PAGE = 1000
INSTITUTION_FILTER = "한국체육산업개발"
PAGE_DELAY_SEC = 0.3


def _parse_items(xml_text: str) -> tuple[list[dict], int]:
    root = ET.fromstring(xml_text)
    result_code = root.findtext("header/resultCode")
    if result_code != "0000":
        raise RuntimeError(f"API_CCA_144 오류: {root.findtext('header/resultMsg')}")
    total_count = int(root.findtext("body/totalCount", "0"))
    items = []
    for item in root.findall("body/items/item"):
        items.append({child.tag: (child.text or "").strip() for child in item})
    return items, total_count


def main() -> None:
    if not PERFORMANCE_INTEGRATED_API_KEY:
        logger.error("PERFORMANCE_INTEGRATED_API_KEY가 .env에 없습니다.")
        return

    session = http_session()
    matched: list[dict] = []
    page = 1
    total_count = None
    total_seen = 0

    while True:
        resp = session.get(
            URL,
            params={
                "serviceKey": PERFORMANCE_INTEGRATED_API_KEY,
                "numOfRows": ROWS_PER_PAGE,
                "pageNo": page,
            },
            timeout=60,
        )
        resp.raise_for_status()
        items, total_count = _parse_items(resp.text)
        if not items:
            break
        total_seen += len(items)
        page_matched = [it for it in items if INSTITUTION_FILTER in it.get("CNTC_INSTT_NM", "")]
        matched.extend(page_matched)
        logger.info(
            "page=%d 조회 %d건 (누적 %d/%d), 한국체육산업개발 매칭 %d건",
            page, len(items), total_seen, total_count, len(page_matched),
        )
        if total_seen >= total_count:
            break
        page += 1
        time.sleep(PAGE_DELAY_SEC)

    path = save_raw_json(
        "integrated_performance",
        {
            "source": "문화체육관광부_공연 정보(통합) API (API_CCA_144)",
            "institution_filter": INSTITUTION_FILTER,
            "total_count_all_institutions": total_count,
            "matched_count": len(matched),
            "items": matched,
        },
        "kspo_filtered.json",
    )
    logger.info("저장 완료: %s (매칭 %d건 / 전체 %d건)", path, len(matched), total_count)
    return True


if __name__ == "__main__":
    main()

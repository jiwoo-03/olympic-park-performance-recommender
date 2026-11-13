"""한국체육산업개발주식회사_올림픽공원 차량 입출차 및 날씨 정보 (data.go.kr 15164822) 수집.

실제 엔드포인트는 문화공공데이터광장 API_CPM_009 (연계형 LINK API).
응답 스키마가 API_CCA_144와 동일한 KCISA 게이트웨이 포맷(header/body/items/item)이라
항목을 고정 필드로 파싱하지 않고 태그를 그대로 dict로 풀어서 저장한다 — 어떤 필드가
오는지는 EDA 단계에서 확인한다.

주의: 이 스크립트 작성 시점에는 504 Gateway Timeout이 반환된다 (파라미터는 공식
명세와 동일: serviceKey/numOfRows/pageNo). 제공기관 쪽 백엔드 장애로 추정된다.
REPORT.md의 "알려진 이슈" 참고.
"""
from __future__ import annotations

import time
import xml.etree.ElementTree as ET

from common import KSPO_PARKING_WEATHER_API_KEY, get_logger, http_session, save_raw_json

logger = get_logger("collect_parking_weather")

URL = "https://api.kcisa.kr/openapi/API_CPM_009/request"
ROWS_PER_PAGE = 100
PAGE_DELAY_SEC = 0.3


def _parse_items(xml_text: str) -> tuple[list[dict], int]:
    root = ET.fromstring(xml_text)
    result_code = root.findtext("header/resultCode")
    if result_code != "0000":
        raise RuntimeError(f"오류 응답: {root.findtext('header/resultMsg')}")
    total_count = int(root.findtext("body/totalCount", "0"))
    items = [
        {child.tag: (child.text or "").strip() for child in item}
        for item in root.findall("body/items/item")
    ]
    return items, total_count


def main() -> bool:
    if not KSPO_PARKING_WEATHER_API_KEY:
        logger.error("KSPO_PARKING_WEATHER_API_KEY가 .env에 없습니다.")
        return False

    session = http_session(total_retries=2)
    all_items: list[dict] = []
    page = 1

    try:
        while True:
            resp = session.get(
                URL,
                params={
                    "serviceKey": KSPO_PARKING_WEATHER_API_KEY,
                    "numOfRows": ROWS_PER_PAGE,
                    "pageNo": page,
                },
                timeout=30,
            )
            if resp.status_code != 200:
                logger.error("HTTP %d: %s", resp.status_code, resp.text[:300])
                return False
            items, total_count = _parse_items(resp.text)
            all_items.extend(items)
            logger.info("page=%d -> %d건 (누적 %d/%d)", page, len(items), len(all_items), total_count)
            if len(items) < ROWS_PER_PAGE or len(all_items) >= total_count:
                break
            page += 1
            time.sleep(PAGE_DELAY_SEC)
    except Exception as exc:  # noqa: BLE001
        logger.error("수집 실패: %s", exc)
        return False

    path = save_raw_json("parking_weather", all_items, "parking_weather.json")
    logger.info("저장 완료: %s (%d건)", path, len(all_items))
    return True


if __name__ == "__main__":
    main()

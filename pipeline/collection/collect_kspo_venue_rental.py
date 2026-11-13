"""한국체육산업개발주식회사_올림픽공원 대관정보 (data.go.kr 15015212) 수집.

실제 엔드포인트는 문화공공데이터광장 meta12/getKSCD0803 (연계형 LINK API).
행사명·대관기간·장소 등을 제공한다.

주의: 이 스크립트 작성 시점에는 발급받은 서비스키로 호출하면 401 Unauthorized가
반환된다 (파라미터는 공식 명세와 동일하게 맞췄음 — serviceKey/numOfRows/pageNo).
활용신청이 아직 전체 승인되지 않았거나 레거시 게이트웨이 쪽 키 발급이 지연된 것으로
추정된다. REPORT.md의 "알려진 이슈" 참고. 승인 후에는 별도 수정 없이 바로 동작해야
한다.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from common import KSPO_PERFORMANCE_API_KEY, get_logger, http_session, save_raw_json

logger = get_logger("collect_kspo_venue_rental")

URL = "https://api.kcisa.kr/openapi/service/rest/meta12/getKSCD0803"
ROWS_PER_PAGE = 100


def _parse_items(xml_text: str) -> tuple[list[dict], int]:
    root = ET.fromstring(xml_text)
    result_code = root.findtext("header/resultCode") or root.findtext("cmmMsgHeader/returnReasonCode")
    if result_code not in (None, "0000", "00"):
        raise RuntimeError(f"오류 응답: {xml_text[:300]}")
    total_count = int(root.findtext("body/totalCount", "0"))
    items = [
        {child.tag: (child.text or "").strip() for child in item}
        for item in root.findall("body/items/item")
    ]
    return items, total_count


def main() -> bool:
    if not KSPO_PERFORMANCE_API_KEY:
        logger.error("KSPO_PERFORMANCE_API_KEY가 .env에 없습니다.")
        return False

    session = http_session(total_retries=2)
    all_items: list[dict] = []
    page = 1

    try:
        while True:
            resp = session.get(
                URL,
                params={
                    "serviceKey": KSPO_PERFORMANCE_API_KEY,
                    "numOfRows": ROWS_PER_PAGE,
                    "pageNo": page,
                },
                timeout=30,
            )
            if resp.status_code != 200:
                logger.error(
                    "HTTP %d: %s (활용신청 승인 상태를 data.go.kr 마이페이지에서 확인할 것)",
                    resp.status_code, resp.text[:300],
                )
                return False
            items, total_count = _parse_items(resp.text)
            all_items.extend(items)
            logger.info("page=%d -> %d건 (누적 %d/%d)", page, len(items), len(all_items), total_count)
            if len(items) < ROWS_PER_PAGE or len(all_items) >= total_count:
                break
            page += 1
    except Exception as exc:  # noqa: BLE001
        logger.error("수집 실패: %s", exc)
        return False

    path = save_raw_json("kspo_venue_rental", all_items, "venue_rental.json")
    logger.info("저장 완료: %s (%d건)", path, len(all_items))
    return True


if __name__ == "__main__":
    main()

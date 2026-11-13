"""KOPIS 박스오피스(예매 현황판) API 수집 — 추천 모델의 인기도 신호.

- 공연 상세(`pblprfr`)에는 예매상황판에 해당하는 필드가 없어서(`visit`은 내한공연
  여부일 뿐 인기도가 아님), 별도 박스오피스 API(`/boxoffice`)로 전국 랭킹 상위 50건을
  받아온다. 응답의 mt20id가 `performance_detail.json`의 mt20id와 같은 키라 전처리
  단계에서 추가 매칭 없이 바로 조인할 수 있다.
- 이 API는 기간을 최대 31일까지만 받는다("05 최대 31일까지 조회가능합니다" 오류로 확인됨).
  그래서 최근 N개월을 월 단위로 순회해 호출한다.
- 전국 랭킹이라 올림픽공원 외 공연도 섞여 들어오지만, 전처리 단계에서 우리 쪽
  kopis_mt20id와 겹치는 것만 걸러 쓴다.
"""
from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta

from common import KOPIS_API_KEY, get_logger, http_session, save_raw_json

logger = get_logger("collect_kopis_boxoffice")

BASE_URL = "http://www.kopis.or.kr/openApi/restful/boxoffice"
MAX_ROWS = 50
MONTHS_BACK = 12
CALL_DELAY_SEC = 0.2


def _month_ranges(months_back: int) -> list[tuple[str, str]]:
    """오늘이 속한 달부터 거슬러 올라가며 (YYYYMMDD, YYYYMMDD) 월 구간을 만든다."""
    ranges = []
    year, month = date.today().year, date.today().month
    for _ in range(months_back):
        start = date(year, month, 1)
        end = (date(year + (month == 12), (month % 12) + 1, 1)) - timedelta(days=1)
        ranges.append((start.strftime("%Y%m%d"), end.strftime("%Y%m%d")))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return ranges


def _parse_boxoffice_xml(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    if root.find("db/returncode") is not None:
        raise RuntimeError(f"KOPIS 박스오피스 오류 응답: {xml_text[:200]}")
    return [
        {child.tag: (child.text or "").strip() for child in boxof}
        for boxof in root.findall("boxof")
    ]


def fetch_boxoffice(session, stdate: str, eddate: str) -> list[dict]:
    resp = session.get(
        BASE_URL,
        params={"service": KOPIS_API_KEY, "stdate": stdate, "eddate": eddate, "rows": MAX_ROWS},
        timeout=30,
    )
    resp.raise_for_status()
    return _parse_boxoffice_xml(resp.text)


def main() -> None:
    if not KOPIS_API_KEY:
        logger.error("KOPIS_API_KEY가 .env에 없습니다.")
        return

    session = http_session()
    all_entries: list[dict] = []
    failed_months = 0
    for stdate, eddate in _month_ranges(MONTHS_BACK):
        try:
            entries = fetch_boxoffice(session, stdate, eddate)
        except Exception:  # noqa: BLE001
            logger.warning("박스오피스 수집 실패 (%s~%s)", stdate, eddate, exc_info=True)
            failed_months += 1
            continue
        logger.info("박스오피스 %s~%s -> %d건", stdate, eddate, len(entries))
        for entry in entries:
            entry["query_stdate"] = stdate
            entry["query_eddate"] = eddate
        all_entries.extend(entries)
        time.sleep(CALL_DELAY_SEC)

    # 전부(또는 전부에 가깝게) 실패했는데 그냥 저장하면, 이전에 잘 받아둔 데이터를 빈
    # 결과로 덮어써버린다(실제로 한 번 겪은 사고). 호출이 하나도 안 성공했으면 기존
    # boxoffice.json을 그대로 두고 실패로 끝낸다.
    if not all_entries:
        logger.error(
            "%d개월 전부 수집 실패 — 기존 data/raw/kopis/boxoffice.json을 덮어쓰지 않고 종료",
            MONTHS_BACK,
        )
        return False

    path = save_raw_json("kopis", all_entries, "boxoffice.json")
    logger.info(
        "저장 완료: %s (%d건, 최근 %d개월 중 %d개월 실패)",
        path, len(all_entries), MONTHS_BACK, failed_months,
    )
    return failed_months == 0


if __name__ == "__main__":
    main()

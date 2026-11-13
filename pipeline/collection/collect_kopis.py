"""KOPIS 공연예술통합전산망 API 수집.

올림픽공원(시설코드 FC001247)에서 열린/열릴 공연 목록과 공연별 상세(출연진·요금·
관람연령·예매처 링크 등)를 수집해 data/raw/kopis/ 에 저장한다.

- 목록: GET /openApi/restful/pblprfr (prfplccd=FC001247, 최대 rows=100)
- 상세: GET /openApi/restful/pblprfr/{mt20id}
- 공연장: 올림픽공원 시설그룹코드는 /openApi/restful/prfplc?shprfnmfct=올림픽공원 으로 확인함
  (KSPO DOME, 우리금융아트홀, 핸드볼경기장 등 하위 12개 공연장을 포함).
"""
from __future__ import annotations

import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

from common import KOPIS_API_KEY, RAW_DIR, get_logger, http_session, save_raw_json

logger = get_logger("collect_kopis")

BASE_URL = "http://www.kopis.or.kr/openApi/restful"
OLYMPIC_PARK_FCLTYCD = "FC001247"
MAX_ROWS = 100
DETAIL_CALL_DELAY_SEC = 0.3


def _parse_list_xml(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    if root.find("db/returncode") is not None:
        raise RuntimeError(f"KOPIS 오류 응답: {xml_text[:200]}")
    items = []
    for db in root.findall("db"):
        items.append({child.tag: (child.text or "").strip() for child in db})
    return items


def fetch_performance_list(session, stdate: str, eddate: str) -> list[dict]:
    all_items: list[dict] = []
    page = 1
    while True:
        resp = session.get(
            f"{BASE_URL}/pblprfr",
            params={
                "service": KOPIS_API_KEY,
                "stdate": stdate,
                "eddate": eddate,
                "cpage": page,
                "rows": MAX_ROWS,
                "prfplccd": OLYMPIC_PARK_FCLTYCD,
            },
            timeout=30,
        )
        resp.raise_for_status()
        items = _parse_list_xml(resp.text)
        logger.info("목록 page=%d -> %d건", page, len(items))
        all_items.extend(items)
        if len(items) < MAX_ROWS:
            break
        page += 1
        time.sleep(DETAIL_CALL_DELAY_SEC)
    return all_items


def fetch_performance_detail(session, mt20id: str) -> dict:
    resp = session.get(
        f"{BASE_URL}/pblprfr/{mt20id}",
        params={"service": KOPIS_API_KEY},
        timeout=30,
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    db = root.find("db")
    if db is None:
        raise RuntimeError(f"{mt20id} 상세 응답에 db 없음: {resp.text[:200]}")
    detail = {}
    for child in db:
        if child.tag == "relates":
            detail["relates"] = [
                {"relatenm": r.findtext("relatenm", ""), "relateurl": r.findtext("relateurl", "")}
                for r in child.findall("relate")
            ]
        elif child.tag == "styurls":
            detail["styurls"] = [u.text for u in child.findall("styurl") if u.text]
        else:
            detail[child.tag] = (child.text or "").strip()
    return detail


def _load_existing_details() -> dict[str, dict]:
    """기존 performance_detail.json을 mt20id -> detail로 읽어온다. 없거나 깨졌으면 빈 dict.

    이번 호출에서 어떤 mt20id가 실패해도, 전에 성공했던 데이터가 있으면 그걸 그대로
    남겨서 저장한다 — 예전엔 실패가 늘면(KOPIS 쪽 일시 장애 등) 그 적은 결과로 기존
    파일을 통째로 덮어써서 데이터를 잃는 사고가 있었다(812건 -> 565건으로 247건 손실,
    tasks/verification.md [2026-11-12] 참고).
    """
    path = RAW_DIR / "kopis" / "performance_detail.json"
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            existing = json.load(f)
        return {d["mt20id"]: d for d in existing if d.get("mt20id")}
    except Exception:  # noqa: BLE001
        logger.warning("기존 performance_detail.json을 읽지 못했습니다 — 빈 상태로 시작", exc_info=True)
        return {}


def main() -> None:
    if not KOPIS_API_KEY:
        logger.error("KOPIS_API_KEY가 .env에 없습니다.")
        return

    session = http_session()

    stdate = "20130101"
    eddate = (datetime.now() + timedelta(days=365)).strftime("%Y%m%d")

    logger.info("KOPIS 공연 목록 수집 시작 (%s ~ %s, 올림픽공원)", stdate, eddate)
    performances = fetch_performance_list(session, stdate, eddate)
    logger.info("목록 수집 완료: %d건", len(performances))
    list_path = save_raw_json("kopis", performances, "performance_list.json")
    logger.info("저장: %s", list_path)

    existing_details = _load_existing_details()
    merged: dict[str, dict] = {}
    failed = []
    newly_succeeded = 0
    recovered_from_existing = 0
    for i, perf in enumerate(performances, start=1):
        mt20id = perf.get("mt20id")
        try:
            merged[mt20id] = fetch_performance_detail(session, mt20id)
            newly_succeeded += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("상세 수집 실패 mt20id=%s: %s", mt20id, exc)
            failed.append({"mt20id": mt20id, "error": str(exc)})
            if mt20id in existing_details:
                merged[mt20id] = existing_details[mt20id]
                recovered_from_existing += 1
        if i % 50 == 0:
            logger.info("상세 수집 진행: %d/%d", i, len(performances))
        time.sleep(DETAIL_CALL_DELAY_SEC)

    details = list(merged.values())
    fully_failed = len(failed) - recovered_from_existing
    detail_path = save_raw_json("kopis", details, "performance_detail.json")
    logger.info(
        "상세 저장: %s (%d건 = 이번에 성공 %d + 기존 데이터로 보존 %d, 완전 실패 %d건)",
        detail_path, len(details), newly_succeeded, recovered_from_existing, fully_failed,
    )
    if failed:
        save_raw_json("kopis", failed, "performance_detail_failed.json")
    return fully_failed == 0


if __name__ == "__main__":
    main()

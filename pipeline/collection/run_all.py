"""6개 수집 스크립트를 순서대로 실행하고 출처별 성공/실패를 요약한다.

사용법: python run_all.py  (pipeline/collection 디렉터리에서 실행)
"""
from __future__ import annotations

import traceback

from common import get_logger

logger = get_logger("run_all")

SCRIPTS = [
    ("KOPIS 공연 목록·상세", "collect_kopis"),
    ("KOPIS 박스오피스(인기도)", "collect_kopis_boxoffice"),
    ("문체부 통합 공연정보(KSPO 필터)", "collect_integrated_performance"),
    ("영문 공연정보(CSV)", "collect_english_performance_file"),
    ("KSPO 올림픽공원 대관정보", "collect_kspo_venue_rental"),
    ("주차·차량입출차·날씨", "collect_parking_weather"),
]


def main() -> None:
    results = []
    for label, module_name in SCRIPTS:
        logger.info("=== %s 시작 ===", label)
        try:
            module = __import__(module_name)
            ok = module.main()
            results.append((label, "OK" if ok is not False else "FAILED"))
        except Exception:  # noqa: BLE001
            logger.error("%s 실패:\n%s", label, traceback.format_exc())
            results.append((label, "FAILED"))
        logger.info("=== %s 종료 ===\n", label)

    logger.info("수집 요약")
    for label, status in results:
        logger.info("  - %-30s %s", label, status)


if __name__ == "__main__":
    main()

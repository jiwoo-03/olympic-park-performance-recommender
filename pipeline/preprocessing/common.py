"""전처리·EDA 공통 유틸: data/raw 로딩, data/processed 저장, 경로 상수."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def load_raw_json(source_name: str, filename: str):
    path = RAW_DIR / source_name / filename
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_processed_json(filename: str):
    path = PROCESSED_DIR / filename
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_processed_json(payload, filename: str) -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = PROCESSED_DIR / filename
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def save_processed_csv(df, filename: str) -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = PROCESSED_DIR / filename
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


_YEAR_TOKEN_PATTERN = re.compile(r"(?<!\d)(19|20)\d{2}(?!\d)")
_NORMALIZE_PATTERN = re.compile(r"[\s\W_]+", flags=re.UNICODE)
# "%"가 들어간 괄호만 지운다 — "［얼리버드 50%］"류 할인 프로모션 문구는 KOPIS 쪽 제목에는
# 없어서 유사도를 깎아먹지만(실제로 매칭을 놓친 사례 확인함: tasks/verification.md
# [2026-11-12] "백 번째 리뷰" 참고), "[앵콜]"/"[서울]"처럼 실제로 다른 회차를 구분해주는
# 괄호는 % 없이 그대로 남아서 오매칭을 막는 안전장치 역할을 계속한다.
_PROMO_BRACKET_PATTERN = re.compile(r"[\[［][^\]］]*%[^\]］]*[\]］]")


def normalize_title(title: str) -> str:
    """공백·특수문자·연도 숫자·할인 프로모션 괄호를 제거해 출처 간 공연명 매칭 키로 쓴다.

    한국체육산업개발 쪽 제목은 "2026 ○○ 콘서트 〈2026 ○○〉"처럼 연도를 중복
    표기하는 경우가 많아, 연도는 먼저 제거하고 기간(PERIOD) 겹침으로 교차
    검증한다 — 연도 불일치 매칭 오류는 그 교차 검증이 걸러낸다.
    """
    if not title:
        return ""
    without_promo = _PROMO_BRACKET_PATTERN.sub("", title)
    without_year = _YEAR_TOKEN_PATTERN.sub("", without_promo)
    return _NORMALIZE_PATTERN.sub("", without_year).lower()

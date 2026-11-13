"""4개 API 공통 설정: .env 키 로딩, HTTP 재시도 세션, data/raw 저장 헬퍼."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

load_dotenv(PROJECT_ROOT / ".env")

PERFORMANCE_INTEGRATED_API_KEY = os.environ.get("PERFORMANCE_INTEGRATED_API_KEY", "")
KSPO_PERFORMANCE_API_KEY = os.environ.get("KSPO_PERFORMANCE_API_KEY", "")
KSPO_PARKING_WEATHER_API_KEY = os.environ.get("KSPO_PARKING_WEATHER_API_KEY", "")
KOPIS_API_KEY = os.environ.get("KOPIS_API_KEY", "")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def http_session(total_retries: int = 3, backoff_factor: float = 1.0) -> requests.Session:
    """타임아웃·5xx에 재시도하는 세션. (주차 API는 504가 잦아 재시도가 필요하다)"""
    session = requests.Session()
    retry = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    session.mount("http://", HTTPAdapter(max_retries=retry))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session


def today_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def save_raw_json(source_name: str, payload, filename: str | None = None) -> Path:
    out_dir = RAW_DIR / source_name
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = filename or f"{today_stamp()}.json"
    out_path = out_dir / filename
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_path


def save_raw_bytes(source_name: str, data: bytes, filename: str) -> Path:
    out_dir = RAW_DIR / source_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_bytes(data)
    return out_path

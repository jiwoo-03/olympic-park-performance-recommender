"""정제된 performances.csv에 대한 EDA: 공연장·월별 공연 수, 장르 비중, 요금 분포,
요일별 공연 패턴. 통계는 로그로 남기고 차트는 figures/ 에 PNG로 저장한다.
"""
from __future__ import annotations

import re
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.use("Agg")
_NANUM_PATH = Path.home() / ".fonts" / "NanumGothic.ttf"
if _NANUM_PATH.exists():
    matplotlib.font_manager.fontManager.addfont(str(_NANUM_PATH))
    matplotlib.rcParams["font.family"] = matplotlib.font_manager.FontProperties(fname=str(_NANUM_PATH)).get_name()
matplotlib.rcParams["axes.unicode_minus"] = False

from common import PROCESSED_DIR, get_logger

logger = get_logger("eda")
FIGURES_DIR = Path(__file__).resolve().parent / "figures"

_PERIOD_PATTERN = re.compile(r"(\d{4})(\d{2})(\d{2})\s+(\d{4})(\d{2})(\d{2})")


def _parse_period_start(period: str) -> pd.Timestamp | None:
    m = _PERIOD_PATTERN.search(period or "")
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return pd.Timestamp(year=y, month=mo, day=d)
    except ValueError:
        return None


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(PROCESSED_DIR / "performances.csv")
    logger.info("분석 대상(대관 운영 행 제외, KSPO 기준) %d건", len(df))

    df["start_date"] = df["period"].apply(_parse_period_start)
    df = df[df["start_date"].notna()].copy()
    df["month"] = df["start_date"].dt.to_period("M").astype(str)
    df["weekday"] = df["start_date"].dt.day_name()

    # 1) 장르 비중
    genre_counts = df["genre"].value_counts()
    logger.info("장르 비중:\n%s", genre_counts.to_string())
    ax = genre_counts.plot(kind="bar", figsize=(8, 5), title="장르별 공연 수 (KSPO 전체, 미분류 포함)")
    ax.set_xlabel("")
    ax.set_ylabel("공연 수")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "genre_distribution.png", dpi=120)
    plt.close()

    # 2) 공연장별 공연 수 (콤마로 여러 장소가 함께 적힌 행은 각각으로 분리해서 센다)
    venue_series = df["venue"].fillna("").str.split(",").explode().str.strip()
    venue_series = venue_series[venue_series != ""]
    venue_counts = venue_series.value_counts().head(15)
    logger.info("공연장별 공연 수 (상위 15):\n%s", venue_counts.to_string())
    ax = venue_counts.plot(kind="barh", figsize=(8, 6), title="공연장별 공연 수 (상위 15)")
    ax.invert_yaxis()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "venue_counts.png", dpi=120)
    plt.close()

    # 3) 월별 공연 수 (연-월 단위 추세, 데이터가 2010~2027년에 걸쳐 있어 연도별로도 집계)
    monthly_counts = df.groupby("month").size()
    logger.info("월별 공연 수 데이터 포인트 %d개 (연-월 단위)", len(monthly_counts))
    df["year"] = df["start_date"].dt.year
    yearly_counts = df.groupby("year").size()
    logger.info("연도별 공연 수:\n%s", yearly_counts.to_string())
    ax = yearly_counts.plot(kind="bar", figsize=(10, 5), title="연도별 공연 수 (KSPO, 2010~2027)")
    ax.set_xlabel("")
    ax.set_ylabel("공연 수")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "yearly_counts.png", dpi=120)
    plt.close()

    # 4) 요일별 공연 패턴 (공연 시작일 기준)
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_kr = {"Monday": "월", "Tuesday": "화", "Wednesday": "수", "Thursday": "목",
                  "Friday": "금", "Saturday": "토", "Sunday": "일"}
    weekday_counts = df["weekday"].value_counts().reindex(weekday_order).rename(index=weekday_kr)
    logger.info("요일별 공연 시작 건수:\n%s", weekday_counts.to_string())
    ax = weekday_counts.plot(kind="bar", figsize=(7, 5), title="요일별 공연 시작 건수")
    ax.set_xlabel("")
    ax.set_ylabel("공연 수")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "weekday_counts.png", dpi=120)
    plt.close()

    # 5) 요금 분포 (KOPIS 매칭으로 요금을 확인한 공연만)
    priced = df[df["price_min"].notna()]
    logger.info(
        "요금 확인 가능 %d건 (전체의 %.1f%%) — 최저가 평균 %.0f원, 최고가 평균 %.0f원",
        len(priced), 100 * len(priced) / len(df), priced["price_min"].mean(), priced["price_max"].mean(),
    )
    ax = priced["price_min"].plot(kind="hist", bins=20, figsize=(8, 5), title="최저 티켓가 분포 (원)")
    ax.set_xlabel("최저가(원)")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "price_distribution.png", dpi=120)
    plt.close()

    # 6) 매칭 상태별 비중 (KOPIS 매칭 커버리지)
    match_counts = df["match_status"].value_counts()
    logger.info("매칭 상태 비중:\n%s", match_counts.to_string())

    logger.info("차트 저장 위치: %s", FIGURES_DIR)


if __name__ == "__main__":
    main()

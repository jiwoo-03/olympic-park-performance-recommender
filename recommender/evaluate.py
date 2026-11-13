"""오프라인 평가: 가상 사용자 프로필 30개로 Precision@5, Coverage, Diversity 측정.

완료 기준(워크플로우 문서 4.4장, 6장): 가상 프로필 30개의 장르 일치율(Precision@5),
Coverage, Diversity를 평가표로 남긴다.

가상 프로필은 "장르 하나만 좋아하는" 단순한 취향으로 만든다(6개 실제 장르 × 5명 = 30명,
"미분류"는 선택 가능한 취향이 아니므로 제외) — 특정 장르를 좋아하는 사용자에게 실제로
그 장르가 추천되는지를 가장 직접적으로 검증할 수 있는 구성이다.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

import recommend as R
from common import get_logger
from scoring import CONTENT_FIRST_MODE
from vectorize import GENRE_ORDER

logger = get_logger("evaluate")

EVAL_GENRES = [g for g in GENRE_ORDER if g != "미분류"]
PROFILES_PER_GENRE = 5
TOP_K = 5
EVAL_TODAY = date(2026, 11, 12)  # 평가 재현성을 위해 고정(운영에서는 매일 바뀌는 실제 오늘)


def build_profiles() -> list[dict]:
    return [
        {"id": f"{genre}-{i + 1}", "favorite_genres": [genre]}
        for genre in EVAL_GENRES
        for i in range(PROFILES_PER_GENRE)
    ]


def evaluate() -> tuple[pd.DataFrame, float, int, int]:
    df, vectors = R.load_data()
    eligible_idx = set(df.index[R._eligible_mask(df, EVAL_TODAY, allow_historical=CONTENT_FIRST_MODE)])

    rows = []
    all_recommended_idx: set[int] = set()
    for profile in build_profiles():
        target_genre = profile["favorite_genres"][0]
        result = R.taste_recommend(
            df, vectors, favorite_genres=profile["favorite_genres"], top_k=TOP_K, today=EVAL_TODAY,
        )
        hit = int((result["genre"] == target_genre).sum())
        all_recommended_idx.update(result.index)
        status_counts = result["status"].value_counts().to_dict() if len(result) else {}
        rows.append({
            "profile": profile["id"],
            "target_genre": target_genre,
            "returned": len(result),
            "precision_at_5": round(hit / len(result), 3) if len(result) else 0.0,
            "diversity_genres": result["genre"].nunique(),
            "status_breakdown": status_counts,
        })

    report = pd.DataFrame(rows)
    coverage = len(all_recommended_idx) / len(eligible_idx) if eligible_idx else 0.0
    return report, coverage, len(all_recommended_idx), len(eligible_idx)


def main() -> None:
    report, coverage, covered_n, eligible_n = evaluate()

    logger.info("프로필 %d개 평가 완료", len(report))
    logger.info("평균 Precision@5: %.3f", report["precision_at_5"].mean())
    logger.info("평균 Diversity(추천 목록 내 장르 수): %.2f", report["diversity_genres"].mean())
    logger.info("Coverage: %d/%d = %.3f", covered_n, eligible_n, coverage)
    logger.info(
        "장르별 Precision@5:\n%s",
        report.groupby("target_genre")["precision_at_5"].mean().round(3).to_string(),
    )
    status_tally: dict[str, int] = {}
    for d in report["status_breakdown"]:
        for k, v in d.items():
            status_tally[k] = status_tally.get(k, 0) + v
    logger.info("추천 결과 상태 분포(전체 30프로필 합산): %s", status_tally)
    low_returned = report[report["returned"] < TOP_K]
    if not low_returned.empty:
        logger.info(
            "top_k(%d)보다 적게 반환된 프로필 %d개(후보 자체가 적은 장르):\n%s",
            TOP_K, len(low_returned), low_returned.to_string(index=False),
        )

    report.to_csv("evaluation_results.csv", index=False)
    logger.info("저장 완료: recommender/evaluation_results.csv")


if __name__ == "__main__":
    main()

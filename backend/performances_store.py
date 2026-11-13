"""performances.csv + performance_vectors.npz를 서버 시작 시 메모리로 읽어온다.

pipeline/이 매일 다시 만드는 배치 산출물이라 DB에 중복 저장하지 않는다(database.py
설명 참고). `recommender/`의 추천 함수를 그대로 재사용한다 — API 핸들러가 임베딩을
다시 계산하면 안 된다는 CLAUDE.md 아키텍처 규칙 때문에, 벡터는 여기서 한 번만 로드하고
recommend.py의 함수들에 그대로 넘긴다.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RECOMMENDER_DIR = PROJECT_ROOT / "recommender"
if str(RECOMMENDER_DIR) not in sys.path:
    sys.path.insert(0, str(RECOMMENDER_DIR))

import recommend as rec  # noqa: E402  (recommender/ 모듈 재사용을 위한 경로 추가 이후 임포트)
from scoring import is_ended, period_overlaps  # noqa: E402


def to_records(df: pd.DataFrame, today: date | None = None) -> list[dict]:
    """DataFrame을 JSON으로 바로 내려줄 수 있는 dict 리스트로 바꾼다 — 행 인덱스를
    `id`로, NaN은 None으로 바꾼다.

    `status`(확정 예정/매년 반복 예상/과거 유사 공연)가 아직 없는 행에는 여기서 채운다 —
    추천 함수가 만든 결과는 이미 `status` 컬럼이 있어서(recommend._with_status) 그대로
    쓰고, `GET /performances` 같은 단순 조회 결과에도 "예매 가능 여부"가 항상 보이도록
    한다(프론트엔드에서 날짜와 상관없이 상태를 명확히 안내해야 하므로)."""
    today = today or date.today()
    records = []
    for idx, row in df.iterrows():
        d = row.to_dict()
        d["id"] = int(idx)
        if "status" not in d or pd.isna(d["status"]):
            d["status"] = rec._status_for(row, today)
        for k, v in d.items():
            if isinstance(v, float) and pd.isna(v):
                d[k] = None
        records.append(d)
    return records


class PerformanceStore:
    def __init__(self) -> None:
        self.df: pd.DataFrame = pd.DataFrame()
        self.vectors: np.ndarray = np.zeros((0, 0))
        self.reload()

    def reload(self) -> None:
        self.df, self.vectors = rec.load_data()

    def get_row(self, performance_id: int) -> pd.Series | None:
        if performance_id not in self.df.index:
            return None
        return self.df.loc[performance_id]

    def filter(self, on_date: date | None = None, genre: str | None = None) -> pd.DataFrame:
        """목록 조회(추천 아님). 날짜를 안 줘도 종료된(과거) 공연은 기본적으로 뺀다 —
        날짜·장르 필터 없이 전체를 보면 과거 공연까지 다 나와서 결과가 너무 많아지는
        문제가 있었다(tasks/todo.md "추가 기능 요청" 3번 참고). "미분류"도 기본적으로
        뺀다 — 장르 선택 드롭다운에 없는 값이라 달력·검색 결과에 보이면 사용자가 골라낼
        방법이 없다(2026-11-12, 사용자가 "정승환 콘서트"가 미분류로 나온 걸 발견해서
        키워드 규칙을 보강했지만, 방어적으로 여기서도 한 번 더 막는다). 단건 조회
        (get_row)나 추천 계열(recommend.py)은 이 필터와 무관하게 과거 공연·미분류를
        의도적으로 보여줄 수 있으므로(후자는 venue_fallback.py가 담당) 영향 없다."""
        today = date.today()
        df = self.df[~self.df["period"].map(lambda p: is_ended(p, today))]
        df = df[df["genre"] != "미분류"]
        if genre:
            df = df[df["genre"] == genre]
        if on_date:
            df = df[df["period"].map(lambda p: period_overlaps(p, on_date, on_date))]
        return df


store = PerformanceStore()

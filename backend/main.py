"""백엔드 API. 엔드포인트는 워크플로우 문서 4.5장 + tasks/todo.md "5단계" 설계를 따른다.

API 핸들러는 임베딩 계산이나 외부 API 호출을 하지 않는다(CLAUDE.md 아키텍처 규칙) —
여기서는 서버 시작 시 메모리로 미리 올려둔 `performances_store`와 `recommender/`의
함수를 호출해 조회·필터·정렬만 한다.

실행: `uvicorn main:app --reload` (backend/ 디렉터리에서, .venv 활성화 후)
"""
from __future__ import annotations

import os
from datetime import date

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import get_db, init_db
from models import RecLog
from performances_store import store, to_records  # recommender/ 경로를 sys.path에 추가함
import recommend as rec  # noqa: E402  (위 임포트가 경로를 추가한 뒤에 가능해짐)

app = FastAPI(title="올림픽공원 공연 추천 API", version="0.1.0")

# 프론트엔드(Next.js, 다른 포트/도메인)가 브라우저에서 바로 호출해야 하므로 CORS가 필요하다.
# 로컬 개발 기본값은 전체 허용("*")이고, 배포 환경에서는 Render 대시보드에 ALLOWED_ORIGIN
# 환경변수(Vercel 배포 URL, 쉼표로 여러 개 가능)를 설정하면 코드 수정 없이 좁혀진다.
_allowed_origin = os.environ.get("ALLOWED_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allowed_origin == "*" else _allowed_origin.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


def _log_impressions(db: Session, session_id: str, result: pd.DataFrame, recommend_type: str) -> None:
    for performance_id in result.index:
        db.add(RecLog(
            session_id=session_id, performance_id=int(performance_id),
            recommend_type=recommend_type, event="impression",
        ))
    db.commit()


@app.get("/performances")
def list_performances(date: date | None = None, genre: str | None = None):
    """GET /performances?date=&genre= — 목록 조회(필터만, 추천 아님)."""
    return to_records(store.filter(on_date=date, genre=genre))


@app.get("/performances/{performance_id}")
def get_performance(performance_id: int):
    row = store.get_row(performance_id)
    if row is None:
        raise HTTPException(status_code=404, detail="공연을 찾을 수 없습니다")
    return to_records(row.to_frame().T)[0]


@app.get("/recommend/me")
def recommend_me(session_id: str | None = None, db: Session = Depends(get_db)):
    """장르 선택(온보딩) 없이, 지금 예매 가능한 공연 상위 3개를 보여준다
    (2026-11-12, 사용자 요청 — 장르별 추천은 데이터가 적은 장르에서 엉뚱한 장르로
    채워지는 문제가 있어 폐기, tasks/todo.md 참고)."""
    result = rec.bookable_top(store.df)
    if session_id:
        _log_impressions(db, session_id, result, "me")
    return to_records(result)


@app.get("/recommend/similar/{performance_id}")
def recommend_similar(performance_id: int, db: Session = Depends(get_db), session_id: str | None = None):
    row = store.get_row(performance_id)
    if row is None:
        raise HTTPException(status_code=404, detail="공연을 찾을 수 없습니다")

    result = rec.similar_performances(store.df, store.vectors, row["title"])
    if session_id:
        _log_impressions(db, session_id, result, "similar")
    return to_records(result)


@app.get("/parking/forecast")
def parking_forecast(forecast_date: date):
    """주차 혼잡 예보. 원본 데이터(KSPO 차량 입출차·날씨) 수집이 막혀 있어 아직 만들 수
    없다 — CLAUDE.md "알려진 이슈 → 미해결 블로커" 참고."""
    raise HTTPException(
        status_code=501,
        detail="주차 혼잡 예보는 아직 제공하지 않습니다 — 원본 데이터(collect_parking_weather.py) 수집이 막혀 있습니다.",
    )

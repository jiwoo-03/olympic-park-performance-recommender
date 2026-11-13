"""SQLite 연결 설정.

여기 저장하는 건 쓰기가 필요한 상태(user_prefs, favorites, rec_logs)뿐이다.
performances·venues는 DB 테이블이 아니라 pipeline/이 만든 CSV·벡터를 서버 시작 시
메모리로 읽어서 쓴다(performances_store.py) — 매일 통째로 다시 만들어지는 배치 산출물을
DB에 또 복제하는 동기화 비용을 피하려는 8주 MVP 단계의 단순화다
(tasks/todo.md "5단계: 백엔드" 참고).
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_PATH = Path(__file__).resolve().parent / "app.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

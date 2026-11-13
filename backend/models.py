"""쓰기가 필요한 상태만 담는 테이블: 추천 로그.

로그인·찜하기·온보딩 장르 취향(User/Favorite/UserPref)은 전부 삭제했다(2026-11-12,
사용자 요청 — 마이페이지·장르 선택 UI를 없애면서 쓸 일이 없어짐, tasks/todo.md
"추가 수정 작업" 참고). 남은 건 추천 노출 로그(RecLog)뿐이다.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RecLog(Base):
    __tablename__ = "rec_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    performance_id: Mapped[int] = mapped_column(Integer, index=True)
    recommend_type: Mapped[str] = mapped_column(String)  # me/similar
    event: Mapped[str] = mapped_column(String, default="impression")  # impression/click/booking_click
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

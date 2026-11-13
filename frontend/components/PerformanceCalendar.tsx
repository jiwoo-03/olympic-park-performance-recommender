"use client";

import { useMemo, useState } from "react";
import { parsePeriod, type Performance } from "@/lib/types";
import PerformanceCard from "./PerformanceCard";

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

/* COEX 행사 일정 캘린더(https://www.coex.co.kr/event/full-schedules/)의 "캘린더형"을
 * 참고했다 — 월 단위 그리드, 요일별 주말 색상 구분, 카테고리(장르)별 색점+범례. 다만
 * 그 페이지는 데스크톱 와이드 레이아웃이라 날짜 칸 안에 제목 텍스트를 그대로 넣는데,
 * 우리는 모바일 우선(최대 너비 ~390px)이라 칸에 텍스트를 넣으면 안 보여서, 장르별
 * 색점(최대 3개+더보기 숫자)으로 축약하고 날짜를 누르면 아래에 전체 목록이 펼쳐지는
 * 방식으로 조정했다. */
const GENRE_COLORS: Record<string, string> = {
  "콘서트": "bg-rose-500",
  "뮤지컬": "bg-violet-500",
  "클래식": "bg-amber-500",
  "페스티벌": "bg-sky-500",
  "어린이": "bg-emerald-500",
  "스포츠/기타": "bg-slate-500",
};
const DEFAULT_DOT_COLOR = "bg-gray-400";
const MAX_DOTS = 3;

function sameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

function isInPeriod(day: Date, performance: Performance): boolean {
  const parsed = parsePeriod(performance.period);
  if (!parsed) return false;
  const [start, end] = parsed;
  const d = new Date(day.getFullYear(), day.getMonth(), day.getDate());
  return d >= new Date(start.getFullYear(), start.getMonth(), start.getDate())
    && d <= new Date(end.getFullYear(), end.getMonth(), end.getDate());
}

export default function PerformanceCalendar({ performances }: { performances: Performance[] }) {
  const today = useMemo(() => new Date(), []);
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth()); // 0-11
  const [selectedDay, setSelectedDay] = useState<Date | null>(null);

  const genresInView = useMemo(
    () => Array.from(new Set(performances.map((p) => p.genre))),
    [performances],
  );

  const weeks = useMemo(() => {
    const firstOfMonth = new Date(viewYear, viewMonth, 1);
    const startOffset = firstOfMonth.getDay(); // 0=일
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();

    const cells: (Date | null)[] = [
      ...Array(startOffset).fill(null),
      ...Array.from({ length: daysInMonth }, (_, i) => new Date(viewYear, viewMonth, i + 1)),
    ];
    while (cells.length % 7 !== 0) cells.push(null);

    const rows: (Date | null)[][] = [];
    for (let i = 0; i < cells.length; i += 7) rows.push(cells.slice(i, i + 7));
    return rows;
  }, [viewYear, viewMonth]);

  function performancesFor(day: Date): Performance[] {
    return performances.filter((p) => isInPeriod(day, p));
  }

  function goPrevMonth() {
    setSelectedDay(null);
    if (viewMonth === 0) {
      setViewYear((y) => y - 1);
      setViewMonth(11);
    } else {
      setViewMonth((m) => m - 1);
    }
  }

  function goNextMonth() {
    setSelectedDay(null);
    if (viewMonth === 11) {
      setViewYear((y) => y + 1);
      setViewMonth(0);
    } else {
      setViewMonth((m) => m + 1);
    }
  }

  const selectedPerformances = selectedDay ? performancesFor(selectedDay) : [];

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={goPrevMonth}
          className="rounded-lg border border-black/15 px-2 py-1 text-sm dark:border-white/15"
          aria-label="이전 달"
        >
          ◀
        </button>
        <span className="text-lg font-bold tracking-tight">
          {viewYear}.{String(viewMonth + 1).padStart(2, "0")}
        </span>
        <button
          type="button"
          onClick={goNextMonth}
          className="rounded-lg border border-black/15 px-2 py-1 text-sm dark:border-white/15"
          aria-label="다음 달"
        >
          ▶
        </button>
      </div>

      {/* 데이터 로딩 전엔 비어있지만 min-h로 자리를 미리 잡아둬서, 장르가 채워질 때
       * 아래 달력 전체가 밀리지 않게 한다(Lighthouse CLS 점검에서 발견, 2026-11-12). */}
      <div className="flex min-h-[1lh] flex-wrap gap-x-3 gap-y-1 text-[11px] text-gray-500 dark:text-gray-400">
        {genresInView.map((g) => (
          <span key={g} className="flex items-center gap-1">
            <span className={`h-1.5 w-1.5 rounded-full ${GENRE_COLORS[g] ?? DEFAULT_DOT_COLOR}`} />
            {g}
          </span>
        ))}
      </div>

      <table className="w-full table-fixed border-collapse text-center text-xs">
        <thead>
          <tr>
            {WEEKDAYS.map((w, i) => (
              <th
                key={w}
                className={`pb-1 font-medium ${
                  i === 0 ? "text-rose-600" : i === 6 ? "text-sky-700" : "text-gray-500 dark:text-gray-400"
                }`}
              >
                {w}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {weeks.map((row, i) => (
            <tr key={i}>
              {row.map((day, j) => {
                if (!day) return <td key={j} className="py-2" />;
                const dayPerformances = performancesFor(day);
                const isSelected = selectedDay && sameDay(day, selectedDay);
                const isToday = sameDay(day, today);
                const weekendClass = j === 0 ? "text-rose-600" : j === 6 ? "text-sky-700" : "";
                return (
                  <td key={j} className="py-1">
                    <button
                      type="button"
                      onClick={() => setSelectedDay(dayPerformances.length > 0 ? day : null)}
                      disabled={dayPerformances.length === 0}
                      className={`flex w-full flex-col items-center gap-1 rounded-lg py-1.5 ${
                        isSelected
                          ? "bg-black text-white dark:bg-white dark:text-black"
                          : dayPerformances.length > 0
                            ? `hover:bg-black/5 dark:hover:bg-white/10 ${weekendClass}`
                            : `text-gray-300 dark:text-gray-700 ${isToday ? "" : weekendClass}`
                      } ${isToday && !isSelected ? "font-bold ring-1 ring-emerald-500" : ""}`}
                    >
                      <span>{day.getDate()}</span>
                      {/* 항상 h-1.5 높이를 차지해서(점이 없어도) 데이터 로딩 전/후로
                       * 칸 높이가 바뀌어 레이아웃이 밀리지 않게 한다. */}
                      <span className="flex h-1.5 items-center gap-0.5">
                        {dayPerformances.slice(0, MAX_DOTS).map((p) => (
                          <span
                            key={p.id}
                            className={`h-1.5 w-1.5 rounded-full ${
                              isSelected ? "bg-white dark:bg-black" : (GENRE_COLORS[p.genre] ?? DEFAULT_DOT_COLOR)
                            }`}
                          />
                        ))}
                        {dayPerformances.length > MAX_DOTS && (
                          <span className="text-[9px] leading-none">+{dayPerformances.length - MAX_DOTS}</span>
                        )}
                      </span>
                    </button>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {selectedDay && (
        <div className="flex flex-col gap-2">
          <h3 className="text-xs font-bold text-gray-500 dark:text-gray-400">
            {selectedDay.getMonth() + 1}월 {selectedDay.getDate()}일 공연 {selectedPerformances.length}건
          </h3>
          {selectedPerformances.map((p) => (
            <PerformanceCard key={p.id} performance={p} />
          ))}
        </div>
      )}
    </div>
  );
}

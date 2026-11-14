"use client";

import { useEffect, useState } from "react";
import { listPerformances, recommendMe } from "@/lib/api";
import { getSessionId } from "@/lib/session";
import type { Performance } from "@/lib/types";
import PerformanceCalendar from "@/components/PerformanceCalendar";
import PerformanceCard from "@/components/PerformanceCard";

const GENRES = ["콘서트", "뮤지컬", "클래식", "페스티벌", "어린이", "스포츠/기타"];

function Section({
  title,
  items,
  loading,
  emptyText,
}: {
  title: string;
  items: Performance[];
  loading: boolean;
  emptyText: string;
}) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-sm font-bold">{title}</h2>
      {loading ? (
        <p className="text-sm text-muted">불러오는 중...</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-muted">{emptyText}</p>
      ) : (
        <div className="flex flex-col gap-2">
          {items.map((p) => (
            <PerformanceCard key={p.id} performance={p} />
          ))}
        </div>
      )}
    </section>
  );
}

export default function HomePage() {
  const [myRecs, setMyRecs] = useState<Performance[]>([]);
  const [myRecsLoading, setMyRecsLoading] = useState(true);

  const [calendarGenre, setCalendarGenre] = useState("");
  const [calendarPerformances, setCalendarPerformances] = useState<Performance[]>([]);

  useEffect(() => {
    recommendMe(getSessionId())
      .then(setMyRecs)
      .finally(() => setMyRecsLoading(false));
  }, []);

  useEffect(() => {
    listPerformances({ genre: calendarGenre || undefined }).then(setCalendarPerformances);
  }, [calendarGenre]);

  return (
    <div className="flex flex-col gap-8 py-4">
      <Section
        title="예매 가능한 공연"
        items={myRecs}
        loading={myRecsLoading}
        emptyText="지금 예매 가능한 공연이 없어요."
      />

      <section className="flex flex-col gap-3 border-t border-line pt-6">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold">날짜로 찾기</h2>
          <select
            aria-label="장르 필터"
            value={calendarGenre}
            onChange={(e) => setCalendarGenre(e.target.value)}
            className="rounded-lg border border-line bg-surface px-2 py-1 text-xs"
          >
            <option value="">장르 전체</option>
            {GENRES.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </div>

        {/* 로딩 중에도 빈 달력 그리드를 그대로 그려서(데이터만 비어있음) 레이아웃이
         * "불러오는 중..." 텍스트 → 달력으로 갑자기 커지며 밀리는 걸 막는다
         * (Lighthouse CLS 0.328→0, 2026-11-12 점검에서 발견). */}
        <PerformanceCalendar performances={calendarPerformances} />
      </section>
    </div>
  );
}

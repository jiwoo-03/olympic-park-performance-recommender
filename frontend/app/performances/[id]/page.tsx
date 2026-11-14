"use client";

import { useParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { getPerformance, recommendSimilar } from "@/lib/api";
import { parseTicketLinks, type Performance } from "@/lib/types";
import { posterGradient } from "@/lib/posterGradient";
import PerformanceCard from "@/components/PerformanceCard";
import StatusBadge, { statusHelpText } from "@/components/StatusBadge";

function formatPeriod(period: string): string {
  const m = period.match(/(\d{4})(\d{2})(\d{2})\s+(\d{4})(\d{2})(\d{2})/);
  if (!m) return period;
  const [, y1, mo1, d1, y2, mo2, d2] = m;
  return `${y1}.${mo1}.${d1} ~ ${y2}.${mo2}.${d2}`;
}

export default function PerformanceDetailPage() {
  return (
    <Suspense fallback={<p className="py-6 text-sm text-muted">불러오는 중...</p>}>
      <PerformanceDetailContent />
    </Suspense>
  );
}

function PerformanceDetailContent() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  const [performance, setPerformance] = useState<Performance | null>(null);
  const [similar, setSimilar] = useState<Performance[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getPerformance(id), recommendSimilar(id)])
      .then(([p, s]) => {
        setPerformance(p);
        setSimilar(s);
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <p className="py-6 text-sm text-muted">불러오는 중...</p>;
  if (!performance) return <p className="py-6 text-sm text-muted">공연을 찾을 수 없어요.</p>;

  const ticketLinks = parseTicketLinks(performance.ticket_links);
  const isBookable = performance.status === "확정 예정";

  return (
    <div className="flex flex-col gap-6 py-4">
      <div className="flex flex-col gap-3">
        {performance.poster ? (
          // 가로세로 비율을 미리 고정해서 이미지 로딩 전후로 레이아웃이 밀리는 걸
          // 막는다(Lighthouse CLS 0.467→0, 2026-11-12 점검에서 발견).
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={performance.poster}
            alt={performance.title}
            width={600}
            height={900}
            className="aspect-[2/3] w-full rounded-lg object-cover"
          />
        ) : (
          <div
            className="aspect-[2/3] w-full rounded-lg"
            style={{ background: posterGradient(performance.title) }}
          />
        )}
        <div className="flex items-start justify-between gap-2">
          <h1 className="text-lg font-bold">{performance.title}</h1>
          <StatusBadge status={performance.status} />
        </div>
        <p className="text-sm text-muted">
          {statusHelpText(performance.status)}
        </p>
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
          <dt className="text-muted">기간</dt>
          <dd>{formatPeriod(performance.period)}</dd>
          <dt className="text-muted">장소</dt>
          <dd>{performance.venue_normalized || performance.venue}</dd>
          <dt className="text-muted">장르</dt>
          <dd>{performance.genre}</dd>
          {performance.cast && (
            <>
              <dt className="text-muted">출연</dt>
              <dd>{performance.cast}</dd>
            </>
          )}
          {performance.min_age !== null && (
            <>
              <dt className="text-muted">관람연령</dt>
              <dd>{performance.min_age === 0 ? "전체관람가" : `만 ${performance.min_age}세 이상`}</dd>
            </>
          )}
          {performance.price_min !== null && (
            <>
              <dt className="text-muted">가격</dt>
              <dd>
                {performance.price_min.toLocaleString()}원 ~{" "}
                {performance.price_max?.toLocaleString()}원
              </dd>
            </>
          )}
        </dl>
        {performance.synopsis && <p className="text-sm">{performance.synopsis}</p>}
      </div>

      {isBookable && (
        <div className="flex flex-col gap-2">
          <h2 className="text-sm font-bold">예매하기</h2>
          {ticketLinks.length > 0 ? (
            ticketLinks.map((link) => (
              <a
                key={link.relateurl}
                href={link.relateurl}
                target="_blank"
                rel="noreferrer"
                className="rounded-lg border border-line px-4 py-2 text-center text-sm font-medium transition hover:border-brand/40"
              >
                {link.relatenm}에서 예매
              </a>
            ))
          ) : (
            <p className="text-sm text-muted">예매처 정보가 아직 없어요.</p>
          )}
          <p className="text-xs text-muted">
            ⚠️ 일정이 변경되거나 취소될 수 있으니, 예매처에서 최종 확인해주세요.
          </p>
        </div>
      )}

      <div className="flex flex-col gap-2">
        <h2 className="text-sm font-bold">주차 혼잡 예보</h2>
        <p className="rounded-lg bg-surface-2 px-4 py-3 text-sm text-muted">
          준비 중이에요 — 올림픽공원 주차 데이터 수집이 아직 안 돼서 예보를 보여드릴 수
          없어요.
        </p>
      </div>

      {similar.length > 0 && (
        <div className="flex flex-col gap-2">
          <h2 className="text-sm font-bold">비슷한 공연</h2>
          <div className="flex flex-col gap-2">
            {similar.map((p) => (
              <PerformanceCard key={p.id} performance={p} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

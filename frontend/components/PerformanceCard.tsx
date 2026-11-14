import Link from "next/link";
import type { Performance } from "@/lib/types";
import { posterGradient } from "@/lib/posterGradient";
import StatusBadge from "./StatusBadge";

function formatPeriod(period: string): string {
  const m = period.match(/(\d{4})(\d{2})(\d{2})\s+(\d{4})(\d{2})(\d{2})/);
  if (!m) return period;
  const [, y1, mo1, d1, y2, mo2, d2] = m;
  return `${y1}.${mo1}.${d1} ~ ${y2}.${mo2}.${d2}`;
}

export default function PerformanceCard({ performance }: { performance: Performance }) {
  const isHistorical = performance.status === "과거 유사 공연 — 참고용";

  return (
    <Link
      href={`/performances/${performance.id}`}
      className={`flex gap-3 rounded-lg border border-line p-3 transition hover:border-brand/40 ${
        isHistorical ? "opacity-60" : ""
      }`}
    >
      {performance.poster ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={performance.poster}
          alt={performance.title}
          className="h-24 w-16 shrink-0 rounded object-cover"
        />
      ) : (
        <div
          className="h-24 w-16 shrink-0 rounded"
          style={{ background: posterGradient(performance.title) }}
        />
      )}
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-start justify-between gap-2">
          <h3 className="line-clamp-2 text-sm font-semibold">{performance.title}</h3>
        </div>
        <p className="text-xs text-muted">
          {formatPeriod(performance.period)} · {performance.venue_normalized || performance.venue}
        </p>
        <div className="mt-auto flex flex-wrap items-center gap-1.5">
          <span className="rounded bg-surface-2 px-2 py-0.5 text-xs text-muted">
            {performance.genre}
          </span>
          <StatusBadge status={performance.status} />
        </div>
      </div>
    </Link>
  );
}

import Link from "next/link";
import type { Performance } from "@/lib/types";
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
      className={`flex gap-3 rounded-lg border border-black/10 p-3 transition hover:border-black/20 dark:border-white/10 dark:hover:border-white/20 ${
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
        <div className="h-24 w-16 shrink-0 rounded bg-black/5 dark:bg-white/10" />
      )}
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-start justify-between gap-2">
          <h3 className="line-clamp-2 text-sm font-semibold">{performance.title}</h3>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {formatPeriod(performance.period)} · {performance.venue_normalized || performance.venue}
        </p>
        <div className="mt-auto flex flex-wrap items-center gap-1.5">
          <span className="rounded bg-black/5 px-2 py-0.5 text-xs dark:bg-white/10">
            {performance.genre}
          </span>
          <StatusBadge status={performance.status} />
        </div>
      </div>
    </Link>
  );
}

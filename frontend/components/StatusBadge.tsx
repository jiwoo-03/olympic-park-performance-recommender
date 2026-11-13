import type { PerformanceStatus } from "@/lib/types";

const STYLES: Record<PerformanceStatus, string> = {
  "확정 예정": "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  "매년 반복 예상": "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  "과거 유사 공연 — 참고용": "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400",
};

const HELP: Record<PerformanceStatus, string> = {
  "확정 예정": "예매 가능 — 아래 예매처에서 확인하세요",
  "매년 반복 예상": "매년 비슷한 시기에 열리는 공연으로, 공식 일정은 아직 미확정입니다",
  "과거 유사 공연 — 참고용": "이미 종료된 공연입니다. 취향 참고용으로만 보여드려요",
};

export default function StatusBadge({ status }: { status: PerformanceStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[status]}`}
      title={HELP[status]}
    >
      {status}
    </span>
  );
}

export function statusHelpText(status: PerformanceStatus): string {
  return HELP[status];
}

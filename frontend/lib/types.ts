export type PerformanceStatus =
  | "확정 예정"
  | "매년 반복 예상"
  | "과거 유사 공연 — 참고용";

export interface TicketLink {
  relatenm: string;
  relateurl: string;
}

export interface Performance {
  id: number;
  title: string;
  period: string;
  venue: string;
  venue_normalized: string;
  genre: string;
  cast: string | null;
  synopsis: string | null;
  min_age: number | null;
  price_min: number | null;
  price_max: number | null;
  popularity_score: number;
  poster: string | null;
  venue_kopis: string | null;
  ticket_links: string; // JSON 문자열 — parseTicketLinks()로 파싱
  status: PerformanceStatus;
}

export function parseTicketLinks(raw: string | null | undefined): TicketLink[] {
  if (!raw) return [];
  try {
    return JSON.parse(raw) as TicketLink[];
  } catch {
    return [];
  }
}

/** "YYYYMMDD YYYYMMDD" -> [시작일, 종료일] Date. 파싱 실패 시 null. */
export function parsePeriod(period: string): [Date, Date] | null {
  const m = period.match(/(\d{4})(\d{2})(\d{2})\s+(\d{4})(\d{2})(\d{2})/);
  if (!m) return null;
  const [, y1, mo1, d1, y2, mo2, d2] = m;
  const start = new Date(Number(y1), Number(mo1) - 1, Number(d1));
  const end = new Date(Number(y2), Number(mo2) - 1, Number(d2));
  return [start, end];
}

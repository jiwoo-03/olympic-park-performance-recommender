import type { Performance } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? `요청 실패 (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function listPerformances(params: { date?: string; genre?: string } = {}) {
  const qs = new URLSearchParams();
  if (params.date) qs.set("date", params.date);
  if (params.genre) qs.set("genre", params.genre);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return request<Performance[]>(`/performances${suffix}`);
}

export function getPerformance(id: number) {
  return request<Performance>(`/performances/${id}`);
}

export function recommendMe(sessionId: string) {
  return request<Performance[]>(`/recommend/me?session_id=${encodeURIComponent(sessionId)}`);
}

export function recommendSimilar(id: number) {
  return request<Performance[]>(`/recommend/similar/${id}`);
}

/** 주차 혼잡 예보 — 원본 데이터 수집이 막혀 있어 백엔드가 501을 돌려준다
 * (CLAUDE.md "알려진 이슈" 참고). 화면에서는 "준비 중"으로 보여준다. */
export async function parkingForecastAvailable(): Promise<boolean> {
  try {
    await request(`/parking/forecast?forecast_date=${new Date().toISOString().slice(0, 10)}`);
    return true;
  } catch {
    return false;
  }
}

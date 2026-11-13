// 로그인 없음 — 클라이언트가 만든 익명 session_id(랜덤 UUID)로 추천 노출 로그만 구분한다.
const SESSION_KEY = "op-session-id";

export function getSessionId(): string {
  if (typeof window === "undefined") return "";
  let id = window.localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = crypto.randomUUID();
    window.localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

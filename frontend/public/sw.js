// 홈 화면 설치(PWA) 요건 충족용 — 공연 데이터는 매일 바뀌므로 오프라인 캐싱은 하지 않는다.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});

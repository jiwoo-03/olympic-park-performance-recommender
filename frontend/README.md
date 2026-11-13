# frontend/

Next.js(App Router) + Tailwind CSS. 모바일 우선 반응형(공원 현장 접속 가정). 워크플로우
문서 4.6장의 화면 4종 + 추천 결과의 "예매 가능 여부" 안내(사용자 요청)를 구현한다.

상태: 완료 (6단계). 설계·구현 기록은 `tasks/todo.md` "6단계: 프론트엔드",
`tasks/verification.md` 참고.

## 화면 (2026-11-12 기준 — 홈 + 상세 2개뿐)

- `app/page.tsx`(홈) — **예매 가능한 공연**(`GET /recommend/me`, 장르 구분 없이 지금
  예매 가능한 상위 3개 — 장르 선택 UI는 2026-11-12에 없앴다, 아래 "폐기한 기능" 참고)
  + **날짜로 찾기**: 월별 달력(`components/PerformanceCalendar.tsx`)으로 공연 있는
  날짜를 점으로 표시하고 클릭하면 그 날 공연을 보여준다(코엑스류 박람회 캘린더 참고).
  장르 드롭다운으로 점 표시를 좁힐 수 있다(이건 검색용 필터라 남겨둠, 추천용 장르
  선택과는 다름). `GET /performances?genre=`(날짜 없이, 과거 공연은 기본 제외됨)를
  한 번 받아서 프론트에서 날짜별로 계산 — 새 백엔드 엔드포인트 없음.
- `app/performances/[id]/` — 상세 + 비슷한 공연(`GET /recommend/similar/{id}`) + 예매처
  링크 + 주차 예보(준비 중).

### 폐기한 기능 (만들었다가 사용 중 다시 뺀 것들, 2026-11-12)

- **올림픽공원 소식 게시판**: 실제 API(KCISA `meta/KSCkrep`)까지 받아서 테스트했지만
  날짜 필드(`regDate`)가 수집 시각일 뿐 실제 보도 날짜가 아니라 "최신순" 정렬이
  불가능해서 롤백.
- **온보딩(`app/onboarding/`, 장르 선택) + 장르별 "취향 추천"**: 예정 공연이 적은
  장르(뮤지컬·클래식·페스티벌·어린이)를 선택하면 실제로는 그 장르가 하나도 없어서
  엉뚱한 콘서트로 채워지는 버그가 재발해서, 장르 선택 자체를 없애고 "장르 무관 상위
  3개"(`recommend.bookable_top()`)로 단순화.
- **찜하기(`lib/favorites.ts`, 상세 페이지 버튼)**: 사용자 요청으로 삭제.
- **로그인(`app/login/`, `lib/auth.ts`) + 마이페이지(`app/mypage/`)**: 로그인을
  만들었다가 사용자 요청으로 삭제. 마이페이지는 로그인+찜이 둘 다 없어지면서 보여줄
  내용이 없어져 같이 삭제.

## 예매 가능 여부 안내 (`status`)

백엔드의 모든 공연 응답에 `status`가 붙는다(`components/StatusBadge.tsx`):

| status | 의미 | UI |
| --- | --- | --- |
| 확정 예정 | 지금 예매 가능 | 초록 배지 + "예매하기" 버튼(ticket_links) |
| 과거 유사 공연 — 참고용 | 이미 종료, 콘텐츠 참고용 | 회색 배지 + 카드 흐리게, 예매 버튼 없음 |

"매년 반복 예상"(반복 시리즈 예측)은 `scoring.INCLUDE_PREDICTED_SERIES = False`로
꺼서 지금은 안 나온다. "비슷한 공연"(`GET /recommend/similar/{id}`)은 콘텐츠 우선
모드(`CONTENT_FIRST_MODE`)로 과거도 참고용으로 섞여 나올 수 있어서 이 배지가 필요하지만,
홈의 "예매 가능한 공연"(`GET /recommend/me`)은 항상 과거를 제외하므로 사실상 "확정
예정"만 나온다.

## 실행

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_BASE가 백엔드 주소를 가리키는지 확인
npm run dev
# http://localhost:3000
```

백엔드(`backend/`)가 먼저 떠 있어야 한다.

## 테스트

- `npm run build`, `npm run lint` 통과 확인.
- 백엔드+프론트를 둘 다 로컬로 띄우고 Playwright(실제 Chromium)로 홈·공연 상세 화면을
  스크린샷까지 떠서 확인 완료(사용자가 sudo로 `playwright install-deps` 실행 후 재시도).
  이 과정에서 **`curl`/`TestClient`로는 못 잡는 버그 2건을 실제 브라우저 테스트로 발견**:
  1. **CORS 미설정** — 백엔드는 200을 돌려주는데 브라우저가 `Access-Control-Allow-Origin`
     헤더 없음을 이유로 응답을 막아서 `fetch`가 전부 실패하고 있었음. `backend/main.py`에
     `CORSMiddleware` 추가로 해결.
  2. **Next.js 16의 `allowedDevOrigins` 기본 차단** — `127.0.0.1`로 접근하면 dev 리소스가
     보안상 막혀서 클라이언트 `useEffect`가 아예 안 돌고 있었음(겉보기엔 "로딩 중"에
     멈춘 것처럼 보임). `next.config.ts`에 `allowedDevOrigins: ["127.0.0.1", "localhost"]`
     추가로 해결.
  둘 다 고친 뒤 재검증: 상태별(확정 예정/과거 유사 공연) 배지·예매 버튼 노출이 스크린샷
  상으로 전부 의도대로 렌더링됨을 확인(`tasks/verification.md` [2026-11-12] 참고).
- WSL에서 `/mnt/c/...` 경로라 서버 콜드 스타트가 느리다 — 포트가 뜰 때까지 넉넉히(40~90초)
  기다려야 하고, `npm run dev`를 재시작할 땐 로그에 "Another next dev server is already
  running" 경고가 없는지 확인할 것(없으면 PID로 직접 `kill -9` 해야 진짜 재시작된다).

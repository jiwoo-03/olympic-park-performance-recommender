# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 현재 상태

1~6단계 전부 완료(기획 → 데이터 수집 → 전처리·EDA → 추천 모델(콘텐츠 우선 모드 전환,
Precision@5 0.200→0.855) → `backend/`(FastAPI) → `frontend/`(Next.js)), 실제 Chromium
연동 테스트까지 마쳤다. 그 뒤 실사용 중 나온 요청으로 여러 번 추가·롤백을 거쳐
**지금(2026-11-12) 최종 상태는 의도적으로 매우 단순**하다 — 화면은 홈(예매 가능한
공연 3개 + 달력)과 공연 상세 2개뿐, 로그인·찜하기·온보딩(장르 선택)·소식 게시판은
전부 만들었다가 문제가 생기거나 필요가 없어져서 도로 뺐다. DB에 남은 테이블은 추천
노출 로그(`RecLog`) 하나뿐이다. 이 과정에서 발견한 버그·되돌린 이유는 전부 아래
"알려진 이슈"와 `tasks/todo.md` "추가 기능 요청"/"추가 수정 작업"에 기록돼 있다 —
핵심만 요약하면:
- 장르별 "취향 추천"(온보딩)은 예정 공연이 적은 장르에서 엉뚱한 장르로 채워지는 버그가
  있어 폐기 → 장르 무관 "지금 예매 가능한 공연 상위 3개"(`recommend.bookable_top()`)로
  교체.
- 찜하기·로그인은 만들었다가 사용자 요청으로 삭제. 둘 다 없어지며 마이페이지도 같이 삭제.
- 반복 시리즈 다음 회차 예측("매년 반복 예상")은 `scoring.INCLUDE_PREDICTED_SERIES`로 끔.
- "올림픽공원 소식 게시판"은 실제 API(KCISA)까지 테스트했지만 날짜 필드를 못 믿어서 롤백.
- "미분류" 장르가 드롭다운에 없는데 화면에 새는 버그를 발견·수정(제목 키워드 보강 +
  방어적 필터).
4.7장(테스트·개선) 중 **pytest 단위·통합 테스트(43건)·Lighthouse 성능 점검 완료**했다 —
`recommender/tests/`·`pipeline/preprocessing/tests/`·`backend/tests/`에 각각
작성, 세 디렉터리 전부 독립 실행으로 통과 확인. Lighthouse는 레이아웃 밀림(CLS)
2건·접근성 2건을 실제로 찾아 고쳤고(홈 Accessibility 89→100, CLS 전부 0), 보조
텍스트 색상 대비 미달 1건은 당시엔 앱 전체 디자인 토큰 문제라 디자인 다듬기 단계로
미뤘었는데 **2026-11-13에 해결 완료**(아래 "디자인 다듬기" 참고). 4.7장은 이걸로 사실상
끝 — 남은 "사용성 테스트 5명"은 날짜·참가자가 아직 안 정해져서 사용자가 일정을 잡으면
이어서 진행한다.

**8단계(배포) 선행 블로커 2가지는 2026-11-13에 전부 해결 완료**: (1) 이 폴더가 git
저장소가 아니던 문제 → `git init` + GitHub 원격 저장소(`jiwoo-03/
olympic-park-performance-recommender`, public) 연결·push까지 완료. (2) `.gitignore`가
`data/processed/*`를 전부 무시해서 배포하면 빈 화면만 뜨던 문제 → `performances.csv`·
`performance_vectors.npz`를 예외로 추가해 커밋 완료. 상세 실행 기록은 `tasks/todo.md`
"8단계: 배포" 참고. **배포 용도 재확인(2026-11-14)**: 공모전 심사 발표에서 QR코드로
모바일 시연하는 용도로만 쓴다(상시 운영 서비스 아님) — 이에 맞춰 백엔드 호스팅
**Render** 확정, GitHub Actions 매일 재수집 자동화는 이번엔 생략하기로 결정.
**본작업 A·B·C단계 완료(2026-11-14)**: A(로컬 준비) — 출처 문구를 화면 footer에도
추가(`frontend/app/layout.tsx`), `backend/main.py` CORS를 `ALLOWED_ORIGIN` 환경변수
기반으로 변경, `backend/README.md`·루트 `README.md`에 Render Start Command·설정값
문서화. B(외부 계정, 사용자 직접) — Render·Vercel 둘 다 실제 배포 완료:
- 백엔드(Render): `https://olympic-park-performance-recommender.onrender.com`
- 프론트(Vercel): `https://olympic-park-performance-recommende.vercel.app`
  (Vercel이 처음 보여준 랜덤 해시 URL은 로그인 필요한 Preview였음 — Settings→Domains의
  해시 없는 production 도메인을 써야 함, `tasks/verification.md` [2026-11-14] 참고)

C(마무리) — Render `ALLOWED_ORIGIN`을 실제 Vercel 도메인으로 설정 → push 후 재배포되며
반영 확인(허용 Origin만 CORS 통과, 그 외는 차단 확인). README에 실제 URL 반영.
D(QR코드 생성) — 손으로 짠 JS 인코더 대신 이 환경에 이미 설치돼 있던
`libqrencode.so.4`(apt `libqrencode4`, 새 설치 없음)를 Python `ctypes`로 직접 호출해
신뢰도 있는 QR을 생성(버전 4, 33×33), 시스템 `PIL`로 PNG 렌더링 후 육안 검증, 앱 브랜드
토큰을 재사용한 Artifact 페이지로 제작·게시
(https://claude.ai/code/artifact/1e15f486-59f7-44f8-b2bc-27e0ac06b169).

**8단계(배포) 본작업 A~E 전부 완료(2026-11-14)**. 공개 URL: 백엔드
`https://olympic-park-performance-recommender.onrender.com`, 프론트
`https://olympic-park-performance-recommende.vercel.app`. 남은 건 발표 자료(사용자
작업 영역)와 발표 당일 QR 실제 스캔 리허설(사용자가 직접 — 이 환경은 카메라로 스캔
검증 불가)뿐.

**디자인 다듬기(9단계, 완료, 2026-11-13~14)**: 사용자가 올림픽공원 공식 심볼마크
파일을 제공하며 시작. Artifact로 시안을 먼저 만들어 승인받은 뒤 단계적으로 반영 —
(1) 포스터 없는 공연의 회색 빈 박스를 심볼마크 색 기반 그라데이션으로 교체
(`frontend/lib/posterGradient.ts`), (2) 심볼마크 링 그래픽에서 실제 추출한 브랜드
팔레트(`frontend/app/globals.css`의 `--brand`/`--teal`/`--sky`/`--lime`/`--amber`/
`--stone` 등)로 기존 Tailwind 기본 회색·장르색을 전부 교체 — 이 과정에서 Lighthouse가
찾아놓고 못 고쳤던 보조 텍스트 대비 미달 문제(`text-gray-400/500` 등)도 전부 WCAG AA
(4.5:1) 검증된 `--muted`/`--stone` 토큰으로 교체해 해결, (3) 앱바에 심볼마크 로고칩
추가(`frontend/public/olympic-park-mark.png`). 달력 주말 색상은 처음에 브랜드 팔레트로
통일했다가 사용자 요청으로 "일요일=빨강/토요일=파랑" 관례를 복구(`--sunday`/`--saturday`
전용 토큰, 브랜드 팔레트와 분리). **이 작업 전체가 2026-11-14까지 로컬에만 있고 git에
커밋된 적이 없어서, 이미 배포된 `layout.tsx`가 참조하는 로고 파일이 Vercel에 없어
배포 사이트에서 404(깨진 로고)로 나타나는 버그가 있었음** — 사용자가 QR로 실제
배포 사이트를 열어보고 발견, 9단계 전체를 커밋·push해서 해결(교훈은
`tasks/lessons.md` [2026-11-14] 참고). 상세는 `tasks/todo.md` "9단계: 디자인 다듬기"
참고.

**PWA(10단계, 완료, 2026-11-14)**: QR로 링크를 받은 사람이 "앱을 다운로드해서
사용"하고 싶다는 요청 → 네이티브 앱(APK 등)은 공모전 일정에 안 맞아서 **홈 화면
설치(PWA)**로 결정. `frontend/app/manifest.ts`(Next.js 자동 `/manifest.webmanifest`
서빙)·`frontend/public/sw.js`(설치 조건만 충족, **오프라인 캐싱은 의도적으로 안 함**
— 공연 데이터가 매일 바뀌어서 캐싱하면 오래된 데이터를 보여줄 위험)·아이콘 4종
(`frontend/public/icons/`, 이미 있던 `PIL`로 로고에서 생성, 새 설치 없음) 추가.
Lighthouse 13.6.0은 PWA 카테고리를 완전히 제거해서 자동 감사 불가 — 대신 `curl`로
매니페스트 JSON·서비스워커·아이콘·메타태그를 전부 수동 검증. 상세는
`tasks/todo.md` "10단계: PWA" 참고. **남은 건 사용자가 실제 폰으로 "홈 화면에 추가"
확인뿐**(이 환경은 실기기 설치 UX 재현 불가).

폴더 구조는 `pipeline/`·`recommender/`·`backend/`·`frontend/` 전부 완료 상태다. 자세한
역할은 아래 "폴더 구조" 참고.
`올림픽공원_공연추천시스템_웹개발_워크플로우.md`는 **지금 우리가 진행할 목적과 계획이
담긴 계획서**이자 요구사항·아키텍처·일정의 단일 소스(source of truth)다. 이 문서의
결정사항과 충돌하는 구현을 임의로 선택하지 말고, 모호한 부분은 문서의 "확인할 것"
체크리스트를 따른다.

**작업 규칙**: 작업(스크립트 실행, 단계 진행, 코드 수정 등)이 끝나고 나면 매번 반드시
이 "현재 상태" 섹션(과 "알려진 이슈")을 실제 결과로 갱신한다.

### 알려진 이슈

**미해결 블로커**

- `collect_parking_weather.py`(차량 입출차·날씨): 504 Gateway Timeout. **주차 혼잡
  예보 모델·실시간 차량 입출차 UI는 이 데이터 없이는 착수 불가** — 4주차 전 해결 필요.
  2026-11-12에 사용자가 찾아온 새 키·새 게이트웨이(`API_CPM_008`, 차량 입출차 전용)로도
  재시도했지만 똑같이 504 — 키 문제가 아니라 제공기관 백엔드 자체 장애로 확정됨.
  재시도 방법은 [`pipeline/collection/REPORT.md`](./pipeline/collection/REPORT.md) 참고.
  (추천 모델 진행에는 영향 없음 — 별도 기능)

**해결됨 (참고용 — 다시 건드릴 필요 없음)**

- 매칭된 공연의 `period`가 항상 KSPO 쪽 기간을 써서, KOPIS 쪽 기간이 더 긴 경우(공연
  연장 등, "백 번째 리뷰": KSPO 8/30 종료, KOPIS 12/27 종료)를 놓치는 문제 → KSPO/KOPIS
  두 옵션을 실제로 비교한 결과(매칭 646건 중 날짜 다른 23건 전부 KOPIS 종료일이 KSPO보다
  짧은 적 없음) **매칭된 공연은 KOPIS 기간을 쓰도록 결정·구현**
  (`normalize_and_clean.resolve_period()`). Precision@5 0.800→0.855로 개선.
- 사용자가 "장르를 다르게 선택해도 같은 공연이 나오는 오류는 없었냐"고 확인을 요청해서
  6개 장르를 직접 대조해보니, "스포츠/기타"를 선택하면 "콘서트"와 **완전히 동일한 5건**이
  나오는 버그가 있었음 — `vectorize.NO_GENRE_SIGNAL`(스포츠/기타는 장르 신호를 0으로
  죽임)과 `recommend.build_profile_vector`(사용자 프로필 생성)가 서로 다른 기준을 써서,
  모든 공연과의 유사도가 똑같이 0이 돼 인기도 순위(=콘서트 랭킹)로 조용히 대체되던 것.
  `build_profile_vector`가 `NO_GENRE_SIGNAL`을 참조하도록 수정 — 이제 "스포츠/기타"는
  콜드스타트로 정상 대체됨(나머지 5개 장르는 서로 고유한 리스트 반환 확인). 교훈은
  `tasks/lessons.md` [2026-11-12] "신호를 죽인 특성은 프로필/쿼리 쪽에서도 똑같이
  죽여야 한다" 참고.
- **[중요] 오프라인 평가에서 발견했던 "예정 공연 부족" 문제 → 설계 전환으로 해결**:
  매칭된 공연 651건 중 안 끝난 공연이 13건뿐(콘서트 12 + 스포츠/기타 1, 나머지 장르 0건,
  워크플로우 문서 7장 리스크 1번 실측 확인)이었던 문제를, 재수집·매칭 개선으로는 못
  풀고 **추천 방식 자체를 바꿔서 해결**했다: (1) 반복 시리즈 다음 회차 예측(`series.py`,
  규칙 기반), (2) 취향 추천·비슷한 공연은 날짜 무관하게 콘텐츠로 추천 후 상태(확정 예정/
  매년 반복 예상/과거 유사 공연) 표시, (3) `scoring.CONTENT_FIRST_MODE` 스위치로 — 한국
  체육산업개발이 실제 서비스로 채택해 미래 일정이 충분해지면 `False`로 바꿔서 원래
  설계(확정 공연만 추천)로 되돌릴 수 있게 구성. 결과: Precision@5 0.200→0.800. 조건
  추천·콜드스타트는 이 스위치와 무관하게 항상 날짜 기반 유지(특정 날짜를 묻는 기능에
  과거 공연을 보여주면 안 되므로). 상세는 [`recommender/REPORT.md`](./recommender/REPORT.md)
  "설계 전환" 참고.

- `collect_kspo_venue_rental.py`(대관정보, `meta12` 게이트웨이): 401 Unauthorized.
  문체부 통합 공연정보 API로 같은 정보를 대체 확보해 영향 없음. **2026-11-12 재확인**:
  사용자가 새 키를 찾아와서 재시도 → 401은 해결(200, 717건)됐지만, 날짜 필드
  (`temporalCoverage`)가 100건 전부 빈 값이라 "공연처럼 일정을 보여주는" 용도로는
  여전히 못 씀 — 날짜 없는 과거 대관 이력 아카이브일 뿐. 기존 대체 데이터(문체부 통합
  API+KOPIS 매칭, 실제 기간 포함)가 더 나아서 그대로 사용. 같은 API 재시도 불필요
  (`pipeline/collection/REPORT.md` 4절 참고).
- KSPO-KOPIS 매칭률 33%(미분류 63%) → 미분류는 장르 기반 추천에서 제외하고
  `recommender/venue_fallback.py`로 같은 장소의 다른 공연을 부가 노출하기로 결정·구현 완료.
- KOPIS 상세의 `sty`(줄거리)가 812건 중 **12건(1.5%)만** 채워져 있음 → "출연진+줄거리
  임베딩"은 실제로는 출연진·제목 위주로 구성(상세는 `tasks/verification.md` [2026-11-12]).
- 인기도(예매상황판) 신호가 KOPIS 상세엔 없었음(`visit`은 내한공연 여부일 뿐) → 별도
  박스오피스 API(`collect_kopis_boxoffice.py`)로 수집해 `performances.csv`의
  `popularity_score` 컬럼으로 조인 완료. 매칭 공연 651건 중 77건(11.8%)이 신호를 가짐.

상세 내역은 [`pipeline/preprocessing/REPORT.md`](./pipeline/preprocessing/REPORT.md) 5절과
`tasks/todo.md` "0. 데이터 보강", `tasks/verification.md` 참고.

- **[중요] `backend`+`frontend`를 `TestClient`/`npm run build`만으로 검증하고 "완료"로
  표시했다가, 실제 Chromium(Playwright)으로 연동 테스트하니 홈·상세 화면이 전부 "불러오는
  중..."에서 멈추는 문제** → 두 가지 진짜 버그가 겹쳐 있었음: (1) 백엔드에 `CORSMiddleware`가
  없어서 브라우저가 `Access-Control-Allow-Origin` 헤더 없음을 이유로 `fetch`를 전부 차단
  (`TestClient`는 CORS를 검사 안 해서 못 잡음) — `backend/main.py`에 추가로 해결. (2) Next.js
  16이 `127.0.0.1`로의 dev 리소스(HMR 등) 요청을 기본으로 차단해서 클라이언트 `useEffect`가
  통째로 안 돌고 있었음 — `next.config.ts`에 `allowedDevOrigins: ["127.0.0.1", "localhost"]`
  추가로 해결. 둘 다 고친 뒤 재검증한 스크린샷에서 상태별(확정 예정/과거 유사 공연) 배지·
  예매 버튼 노출이 의도대로 렌더링됨을 확인. 교훈은 `tasks/lessons.md` [2026-11-12] "API
  단위 테스트가 통과해도 실제 브라우저로 한 번은 때려봐야 한다" 참고.

- **"미분류" 장르가 장르 드롭다운엔 없는데 달력에 새어나오는 버그**(사용자 발견,
  "정승환 콘서트"가 미분류로 뜸) → `normalize_and_clean.classify_genre()`가 KOPIS
  매칭 안 된 공연은 제목에 "콘서트"라고 써 있어도 분류 규칙이 없어서 전부 미분류로
  떨어지던 게 원인(미분류 1,247건 중 475건이 제목에 콘서트 포함). 매칭 안 된 행
  전용 키워드 폴백을 추가해 해결 — **매칭된 공연에는 적용 안 함**(처음엔 전체
  적용했다가 KOPIS가 이미 "클래식"으로 정확히 분류해둔 공연까지 덮어써서 클래식이
  18→9건으로 반토막 나는 회귀를 실측으로 잡고 범위를 좁혔다, `tasks/lessons.md`
  [2026-11-12] 참고). `backend/performances_store.py`에도 "미분류" 방어적 제외를
  추가해서 앞으로 비슷한 누락이 또 생겨도 달력에 안 새게 함. Precision@5는 0.855로
  그대로(회귀 없음, `vectorize.py`+`evaluate.py` 재실행 확인).
- **올림픽공원 소식 게시판용으로 받은 KCISA 보도자료 API(`meta/KSCkrep`)를 테스트해보고
  기능 자체를 뺌** — 호출은 성공(`resultCode: 0000`, 1,080건, 필드는 `title`·
  `description`(이미지 포함 raw HTML)·`creator`·`collectionDb` 정도만 실제로 채워짐).
  **`regDate`가 실제 보도 날짜가 아니라 문화공공데이터광장 수집 시각**이라(같은 페이지의
  2017년 글과 2024년 글이 regDate가 똑같음), "최신순" 게시판에 못 씀. 본문에서 정규식으로
  날짜 추출도 시도했으나 100건 중 2건만 매칭(그마저 보도 날짜 아닌 본문 중 언급)돼서
  포기 — 홈(`/`)은 추천+검색 화면으로 유지, `/recommend` 라우트·네비게이션 추가분은
  롤백. **같은 API를 다시 시도할 필요 없음** — 날짜 필드 문제는 API 자체의 한계라
  재시도해도 똑같다. 상세는 `tasks/todo.md` "추가 기능 요청" 5번 참고.

- **pytest 단위·통합 테스트 43건 작성·통과** — `recommender/tests/`(22건)·
  `pipeline/preprocessing/tests/`(6건, "미분류" 버그 회귀 포함)·`backend/tests/`
  (15건, 삭제한 엔드포인트 5개가 404로 남아있는지 포함). 세 디렉터리는 서로 다른
  이름의 `common.py`를 갖고 있어서 **독립적으로 실행**해야 한다(`cd recommender &&
  ../.venv/bin/python3 -m pytest tests/` 식) — 루트에서 한 번에 `pytest .`로 돌리면
  모듈 캐싱 충돌 위험이 있다.
- **Lighthouse 성능 점검(프로덕션 빌드, 홈+상세 2페이지)에서 실제 버그 2종 발견·수정**:
  1. **레이아웃 밀림(CLS)** — 상세 페이지 포스터 `<img>`에 width/height가 없어서
     로딩 전/후로 레이아웃이 크게 밀림(CLS 0.467) + 홈 달력이 "불러오는 중..." 텍스트
     → 전체 그리드로 바뀌면서 더 크게 밀림(CLS 0.328~0.357). 둘 다 "로딩 중에도 빈
     틀(그리드·범례·점 칸)을 미리 같은 높이로 그려둔다"는 같은 원리로 고쳐서 **CLS
     전부 0**으로 만들었다.
  2. **접근성** — 장르 `<select>`에 `aria-label` 없음, 달력 주말 색상
     (`text-rose-500`/`text-sky-500`)이 흰 배경 대비 WCAG AA(4.5:1) 미달(2.7~3.75)
     → 라벨 추가 + 실제 명도 대비를 계산해서 통과하는 `-600`/`-700` shade로 교체.
     홈 Accessibility 89→100.
  - **보류한 것**: 카드·배지류의 `text-gray-400/500` 보조 텍스트가 여러 컴포넌트에서
    WCAG AA 미달(2.19~4.36)인데, 이건 컴포넌트 하나가 아니라 앱 전체 "보조 텍스트"
    색상 토큰 문제라 디자인 다듬기 단계로 넘김(지금 임의로 전체 색상 체계를 바꾸지
    않음).
  - **환경 사고**: `npx lighthouse`가 Chrome 프로필을 `C:\Users\...` 형태의 리터럴
    파일명으로 `frontend/` 안에 만들어버려서 `next build`가 실패한 적이 있음 —
    `--user-data-dir`을 스크래치패드 경로로 명시하고 실행 위치도 옮겨서 해결, 생성된
    잔재는 삭제함. **같은 디렉터리에서 lighthouse를 바로 실행하지 말 것.**
  - 서버 재시작 중 이전 PID가 포트를 계속 쥐고 있어서 "재시작"이 조용히 실패한 경우가
    2번 더 있었음(`app.db` 핸들 꼬임으로 500 재발, `next start` 포트 충돌로 옛 빌드가
    계속 응답) — 매번 `ss -ltnp`로 실제 PID 확인 후 `kill -9`로 해결.
  - 최종 점수(로컬 HTTP, WSL 환경이라 절대값보다 "회귀 없음"에 의미를 둘 것): 홈
    Performance 86·Accessibility 100·Best Practices 77·SEO 100, 상세 Performance
    79·Accessibility 96·Best Practices 77·SEO 100. Best Practices 77은 로컬
    HTTP(비보안) 테스트 특성 + KOPIS 포스터가 `http://`라 뜨는 쿠키 경고 때문이라
    배포 환경/외부 데이터 제약상 지금 코드로는 못 고침. 상세는
    `tasks/verification.md` [2026-11-13] 참고.

## 작업 기록 (`tasks/`)

- 작업을 시작하기 전에 계획을 [`tasks/todo.md`](./tasks/todo.md)에 적는다.
- **작업 수행이 끝나면 항상 검증 단계를 거친다.** 무엇을·어떻게 확인했는지, 통과/실패 결과를
  [`tasks/verification.md`](./tasks/verification.md)에 기록한다.
- 그 검증 기록에서 실수나 잘못이 드러나면, 또는 [`tasks/lessons.md`](./tasks/lessons.md)에
  적힌 "실행 조건" 중 하나라도 충족되면(사용자가 결과물이 잘못됐다고 말하거나, 패턴·스타일·
  접근을 바로잡거나, 실수를 반복했다는 걸 깨닫는 등) 그 문서의 형식(Trigger/Pattern/Rule/
  Files affected)대로 기록해 같은 오류를 반복하지 않도록 한다.
- [`tasks/session-log.md`](./tasks/session-log.md)는 **세션을 기록하는 장소**다 — 세션마다
  한 일·막힌 점·다음 할 일을 여기에 남긴다.

## 폴더 구조

```
pipeline/        # 오프라인 배치: 수집(collection/)·매칭·정제(preprocessing/)·임베딩(미착수)
recommender/     # 추천 점수 계산 모듈(4단계 완료) — venue_fallback·vectorize·scoring·series·recommend·evaluate
backend/         # FastAPI, 저장소 읽기 전용(5단계 완료) — database·models·schemas·performances_store·main
frontend/        # Next.js(6단계 완료) — app/{onboarding,page,performances/[id],mypage}, lib/, components/
```

## 단계별 실행

```bash
# 1. 데이터 수집 (.env에 서비스키 4종 필요, .env.example 참고)
cd pipeline/collection && pip install -r requirements.txt && python run_all.py

# 2. 전처리·EDA (data/raw 필요; match_performances → normalize_and_clean → eda 순서)
cd pipeline/preprocessing && pip install -r requirements.txt && python run_all.py

# 1+2를 체이닝: cd pipeline && python run_all.py

# 3. 추천 모델: recommender/vectorize.py → evaluate.py (평가표는 recommender/REPORT.md)

# 4. 백엔드 (이 저장소는 .venv에 pip가 없어 get-pip.py로 부트스트랩했음 — backend/README.md 참고)
cd backend && ../.venv/bin/pip install -r requirements.txt
../.venv/bin/python3 -m uvicorn main:app --reload   # http://127.0.0.1:8000/docs

# 5. 프론트엔드 (backend가 먼저 떠 있어야 함)
cd frontend && npm install && npm run dev   # http://localhost:3000
```

빌드·린트: `cd frontend && npm run build && npm run lint`. 로컬에서 서버(uvicorn/Next dev)를
띄울 때 WSL의 `/mnt/c/...` 경로라 콜드 스타트가 느릴 수 있다 — curl로 확인할 때 짧게
기다리다 포기하지 말고 40초 이상 폴링할 것(`backend/README.md` 참고, 한 번 "포트를 열면
세션이 죽는다"고 잘못 결론 낸 적 있음).

## 프로젝트 개요

올림픽공원 내 공연(KSPO DOME, 우리금융아트홀, 핸드볼경기장, 88잔디마당, 수변무대 등)을
사용자의 장르·아티스트 취향, 방문 날짜, 동행 유형(가족/연인/혼자), 예산에 맞춰 추천하고,
공연 당일 주차 혼잡도 예보까지 함께 보여주는 웹 서비스. 예매는 직접 처리하지 않고 외부
예매처 링크로 연결한다. 8주 MVP 목표.

## 아키텍처: 배치/온라인 분리

핵심 설계 원칙은 **임베딩·추천 계산을 매일 배치로 미리 끝내고, 웹 서버는 조회·필터·정렬만
수행**하는 것이다. 이렇게 해야 무료 호스팅 티어에서도 응답 속도를 확보할 수 있다.

```
오프라인 (GitHub Actions, 매일)
  KSPO 공연정보 API + 문체부 통합 공연 API + KOPIS 공연 상세
    → 배치 파이프라인 (수집·KOPIS 매칭 → 장르 통일·정제 → 신규 공연 임베딩 → 종료 공연 제외)
    → 저장소 (PostgreSQL: performances/venues/favorites/rec_logs, FAISS: 공연 임베딩)

온라인 (사용자 요청)
  사용자 → React(Next.js) 프론트엔드(Vercel) → FastAPI 백엔드(Render)
    → 저장소를 읽기만 하고 추천 로그만 기록
```

## 기술 스택

| 영역 | 기술 | 비고 |
| --- | --- | --- |
| 데이터 처리 | Python, pandas, KoNLPy, rapidfuzz | XML 파싱, 줄거리 형태소 분석, 출처 간 공연명 매칭 |
| 추천 | scikit-learn(TF-IDF), sentence-transformers, FAISS | 베이스라인 TF-IDF, 개선안은 한국어 문장 임베딩(`jhgan/ko-sroberta-multitask`) |
| 백엔드 | FastAPI, SQLAlchemy | Swagger 문서 자동 생성 |
| DB | PostgreSQL (개발 단계는 SQLite) | |
| 프론트엔드 | React(Next.js), Tailwind CSS | 모바일 우선 반응형 |
| 배포·자동화 | Vercel(프론트), Render/Railway(백엔드·DB), GitHub Actions(매일 재수집) | 전부 무료 티어 기준 |

## 데이터 소스와 매칭

4개 소스의 실제 수집 결과·엔드포인트·매칭 방법은
[`pipeline/collection/REPORT.md`](./pipeline/collection/REPORT.md)와
[`pipeline/preprocessing/REPORT.md`](./pipeline/preprocessing/REPORT.md)에 기록되어 있다.
설계 근거는 워크플로우 문서 2장·4.2~4.3장 참고.

## 추천 로직 / DB 스키마 / API

워크플로우 문서 4.4~4.5장, 6장 참고 — 이 문서에서 중복 서술하지 않는다.

## 꼭 지켜야 하는 규칙

- API 핸들러에 임베딩 계산이나 외부 API 호출을 넣지 말 것 — 그건 배치 파이프라인의 책임이다.
- 서비스키(KOPIS 등)는 `.env`로 분리하고 커밋하지 않는다.
- 배포 URL과 README에 "한국체육산업개발 공공데이터 활용" 출처 표기가 필수(공모전 요건).
- 포스터 이미지는 KOPIS가 제공하는 범위만 사용.
- 공연 상세 화면에는 "예매처에서 최종 확인" 안내를 넣는다.
- 워크플로우 문서의 결정사항과 충돌하는 구현을 임의로 선택하지 않는다 — 모호하면 문서의
  "확인할 것" 체크리스트를 따른다.
- **모든 실행 작업(스크립트·커맨드 실행, 파이프라인 구동 등)은 사용자 승인 없이 임의로
  실행하지 않는다** — 실행 전에 무엇을 실행할지 설명하고 사용자 승인을 받은 뒤에만 실행한다.
- **`data/raw`의 원본 파일은 절대 손상시키지 않는다** — 수정·삭제·덮어쓰기하지 않고
  읽기 전용으로만 취급한다. 재수집은 `pipeline/collection`의 수집 스크립트로만 하고,
  원본을 직접 고치지 않는다. **수집 스크립트 자체도 이 규칙을 지켜야 한다**: 여러 건을
  개별적으로 가져오며 일부 실패를 허용(catch-and-continue)하는 스크립트는, 실패가
  갑자기 늘어난 상황에서 적게 수집된 결과로 기존 파일을 덮어쓰지 않도록 merge/중단
  안전장치가 있어야 한다(실제로 이 규칙이 없어서 812건 → 565건 데이터 손상이 났던 사고가
  있었음 — `tasks/lessons.md` [2026-11-12] 참고).

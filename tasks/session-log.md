# Session Log

## 2026-11-11
- 한 일: CLAUDE.md를 실제 진행 상황(1~3단계 완료)에 맞게 재작성. `tasks/` 폴더
  (todo.md, lessons.md, session-log.md) 생성 및 CLAUDE.md에 작업 기록 규칙 추가.
  `01_data_collection/`, `02_eda_preprocessing/`를 `pipeline/collection/`,
  `pipeline/preprocessing/`로 이동하고 `recommender/`, `backend/`, `frontend/`
  빈 폴더(+README) 추가. 이동에 따라 `common.py`의 `PROJECT_ROOT` 깊이, 문서 내
  경로 참조(README.md, CLAUDE.md, REPORT.md, run_all.py 독스트링) 전부 갱신.
- 막힌 점·확인할 것: 없음. `PROJECT_ROOT` 재계산은 각 폴더에서 직접 실행해 검증함.
- 다음에 할 일: 4단계 추천 모델(`recommender/`) 착수.
- 추가: CLAUDE.md "현재 상태"에 폴더 재구성 사실(pipeline/recommender/backend/frontend) 한
  문장으로 반영.

## 2026-11-12
- 한 일: tasks/todo.md에 4단계 추천 모델 계획 작성. "미분류 장르" 처리 방침을 사용자와
  논의해 "같은 장소의 다른 공연 부가 노출"로 결정. "0. 데이터 보강" 선행 작업 수행:
  `match_performances.py`·`normalize_and_clean.py`에 `synopsis`(KOPIS sty)·
  `venue_normalized` 컬럼 추가, `recommender/venue_fallback.py`(같은 장소 부가 추천) 구현.
  승인받아 `pipeline/preprocessing` 재실행 후 검증, `tasks/verification.md`에 기록.
  이어서 인기도 신호 문제 해결: 사용자가 KOPIS 박스오피스 API URL(`/boxoffice`)을 찾아와서
  테스트 호출로 유효성·커버리지 확인(2025년 1월 상위 50건 중 17건이 올림픽공원 공연) →
  `collect_kopis_boxoffice.py` 작성, `pipeline/collection/run_all.py`에 등록, 승인받아
  실행 → `data/raw/kopis/boxoffice.json`(최근 12개월, 600건/distinct 424건, 올림픽공원
  겹침 84건) 생성 확인.
  이어서 `normalize_and_clean.py`에 `build_popularity_map()`을 추가해 `boxoffice.json`을
  `kopis_mt20id`로 조인, `performances.csv`에 `popularity_score`(0~1) 컬럼 생성 → 재실행해
  매칭 651건 중 77건(11.8%)이 신호를 가짐을 확인, 상위권이 실제 대형 K-pop 투어인 것도 확인.
  이로써 "0. 데이터 보강" 선행 작업 4개 전부 완료.
  이어서 "1. 공연 벡터" 착수: `recommender/common.py`, `vectorize.py` 작성(장르 원-핫 +
  출연진/제목/줄거리 TF-IDF, FAISS·KoNLPy는 베이스라인 단순화로 보류) → 승인받아 실행 →
  `UserWarning`(np.divide에 out= 누락, 잠재 버그) 발견해 수정 → 같은 가수 공연 쌍 유사도
  0.766 vs 무작위 콘서트 0.500으로 기능 검증 → `data/processed/performance_vectors.npz` 생성.
  이로써 "0. 데이터 보강"·"1. 공연 벡터" 모두 완료.
- 막힌 점·확인할 것: 없음.
- 이어서 "2. 추천 로직" 착수: `recommender/scoring.py`(기간 파싱·종료 판별·날짜 근접도·
  최종 점수·MMR 재정렬), `recommend.py`(취향/조건/비슷한 공연/콜드스타트 4개 함수) 작성 →
  승인받아 실제 데이터로 1회씩 호출 → 처음엔 버그로 보였던 2가지(같은 가수 공연이 비슷한
  공연에 안 뜸, 조건 추천 1건만 나옴)를 디버깅했는데 둘 다 정상 동작으로 확인(각각 "이미
  끝난 공연 제외", "예산 필터가 실제로 걸러낸 것"). 이로써 "0~2번"까지 전부 완료.
- 막힌 점·확인할 것: 없음.
- 사용자가 "미분류 제외한 메인 후보 중 취향과 안 맞는 군집이 있는지" 확인을 요청해서 조사:
  "스포츠/기타" 장르가 서커스/마술·연극·대중무용·전통무용을 뭉친 잡동사니 버킷이라, 장르만
  같아도 완전히 무관한 두 공연이 유사도 0.5를 받는 가짜 군집을 발견 → `vectorize.py`에
  `NO_GENRE_SIGNAL` 추가해 이 장르의 원-핫 신호를 0으로 만들고 재실행·재검증(마술-연극
  0.5→0.0, 콘서트-콘서트는 그대로) → `lessons.md`에 일반화된 교훈("기타류 캐치올 버킷은
  원-핫에 그대로 쓰면 안 됨") 기록.
  이어서 사용자가 `top_k`에 상한이 없는 걸 지적(데이터가 쌓이면 결과가 무한정 커질 위험) →
  `scoring.MAX_TOP_K=20` 추가해 `recommend.py` 4개 함수 전부 clamp, `taste_recommend`가
  MMR로 뽑은 뒤 점수 내림차순으로 재정렬하도록 수정 → `top_k=9999` 테스트로 확인.
  이어서 "3. 오프라인 평가" 착수: `recommender/evaluate.py` 작성(가상 프로필 30개 = 장르
  6종×5명) → 승인받아 실행 → Precision@5가 콘서트만 1.0, 나머지 5개 장르는 거의 0으로
  나와서 버그인지 디버깅 → **버그 아니었음**: 매칭 공연 651건 중 안 끝난 공연이 13건뿐
  (콘서트 12 + 스포츠/기타 1), 뮤지컬·클래식·페스티벌·어린이는 예정 공연 0건이라 구조적으로
  추천할 게 없었던 것(워크플로우 문서 7장 리스크 1번 실측 확인). `recommender/REPORT.md`에
  정리하고 CLAUDE.md "알려진 이슈"에 사용자 결정이 필요한 항목으로 추가. 이로써 4단계
  (0~3번) 전부 완료.
- 막힌 점·확인할 것: **오프라인 평가 결과, 데모 전 데이터 재수집/폴백 로직/투명 공개 중
  하나를 사용자가 결정해야 함**(`recommender/REPORT.md` "결론 및 제안" 참고).
- 다음에 할 일: 위 결정 이후 5단계 `backend/`(FastAPI) 착수.

## 2026-11-12 (계속)
- 한 일: 오프라인 평가에서 나온 "뮤지컬/클래식/페스티벌/어린이 예정 공연 0건" 문제에 대해
  사용자와 두 가지를 논의: (1) 재수집으로 완화되는지 시도, (2) "오늘 하는 공연"이 아니라
  "예매 가능한 공연" 기준으로 추천하는 게 어떤지. 조사 결과: `is_ended()`는 이미 미래
  공연까지 포함하고 있었고, KOPIS의 `prfstate` 필드는 수집 시점 스냅샷이라 오히려 부정확함을
  확인(현재 방식이 맞는 방향). 조사 중 "백 번째 리뷰"(연극, 아직 안 끝남)가 매칭에서
  빠진 걸 발견 — KSPO 제목의 "［얼리버드 50%］" 프로모션 문구 때문에 퍼지 매칭 점수(55.6)가
  기준(70) 미달이었던 것. `normalize_title()`에 `%` 포함 괄호만 제거하는 패턴을 추가해
  83.3으로 끌어올림(검증: `fuzz.ratio` 직접 계산).
  재수집(`pipeline/collection`) 실행 중 **데이터 손상 사고 발생**: `collect_kopis.py`·
  `collect_kopis_boxoffice.py`가 KOPIS 일시 장애로 생긴 "적은 결과"를 기존 좋은 데이터에
  그대로 덮어써서 `performance_detail.json` 812→565건, `boxoffice.json` 600→0건 손상.
  즉시 사용자에게 투명하게 보고하고 중단 → 두 스크립트에 안전장치 추가(merge/저장 중단) →
  KOPIS 안정화 후 재실행해 완전 복구(812건, 600건). `tasks/lessons.md`에 일반화된 교훈
  기록, CLAUDE.md "data/raw 손상 금지" 규칙에 수집 스크립트 자체도 지켜야 한다는 내용 추가.
- 막힌 점·확인할 것: 없음 — 복구 완료, 안전장치 추가 완료.
- 다음에 할 일: 매칭 수정 + 복구된 최신 데이터로 `pipeline/preprocessing` 전체 재실행
  (match_performances → normalize_and_clean → vectorize → evaluate) → "백 번째 리뷰" 등이
  실제로 매칭·추천에 반영되는지, 오프라인 평가 수치(Precision@5)가 나아지는지 확인.

## 2026-11-12 (계속 2)
- 한 일: 사용자가 "결국 KSPO가 미래 날짜를 줘야 하는 거 아니냐"고 질문 → KSPO 데이터만으론
  부족하다고 설명(KSPO는 날짜만 알고 장르는 KOPIS 등록이 있어야 안다는 구조적 한계).
  이어서 사용자가 방향 전환 제안: (c) 투명 공개 + 추천 모델을 "주기적 공연은 예측, 나머지는
  날짜 무관 콘텐츠 기준 추천"으로 바꾸자 + "나중에 KSPO가 쓰게 되면 원래 방식으로 되돌릴
  장치"도 요청.
  구현: 반복 시리즈 조사(3회 이상 반복 6개, 전부 페스티벌/콘서트 계열 — 뮤지컬·클래식·
  어린이는 0개임을 먼저 확인) → `recommender/series.py`(규칙 기반 다음 회차 예측) 작성 →
  `scoring.py`에 `CONTENT_FIRST_MODE` 스위치 + `STATUS_*` 상수 추가 → `recommend.py` 전면
  수정(`_eligible_mask`에 `allow_historical` 파라미터, 예측 행 주입, 모든 결과에 `status`
  라벨 부착; `condition_recommend`·`coldstart_recommend`는 스위치 무관하게 날짜 기반 유지).
  `evaluate.py`도 새 기준에 맞게 갱신 → 재실행해 **Precision@5 0.200 → 0.800** 확인,
  상태 라벨·반복 예측 행이 의도대로 동작하는지 직접 샘플로 검증.
- 막힌 점·확인할 것: 없음 — 검증 완료.
- 다음에 할 일: 5단계 `backend/`(FastAPI) 착수. (남은 미해결: 매칭된 공연의 period가
  KSPO/KOPIS 중 어느 쪽을 쓸지 — `tasks/todo.md` "후속 이슈" 참고)

## 2026-11-12 (계속 3)
- 한 일: 사용자가 "장르를 다르게 선택해도 똑같은 공연이 나오는 오류는 없었냐"고 확인
  요청 → 6개 장르 전부를 직접 호출해 대조 → **버그 발견**: "스포츠/기타" 선택 시
  "콘서트"와 완전히 동일한 5건 반환. 원인: `vectorize.NO_GENRE_SIGNAL`(공연 벡터 쪽에서
  스포츠/기타 신호를 0으로 죽임)과 `build_profile_vector`(사용자 프로필 쪽)가 서로
  다른 기준을 쓰고 있었음 — 프로필은 여전히 그 장르에 1을 넣어서 모든 공연과의 유사도가
  균일하게 0이 되고, 순위가 인기도만으로 매겨져 콘서트 랭킹과 우연히 같아졌던 것.
  `build_profile_vector`가 `NO_GENRE_SIGNAL`을 참조하도록 수정 → 재테스트: "스포츠/기타"는
  이제 콜드스타트로 정상 대체(로그로 확인), 나머지 5개 장르는 서로 고유한 리스트 반환.
  `evaluate.py` 재실행 — 전체 Precision@5는 0.800 그대로(스포츠/기타는 버그 전후 모두
  0.0이지만, 이제는 투명한 결과). `lessons.md`에 일반화된 교훈("신호를 죽인 특성은
  프로필/쿼리 쪽에서도 똑같이 죽여야 한다") 기록.
- 막힌 점·확인할 것: 없음.
- 다음에 할 일: 5단계 `backend/`(FastAPI) 착수.

## 2026-11-12 (계속 4)
- 한 일: 사용자가 "아까 말했던 미해결 후속 이슈가 이거 맞냐"고 확인 → 맞다고 설명(KSPO/KOPIS
  기간 불일치, 조건추천·콜드스타트엔 여전히 영향 있음) → 사용자가 "1번·2번 둘 다 테스트해보고
  나은 쪽으로 고쳐달라"고 요청.
  매칭 646건 전체로 KSPO vs KOPIS 기간을 직접 비교하는 스크립트 실행 → 날짜 다른 23건
  (3.6%) 전부 KOPIS 종료일이 KSPO보다 짧은 적 없음을 확인 → "KOPIS 우선"과 "둘 중 늦은
  날짜"가 실질적으로 동일한 결과라서 더 단순한 "KOPIS 우선"으로 결정.
  `match_performances.py`에 `kopis_prfpdfrom/prfpdto` 추가, `normalize_and_clean.py`에
  `resolve_period()` 추가 → 파이프라인 재실행 → "백 번째 리뷰" status가 "확정 예정"으로
  정상화 확인 → `evaluate.py` 재실행 — **Precision@5 0.800 → 0.855**(스포츠/기타
  0.0→0.333). CLAUDE.md "미해결 블로커"에서 "해결됨"으로 이동.
- 막힌 점·확인할 것: 없음 — 추천 모델(4단계) 전부 완료.
- 다음에 할 일: 5단계 `backend/`(FastAPI) 착수.

## 2026-11-12 (계속 5)
- 한 일: 5단계 백엔드 설계를 `tasks/todo.md`에 먼저 기록(저장소 구성, API 8개, 인증 방식,
  파일 구성) → `fastapi`·`sqlalchemy`·`uvicorn` 설치 시도 → 시스템 pip가
  externally-managed-environment로 막힘 → 사용자가 "안전장치를 끄는 행동이 뭐냐",
  "더 안전한 방법 없나", "배포 목표인데 위험하지 않냐"고 질문 → 배포는 Render가 완전히
  새 환경을 만드니 로컬 문제와 무관하다고 설명 + `get-pip.py`로 `.venv`(기존에 있던,
  pip 없는 빈 가상환경)에 pip만 부트스트랩하는 더 안전한 방법 제안 → 승인받아 진행,
  시스템 파이썬은 전혀 안 건드리고 `.venv`에만 fastapi·sqlalchemy·uvicorn·pandas·numpy·
  scikit-learn 설치 성공.
  `backend/{database.py, models.py, schemas.py, performances_store.py, main.py,
  requirements.txt, README.md}` 구현(설계대로 — 읽기 전용은 메모리 로드, 쓰기는 SQLite,
  세션 기반 식별). import 순서 버그(recommend를 performances_store보다 먼저 import)
  발견·수정. 실제 서버(uvicorn)를 띄워 curl로 테스트하려 했으나 **이 로컬 샌드박스에서
  포트를 리스닝하는 백그라운드 프로세스를 두면 세션이 강제 종료되는 환경 문제**를
  반복 확인(배포 환경과는 무관) → `fastapi.testclient.TestClient`로 전환해 8개
  엔드포인트 + 엣지 케이스(존재하지 않는 id, 찜 중복, 신호 없는 장르) 전부 통과 확인.
- 막힌 점·확인할 것: 없음 — 5단계 완료.
- 다음에 할 일: 6단계 `frontend/`(Next.js) 착수.

## 2026-11-12 (계속 6)
- 한 일: 사용자가 "찜 페이지(GET /favorites)는 빼도 될 것 같아, 기존 것만 먼저" 요청 →
  문서 7개 API 밖이었던 `GET /favorites` 라우트 제거(`Favorite` 테이블·`POST /favorites`는
  유지) → `TestClient`로 나머지 7개 재검증, `GET /favorites`가 405로 확실히 빠졌는지 확인.
  `backend/README.md`·`tasks/todo.md`에 "미룬 것"으로 명시.
- 막힌 점·확인할 것: 없음.
- 다음에 할 일: 6단계 `frontend/`(Next.js) 착수 — 작업 중단 상태, 사용자가 이어서 요청하면 시작.

## 2026-11-12 (계속 7)
- 한 일: 사용자가 "지금 모델이 실시간 예매 가능한 공연도 추천하냐"고 질문 → 직접 테스트해서
  `taste_recommend`는 상태 섞여 나오고(뮤지컬 테스트 시 5건 전부 "과거 유사 공연"), 날짜
  필터(`condition_recommend`류)만 실시간이라고 설명 → 사용자가 "프론트에서 예매 가능
  여부를 명확히 안내하자, 6단계 진행해달라"고 요청.
  선행 수정: `performances.csv`에 예매처 링크(`ticket_links`)가 아예 없던 걸 발견해
  추가, 백엔드 `to_records()`가 모든 공연 응답에 `status`를 공통으로 붙이도록 보강.
  Next.js(App Router, TS, Tailwind v4) 앱 생성 → 화면 4종(온보딩/홈/상세/마이페이지)
  구현, `status`별 배지·예매 버튼 표시 분기. 빌드·린트 통과(Suspense, lazy useState
  initializer로 수정한 이슈 3건 포함).
  `/run` 스킬로 실제 구동 확인 시도 → `lsof` 기반 안전한 포트 정리 + 긴 폴링으로 백엔드·
  프론트 둘 다 정상 기동 확인(**이전에 "포트 열면 세션 죽는다"고 결론 낸 게 사실은 WSL
  콜드 스타트가 느려서 생긴 오판이었음을 발견 — lessons.md에 기록**). 스크린샷은
  Playwright+Chromium의 시스템 라이브러리 부족(`libnspr4.so`, sudo 필요)으로 못 함 —
  코드 리뷰로 대체, 사용자에게 투명하게 고지.
- 막힌 점·확인할 것: 시각적 스크린샷 확인은 sudo 권한 있는 환경에서 재시도 필요
  (`frontend/README.md` 참고).
- 다음에 할 일: 4.7장(사용성 테스트)·4.8장(배포, Vercel/Render) — 아직 로컬 구현만
  끝난 상태.

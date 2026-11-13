# backend/

FastAPI 서버. 임베딩 계산이나 외부 API 호출은 여기 두지 않는다 — 그건
`pipeline/`·`recommender/`의 책임이다(CLAUDE.md 아키텍처 규칙).

상태: 완료 (5단계). API 목록·DB 스키마 설계 근거는 워크플로우 문서 4.5장, 실제 설계·
구현 기록은 `tasks/todo.md` "5단계: 백엔드", `tasks/verification.md` 참고.

## 저장소 구성

- **읽기 전용(performances)**: DB 테이블로 두지 않고, 서버 시작 시
  `data/processed/performances.csv` + `performance_vectors.npz`를 메모리로 읽어서 쓴다
  (`performances_store.py`, `recommender/`의 `recommend.load_data()` 재사용). 워크플로우
  문서는 DB 테이블로 명시했지만, 매일 배치가 통째로 다시 만드는 데이터를 DB에 또
  복제하는 동기화 비용을 피하려는 8주 MVP 단계의 단순화다.
- **쓰기가 필요한 것(rec_logs)**: SQLite(`app.db`, git에 미포함) + SQLAlchemy
  (`models.py`, `database.py`)로 실제 저장. 로그인·찜하기·온보딩 장르 취향(User/
  Favorite/UserPref)은 2026-11-12에 사용자 요청으로 전부 삭제했다(tasks/todo.md
  "추가 수정 작업" 참고) — 지금 DB에 남은 테이블은 추천 노출 로그(`RecLog`)뿐이다.
- **인증 없음**: 로그인 시스템을 만들었다가 사용 과정에서 다시 뺐다. 클라이언트가
  만든 익명 `session_id`로 추천 로그만 구분한다.
- **CORS**: `CORSMiddleware`로 전부 허용(`allow_origins=["*"]`) — 프론트(다른 포트)가
  브라우저에서 바로 호출해야 하기 때문. `TestClient`로는 이 문제가 안 드러나서(CORS를
  검사 안 함), 실제 브라우저로 연동 테스트하다가 뒤늦게 발견했다(`tasks/verification.md`
  [2026-11-12] 참고). **배포 시에는 `"*"` 대신 실제 프론트 도메인으로 좁혀야 한다.**

## API

| 메서드/경로 | 설명 |
| --- | --- |
| `GET /performances?date=&genre=` | 목록 조회(필터만, 추천 아님) |
| `GET /performances/{id}` | 상세 |
| `GET /recommend/me?session_id=` | 장르 구분 없이 지금 예매 가능한 공연 상위 3개(`recommend.bookable_top()`) |
| `GET /recommend/similar/{id}` | 비슷한 공연 |
| `GET /parking/forecast?forecast_date=` | **501** — 원본 데이터 수집이 막혀 있음(CLAUDE.md 참고) |

`POST /recommend/onboarding`·`POST`/`GET /favorites`·`POST /auth/signup`·
`POST /auth/login`은 전부 2026-11-12에 삭제했다 — 장르별 추천이 후보가 적은 장르에서
엉뚱한 장르로 채워지는 버그가 있어 장르 선택 자체를 없앴고(`tasks/todo.md` "추가
수정 작업" 참고), 그러면서 찜하기·로그인도 쓸 일이 없어져서 함께 뺐다.

추천 계열 응답에는 `status`(확정 예정/과거 유사 공연 — 참고용)가 항상 붙는다
(`recommender/scoring.CONTENT_FIRST_MODE` 참고, `/recommend/me`는 항상 과거를
제외하니 사실상 "확정 예정"만 나온다).

## 실행

```bash
cd backend
../.venv/bin/pip install -r requirements.txt   # 또는 .venv 없이 python3 -m venv .venv로 새로 생성
../.venv/bin/python3 -m uvicorn main:app --reload
# http://127.0.0.1:8000/docs 에서 Swagger로 확인
```

## 테스트

~~로컬 샌드박스에서 포트를 열면 세션이 강제 종료된다~~ — 처음엔 그렇게 보였는데, 실제
원인은 **WSL에서 `/mnt/c/...` 경로(윈도우 드라이브)라 pandas·scikit-learn 같은 무거운
import의 콜드 스타트가 느려서**(디스크 I/O 대기) 폴링 타임아웃이 너무 짧았던 것이었다
— 충분히 기다리면(`timeout 40 bash -c 'until curl -sf ...'`) 정상적으로 뜬다
(`tasks/verification.md` [2026-11-12] 참고, 정정됨).

API 단위 테스트는 `fastapi.testclient.TestClient`(실제 소켓 없이 ASGI 앱을 직접 호출)로
현재 엔드포인트와 주요 엣지 케이스(존재하지 않는 id)를 전부 통과시켰다. 실제 배포
환경(Render 등)에서는 포트 충돌 문제가 없다 — 로컬 개발 중 포트를 직접 열어 테스트할
때는 `TestClient`를 우선 쓰는 걸 권장한다.

**교훈(2026-11-12)**: `nohup ... &`로 "재시작"했다고 생각했는데 실제로는 세션 훨씬
앞에서 띄워둔 오래된 프로세스가 포트를 계속 쥐고 있어서 새 프로세스가 조용히 안 뜬
적이 있었다 — `app.db`를 그사이 여러 번 지웠다 다시 만들면서 그 오래된 프로세스의
파일 핸들이 꼬여 `sqlite3.OperationalError: attempt to write a readonly database`로
이어졌다(브라우저에는 CORS 에러로 보였음). 재시작 후에는 항상 `lsof -ti:PORT`로
**실제로 그 포트를 쥔 PID**를 확인할 것 — `nohup`을 실행했다는 사실 자체가 재시작
성공을 보장하지 않는다.

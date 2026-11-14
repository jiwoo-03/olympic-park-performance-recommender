# To-do

## 4단계: 추천 모델 (`recommender/`)

완료 기준(워크플로우 문서 4.4장): 사용자 취향·조건을 넣으면 예정 공연 상위 5개를 반환하는
함수 + 오프라인 평가표. 설계 상세는 6장 참고.

### 0. 데이터 보강 (착수 전 선행 작업) — 전부 완료

- [x] `pipeline/preprocessing/match_performances.py`·`normalize_and_clean.py`에 KOPIS 상세의
      `sty`(줄거리) 컬럼을 추가해 `performances.csv`에 포함시키기 — 현재 장르·출연진은 있지만
      줄거리가 빠져 있어 6장이 요구하는 "출연진+줄거리 텍스트 임베딩"을 바로 만들 수 없음.
      (매칭된 행에만 존재, 미분류 행은 그대로 빈 값) **완료 — 파이프라인 재실행·검증 끝.**
      단, KOPIS 원본 812건 중 `sty`가 실제로 채워진 건 **12건(1.5%)뿐** — 버그가 아니라
      KOPIS 데이터 자체의 한계. 1번 작업에서 "출연진+줄거리 임베딩"을 설계할 때 줄거리는
      거의 없다고 가정해야 함(상세는 `tasks/verification.md` 참고).
- [x] 공연장명 정규화 컬럼(`venue_normalized`) 추가. **확인 결과**: `venue`(kspo_venue, 전체
      1,961행에 존재)는 표기가 30종 넘게 흩어져 있고(예: "올림픽홀"/"올림픽공원 올림픽홀"/
      "올림픽공원 內 올림픽홀"), `venue_kopis`(kopis_fcltynm)는 매칭된 행에만 있지만 8종으로
      이미 깨끗함. 미분류 행도 장소 기준으로 묶으려면 `venue`를 키워드 매칭으로 정규화해야
      함 — 표준 5개가 아니라 실제로 관측되는 8개 장소(올림픽홀, KSPO DOME, 핸드볼경기장,
      우리금융아트홀, 88잔디마당, 수변무대, K-아트홀, 뮤즈라이브)로 정규화. **완료** —
      `normalize_venue()` 구현·재실행·검증 끝. 1차 결과는 "기타"가 356건(18%)으로 과했는데
      "체조경기장"(KSPO DOME 별칭)·"우리금용아트홀"(오타) 키워드가 빠져 있었던 것 — 규칙
      보강 후 150건(7.6%)으로 줄었고, 남은 150건은 올림픽공원 내 KOPIS 미등록 장소(벨로드롬·
      광장·축구장 등)라 "기타"가 맞는 결과.
- [x] **미분류 장르(약 1,243건, 63%) 처리 방침 결정**: 장르 기반 추천(취향·조건 추천)
      후보에서는 제외한다. 대신 `venue_normalized`가 같은 공연을 "이 장소의 다른 공연"
      섹션으로 추천 결과에 부가 노출한다(메인 추천 5개에는 섞지 않음 — 성격이 다른 공연이
      같은 장소라는 이유만으로 끼어들 수 있어서). **완료**: `recommender/venue_fallback.py`
      (`same_venue_fallback()`) 구현·실제 데이터로 검증 끝(과거 공연·자기 자신 제외 확인).
- [x] **인기도 신호 — (a) 박스오피스 API 수집으로 결정**. KOPIS 공연 상세에는 예매상황판
      필드가 없고(`visit`은 내한공연 여부일 뿐), 대신 `/openApi/restful/boxoffice`가 전국
      예매 랭킹 상위 50건을 제공함을 테스트 호출로 확인 — 응답의 `mt20id`가 상세의 `mt20id`와
      동일해 추가 매칭 없이 조인 가능. 기간은 최대 31일이라 월 단위로 순회 호출해야 함.
      테스트(2025년 1월): 전국 상위 50건 중 17건이 올림픽공원 공연. **구현 완료**:
      `pipeline/collection/collect_kopis_boxoffice.py`(최근 12개월, `run_all.py`에 등록) —
      실행 완료, `data/raw/kopis/boxoffice.json` 600건(distinct 424건) 생성, 올림픽공원
      공연과 겹치는 건 84건(매칭 공연의 약 13%) 확인됨(`pipeline/collection/REPORT.md` 참고).
      **완료**: `normalize_and_clean.py`에 `build_popularity_map()` 추가, `performances.csv`에
      `popularity_score`(0~1, `(51-최저랭크)/50`, 랭킹 없으면 0.0) 컬럼 생성·검증 끝 — `matched`
      651건 중 77건(11.8%)이 신호를 가짐(상세는 `tasks/verification.md` 참고).

### 1. 공연 벡터 — 전부 완료 (`recommender/vectorize.py`)

- [x] 장르 원-핫 인코딩 (콘서트·뮤지컬·클래식·페스티벌·어린이·스포츠/기타·미분류). **사후
      수정**: "스포츠/기타"가 서커스/마술·연극·대중무용·전통무용을 뭉친 잡동사니 버킷이라,
      장르만 같다는 이유로 완전히 무관한 두 공연(마술 vs 연극)이 유사도 0.5를 받는 가짜
      군집이 생겼었음(사용자 지적으로 발견). `NO_GENRE_SIGNAL`로 이 장르만 원-핫 신호를
      0으로 만들어 수정 — 상세는 `tasks/verification.md`·`lessons.md` [2026-11-12] 참고.
- [x] 출연진(`cast`) + 제목 + 줄거리(`synopsis`, 대부분 비어있음) 텍스트 임베딩 —
      scikit-learn TF-IDF(`token_pattern=r"[^\s,]+"`, min_df=2). **베이스라인 단순화**:
      FAISS·KoNLPy는 안 씀(공연 ~2,000건뿐이라 전체 코사인 유사도로 충분, 줄거리가
      1.5%뿐이라 형태소 분석 효과가 작음) — 공연 수가 늘거나 문장 임베딩으로 바꿀 때 재검토.
- [x] 두 벡터를 합쳐 `data/processed/performance_vectors.npz`로 저장(performances.csv와
      같은 행 순서). 검증: 같은 가수 공연 쌍 유사도 0.766 vs 무작위 다른 콘서트 0.500 —
      텍스트 성분이 실제로 유의미하게 작동함 확인(`tasks/verification.md` 참고).

### 2. 추천 로직 (MVP 3종) — 전부 완료 (`recommender/scoring.py`, `recommend.py`)

- [x] 취향 추천: 온보딩 선택(장르·아티스트)·찜 목록 → 사용자 프로필 벡터, 공연 벡터와
      코사인 유사도. `taste_recommend()`. 아티스트는 찜 목록(공연 인덱스)의 벡터 평균으로
      반영 — "아티스트 자체"를 별도 입력으로 받는 UI는 아직 없음(`backend/` 단계에서 결정).
- [x] 조건 추천: 날짜·동행 유형(가족→관람연령 12세 이하로 제한)·예산으로 필터 후 취향
      점수로 정렬. `condition_recommend()`.
- [x] 비슷한 공연: 공연 1건 기준 장르+출연진+줄거리 임베딩 유사도 상위 5. `similar_performances()`.
- [x] 최종 점수 = 취향 유사도×0.6 + 인기도×0.2 + 날짜 근접도×0.2(`scoring.final_score`),
      종료 공연 제외(`scoring.is_ended`), 동일 장르 몰림 방지 MMR 재정렬(`scoring.mmr_rerank`,
      취향 추천에만 적용 — 조건/비슷한 공연은 이미 필터링된 좁은 후보라 다양성보다 정확도가
      우선이라고 판단).
- [x] 콜드스타트(온보딩 없음): "이번 주말 인기 공연" 기본값. `coldstart_recommend()` — 이번
      주말에 겹치는 공연이 없으면 전체 예정 공연 중 인기순으로 대체.
- [x] **사후 보강(사용자 지적)**: `top_k`에 상한이 없어 데이터가 쌓일수록(후보 풀이 커질수록)
      호출하는 쪽이 큰 값을 넘기면 결과가 무한정 커질 위험 → `scoring.MAX_TOP_K`(20)로 4개
      함수 전부 clamp. 또한 `taste_recommend`가 MMR로 뽑은 뒤 선택 순서 그대로 반환하면
      관련성 낮은 게 먼저 나올 수 있어서, 뽑은 뒤 점수 내림차순으로 다시 정렬하도록 수정
      (상세는 `tasks/verification.md` 참고).

**검증**: 4개 함수를 실제 데이터로 1회씩 호출해 결과를 상식과 대조. 처음엔 버그로 보였던
2가지(같은 가수 공연이 비슷한 공연에 안 뜸, 조건 추천이 1건만 나옴)를 디버깅했는데 둘 다
정상 동작(각각 "이미 끝난 공연 제외", "예산 필터가 실제로 걸러낸 것")으로 확인됨
(`tasks/verification.md` 참고).

### 3. 오프라인 평가 — 완료 (`recommender/evaluate.py`, `REPORT.md`) — ⚠️ 중대한 발견

- [x] 가상 사용자 프로필 30개 작성 (장르 6종 × 5명, `build_profiles()`)
- [x] Precision@5(선택 장르 vs 추천 장르 일치율) 계산 — **평균 0.200**
- [x] Coverage(6/13=0.462), Diversity(목록 내 장르 수, 평균 1.83) 계산
- [x] 평가 결과를 `recommender/REPORT.md` + `evaluation_results.csv`로 정리

**발견한 문제(코드 버그 아님 — 데이터 커버리지 문제) → 설계 전환으로 해결됨**: 장르별
Precision@5가 콘서트만 1.0이고 나머지는 거의 0이었던 원인은 매칭된 공연 651건 중
안 끝난 공연이 13건뿐(워크플로우 문서 7장 리스크 1번 실측 확인)이었던 것. 재수집·매칭
개선(아래 "후속 이슈" 직전 시도)으로는 해결 안 돼서, **추천 방식을 "콘텐츠 우선 모드"로
전환**하기로 결정(사용자 논의) — 아래 "4. 콘텐츠 우선 모드 전환" 참고. 결과: Precision@5
**0.200 → 0.800**.

### 4. 콘텐츠 우선 모드 전환 — 완료 (`series.py`, `scoring.CONTENT_FIRST_MODE`)

사용자가 제안한 방향: (c) 데모·발표에서 데이터 한계를 투명하게 설명 + 추천 모델 자체를
"미래 날짜 확정"에 의존하지 않는 쪽으로 틀기.

- [x] **반복 공연 시리즈 다음 회차 예측**(`series.py`, 규칙 기반 — ML 예측 모델 아님):
      제목(연도 제거)이 3회 이상 반복된 시리즈(6개: 그랜드민트페스티벌·서울파크뮤직
      페스티벌·뷰티풀민트라이프·성시경 관련 2종·조이올팍페스티벌)의 최근 회차를 1년
      뒤로 투영해 "다음 회차 예상" 후보를 만든다. 뮤지컬·클래식·어린이는 반복 시리즈가
      0개라 이 기능의 수혜 대상이 아님(조사로 확인).
- [x] **취향 추천·비슷한 공연은 날짜 무관 콘텐츠 기준 + 상태 라벨**: `CONTENT_FIRST_MODE=True`
      일 때 `taste_recommend`·`similar_performances`는 종료 여부와 상관없이 추천하고,
      결과마다 `status`(확정 예정/매년 반복 예상/과거 유사 공연 — 참고용)를 붙인다.
      `condition_recommend`·`coldstart_recommend`는 스위치와 무관하게 항상 날짜 기반 유지
      (특정 날짜를 묻는 기능에 과거 공연을 보여주면 거짓 정보가 되므로).
- [x] **되돌리기 스위치**: `scoring.CONTENT_FIRST_MODE`(현재 `True`) — 한국체육산업개발이
      실제 서비스로 채택해 미래 공연 일정이 충분해지면 `False`로 바꾸는 것만으로 원래
      설계(확정된 예정 공연만 추천)로 돌아간다. 코드 변경 불필요.

**검증**(`evaluate.py` 재실행): Precision@5 0.200→**0.800**(뮤지컬 1.0, 어린이 1.0,
페스티벌 1.0, 클래식 0.8, 콘서트 1.0). 스포츠/기타만 0.0인데 이건 `NO_GENRE_SIGNAL`
(스포츠/기타는 장르 신호를 안 줌) 때문에 생기는 당연한 결과. 반복 시리즈 예측 5건은
이번 평가에서 top5에 하나도 안 들었음(인기도 0, 날짜 근접도 보통 범위 밖 — 기능은
정상이나 지금 당장 체감 효과는 적음). 상세는 `recommender/REPORT.md` "설계 전환",
`tasks/verification.md` [2026-11-12] 참고.

### 선행 조건 / 블로커 (CLAUDE.md "알려진 이슈" 참고)

- 주차 혼잡 예보는 `collect_parking_weather.py` 데이터 없이는 착수 불가 — 추천 모델과
  분리해서 별도로 블로킹 해제 추적.

### 후속 이슈 (2026-11-12 발견) — 완료

- [x] 매칭된 공연의 `period`가 항상 KSPO 쪽 기간을 쓰는데, KOPIS 쪽 기간이 더 정확하거나
      더 긴 경우(공연 연장 등)가 있음을 확인함("백 번째 리뷰": KSPO는 8/30 종료, KOPIS는
      12/27 종료). **옵션 1(KOPIS 우선)과 옵션 2(둘 중 늦은 날짜) 실제로 비교**: 매칭
      646건 중 날짜 다른 23건 전부 KOPIS 종료일이 KSPO보다 짧은 적이 없어 두 옵션이
      실질적으로 동일 — 더 단순한 **옵션 1(매칭된 공연은 KOPIS 기간을 쓴다)로 결정·구현**
      (`match_performances.py`에 `kopis_prfpdfrom/prfpdto` 추가,
      `normalize_and_clean.resolve_period()`). 재평가: Precision@5 0.800→**0.855**,
      스포츠/기타 0.0→0.333. 상세는 `tasks/verification.md`·`recommender/REPORT.md` 참고.

### 5. 버그 수정 (2026-11-12, 사용자 지적) — 완료

- [x] 장르 선택 간 결과 중복 버그: "스포츠/기타" 선택 시 "콘서트"와 완전히 동일한 5건이
      나오던 문제. 원인: `NO_GENRE_SIGNAL`(공연 벡터 쪽)과 `build_profile_vector`(사용자
      프로필 쪽)가 서로 다른 기준을 쓰고 있었음. `build_profile_vector`가
      `vectorize.NO_GENRE_SIGNAL`을 참조하도록 수정 — 이제 "스포츠/기타"만 선택하면
      콜드스타트로 정상 대체됨. 나머지 5개 장르는 서로 고유한 리스트를 반환함을 재검증.
      상세는 `tasks/verification.md`·`lessons.md`·`recommender/REPORT.md` 참고.

## 5단계: 백엔드 (`backend/`) — 완료

완료 기준(워크플로우 문서 4.5장): Swagger 문서와 Postman 테스트 통과.

### 저장소 구성

- **읽기 전용(performances/venues)**: DB 테이블로 중복 저장하지 않고 서버 시작 시
  `data/processed/performances.csv` + `performance_vectors.npz`를 메모리로 로드해서 쓴다.
  CLAUDE.md의 "배치가 만든 결과를 읽기만 한다" 원칙과 FAISS/KoNLPy 생략 때와 같은 결의
  단순화 — 워크플로우 문서는 DB 테이블로 명시했지만, 매일 배치가 통째로 다시 만드는
  데이터를 DB에 또 복제하는 건 8주 MVP에서 불필요한 동기화 비용이라고 판단함.
- **쓰기가 필요한 것(user_prefs, favorites, rec_logs)**: SQLite + SQLAlchemy로 실제 저장
  (개발 단계는 SQLite, 기술 스택 표와 일치).
- **인증**: 로그인 시스템은 구현하지 않음(문서에 명시 안 돼 있고 8주 MVP 범위 밖) — 대신
  클라이언트가 생성한 `session_id`로 사용자를 식별한다. **다만 나중에 로그인 시스템을
  추가할 가능성을 염두에 두고 있다** — `UserPref`가 `session_id`를 기본 식별자로 쓰고
  있어서, 실제 로그인을 붙일 때는 `session_id`를 로그인된 `user_id`로 바꾸거나 둘을
  매핑하는 정도로 확장하면 될 것(현재는 설계만 기록, 작업은 아직 없음).

### API (문서의 7개 그대로 — 추가분은 나중으로 미룸)

- `GET /performances?date=&genre=` — 목록
- `GET /performances/{id}` — 상세 (`id`는 performances.csv 로드 시 행 순서로 부여, 배치가
  다시 돌면 바뀔 수 있음 — 8주 MVP 단계의 알려진 한계로 남겨둠)
- `POST /recommend/onboarding` — `{session_id, favorite_genres, favorite_performance_ids}`
  저장 + 취향 추천 결과 반환 + `rec_logs`에 노출 기록
- `GET /recommend/me?session_id=` — 저장된 취향으로 취향 추천
- `GET /recommend/similar/{id}` — 비슷한 공연
- `GET /parking/forecast?date=` — 주차 데이터 수집이 막혀 있어서(504, CLAUDE.md "미해결
  블로커") 501 Not Implemented로 명확히 응답
- `POST /favorites` — 찜 추가

**미룬 것**: `GET /favorites?session_id=`(찜 목록 조회, "마이페이지" 화면용)는 문서 7개
API에 없던 추가분이라 처음엔 넣었다가, 사용자 요청으로 "기존 것만 먼저" 범위로 좁히면서
뺐다. `Favorite` 테이블·`POST /favorites`는 이미 있으니 나중에 조회 엔드포인트만
추가하면 된다.

### 파일 구성(예정)

`backend/{requirements.txt, database.py, models.py, schemas.py, performances_store.py,
main.py, README.md}` — 다른 단계 폴더와 같은 구조(README.md에 실행법, requirements.txt).

### 완료 기록

- [x] `.venv`(이 프로젝트 전용 가상환경)에 pip를 직접 부트스트랩(`get-pip.py`)해서
      `fastapi`·`uvicorn`·`sqlalchemy`·`pandas`·`numpy`·`scikit-learn` 설치 — 시스템
      파이썬은 건드리지 않음(`--break-system-packages` 안 씀). 계기는 사용자 질문
      ("안전장치를 끄는 행동이 뭐냐", "더 안전한 방법 없나") → get-pip.py로 .venv 안에만
      pip를 심는 방식으로 결정.
- [x] 위 파일 구성대로 구현(`database.py`, `models.py`, `schemas.py`,
      `performances_store.py`, `main.py`, `requirements.txt`, `README.md`)
- [x] 엔드포인트 7개 + 엣지 케이스(존재하지 않는 id, 찜 중복, 신호 없는 장르 선택) 테스트.
      **로컬 샌드박스에서 실제 포트를 열어 curl로 테스트하면 백그라운드 리스닝 프로세스
      때문에 세션이 강제 종료되는 환경 문제가 있어서**, `fastapi.testclient.TestClient`
      (소켓 없이 ASGI 앱을 직접 호출)로 전환해 전부 통과시킴. 실제 배포 환경(Render 등)
      에는 이 문제가 없음.
- [x] `tasks/verification.md`에 테스트 결과 기록

## 6단계: 프론트엔드 (`frontend/`) — 다음에 이어서 시작

여기서 작업을 멈춤. 착수 시 워크플로우 문서 4.6장(화면 4종: 온보딩·홈·공연 상세·마이페이지)
참고해서 설계부터 이 자리에 기록할 것.

## 6단계: 프론트엔드 (`frontend/`) — 완료

완료 기준(워크플로우 문서 4.6장): 화면 4종(온보딩·홈·공연 상세·마이페이지)이 실제
API와 연동되어 동작.

### 0. 선행 수정 — 예매처 링크 데이터 누락

조사 중 발견: `performances.csv`에 **예매처 링크가 아예 없음**. `match_performances.py`는
KOPIS의 `relates`(예매처명+URL 목록)를 받아오지만, `normalize_and_clean.py`가 최종 CSV에
옮기지 않고 버리고 있었음. CLAUDE.md 제약("예매는 직접 처리하지 않고 외부 예매처 링크로
연결") 때문에 공연 상세 화면이 이 데이터 없이는 핵심 기능을 못 함.

- [x] `normalize_and_clean.py`에 `ticket_links`(JSON 문자열, KOPIS `relates` 그대로) 컬럼
      추가 → 파이프라인 재실행 → 매칭된 646건 전부 채워짐 확인(상세는
      `tasks/verification.md` 참고). 추가로 백엔드 `to_records()`가 추천 결과뿐 아니라
      `GET /performances`·`GET /performances/{id}`에도 `status`를 공통으로 붙이도록 보강
      (프론트가 어디서든 예매 가능 여부를 표시할 수 있어야 해서).

### 1. 사용자 요청: 예매 가능 여부를 UI로 명확히 안내

`status`(확정 예정/매년 반복 예상/과거 유사 공연 — 참고용)에 따라 카드 표시를 다르게 함:
- **확정 예정**: 일반 카드 + "예매하기" 버튼(ticket_links로 연결, 여러 개면 전부 노출) +
  "예매처에서 최종 확인" 안내(CLAUDE.md 제약)
- **매년 반복 예상**: "예상 일정" 배지 + "매년 비슷한 시기에 열리는 공연으로, 공식 일정은
  아직 미확정입니다" 안내, 예매 버튼 없음
- **과거 유사 공연**: 흐리게(비활성 느낌) 표시 + "종료된 공연 — 참고용" 배지, 예매 버튼
  없고 "비슷한 공연" 성격만 전달

### 2. 화면 4종 (워크플로우 문서 4.6장)

- **온보딩**: 장르 선택(6종 체크) → `POST /recommend/onboarding`. **동행 유형은 뺐다** —
  백엔드 `OnboardingRequest`/`taste_recommend`가 동행 유형을 안 받는다(그건
  `condition_recommend`용인데, 이 엔드포인트는 워크플로우 문서 7개 API에 아예 없어서
  REST로 노출 안 했었음). 지금 있는 `GET /performances?date=&genre=`로 "날짜·장르로 찾기"
  섹션만 홈 화면에 구현.
- **홈**: 내 추천(위 온보딩 결과) + 이번 주말 공연(콜드스타트) + 날짜 필터(`GET /performances?date=`)
- **공연 상세**: `GET /performances/{id}` + 비슷한 공연(`GET /recommend/similar/{id}`) +
  주차 예보 자리(지금은 501이라 "준비 중" 표시) + 상태별 안내(위 1번)
- **마이페이지**: 찜 목록 — **`GET /favorites` 조회 엔드포인트가 지금 없어서(이전에 사용자
  요청으로 범위 축소함) 로컬(브라우저 localStorage)에 찜한 id만 저장해 보여주는 걸로
  임시 구현**. 서버에 `POST /favorites`로는 올리되(로그 목적), 목록 표시는 로컬 기준.

### 3. 기술/구조

- Next.js(App Router) + Tailwind CSS, 모바일 우선. `session_id`는 첫 방문 시 브라우저에
  생성해 localStorage에 저장(백엔드 설계와 일치).
- `frontend/{app/, components/, lib/api.ts, lib/session.ts, README.md}` — API base URL은
  환경변수(`NEXT_PUBLIC_API_BASE`)로.

### 완료 기록

- [x] 0, 1번 수정(`ticket_links`, `status` 공통화)
- [x] Next.js 앱 생성(App Router, TypeScript, Tailwind v4) — `npx create-next-app`
- [x] 화면 4종 구현(`lib/api.ts`, `lib/session.ts`, `lib/favorites.ts`,
      `components/{StatusBadge,PerformanceCard}.tsx`, `app/{onboarding,page,
      performances/[id],mypage}`)
- [x] `npm run build`·`npm run lint` 통과(중간에 Next.js 16의 `set-state-in-effect` 규칙
      위반 3건을 lazy `useState` initializer로 수정, `useParams` prerender 에러를 `Suspense`
      로 수정)
- [x] 백엔드+프론트 둘 다 실제로 띄워서 curl로 연동 확인. **처음엔 "포트를 열면 세션이
      강제 종료된다"고 오판했는데, 실제로는 WSL `/mnt/c/...` 경로라 pandas 등 콜드 스타트가
      느려서(디스크 I/O) 폴링 타임아웃이 부족했던 것** — 충분히 기다리니 둘 다 정상 기동
      (`backend/README.md` 정정함).
- [x] **스크린샷 기반 시각 확인 — 완료**: 사용자가 sudo로 `playwright install-deps` 실행
      후 재시도해서 실제 Chromium 스크린샷으로 확인함. 이 과정에서 **curl/TestClient로는
      못 잡는 버그 2건을 발견·수정**:
      1. CORS 미설정 → `backend/main.py`에 `CORSMiddleware` 추가.
      2. Next.js 16 `allowedDevOrigins` 기본 차단(127.0.0.1 접근 시 dev 리소스 차단돼
         `useEffect`가 아예 안 돎) → `next.config.ts`에 `allowedDevOrigins` 추가.
      수정 후 홈 화면(내 추천/이번 주말 공연에 실데이터+배지)·확정 예정 공연(예매 버튼
      있음)·과거 공연(예매 버튼 없음) 전부 스크린샷으로 의도대로 렌더링됨을 확인.
      상세는 `tasks/verification.md`·`lessons.md` [2026-11-12] 참고.

## 7단계: 테스트·개선 (워크플로우 문서 4.7장) — 설계 (구현 전)

### 0. 배경 — 지금까지 뭐가 "테스트"였나

여태 백엔드 검증은 매번 **임시 TestClient 스크립트**를 그 자리에서 돌리고 지웠고
(결과만 `tasks/verification.md`에 기록, 재현 가능한 코드로는 안 남음), 프론트는
`npm run build`/`lint` + 수동 Playwright 스크린샷 1회성 확인뿐이었다. 4.7장의 완료
기준("치명 버그 0건, 개선 목록 반영")을 충족하려면 **재실행 가능한** 테스트 코드로
남겨야 한다. 문서 4.7장이 요구하는 4가지: 단위 테스트(pytest)·API 통합 테스트·
Lighthouse 성능 점검·사용성 테스트 5명.

### 1. 단위 테스트 (pytest) — `recommender/`

- 대상: 과거에 실제로 버그가 났던 지점을 회귀 테스트로 고정하는 게 최우선.
  - `vectorize.NO_GENRE_SIGNAL` ↔ `recommend.build_profile_vector`가 같은 기준을
    쓰는지(장르 중복 버그, 2026-11-12 수정분).
  - `normalize_and_clean.resolve_period()`가 매칭된 행은 KOPIS 기간을 쓰는지.
  - `scoring.CONTENT_FIRST_MODE` on/off 양쪽에서 `_status_for()`가 확정 예정/매년
    반복 예상/과거 유사 공연을 올바르게 구분하는지.
  - `series.py`의 반복 시리즈 다음 회차 예측 규칙(최소 1건 샘플 고정값으로).
- 파일: `recommender/tests/test_vectorize.py`, `test_scoring.py`, `test_series.py`,
  `test_recommend.py`.
- `.venv`에 `pytest` 추가 필요(dev 전용 — `requirements.txt`에 별도 `requirements-dev.txt`로
  분리할지, 그냥 같이 둘지는 사용자 결정 필요 없이 `requirements-dev.txt`로 분리 — 배포
  환경(Render)에 테스트 의존성까지 설치할 이유 없음).

### 2. API 통합 테스트 — `backend/`

- 대상: 7개 엔드포인트 전부 + 과거에 수동으로 확인했던 엣지케이스(존재하지 않는 id,
  찜 중복 호출, 신호 없는 장르 선택 시 응답) + `status`가 `GET /performances`·
  `GET /performances/{id}`·추천 3종 전부에 공통으로 붙는지.
- **한계를 명시**: `TestClient`는 CORS를 검사하지 않으므로 CORS류 버그는 여기서 못
  잡는다(이미 실측됨, `backend/README.md` 참고) — 이 한계는 Lighthouse 단계(실제
  Chromium 사용)에서 간접적으로나마 다시 한번 교차 확인한다.
- 파일: `backend/tests/test_main.py`. `requirements-dev.txt`에 `pytest`+이미 있는
  `httpx2`(TestClient용) 정리.

### 완료 기록 (2026-11-12, 1·2번 구현)

이 설계를 적은 뒤로 찜하기·로그인·온보딩·반복 시리즈 예측이 전부 삭제돼서, 위에 적힌
대상 중 "찜 중복"·"매년 반복 예상"류는 더 이상 해당 사항이 없다. 실제로 구현한 건
**지금 남아있는 기능 기준**으로 범위를 다시 잡았다:

- [x] `requirements-dev.txt` 신규(루트) — `pytest` 하나만. 배포용 `backend/requirements.txt`
      와 분리.
- [x] `recommender/tests/`: `test_scoring.py`(순수 함수 11건), `test_build_profile_vector.py`
      (NO_GENRE_SIGNAL 회귀 4건), `test_recommend.py`(`bookable_top`·`similar_performances`
      7건, 과거·미분류 제외 + CONTENT_FIRST_MODE로 "비슷한 공연"엔 과거 포함되는 것까지
      확인). 합성 DataFrame/벡터를 직접 만들어서 써서 실데이터(매일 배치로 바뀜)에
      의존 안 함.
- [x] `pipeline/preprocessing/tests/test_normalize_and_clean.py`(6건) — "미분류" 버그
      수정 때 실제로 겪은 회귀(매칭된 공연의 KOPIS 장르를 제목 키워드가 덮어쓰면 안 됨)를
      고정.
- [x] `backend/tests/test_main.py`(15건) — 남아있는 5개 엔드포인트 정상 동작 +
      삭제한 5개 엔드포인트(`/favorites`, `/auth/*`, `/recommend/onboarding`)가 전부
      404로 남아있는지 회귀 테스트.
- [x] 3개 디렉터리 전부 따로 실행해서 **43건 전부 통과** 확인
      (`cd recommender && ../.venv/bin/python3 -m pytest tests/` 등). **한 번에
      `pytest .`로 루트에서 전체를 돌리지 않는다** — `recommender/common.py`와
      `pipeline/preprocessing/common.py`처럼 이름이 같은 모듈이 서로 다른 디렉터리에
      있어서, 한 pytest 세션에서 둘 다 import하면 먼저 캐싱된 쪽이 다른 디렉터리의
      테스트에도 쓰여버리는 위험이 있다 — 각 디렉터리는 기존에도 독립 실행 전제였다
      (`pipeline/collection && python run_all.py` 식으로).

### 3. Lighthouse 성능 점검

- WSL이라 GUI 크롬이 없음 — 이미 설치돼 있는 Playwright 헤드리스 Chromium
  (`~/.cache/ms-playwright/chromium-1254/chrome-linux64/chrome`)을 `CHROME_PATH`로
  지정해서 `npx lighthouse`를 그 바이너리로 실행.
- 측정 대상은 **dev 서버가 아니라 프로덕션 빌드**(`next build && next start`) — dev
  모드는 HMR·압축이 꺼져 있어서 점수가 실제보다 낮게 나와 의미가 없다.
- 측정 페이지: 홈(`/`), 공연 상세(`/performances/0`).
- 결과는 `tasks/verification.md`에 4개 지표(Performance/Accessibility/Best
  Practices/SEO) 점수와 주요 경고를 기록.

### 완료 기록 (2026-11-12~13)

- [x] 프로덕션 빌드(`next build && next start -p 3000`) + Playwright 헤드리스
      Chromium(`CHROME_PATH`)로 홈·공연 상세 2페이지 측정.
- [x] **실제로 고친 문제 3건**(발견 즉시 수정, 재측정으로 확인):
      1. 상세 페이지 포스터 이미지에 `width`/`height`가 없어서 로딩 전/후 레이아웃이
         크게 밀림(CLS 0.467) → `aspect-[2/3]` + 명시적 width/height 추가로 CLS 0.
      2. 홈 화면 달력이 데이터 로딩 중엔 "불러오는 중..." 텍스트만 있다가 로딩 후
         전체 그리드로 바뀌면서 큰 레이아웃 밀림(CLS 0.328~0.357) → 로딩 상태에서도
         빈 달력 그리드·장르 범례·점 칸을 항상 같은 높이로 그려서(데이터만 비어있게)
         CLS 0.
      3. 장르 필터 `<select>`에 접근성 라벨이 없음, 달력 주말 색상(`text-rose-500`/
         `text-sky-500`)이 흰 배경 대비 WCAG AA(4.5:1) 미달(2.7~3.75) → `aria-label`
         추가 + `text-rose-600`/`text-sky-700`로 조정, Accessibility 89→100(홈).
- [x] **발견했지만 지금 안 고친 것(디자인 다듬기 단계로 넘김)**:
      - 상세 페이지의 `text-gray-400/500`류 보조 텍스트(공연 카드 날짜·장소, 장르
        태그, 주차 예보 안내 문구 등)가 여러 군데서 WCAG AA 대비 미달(2.19~4.36,
        4.5 필요) — 특정 컴포넌트 하나가 아니라 앱 전체의 "보조 텍스트" 색상
        토큰이라, 지금 Lighthouse 점검 범위를 넘어서는 디자인 결정으로 보고 보류.
      - "Does not use HTTPS"(Best Practices) — 로컬 HTTP 테스트라서 당연히 뜨는
        경고, 실제 배포(Vercel/Render)하면 자동 해결.
      - KOPIS 포스터 이미지가 `http://`(비보안)라 "Issues" 패널에 쿠키 경고가 뜸 —
        우리가 포스터를 직접 호스팅하지 않는 한 고칠 수 없음(CLAUDE.md "포스터
        이미지는 KOPIS가 제공하는 범위만 사용" 제약과도 맞물림).
- [x] **중간에 재발견한 버그**: 백엔드·프론트 둘 다 "재시작"했다고 생각했는데 실제로는
      이전 PID가 계속 포트를 쥐고 있던 적이 두 번 더 있었음(`app.db` 핸들 꼬임으로
      500 에러 재발 1번, `next start`가 포트 충돌로 조용히 실패해서 옛 빌드가 계속
      응답한 적 1번) — 매번 `ss -ltnp`/`lsof`로 실제 PID를 확인하고 나서야 잡혔다.
      이제는 서버를 띄울 때마다 습관적으로 확인하는 걸로 함(lessons.md 기존 항목
      "서버 로그 경고를 끝까지 읽어야 한다"의 연장선).
- [x] Lighthouse가 `npx`로 실행되면서 Chrome 프로필 디렉터리를 `C:\Users\...` 형태의
      **리터럴 파일명**으로 `frontend/` 안에 만들어버리는 부작용 발견(`next build`가
      이 파일을 읽으려다 실패) → `--user-data-dir`을 스크래치패드 경로로 명시하고,
      실행 위치도 `frontend/`가 아닌 스크래치패드로 옮겨서 해결. 생성됐던 잔재
      디렉터리는 삭제.
- [x] 최종 점수(프로덕션 빌드, 로컬 HTTP 기준):

  | 페이지 | Performance | Accessibility | Best Practices | SEO |
  | --- | --- | --- | --- | --- |
  | 홈(`/`) | 86 | 100 | 77 | 100 |
  | 상세(`/performances/0`) | 79 | 96 | 77 | 100 |

  Performance가 90대 밑인 건 WSL 환경 자체의 네트워크/디스크 I/O 지연(LCP 3~3.4초)
  영향이 커서, 실제 배포(Vercel CDN) 환경에서는 더 잘 나올 가능성이 높음 — 지금
  숫자를 "확정 수치"로 보지 말 것. CLS는 0으로 완전히 해결했고, 치명적인 성능
  문제는 없음.

### 4. 사용성 테스트 5명

- **내가 직접 실행할 수 없는 부분** — 실제 사람 5명이 필요하므로, 내 역할은 "실행
  가능한 설계"까지고 실제 진행은 사용자가 해야 한다.
- 진행 방식(제안): 참가자에게 휴대폰으로 배포 전이면 로컬 서버 URL(같은 와이파이망 +
  `--host 0.0.0.0`) 또는 배포 후면 실제 URL 접속 → 온보딩(장르 선택) → 추천 5개 화면 →
  "이 중 실제로 보러 가고 싶은 공연이 있나요? (있으면 몇 개)" 질문.
- 기록 템플릿: `tasks/usability_results.md` 신규 생성 — 참가자별 선택 장르, 추천 5개
  중 "가고 싶다" 선택 개수, 자유 의견(헷갈렸던 점 등) 표 형식.
- 메트릭(문서 4.7장 그대로): 5명 × 5개 추천 중 "가고 싶다" 선택 비율(인당 비율의 평균).

### 5. 완료 기준

- **치명 버그** = 화면이 전혀 안 뜸, 크래시, 잘못된/깨진 예매 링크, 데이터 손상 등
  핵심 기능 자체가 깨지는 것. 치명 버그 0건이 배포(8단계) 착수 조건.
  **일반 개선**(UI 문구, 레이아웃 등)은 별도 백로그로 분리해 배포를 막지 않는다.
- 사용성 테스트·Lighthouse에서 나온 개선 아이디어는 `tasks/usability_results.md`
  "개선 목록" 절에 모아두고, 배포 전 반영 여부를 사용자와 같이 판단.

### 확인 완료 (사용자 결정, 2026-11-12)

- **Lighthouse**: 목표 점수 없이 측정만 하고 기록. 심각하게 낮으면(예: 50점 미만) 그때
  개선 여부 판단.
- **사용성 테스트 5명**: 진행 일정·참가자 아직 미정 — 사용자가 날짜를 잡으면 알려주기로
  함(그때 `tasks/session-log.md`에 기록). 지금은 1~3번(pytest 단위·통합 테스트,
  Lighthouse)부터 구현 착수 가능.

## 추가 기능 요청 (2026-11-12, 사용자가 실제 화면을 써보고 요청) — 설계

실제 화면을 써본 뒤 나온 요청 3건. 전부 워크플로우 문서의 원래 7개 API·"로그인 없음"
범위를 넘어서는 **사용자의 의도적인 확장 결정**이라 그대로 진행한다(문서와 충돌하는
걸 내가 임의로 고르는 게 아니라 문서 소유자가 직접 바꾸는 것).

### 1. "내 추천"과 "이번 주말 공연" 통합

- 확인 결과(사용자 결정): 그냥 통합 리스트 하나로 보여주면 됨 — "주마다 갱신"은 별도
  캐싱이 필요한 요구가 아니라, 매 요청마다 최신 데이터로 다시 계산되는 것으로 충분.
- **백엔드 변경 없음**: `recommend.taste_recommend()`가 취향 신호가 없으면 이미
  `coldstart_recommend()`(이번 주말 인기 공연)로 자연히 대체된다(`recommend.py:146-148`).
  즉 지금의 "내 추천" 섹션 하나만 남겨도 온보딩 전/후 둘 다 적절한 결과가 나온다.
- 프론트(`app/page.tsx`): "이번 주말 공연" `Section`과 관련 상태(`weekend`,
  `weekendLoading`, `upcomingSaturday()`)를 전부 제거. "내 추천" 섹션만 남김.

### 2. 로그인 시스템 + 마이페이지(내 정보·활동 내역) + 홈(올림픽공원 소식 게시판)

확인 결과(사용자 결정): 로그인 = 이메일+비밀번호 간단 로그인(bcrypt 해시, OAuth 없음).
마이페이지의 "결제한 것들"은 실제 결제 연동이 아니라 **찜/활동 내역으로 대체**(현재
CLAUDE.md 규칙 "예매는 직접 처리 안 하고 외부 예매처로 연결"과 충돌하지 않게).

**백엔드**

- 신규 의존성 `bcrypt` 추가(`requirements.txt`) — 설치 승인 필요.
- `models.py`에 `User` 테이블 추가: `id`(PK, autoincrement) · `email`(unique, index) ·
  `password_hash` · `created_at`.
- `schemas.py`에 `SignupRequest`/`LoginRequest`(email, password) 추가.
- `main.py`에 `POST /auth/signup`, `POST /auth/login` 추가 — 성공 시
  `{"user_id":, "email":}` 반환. 비밀번호는 bcrypt로만 비교, 평문 저장 안 함.
- **세션 체계는 안 바꾸고 재사용**: 로그인하면 프론트가 기존 `session_id` 문자열을
  `"user:{user_id}"`라는 고정값으로 바꿔서 그대로 쓴다 — `UserPref`/`Favorite`/
  `RecLog` 테이블 스키마를 안 바꿔도 로그인 전/후가 이어진다.
- **익명 데이터 이전**: 가입/로그인 시, 그 브라우저가 로그인 전에 쓰던 익명
  `session_id`로 쌓인 `Favorite`·`UserPref` 행이 있으면 새 `user:{id}`로
  재배정(`UPDATE ... SET session_id=`) — 안 하면 가입 직전까지 찜한 공연이 사라진
  것처럼 보임.
- **`GET /favorites?session_id=` 복구**: 전에 "일단 기존 것만" 요청으로 뺐었는데
  (`tasks/todo.md` "5단계" 참고), 로그인으로 `session_id`가 기기와 무관하게 안정된
  지금은 다시 의미가 있음(마이페이지에서 어느 기기로 로그인해도 같은 찜 목록을 봐야
  하므로) — `Favorite` 테이블은 이미 있으니 조회 엔드포인트만 추가.

**프론트엔드**

- `lib/auth.ts` 신규: `signup()`·`login()`·`logout()`·`getCurrentUser()`(localStorage에
  `{user_id, email}`) · `isLoggedIn()`.
- `lib/session.ts` 수정: `getSessionId()`가 로그인 상태면 `"user:{user_id}"`를, 아니면
  기존 랜덤 UUID를 반환.
- `app/login/page.tsx` 신규: 이메일+비밀번호, 로그인/회원가입 토글, 성공 시 `/mypage`로
  이동.
- `app/mypage/page.tsx` 재작성: 로그인 안 돼 있으면 "로그인이 필요합니다" + 로그인
  버튼만. 로그인 돼 있으면 "내 정보"(이메일)·"활동 내역"(찜한 공연, 이제
  `GET /favorites?session_id=`로 서버에서 조회)·로그아웃 버튼.
- **정보구조 변경**: 지금 `/`(홈)에 있는 추천+검색 콘텐츠를 `/recommend`로 옮기고,
  `/`(홈)은 **올림픽공원 소식 게시판 스텁**이 차지한다(사용자가 나중에 API를 줄
  예정이라 지금은 "준비 중" 안내 카드만). `app/layout.tsx` 네비게이션도 "홈"(`/`)·
  "공연 추천"(`/recommend`)·"마이페이지"(`/mypage`) 3개로. 온보딩 완료 후
  `router.push("/")`도 `/recommend`로 수정.
- 나중에 실제 소식 API를 받으면 `/`(홈)에 연동만 추가하면 됨 — 지금은 백엔드 변경 없음,
  프론트 스텁만.

### 3. "날짜·장르로 찾기"에서 과거 공연 제외

- 증상: 날짜를 선택 안 하고 장르를 "전체"로 두면 `GET /performances?genre=` 호출이
  과거에 끝난 공연까지 전부 반환해서 결과가 너무 많음.
- 수정: `backend/performances_store.py`의 `PerformanceStore.filter()`에서 `on_date`가
  없어도 기본적으로 **종료된(과거) 공연은 제외**한다 — `scoring.is_ended()`를
  `period_overlaps`처럼 가져와서 `genre`/`on_date` 필터 전에 `not_ended` 마스크를 항상
  먼저 적용.
- 영향 범위 한정: `GET /performances/{id}`(단건 조회, 상세 페이지 링크용)는 그대로
  유지 — 과거 공연이어도 id로 직접 보면 보여야 한다. `recommend.similar_performances`
  등 추천 계열은 `CONTENT_FIRST_MODE`로 과거를 "참고용"으로 보여주는 게 의도된
  설계라 안 건드림 — 이번 수정은 `GET /performances` 단순 목록 조회에만 적용.

### 구현 순서(제안)

1. 3번(과거 공연 제외) — 작고 독립적, 리스크 낮음.
2. 1번(홈 화면 섹션 통합) — 프론트 단순 삭제, 백엔드 변경 없음.
3. 2번(로그인+마이페이지+홈 게시판 스텁) — 가장 큼, 새 의존성(`bcrypt`)·새 테이블·
   정보구조 변경 포함.

### 완료 기록 (2026-11-12)

- [x] **3번**: `performances_store.PerformanceStore.filter()`에 `scoring.is_ended` 기반
      `not_ended` 마스크 추가 — `on_date` 없어도 과거 공연 기본 제외. 단건 조회·추천
      계열은 그대로.
- [x] **1번**: `app/page.tsx`(현재 `/recommend`)에서 "이번 주말 공연" 섹션·관련 상태·
      `upcomingSaturday()` 제거, "추천 공연" 섹션 하나만 유지. 백엔드 변경 없음(이미
      `taste_recommend`가 콜드스타트로 자연히 대체).
- [x] **2번**:
      - 백엔드: `bcrypt` 설치, `User` 테이블, `POST /auth/signup`·`POST /auth/login`
        (성공 시 `session_id`를 `"user:{id}"`로 반환), 로그인/가입 시 익명 세션의
        `Favorite`·`UserPref` 이전(`_migrate_anonymous_session`), `GET /favorites?session_id=`
        복구.
      - 프론트: `lib/auth.ts`(signup/login/logout/getCurrentUser), `lib/session.ts`를
        익명/로그인 세션 둘 다 지원하도록 수정, `app/login/page.tsx` 신규,
        `app/mypage/page.tsx` 로그인 게이트 + "내 정보"·"활동 내역"으로 재작성.
      - 정보구조: 기존 홈 콘텐츠를 `app/recommend/page.tsx`로 옮기고, `app/page.tsx`는
        올림픽공원 소식 게시판 스텁("준비 중")으로 교체. `app/layout.tsx` 네비게이션에
        "공연 추천" 추가. 온보딩 완료 후 리다이렉트를 `/recommend`로 수정.
- **검증**: `npm run build`·`npm run lint` 통과 + 백엔드 TestClient로 signup/login/
  duplicate/wrong-password/찜 이전 전부 확인 + 실제 Chromium(Playwright)으로 홈·
  `/recommend`·날짜 미선택+장르 전체 검색·로그아웃/로그인 상태 마이페이지 스크린샷
  확인. 상세는 `tasks/verification.md` [2026-11-12] 참고.

### 4. 반복 시리즈 다음 회차 예측("매년 반복 예상") 제거

- 요청: 아직 확정 안 된 미래 일정을 "열릴 것으로 예상"처럼 보여주는 게 오해를 살 수
  있어서 빼기로 함.
- 수정: `scoring.py`에 `CONTENT_FIRST_MODE`와 독립된 새 스위치
  `INCLUDE_PREDICTED_SERIES = False` 추가 → `recommend.load_data()`가 이 스위치가
  꺼져 있으면 `series.build_predicted_rows()`로 만든 예측 행을 아예 후보 풀에 안 섞음.
  `series.py` 코드 자체는 안 지움 — 나중에 다시 켜고 싶으면 `True`로 바꾸면 됨(기존
  `CONTENT_FIRST_MODE`와 같은 "토글로 되돌리기" 설계를 그대로 따름).
- **알아둘 트레이드오프**: 예측 행이 빠지니 뮤지컬·페스티벌·어린이처럼 원래도 확정된
  예정 공연이 적었던 장르는 추천 5개 중 "과거 유사 공연 — 참고용"이 채우는 비중이
  커짐(TestClient로 장르별 확인: 뮤지컬·페스티벌·어린이는 5개 중 4~5개가 과거 참고용).
  빈 결과는 아니지만, 콘텐츠 자체가 더 과거 위주로 보일 수 있음 — 사용자가 감수하기로
  한 결과.
- 검증: TestClient로 `GET /performances`·`GET /recommend/me`·6개 장르
  `POST /recommend/onboarding` 전부 `status`에 "매년 반복 예상"이 하나도 없음을 확인 +
  실제 Chromium으로 `/recommend` 전체 검색 결과에도 없음을 재확인(`tasks/verification.md`
  [2026-11-12] 참고).

### 5. 홈 "올림픽공원 소식 게시판" 롤백 (2번의 일부를 되돌림)

사용자가 보도자료 API 서비스키를 받아와서 실제로 테스트해본 뒤 **기능 자체를 빼기로
결정**. 경위:

- 호출은 성공(`https://api.kcisa.kr/openapi/service/rest/meta/KSCkrep`, `resultCode: 0000`,
  올림픽공원 보도자료 1,080건). 필드는 `title`·`description`(이미지 포함 raw HTML)·
  `creator`·`collectionDb`("올림픽공원보도") 정도만 실제로 채워져 있었음.
- **`regDate`가 진짜 보도 날짜가 아니었음** — 같은 페이지 안의 2017년 글과 2024년 글이
  똑같은 `regDate`를 가짐 → 문화공공데이터광장에 수집된 시각일 뿐, 실제 게시판에 "최신
  순"으로 쓸 수 없음.
  `subjectCategory`·`temporal`·`uci`(원문 링크)·`rights` 등 나머지 필드는 100건 샘플
  전부 빈 값.
- 사용자 지시대로 **본문(title+description)에서 정규식으로 날짜 패턴 추출을 시도** →
  100건 중 **2건만 매칭**(그마저도 "2016년 9월 23일 열린다" 같은 행사 날짜 언급이지,
  보도 날짜가 아님) → 신뢰 불가 판정.
- **기능 삭제 처리**: `app/recommend/page.tsx`(추천+검색) 내용을 다시 `app/page.tsx`로
  옮기고 `/recommend` 라우트 삭제, `app/layout.tsx` 네비게이션에서 "공연 추천" 메뉴
  제거(2번 항목 이전으로 복귀), 온보딩 완료 리다이렉트도 `/`로 되돌림. 백엔드는 이
  기능을 위해 아무것도 만든 게 없어서(curl/python으로 외부 API만 테스트, 수집
  스크립트는 안 만듦) 되돌릴 것 없음.
- **키 처리**: 사용자가 채팅에 직접 붙여넣은 서비스키는 어떤 저장소 파일에도 커밋하지
  않음(CLAUDE.md "서비스키는 .env로 분리" 규칙) — 이 기능 자체를 빼기로 했으므로 `.env`에
  넣을 필요도 없어짐.
- 검증: `npm run build`·`npm run lint` 통과(처음 빌드 시 삭제된 `/recommend` 라우트의
  캐시된 타입 선언이 남아 `TS2307` 에러가 났는데, `.next` 캐시를 지우고 재빌드해서
  해결). 빌드 결과 라우트 목록에 `/recommend` 없이 `/`·`/login`·`/mypage`·`/onboarding`·
  `/performances/[id]`만 남는 것 확인.

### 6. 홈 화면 "날짜·장르로 찾기"를 달력 뷰로 교체 — 설계+구현

**문제**: 공연 목록이 항상 세로 리스트였고, 홈의 기본 섹션("추천 공연")은 추천된
공연만 보여줘서 추천에 안 걸린 공연은 날짜를 직접 입력해 검색해야만 보였음. 사용자가
코엑스 박람회 일정처럼 **월별 달력**으로 한눈에 보고 싶어함.

**설계**:
- 새 데이터·백엔드 변경 불필요 — `GET /performances`(장르 필터만, 날짜 없이 호출하면
  과거 제외한 전체 예정 공연)를 한 번에 받아서 프론트에서 날짜별로 계산.
- `frontend/lib/types.ts`에 `period`("YYYYMMDD YYYYMMDD") 파싱 유틸 추가.
- `frontend/components/PerformanceCalendar.tsx` 신규: 월 그리드(일~토) + ◀▶ 월 이동 +
  공연 있는 날짜에 점/개수 표시(여러 날짜에 걸친 공연은 기간 내 모든 날에 표시) + 날짜
  클릭 시 그 날 공연 목록을 아래에 카드로 표시(기존 `PerformanceCard` 재사용).
- `app/page.tsx`: "날짜·장르로 찾기" 섹션의 날짜 입력+검색 버튼을 달력으로 교체. 장르
  드롭다운은 유지해서 달력 점 표시를 좁히는 용도로 재사용. 상단 "추천 공연" 섹션은
  그대로 유지.

**완료 기록**:
- [x] `frontend/lib/types.ts`에 `parsePeriod()` 추가("YYYYMMDD YYYYMMDD" → `[Date, Date]`).
- [x] `frontend/components/PerformanceCalendar.tsx` 신규 — 월 그리드, 오늘 강조, 공연
      있는 날 점 표시(기간 전체 날짜에 표시), 날짜 클릭 시 그 날 공연 카드 목록, ◀▶ 월 이동.
- [x] `app/page.tsx`의 "날짜·장르로 찾기"를 "날짜로 찾기"(장르 드롭다운 유지)+달력으로
      교체. 장르 바뀌면 `GET /performances?genre=`를 다시 불러서 달력에 반영.
- [x] `npm run lint`에서 `react-hooks/set-state-in-effect` 1건 발견(장르 변경 시
      `setCalendarLoading(true)`를 effect 본문에서 동기 호출) → 초기 로딩 표시만 남기고
      제거해서 해결(장르 재조회 시엔 "불러오는 중" 문구 없이 조용히 갱신).
- [x] `npm run build`·`npm run lint` 통과.
- [x] 실제 Chromium(Playwright)으로 월 화면·날짜 선택·장르 필터(뮤지컬 선택 시 점 0개로
      정확히 줄어듦)·다음 달 이동 전부 스크린샷 확인. 서버 재시작·검증 과정은
      `tasks/verification.md` [2026-11-12] 참고.
- [x] **참고 디자인 반영**: 사용자가 준 URL(https://www.coex.co.kr/event/full-schedules/)의
      "캘린더형"을 WebFetch+Playwright 스크린샷으로 확인(요일별 주말 색상, 카테고리별
      색점+범례, "YYYY.MM" 월 헤더, 날짜 칸 안에 제목 텍스트). 그 사이트는 데스크톱
      와이드 레이아웃이라 칸 안에 제목을 그대로 넣는데, 우리는 모바일 우선이라 텍스트
      대신 **장르별 색점(최대 3개+"+N" 더보기)**·주말 요일/날짜 색상(일=rose, 토=sky)·
      장르 범례로 축약해서 반영. 브랜드 로고·정확한 색상표 등은 그대로 베끼지 않음.

### 6-1. "미분류" 장르 분류 버그 수정 (사용자 발견, 2026-11-12)

**증상**: "2026 정승환 10주년 콘서트"가 "미분류"로 떴는데, 장르 선택 드롭다운엔 애초에
"미분류"라는 옵션이 없어서 달력에 어디 속하는지 알 수 없는 항목이 새어나온 것.

**원인**: `pipeline/preprocessing/normalize_and_clean.py`의 `classify_genre()`가
KOPIS 매칭이 안 된(`unmatched`) 공연은 제목에 "콘서트"라고 써 있어도 장르를 추론할
규칙이 아예 없어서 전부 "미분류"로 떨어졌음. 미분류 1,247건 중 **475건이 제목에
콘서트/concert/CONCERT을 포함**.

**수정**:
1. `UNMATCHED_FALLBACK_KEYWORDS_BY_TITLE`(콘서트 키워드)을 추가하되, **KOPIS 매칭이
   안 된 행(`kopis_genre`가 빈 경우)에만** 적용 — 처음엔 `GENRE_KEYWORDS_BY_TITLE`에
   같이 넣었다가 "OOO 신년 콘서트"처럼 KOPIS가 이미 "클래식"으로 정확히 분류해둔
   매칭 공연까지 덮어써서 클래식이 18건→9건으로 반토막 나는 회귀를 실측으로 발견 →
   매칭 안 된 행 전용 폴백으로 분리해서 해결(뮤지컬/클래식/스포츠기타 전부 원래
   건수로 복구 확인).
2. `backend/performances_store.py`의 `filter()`에서 `genre == "미분류"`를 방어적으로
   항상 제외 — 앞으로 비슷한 분류 누락이 또 생겨도 달력·날짜검색에 "미분류"가 새는
   일 자체가 안 생기게 함. 남는 미분류(진짜 알 수 없는 772건, 전부 과거)는
   `venue_fallback.py`(같은 장소 다른 공연)로만 계속 노출.
3. 재실행: `normalize_and_clean.py`(→ 콘서트 538→1013건, 미분류 1247→772건) →
   `vectorize.py`(벡터 재생성) → `evaluate.py`(Precision@5 **0.855 그대로**, 회귀
   없음 확인).
4. 검증: `GET /performances` 응답에 "미분류" 장르 0건, "정승환 10주년 콘서트" genre가
   "콘서트"로 확인(curl). 실제 Chromium에서 달력 범례에 "미분류" 문구 0건(본문 전체
   검사) 확인. 상세는 `tasks/verification.md` [2026-11-12] 참고.

### 7. 찜한 공연 "예매 시간 다가오면 알림" — 보류 (착수 안 함)

사용자 요청으로 조사만 하고 구현은 보류. 핵심 블로커: **"예매 오픈 일시" 데이터가 어느
소스에도 없음** — KOPIS 상세(`data/raw/kopis/performance_detail.json`)·문체부 통합
공연정보(`data/raw/integrated_performance/kspo_filtered.json`) 원본을 직접 까봤지만
둘 다 공연 **기간**(`prfpdfrom`/`prfpdto`, `PERIOD`)만 있고 예매처별 오픈 시각 필드
자체가 없음(`relates`도 이름+URL뿐). 실제 예매 오픈 시각은 각 예매처(인터파크 등)가
개별 공지하는 거라 공공데이터로는 애초에 안 들어옴.
대안으로 (1) 공연 시작일 임박 알림(데이터 있음, 바로 구현 가능)과 (2) 사용자가 예매
오픈일을 직접 입력(수고 필요)을 제시했고, 알림 채널(이메일 — 로그인으로 이메일은 이미
있음 / 앱 내 배지만)도 같이 물었는데, **사용자가 "일단 이 작업은 아직 하지말자"고
보류 결정**. 나중에 재개할 때는 이 두 질문(트리거 기준·알림 채널)부터 다시 확인할 것.

### 8. 추천 공연 과거 제외 + 찜하기·로그인 시스템 삭제 (사용자 요청, 2026-11-12)

**1. 추천 공연 리스트에서 과거 공연 제외**: `recommend.taste_recommend()`가
`_eligible_mask(df, today, allow_historical=CONTENT_FIRST_MODE)`를 썼는데, 이걸
`allow_historical=False`로 고정 — `CONTENT_FIRST_MODE`(과거를 참고용으로 보여주는
전역 스위치)와 무관하게 "추천 공연" 섹션만 항상 날짜 기반으로 거르게 함.
`similar_performances`(상세 페이지 "비슷한 공연")는 요청 범위 밖이라 안 건드림.
**트레이드오프 예상**: 전에 이 설계 전환(CONTENT_FIRST_MODE 도입)의 원인이 "안 끝난
공연이 너무 적어서"였으므로, 되돌리면 장르에 따라 추천 결과가 5개보다 적게(또는
0개) 나올 수 있음 — 구현 후 실제 장르별 건수를 확인해서 보고함.

**2. 찜하기 시스템 삭제**: 백엔드 `Favorite` 모델·`POST/GET /favorites`, 프론트
`lib/favorites.ts`·상세 페이지 "찜하기" 버튼·`lib/api.ts`의 `addFavorite`/
`listFavorites` 전부 삭제.

**3. 로그인 시스템 삭제**: 백엔드 `User` 모델·`/auth/signup`·`/auth/login`·
`_migrate_anonymous_session`(찜 삭제로 이전할 찜 자체가 없어짐), `bcrypt` 의존성,
프론트 `lib/auth.ts`·`app/login/`. `lib/session.ts`는 로그인 분기 없이 익명
session_id만 쓰도록 되돌림.

**부수 정리**: 찜하기+로그인이 둘 다 없어지면 마이페이지가 보여줄 게 하나도 안 남아서
`app/mypage/`와 네비게이션의 "마이페이지" 링크도 같이 삭제(홈 하나만 남김). `UserPref`
(온보딩 장르 취향 저장)·`RecLog`(추천 로그)는 로그인·찜과 무관한 별개 기능이라 그대로
유지.

**설계 변경(대화 중 확정)**: 1번(과거 공연 제외)을 "장르별 취향 추천"에 그대로 적용하면
장르별 후보가 적어서 엉뚱한 장르로 채워지는 재발 버그가 실측으로 발견됨(뮤지컬·클래식·
페스티벌·어린이가 전부 똑같은 콘서트 5개로 수렴) → 사용자 제안으로 **온보딩 장르 선택
UI 자체를 없애고, 장르 구분 없이 "지금 예매 가능한 공연" 상위 3개**를 보여주는 걸로
설계 변경. 이에 따라 온보딩(`/onboarding`)·`UserPref`도 같이 삭제 대상에 포함됨.

**완료 기록**:
- [x] `recommender/recommend.py`에 `bookable_top()` 신규 — 장르 무관, 과거·미분류
      제외, 인기도+날짜근접도로 상위 top_k(기본 3)개. `taste_recommend`는 건드리지
      않고 그대로 둠(오프라인 평가 `evaluate.py`에서 Precision@5 측정용으로 계속
      쓰임 — API에서만 안 씀). 실측: 콘서트 3건(인기도 0.98/0.94/0.82 순)으로 정상
      동작 확인.
- [x] 백엔드: `POST /recommend/onboarding`·`POST/GET /favorites`·`POST /auth/signup`·
      `POST /auth/login` 전부 제거. `GET /recommend/me`가 `bookable_top()`을 쓰도록
      변경(session_id는 선택값, 로그 기록용으로만 유지). `models.py`에서 `User`·
      `UserPref`·`Favorite` 제거, `RecLog`만 남김. `schemas.py` 완전 삭제(남는 POST
      바디가 없어짐). `requirements.txt`에서 `bcrypt` 제거.
- [x] 프론트: `app/onboarding/`·`app/login/`·`app/mypage/`·`lib/favorites.ts`·
      `lib/auth.ts` 삭제. `lib/session.ts`를 익명 전용으로 되돌림. `lib/api.ts`에서
      `recommendOnboarding`·`addFavorite`·`listFavorites` 제거. `app/layout.tsx`
      네비게이션 "홈"만 남김. `app/page.tsx`에서 온보딩 배너 제거, "추천 공연" 섹션을
      "예매 가능한 공연"으로 개명(더 이상 개인화가 아니므로 정확한 라벨로). 상세 페이지
      "찜하기" 버튼 제거.
- [x] `npm run build`·`npm run lint` 통과(라우트 `/`·`/performances/[id]`만 남음).
      TestClient로 삭제된 엔드포인트 전부 404, 남은 엔드포인트 정상 동작 확인.
- [x] **재기동 중 발견한 버그**: 백엔드를 재시작했다고 생각했는데 실제로는 훨씬
      전(세션 초반)에 띄워둔 **오래된 프로세스가 포트 8000을 계속 쥐고 있었음**
      (`lsof -ti:8000`으로 실제 PID 확인, `nohup` 재실행은 포트 충돌로 조용히
      실패했었음) — 그 오래된 프로세스가 물고 있던 `app.db` 핸들이 그사이 여러 번
      지웠다 새로 만든 파일과 꼬이면서 `sqlite3.OperationalError: attempt to write
      a readonly database`로 `GET /recommend/me`가 500 → 브라우저에선 CORS 에러로
      보였음(TestClient로는 이 증상 자체가 재현 안 됨, DB 파일 상태에 의존적이라).
      PID로 직접 `kill -9` 하고 진짜 새 프로세스로 재기동해서 해결 — 전에 lessons.md
      에 적어둔 "서버 로그 경고를 끝까지 읽어야 한다"가 다시 한번 재현된 사례.
      실제 Chromium 콘솔 로그로 에러 0건, 화면에 "예매 가능한 공연" 3건 정상 렌더링
      확인.

## 8단계: 배포 (워크플로우 문서 4.8장) — 설계 (구현 전, 실행 안 함)

4.7장(pytest 43건·Lighthouse)까지 끝났으니 다음은 배포다. **실행은 전부 사용자 승인·
참여가 필요해서 설계만 기록하고 착수 안 함** — git 저장소 생성, GitHub 연동, Vercel/
Render 계정 연결은 내가 대신 할 수 없는 부분이 많다.

### 0. 선행 조건 확인 — 지금 상태

- **이 폴더는 아직 git 저장소가 아니다**(`.git` 없음). 배포 전 `git init` +
  GitHub 원격 저장소 연결이 먼저 필요하다 — Vercel·Render 둘 다 보통 GitHub 연동으로
  자동 배포하는 흐름이 가장 간단하다(CLI로 직접 배포하는 방법도 있지만 "매일 재수집
  → 재배포" 자동화와 궁합이 안 좋음).
- **`.gitignore`가 `data/processed/*`를 전부 무시하도록 돼 있다**(`performances.csv`·
  `performance_vectors.npz` 포함, `.gitkeep`만 예외). 이대로 배포하면 **백엔드가 서빙할
  데이터 자체가 배포 환경에 없어서 빈 화면만 뜬다** — `performances_store.py`가 서버
  시작 시 이 두 파일을 읽기 때문. 두 파일은 작아서(CSV 464KB + npz 64KB) 커밋해도
  무방 — **`data/raw/*`(원본)는 그대로 무시하고, `data/processed/performances.csv`·
  `performance_vectors.npz`만 예외로 빼는 쪽을 추천**(아래 "확인 필요" 참고).

### 1. 프론트엔드 (Vercel)

- GitHub 저장소를 Vercel에 연결, `frontend/`를 루트 디렉터리로 지정.
- 환경변수 `NEXT_PUBLIC_API_BASE`를 Render에 배포된 백엔드의 실제 URL로 설정.
- 빌드 명령은 `npm run build`(Next.js 기본 감지로 충분).

### 2. 백엔드 (Render 또는 Railway, 무료 티어)

- `backend/requirements.txt` 설치 + `uvicorn main:app --host 0.0.0.0 --port $PORT`
  실행 명령으로 배포.
- **CORS 좁히기**: 지금 `allow_origins=["*"]`로 열어둔 걸 실제 Vercel 배포 도메인
  하나로 좁혀야 한다(`backend/README.md`에 이미 메모해둔 대로).
- **SQLite(`app.db`) 영속성 주의**: Render 무료 티어는 재배포·슬립 때 파일시스템이
  초기화될 수 있어서 `rec_logs`(추천 노출 로그)가 날아갈 수 있음 — 로그 용도라
  치명적이지 않지만, 꼭 보존하고 싶으면 유료 디스크나 외부 DB가 필요하다는 점을
  알아둘 것(MVP 단계에서는 감수하고 진행 추천).

### 3. GitHub Actions — 매일 재수집

- `.github/workflows/daily.yml` 신규: `pipeline/collection` → `pipeline/preprocessing`
  → `recommender/vectorize.py` 순서로 실행 후, 바뀐 `data/processed/*` 커밋(또는
  Render 쪽에 재배포 훅 호출).
- **GitHub Secrets로 등록해야 할 서비스키 4종**(`.env.example` 기준):
  `PERFORMANCE_INTEGRATED_API_KEY`, `KSPO_PERFORMANCE_API_KEY`,
  `KSPO_PARKING_WEATHER_API_KEY`, `KOPIS_API_KEY`.
- Render는 파일 변경만으로 자동 재배포되지 않으므로, 워크플로우 마지막 단계에서
  Render의 Deploy Hook(배포 URL)을 호출하거나, "데이터 커밋 → Render가 그 커밋을
  감지해 재배포"하도록 Render 쪽을 "Auto-Deploy on push" 설정으로 맞춰야 한다.

### 4. 완료 기준 (워크플로우 문서 7장 최종 체크리스트)

- [ ] 공개 URL(프론트·백엔드 둘 다)
- [ ] README에 실행 방법 + "한국체육산업개발 공공데이터 활용" 출처 표기(CLAUDE.md
      필수 규칙 — 지금 각 디렉터리 README에 있는지 재확인 필요)
- [ ] 발표 자료 (이건 내가 대신 못 만드는 부분 — 필요하면 별도 요청)

### 확인 완료 (사용자 결정, 2026-11-13)

1. `data/processed/performances.csv`·`performance_vectors.npz` → **git에 직접 커밋**
   (CI가 매번 새로 만드는 방식 대신 — 두 파일이 작고, 지금 당장 CI 파이프라인까지
   같이 구축하는 건 범위가 커서 보류). `performances_matched.json`(중간 산출물,
   980KB, 백엔드가 안 읽음)은 그대로 `.gitignore` 유지.
2. "git 저장소 아님" 블로커 범위 → **GitHub 원격 저장소 연결까지 포함**.
3. GitHub 저장소 가시성 → **public**(공모전 제출용).
4. Render vs Railway는 이번 두 블로커 해결 범위 밖(실제 백엔드 배포 단계에서 결정) —
   미확인 상태 유지.

### 블로커 해결 실행 순서 (설계, 2026-11-13 — 실행 전 승인 대기)

**환경 확인 결과**: `git`은 설치돼 있음(2.53.0)·`gh`(GitHub CLI)는 설치 안 돼 있음 →
GitHub repo 생성은 CLI로 자동화 못 하고 웹 UI에서 사용자가 직접 만들거나, 만든 뒤
remote URL만 알려주면 나머지(`remote add`·`push`)는 git으로 진행 가능.

1. **`.gitignore` 수정**(블로커 2): `data/processed/*` 예외 규칙 2줄 추가 —
   `!data/processed/performances.csv`, `!data/processed/performance_vectors.npz`.
   `data/raw/*`·`.env`·DB 파일 등 기존 제외 규칙은 그대로 유지.
2. **`git init`**(블로커 1) — 프로젝트 루트에서 1회.
3. **첫 커밋 전 점검**: `git status`로 어떤 파일이 스테이징되는지 확인 —
   `.env`·`data/raw/*`·`*.db` 등이 안 들려오는지 재확인(이미 `.gitignore`에 있지만
   커밋 직전 한 번 더 눈으로 확인). `.claude/settings.local.json`(로컬 권한 설정,
   비밀값 없음)은 관례상 커밋 안 하는 게 깨끗해서 `.gitignore`에 추가 제안(사소한
   추가 — 두 블로커와 무관, 원치 않으면 생략 가능).
4. **첫 커밋**: `git add -A` → `git commit -m "Initial commit"`류.
5. **GitHub 저장소 생성**(public) — `gh` 없어서 사용자가 https://github.com/new 에서
   직접 만들거나, 만든 뒤 remote URL(`https://github.com/<user>/<repo>.git`)을 알려주면
   내가 이어서 진행.
6. **원격 연결·푸시**: `git remote add origin <url>` → `git branch -M main` →
   `git push -u origin main`.

**실행 승인 필요**(CLAUDE.md "모든 실행 작업은 승인 없이 임의로 실행하지 않는다"):
1~4번(로컬, 되돌리기 쉬움)과 5~6번(GitHub에 올라가는 순간부터 되돌리기 어려움)을
나눠서 승인받는 걸 추천 — 1~4번 먼저 진행하고 결과 확인 후 5~6번 진행.

### 완료 기록 (2026-11-13, 1~4번)

- [x] **1. `.gitignore` 수정**: `!data/processed/performances.csv`·
      `!data/processed/performance_vectors.npz` 2줄 추가. 추가로(설계에 적어둔 사소한
      제안) `.claude/settings.local.json`도 로컬 전용 권한 설정이라 `.gitignore`에 추가.
- [x] **2. `git init`** — 프로젝트 루트에서 실행(`master` 브랜치로 생성됨, 아직 `main`으로
      안 바꿈 — 5~6번에서 `git branch -M main` 예정).
- [x] **3. 커밋 전 점검**: `git add -A` 후 `git status`로 스테이징 목록 확인 —
      `.env`·`data/raw/*`·`*.db`·`performances_matched.json` 전부 안 들어온 것,
      `data/processed/performances.csv`·`performance_vectors.npz`는 들어온 것 확인.
      `.claude/settings.local.json`은 `git rm --cached`로 제외.
- [x] **4. 첫 커밋**: `git commit`(해시 `cdbd722`, 89개 파일). 커밋 전 **git 계정 미설정**
      문제 발견(`user.name`/`user.email` 없음) → 사용자 확인 후 전역(`--global`)으로
      `user.name=jiwoo`, `user.email=jiwoo7914@gmail.com` 설정(사용자 직접 지정값,
      CLAUDE.md "모든 실행 작업은 승인 필요" 원칙에 따라 git config 변경도 승인받고 진행).
      커밋 후 `git status` clean 확인.

**다음**: 5~6번(GitHub public repo 생성·remote 연결·push)은 `gh` CLI가 없어서 사용자가
https://github.com/new 에서 직접 만들거나 remote URL을 알려주는 방식으로 진행 — 아직
착수 안 함, 승인 대기.

### 이메일 프라이버시 조정 (2026-11-13, 추가)

public repo로 올라가면 커밋 작성자 이메일이 평문으로 영구 노출된다는 점을 사용자가
확인 질문해서, push 전에 조정함:
- **전역(`--global`) 설정은 그대로**(`user.name=jiwoo`, `user.email=jiwoo7914@gmail.com`)
  — 이 컴퓨터의 다른(비공개) 저장소에는 영향 없음.
- **이 저장소만 local로 override**: `git config user.email
  "275266434+jiwoo-03@users.noreply.github.com"`(GitHub 계정 `jiwoo-03`의 공식
  noreply 주소, 사용자가 GitHub Settings→Emails에서 직접 확인해 제공).
- 이미 만든 첫 커밋(`cdbd722`)도 `git commit --amend --author=...`로 author/committer를
  noreply 주소로 교체 → 새 해시 `acba987`. (`--amend`라 해시가 바뀌는 건 정상 — 아직
  push 전이라 문제 없음.)

### 완료 기록 (2026-11-13, 5~6번 — GitHub 연결·push)

- [x] **5. GitHub repo 생성**: 사용자가 https://github.com/new 에서 직접 생성
      (`jiwoo-03/olympic-park-performance-recommender`, public, README/.gitignore/
      license 전부 미생성 — 로컬 히스토리와 충돌 방지).
- [x] **6. 원격 연결·푸시**: `git remote add origin
      https://github.com/jiwoo-03/olympic-park-performance-recommender.git` →
      `git branch -M main`. **push 인증 이슈**: 이 샌드박스 환경은 GitHub 로그인
      프롬프트(tty)를 못 띄워서(`fatal: could not read Username ... No such device
      or address`) 내가 직접 push 못 함 → 사용자가 Personal Access Token(`repo` scope)을
      발급해서 **본인 터미널에서 직접** `git push -u origin main` 실행(토큰은 채팅에
      안 노출, 비밀번호 입력란에만 붙여넣음). 완료 후 `git fetch origin`+
      `git branch -vv`로 `origin/main`이 로컬 `main`과 동일한 커밋(`acba987`)을
      가리키는 것 확인 — **블로커 1·2 둘 다 완전히 해결**.
- [x] **후속 커밋**: 이번 대화 중 기록 갱신분(`CLAUDE.md`·`tasks/todo.md`)을 2번째
      커밋으로 추가 push.

### 본작업 실행 계획 (2026-11-14, 설계 — 실행 전 승인 대기)

9단계(디자인 다듬기) 완료 후 이어서 진행. 블로커 1·2 해결 때와 같은 이유로 **외부
플랫폼 계정 작업은 사용자가 직접 해야 한다** — 계획만 세우고 단계별로 승인받아 진행.

**사용자 결정(2026-11-14)**: 백엔드 호스팅 **Render**. GitHub Actions 매일 재수집
자동화는 **이번엔 생략**(지금 커밋된 `performances.csv`/벡터 스냅샷으로 서비스가 정상
동작하고, 공모전 제출(데모) 목적엔 매일 자동 갱신이 필수가 아니라고 판단 — 나중에
필요해지면 별도 작업). 실제 화면에 "한국체육산업개발 공공데이터 활용" 출처 문구가
**README에만 있고 화면 어디에도 없는 걸 발견**(CLAUDE.md 필수 규칙 재확인 중) →
**이번에 화면에도 추가**하기로 함.

**용도 재확인(2026-11-14)**: 공모전 제출 자체는 소스코드·발표자료 위주이고, 배포는
**심사 발표 때 QR코드로 모바일 시연하는 용도**로만 쓴다(상시 운영 서비스가 아님).
그래서 계획을 다음 두 가지 관점으로 조정:
- **QR코드 생성을 완료 기준에 새로 추가**(아래 E) — 최종 산출물은 "Vercel URL을 담은
  QR코드 이미지"다.
- **Render 무료 티어 콜드 스타트 주의**: 무료 Web Service는 일정 시간 요청이 없으면
  슬립 상태가 되고, 슬립에서 깨는 첫 요청은 30~50초가량 걸릴 수 있음. 발표 중 QR을
  찍었는데 한참 안 뜨면 치명적이므로, **발표 시작 몇 분 전에 미리 한 번 접속해서
  깨워두는 걸 "데모 당일 체크리스트"에 명시**(인프라를 더 복잡하게 만들지 않고 운영
  절차로 해결 — 상시 서비스가 아니므로 유료 티어·상시 핑(ping) 자동화는 과함).

#### A. 로컬 준비 (내가 실행, 승인 후 — 로컬·되돌리기 쉬움, 외부 계정 불필요)

1. **출처 표기 추가**: `frontend/app/layout.tsx`의 공통 레이아웃(모든 페이지에 뜨는
   footer 등)에 "한국체육산업개발 공공데이터 활용" 한 줄 추가.
2. **CORS 유연화**: `backend/main.py`의 `allow_origins=["*"]`를 환경변수
   `ALLOWED_ORIGIN`(미설정 시 `"*"`로 폴백) 기반으로 바꿔서, Vercel URL이 정해진 뒤
   코드를 다시 고치지 않고 Render 대시보드에서 환경변수 값만 넣으면 좁혀지도록 함(Render
   환경변수 변경은 재배포 커밋 없이 바로 적용됨).
3. **시작 커맨드 문서화**: `backend/README.md`에 지금은 로컬 전용(`--reload`) 커맨드만
   있음 → Render "Start Command" 란에 그대로 붙여넣을 `uvicorn main:app --host 0.0.0.0
   --port $PORT` 커맨드를 명시.
4. **루트 `README.md`**: 배포 URL 자리(placeholder) + Render/Vercel 각각의 설정값
   (Root Directory, Build/Start Command, 환경변수) 섹션 추가.
5. 위 변경 로컬 커밋(push는 B 단계 전/후 사용자와 상의해서 진행).

**완료 기록 (2026-11-14)**

- [x] 1~4번 전부 구현: `frontend/app/layout.tsx` footer(출처 문구, `text-muted` 토큰 —
      9단계에서 WCAG AA 검증된 색상이라 재검증 불필요), `backend/main.py`
      `ALLOWED_ORIGIN` 환경변수(미설정 시 `"*"`), `backend/README.md`·루트
      `README.md`에 Render Start Command·배포 URL·설정값 섹션 추가.
- [x] 검증: `npm run build`·`npm run lint` 통과, `ALLOWED_ORIGIN` 설정 시 실제로 반영되는지
      TestClient로 확인, `backend/tests/` 15건 전부 통과(회귀 없음).
- **다음**: B(Render/Vercel 외부 계정 작업)는 사용자가 직접 진행 — 승인 대기.
- **push 시점 결정(2026-11-14)**: A단계 커밋(`81c96f1`)은 B단계가 끝날 때까지 로컬에만
  두고, B 완료 후 C단계 변경분(CORS 좁히기·README URL 채우기)까지 합쳐서 한 번에
  push하기로 함.

#### B. 사용자가 외부 플랫폼에서 직접 해야 하는 작업 (내가 대신 못 함) — 완료

1. [x] **Render**: `backend`를 Root Directory로 Web Service 생성 → 배포 URL
   `https://olympic-park-performance-recommender.onrender.com` 확보. `curl`로
   `GET /performances` 200 확인(실제 공연 데이터 응답, 2026-11-14).
2. [x] **Vercel**: `frontend`를 Root Directory로 Import, 환경변수
   `NEXT_PUBLIC_API_BASE`는 처음에 "Production and Preview"만 선택 가능해서(Development
   제외 — 로컬은 기본값 `127.0.0.1:8000`을 쓰니 문제 없음) 그렇게 설정 → 배포 URL
   `https://olympic-park-performance-recommende.vercel.app` 확보. **주의**: Vercel이
   처음 보여준 랜덤 해시 붙은 URL(`...-fy7zmg2im.vercel.app`)은 Vercel SSO 로그인으로
   리다이렉트되는 **Preview 배포 URL**이었음 — Settings → Domains의 해시 없는 production
   도메인이 실제로 로그인 없이 공개되는 QR용 주소. `curl`로 200 확인, `<title>` 정상.
   **A단계 커밋(footer 출처 문구)이 아직 push 전이라 지금은 footer가 안 보이는 게
   정상** — C에서 push 후 재확인 예정.

#### C. 양쪽 URL 확인 후 마무리 (내가 실행, 승인 후) — 완료 (2026-11-14)

1. [x] 사용자가 Render 대시보드에서 `ALLOWED_ORIGIN` 환경변수를 Vercel production
   도메인(`https://olympic-park-performance-recommende.vercel.app`)으로 설정 →
   push(A+C 커밋)로 Render가 재배포되며 반영됨(처음 2회는 재배포 전이라 `*`였고,
   3번째 polling에서 좁혀진 값 확인 — 아래 4번 참고).
2. [x] `curl`로 두 공개 URL 응답 확인 — 백엔드 `GET /performances` 200(실데이터),
   프론트 홈 200 + footer 출처 문구 정상 노출.
3. [x] 루트 `README.md`의 배포 URL placeholder를 실제 값으로 채워 커밋(`895582b`) →
   사용자가 직접 `git push`(샌드박스는 GitHub 로그인 프롬프트를 못 띄워 push 불가 —
   기존에 겪은 환경 제약과 동일).
4. [x] CORS 좁히기 최종 확인: 허용된 Origin(Vercel URL)으로는
   `access-control-allow-origin` 헤더가 정확히 그 값으로 오고, 허용 안 된 Origin
   (`https://evil-example.com`)으로는 헤더 자체가 안 옴(차단 확인). 상세는
   `tasks/verification.md` [2026-11-14] 참고.

#### D. QR코드 생성 (최종 산출물, 내가 실행, 승인 후)

1. **모바일 접속 재확인**: C.2에서 확인한 Vercel URL을 실제 모바일 화면 폭으로도
   한 번 더 확인(이미 "모바일 우선 반응형"으로 구현돼 있지만, 데모 당일 바로 쓸
   화면이라 재확인 가치 있음).
2. **QR 생성 방식 결정**(둘 중 하나, 실행 시점에 선택):
   - (a) Python `qrcode` 라이브러리로 `.venv`에 설치 후 PNG 생성(설치는 사용자 승인
     필요 — `bcrypt` 추가 때와 같은 절차).
   - (b) 외부 설치 없이 자체완결 HTML(Artifact)에 QR 인코딩 로직을 인라인 JS로 넣어
     화면에 렌더링(발표 중 노트북 화면에 띄워놓고 찍게 하거나, 그 화면을 캡처해 인쇄).
   - 둘 다 **URL을 외부 QR 생성 API(제3자 서버)로 보내지 않는다** — 로컬/자체완결
     생성만 쓴다(공모전 제출용 URL을 불필요하게 외부에 노출하지 않기 위함).
3. 생성한 QR 이미지를 사용자에게 전달(파일 경로 또는 Artifact 링크) — 인쇄·슬라이드
   삽입은 사용자가 진행.

#### E. 완료 기준 (워크플로우 문서 7장 최종 체크리스트 + 시연 목적 추가분)

- [ ] 공개 URL(프론트·백엔드 둘 다)
- [ ] README 실행 방법 + 출처 표기(이번에 화면에도 반영)
- [ ] **QR코드 이미지**(Vercel URL 인코딩, 모바일 스캔 확인됨)
- [ ] **데모 당일 체크리스트**: 발표 몇 분 전 Render URL 미리 접속해 깨워두기
- [ ] 발표 자료 (사용자 작업 — 필요하면 별도 요청)

#### 범위 밖(이번엔 생략, 사용자 결정)

- GitHub Actions `.github/workflows/daily.yml`(매일 재수집→재배포, 서비스키 4종
  GitHub Secrets 등록 포함)은 이번 배포 작업 범위에서 뺀다. 지금 스냅샷으로 서비스는
  정상 동작하므로 배포를 막는 블로커가 아님 — 필요해지면 그때 별도로 설계·착수.
- Render 무료 티어 콜드 스타트 해소를 위한 상시 핑/유료 플랜 전환도 범위 밖 — 상시
  운영 서비스가 아니라 1회성 시연이므로 "발표 전 깨워두기" 운영 절차로 충분하다고 판단.

**실행 승인 필요**: A(로컬)부터 승인받아 진행 → 완료 후 B(외부 계정, 사용자 직접)로
안내 → B 결과(두 URL) 받으면 C로 마무리 → D(QR코드 생성)까지 끝나야 완료. 지금은
설계만, 아직 착수 안 함.

## 9단계: 디자인 다듬기 (2026-11-13~ , 진행 중)

배포 전 CLAUDE.md "알려진 이슈"에 남겨뒀던 보조 텍스트 색상 대비 문제를 포함해 전체적인
룩을 다듬는 단계. 사용자가 올림픽공원 공식 심볼마크 파일(`recommender/olympicpark_pi_symbol.jpg`·
`.ai`)을 제공하며 "바로 적용하지 말고 시안부터 만들어서 보여달라"고 요청.

### 1. 홈 화면 디자인 시안 (Artifact로 미리보기)

- 심볼마크 링 그래픽에서 실제 픽셀 색을 추출(`#1f5e49`·`#3c9b47`·`#16a06a`·`#2bb8d8`·
  `#c3d62e` 등)해 브랜드 팔레트로 구성, WCAG AA 대비(4.5:1)를 직접 계산해 검증.
  "스포츠/기타" 장르는 추천 로직에서 실제로 장르 신호를 안 주는(`NO_GENRE_SIGNAL`) 버킷
  이라는 점에 맞춰 색도 중립(stone)으로 분리 — 비주얼이 실제 시스템 동작을 반영하게 함.
  데이터는 `performances.csv` 실제 값(TXT·에픽하이·조용필 등, 2026-11-13 기준) 사용.
  **Artifact로 publish해 사용자 승인 전 미리보기만 제공, 코드에는 미반영.**
- 사용자 확인 질문: "포스터 있는 공연도 그라데이션으로 바뀌는 거냐" → 아니다, Artifact
  자체가 외부 이미지 로딩을 CSP로 차단해서 미리보기에서만 전부 그라데이션으로 보인
  것이고 실제 반영 시 포스터 있는 공연은 그대로 실사진이 나온다고 설명.

### 2. 포스터 없는 공연의 그라데이션 대체 — 완료 (사용자 승인, 2026-11-13)

시안 중 "그라데이션 포스터" 아이디어만 먼저 실제 코드에 반영(나머지 전체 팔레트 교체는
범위 밖, 아직 미반영).

- [x] `frontend/lib/posterGradient.ts` 신규: 브랜드 그라데이션 5종 중 제목 문자열 해시로
      결정적 선택(새로고침해도 같은 공연은 항상 같은 그라데이션).
- [x] `frontend/components/PerformanceCard.tsx`: 포스터 없을 때의 빈 회색 박스
      (`bg-black/5`)를 `posterGradient()` 적용 박스로 교체.
- [x] `frontend/app/performances/[id]/page.tsx`: 상세 페이지도 동일 적용. 기존엔
      포스터 없으면 아예 아무것도 안 그려서(조건부 렌더링 자체가 없었음) 빈 공백이었는데,
      이제 그라데이션 블록이 항상 그려짐(레이아웃 크기는 기존과 동일하게 `aspect-[2/3]`
      유지 — CLS 영향 없음).
- [x] `npm run build`·`npm run lint` 통과.
- [x] **재기동 중 발견한 환경 이슈**: 파일을 수정했는데도 `next dev`가 HMR로 반영을 못
      해서(포스터 없는 공연 상세 페이지 접속해도 변경 전 모습 그대로) 처음엔 버그로
      오인함 — WSL에서 `/mnt/c/...` 경로의 파일 변경을 Turbopack 파일 감시자가 못 잡는
      문제로 추정(이 프로젝트에서 반복적으로 겪은 WSL 특유의 환경 이슈 계열).
      `.next` 캐시 삭제 + dev 서버 완전 재시작으로 해결. **다음에도 "분명히 고쳤는데
      화면이 그대로"면 먼저 dev 서버를 완전히 내렸다 올릴 것.**
- [x] 실제 Chromium(Playwright)으로 검증: 포스터 없는 실제 공연("2026 정승환 10주년
      콘서트", id=15)의 상세 페이지에 그라데이션 정상 렌더링 확인. 홈 화면 "예매 가능한
      공연" 3건(TXT·로이킴·조용필, 전부 실제 포스터 보유)은 기존처럼 실사진 그대로
      나오는 것도 함께 확인(그라데이션으로 안 바뀜 — 의도대로 포스터 있는 공연은
      안 건드림).

### 3. 전체 팔레트·로고칩·대비 수정 — 완료 (사용자 승인 "전부 적용", 2026-11-13)

사용자가 "로고 등 다른 스타일이 안 적용된 것 같다"고 지적 → 그라데이션 포스터만 먼저
반영했던 걸 확인시켜주고, 시안의 나머지(로고칩+전체 팔레트+대비 수정) 전부 적용 승인받음.

- [x] `frontend/app/globals.css`: 심볼마크에서 추출한 토큰 전체 등록(`--brand`·
      `--brand-fill`·`--teal`·`--teal-fill`·`--sky`·`--sky-fill`·`--lime`·`--amber`·
      `--amber-fill`·`--stone`·`--muted`·`--surface`·`--surface-2`·`--line`), Tailwind
      v4 `@theme inline`으로 유틸리티 클래스화(`bg-brand`, `text-muted` 등). 라이트/다크
      둘 다 WCAG AA(4.5:1) 직접 계산해서 통과하는 값만 텍스트 토큰으로 등록(`-fill`
      접미사 토큰은 장식 전용, 텍스트 대비 미검증).
- [x] `frontend/public/olympic-park-mark.png` 신규 — 심볼마크 원본에서 링만 크롭한
      로고 에셋. `app/layout.tsx` 헤더에 흰 배지 칩으로 추가(`alt=""` — 옆에 이미 텍스트
      링크로 같은 이름이 있어서 스크린리더 중복 안내 방지).
- [x] `text-gray-400/500` 전부 `text-muted`로 교체(`page.tsx`·`PerformanceCard.tsx`·
      `performances/[id]/page.tsx`·`PerformanceCalendar.tsx`) — Lighthouse가 찾아놓고
      "디자인 다듬기로 미룬다"고 보류했던 그 이슈. `StatusBadge.tsx`의 "과거 유사 공연"
      배지(`bg-gray-100 text-gray-500`, 대비 4.39 — AA 미달 확인)도 `bg-surface-2
      text-muted`(대비 6.05)로 교체.
- [x] `PerformanceCalendar.tsx`: 장르 점 색상을 심볼마크 팔레트로 재배색(콘서트=brand-fill·
      뮤지컬=teal-fill·클래식=sky-fill·페스티벌=lime·어린이=amber-fill·스포츠/기타=stone).
      "스포츠/기타"만 중립(stone)인 건 의도적 — `vectorize.NO_GENRE_SIGNAL`과 마찬가지로
      이 장르가 실제로 신호를 안 주는 잡동사니 버킷이라는 걸 비주얼에도 반영.
      주말 색상도 처음엔 브랜드 팔레트로 통일(일요일 `text-sky`, 토요일 `text-brand`)했다가,
      사용자가 "빨강=일요일" 관례를 되돌려달라고 요청 → `--sunday`(#e11d48/다크 #fb7185)·
      `--saturday`(#0369a1/다크 #38bdf8) 전용 토큰을 별도로 추가해 원래 색감으로 복구
      (둘 다 WCAG AA 재검증 통과). 브랜드 팔레트와는 별개 토큰으로 분리해서 앞으로
      브랜드 색을 바꿔도 주말 색엔 영향 없게 함.
- [x] `bg-black/5`·`border-black/10` 등 임시 투명도 유틸리티를 `bg-surface-2`·
      `border-line` 토큰으로 정리(5개 파일).
- [x] `npm run build`·`npm run lint` 통과.
- [x] **재기동 환경 이슈 재발**: 이번에도 `next dev`가 WSL `/mnt/c` 파일 변경을 못 잡아서
      `.next` 캐시 삭제 + 서버 완전 재시작으로 해결(9단계 2번과 동일 증상 — 앞으로 "분명히
      고쳤는데 그대로"면 매번 이 절차부터).
- [x] 실제 Chromium(Playwright)으로 라이트/다크 모드 둘 다 홈·상세 페이지 스크린샷 확인 —
      로고칩·브랜드 팔레트·그라데이션 포스터·달력 장르색·과거 배지 전부 의도대로 렌더링.

# Verification

작업을 마친 뒤 거친 검증을 날짜순으로 기록한다. 형식:

## [YYYY-MM-DD] <무엇을 검증했는지>

**검증 대상**: <어떤 작업/변경을 검증하는지>
**검증 방법**: <어떻게 확인했는지 — 실행한 명령, 비교한 값·파일 등>
**결과**: 통과 / 실패 — 실패라면 구체적으로 무엇이 틀렸는지
**lessons.md 반영**: 반영함(날짜 링크) / 해당 없음

## [2026-11-12] 0. 데이터 보강 (synopsis, venue_normalized, venue_fallback)

**검증 대상**: `pipeline/preprocessing`에 추가한 `synopsis`(KOPIS `sty`)·`venue_normalized`
컬럼, `recommender/venue_fallback.py`의 같은 장소 부가 추천.
**검증 방법**: `python run_all.py`로 파이프라인 재실행 → `performances.csv` 컬럼·분포 확인 →
`venue_fallback.same_venue_fallback()`을 KSPO DOME의 미분류 공연 하나로 직접 호출.
**결과**: 통과, 단 실행 중 두 가지를 발견해 바로 고쳤고 하나는 설계에 영향:
  1. (고침) `venue_normalized` 1차 실행 결과 "기타"가 356건(18%)으로 과도 — 원인은 "체조경기장"
     (KSPO DOME의 옛/별칭)과 "우리금용아트홀"(오타) 키워드가 규칙에 없었음. 추가 후 150건(7.6%)
     으로 줄었고, 남은 150건은 표본 확인상 올림픽공원 내 KOPIS 미등록 장소(벨로드롬·광장·축구장
     등)라 "기타"가 맞음.
  2. (설계 영향, 미수정) KOPIS 원본 상세 812건 중 `sty`(줄거리)가 채워진 건 **12건(1.5%)뿐**.
     버그가 아니라 KOPIS 쪽 데이터 자체의 한계. → `tasks/todo.md` "1. 공연 벡터"에서 "출연진+
     줄거리 임베딩"은 사실상 줄거리가 거의 없다고 가정하고 설계해야 함(출연진·제목 위주, 줄거리는
     있을 때만 보너스).
  3. `venue_fallback.same_venue_fallback()`은 같은 장소의 예정 공연만 정상 반환(과거 공연·자기
     자신 제외 확인됨).
**lessons.md 반영**: 해당 없음(사용자 지적 아닌 자체 검증에서 바로 수정, 패턴화할 반복 실수는
아님).

## [2026-11-12] KOPIS 박스오피스 수집 (인기도 신호)

**검증 대상**: `pipeline/collection/collect_kopis_boxoffice.py` 신규 수집 스크립트.
**검증 방법**: 사전에 `/openApi/restful/boxoffice`를 테스트 호출(기존 `KOPIS_API_KEY` 재사용,
기간·rows 제한 확인) → 스크립트 작성 → 승인받아 실제 실행 → `data/raw/kopis/boxoffice.json`
생성 여부와 우리 데이터(`kopis_mt20id`)와의 겹침을 직접 확인.
**결과**: 통과. 최근 12개월, 600건(distinct 424건) 수집, 올림픽공원 공연과 겹치는 건 84건
(매칭 공연 651건의 약 13%). API는 기간 최대 31일 제한이 있어 월 단위로 순회 호출하도록
설계했고 실제로도 각 호출이 정상 완료됨. `data/raw` 기존 파일은 건드리지 않고 새 파일만 추가됨.
**lessons.md 반영**: 해당 없음.

## [2026-11-12] 공연 벡터 생성 (vectorize.py)

**검증 대상**: `recommender/vectorize.py` — 장르 원-핫 + 출연진/제목/줄거리 TF-IDF를 합친
공연 벡터, `data/processed/performance_vectors.npz`.
**검증 방법**: 실행 후 (1) 로그로 차원·빈 벡터 건수 확인 → 103건이 전부 왜 빈 텍스트가
됐는지 직접 열어봄, (2) 같은 출연진이 겹치는 공연 쌍과 무작위 다른 콘서트 간 코사인
유사도를 비교.
**결과**: 통과, 실행 중 버그 하나를 발견해 바로 고침:
  1. (고침) `np.divide(..., where=genre_norm>0)`에 `out=`을 안 줘서 `UserWarning`(초기화
     안 된 메모리 사용 경고) 발생. 지금 데이터는 `genre`가 항상 7종 중 하나라 실제로
     문제가 된 행은 없었지만(`genre_norm`이 0인 행 없음), 조건을 안 타는 행이 생기면
     쓰레기값이 들어갈 수 있는 잠재 버그라 `out=np.zeros_like(...)`로 수정.
  2. 텍스트 성분이 전부 0인 103건은 버그가 아니라 `unmatched`(96건 미분류 포함) 행의
     제목이 "주간행사계획(10.25-10.31)"처럼 유일해서 `min_df=2` 필터에 다 걸린 것 —
     장르 블록만으로 유사도를 계산하는 정상적인 저하(degradation).
  3. **기능 검증**: 같은 가수("박지현")의 공연 두 건 간 코사인 유사도 0.766, 무작위 다른
     콘서트와는 0.500 — 장르만으론 이 차이가 안 나므로 출연진 텍스트 성분이 실제로
     유의미하게 작동함을 확인.
**lessons.md 반영**: 해당 없음(자체 검증에서 바로 수정, 반복되는 패턴은 아님).

## [2026-11-12] popularity_score 조인

**검증 대상**: `normalize_and_clean.py`의 `build_popularity_map()`/`popularity_score` 컬럼 —
`boxoffice.json`을 `kopis_mt20id`로 조인해 0~1 점수로 정규화.
**검증 방법**: 승인받아 `pipeline/preprocessing` 재실행 → 로그로 매칭 건수 확인 → 상위 점수
공연 목록을 상식과 대조(대형 K-pop 투어가 1등권인지).
**결과**: 통과. `matched` 651건 중 77건(11.8%)이 popularity_score > 0. 1위는 TOMORROW X
TOGETHER(0.98), 이어서 SHINee·NCT127·EXO·ENHYPEN 월드투어 — 전부 실제로 화제성 있는 대형
콘서트라 점수가 상식과 일치함. (직전 조사에서 추정한 84건과 77건의 차이는, 84건은 KOPIS
상세 812건 전체 기준이고 77건은 KSPO와 실제 매칭된 651건 기준이라 생기는 자연스러운 차이.)
**lessons.md 반영**: 해당 없음.

## [2026-11-12] 추천 3종 + 콜드스타트 (recommend.py, scoring.py)

**검증 대상**: `taste_recommend`, `condition_recommend`, `similar_performances`,
`coldstart_recommend` 4개 함수.
**검증 방법**: `today=2026-11-12`로 고정해 각각 1회씩 호출 → 결과가 이상해 보이는 2곳을
직접 디버깅.
**결과**: 통과, 버그 없음(처음엔 버그로 보였던 2가지가 전부 정상 동작으로 확인됨):
  1. `similar_performances`에서 같은 가수(박지현)의 다른 공연 5건이 결과에 전혀 안 나와서
     의심했는데, 디버깅해보니 그 5건 전부 `today` 기준으로 **이미 끝난 공연**이었음
     (`is_ended`가 올바르게 제외한 것) — 유일하게 안 끝난 같은 가수 공연은 질의 자체였음.
  2. `condition_recommend`(12월·가족·예산 10만원)가 1건만 반환해서 필터가 과한가 의심했는데,
     단계별로 뜯어보니 12월 예정 공연 7건 → 가족 조건 통과 7건 → 예산(10만원) 통과 1건으로,
     나머지 6건이 실제로 10만원을 넘는 가격이라 걸러진 것 — 필터 로직 정상.
  3. `taste_recommend`(콘서트)·`coldstart_recommend`(이번 주말)도 결과가 상식과 일치
     (인기도 높은 공연이 상위, 장르 일치, 종료 공연 없음).
**lessons.md 반영**: 해당 없음.

## [2026-11-12] "스포츠/기타" 장르 가짜 군집 — 사용자 지적으로 발견·수정

**검증 대상**: "미분류를 제외한 메인 후보 중 취향과 안 맞는 군집이 있는지" 사용자 요청으로
`genre == "스포츠/기타"` 버킷(19건)을 직접 조사.
**검증 방법**: `performances_matched.json`의 원본 KOPIS 세부 장르(`genrenm`)로 역추적 →
서커스/마술(7)·연극(6)·대중무용(4)·전통무용(2)이 섞여 있음을 확인 → 최현우(마술)와
로미오와 줄리엣(연극) 간 코사인 유사도를 계산해 실제로 장르 일치만으로 0.5가 나오는지 확인.
**결과**: **문제 확인 → 수정함**. "스포츠/기타"는 나머지 5개 장르에 안 걸리는 걸 모은
잡동사니 버킷인데, 장르 원-핫이 "같은 기타"라는 이유만으로 완전히 무관한 두 공연에
0.5 유사도를 부여하고 있었음(반면 장르가 다르면 0.0). `vectorize.py`에
`NO_GENRE_SIGNAL = {"스포츠/기타"}`를 추가해 이 장르는 원-핫 신호를 0으로 만들고 텍스트
유사도에만 맡기도록 수정. 재실행 후 확인:
  - 마술 vs 연극: 0.5 → **0.0**
  - 마술 vs 댄스: 0.5 → **0.033**
  - 같은 사람(최현우)의 다른 공연 두 건: **0.49**(이제 순수 텍스트 신호, 가짜 장르 신호 아님)
  - 영향 없어야 할 콘서트-콘서트(무작위): 0.500 → 0.528로 거의 그대로(정상 범위 내 재계산
    차이) — 수정이 "스포츠/기타"에만 국한됐음을 확인.
  - `recommend.py` 4개 함수 재실행해 여전히 정상 동작함을 스모크 테스트로 확인.
**lessons.md 반영**: 반영함 — 아래 [2026-11-12] "장르 원-핫 설계 시 '기타' 버킷 주의" 참고.

## [2026-11-12] top_k 상한(MAX_TOP_K)과 취향 추천 결과 정렬

**검증 대상**: `scoring.MAX_TOP_K` clamp(사용자 지적 — 데이터가 쌓이면 `top_k`에 상한이
없어 호출하는 쪽이 큰 값을 넘기면 결과가 무한정 커질 수 있음), `taste_recommend`가 MMR로
뽑은 뒤에도 점수 내림차순으로 반환하는지.
**검증 방법**: `top_k=9999`로 호출해 반환 건수 확인, `taste_recommend` 결과 5건의
`final_score`를 직접 재계산해 내림차순인지 확인.
**결과**: 통과. `top_k=9999` → 13건 반환(전체 후보가 그만큼뿐이라 20 상한보다 적게 나옴,
상한 자체는 정상 동작). 취향 추천 5건 점수: 0.8136 > 0.7283 > 0.7123 > 0.6469 > 0.6163으로
정확히 내림차순. (MMR은 "어떤 top_k개를 뽑을지"만 다양성 고려로 정하고, 뽑힌 뒤에는
`sorted(selected, key=lambda i: -relevance[i])`로 다시 정렬하게 바꿈 — MMR 선택 순서 그대로
보여주면 관련성 낮은 게 먼저 나올 수 있었음.)
**lessons.md 반영**: 해당 없음.

## [2026-11-12] 오프라인 평가 (evaluate.py) — Precision@5가 장르 5/6에서 0

**검증 대상**: `recommender/evaluate.py` — 가상 프로필 30개(장르 6종×5명)로 Precision@5,
Coverage, Diversity 계산.
**검증 방법**: 실행 → Precision@5가 콘서트만 1.0이고 나머지는 거의 0인 게 코드 버그인지
데이터 문제인지 직접 디버깅(`_eligible_mask`로 장르별 "안 끝난 공연" 개수 직접 집계).
**결과**: **코드 버그 아님 — 데이터 커버리지 문제로 확인.** 매칭된 공연 651건 중
2026-11-12 기준 안 끝난 공연이 13건뿐이고(콘서트 12, 스포츠/기타 1), 뮤지컬·클래식·
페스티벌·어린이는 안 끝난 공연이 **0건**이라 애초에 추천할 후보 자체가 없었음.
`taste_recommend`는 그 상황에서 차선책(콘서트)을 정상적으로 보여준 것. 워크플로우 문서
7장 리스크 1번이 실측으로 확인된 사례. 상세는 `recommender/REPORT.md` 참고.
**lessons.md 반영**: 해당 없음 — 내 실수가 아니라 실제 데이터 상태를 발견한 것.

## [2026-11-12] 재수집 중 데이터 손상 사고 — 발견·복구·안전장치 추가

**검증 대상**: 사용자 요청으로 `pipeline/collection` 재수집(1번 옵션) + 매칭 알고리즘
프로모션 문구 수정을 진행하는 과정.
**검증 방법**: 재수집 실행 → `run_all.py` 로그에서 "KOPIS 공연 목록·상세 FAILED" 확인 →
`data/raw/kopis/` 파일별 건수·수정시각 직접 대조.
**결과**: **사고 발생 → 원인 파악 → 안전장치 추가 → 복구 완료.**
  1. `boxoffice.json`이 600건 → 빈 배열(`[]`)로 덮어써짐. `collect_kopis_boxoffice.py`가
     이번 달 전부 실패했는데도 빈 결과를 그냥 저장해버린 것(원인: 그 시점 KOPIS 응답 불안정).
  2. (앞선 수정 발견 후) `collect_kopis.py`에도 같은 패턴의 버그가 있어서
     `performance_detail.json`이 812건 → 565건으로 **247건 손상**(실패 9건 → 259건으로
     급증한 상태를 그대로 저장).
  3. 두 스크립트 모두 수정: `collect_kopis_boxoffice.py`는 전부 실패 시 저장 안 함,
     `collect_kopis.py`는 mt20id별로 기존 성공 데이터와 merge(이번에 실패해도 예전에
     성공한 데이터는 보존). 다른 4개 수집 스크립트는 전부 "단일 호출 성공/실패" 구조라
     같은 위험이 없음을 확인(해당 없음).
  4. 복구 재실행: KOPIS가 안정화된 상태에서 `collect_kopis.py` 재실행 → 812건 완전 복구
     (786건 신규 성공 + 26건 기존 데이터로 보존, 완전 실패 12건). `collect_kopis_boxoffice.py`
     재실행 → 600건 완전 복구(12개월 전부 성공).
**lessons.md 반영**: 반영함 — [2026-11-12] "수집 스크립트는 '부분 실패'를 '성공'처럼
저장하면 안 된다".

## [2026-11-12] 프로모션 문구 매칭 수정 + 재수집 반영 후 재검증

**검증 대상**: `normalize_title()`의 `%` 괄호 제거 수정이 실제로 "백 번째 리뷰"를
매칭시키는지, 재수집한 데이터로 오프라인 평가(Precision@5)가 나아지는지.
**검증 방법**: `pipeline/preprocessing` 전체 재실행 → `performances_matched.json`에서
"백 번째 리뷰" 직접 조회 → `vectorize.py`·`evaluate.py` 재실행해 수치 비교.
**결과**: 절반만 성공.
  1. 매칭 자체는 성공: `match_method: fuzzy(83)`로 KOPIS와 연결됨(장르 연극, 출연진 등
     콘텐츠 확보). 사전 계산한 83.3과 일치.
  2. **그런데 추천에는 여전히 안 잡힘** — `performances.csv`의 `period`는 KSPO 쪽 기간
     (20260404~20260830)을 쓰는데, 같은 공연의 KOPIS 쪽 기간은 2026.12.27까지로 더 길다
     (공연이 연장된 것으로 보임). `is_ended()`가 KSPO 기간 기준으로 "이미 끝남"으로 판단해
     여전히 추천 후보에서 빠짐.
  3. 전체 매칭 건수는 651→646으로 오히려 소폭 감소(재수집에서 실패한 id가 이전과 다른
     12건이라 생기는 자연스러운 데이터 변동, 매칭 수정과는 무관).
  4. `evaluate.py` Precision@5: **0.200으로 동일**, 변화 없음. 이번 수정 하나로는 평가
     지표가 개선되지 않음을 확인.
**lessons.md 반영**: 해당 없음(새로운 실수 패턴이 아니라, 두 소스의 기간이 다를 수
있다는 걸 알게 된 것 — `tasks/todo.md`에 다음 작업으로 반영).

## [2026-11-12] 콘텐츠 우선 모드 전환 (series.py, CONTENT_FIRST_MODE) + 재평가

**검증 대상**: 사용자 요청으로 추천 방향을 전환 — (1) 반복 시리즈 다음 회차 예측
(`series.py`), (2) 취향 추천/비슷한 공연은 날짜 무관하게 콘텐츠 기준으로 추천하고
상태(확정 예정/매년 반복 예상/과거 유사 공연) 표시, (3) `scoring.CONTENT_FIRST_MODE`
스위치로 원래 날짜 기반 설계로 되돌릴 수 있게 구성.
**검증 방법**: `evaluate.py` 재실행 → Precision@5 변화 확인 → 뮤지컬·페스티벌 프로필의
실제 결과를 직접 열어 `status` 라벨이 맞게 붙는지 확인 → 반복 시리즈 예측 행 5건을
직접 조회해 예측 날짜가 합리적인지 확인.
**결과**: 통과, 큰 개선 확인.
  - Precision@5: **0.200 → 0.800**(뮤지컬 1.0, 어린이 1.0, 페스티벌 1.0, 클래식 0.8,
    콘서트 1.0). 스포츠/기타만 0.0으로 떨어졌는데, 이건 버그가 아니라 이전에 고친
    `NO_GENRE_SIGNAL`(스포츠/기타는 잡동사니 버킷이라 장르 신호를 안 줌) 때문에
    "스포츠/기타를 좋아한다"는 프로필 자체가 어떤 후보와도 장르로 구분이 안 되는
    당연한 결과.
  - 상태 라벨 정상 동작: 150건 중 45건 "확정 예정", 105건 "과거 유사 공연". 반복 시리즈
    예측 5건(그랜드민트페스티벌·서울파크뮤직페스티벌·뷰티풀민트라이프·성시경 관련 2건,
    전부 다음 해로 투영된 합리적인 날짜)은 이번 30개 프로필에서는 top5에 하나도 안 들었음
    — 실제 확정/과거 후보들이 인기도·날짜근접도에서 더 높은 점수를 받았기 때문(예측 행은
    popularity_score=0, 날짜가 대개 30일 근접도 범위 밖). 메커니즘 자체는 정상이고, 그냥
    이번 스냅샷에서는 다른 후보가 더 강했던 것 — 버그 아님.
  - Coverage 분모가 13 → 719로 커짐(콘텐츠 우선 모드라 과거 공연도 전부 후보가 됨) —
    예상된 변화, 지표 해석이 달라져야 함(상세는 `recommender/REPORT.md` 참고).
**lessons.md 반영**: 해당 없음(설계 전환에 따른 예상된 결과, 반복 실수 아님).

## [2026-11-12] 장르 선택 간 결과 중복 — 사용자 지적으로 발견·수정

**검증 대상**: 사용자 요청으로 6개 장르 전부를 선택했을 때 서로 다른 추천이 나오는지,
같은 리스트 안에 중복이 있는지 점검.
**검증 방법**: `taste_recommend`를 6개 장르 각각에 대해 1회씩 호출해 결과 제목 목록을
직접 대조.
**결과**: **버그 발견 → 수정함**. "스포츠/기타"를 선택하면 "콘서트"를 선택했을 때와
**완전히 동일한 5건**이 나왔다. 원인: `vectorize.py`가 "스포츠/기타"의 장르 원-핫
신호를 0으로 죽여놨는데(이전 수정, 잡동사니 버킷이라서), `build_profile_vector`는
그 사실을 모른 채 사용자가 "스포츠/기타"를 선택하면 여전히 프로필의 그 칸에 1을
넣고 있었다 — 그러면 모든 공연과의 유사도가 똑같이 0이 돼서, 순위가 인기도만으로
매겨지고 그게 우연히 콘서트 랭킹과 같아진 것. 사용자가 취향을 골랐는데 시스템은
조용히 무시한 셈.
수정: `build_profile_vector`가 `vectorize.NO_GENRE_SIGNAL`에 속한 장르는 원-핫에
반영하지 않도록 변경 — 그 결과 "스포츠/기타"만 선택하면 프로필이 완전한 영벡터가 돼서
`taste_recommend`의 기존 콜드스타트 폴백("취향 정보 없음 — 콜드스타트로 대체")이 정상
발동한다. 재테스트: 나머지 5개 장르는 서로 전부 다른 고유 리스트, 각 리스트 내 중복
없음을 확인.
**lessons.md 반영**: 반영함 — [2026-11-12] "신호를 죽인 특성은 프로필/쿼리 쪽에서도
똑같이 죽여야 한다".

## [2026-11-12] 매칭 공연 기간: KOPIS 우선으로 전환 (1번·2번 비교 후 결정)

**검증 대상**: 매칭된 공연의 `period`를 KSPO 대신 KOPIS 기간으로 쓰도록 바꾼 결정
(옵션 1: KOPIS 우선, 옵션 2: 둘 중 늦은 종료일) — 어느 쪽이 나은지 비교.
**검증 방법**: 매칭된 646건 전체에서 KSPO·KOPIS 기간을 직접 비교하는 스크립트를 짜서
실행 → 두 옵션이 실제로 다른 결과를 내는지 통계로 확인 → 옵션 1을 구현(`match_performances.py`
에 `kopis_prfpdfrom/prfpdto` 추가, `normalize_and_clean.py`에 `resolve_period()` 추가) →
재실행 → "백 번째 리뷰" 상태가 "확정 예정"으로 바뀌는지, 오프라인 평가 수치가 나아지는지 확인.
**결과**: 통과.
  - 비교 결과: 646건 중 23건(3.6%)만 날짜가 다름. **종료일은 KOPIS가 KSPO보다 짧은
    경우가 0건** — 옵션 1(KOPIS 우선)과 옵션 2(늦은 종료일)가 종료일 기준으로는 완전히
    동일한 결과. 시작일 차이는 최대 ±2일(노이즈 수준). → 더 단순한 옵션 1로 결정.
  - 적용 후: "백 번째 리뷰" `status`가 "과거 유사 공연"→**"확정 예정"**으로 정상화.
  - `evaluate.py` 재실행: Precision@5 0.800→**0.855**, 스포츠/기타 0.0→**0.333**(3건
    반환, 그중 1건이 "백 번째 리뷰" 자체). 다른 장르는 영향 없음(기대대로 KOPIS/KSPO
    날짜가 일치하는 623건은 그대로).
**lessons.md 반영**: 해당 없음(사용자가 명시적으로 "둘 다 테스트해보고 결정"을 요청한
정상적인 의사결정 과정).

## [2026-11-12] 백엔드(backend/) 구현 — 엔드포인트 8개 테스트

**검증 대상**: `backend/main.py`의 API 8개(워크플로우 문서 4.5장 7개 + `GET /favorites`
추가분) — `GET /performances`, `GET /performances/{id}`, `POST /recommend/onboarding`,
`GET /recommend/me`, `GET /recommend/similar/{id}`, `GET /parking/forecast`,
`POST /favorites`, `GET /favorites`.
**검증 방법**: 1차로 `uvicorn`을 백그라운드로 띄워 curl로 테스트하려 했으나, 이 로컬
샌드박스 환경에서 **포트를 열어 리스닝하는 프로세스를 두면 세션이 자꾸 강제 종료됨**
(exit 144, `pkill`로 정리하려 해도 동일 증상)을 반복 확인 — 원인은 확정 못 했지만
uvicorn/http.server처럼 포트를 bind하는 프로세스가 백그라운드에 남아있을 때마다
재현됨. 실제 배포 환경(Render 등)과 무관한 이 샌드박스만의 제약으로 판단하고,
`fastapi.testclient.TestClient`(소켓 없이 ASGI 앱을 직접 호출하는 FastAPI 표준 테스트
방식)로 전환해 재시도.
**결과**: 통과. 8개 엔드포인트 전부 의도대로 동작:
  - `GET /performances?genre=콘서트` → 200, 541건
  - `GET /performances/{id}` → 200, 상세 정확
  - `POST /recommend/onboarding`(뮤지컬) → 200, 뮤지컬 5건 반환
  - `GET /recommend/me` → 200, 결과마다 `status` 라벨("과거 유사 공연" 등) 정상 부착
  - `GET /recommend/similar/{id}` → 200, 비슷한 공연 5건
  - `GET /parking/forecast` → **501**(수집 블로커를 명시한 메시지, 의도대로)
  - `POST /favorites` 중복 호출 → 둘 다 200(멱등, 에러 없이 조용히 무시)
  - `GET /favorites` → 200, 찜한 공연만 정확히 반환
  - 엣지 케이스: 존재하지 않는 id → 404, "스포츠/기타"(신호 없는 장르) 온보딩 →
    콜드스타트로 정상 대체되고 "확정 예정" 라벨이 붙은 3건 반환(이전에 고친
    `NO_GENRE_SIGNAL` 버그가 API 레벨에서도 정상 작동함을 재확인).
  - 과정에서 import 순서 버그 1건 발견·수정: `main.py`가 `performances_store`(여기서
    `recommender/`를 `sys.path`에 추가함)보다 먼저 `import recommend`를 해서
    `ModuleNotFoundError`가 났음 — import 순서를 바꿔 해결.
**lessons.md 반영**: 해당 없음(import 순서는 작성 중 바로 잡은 실수, 환경 이슈는 별도
기록 안 함 — README.md에 테스트 방법으로만 남김).

## [2026-11-12] GET /favorites 제거(범위 축소) 후 재검증

**검증 대상**: 사용자가 "찜 페이지는 빼도 될 것 같아, 기존 것만 먼저" 요청 → 문서 7개
API 밖이었던 `GET /favorites?session_id=`를 제거한 뒤 나머지 7개가 그대로 동작하는지.
**검증 방법**: `GET /favorites` 라우트 제거 → `TestClient`로 7개 전부 재호출 +
`GET /favorites`가 실제로 없어졌는지 확인.
**결과**: 통과. 7개 전부 정상(200/501), `GET /favorites`는 405(Method Not Allowed —
경로 자체는 `POST /favorites`로만 남아서 GET은 안 받음)로 확실히 제거됨을 확인.
`Favorite` 테이블·`POST /favorites`는 그대로 남겨둠(나중에 조회만 추가하면 복원 가능).
**lessons.md 반영**: 해당 없음.

## [2026-11-12] 예매처 링크(ticket_links) 추가

**검증 대상**: 프론트엔드 설계 중 발견한 누락 — `performances.csv`에 예매처 링크가 없었음.
**검증 방법**: `normalize_and_clean.py`에 `ticket_links`(JSON 문자열) 컬럼 추가 →
파이프라인 재실행 → "백 번째 리뷰" 등 매칭된 공연의 실제 링크 확인 → 백엔드
`GET /performances/{id}`가 그 값을 그대로 내려주는지 확인.
**결과**: 통과. 매칭된 646건 전부 `ticket_links`가 채워짐(미분류/unmatched는 `"[]"`).
예: "백 번째 리뷰" → 네이버N예약·놀유니버스·카카오톡예약하기 3개 링크. 백엔드도 그대로
JSON 문자열로 내려줌(프론트에서 `JSON.parse` 필요).
**lessons.md 반영**: 해당 없음.

## [2026-11-12] 프론트엔드(frontend/) 구현 — 빌드·연동 테스트, "포트 강제종료" 추정 정정

**검증 대상**: `frontend/` 전체(온보딩·홈·상세·마이페이지 4화면), `ticket_links`/
공통 `status` 백엔드 보강, 그리고 전에 "로컬 샌드박스에서 포트를 열면 세션이 강제
종료된다"고 결론 내렸던 추정.
**검증 방법**: (1) `npm run build`·`npm run lint`, (2) `lsof -ti:PORT | xargs kill`로
포트를 안전하게 비우고 백엔드·프론트를 둘 다 백그라운드로 띄운 뒤 `timeout 40 bash -c
'until curl -sf ...'`로 길게 폴링, (3) Playwright로 실제 화면 스크린샷 시도.
**결과**:
  1. 빌드/린트: 처음엔 `useParams()`가 `<Suspense>` 밖에 있어 prerender 에러,
     `react-hooks/set-state-in-effect` 규칙 위반 3건(mypage, page, 상세 페이지의 동기
     `setState`) — 전부 수정 후 통과.
  2. **"포트 바인딩하면 세션이 강제종료된다"는 이전 추정은 틀렸던 것으로 정정**: 이번엔
     백엔드·프론트 둘 다 정상적으로 떠서 응답했다. 원인은 WSL에서 `/mnt/c/...`(윈도우
     드라이브) 경로라 pandas·scikit-learn 등 무거운 import의 콜드 스타트가 느려서(디스크
     I/O 대기, uvicorn 프로세스가 한동안 "Dl"(disk sleep) 상태) — 예전엔 폴링을 짧게
     하고 포기했던 것이 실제 원인. `backend/README.md`·`frontend/README.md` 둘 다 정정.
  3. 홈 화면 HTML을 curl로 직접 확인 — 의도한 섹션(내 추천/이번 주말 공연/날짜·장르로
     찾기)이 전부 정상 렌더링됨.
  4. **스크린샷은 실패**: Playwright 설치(`pip install playwright` + `playwright install
     chromium`)까지는 됐지만, Chromium 실행에 필요한 시스템 라이브러리(`libnspr4.so`)가
     없고 설치하려면 `sudo apt`가 필요한데 이 세션엔 비밀번호 없는 sudo 권한이 없음. 코드
     리뷰(상태별 조건 렌더링 직접 확인)로 대체 — 실제 배지가 눈에 보이는 걸 확인하려면
     사용자가 sudo 권한이 있는 환경에서 `npx playwright install-deps` 실행 필요.
**lessons.md 반영**: 반영함 — 아래 [2026-11-12] "환경 제약을 '불가능'으로 단정하기 전에
타임아웃을 먼저 늘려봐야 한다" 참고.

## [2026-11-12] 실제 브라우저(Playwright) 스크린샷 검증 — 진짜 버그 2건 발견·수정

**검증 대상**: 사용자가 sudo로 `playwright install-deps`를 직접 실행해준 뒤, 실제 Chromium으로
홈/공연 상세 화면을 스크린샷해서 `status` 배지·예매 버튼 노출이 의도대로 되는지 확인.
**검증 방법**: 백엔드·프론트를 `lsof` 기반으로 띄우고 Playwright(`sync_playwright`)로
`nav` → `wait` → `screenshot`. 처음엔 "불러오는 중..."에서 멈춰서, `console`/`pageerror`/
`request` 이벤트를 전부 로깅하며 단계적으로 원인을 좁혀나감.
**결과**: **TestClient·curl로는 못 잡는 버그 2건을 실제 브라우저 테스트로 발견·수정**.
  1. **CORS 미설정**: 백엔드가 요청을 200으로 정상 처리하는데도, 브라우저가
     `Access-Control-Allow-Origin` 헤더가 없다는 이유로 응답을 막아 `fetch()`가
     `TypeError: Failed to fetch`로 거부됨. `main.py`에 `CORSMiddleware` 추가로 해결.
     **`TestClient`는 CORS를 전혀 검사하지 않아서 기존 백엔드 테스트로는 이 버그를 못
     잡았음** — 실제 브라우저로 때려봐야만 드러나는 종류의 버그였음.
  2. **Next.js 16의 `allowedDevOrigins` 기본 차단**: `127.0.0.1`로 접근하면 dev 리소스
     (HMR, JS 청크)가 보안상 기본 차단돼서, 페이지 뼈대(SSR)는 뜨는데 클라이언트
     `useEffect`가 아예 실행 안 됨(겉보기엔 "로딩 중"에 영원히 멈춘 것처럼 보임).
     `next.config.ts`에 `allowedDevOrigins: ["127.0.0.1", "localhost"]` 추가로 해결.
     최소 재현 페이지(`app/debug/page.tsx`, 테스트 후 삭제)로 `useEffect` 자체가
     실행되는지부터 격리해서 확인하는 방식으로 원인을 좁혔음.
  3. **메타 발견**: 이 두 버그를 찾는 과정에서, `lsof -ti:PORT | xargs kill`로 "재시작"
     했다고 생각한 게 실제로는 Next.js의 "다른 dev 서버가 이미 실행 중" 로그 메시지를
     못 보고 지나쳐서 **오래된 프로세스가 계속 응답하고 있었음**을 발견 — PID로 직접
     kill해야 확실하게 재시작됨.
  4. 수정 후 스크린샷으로 최종 확인: 홈 화면(내 추천·이번 주말 공연에 실제 데이터+배지),
     확정 예정 공연(초록 배지+예매 버튼+예매처 최종확인 안내), 과거 공연(회색 배지,
     예매 버튼 없음) 전부 의도대로 렌더링됨.
**lessons.md 반영**: 반영함 — [2026-11-12] "API 테스트가 통과해도 실제 브라우저로
한 번은 때려봐야 한다"와 "서버 로그의 경고 메시지를 끝까지 읽어야 한다" 참고.

## [2026-11-12] 추가 기능 요청 3건(추천 통합·로그인/마이페이지·과거 공연 제외) 검증

실제 화면을 써본 뒤 나온 요청 3건(`tasks/todo.md` "추가 기능 요청" 참고)을 구현하고
아래 방법으로 확인:

1. **백엔드 로직(TestClient, `with TestClient(app) as c:` — lifespan 이벤트가 돌아야
   `init_db()`가 호출돼 `users` 테이블이 생김, 이걸 빼먹어서 "no such table: users"로
   한 번 실패했다가 고쳐서 재확인)**:
   - `GET /performances`(날짜 없음) 결과 21건 전부 `status != "과거 유사 공연 — 참고용"`
     확인 → 과거 공연 제외 정상.
   - `GET /performances/{id}`로 과거 공연(`id=6` 등) 단건 조회는 여전히 200 반환 →
     의도대로 단건 조회는 안 막힘.
   - `POST /auth/signup` 성공(200, `session_id="user:1"`) → 같은 이메일 재가입 409 →
     틀린 비밀번호 로그인 401 → 맞는 비밀번호 로그인 200 확인.
   - 익명 `session_id`로 찜 1건 추가 → 그 익명 세션으로 가입 → `GET /favorites?session_id=`
     조회 시 찜한 1건이 새 `user:{id}` 세션으로 이전돼 보임 확인(`_migrate_anonymous_session`).
2. **빌드/린트**: `npm run build`·`npm run lint` 둘 다 통과. 라우트 `/`·`/recommend`·
   `/login`·`/mypage`·`/onboarding`·`/performances/[id]` 전부 정상 생성 확인.
3. **실제 Chromium(Playwright) 스크린샷** — 백엔드·프론트 둘 다 코드 변경 반영한
   완전히 새 프로세스로 재기동 후:
   - `/`(홈): "올림픽공원 소식" 준비 중 안내 + "공연 추천 보러 가기" 버튼으로 교체됨.
   - `/recommend`: "내 추천"·"이번 주말 공연" 분리 없이 "추천 공연" 섹션 하나로 통합됨.
   - 날짜 미선택 + 장르 "전체"로 검색 → 결과 전부 "확정 예정"·"매년 반복 예상" 배지만
     나오고 "과거 유사 공연" 문구 0건(정규식 카운트로 확인) — 요청 3번 해결 확인.
   - 로그아웃 상태 `/mypage`: "로그인하면 내 정보와 활동 내역을 볼 수 있어요" 안내 +
     로그인 버튼만 보임.
   - `/login`에서 회원가입(`tester@example.com`) → `/mypage`로 자동 이동 → "내 정보"
     (이메일)·"활동 내역 — 찜한 공연"(서버 `GET /favorites` 기반) 섹션이 보임 확인.
4. 테스트로 만든 `tester@example.com` 계정·찜 데이터는 확인 후 `backend/app.db`를
   지우고 백엔드를 재기동해 정리함(실제 사용자가 볼 상태를 깨끗하게 유지).

**결론**: 치명 버그 없음. 세 요청 모두 의도대로 동작.

## [2026-11-12] "매년 반복 예상" 예측 제거 검증

`scoring.INCLUDE_PREDICTED_SERIES = False` 추가(`CONTENT_FIRST_MODE`와 독립 스위치) +
`recommend.load_data()`에서 조건부로 바꿔서 확인:

- TestClient: `GET /performances`(날짜·장르 없음) 응답 전체 status가 `{"확정 예정"}`
  뿐임(과거는 이미 전 단계에서 제외, 이제 예측도 없음). `GET /recommend/me` 콜드스타트
  결과도 전부 "확정 예정". 6개 장르 전부 `POST /recommend/onboarding`으로 돌려서
  "매년 반복 예상"이 하나도 안 나옴을 확인 — 대신 콘서트/스포츠 외 장르는 "과거 유사
  공연 — 참고용"이 그 자리를 채움(뮤지컬 5/5, 페스티벌 5/5, 어린이 5/5, 클래식 4/5가
  과거 참고용). 빈 결과는 없음.
- 실제 Chromium: `/recommend`에서 "날짜·장르로 찾기"를 장르 전체로 돌려도 본문에
  "매년 반복 예상" 문자열이 0건(`"매년 반복 예상" in body_text` → `False`).

**결론**: 요청대로 반복 시리즈 예측이 완전히 안 보임. 트레이드오프(일부 장르가 과거
참고용 위주로 보임)는 `tasks/todo.md` "추가 기능 요청" 4번에 기록.

## [2026-11-12] 올림픽공원 소식 게시판 API 테스트 → 롤백 검증

실제 서비스키로 `https://api.kcisa.kr/openapi/service/rest/meta/KSCkrep`를
`serviceKey`·`numOfRows`·`pageNo` 파라미터로 호출(curl):

- `resultCode: 0000`, `totalCount: 1080` — 호출 자체는 정상.
- 100건 샘플에서 `alternativeTitle`·`subjectCategory`·`subjectKeyword`·`extent`·
  `spatialCoverage`·`temporal`·`person`·`language`·`sourceTitle`·`rights`·
  `copyrightOthers`·`uci`·`contributor` **전부 0건 채워짐**(실제 값 있는 필드는
  `title`·`creator`·`regDate`·`collectionDb`·`description`뿐).
- 서로 다른 페이지(1/2/50/100/360)에서 `regDate`를 비교 → 같은 페이지 안의 서로 다른
  연도 내용(2017년 행사 vs 2024년 행사)이 똑같은 초 단위 `regDate`를 가짐 → 실제 보도
  날짜가 아니라 배치 수집 시각으로 확정.
- 사용자 지시대로 title+description(HTML 태그 제거 후)에서 정규식(`YYYY-MM-DD`,
  `YYYY년 M월 D일`, `YYYY년 M월`)으로 날짜 추출 시도 → 100건 중 **2건만 매칭**, 그마저
  "2016년 9월 23일 열린다"(행사 날짜 언급) 같은 본문 맥락이라 보도 날짜로 쓸 수 없음 →
  날짜 신뢰 불가로 최종 확인.
- 기능 롤백 후 `npm run build`·`npm run lint` 통과 확인(라우트 목록에서 `/recommend`
  제거, `/`·`/login`·`/mypage`·`/onboarding`·`/performances/[id]`만 남음 — 최초 빌드 때
  `.next` 캐시에 남은 옛 라우트 타입 선언 때문에 `TS2307`이 났었는데 캐시 삭제 후
  재빌드해서 해결). 서비스키는 어떤 파일에도 커밋하지 않음.

**결론**: API 자체는 유효하나 날짜 신뢰성 문제로 기능 전체를 빼기로 결정(치명 버그 아님,
설계 판단).

## [2026-11-12] 홈 화면 달력 뷰("날짜로 찾기") 검증

`npm run build`·`npm run lint` 통과(처음엔 장르 변경 effect에서 `setCalendarLoading(true)`
동기 호출로 `react-hooks/set-state-in-effect` 걸림 → 제거해서 해결). 실제 Chromium으로:

- 월 화면 진입 시 오늘(11/12)이 강조 표시되고, 공연이 있는 날짜엔 초록 점이 찍힘(여러
  날에 걸친 "［얼리버드 50%］ 연극 〈백 번째 리뷰〉"(4/4~12/27)가 11월 전체 날짜에
  점으로 표시되는 것까지 확인 — 기간 전체 반영 로직 정상).
- 1일 클릭 → "11월 1일 공연 1건" + 해당 공연 카드가 달력 아래에 나타남.
- 장르를 "뮤지컬"로 바꾸니 점이 전부 사라지고(현재 예정 공연 중 뮤지컬 없음, 데이터와
  일치) 선택돼 있던 1일의 "공연 0건"으로 즉시 갱신됨.
- 다음 달(12월)로 이동해도 장르 필터(뮤지컬)가 유지된 채 점 없음 유지 확인.

**결론**: 치명 버그 없음, 설계대로 동작.

## [2026-11-12] "미분류" 장르 분류 버그 수정 검증

사용자가 "정승환 콘서트"가 미분류로 뜨는 걸 발견 → `classify_genre()` 수정 + 방어적
필터 추가 후:

- `normalize_and_clean.py` 1차 수정(콘서트 키워드를 매칭 공연에도 적용) → 장르 분포
  확인 중 **클래식 18→9, 뮤지컬 29→26, 스포츠/기타 20→19로 줄어드는 회귀 발견** —
  KOPIS가 이미 정확히 분류해둔 매칭 공연을 제목 키워드가 덮어쓴 것. 매칭 안 된 행
  전용 폴백으로 범위를 좁혀 재수정.
- 2차 수정 후 재실행: 뮤지컬 29·클래식 18·스포츠/기타 20 전부 원래 건수로 복구
  확인(회귀 없음). 콘서트 538→1013, 미분류 1247→772.
- `recommender/vectorize.py`(벡터 재생성) → `recommender/evaluate.py` →
  **Precision@5 0.855**(수정 전과 동일, 회귀 없음).
- 백엔드 재기동 후 `GET /performances` curl 확인: 응답 16건 중 "미분류" 장르 0건,
  "2026 정승환 10주년 콘서트" genre가 "콘서트"로 정확히 나옴.
- 실제 Chromium으로 홈 화면(달력) 전체 텍스트에서 "미분류" 문자열 0건 확인(범례에
  "콘서트"·"스포츠/기타"만 남음).

**결론**: 치명 버그였던 건 아니지만(이미 UI에서 드롭다운에 없는 값이 노출되는
일관성 문제), 데이터 품질 버그(일반 규칙 누락, 414→475건 영향)와 UI 방어 코드 둘 다
수정 완료.

## [2026-11-12] 장르 추천 폐기 + 찜하기·로그인 삭제 검증

1. **장르별 추천이 "과거 제외"만 적용하면 엉뚱한 장르로 채워지는 버그 실측**:
   `taste_recommend`에서 historical을 빼고 6개 장르로 테스트하니 뮤지컬·클래식·
   페스티벌·어린이 4개 장르가 **완전히 동일한 콘서트 5개**를 반환(해당 장르의 실제
   예정 공연이 0건이라 인기도 기반으로 조용히 대체됨). → 사용자와 상의해 장르 선택
   UI 자체를 없애고 `bookable_top()`(장르 무관 상위 3개)으로 설계 변경.
2. `bookable_top()` 단독 테스트: 콘서트 3건, 인기도 0.98/0.94/0.82 순으로 정상 반환.
3. TestClient로 삭제 대상 5개 엔드포인트(`/recommend/onboarding`, `POST&GET
   /favorites`, `/auth/signup`, `/auth/login`) 전부 404 확인, 남은 엔드포인트
   (`/performances`, `/recommend/me`, `/recommend/similar/{id}`) 정상 동작 확인.
4. `npm run build`·`npm run lint` 통과 — 라우트가 `/`·`/performances/[id]` 둘만 남음.
5. **실제 브라우저 재검증 중 발견한 버그**: 처음 재시작 후 홈 화면에 빈 목록 + 좌하단
   "1 Issue" 배지가 떠서 콘솔을 보니 `GET /recommend/me`가 CORS 에러로 실패 중이었음
   — 실제 원인은 CORS가 아니라 **세션 훨씬 앞에서 띄워둔 오래된 백엔드 프로세스가
   포트 8000을 계속 쥐고 있어서**, 새로 `nohup` 띄운 "재시작"이 조용히 실패하고 옛
   프로세스가 계속 응답하고 있었던 것(`lsof -ti:8000`으로 실제 PID 확인). 그 옛
   프로세스가 들고 있던 `app.db` 파일 핸들이 그사이 반복된 `rm -f app.db`와 꼬이면서
   `sqlite3.OperationalError: attempt to write a readonly database` → 500 →
   브라우저에는 CORS 에러로 보인 것(TestClient 테스트 때는 매번 새 프로세스였어서
   이 증상이 전혀 안 잡혔음). PID로 직접 `kill -9` 후 재기동해서 해결, 콘솔 에러 0건·
   "예매 가능한 공연" 3건 정상 렌더링 스크린샷으로 확인.

**결론**: 치명 버그 없음(발견한 버그는 전부 배포 전에 잡아서 수정). 최종 상태: 홈
(예매 가능한 공연 3개 + 달력) + 공연 상세 2화면, DB는 `rec_logs`만 남음.

## [2026-11-12] pytest 단위·통합 테스트 작성 및 실행 (4.7장 1·2번)

`.venv`에 `pytest` 설치(`requirements-dev.txt` 신규) 후 3개 디렉터리에 각각 작성·실행:

- `recommender/tests/`(22건): `test_scoring.py`(순수 함수), `test_build_profile_vector.py`
  (장르 중복 버그 회귀), `test_recommend.py`(`bookable_top`·`similar_performances`,
  합성 DataFrame으로 과거/미분류 제외·CONTENT_FIRST_MODE 동작 확인).
- `pipeline/preprocessing/tests/`(6건): `classify_genre()` — "미분류" 버그 수정 때
  실제로 겪은 회귀(매칭 공연의 KOPIS 장르를 제목 키워드가 덮어쓰면 안 됨) 포함.
- `backend/tests/`(15건): `TestClient`로 현재 5개 엔드포인트 정상 동작 + 삭제한
  5개 엔드포인트가 404로 남아있는지.

각 디렉터리에서 독립적으로 실행해 **43건 전부 통과**:
```
cd recommender && ../.venv/bin/python3 -m pytest tests/        # 22 passed
cd pipeline/preprocessing && ../../.venv/bin/python3 -m pytest tests/  # 6 passed
cd backend && ../.venv/bin/python3 -m pytest tests/            # 15 passed
```
루트에서 `pytest .`로 한 번에 돌리지 않는 이유: `recommender/common.py`와
`pipeline/preprocessing/common.py`처럼 서로 다른 디렉터리에 같은 이름의 모듈이 있어서,
한 세션에서 섞어 import하면 모듈 캐싱 충돌 위험이 있음(각 디렉터리는 원래도 독립 실행
전제).

**결론**: 치명 버그 없음(실행 자체가 전부 통과). `backend/main.py`의 `@app.on_event`
deprecation 경고는 FastAPI 자체의 안내일 뿐 테스트 실패는 아니라 지금은 안 고침.

## [2026-11-13] Lighthouse 성능 점검 (4.7장 3번)

프로덕션 빌드(`next build && next start -p 3000`) + Playwright 헤드리스 Chromium
(`CHROME_PATH`)로 홈·공연 상세 2페이지 측정. 발견·수정 내역:

1. **CLS(레이아웃 밀림) 2건 실제로 고침**: 상세 페이지 포스터 `<img>`에 width/height
   없음(0.467→0) + 홈 달력이 로딩 중/후로 그리드 통째가 나타나 밀림(0.328~0.357→0).
   둘 다 "로딩 중엔 빈 틀을 미리 그려서 자리를 잡아둔다" 방식으로 해결.
2. **접근성 2건 고침**: 장르 `<select>` 라벨 없음(`aria-label` 추가) + 달력 주말
   색상 대비 미달(`text-rose-500`→`-600`, `text-sky-500`→`-700`, 둘 다 WCAG AA
   4.5:1 통과하도록 실제 명도 대비를 계산해서 선택). 홈 Accessibility 89→100.
3. **발견했지만 보류**: 상세 페이지의 `text-gray-400/500`류 보조 텍스트가 여러
   컴포넌트(카드 날짜/장소, 장르 태그, 주차 예보 안내)에서 WCAG AA 미달(2.19~4.36)
   — 컴포넌트 하나가 아니라 앱 전체 보조 텍스트 색상 토큰 문제라 디자인 다듬기
   단계로 넘김(지금 임의로 전체 색상 체계를 바꾸지 않음).
4. **환경 이슈**: Lighthouse(`npx`)가 Chrome 프로필을 `C:\Users\...` 형태의 리터럴
   파일명으로 `frontend/` 안에 생성해버려서 `next build`가 실패하는 사고가 있었음
   → `--user-data-dir`을 스크래치패드로 명시하고 실행 위치도 옮겨서 해결, 잔재
   삭제함.
5. **재발 버그**: 서버 재시작 중 이전 PID가 포트를 계속 쥐고 있어서 "재시작"이
   조용히 실패한 경우가 2번 더 있었음(`app.db` 핸들 꼬임 500, `next start` 포트
   충돌) — 매번 `ss -ltnp`로 실제 PID 확인 후 `kill -9`로 해결(기존 lessons.md
   항목과 동일 패턴 재확인).

**최종 점수(로컬 HTTP, WSL 환경 — 실제 배포 시 더 나아질 수 있음)**:

| 페이지 | Performance | Accessibility | Best Practices | SEO |
| --- | --- | --- | --- | --- |
| 홈 | 86 | 100 | 77 | 100 |
| 상세 | 79 | 96 | 77 | 100 |

Best Practices 77은 로컬 HTTP(비-HTTPS) 테스트 특성 + KOPIS 포스터가 `http://`라
뜨는 쿠키 경고 때문 — 둘 다 배포 환경/외부 데이터 제약이라 지금 코드로 못 고침.

**결론**: 치명 버그 없음. CLS는 완전히 해결(0), 접근성은 홈 100/상세 96. 성능 점수는
WSL 로컬 환경 I/O 지연 영향을 받으므로 절대값보다 "회귀 없음"에 의미를 둔다.

## [2026-11-14] 8단계 배포 — A단계(로컬 준비) 검증

대상: `frontend/app/layout.tsx`(출처 footer), `backend/main.py`(`ALLOWED_ORIGIN` CORS),
`backend/README.md`·루트 `README.md`(배포 설정 문서화). 상세 설계는 `tasks/todo.md`
"8단계: 배포 → 본작업 실행 계획 → A" 참고.

1. **프론트 빌드·린트**: `npm run build` 성공(라우트 `/`·`/_not-found`·
   `/performances/[id]` 전부 정상 생성), `npm run lint` 경고·에러 0건.
2. **CORS 환경변수 동작 확인**: `ALLOWED_ORIGIN=https://example-demo.vercel.app`로
   설정 후 `TestClient`로 `GET /performances` 호출 → 200, `main._allowed_origin`이
   설정한 값으로 반영됨을 확인. 미설정 시 기존 동작(`"*"`)과 동일(코드상 폴백 확인).
3. **백엔드 회귀 테스트**: `../.venv/bin/python3 -m pytest tests/` — 15건 전부 통과
   (기존 `on_event` deprecation 경고는 이번 변경과 무관, 사전부터 있던 것).
4. **접근성 재사용 확인**: footer에 쓴 `text-muted`는 9단계 디자인 다듬기에서 WCAG AA
   (4.5:1) 검증을 이미 거친 토큰이라 별도 대비 재검증 안 함.

**결론**: A단계(로컬 준비) 4개 항목 전부 구현·검증 완료, 회귀 없음. B단계(Render/Vercel
외부 계정 작업)는 사용자가 직접 진행해야 함 — 다음 단계로 안내.

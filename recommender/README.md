# recommender/

추천 점수 계산 모듈 (오프라인 평가 포함). `pipeline/`이 만든 `performances.csv`·임베딩을
입력으로 받아 취향 유사도·인기도·날짜 근접도를 조합한 점수를 계산한다. `backend/`는 이
결과를 미리 계산된 형태로 읽기만 하고, 요청 시점에 임베딩·점수를 다시 계산하지 않는다.

상태: 착수 (4단계). 설계는 워크플로우 문서 4.4장, 6장 참고. 진행 상황은 `tasks/todo.md`
"4단계: 추천 모델" 참고.

- `venue_fallback.py` — 장르 "미분류" 공연은 메인 취향/조건 추천에서 제외하고, 대신
  같은 장소(`venue_normalized`)의 다른 예정 공연을 별도 섹션으로 보여주는 보조 추천.
  `pipeline/preprocessing`이 `performances.csv`에 넣는 `venue_normalized` 컬럼에 의존한다.
  (`tasks/todo.md` "0. 데이터 보강" 참고)
- `vectorize.py` — 공연 벡터(장르 원-핫 + 출연진/제목/줄거리 TF-IDF) 생성. 실행하면
  `data/processed/performance_vectors.npz`를 만든다(`performances.csv`와 같은 행 순서).
  **베이스라인 단순화**: FAISS·KoNLPy는 아직 안 씀 — 공연이 ~2,000건뿐이라 전체 코사인
  유사도 계산이 충분히 빠르고, 줄거리가 1.5%만 있어 형태소 분석(JVM 의존성 필요)의 효과가
  작기 때문. 공연 수가 늘거나 문장 임베딩으로 바꿀 때 재검토.
- `scoring.py` — 공연 기간 파싱, 종료 판별, 날짜 근접도, 최종 점수(취향×0.6 + 인기도×0.2 +
  날짜근접도×0.2), MMR 재정렬 등 추천 계산에 공통으로 쓰는 함수 모음. **`CONTENT_FIRST_MODE`
  스위치**가 여기 있다 — 지금은 `True`(콘텐츠 우선 모드), 미래 공연 데이터가 충분해지면
  `False`로 바꿔서 원래 설계(확정된 예정 공연만 추천)로 되돌릴 수 있다.
- `series.py` — 반복 공연 시리즈 감지 + 다음 회차 예상 시기 추정(규칙 기반, ML 아님).
  제목(연도 제거)이 3회 이상 반복된 시리즈의 최근 회차를 1년 뒤로 투영해 추천 후보에 끼운다.
- `recommend.py` — 추천 3종(MVP): `taste_recommend`(취향 추천), `condition_recommend`
  (날짜·동행·예산 조건 추천), `similar_performances`(비슷한 공연), `coldstart_recommend`
  (이번 주말 인기 공연). "미분류" 장르는 항상 후보에서 뺀다(`venue_fallback.py`가 대신
  처리). `CONTENT_FIRST_MODE`가 켜져 있으면 `taste_recommend`·`similar_performances`는
  날짜 확정 여부와 무관하게 콘텐츠로 추천하고 결과마다 `status`(확정 예정/매년 반복
  예상/과거 유사 공연 — 참고용)를 붙인다. `condition_recommend`·`coldstart_recommend`는
  이 스위치와 무관하게 항상 날짜 기반(특정 날짜를 묻는 기능에 과거 공연을 보여주면
  안 되므로). 가중치·날짜 근접도 기준은 `scoring.py` 상수로 분리해 "3. 오프라인 평가"
  단계에서 튜닝할 수 있게 해둠.
- `evaluate.py` — 오프라인 평가(가상 프로필 30개, Precision@5·Coverage·Diversity).
  결과·원인 분석·설계 전환 기록은 `REPORT.md` 참고. 콘텐츠 우선 모드 전환 후
  Precision@5 0.200 → **0.800**.

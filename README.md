# 올림픽공원 공연 추천 시스템

올림픽공원에서 열리는 공연·행사를 취향·방문 날짜·동행 유형에 맞춰 추천하고, 공연 당일 주차
혼잡 정보까지 안내하는 웹 서비스. 자세한 기획·아키텍처는
[`올림픽공원_공연추천시스템_웹개발_워크플로우.md`](./올림픽공원_공연추천시스템_웹개발_워크플로우.md)
참고.

> 본 서비스는 **한국체육산업개발 공공데이터**를 활용합니다.

## 진행 상황

| 단계 | 상태 | 비고 |
| --- | --- | --- |
| 1. 기획·요구사항 정의 | 완료 | 워크플로우 문서 |
| 2. 데이터 수집 | 완료 | [`pipeline/collection/REPORT.md`](./pipeline/collection/REPORT.md) — 2개 API(KSPO 대관정보, 주차·날씨)는 현재 실패 상태 |
| 3. 전처리·EDA | 완료 | [`pipeline/preprocessing/REPORT.md`](./pipeline/preprocessing/REPORT.md) |
| 4. 추천 모델 | 미착수 | `recommender/` |
| 5. 백엔드 | 미착수 | `backend/` |
| 6. 프론트엔드 | 미착수 | `frontend/` |

## 폴더 구조

```
pipeline/                       # 오프라인 배치: 수집·매칭·정제·임베딩 (GitHub Actions가 매일 실행)
├── collection/                 # 4개 공공데이터 API 수집 스크립트 (.py) + REPORT.md
└── preprocessing/              # KSPO-KOPIS 매칭, 장르/요금/연령 정규화, EDA 스크립트 (.py) + REPORT.md + figures/
recommender/                    # 추천 점수 계산 모듈 (오프라인 평가 포함) — 미착수
backend/                        # FastAPI, 저장소 읽기 전용 — 미착수
frontend/                       # Next.js — 미착수
data/
├── raw/                        # 각 출처의 원본 응답(JSON/CSV)을 그대로 저장 (git에는 미포함)
└── processed/                  # 매칭·정제를 거친 performances 등 가공 데이터 (git에는 미포함)
```

- `data/raw`, `data/processed`의 실제 데이터 파일은 `.gitignore`로 제외되어 있다(폴더 구조만
  `.gitkeep`으로 유지). 재수집하려면 아래 실행 방법을 따른다.
- 각 단계 폴더의 `REPORT.md`에 수집 건수, 매칭률, EDA 결과, 알려진 이슈가 정리되어 있다.

## 실행 방법

1. 저장소 루트에 `.env` 생성 (`.env.example` 참고, 공공데이터포털·KOPIS 서비스키 4종 필요):

   ```
   PERFORMANCE_INTEGRATED_API_KEY=
   KSPO_PERFORMANCE_API_KEY=
   KSPO_PARKING_WEATHER_API_KEY=
   KOPIS_API_KEY=
   ```

2. 데이터 수집:

   ```bash
   cd pipeline/collection
   pip install -r requirements.txt
   python run_all.py
   ```

3. 전처리·EDA (수집 산출물이 `data/raw`에 있어야 함):

   ```bash
   cd pipeline/preprocessing
   pip install -r requirements.txt
   python run_all.py
   ```

## 기술 스택

Python(FastAPI, pandas, KoNLPy, rapidfuzz) · scikit-learn/sentence-transformers/FAISS(추천) ·
React(Next.js) · PostgreSQL(SQLite 개발) · Vercel/Render/GitHub Actions(배포·자동화). 자세한
근거는 워크플로우 문서 5장 참고.

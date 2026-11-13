# pipeline/

수집·매칭·정제·임베딩을 담당하는 오프라인 배치. GitHub Actions가 매일 이 전체를 실행해
`data/processed/performances.csv`(와 추후 임베딩 산출물)를 갱신한다.

| 폴더 | 역할 | 상태 |
| --- | --- | --- |
| [`collection/`](./collection/REPORT.md) | 4개 공공데이터 API 수집 | 완료 (2개 API 실패 중, REPORT.md 참고) |
| [`preprocessing/`](./preprocessing/REPORT.md) | KSPO-KOPIS 매칭, 장르/요금/연령 정규화, EDA | 완료 |
| 임베딩 | 신규 공연 임베딩 생성 (`recommender/`가 쓸 벡터) | 미착수 |

## 실행

```bash
# 개별 단계
cd collection && pip install -r requirements.txt && python run_all.py
cd ../preprocessing && pip install -r requirements.txt && python run_all.py

# 전체 (collection → preprocessing 순서로 체이닝)
python run_all.py
```

각 단계의 데이터 경로·매칭 방법·알려진 이슈는 하위 폴더의 `REPORT.md`에 있다.

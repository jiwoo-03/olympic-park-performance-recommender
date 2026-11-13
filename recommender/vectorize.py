"""공연 벡터 생성: 장르 원-핫 + 출연진/제목/줄거리 TF-IDF.

출력: data/processed/performance_vectors.npz — performances.csv와 같은 행 순서의
공연 벡터(한 행 = [장르 원-핫(7) | TF-IDF]를 이어붙인 것). 소비하는 쪽은 두 파일을
같은 행 순서로 함께 읽으면 된다(따로 id 매핑을 두지 않음).

베이스라인 단계라 FAISS·KoNLPy는 쓰지 않는다 — 공연이 ~2,000건뿐이라 전체 코사인
유사도를 그냥 계산해도 충분히 빠르고, 형태소 분석기(KoNLPy)는 JVM 의존성이 필요한데
줄거리가 1.5%만 있어서(tasks/verification.md [2026-11-12] 참고) 들이는 비용 대비 효과가
작다. 공연 수가 크게 늘거나 문장 임베딩(ko-sroberta 등)으로 바꿀 때 재검토한다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from common import PROCESSED_DIR, get_logger

logger = get_logger("vectorize")

GENRE_ORDER = ["콘서트", "뮤지컬", "클래식", "페스티벌", "어린이", "스포츠/기타", "미분류"]

# "스포츠/기타"는 KOPIS 세부 장르 중 나머지 5종에 안 걸리는 걸 전부 모은 잡동사니
# 버킷이다(서커스/마술·연극·대중무용·전통무용이 뒤섞여 있음 — tasks/verification.md
# [2026-11-12] 참고). 같은 "기타"라는 것만으로 비슷하다고 볼 근거가 없어서(최현우 마술
# 공연과 로미오와 줄리엣 연극이 장르 일치만으로 유사도 0.5를 받는 문제를 실제로 확인함),
# 이 장르는 원-핫에서 신호를 안 주고 텍스트(제목·출연진) 유사도에만 맡긴다.
NO_GENRE_SIGNAL = {"스포츠/기타"}

# 장르 원-핫과 텍스트(TF-IDF) 블록을 이어붙일 때 쓰는 가중치. 둘 다 L2 정규화된
# 블록이라, 가중치를 조절하면 "장르가 같은 것"과 "출연진·제목이 비슷한 것" 중
# 코사인 유사도에서 어느 쪽을 더 중요하게 볼지 바꿀 수 있다(6장 평가에서 조정 대상).
GENRE_WEIGHT = 1.0
TEXT_WEIGHT = 1.0


def _build_text(df: pd.DataFrame) -> pd.Series:
    """제목+출연진+줄거리를 하나의 문자열로 합친다. 제목은 항상 있어 모든 행이
    빈 벡터가 되는 걸 막아준다(미분류 행은 cast·synopsis가 비어있는 경우가 많음)."""
    return (
        df["title"].fillna("") + " " + df["cast"].fillna("") + " " + df["synopsis"].fillna("")
    ).str.strip()


def build_vectors(df: pd.DataFrame) -> tuple[np.ndarray, TfidfVectorizer]:
    genre_onehot = pd.get_dummies(df["genre"]).reindex(columns=GENRE_ORDER, fill_value=0)
    for col in NO_GENRE_SIGNAL:
        genre_onehot[col] = 0
    genre_matrix = genre_onehot.to_numpy(dtype="float64")
    genre_norm = np.linalg.norm(genre_matrix, axis=1, keepdims=True)
    genre_matrix = np.divide(
        genre_matrix, genre_norm, out=np.zeros_like(genre_matrix), where=genre_norm > 0
    ) * GENRE_WEIGHT

    text = _build_text(df)
    # 쉼표·공백으로만 나눈 토큰 — 출연진 이름(고유명사)은 형태소 분석을 하면 오히려
    # 쪼개져서 매칭이 깨지므로, 쉼표/공백 구분 그대로를 토큰으로 쓰는 게 더 안전하다.
    vectorizer = TfidfVectorizer(token_pattern=r"[^\s,]+", min_df=2, max_features=5000)
    text_matrix = vectorizer.fit_transform(text).toarray() * TEXT_WEIGHT

    vectors = np.hstack([genre_matrix, text_matrix]).astype("float32")
    return vectors, vectorizer


def main() -> None:
    df = pd.read_csv(PROCESSED_DIR / "performances.csv")
    vectors, vectorizer = build_vectors(df)
    text_dim = vectors.shape[1] - len(GENRE_ORDER)
    logger.info(
        "공연 %d건, 벡터 차원 %d (장르 %d + 텍스트 TF-IDF %d, 어휘 %d개)",
        len(df), vectors.shape[1], len(GENRE_ORDER), text_dim, len(vectorizer.vocabulary_),
    )

    empty_text_rows = int((vectors[:, len(GENRE_ORDER):].sum(axis=1) == 0).sum())
    logger.info("텍스트 성분이 전부 0인 행(제목·출연진·줄거리에 흔한 단어가 없음): %d건", empty_text_rows)

    out_path = PROCESSED_DIR / "performance_vectors.npz"
    np.savez_compressed(out_path, vectors=vectors)
    logger.info("저장 완료: %s (performances.csv와 같은 행 순서)", out_path)


if __name__ == "__main__":
    main()

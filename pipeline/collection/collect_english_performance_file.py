"""한국체육산업개발주식회사_영문 공연정보 (data.go.kr 15149169) 수집.

이 데이터셋은 "파일데이터"라서 서비스키 없이 로그인 없이 CSV를 내려받을 수 있다.
data.go.kr는 다운로드를 2단계로 처리한다:
  1) POST /tcs/dss/selectFileDataDownload.do 로 최신 atchFileId를 조회
  2) GET  /cmm/cmm/fileDownload.do?atchFileId=...&fileDetailSn=... 로 실제 파일을 받음
파일은 CP949(EUC-KR)로 인코딩되어 있어 UTF-8로 변환해 저장한다.
"""
from __future__ import annotations

import csv
import io
import re

from common import get_logger, http_session, save_raw_bytes

logger = get_logger("collect_english_performance_file")

PUBLIC_DATA_PK = "15149169"
FILE_DATA_PAGE = f"https://www.data.go.kr/data/{PUBLIC_DATA_PK}/fileData.do"
DOWNLOAD_META_URL = "https://www.data.go.kr/tcs/dss/selectFileDataDownload.do"
DOWNLOAD_URL = "https://www.data.go.kr/cmm/cmm/fileDownload.do"


def _find_public_data_detail_pk(html: str) -> str:
    m = re.search(r"fn_fileDataDown\('" + PUBLIC_DATA_PK + r"',\s*'(uddi:[0-9a-f-]+)'", html)
    if not m:
        raise RuntimeError("publicDataDetailPk(uddi)를 페이지에서 찾지 못함 — data.go.kr 페이지 구조가 바뀌었을 수 있음")
    return m.group(1)


def main() -> None:
    session = http_session()

    page_resp = session.get(FILE_DATA_PAGE, timeout=30)
    page_resp.raise_for_status()
    detail_pk = _find_public_data_detail_pk(page_resp.text)
    logger.info("publicDataDetailPk=%s", detail_pk)

    meta_resp = session.post(
        DOWNLOAD_META_URL,
        data={
            "publicDataDetailPk": detail_pk,
            "publicDataPk": PUBLIC_DATA_PK,
            "atchFileId": "",
            "fileDetailSn": "1",
            "publicDataTyCode": "PR0051",
        },
        timeout=30,
    )
    meta_resp.raise_for_status()
    meta = meta_resp.json()
    atch_file_id = meta.get("atchFileId") or meta.get("fileDataRegistVO", {}).get("atchFileId")
    file_detail_sn = meta.get("fileDetailSn", "1")
    if not atch_file_id:
        raise RuntimeError(f"atchFileId를 응답에서 찾지 못함: {meta}")
    logger.info("atchFileId=%s fileDetailSn=%s", atch_file_id, file_detail_sn)

    file_resp = session.get(
        DOWNLOAD_URL,
        params={"atchFileId": atch_file_id, "fileDetailSn": file_detail_sn},
        timeout=30,
    )
    file_resp.raise_for_status()

    raw_bytes = file_resp.content
    text = raw_bytes.decode("cp949", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    logger.info("CSV 파싱: %d행 (헤더 포함)", len(rows))

    utf8_bytes = text.encode("utf-8")
    saved_path = save_raw_bytes("english_performance", utf8_bytes, "english_performance.csv")
    logger.info("저장 완료: %s", saved_path)
    return True


if __name__ == "__main__":
    main()

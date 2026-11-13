"""API 통합 테스트. 실제 `data/processed/performances.csv`를 그대로 메모리로
읽어서 쓰는 `TestClient`로, 엔드포인트 응답 모양과 엣지 케이스를 확인한다.

CORS는 `TestClient`가 브라우저 정책을 검사하지 않아서 여기서는 못 잡는다 — 그건
실제 Chromium으로만 확인할 수 있다(tasks/verification.md [2026-11-12] 참고). 이
테스트 스위트의 목적은 "응답 모양·상태코드·삭제한 엔드포인트가 진짜 없는지"이지
브라우저 전용 문제까지 잡는 게 아니다."""
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestPerformances:
    def test_list_returns_200_and_list(self, client):
        r = client.get("/performances")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_excludes_historical_and_unclassified(self, client):
        r = client.get("/performances")
        statuses = {row["status"] for row in r.json()}
        genres = {row["genre"] for row in r.json()}
        assert "과거 유사 공연 — 참고용" not in statuses
        assert "미분류" not in genres

    def test_list_filter_by_genre(self, client):
        r = client.get("/performances", params={"genre": "콘서트"})
        assert r.status_code == 200
        assert all(row["genre"] == "콘서트" for row in r.json())

    def test_detail_404_for_nonexistent_id(self, client):
        r = client.get("/performances/999999")
        assert r.status_code == 404

    def test_detail_200_for_existing_id(self, client):
        ids = [row["id"] for row in client.get("/performances").json()]
        r = client.get(f"/performances/{ids[0]}")
        assert r.status_code == 200
        assert r.json()["id"] == ids[0]


class TestRecommend:
    def test_recommend_me_returns_at_most_three_confirmed(self, client):
        r = client.get("/recommend/me", params={"session_id": "test-session"})
        assert r.status_code == 200
        results = r.json()
        assert len(results) <= 3
        assert all(row["status"] == "확정 예정" for row in results)

    def test_recommend_me_works_without_session_id(self, client):
        r = client.get("/recommend/me")
        assert r.status_code == 200

    def test_recommend_similar_404_for_nonexistent_id(self, client):
        r = client.get("/recommend/similar/999999")
        assert r.status_code == 404

    def test_recommend_similar_200_for_existing_id(self, client):
        ids = [row["id"] for row in client.get("/performances").json()]
        r = client.get(f"/recommend/similar/{ids[0]}")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestParkingForecast:
    def test_returns_501_not_available(self, client):
        r = client.get("/parking/forecast", params={"forecast_date": "2026-11-12"})
        assert r.status_code == 501


class TestRemovedEndpointsStayRemoved:
    """2026-11-12에 삭제한 로그인·찜하기·온보딩 엔드포인트가 다시 살아나지 않는지
    지키는 회귀 테스트(tasks/todo.md "추가 수정 작업" 참고)."""

    @pytest.mark.parametrize("method,path", [
        ("post", "/favorites"),
        ("get", "/favorites"),
        ("post", "/auth/signup"),
        ("post", "/auth/login"),
        ("post", "/recommend/onboarding"),
    ])
    def test_endpoint_is_gone(self, client, method, path):
        fn = getattr(client, method)
        r = fn(path, json={}) if method == "post" else fn(path)
        assert r.status_code == 404

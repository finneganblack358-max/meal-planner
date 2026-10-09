import pytest

from app import create_app
from app import routes
from app.clients.themealdb import MealDBError


class FakeClient:
    def search(self, query):
        return [{"id": "1", "title": f"{query} stew", "ingredients": [], "steps": []}]


class BrokenClient:
    def search(self, query):
        raise MealDBError("boom")


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_index_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Find a recipe" in response.data


def test_search_requires_query(client):
    response = client.get("/api/recipes/search")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_search_returns_results(client, monkeypatch):
    monkeypatch.setattr(routes, "get_client", lambda: FakeClient())
    response = client.get("/api/recipes/search?q=beef")
    assert response.status_code == 200
    assert response.get_json()["results"][0]["title"] == "beef stew"


def test_search_handles_upstream_failure(client, monkeypatch):
    monkeypatch.setattr(routes, "get_client", lambda: BrokenClient())
    response = client.get("/api/recipes/search?q=beef")
    assert response.status_code == 502
    assert "error" in response.get_json()
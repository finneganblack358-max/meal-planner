import pytest

from app import routes

RECIPE = {
    "id": "52771",
    "source": "themealdb",
    "title": "Spaghetti Arrabiata",
    "image": None,
    "category": "Vegetarian",
    "area": "Italian",
    "ingredients": [{"name": "penne rigate", "measure": "1 pound"}],
    "steps": ["Boil pasta."],
}


class FakeClient:
    def get_by_id(self, meal_id):
        return RECIPE if meal_id == "52771" else None


@pytest.fixture(autouse=True)
def fake_client(monkeypatch):
    monkeypatch.setattr(routes, "get_client", lambda: FakeClient())


def test_saved_list_starts_empty(client):
    response = client.get("/api/saved")
    assert response.status_code == 200
    assert response.get_json()["results"] == []


def test_save_and_list_recipe(client):
    response = client.post("/api/saved", json={"id": "52771"})
    assert response.status_code == 201
    assert response.get_json()["title"] == "Spaghetti Arrabiata"

    results = client.get("/api/saved").get_json()["results"]
    assert len(results) == 1
    assert results[0]["ingredients"] == RECIPE["ingredients"]
    assert results[0]["steps"] == RECIPE["steps"]


def test_saving_twice_does_not_duplicate(client):
    client.post("/api/saved", json={"id": "52771"})
    response = client.post("/api/saved", json={"id": "52771"})
    assert response.status_code == 200
    assert len(client.get("/api/saved").get_json()["results"]) == 1


def test_save_requires_id(client):
    response = client.post("/api/saved", json={})
    assert response.status_code == 400


def test_save_unknown_recipe(client):
    response = client.post("/api/saved", json={"id": "999"})
    assert response.status_code == 404


def test_remove_saved_recipe(client):
    saved_id = client.post("/api/saved", json={"id": "52771"}).get_json()["saved_id"]
    assert client.delete(f"/api/saved/{saved_id}").status_code == 204
    assert client.get("/api/saved").get_json()["results"] == []


def test_remove_unknown_saved_recipe(client):
    assert client.delete("/api/saved/123").status_code == 404
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
        return RECIPE


@pytest.fixture(autouse=True)
def fake_client(monkeypatch):
    monkeypatch.setattr(routes, "get_client", lambda: FakeClient())


def test_detail_page_shows_recipe(client):
    saved_id = client.post("/api/saved", json={"id": "52771"}).get_json()["saved_id"]
    response = client.get(f"/recipes/{saved_id}")
    assert response.status_code == 200
    assert b"Spaghetti Arrabiata" in response.data
    assert b"1 pound penne rigate" in response.data
    assert b"Boil pasta." in response.data


def test_detail_page_not_found(client):
    assert client.get("/recipes/999").status_code == 404
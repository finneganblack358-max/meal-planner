import pytest

from app import nutrition, routes
from app.clients.usda import USDAError

CHICKEN = {"calories": 100.0, "protein": 20.0, "carbs": 0.0, "fat": 2.0}

INGREDIENTS = [
    {"name": "Chicken", "measure": "200g"},
    {"name": "Salt", "measure": "to taste"},
    {"name": "Mystery", "measure": "100g"},
]


class FakeUSDA:
    def __init__(self):
        self.table = {"chicken": CHICKEN}
        self.calls = []

    def search(self, name):
        self.calls.append(name)
        return self.table.get(name)


class BrokenUSDA:
    def search(self, name):
        raise USDAError("boom")


class FakeMealDB:
    def get_by_id(self, meal_id):
        return {
            "id": meal_id,
            "source": "themealdb",
            "title": "Chicken Bowl",
            "image": None,
            "category": None,
            "area": None,
            "ingredients": INGREDIENTS,
            "steps": [],
        }


def test_grams_for_measure():
    assert nutrition.grams_for_measure("200g") == 200
    assert nutrition.grams_for_measure("1 lb") == pytest.approx(453.592, rel=1e-3)
    assert nutrition.grams_for_measure("1 cup") == pytest.approx(236.588, rel=1e-3)
    assert nutrition.grams_for_measure("2 cloves") is None
    assert nutrition.grams_for_measure("to taste") is None


def test_recipe_per_serving_counts_only_measurable_ingredients(client):
    usda = FakeUSDA()
    with client.application.app_context():
        nutrients, counted = nutrition.recipe_per_serving(INGREDIENTS, usda)

    # 200 g of chicken, split over 4 servings
    assert nutrients["calories"] == pytest.approx(50)
    assert nutrients["protein"] == pytest.approx(10)
    assert nutrients["fat"] == pytest.approx(1)
    assert counted == 1
    # Salt has no weight or volume, so it is never looked up
    assert usda.calls == ["chicken", "mystery"]


def test_lookups_are_cached(client):
    usda = FakeUSDA()
    with client.application.app_context():
        nutrition.recipe_per_serving(INGREDIENTS, usda)
        nutrition.recipe_per_serving(INGREDIENTS, usda)
    # Second run uses the cache, including the "no match" for mystery
    assert usda.calls == ["chicken", "mystery"]


def plan_one_meal(client, monkeypatch):
    monkeypatch.setattr(routes, "get_client", lambda: FakeMealDB())
    saved_id = client.post("/api/saved", json={"id": "1"}).get_json()["saved_id"]
    client.post(
        "/plan/set",
        data={"date": "2026-10-14", "slot": "dinner", "saved_id": str(saved_id)},
    )


def test_nutrition_page_shows_meal_and_day_total(client, monkeypatch):
    plan_one_meal(client, monkeypatch)
    monkeypatch.setattr(routes, "get_usda_client", lambda: FakeUSDA())

    page = client.get("/nutrition?start=2026-10-12")
    assert page.status_code == 200
    assert b"Chicken Bowl" in page.data
    assert b"Day total" in page.data
    assert b"<td>50</td>" in page.data
    assert b"1 of 3 ingredients" in page.data


def test_nutrition_page_empty_week(client, monkeypatch):
    plan_one_meal(client, monkeypatch)
    monkeypatch.setattr(routes, "get_usda_client", lambda: FakeUSDA())

    page = client.get("/nutrition?start=2026-10-19")
    assert page.status_code == 200
    assert b"Nothing planned" in page.data


def test_nutrition_page_handles_usda_failure(client, monkeypatch):
    plan_one_meal(client, monkeypatch)
    monkeypatch.setattr(routes, "get_usda_client", lambda: BrokenUSDA())

    page = client.get("/nutrition?start=2026-10-12")
    assert page.status_code == 502
    assert b"USDA" in page.data
import pytest

from app import routes


def make_recipe(meal_id, title):
    return {
        "id": meal_id,
        "source": "themealdb",
        "title": title,
        "image": None,
        "category": None,
        "area": None,
        "ingredients": [],
        "steps": [],
    }


RECIPES = {
    "101": make_recipe("101", "Spaghetti Arrabiata"),
    "102": make_recipe("102", "Pancakes"),
}


class FakeClient:
    def get_by_id(self, meal_id):
        return RECIPES.get(meal_id)


@pytest.fixture(autouse=True)
def fake_client(monkeypatch):
    monkeypatch.setattr(routes, "get_client", lambda: FakeClient())


@pytest.fixture
def saved(client):
    """Save both recipes and return their saved ids."""
    return [
        client.post("/api/saved", json={"id": meal_id}).get_json()["saved_id"]
        for meal_id in RECIPES
    ]


def plan_meal(client, saved_id, slot="dinner", date="2026-10-14"):
    return client.post(
        "/plan/set", data={"date": date, "slot": slot, "saved_id": str(saved_id)}
    )


def link_to(saved_id):
    return f'href="/recipes/{saved_id}"'.encode()


def test_plan_page_loads(client):
    response = client.get("/plan")
    assert response.status_code == 200
    assert b"Weekly plan" in response.data


def test_plan_page_shows_requested_week(client):
    response = client.get("/plan?start=2026-10-14")
    assert b"Mon Oct 12" in response.data
    assert b"Sun Oct 18" in response.data


def test_set_meal_shows_on_plan(client, saved):
    first, _ = saved
    response = plan_meal(client, first)
    assert response.status_code == 302
    assert "start=2026-10-12" in response.headers["Location"]

    page = client.get("/plan?start=2026-10-12")
    assert link_to(first) in page.data


def test_setting_a_slot_again_replaces_the_meal(client, saved):
    first, second = saved
    plan_meal(client, first)
    plan_meal(client, second)

    page = client.get("/plan?start=2026-10-12")
    assert link_to(second) in page.data
    assert link_to(first) not in page.data


def test_empty_choice_clears_the_slot(client, saved):
    first, _ = saved
    plan_meal(client, first)
    plan_meal(client, "")

    page = client.get("/plan?start=2026-10-12")
    assert link_to(first) not in page.data


def test_set_rejects_invalid_slot(client, saved):
    assert plan_meal(client, saved[0], slot="brunch").status_code == 400


def test_set_rejects_unknown_recipe(client):
    assert plan_meal(client, 999).status_code == 400


def test_set_rejects_invalid_date(client, saved):
    assert plan_meal(client, saved[0], date="not-a-date").status_code == 400


def test_removing_a_saved_recipe_clears_it_from_the_plan(client, saved):
    first, _ = saved
    plan_meal(client, first)
    client.delete(f"/api/saved/{first}")

    page = client.get("/plan?start=2026-10-12")
    assert link_to(first) not in page.data
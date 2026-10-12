import pytest

from app import routes
from app.shopping import build_shopping_list


def ing(name, measure):
    return {"name": name, "measure": measure}


def as_dict(items):
    return {item["name"].lower(): item["quantity"] for item in items}


def test_merges_same_unit():
    items = build_shopping_list([ing("Flour", "1 cup"), ing("flour", "2 cup")])
    assert items == [{"name": "Flour", "quantity": "3 cup"}]


def test_converts_volumes():
    items = build_shopping_list(
        [
            ing("Flour", "1 cup"),
            ing("Flour", "8 tbsp"),
            ing("Sugar", "2 tsp"),
            ing("Sugar", "1 tsp"),
        ]
    )
    assert as_dict(items) == {"flour": "1.5 cup", "sugar": "1 tbsp"}


def test_converts_weights():
    items = build_shopping_list([ing("Butter", "1 pound"), ing("butter", "8 oz")])
    assert items == [{"name": "Butter", "quantity": "1.5 lb"}]


def test_keeps_metric_units_metric():
    items = build_shopping_list(
        [
            ing("Beef", "800g"),
            ing("Beef", "400 g"),
            ing("Rice", "500 g"),
            ing("Rice", "250 g"),
        ]
    )
    assert as_dict(items) == {"beef": "1.2 kg", "rice": "750 g"}


def test_handles_fractions_and_mixed_numbers():
    items = build_shopping_list(
        [
            ing("Flour", "1 1/2 cup"),
            ing("Flour", "1/2 cup"),
            ing("Milk", "0.5 cup"),
            ing("Milk", "0.5 cup"),
        ]
    )
    assert as_dict(items) == {"flour": "2 cup", "milk": "1 cup"}


def test_merges_counts_with_plural_units():
    items = build_shopping_list([ing("Garlic", "2 cloves"), ing("Garlic", "3 clove")])
    assert items == [{"name": "Garlic", "quantity": "5 cloves"}]


def test_merges_amounts_with_no_unit():
    items = build_shopping_list([ing("Eggs", "2"), ing("Eggs", "3")])
    assert items == [{"name": "Eggs", "quantity": "5"}]


def test_different_unit_types_stay_separate():
    items = build_shopping_list([ing("Tomato", "1 cup"), ing("Tomato", "2 large")])
    assert items == [{"name": "Tomato", "quantity": "1 cup + 2 large"}]


def test_unparsed_measures_become_notes():
    items = build_shopping_list(
        [
            ing("Salt", "to taste"),
            ing("Olive oil", "2 tbsp"),
            ing("olive oil", "to taste"),
            ing("Olive Oil", "to taste"),
        ]
    )
    assert items == [
        {"name": "Olive oil", "quantity": "2 tbsp + to taste"},
        {"name": "Salt", "quantity": "to taste"},
    ]


def test_blank_measure_gives_name_only():
    assert build_shopping_list([ing("Salt", "")]) == [{"name": "Salt", "quantity": ""}]


def test_ranges_are_not_guessed():
    items = build_shopping_list([ing("Garlic", "3-4 cloves")])
    assert items == [{"name": "Garlic", "quantity": "3-4 cloves"}]


def test_list_is_sorted_by_name():
    items = build_shopping_list([ing("Zucchini", "1"), ing("apple", "2")])
    assert [item["name"] for item in items] == ["apple", "Zucchini"]


def make_recipe(meal_id, title, ingredients):
    return {
        "id": meal_id,
        "source": "themealdb",
        "title": title,
        "image": None,
        "category": None,
        "area": None,
        "ingredients": ingredients,
        "steps": [],
    }


RECIPES = {
    "101": make_recipe(
        "101", "Bread", [ing("Flour", "1 cup"), ing("Salt", "to taste")]
    ),
    "102": make_recipe("102", "Pancakes", [ing("Flour", "2 cup")]),
}


class FakeClient:
    def get_by_id(self, meal_id):
        return RECIPES.get(meal_id)


@pytest.fixture(autouse=True)
def fake_client(monkeypatch):
    monkeypatch.setattr(routes, "get_client", lambda: FakeClient())


def plan_two_meals(client):
    first = client.post("/api/saved", json={"id": "101"}).get_json()["saved_id"]
    second = client.post("/api/saved", json={"id": "102"}).get_json()["saved_id"]
    for date, slot, saved_id in (
        ("2026-10-14", "dinner", first),
        ("2026-10-15", "lunch", second),
    ):
        client.post(
            "/plan/set", data={"date": date, "slot": slot, "saved_id": str(saved_id)}
        )


def test_shopping_page_totals_planned_meals(client):
    plan_two_meals(client)
    page = client.get("/shopping?start=2026-10-12")
    assert page.status_code == 200
    assert b"3 cup" in page.data
    assert b"to taste" in page.data


def test_shopping_page_empty_week(client):
    plan_two_meals(client)
    page = client.get("/shopping?start=2026-10-19")
    assert page.status_code == 200
    assert b"Nothing planned" in page.data
import pytest
import requests

from app.clients.usda import USDAClient, USDAError, normalize_food

RAW_FOOD = {
    "fdcId": 171077,
    "description": "Chicken, breast, raw",
    "foodNutrients": [
        {"nutrientId": 1008, "nutrientNumber": "208", "unitName": "KCAL", "value": 120},
        {"nutrientId": 1003, "nutrientNumber": "203", "unitName": "G", "value": 22.5},
        {"nutrientId": 1004, "nutrientNumber": "204", "unitName": "G", "value": 2.6},
        {"nutrientId": 1005, "nutrientNumber": "205", "unitName": "G", "value": 0},
        {"nutrientId": 1087, "nutrientNumber": "301", "unitName": "MG", "value": 5},
    ],
}


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class FakeSession:
    def __init__(self, data=None, error=None):
        self.data = data
        self.error = error
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append((url, params))
        if self.error:
            raise self.error
        return FakeResponse(self.data)


def test_normalize_food_maps_nutrients():
    assert normalize_food(RAW_FOOD) == {
        "calories": 120.0,
        "protein": 22.5,
        "carbs": 0.0,
        "fat": 2.6,
    }


def test_normalize_food_uses_atwater_energy_when_needed():
    food = {
        "foodNutrients": [
            {"nutrientId": 2047, "nutrientNumber": "957", "value": 98},
            {"nutrientId": 1003, "nutrientNumber": "203", "value": 10},
        ]
    }
    values = normalize_food(food)
    assert values["calories"] == 98.0
    assert values["protein"] == 10.0
    assert values["fat"] == 0.0


def test_normalize_food_without_macros_is_none():
    food = {"foodNutrients": [{"nutrientId": 1087, "nutrientNumber": "301", "value": 5}]}
    assert normalize_food(food) is None


def test_search_returns_values_and_sends_key_and_query():
    session = FakeSession({"foods": [RAW_FOOD]})
    values = USDAClient(api_key="KEY", session=session).search("chicken")
    assert values["calories"] == 120.0

    url, params = session.calls[0]
    assert url.endswith("/foods/search")
    assert params["api_key"] == "KEY"
    assert params["query"] == "chicken"


def test_search_with_no_match_is_none():
    session = FakeSession({"foods": []})
    assert USDAClient(session=session).search("zzzz") is None


def test_search_failure_raises_usda_error():
    session = FakeSession(error=requests.ConnectionError("boom"))
    with pytest.raises(USDAError):
        USDAClient(session=session).search("chicken")
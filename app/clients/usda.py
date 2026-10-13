"""USDA FoodData Central client.

Looks up one ingredient and returns its nutrients per 100 g, or None when
nothing matches. API guide: https://fdc.nal.usda.gov/api-guide.html
"""

import requests

BASE_URL = "https://api.nal.usda.gov/fdc/v1"
TIMEOUT_SECONDS = 10

# Nutrient ids and numbers, in order of preference. Foundation foods report
# energy under the Atwater ids (2047, 2048) instead of 1008.
NUTRIENT_KEYS = {
    "calories": ("1008", "208", "2047", "957", "2048", "958"),
    "protein": ("1003", "203"),
    "carbs": ("1005", "205"),
    "fat": ("1004", "204"),
}


class USDAError(Exception):
    """Raised when FoodData Central can't be reached or returns bad data."""


class USDAClient:
    def __init__(self, api_key="DEMO_KEY", session=None):
        self.api_key = api_key
        self.session = session or requests.Session()

    def search(self, name):
        """Return {"calories", "protein", "carbs", "fat"} per 100 g, or None."""
        try:
            response = self.session.get(
                f"{BASE_URL}/foods/search",
                params={
                    "api_key": self.api_key,
                    "query": name,
                    "dataType": "Foundation,SR Legacy",
                    "pageSize": 1,
                },
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            raise USDAError(
                f"USDA request failed ({type(exc).__name__}, status {status})"
            ) from exc

        foods = data.get("foods") or []
        return normalize_food(foods[0]) if foods else None


def normalize_food(food):
    found = {}
    for nutrient in food.get("foodNutrients") or []:
        if nutrient.get("value") is None:
            continue
        for key in (nutrient.get("nutrientId"), nutrient.get("nutrientNumber")):
            if key is not None:
                found[str(key)] = float(nutrient["value"])

    values = {}
    for name, keys in NUTRIENT_KEYS.items():
        values[name] = next((found[k] for k in keys if k in found), None)

    if all(value is None for value in values.values()):
        return None
    return {name: value or 0.0 for name, value in values.items()}
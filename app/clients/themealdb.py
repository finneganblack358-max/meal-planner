"""TheMealDB client.

Every API response is converted into the app's internal recipe format, so the
rest of the app never depends on TheMealDB's field names. Future clients
(Spoonacular, etc.) should return the same shape:

    {
        "id": str, "source": str, "title": str, "image": str | None,
        "category": str | None, "area": str | None,
        "ingredients": [{"name": str, "measure": str}],
        "steps": [str],
    }
"""

import requests

BASE_URL = "https://www.themealdb.com/api/json/v1"
TIMEOUT_SECONDS = 10
MAX_INGREDIENTS = 20  # TheMealDB uses numbered fields: strIngredient1..20


class MealDBError(Exception):
    """Raised when TheMealDB can't be reached or returns bad data."""


class TheMealDBClient:
    def __init__(self, api_key="1", session=None):
        self.api_key = api_key
        self.session = session or requests.Session()

    def _get(self, endpoint, **params):
        url = f"{BASE_URL}/{self.api_key}/{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise MealDBError(f"TheMealDB request failed: {exc}") from exc

    def search(self, query):
        data = self._get("search.php", s=query)
        return [normalize_meal(meal) for meal in data.get("meals") or []]

    def get_by_id(self, meal_id):
        data = self._get("lookup.php", i=meal_id)
        meals = data.get("meals") or []
        return normalize_meal(meals[0]) if meals else None

    def random(self):
        data = self._get("random.php")
        meals = data.get("meals") or []
        return normalize_meal(meals[0]) if meals else None


def normalize_meal(raw):
    ingredients = []
    for i in range(1, MAX_INGREDIENTS + 1):
        name = (raw.get(f"strIngredient{i}") or "").strip()
        measure = (raw.get(f"strMeasure{i}") or "").strip()
        if name:
            ingredients.append({"name": name, "measure": measure})

    instructions = raw.get("strInstructions") or ""
    steps = [line.strip() for line in instructions.splitlines() if line.strip()]

    return {
        "id": raw.get("idMeal"),
        "source": "themealdb",
        "title": raw.get("strMeal"),
        "image": raw.get("strMealThumb"),
        "category": raw.get("strCategory"),
        "area": raw.get("strArea"),
        "ingredients": ingredients,
        "steps": steps,
    }
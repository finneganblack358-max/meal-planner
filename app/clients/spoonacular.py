"""Spoonacular client.

One complexSearch call returns full recipe details, which are converted into
the app's internal recipe format. The free plan has a small daily quota, so
callers cache results (see db.py).
"""

import requests

BASE_URL = "https://api.spoonacular.com"
TIMEOUT_SECONDS = 15
RESULTS_PER_SEARCH = 10

# Diet names Spoonacular understands (a subset of its full list).
DIETS = ("vegetarian", "vegan", "gluten free", "ketogenic", "pescetarian", "paleo", "whole30")

# Allergy / intolerance names Spoonacular understands.
INTOLERANCES = (
    "Dairy", "Egg", "Gluten", "Grain", "Peanut", "Seafood",
    "Sesame", "Shellfish", "Soy", "Sulfite", "Tree Nut", "Wheat",
)


class SpoonacularError(Exception):
    """Raised when Spoonacular can't be reached or returns bad data."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class SpoonacularClient:
    def __init__(self, api_key="", session=None):
        self.api_key = api_key
        self.session = session or requests.Session()

    def search(self, query, diet=None, intolerances=None):
        params = {
            "apiKey": self.api_key,
            "query": query,
            "number": RESULTS_PER_SEARCH,
            "addRecipeInformation": "true",
            "instructionsRequired": "true",
        }
        if diet:
            params["diet"] = diet
        if intolerances:
            params["intolerances"] = intolerances

        try:
            response = self.session.get(
                f"{BASE_URL}/recipes/complexSearch",
                params=params,
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            raise SpoonacularError(
                f"Spoonacular request failed ({type(exc).__name__}, status {status})",
                status,
            ) from exc

        return [normalize_recipe(raw) for raw in data.get("results") or []]


def format_amount(value):
    return f"{value:.2f}".rstrip("0").rstrip(".")


def normalize_recipe(raw):
    ingredients = []
    for item in raw.get("extendedIngredients") or []:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        amount = item.get("amount")
        unit = (item.get("unit") or "").strip()
        measure = f"{format_amount(amount)} {unit}".strip() if amount else ""
        ingredients.append({"name": name, "measure": measure})

    steps = []
    for group in raw.get("analyzedInstructions") or []:
        for step in group.get("steps") or []:
            text = (step.get("step") or "").strip()
            if text:
                steps.append(text)

    cuisines = raw.get("cuisines") or []
    dish_types = raw.get("dishTypes") or []
    return {
        "id": str(raw.get("id")),
        "source": "spoonacular",
        "title": raw.get("title"),
        "image": raw.get("image"),
        "category": dish_types[0].title() if dish_types else None,
        "area": cuisines[0] if cuisines else None,
        "ingredients": ingredients,
        "steps": steps,
    }
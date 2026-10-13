"""Estimate nutrition for planned meals from USDA FoodData Central.

USDA reports nutrients per 100 g, so only ingredients measured by weight or
volume can be counted (volumes are treated as 1 g per ml). Everything else is
skipped, and the page shows how many ingredients were counted.
"""

from . import db
from .shopping import UNITS, parse_measure

NUTRIENTS = ("calories", "protein", "carbs", "fat")
SERVINGS = 4  # TheMealDB doesn't say how many people a recipe feeds


def grams_for_measure(measure):
    """Return the grams in a measure like '200g' or '1 cup', or None."""
    parsed = parse_measure(measure)
    if parsed is None:
        return None
    amount, unit = parsed
    info = UNITS.get(unit.lower())
    if info is None:
        return None
    return amount * info[1]


def get_per_100g(name, client):
    """Nutrients per 100 g for an ingredient, using the SQLite cache first."""
    key = name.strip().lower()
    cached = db.get_nutrition(key)
    if cached is not None:
        return cached["values"]
    values = client.search(key)  # may raise USDAError
    db.save_nutrition(key, values)
    return values


def recipe_per_serving(ingredients, client):
    """Return (nutrients per serving, number of ingredients counted)."""
    totals = {name: 0.0 for name in NUTRIENTS}
    counted = 0
    for ingredient in ingredients:
        grams = grams_for_measure(ingredient.get("measure") or "")
        if grams is None:
            continue
        per_100g = get_per_100g(ingredient["name"], client)
        if per_100g is None:
            continue
        for name in NUTRIENTS:
            totals[name] += per_100g[name] * grams / 100
        counted += 1
    return {name: totals[name] / SERVINGS for name in NUTRIENTS}, counted


def build_week_nutrition(meals, client):
    """Group planned meals by date: {date: {"meals": [...], "totals": {...}}}."""
    per_recipe = {}
    week = {}
    for meal in meals:
        saved_id = meal["saved_id"]
        if saved_id not in per_recipe:
            per_recipe[saved_id] = recipe_per_serving(meal["ingredients"], client)
        nutrients, counted = per_recipe[saved_id]

        day = week.setdefault(
            meal["plan_date"], {"meals": [], "totals": {name: 0.0 for name in NUTRIENTS}}
        )
        day["meals"].append(
            {
                "slot": meal["slot"],
                "title": meal["title"],
                "nutrients": nutrients,
                "counted": counted,
                "total": len(meal["ingredients"]),
            }
        )
        for name in NUTRIENTS:
            day["totals"][name] += nutrients[name]
    return week
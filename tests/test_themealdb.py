from app.clients.themealdb import normalize_meal

RAW_MEAL = {
    "idMeal": "52771",
    "strMeal": "Spaghetti Arrabiata",
    "strCategory": "Vegetarian",
    "strArea": "Italian",
    "strInstructions": "Boil pasta.\r\n\r\nMake sauce.",
    "strMealThumb": "https://example.com/arrabiata.jpg",
    "strIngredient1": "penne rigate",
    "strMeasure1": "1 pound",
    "strIngredient2": "olive oil",
    "strMeasure2": "1/4 cup",
    "strIngredient3": "",
    "strMeasure3": " ",
    "strIngredient4": None,
}


def test_normalize_meal_maps_fields():
    meal = normalize_meal(RAW_MEAL)
    assert meal["id"] == "52771"
    assert meal["source"] == "themealdb"
    assert meal["title"] == "Spaghetti Arrabiata"
    assert meal["area"] == "Italian"


def test_normalize_meal_skips_blank_ingredients():
    meal = normalize_meal(RAW_MEAL)
    assert meal["ingredients"] == [
        {"name": "penne rigate", "measure": "1 pound"},
        {"name": "olive oil", "measure": "1/4 cup"},
    ]


def test_normalize_meal_splits_steps():
    meal = normalize_meal(RAW_MEAL)
    assert meal["steps"] == ["Boil pasta.", "Make sauce."]
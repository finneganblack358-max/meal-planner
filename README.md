# Meal Planner

A Python (Flask) web app for finding recipes, planning a week of meals, and generating a shopping list. The front end is plain HTML, CSS and JavaScript.

**Status:** Recipe search (TheMealDB, and Spoonacular with diet and allergy filters), saved recipes (SQLite), a recipe detail page, a weekly meal plan, a weekly shopping list and USDA nutrition estimates work. Only the pantry feature is left on the roadmap below.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env             # Windows: copy .env.example .env
python run.py
```

Open http://127.0.0.1:5000, search for a recipe and click Save. Choose Spoonacular as the source to filter by diet or allergy. Saved recipes appear below the search results; click a title to open its detail page. Open the Plan page to assign saved recipes to breakfast, lunch and dinner for each day of the week, then open the Shopping list or Nutrition page for that week. Run the tests with `pytest`.

The SQLite database (`meal_planner.db`) is created automatically on first run.

### API keys

Set these in `.env` and restart the app after changing them.

- **USDA** (Nutrition page): the shared `DEMO_KEY` in `.env.example` is limited to roughly 10 to 30 requests per hour, so get a free personal key (1,000 requests per hour) at https://fdc.nal.usda.gov/api-key-signup and set `USDA_API_KEY`.
- **Spoonacular** (Spoonacular search): get a free key at https://spoonacular.com/food-api and set `SPOONACULAR_API_KEY`. Without it, TheMealDB search still works and Spoonacular search shows a setup message.

## Project structure

```
meal-planner/
├── run.py                  Entry point
├── LICENSE                 MIT license
├── requirements.txt        Runtime dependencies
├── requirements-dev.txt    Adds pytest
├── .env.example            Template for API keys (copy to .env)
├── meal_planner.db         Created on first run (git-ignored)
├── app/
│   ├── __init__.py         App factory (create_app), sets up the database
│   ├── config.py           Settings loaded from environment variables
│   ├── db.py               SQLite storage: saved recipes, meal plan, caches
│   ├── shopping.py         Merges ingredients and converts units for the shopping list
│   ├── nutrition.py        Estimates calories and macros for planned meals
│   ├── routes.py           Pages and JSON endpoints
│   ├── clients/
│   │   ├── themealdb.py    TheMealDB client + conversion to the internal recipe format
│   │   ├── spoonacular.py  Spoonacular client (search with diet and allergy filters)
│   │   └── usda.py         USDA FoodData Central client (nutrients per 100 g)
│   ├── templates/          base.html, index.html, recipe.html, plan.html,
│   │                       shopping.html, nutrition.html
│   └── static/             css/style.css, js/main.js
└── tests/                  conftest.py plus client, route, saved-recipe, detail, plan,
                            shopping, USDA, nutrition and Spoonacular tests (API calls
                            are mocked, each test gets its own temporary database)
```

## How it works

1. The browser calls `GET /api/recipes/search?q=...` on this app, optionally with `source=spoonacular`, `diet=...` and `intolerances=...`.
2. The route asks the TheMealDB or Spoonacular client for matches.
3. The client converts each result into the internal recipe format, so the rest of the app never depends on one provider's field names.
4. The front end renders the results as cards.
5. Clicking Save sends the recipe id and source to `POST /api/saved`. TheMealDB recipes are fetched by id; Spoonacular recipes come from the search cache, so saving costs no quota. The recipe is stored in SQLite.
6. The page lists saved recipes from `GET /api/saved`, and Remove calls `DELETE /api/saved/<id>`.
7. Saved recipes link to `/recipes/<id>`, a server-rendered detail page with the ingredients and steps.
8. The Plan page (`/plan`) shows one week, Monday to Sunday. Choosing a recipe for a slot posts to `/plan/set`, which stores it in the `meal_plan` table. Deleting a saved recipe also removes it from the plan.
9. The Shopping list page (`/shopping`) gathers the ingredients of every meal planned that week and merges them in `app/shopping.py`.
10. The Nutrition page (`/nutrition`) looks up each ingredient in USDA FoodData Central, caches the result in SQLite, and totals calories, protein, carbs and fat per meal and per day.

## Spoonacular rules

The free plan allows 150 points per day, so searches are cached:

- Each search returns up to 10 recipes with full details in one request (about 1.35 points).
- Results are cached in SQLite for 24 hours by query, diet and allergy filter, so repeating a search costs nothing.
- Every recipe in a search is cached too, so saving one makes no extra request.
- If the daily limit is reached the app says so and TheMealDB search keeps working.
- The allergy filter is Spoonacular's automated check and can miss things. Always read the ingredient list yourself if an allergy is serious.

## Shopping list rules

TheMealDB measures are free text, so the merging is deliberately simple:

- Ingredients are matched by name, ignoring case. "Tomato" and "Tomatoes" are different items.
- Measures that start with a number are added up: `1 cup` + `8 tbsp` = `1.5 cup`.
- Teaspoons, tablespoons, cups and millilitres/litres convert between each other, and so do ounces, pounds and grams/kilograms. The result stays in the same system (US or metric) as the first measure seen.
- Other units (`2 cloves`, `1 large`) only merge with the same unit.
- Anything else (`to taste`, `Juice of 1 lime`, ranges like `3-4 cloves`) is kept as a note instead of being guessed.

## Nutrition rules

The numbers are estimates:

- USDA values are per 100 g, so only ingredients measured by weight or volume are counted. Volumes are treated as 1 g per ml. Items like `2 cloves` or `to taste` are skipped.
- Each meal shows how many of its ingredients were counted, so real values are usually higher.
- Recipes don't give servings, so each recipe is assumed to make 4 servings (`SERVINGS` in `app/nutrition.py`) and each planned meal counts as one serving.
- Each ingredient name uses the top match from USDA's Foundation and SR Legacy data, which is sometimes not the food you meant.
- Every lookup is cached in the `nutrition_cache` table, so an ingredient is only requested once.

API keys stay on the server in `.env`, which is git-ignored.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Search page and saved recipes |
| GET | `/recipes/<id>` | Detail page for a saved recipe |
| GET | `/plan?start=YYYY-MM-DD` | Weekly plan page (defaults to this week) |
| POST | `/plan/set` | Set or clear a slot; form fields `date`, `slot`, `saved_id` |
| GET | `/shopping?start=YYYY-MM-DD` | Shopping list for a week (defaults to this week) |
| GET | `/nutrition?start=YYYY-MM-DD` | Nutrition estimates for a week (defaults to this week) |
| GET | `/api/recipes/search?q=...&source=...&diet=...&intolerances=...` | Search; `source` is `themealdb` (default) or `spoonacular`; `diet` and `intolerances` (for example `Dairy,Egg`) apply to Spoonacular |
| GET | `/api/saved` | List saved recipes |
| POST | `/api/saved` | Save a recipe, body `{"id": "52771", "source": "themealdb"}` |
| DELETE | `/api/saved/<id>` | Remove a saved recipe |

## Internal recipe format

Every API client returns recipes in this shape:

```
id, source, title, image, category, area,
ingredients: [{name, measure}],
steps: [text]
```

Saved recipes also carry `saved_id`, the database row id.

## APIs

| API | Key | Role | Status |
|---|---|---|---|
| TheMealDB | Test key `1` | Recipe search and browsing | In use |
| USDA FoodData Central | https://fdc.nal.usda.gov/api-key-signup | Nutrition per ingredient | In use |
| Spoonacular | https://spoonacular.com/food-api | Recipe search with diet and allergy filters | In use |
| Open Food Facts | None (send a User-Agent) | Barcode and pantry lookups | Planned |

## Roadmap

- [x] Project skeleton, TheMealDB search, tests
- [x] SQLite storage for saved recipes
- [x] Recipe detail page
- [x] Weekly meal calendar
- [x] Shopping list with merged ingredients and unit conversion
- [x] USDA nutrition totals per meal and per day
- [x] Spoonacular search with diet and allergy filters (cached; the free daily quota is small)
- [ ] Open Food Facts barcode lookup for a pantry

## License

Released under the [MIT License](LICENSE).
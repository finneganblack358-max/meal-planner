# Meal Planner

A Python (Flask) web app for finding recipes, planning a week of meals, and generating a shopping list. The front end is plain HTML, CSS and JavaScript.

**Status:** Recipe search (TheMealDB), saved recipes (SQLite), a recipe detail page and a weekly meal plan work. Everything else is on the roadmap below.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env             # Windows: copy .env.example .env
python run.py
```

Open http://127.0.0.1:5000, search for a recipe and click Save. Saved recipes appear below the search results; click a title to open its detail page. Open the Plan page to assign saved recipes to breakfast, lunch and dinner for each day of the week. Run the tests with `pytest`.

The SQLite database (`meal_planner.db`) is created automatically on first run.

## Project structure

```
meal-planner/
├── run.py                  Entry point
├── requirements.txt        Runtime dependencies
├── requirements-dev.txt    Adds pytest
├── .env.example            Template for API keys (copy to .env)
├── meal_planner.db         Created on first run (git-ignored)
├── app/
│   ├── __init__.py         App factory (create_app), sets up the database
│   ├── config.py           Settings loaded from environment variables
│   ├── db.py               SQLite storage for saved recipes and the meal plan
│   ├── routes.py           Pages and JSON endpoints
│   ├── clients/
│   │   └── themealdb.py    API client + conversion to the internal recipe format
│   ├── templates/          base.html, index.html, recipe.html, plan.html
│   └── static/             css/style.css, js/main.js
└── tests/                  conftest.py plus client, route, saved-recipe, detail and plan tests
                            (API calls are mocked, each test gets its own temporary database)
```

## How it works

1. The browser calls `GET /api/recipes/search?q=...` on this app.
2. The route asks the TheMealDB client for matches.
3. The client converts each result into the internal recipe format, so the rest of the app never depends on one provider's field names.
4. The front end renders the results as cards.
5. Clicking Save sends the recipe id to `POST /api/saved`. The server fetches the full recipe itself and stores it in SQLite.
6. The page lists saved recipes from `GET /api/saved`, and Remove calls `DELETE /api/saved/<id>`.
7. Saved recipes link to `/recipes/<id>`, a server-rendered detail page with the ingredients and steps.
8. The Plan page (`/plan`) shows one week, Monday to Sunday. Choosing a recipe for a slot posts to `/plan/set`, which stores it in the `meal_plan` table. Deleting a saved recipe also removes it from the plan.

API keys stay on the server in `.env`, which is git-ignored.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Search page and saved recipes |
| GET | `/recipes/<id>` | Detail page for a saved recipe |
| GET | `/plan?start=YYYY-MM-DD` | Weekly plan page (defaults to this week) |
| POST | `/plan/set` | Set or clear a slot; form fields `date`, `slot`, `saved_id` |
| GET | `/api/recipes/search?q=...` | Search TheMealDB |
| GET | `/api/saved` | List saved recipes |
| POST | `/api/saved` | Save a recipe, body `{"id": "52771"}` |
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
| USDA FoodData Central | https://fdc.nal.usda.gov/api-key-signup | Nutrition per ingredient | Planned |
| Spoonacular | https://spoonacular.com/food-api | Diet filters, ingredient parsing | Planned |
| Open Food Facts | None (send a User-Agent) | Barcode and pantry lookups | Planned |

## Roadmap

- [x] Project skeleton, TheMealDB search, tests
- [x] SQLite storage for saved recipes
- [x] Recipe detail page
- [x] Weekly meal calendar
- [ ] Shopping list with merged ingredients and unit conversion
- [ ] USDA nutrition totals per meal and per day
- [ ] Spoonacular search with diet filters (cache results; the free daily quota is small)
- [ ] Open Food Facts barcode lookup for a pantry

## License

Not chosen yet. Add a LICENSE file before publishing.
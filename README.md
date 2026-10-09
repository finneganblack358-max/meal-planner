# Meal Planner

A Python (Flask) web app for finding recipes, planning a week of meals, and generating a shopping list. The front end is plain HTML, CSS and JavaScript.

**Status:** initial commit. Recipe search works through TheMealDB. Everything else is on the roadmap below.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env             # Windows: copy .env.example .env
python run.py
```

Open http://127.0.0.1:5000 and search for a recipe. Run the tests with `pytest`.

## Project structure

```
meal-planner/
├── run.py                  Entry point
├── requirements.txt        Runtime dependencies
├── requirements-dev.txt    Adds pytest
├── .env.example            Template for API keys (copy to .env)
├── app/
│   ├── __init__.py         App factory (create_app)
│   ├── config.py           Settings loaded from environment variables
│   ├── routes.py           Pages and JSON endpoints
│   ├── clients/
│   │   └── themealdb.py    API client + conversion to the internal recipe format
│   ├── templates/          base.html, index.html
│   └── static/             css/style.css, js/main.js
└── tests/                  Client and route tests (API calls are mocked)
```

## How it works

1. The browser calls `GET /api/recipes/search?q=...` on this app.
2. The route asks the TheMealDB client for matches.
3. The client converts each result into the internal recipe format, so the rest of the app never depends on one provider's field names.
4. The front end renders the results as cards.

API keys stay on the server in `.env`, which is git-ignored.

## Internal recipe format

Every API client returns recipes in this shape:

```
id, source, title, image, category, area,
ingredients: [{name, measure}],
steps: [text]
```

## APIs

| API | Key | Role | Status |
|---|---|---|---|
| TheMealDB | Test key `1` | Recipe search and browsing | In use |
| USDA FoodData Central | https://fdc.nal.usda.gov/api-key-signup | Nutrition per ingredient | Planned |
| Spoonacular | https://spoonacular.com/food-api | Diet filters, ingredient parsing | Planned |
| Open Food Facts | None (send a User-Agent) | Barcode and pantry lookups | Planned |

## Roadmap

- [x] Project skeleton, TheMealDB search, tests
- [ ] SQLite storage for saved recipes
- [ ] Recipe detail page
- [ ] Weekly meal calendar
- [ ] Shopping list with merged ingredients and unit conversion
- [ ] USDA nutrition totals per meal and per day
- [ ] Spoonacular search with diet filters (cache results; the free daily quota is small)
- [ ] Open Food Facts barcode lookup for a pantry

## License

Not chosen yet. Add a LICENSE file before publishing.
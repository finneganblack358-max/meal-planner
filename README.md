# Meal Planner

A Python (Flask) web app for finding recipes, planning a week of meals, generating a shopping list and keeping a pantry. The front end is plain HTML, CSS and JavaScript.

**Version 1.0.0.** Recipe search (TheMealDB, and Spoonacular with diet and allergy filters), saved recipes (SQLite), a recipe detail page, a weekly meal plan, a weekly shopping list, USDA nutrition estimates and an Open Food Facts barcode pantry all work. See the [changelog](CHANGELOG.md) for what changed.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env             # Windows: copy .env.example .env
python run.py
```

Open http://127.0.0.1:5000, search for a recipe and click Save. Choose Spoonacular as the source to filter by diet or allergy. Saved recipes appear below the search results; click a title to open its detail page. Open the Plan page to assign saved recipes to breakfast, lunch and dinner for each day of the week, then open the Shopping list or Nutrition page for that week. Open the Pantry page to add products by barcode.

The SQLite database (`meal_planner.db`) is created automatically on first run.

### API keys and settings

Set these in `.env` and restart the app after changing them.

- **USDA** (Nutrition page): the shared `DEMO_KEY` in `.env.example` is limited to roughly 10 to 30 requests per hour, so get a free personal key (1,000 requests per hour) at https://fdc.nal.usda.gov/api-key-signup and set `USDA_API_KEY`.
- **Spoonacular** (Spoonacular search): get a free key at https://spoonacular.com/food-api and set `SPOONACULAR_API_KEY`. Without it, TheMealDB search still works and Spoonacular search shows a setup message.
- **Open Food Facts** (Pantry): no key is needed, but it asks every app to send a User-Agent with a contact. Set `OPENFOODFACTS_USER_AGENT` to something like `MealPlanner/1.0 (your-email@example.com)`.
- **Debug mode**: set `FLASK_DEBUG=1` for development with `run.py` (auto-reload and the debugger). It is off by default, and must stay off on any server other people can reach.
- **Publishing**: `APP_PASSWORD`, `BEHIND_PROXY` and `DATABASE_PATH` are described below.

## Development

Run the tests with:

```bash
pytest
```

Every external API is mocked and each test uses its own temporary database, so no keys or internet connection are needed. A GitHub Actions workflow (`.github/workflows/tests.yml`) runs the same tests on every push and pull request.

`python run.py` uses Flask's development server, which is fine for local use but must not be exposed to the internet.

## Publishing with a Cloudflare Tunnel

A [Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/) lets you reach the app running on your own computer from anywhere, without opening any ports. The app only listens on `127.0.0.1`, and `cloudflared` carries traffic from Cloudflare to it.

**Before you publish**, set these in `.env`:

```
APP_PASSWORD=a-long-password-only-you-know
BEHIND_PROXY=1
# Optional, for example to keep the database out of a OneDrive folder:
# DATABASE_PATH=C:/meal-planner-data/meal_planner.db
```

- `APP_PASSWORD` protects the whole site with a browser login prompt. Any username works. Without a password, anyone who finds the URL could change your data and spend your API quotas.
- `BEHIND_PROXY=1` makes the app trust the forwarded headers Cloudflare adds. Leave it at `0` when not using a tunnel.
- Never publish with `run.py`. Use `serve.py`, which runs the Waitress server.

**Then run it:**

```bash
pip install -r requirements.txt
python serve.py
```

The app is now on http://127.0.0.1:8080 (change the port with `PORT` in `.env`). Install `cloudflared` (`winget install --id Cloudflare.cloudflared` on Windows, then open a new terminal so it is on your path) and either:

- **Quick tunnel** (for testing, no account needed): `cloudflared tunnel --url http://127.0.0.1:8080` prints a random `https://...trycloudflare.com` address that works until you press Ctrl+C. A new address is generated each time.
- **Named tunnel** (a permanent address on your own domain): in the Cloudflare dashboard go to Networking > Tunnels, create a tunnel, run the install command it shows on your computer, then add a published application route that points your hostname to `http://127.0.0.1:8080`.

Use `127.0.0.1`, not `localhost`. On Windows `localhost` can resolve to the IPv6 address `::1`, which the app is not listening on.

The site is only reachable while your computer is on and both `serve.py` and `cloudflared` are running. For stronger protection you can also put Cloudflare Access (an email login) in front of the hostname.

Keep `.env` private. It holds your API keys and the password. The tunnel token is a secret too. If any of them leak, replace them.

### Troubleshooting

- **502 Bad Gateway from Cloudflare**: the tunnel is up but cannot reach the app. Check that `python serve.py` is running, that `curl -I http://127.0.0.1:8080` answers (a `401` means the app is up and asking for the password), and that the tunnel points to `http://127.0.0.1:8080` rather than `localhost`.
- **`cloudflared: command not found`**: a terminal opened before the install does not see it. Close and reopen that program, or use a command prompt opened after installing.
- **A login prompt every time**: the browser asks for the password again after it is closed. That is normal for this kind of login.

## Project structure

```
meal-planner/
├── run.py                  Development server (debug optional)
├── serve.py                Production server (Waitress), used with a tunnel
├── LICENSE                 MIT license
├── CHANGELOG.md            Release notes
├── requirements.txt        Runtime dependencies
├── requirements-dev.txt    Adds pytest
├── .env.example            Template for API keys and settings (copy to .env)
├── meal_planner.db         Created on first run (git-ignored)
├── .github/workflows/      tests.yml runs pytest on GitHub
├── app/
│   ├── __init__.py         App factory (create_app), password, proxy setup, error pages
│   ├── config.py           Settings loaded from environment variables
│   ├── db.py               SQLite storage: saved recipes, meal plan, pantry, caches
│   ├── shopping.py         Merges ingredients and converts units for the shopping list
│   ├── nutrition.py        Estimates calories and macros for planned meals
│   ├── routes.py           Pages and JSON endpoints
│   ├── clients/
│   │   ├── themealdb.py       TheMealDB client + conversion to the internal recipe format
│   │   ├── spoonacular.py     Spoonacular client (search with diet and allergy filters)
│   │   ├── usda.py            USDA FoodData Central client (nutrients per 100 g)
│   │   └── openfoodfacts.py   Open Food Facts client (product by barcode)
│   ├── templates/          base.html, index.html, recipe.html, plan.html,
│   │                       shopping.html, nutrition.html, pantry.html, error.html
│   └── static/             css/style.css, js/main.js
└── tests/                  conftest.py plus client, route, saved-recipe, detail, plan,
                            shopping, USDA, nutrition, Spoonacular, Open Food Facts,
                            config, page and deployment tests
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
11. The Pantry page (`/pantry`) takes a typed barcode, looks the product up in Open Food Facts and stores it in the `pantry` table. Adding the same barcode again increases its count.

## Pantry rules

- Barcodes must be 8, 12, 13 or 14 digits (EAN-8, UPC-A, EAN-13, GTIN-14). Spaces are ignored.
- Open Food Facts is a crowd-sourced database, so some products are missing or have incomplete names. A barcode it doesn't know shows a "No product found" message.
- Product data comes from Open Food Facts (openfoodfacts.org) and is available under the Open Database License.

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

## Known limitations

- It is a single-user app with one shared password (or none), meant to run on your own computer. There are no separate accounts.
- The pantry is a separate list. It isn't used to adjust the shopping list.
- Shopping list merging and nutrition totals depend on free-text measures, so treat them as helpful estimates.
- Camera barcode scanning isn't supported. Barcodes are typed or pasted.
- Check each data provider's terms (especially Spoonacular's free plan) before showing their data to other people.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Search page and saved recipes |
| GET | `/recipes/<id>` | Detail page for a saved recipe |
| GET | `/plan?start=YYYY-MM-DD` | Weekly plan page (defaults to this week) |
| POST | `/plan/set` | Set or clear a slot; form fields `date`, `slot`, `saved_id` |
| GET | `/shopping?start=YYYY-MM-DD` | Shopping list for a week (defaults to this week) |
| GET | `/nutrition?start=YYYY-MM-DD` | Nutrition estimates for a week (defaults to this week) |
| GET | `/pantry` | Pantry page |
| POST | `/pantry/add` | Look up a barcode and add it to the pantry; form field `barcode` |
| POST | `/pantry/<id>/remove` | Remove a pantry item |
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
| Open Food Facts | None (send a User-Agent) | Barcode and pantry lookups | In use |

## Roadmap

- [x] Project skeleton, TheMealDB search, tests
- [x] SQLite storage for saved recipes
- [x] Recipe detail page
- [x] Weekly meal calendar
- [x] Shopping list with merged ingredients and unit conversion
- [x] USDA nutrition totals per meal and per day
- [x] Spoonacular search with diet and allergy filters (cached; the free daily quota is small)
- [x] Open Food Facts barcode lookup for a pantry
- [x] Polish and release (1.0.0)

## License

Released under the [MIT License](LICENSE).
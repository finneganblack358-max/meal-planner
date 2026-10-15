# Changelog

## 1.0.0 - 2026-10-14

First release.

- Recipe search with TheMealDB, and Spoonacular with diet and allergy filters
- Saved recipes and a recipe detail page
- Weekly meal plan (breakfast, lunch and dinner)
- Weekly shopping list with merged ingredients and unit conversion
- USDA nutrition estimates per meal and per day
- Open Food Facts barcode pantry
- Current-page navigation, footer with data credits, friendly error pages
- Debug mode is now off unless `FLASK_DEBUG=1` is set
- Publishing support: Waitress server (`serve.py`), optional site password,
  proxy header support for Cloudflare Tunnel, configurable database location
- MIT license, test suite and a GitHub Actions workflow
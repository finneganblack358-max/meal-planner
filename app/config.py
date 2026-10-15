import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    APP_VERSION = "1.0.0"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    THEMEALDB_API_KEY = os.getenv("THEMEALDB_API_KEY", "1")
    SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY", "")
    USDA_API_KEY = os.getenv("USDA_API_KEY", "DEMO_KEY")
    OPENFOODFACTS_USER_AGENT = os.getenv(
        "OPENFOODFACTS_USER_AGENT", "MealPlanner/1.0 (personal project)"
    )
    DATABASE = os.getenv("DATABASE_PATH") or os.path.join(BASE_DIR, "meal_planner.db")

    # Publishing settings (see README). An empty password means no login.
    APP_PASSWORD = os.getenv("APP_PASSWORD", "")
    BEHIND_PROXY = os.getenv("BEHIND_PROXY", "0") == "1"
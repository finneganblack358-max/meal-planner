import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    THEMEALDB_API_KEY = os.getenv("THEMEALDB_API_KEY", "1")
    SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY", "")
    USDA_API_KEY = os.getenv("USDA_API_KEY", "DEMO_KEY")
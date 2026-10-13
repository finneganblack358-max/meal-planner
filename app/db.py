import json
import sqlite3

from flask import current_app, g

SLOTS = ("breakfast", "lunch", "dinner")

SCHEMA = """
CREATE TABLE IF NOT EXISTS saved_recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    title TEXT NOT NULL,
    image TEXT,
    category TEXT,
    area TEXT,
    ingredients TEXT NOT NULL,
    steps TEXT NOT NULL,
    saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source, source_id)
);

CREATE TABLE IF NOT EXISTS meal_plan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_date TEXT NOT NULL,
    slot TEXT NOT NULL,
    saved_id INTEGER NOT NULL REFERENCES saved_recipes(id) ON DELETE CASCADE,
    UNIQUE (plan_date, slot)
);

CREATE TABLE IF NOT EXISTS nutrition_cache (
    name TEXT PRIMARY KEY,
    found INTEGER NOT NULL,
    calories REAL,
    protein REAL,
    carbs REAL,
    fat REAL
);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    get_db().executescript(SCHEMA)


def row_to_recipe(row):
    """Convert a database row back into the internal recipe format.

    saved_id is the database row id, used to remove the recipe later.
    """
    return {
        "saved_id": row["id"],
        "id": row["source_id"],
        "source": row["source"],
        "title": row["title"],
        "image": row["image"],
        "category": row["category"],
        "area": row["area"],
        "ingredients": json.loads(row["ingredients"]),
        "steps": json.loads(row["steps"]),
    }


def save_recipe(recipe):
    """Save a recipe. Returns (saved_recipe, created). Saving twice is harmless."""
    db = get_db()
    cursor = db.execute(
        """
        INSERT OR IGNORE INTO saved_recipes
            (source, source_id, title, image, category, area, ingredients, steps)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            recipe["source"],
            recipe["id"],
            recipe["title"],
            recipe["image"],
            recipe["category"],
            recipe["area"],
            json.dumps(recipe["ingredients"]),
            json.dumps(recipe["steps"]),
        ),
    )
    db.commit()
    row = db.execute(
        "SELECT * FROM saved_recipes WHERE source = ? AND source_id = ?",
        (recipe["source"], recipe["id"]),
    ).fetchone()
    return row_to_recipe(row), cursor.rowcount == 1


def list_saved():
    rows = get_db().execute(
        "SELECT * FROM saved_recipes ORDER BY saved_at DESC, id DESC"
    ).fetchall()
    return [row_to_recipe(row) for row in rows]


def get_saved(saved_id):
    row = get_db().execute(
        "SELECT * FROM saved_recipes WHERE id = ?", (saved_id,)
    ).fetchone()
    return row_to_recipe(row) if row else None


def delete_saved(saved_id):
    db = get_db()
    cursor = db.execute("DELETE FROM saved_recipes WHERE id = ?", (saved_id,))
    db.commit()
    return cursor.rowcount == 1


def set_meal(plan_date, slot, saved_id):
    """Put a saved recipe in a slot, replacing whatever was there."""
    db = get_db()
    db.execute(
        """
        INSERT INTO meal_plan (plan_date, slot, saved_id) VALUES (?, ?, ?)
        ON CONFLICT (plan_date, slot) DO UPDATE SET saved_id = excluded.saved_id
        """,
        (plan_date, slot, saved_id),
    )
    db.commit()


def clear_meal(plan_date, slot):
    db = get_db()
    db.execute(
        "DELETE FROM meal_plan WHERE plan_date = ? AND slot = ?", (plan_date, slot)
    )
    db.commit()


def get_plan(start_date, end_date):
    """Return {(date, slot): {"saved_id": int, "title": str}} for a date range."""
    rows = get_db().execute(
        """
        SELECT meal_plan.plan_date, meal_plan.slot,
               saved_recipes.id AS saved_id, saved_recipes.title
        FROM meal_plan
        JOIN saved_recipes ON saved_recipes.id = meal_plan.saved_id
        WHERE meal_plan.plan_date BETWEEN ? AND ?
        """,
        (start_date, end_date),
    ).fetchall()
    return {
        (row["plan_date"], row["slot"]): {
            "saved_id": row["saved_id"],
            "title": row["title"],
        }
        for row in rows
    }
    
def get_planned_ingredients(start_date, end_date):
    """Return every ingredient of every meal planned in a date range."""
    rows = get_db().execute(
        """
        SELECT saved_recipes.ingredients
        FROM meal_plan
        JOIN saved_recipes ON saved_recipes.id = meal_plan.saved_id
        WHERE meal_plan.plan_date BETWEEN ? AND ?
        """,
        (start_date, end_date),
    ).fetchall()
    ingredients = []
    for row in rows:
        ingredients.extend(json.loads(row["ingredients"]))
    return ingredients

def get_nutrition(name):
    """Return None if never looked up, else {"values": {...} or None}."""
    row = get_db().execute(
        "SELECT * FROM nutrition_cache WHERE name = ?", (name,)
    ).fetchone()
    if row is None:
        return None
    if not row["found"]:
        return {"values": None}
    return {
        "values": {
            "calories": row["calories"],
            "protein": row["protein"],
            "carbs": row["carbs"],
            "fat": row["fat"],
        }
    }


def save_nutrition(name, values):
    """Remember a lookup. values=None records that USDA had no match."""
    db = get_db()
    if values is None:
        db.execute(
            "INSERT OR REPLACE INTO nutrition_cache (name, found) VALUES (?, 0)",
            (name,),
        )
    else:
        db.execute(
            """
            INSERT OR REPLACE INTO nutrition_cache
                (name, found, calories, protein, carbs, fat)
            VALUES (?, 1, ?, ?, ?, ?)
            """,
            (name, values["calories"], values["protein"], values["carbs"], values["fat"]),
        )
    db.commit()


def get_planned_meals(start_date, end_date):
    """Return planned meals with their ingredients, in date and slot order."""
    rows = get_db().execute(
        """
        SELECT meal_plan.plan_date, meal_plan.slot,
               saved_recipes.id AS saved_id, saved_recipes.title,
               saved_recipes.ingredients
        FROM meal_plan
        JOIN saved_recipes ON saved_recipes.id = meal_plan.saved_id
        WHERE meal_plan.plan_date BETWEEN ? AND ?
        """,
        (start_date, end_date),
    ).fetchall()
    meals = [
        {
            "plan_date": row["plan_date"],
            "slot": row["slot"],
            "saved_id": row["saved_id"],
            "title": row["title"],
            "ingredients": json.loads(row["ingredients"]),
        }
        for row in rows
    ]
    meals.sort(key=lambda meal: (meal["plan_date"], SLOTS.index(meal["slot"])))
    return meals
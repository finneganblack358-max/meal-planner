import json
import sqlite3

from flask import current_app, g

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
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
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


def delete_saved(saved_id):
    db = get_db()
    cursor = db.execute("DELETE FROM saved_recipes WHERE id = ?", (saved_id,))
    db.commit()
    return cursor.rowcount == 1

def get_saved(saved_id):
    row = get_db().execute(
        "SELECT * FROM saved_recipes WHERE id = ?", (saved_id,)
    ).fetchone()
    return row_to_recipe(row) if row else None
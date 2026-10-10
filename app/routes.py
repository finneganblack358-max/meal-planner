from flask import Blueprint, abort, current_app, jsonify, render_template, request

from . import db
from .clients.themealdb import MealDBError, TheMealDBClient

bp = Blueprint("main", __name__)


def get_client():
    return TheMealDBClient(api_key=current_app.config["THEMEALDB_API_KEY"])


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/recipes/<int:saved_id>")
def recipe_detail(saved_id):
    recipe = db.get_saved(saved_id)
    if recipe is None:
        abort(404)
    return render_template("recipe.html", recipe=recipe)


@bp.route("/api/recipes/search")
def search_recipes():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Enter a search term, for example ?q=chicken."}), 400

    try:
        recipes = get_client().search(query)
    except MealDBError:
        return jsonify({"error": "The recipe service is unavailable. Try again in a minute."}), 502

    return jsonify({"results": recipes})


@bp.route("/api/saved", methods=["GET"])
def list_saved():
    return jsonify({"results": db.list_saved()})


@bp.route("/api/saved", methods=["POST"])
def add_saved():
    data = request.get_json(silent=True) or {}
    meal_id = str(data.get("id", "")).strip()
    if not meal_id:
        return jsonify({"error": "Send the recipe id, for example {\"id\": \"52771\"}."}), 400

    try:
        recipe = get_client().get_by_id(meal_id)
    except MealDBError:
        return jsonify({"error": "The recipe service is unavailable. Try again in a minute."}), 502

    if recipe is None:
        return jsonify({"error": "Recipe not found."}), 404

    saved, created = db.save_recipe(recipe)
    return jsonify(saved), 201 if created else 200


@bp.route("/api/saved/<int:saved_id>", methods=["DELETE"])
def remove_saved(saved_id):
    if not db.delete_saved(saved_id):
        return jsonify({"error": "Saved recipe not found."}), 404
    return "", 204
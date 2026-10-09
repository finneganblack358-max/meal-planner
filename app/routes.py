from flask import Blueprint, current_app, jsonify, render_template, request

from .clients.themealdb import MealDBError, TheMealDBClient

bp = Blueprint("main", __name__)


def get_client():
    return TheMealDBClient(api_key=current_app.config["THEMEALDB_API_KEY"])


@bp.route("/")
def index():
    return render_template("index.html")


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
from datetime import date, timedelta

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from . import db
from .clients.themealdb import MealDBError, TheMealDBClient
from .clients.usda import USDAClient, USDAError
from .nutrition import SERVINGS, build_week_nutrition
from .shopping import build_shopping_list

bp = Blueprint("main", __name__)


def get_client():
    return TheMealDBClient(api_key=current_app.config["THEMEALDB_API_KEY"])


def get_usda_client():
    return USDAClient(api_key=current_app.config["USDA_API_KEY"])


def parse_date(text):
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        return None


def monday_of(day):
    return day - timedelta(days=day.weekday())


def week_from_request():
    """Return (start, days) for the ?start= week, defaulting to this week."""
    start = monday_of(parse_date(request.args.get("start")) or date.today())
    return start, [start + timedelta(days=i) for i in range(7)]


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/recipes/<int:saved_id>")
def recipe_detail(saved_id):
    recipe = db.get_saved(saved_id)
    if recipe is None:
        abort(404)
    return render_template("recipe.html", recipe=recipe)


@bp.route("/plan")
def plan():
    start, days = week_from_request()
    meals = db.get_plan(days[0].isoformat(), days[-1].isoformat())
    return render_template(
        "plan.html",
        days=days,
        slots=db.SLOTS,
        meals=meals,
        recipes=db.list_saved(),
        today=date.today(),
        prev_start=start - timedelta(days=7),
        next_start=start + timedelta(days=7),
    )


@bp.route("/plan/set", methods=["POST"])
def plan_set():
    plan_date = parse_date(request.form.get("date"))
    slot = request.form.get("slot")
    if plan_date is None or slot not in db.SLOTS:
        abort(400)

    saved_id = request.form.get("saved_id", "")
    if saved_id == "":
        db.clear_meal(plan_date.isoformat(), slot)
    else:
        if not saved_id.isdigit() or db.get_saved(int(saved_id)) is None:
            abort(400)
        db.set_meal(plan_date.isoformat(), slot, int(saved_id))

    return redirect(url_for("main.plan", start=monday_of(plan_date).isoformat()))


@bp.route("/shopping")
def shopping_list():
    start, days = week_from_request()
    ingredients = db.get_planned_ingredients(days[0].isoformat(), days[-1].isoformat())
    return render_template(
        "shopping.html",
        items=build_shopping_list(ingredients),
        days=days,
        prev_start=start - timedelta(days=7),
        next_start=start + timedelta(days=7),
    )

@bp.route("/nutrition")
def nutrition_page():
    start, days = week_from_request()
    meals = db.get_planned_meals(days[0].isoformat(), days[-1].isoformat())

    week, error = {}, None
    try:
        week = build_week_nutrition(meals, get_usda_client())
    except USDAError as exc:
        current_app.logger.warning("USDA lookup failed: %s", exc)
        error = (
            "Could not get data from USDA FoodData Central. The service may be down "
            "or your API key's request limit may be used up. Anything already looked "
            "up is saved, so try again in a few minutes."
        )

    page = render_template(
        "nutrition.html",
        days=days,
        week=week,
        error=error,
        servings=SERVINGS,
        prev_start=start - timedelta(days=7),
        next_start=start + timedelta(days=7),
    )
    return page, (502 if error else 200)

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
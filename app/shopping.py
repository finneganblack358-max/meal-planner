"""Turn planned recipe ingredients into one merged shopping list.

TheMealDB measures are free text ("1/4 cup", "200g", "to taste"). Amounts we
can read are added together, converting between units of the same kind
(volume or weight). Anything we can't read is kept as a note.
"""

import re
from fractions import Fraction

TSP = 4.92892  # millilitres
TBSP = 3 * TSP
CUP = 16 * TBSP
OZ = 28.3495  # grams
LB = 16 * OZ

# unit name -> (kind, size in ml or g, system)
UNITS = {}


def _add_units(names, kind, size, system):
    for name in names.split():
        UNITS[name] = (kind, size, system)


_add_units("tsp tsps teaspoon teaspoons", "volume", TSP, "us")
_add_units("tbsp tbsps tbs tblsp tablespoon tablespoons", "volume", TBSP, "us")
_add_units("cup cups", "volume", CUP, "us")
_add_units("ml milliliter milliliters millilitre millilitres", "volume", 1, "metric")
_add_units("l liter liters litre litres", "volume", 1000, "metric")
_add_units("oz ounce ounces", "weight", OZ, "us")
_add_units("lb lbs pound pounds", "weight", LB, "us")
_add_units("g gram grams", "weight", 1, "metric")
_add_units("kg kilogram kilograms", "weight", 1000, "metric")

# How to display a total, largest unit first: (label, size, minimum).
# A unit is used once the total reaches `minimum` of it.
DISPLAY = {
    ("volume", "us"): [("cup", CUP, 0.25), ("tbsp", TBSP, 1), ("tsp", TSP, 0)],
    ("volume", "metric"): [("l", 1000, 1), ("ml", 1, 0)],
    ("weight", "us"): [("lb", LB, 1), ("oz", OZ, 0)],
    ("weight", "metric"): [("kg", 1000, 1), ("g", 1, 0)],
}

# A number (mixed "1 1/2", fraction "1/4" or decimal "0.5") then an optional unit word.
MEASURE_RE = re.compile(r"\s*(\d+\s+\d+/\d+|\d+/\d+|\d*\.?\d+)\s*([^\W\d_]+)?")


def parse_measure(measure):
    """Return (amount, unit) for a measure like '1/4 cup', or None if unreadable."""
    match = MEASURE_RE.match(measure)
    if not match:
        return None
    if re.match(r"\s*[-–/]", measure[match.end():]):
        return None  # a range such as "3-4 cloves": don't guess
    try:
        amount = sum(Fraction(part) for part in match.group(1).split())
    except (ValueError, ZeroDivisionError):
        return None
    return float(amount), match.group(2) or ""


def add_amount(totals, amount, unit):
    info = UNITS.get(unit.lower())
    if info:
        kind, size, system = info
        entry = totals.setdefault(kind, {"total": 0.0, "system": system})
        entry["total"] += amount * size
    else:
        # Unknown units (clove, large, ...) only merge with the same unit.
        key = ("count", unit.lower().rstrip("s"))
        entry = totals.setdefault(key, {"total": 0.0, "unit": unit})
        entry["total"] += amount


def format_number(value):
    return f"{value:.2f}".rstrip("0").rstrip(".")


def format_total(key, entry):
    if key in ("volume", "weight"):
        for label, size, minimum in DISPLAY[(key, entry["system"])]:
            if entry["total"] + 1e-6 >= size * minimum:
                return f"{format_number(entry['total'] / size)} {label}"
    return f"{format_number(entry['total'])} {entry['unit']}".strip()


def build_shopping_list(ingredients):
    """Merge [{name, measure}, ...] into [{name, quantity}, ...] sorted by name."""
    items = {}
    for ingredient in ingredients:
        name = (ingredient.get("name") or "").strip()
        if not name:
            continue
        item = items.setdefault(name.lower(), {"name": name, "totals": {}, "notes": []})

        measure = (ingredient.get("measure") or "").strip()
        if not measure:
            continue
        parsed = parse_measure(measure)
        if parsed is None:
            if measure not in item["notes"]:
                item["notes"].append(measure)
        else:
            add_amount(item["totals"], *parsed)

    result = []
    for key in sorted(items):
        item = items[key]
        parts = [format_total(k, e) for k, e in item["totals"].items()] + item["notes"]
        result.append({"name": item["name"], "quantity": " + ".join(parts)})
    return result
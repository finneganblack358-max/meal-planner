"""Open Food Facts client.

Looks up one product by barcode. No API key is needed, but Open Food Facts
asks every app to send a User-Agent with its name, version and a contact.
API docs: https://openfoodfacts.github.io/openfoodfacts-server/api/
"""

import requests

BASE_URL = "https://world.openfoodfacts.org/api/v2/product"
TIMEOUT_SECONDS = 10
FIELDS = "product_name,brands,quantity,image_thumb_url"


class OpenFoodFactsError(Exception):
    """Raised when Open Food Facts can't be reached or returns bad data."""


class OpenFoodFactsClient:
    def __init__(self, user_agent="MealPlanner/1.0 (personal project)", session=None):
        self.user_agent = user_agent
        self.session = session or requests.Session()

    def get_product(self, barcode):
        """Return {"barcode", "name", "brands", "quantity", "image"} or None."""
        try:
            response = self.session.get(
                f"{BASE_URL}/{barcode}.json",
                params={"fields": FIELDS},
                headers={"User-Agent": self.user_agent},
                timeout=TIMEOUT_SECONDS,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise OpenFoodFactsError(
                f"Open Food Facts request failed ({type(exc).__name__})"
            ) from exc
        return normalize_product(barcode, data)


def normalize_product(barcode, data):
    """Convert an API response into a small product dict, or None if not found."""
    if data.get("status") != 1:
        return None
    product = data.get("product") or {}
    if not product:
        return None

    name = (product.get("product_name") or "").strip()
    return {
        "barcode": barcode,
        "name": name or f"Product {barcode}",
        "brands": (product.get("brands") or "").strip(),
        "quantity": (product.get("quantity") or "").strip(),
        "image": product.get("image_thumb_url") or None,
    }
import pytest
import requests

from app import routes
from app.clients.openfoodfacts import (
    OpenFoodFactsClient,
    OpenFoodFactsError,
    normalize_product,
)

FOUND = {
    "code": "3017624010701",
    "status": 1,
    "status_verbose": "product found",
    "product": {
        "product_name": "Nutella",
        "brands": "Ferrero",
        "quantity": "400 g",
        "image_thumb_url": "https://images.openfoodfacts.org/nutella.thumb.jpg",
    },
}

MISSING = {"code": "32562641919", "status": 0, "status_verbose": "product not found"}

PRODUCT = {
    "barcode": "3017624010701",
    "name": "Nutella",
    "brands": "Ferrero",
    "quantity": "400 g",
    "image": None,
}


class FakeResponse:
    def __init__(self, data=None, status_code=200):
        self.data = data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code), response=self)

    def json(self):
        return self.data


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def get(self, url, params, headers, timeout):
        self.calls.append((url, params, headers))
        if self.error:
            raise self.error
        return self.response


class FakeOFF:
    def __init__(self):
        self.products = {PRODUCT["barcode"]: PRODUCT}
        self.calls = []

    def get_product(self, barcode):
        self.calls.append(barcode)
        return self.products.get(barcode)


class BrokenOFF:
    def get_product(self, barcode):
        raise OpenFoodFactsError("boom")


@pytest.fixture
def fake_off(monkeypatch):
    fake = FakeOFF()
    monkeypatch.setattr(routes, "get_openfoodfacts_client", lambda: fake)
    return fake


def add_to_pantry(client, barcode="3017624010701"):
    return client.post("/pantry/add", data={"barcode": barcode})


def test_normalize_product_maps_fields():
    assert normalize_product("3017624010701", FOUND) == {
        "barcode": "3017624010701",
        "name": "Nutella",
        "brands": "Ferrero",
        "quantity": "400 g",
        "image": "https://images.openfoodfacts.org/nutella.thumb.jpg",
    }


def test_normalize_product_not_found_is_none():
    assert normalize_product("32562641919", MISSING) is None


def test_normalize_product_empty_product_is_none():
    assert normalize_product("123", {"status": 1, "product": {}}) is None


def test_normalize_product_falls_back_to_barcode_name():
    product = normalize_product("123", {"status": 1, "product": {"brands": "X"}})
    assert product["name"] == "Product 123"


def test_client_sends_user_agent_and_fields():
    session = FakeSession(FakeResponse(FOUND))
    client = OpenFoodFactsClient(user_agent="Test/1.0 (me@example.com)", session=session)
    product = client.get_product("3017624010701")
    assert product["name"] == "Nutella"

    url, params, headers = session.calls[0]
    assert url.endswith("/3017624010701.json")
    assert "product_name" in params["fields"]
    assert headers["User-Agent"] == "Test/1.0 (me@example.com)"


def test_client_treats_404_as_not_found():
    session = FakeSession(FakeResponse(MISSING, status_code=404))
    assert OpenFoodFactsClient(session=session).get_product("32562641919") is None


def test_client_failure_raises_error():
    session = FakeSession(error=requests.ConnectionError("boom"))
    with pytest.raises(OpenFoodFactsError):
        OpenFoodFactsClient(session=session).get_product("3017624010701")


def test_pantry_page_starts_empty(client):
    page = client.get("/pantry")
    assert page.status_code == 200
    assert b"Your pantry is empty" in page.data


def test_add_product_shows_in_pantry(client, fake_off):
    response = add_to_pantry(client)
    assert response.status_code == 302

    page = client.get("/pantry")
    assert b"Nutella" in page.data
    assert b"Ferrero" in page.data


def test_adding_the_same_barcode_twice_counts_copies(client, fake_off):
    add_to_pantry(client)
    add_to_pantry(client)

    page = client.get("/pantry")
    assert b"2 in pantry" in page.data
    assert page.data.count(b"Nutella") == 1


def test_barcode_whitespace_is_cleaned(client, fake_off):
    response = add_to_pantry(client, " 3017624010701 ")
    assert response.status_code == 302
    assert fake_off.calls == ["3017624010701"]


def test_invalid_barcode_is_rejected(client, fake_off):
    response = add_to_pantry(client, "abc")
    assert response.status_code == 400
    assert b"8, 12, 13 or 14 digits" in response.data
    assert fake_off.calls == []


def test_unknown_product_is_a_404_and_not_added(client, fake_off):
    response = add_to_pantry(client, "99999999")
    assert response.status_code == 404
    assert b"No product found" in response.data
    assert b"Your pantry is empty" in client.get("/pantry").data


def test_service_failure_shows_a_message(client, monkeypatch):
    monkeypatch.setattr(routes, "get_openfoodfacts_client", lambda: BrokenOFF())
    response = add_to_pantry(client)
    assert response.status_code == 502
    assert b"Could not reach" in response.data


def test_remove_pantry_item(client, fake_off):
    add_to_pantry(client)
    assert client.post("/pantry/1/remove").status_code == 302
    assert b"Your pantry is empty" in client.get("/pantry").data


def test_remove_unknown_pantry_item_is_404(client):
    assert client.post("/pantry/999/remove").status_code == 404
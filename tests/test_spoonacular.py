import pytest
import requests

from app import routes
from app.clients.spoonacular import SpoonacularClient, SpoonacularError, normalize_recipe

RAW = {
    "id": 716429,
    "title": "Pasta with Garlic",
    "image": "https://img.spoonacular.com/recipes/716429-312x231.jpg",
    "cuisines": ["Italian"],
    "dishTypes": ["lunch", "main course"],
    "extendedIngredients": [
        {"name": "pasta", "amount": 1.5, "unit": "cups"},
        {"name": "salt", "amount": 0, "unit": ""},
        {"name": "garlic", "amount": 2, "unit": "cloves"},
    ],
    "analyzedInstructions": [
        {"name": "", "steps": [{"number": 1, "step": "Boil pasta."}, {"number": 2, "step": "Add garlic."}]}
    ],
}


class FakeResponse:
    status_code = 200

    def __init__(self, data=None, status_code=200):
        self.data = data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code), response=self)

    def json(self):
        return self.data


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append((url, params))
        return self.response


class FakeSpoon:
    def __init__(self):
        self.calls = []
        self.intolerances = []

    def search(self, query, diet=None, intolerances=""):
        self.calls.append((query, diet))
        self.intolerances.append(intolerances)
        return [normalize_recipe(RAW)]


class BrokenSpoon:
    def search(self, query, diet=None, intolerances=""):
        raise SpoonacularError("boom", 402)


@pytest.fixture
def configured(client):
    client.application.config["SPOONACULAR_API_KEY"] = "test-key"
    return client


def test_normalize_recipe_maps_fields():
    recipe = normalize_recipe(RAW)
    assert recipe["id"] == "716429"
    assert recipe["source"] == "spoonacular"
    assert recipe["title"] == "Pasta with Garlic"
    assert recipe["area"] == "Italian"
    assert recipe["category"] == "Lunch"
    assert recipe["ingredients"] == [
        {"name": "pasta", "measure": "1.5 cups"},
        {"name": "salt", "measure": ""},
        {"name": "garlic", "measure": "2 cloves"},
    ]
    assert recipe["steps"] == ["Boil pasta.", "Add garlic."]


def test_normalize_recipe_handles_missing_parts():
    recipe = normalize_recipe({"id": 1, "title": "Plain"})
    assert recipe["ingredients"] == []
    assert recipe["steps"] == []
    assert recipe["area"] is None
    assert recipe["category"] is None


def test_client_search_sends_key_diet_and_info_flags():
    session = FakeSession(FakeResponse({"results": [RAW]}))
    recipes = SpoonacularClient(api_key="KEY", session=session).search("pasta", "vegan")
    assert recipes[0]["title"] == "Pasta with Garlic"

    url, params = session.calls[0]
    assert url.endswith("/recipes/complexSearch")
    assert params["apiKey"] == "KEY"
    assert params["query"] == "pasta"
    assert params["diet"] == "vegan"
    assert params["addRecipeInformation"] == "true"


def test_client_search_omits_filters_when_blank():
    session = FakeSession(FakeResponse({"results": []}))
    SpoonacularClient(api_key="KEY", session=session).search("pasta", "", "")
    params = session.calls[0][1]
    assert "diet" not in params
    assert "intolerances" not in params


def test_client_failure_raises_error_with_status():
    session = FakeSession(FakeResponse(status_code=402))
    with pytest.raises(SpoonacularError) as info:
        SpoonacularClient(api_key="KEY", session=session).search("pasta")
    assert info.value.status == 402


def test_search_without_key_returns_503(client):
    client.application.config["SPOONACULAR_API_KEY"] = ""
    response = client.get("/api/recipes/search?q=pasta&source=spoonacular")
    assert response.status_code == 503
    assert "SPOONACULAR_API_KEY" in response.get_json()["error"]


def test_search_returns_results_and_passes_diet(configured, monkeypatch):
    fake = FakeSpoon()
    monkeypatch.setattr(routes, "get_spoonacular_client", lambda: fake)

    response = configured.get("/api/recipes/search?q=pasta&source=spoonacular&diet=vegan")
    assert response.status_code == 200
    assert response.get_json()["results"][0]["title"] == "Pasta with Garlic"
    assert fake.calls == [("pasta", "vegan")]


def test_repeat_search_uses_the_cache(configured, monkeypatch):
    fake = FakeSpoon()
    monkeypatch.setattr(routes, "get_spoonacular_client", lambda: fake)

    configured.get("/api/recipes/search?q=pasta&source=spoonacular")
    configured.get("/api/recipes/search?q=pasta&source=spoonacular")
    assert len(fake.calls) == 1


def test_unknown_diet_is_rejected(configured, monkeypatch):
    fake = FakeSpoon()
    monkeypatch.setattr(routes, "get_spoonacular_client", lambda: fake)

    response = configured.get("/api/recipes/search?q=pasta&source=spoonacular&diet=bogus")
    assert response.status_code == 400
    assert fake.calls == []


def test_quota_error_gets_a_clear_message(configured, monkeypatch):
    monkeypatch.setattr(routes, "get_spoonacular_client", lambda: BrokenSpoon())

    response = configured.get("/api/recipes/search?q=pasta&source=spoonacular")
    assert response.status_code == 502
    assert "daily limit" in response.get_json()["error"]


def test_unknown_source_is_rejected(client):
    assert client.get("/api/recipes/search?q=pasta&source=bogus").status_code == 400


def test_saving_a_spoonacular_recipe_uses_the_cache(configured, monkeypatch):
    fake = FakeSpoon()
    monkeypatch.setattr(routes, "get_spoonacular_client", lambda: fake)

    configured.get("/api/recipes/search?q=pasta&source=spoonacular")
    response = configured.post(
        "/api/saved", json={"id": "716429", "source": "spoonacular"}
    )
    assert response.status_code == 201
    assert len(fake.calls) == 1  # saving made no extra API call

    saved = configured.get("/api/saved").get_json()["results"]
    assert saved[0]["source"] == "spoonacular"
    assert saved[0]["title"] == "Pasta with Garlic"


def test_saving_a_recipe_that_was_never_searched_is_404(configured):
    response = configured.post(
        "/api/saved", json={"id": "716429", "source": "spoonacular"}
    )
    assert response.status_code == 404


def test_client_search_sends_intolerances():
    session = FakeSession(FakeResponse({"results": []}))
    SpoonacularClient(api_key="KEY", session=session).search("pasta", "", "Dairy,Egg")
    assert session.calls[0][1]["intolerances"] == "Dairy,Egg"


def test_search_passes_allergy_filter(configured, monkeypatch):
    fake = FakeSpoon()
    monkeypatch.setattr(routes, "get_spoonacular_client", lambda: fake)

    response = configured.get(
        "/api/recipes/search?q=pasta&source=spoonacular&intolerances=Egg,Dairy"
    )
    assert response.status_code == 200
    assert fake.intolerances == ["Dairy,Egg"]  # sorted, so cache keys are consistent


def test_unknown_allergy_is_rejected_and_filters_are_cached_separately(
    configured, monkeypatch
):
    fake = FakeSpoon()
    monkeypatch.setattr(routes, "get_spoonacular_client", lambda: fake)

    bad = configured.get("/api/recipes/search?q=pasta&source=spoonacular&intolerances=Bogus")
    assert bad.status_code == 400
    assert fake.calls == []

    configured.get("/api/recipes/search?q=pasta&source=spoonacular")
    configured.get("/api/recipes/search?q=pasta&source=spoonacular&intolerances=Soy")
    assert len(fake.calls) == 2  # different filters are different searches
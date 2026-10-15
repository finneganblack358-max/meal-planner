import base64

from app import create_app
from app.config import Config


def basic(password, user="me"):
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_no_password_set_means_the_site_is_open(client):
    assert client.get("/").status_code == 200


def test_password_is_required_when_set(client):
    client.application.config["APP_PASSWORD"] = "secret"
    response = client.get("/")
    assert response.status_code == 401
    assert "Basic" in response.headers["WWW-Authenticate"]


def test_wrong_password_is_rejected(client):
    client.application.config["APP_PASSWORD"] = "secret"
    assert client.get("/", headers=basic("nope")).status_code == 401


def test_correct_password_is_accepted(client):
    client.application.config["APP_PASSWORD"] = "secret"
    assert client.get("/", headers=basic("secret")).status_code == 200


def test_password_protects_the_api_forms_and_static_files(client):
    client.application.config["APP_PASSWORD"] = "secret"
    assert client.get("/api/saved").status_code == 401
    assert client.post("/pantry/add", data={"barcode": "3017624010701"}).status_code == 401
    assert client.get("/static/css/style.css").status_code == 401
    assert client.get("/static/css/style.css", headers=basic("secret")).status_code == 200


def test_proxy_headers_are_trusted_only_when_enabled(tmp_path):
    from flask import request

    def build(behind_proxy):
        class Cfg(Config):
            TESTING = True
            DATABASE = str(tmp_path / f"proxy-{behind_proxy}.db")
            APP_PASSWORD = ""
            BEHIND_PROXY = behind_proxy

        app = create_app(Cfg)
        app.add_url_rule("/_scheme", "scheme", lambda: request.scheme)
        return app.test_client()

    headers = {"X-Forwarded-Proto": "https"}
    assert build(True).get("/_scheme", headers=headers).get_data(as_text=True) == "https"
    assert build(False).get("/_scheme", headers=headers).get_data(as_text=True) == "http"


def test_database_folder_is_created(tmp_path):
    class Cfg(Config):
        TESTING = True
        DATABASE = str(tmp_path / "new-folder" / "meal_planner.db")
        APP_PASSWORD = ""

    create_app(Cfg)
    assert (tmp_path / "new-folder" / "meal_planner.db").exists()
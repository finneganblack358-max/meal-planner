import pytest


@pytest.mark.parametrize("path", ["/", "/plan", "/shopping", "/nutrition", "/pantry"])
def test_every_page_loads(client, path):
    assert client.get(path).status_code == 200


def test_unknown_page_shows_a_friendly_404(client):
    response = client.get("/no-such-page")
    assert response.status_code == 404
    assert b"Page not found" in response.data
    assert b"Back to recipes" in response.data


def test_footer_shows_version_license_and_data_credits(client):
    page = client.get("/").data
    version = client.application.config["APP_VERSION"]
    assert f"v{version}".encode() in page
    assert b"MIT License" in page
    assert b"Open Food Facts" in page


def test_nav_marks_the_current_page(client):
    page = client.get("/plan").data
    assert b'<a href="/plan" aria-current="page">Plan</a>' in page
    assert b'aria-current="page">Recipes</a>' not in page
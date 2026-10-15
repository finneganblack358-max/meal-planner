import pytest

from app import create_app
from app.config import Config


@pytest.fixture
def client(tmp_path):
    class TestConfig(Config):
        TESTING = True
        DATABASE = str(tmp_path / "test.db")
        # Never inherit these from your real .env, or tests would hit a login.
        APP_PASSWORD = ""
        BEHIND_PROXY = False

    return create_app(TestConfig).test_client()
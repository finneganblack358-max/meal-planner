import pytest

from app import create_app
from app.config import Config


@pytest.fixture
def client(tmp_path):
    class TestConfig(Config):
        TESTING = True
        DATABASE = str(tmp_path / "test.db")

    return create_app(TestConfig).test_client()
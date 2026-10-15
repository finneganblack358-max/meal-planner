def test_config_has_every_setting_the_routes_use(client):
    config = client.application.config
    for key in (
        "APP_VERSION",
        "THEMEALDB_API_KEY",
        "SPOONACULAR_API_KEY",
        "USDA_API_KEY",
        "OPENFOODFACTS_USER_AGENT",
        "DATABASE",
        "APP_PASSWORD",
        "BEHIND_PROXY",
    ):
        assert key in config

    assert config["OPENFOODFACTS_USER_AGENT"]  # never empty
from app.core.config import Settings


def test_settings_default_values() -> None:
    settings = Settings()
    assert settings.APP_NAME == "AstroAPI"
    assert settings.APP_ENV == "development"
    assert settings.DEBUG is True
    assert settings.LOG_LEVEL == "INFO"


def test_cors_origins_parsing() -> None:
    # Test JSON list string
    settings_json = Settings(
        CORS_ORIGINS='["http://localhost:3000", "http://localhost:8000"]'  # type: ignore[arg-type]
    )
    assert settings_json.CORS_ORIGINS == [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # Test comma-separated string
    settings_comma = Settings(
        CORS_ORIGINS="http://localhost:3000, http://localhost:8000"  # type: ignore[arg-type]
    )
    assert settings_comma.CORS_ORIGINS == [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # Test list input
    settings_list = Settings(
        CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]
    )
    assert settings_list.CORS_ORIGINS == [
        "http://localhost:3000",
        "http://localhost:8000",
    ]


def test_database_url_property() -> None:
    settings = Settings(
        POSTGRES_USER="test_user",
        POSTGRES_PASSWORD="test_password",
        POSTGRES_HOST="test_host",
        POSTGRES_PORT=9999,
        POSTGRES_DB="test_db",
    )
    assert (
        settings.database_url
        == "postgresql+asyncpg://test_user:test_password@test_host:9999/test_db"
    )


def test_redis_url_property() -> None:
    settings_no_pwd = Settings(
        REDIS_HOST="redis_host",
        REDIS_PORT=1234,
        REDIS_DB=2,
        REDIS_PASSWORD=None,
    )
    assert settings_no_pwd.redis_url == "redis://redis_host:1234/2"

    settings_pwd = Settings(
        REDIS_HOST="redis_host",
        REDIS_PORT=1234,
        REDIS_DB=2,
        REDIS_PASSWORD="password123",
    )
    assert settings_pwd.redis_url == "redis://:password123@redis_host:1234/2"

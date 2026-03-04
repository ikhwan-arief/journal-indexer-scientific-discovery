from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Scientific Discovery API"
    api_prefix: str = "/api/v1"
    secret_key: str = "change-this-in-production"
    access_token_expire_minutes: int = 60 * 8
    sqlite_path: str = "data/journal_indexer.db"
    cors_origins: list[str] = ["http://127.0.0.1:8080", "http://localhost:8080"]
    default_admin_username: str = "admin"
    default_admin_password: str = "admin123"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()

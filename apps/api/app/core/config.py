from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://gowild:gowild@localhost:5432/gowild"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    schedule_version: str = "unset"


settings = Settings()

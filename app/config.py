from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://ajaia:ajaia@localhost:5432/ajaia"
    session_secret: str = "dev-only-secret"
    max_upload_bytes: int = 2 * 1024 * 1024


settings = Settings()
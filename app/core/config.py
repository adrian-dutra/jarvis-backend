from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(validation_alias="APP_NAME")
    app_env: str = Field(validation_alias="APP_ENV")
    debug: bool = Field(validation_alias="DEBUG")

    postgres_db: str = Field(validation_alias="POSTGRES_DB")
    postgres_user: str = Field(validation_alias="POSTGRES_USER")
    postgres_password: str = Field(validation_alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(validation_alias="POSTGRES_PORT")

    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")

    gemma_base_url: str = Field(validation_alias="GEMMA_BASE_URL")
    gemma_model: str = Field(validation_alias="GEMMA_MODEL")
    gemma_api_key: str = Field(validation_alias="GEMMA_API_KEY")

    upload_dir: str = Field(validation_alias="UPLOAD_DIR")
    chroma_dir: str = Field(validation_alias="CHROMA_DIR")
    timezone: str = Field(default="America/Campo_Grande", validation_alias="TIMEZONE")
    use_local_dataset: bool = Field(default=False, validation_alias="USE_LOCAL_DATASET")
    local_dataset_path: str = Field(default="data", validation_alias="LOCAL_DATASET_PATH")

    model_config = SettingsConfigDict(
        env_file=(".env", "env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str) and value.lower() in {"release", "prod", "production"}:
            return False
        return value

    @model_validator(mode="after")
    def build_database_url(self):
        if not self.database_url:
            host = self.postgres_host
            port = self.postgres_port

            if host == "db" and Path("/.dockerenv").exists():
                port = 5432
            elif host == "db":
                host = "localhost"
                port = 5433

            self.database_url = (
                f"postgresql://{self.postgres_user}:{self.postgres_password}"
                f"@{host}:{port}/{self.postgres_db}"
            )

        if Path("/.dockerenv").exists():
            self.database_url = self.database_url.replace("@db:5433/", "@db:5432/")
        else:
            self.database_url = self.database_url.replace("@db:5432/", "@localhost:5433/")
            self.database_url = self.database_url.replace("@db:5433/", "@localhost:5433/")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

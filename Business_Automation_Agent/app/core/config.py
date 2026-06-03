from functools import lru_cache
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "change-me-in-production-use-a-long-random-string"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Business Automation Agent"
    APP_ENV: str = "development"
    DEBUG: bool = False

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    DATABASE_URL: str = (
        "postgresql://postgres:postgres@postgres:5432/business_automation"
    )
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    SECRET_KEY: str = DEFAULT_SECRET_KEY
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_S3_BUCKET: str = ""
    PRESIGNED_URL_EXPIRE_SECONDS: int = 86400

    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = ""
    ALERT_EMAIL: str = ""

    @model_validator(mode="after")
    def validate_critical_secrets(self) -> Self:
        errors: list[str] = []

        if self.SECRET_KEY == DEFAULT_SECRET_KEY:
            errors.append(
                "SECRET_KEY must not use the default value; "
                "set a strong random secret in the environment"
            )
        if not self.STRIPE_WEBHOOK_SECRET.strip():
            errors.append(
                "STRIPE_WEBHOOK_SECRET must not be empty; "
                "set the Stripe webhook signing secret in the environment"
            )
        if not self.DATABASE_URL.strip():
            errors.append(
                "DATABASE_URL must not be empty; "
                "set the PostgreSQL connection URL in the environment"
            )

        if errors:
            raise ValueError("; ".join(errors))

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

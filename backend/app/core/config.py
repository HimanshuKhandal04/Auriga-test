from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./parkflow.db"
    jwt_secret_key: str = "replace-this-in-development"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    parking_rate_card_path: Optional[str] = None
    parking_rate_card_format: Optional[str] = None
    parking_first_hour_rate: float = 5.0
    parking_additional_hour_rate: float = 3.0
    parking_daily_cap: float = 30.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

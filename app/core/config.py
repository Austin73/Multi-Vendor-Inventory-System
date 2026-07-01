from pydantic_settings import BaseSettings, SettingsConfigDict
from os import getenv

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Multi-Vendor Inventory System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str =  getenv(
        "DATABASE_URL",
        "https:localhost",
    )

    API_V1_PREFIX: str = "/api/v1"


settings = Settings()

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("APP_ENV", "development")
    app_port: int = int(os.getenv("APP_PORT", "8000"))


settings = Settings()

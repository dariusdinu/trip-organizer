import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("TRIP_ORGANIZER_APP_NAME", "Trip Organizer API")
    database_url: str = os.getenv(
        "TRIP_ORGANIZER_DATABASE_URL",
        "sqlite:///data/trip_organizer.db",
    )
    cors_origins: str = os.getenv(
        "TRIP_ORGANIZER_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )


settings = Settings()

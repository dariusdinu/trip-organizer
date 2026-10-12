from pathlib import Path

from sqlalchemy.engine import make_url

from backend.app.core.config import settings
from backend.app.database.base import Base
from backend.app.database.session import engine
from backend.app.models import Category, Destination, Place  # noqa: F401


def initialize_database() -> None:
    """Create the configured database schema for local development."""
    database_url = make_url(settings.database_url)
    if database_url.get_backend_name() == "sqlite" and database_url.database not in (None, ":memory:"):
        database_path = Path(database_url.database)
        database_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    initialize_database()
    print(f"Database schema initialized at {settings.database_url}")

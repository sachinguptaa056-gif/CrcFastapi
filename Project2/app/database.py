import os
from typing import Generator
from sqlmodel import Session, SQLModel, create_engine

# Database file location (SQLite)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///events.db")

# Engine creation with SQLite check_same_thread disabled for FastAPI multi-threading
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def create_db_and_tables() -> None:
    """Create all database tables on application startup."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependency for providing a transactional SQLModel database session."""
    with Session(engine) as session:
        yield session

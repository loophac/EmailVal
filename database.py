from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = "sqlite:///./database.db"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread":
                  False},  # required for SQLite multithreaded access
    pool_size=20,  # Max number of persistent connections
    max_overflow=30,  # Extra connections allowed during bursts
    pool_timeout=15  # Wait time for a connection before raising an error
)


def init_db():
    from models import APIKey, AdminUser, Log  # ensure model classes are loaded
    SQLModel.metadata.create_all(engine)


def get_session():
    return Session(engine)

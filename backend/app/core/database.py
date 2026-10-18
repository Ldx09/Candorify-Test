from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

IS_SQLITE = settings.DATABASE_URL.startswith("sqlite")

# SQLite (temporary local testing) needs check_same_thread; Postgres gets a 5-second connect timeout
# so the server fails fast instead of hanging when the database is unreachable.
connect_args = {"check_same_thread": False} if IS_SQLITE else {"connect_timeout": 5}

# Connection pool: up to 5 open connections reused across requests (+5 extra under load).
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """Gives each request its own database session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_connection() -> None:
    """Runs on boot. Stops the server with a clear message if the database can't be reached."""
    safe_url = make_url(settings.DATABASE_URL).render_as_string(hide_password=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise RuntimeError(
            f"\n\n  DATABASE CONNECTION FAILED\n  URL: {safe_url}\n  Reason: {exc.__class__.__name__}: "
            f"{str(exc).splitlines()[0]}\n  Check DATABASE_URL in backend/.env and that the database is running.\n"
        ) from None
    print(f"INFO:     Database connected: {safe_url}")
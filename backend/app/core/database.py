from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# Adjust sqlite URL if needed for async or pooling
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        settings.DATABASE_URL, 
        connect_args=connect_args,
        echo=False
    )

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):
        # WAL + NORMAL sync: ~10-50x faster bulk ingestion and concurrent reads during writes
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA foreign_keys=OFF")
        cur.close()
else:
    # PostgreSQL configuration with connection pooling
    # If postgres:// is provided (e.g. older Render urls), normalize to postgresql://
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    # Auto-detect installed PostgreSQL DBAPI drivers (psycopg v3 vs psycopg2)
    try:
        import psycopg  # noqa: F401
        has_psycopg = True
    except ImportError:
        has_psycopg = False

    try:
        import psycopg2  # noqa: F401
        has_psycopg2 = True
    except ImportError:
        has_psycopg2 = False

    # Automatically adapt driver prefix if the requested one is not installed
    if "postgresql+psycopg://" in db_url and not has_psycopg and has_psycopg2:
        db_url = db_url.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)
    elif "postgresql+psycopg2://" in db_url and not has_psycopg2 and has_psycopg:
        db_url = db_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    elif db_url.startswith("postgresql://") and "+psycopg" not in db_url:
        # Default postgresql:// uses psycopg2 in SQLAlchemy 2.0; if missing, fallback to psycopg v3
        if not has_psycopg2 and has_psycopg:
            db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=10,
        max_overflow=20,
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency for obtaining a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

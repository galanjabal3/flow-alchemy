from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL or "postgresql://flowalchemy:flowalchemy_dev_password@localhost:5432/flowalchemy"

# SQLite (memory or file) does not accept a QueuePool pool_size; only pass
# pool options that apply to the selected dialect.
_engine_options = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    _engine_options["connect_args"] = {"check_same_thread": False}
else:
    _engine_options["pool_size"] = 5

engine = create_engine(DATABASE_URL, **_engine_options)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

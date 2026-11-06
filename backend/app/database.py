import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

logger = logging.getLogger("uvicorn")

# Try initializing MySQL Engine; Fallback to SQLite if MySQL is offline
try:
    engine = create_engine(
        settings.MYSQL_DATABASE_URL, 
        pool_pre_ping=True,
        pool_recycle=3600
    )
    # Test connection
    with engine.connect() as conn:
        logger.info("Successfully connected to MySQL database: %s", settings.MYSQL_DB)
except Exception as e:
    logger.warning("MySQL connection failed (%s). Falling back to SQLite database: %s", e, settings.SQLITE_DATABASE_URL)
    engine = create_engine(
        settings.SQLITE_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

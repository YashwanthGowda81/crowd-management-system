import os
from pydantic_settings import BaseSettings

_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_default_sqlite_path = os.path.join(_backend_dir, "crowd_system.db").replace("\\", "/")
_default_sqlite_url = f"sqlite:///{_default_sqlite_path}"

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Based Real-Time Crowd Management & Safety System"
    VERSION: str = "2.4.0"
    API_PREFIX: str = "/api"
    
    # Database Configuration (MySQL with SQLite fallback)
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "yashu")
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: str = os.getenv("MYSQL_PORT", "3306")
    MYSQL_DB: str = os.getenv("MYSQL_DB", "crowd_db")
    
    MYSQL_DATABASE_URL: str = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    SQLITE_DATABASE_URL: str = os.getenv("SQLITE_DATABASE_URL", _default_sqlite_url)
    
    # Computer Vision Settings
    YOLO_MODEL_NAME: str = "yolov8n.pt"  # Ultralytics lightweight model
    CONFIDENCE_THRESHOLD: float = 0.45
    IOU_THRESHOLD: float = 0.50
    
    # JWT & Auth
    SECRET_KEY: str = "ai_crowd_surveillance_secret_key_2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 Hours

    class Config:
        case_sensitive = True

settings = Settings()

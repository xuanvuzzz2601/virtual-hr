from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./virtual_hr.db"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    GEMINI_API_KEY: str = ""
    UPLOAD_DIR: str = "./uploads"
    APP_NAME: str = "Virtual HR Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # JWT
    JWT_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # App
    APP_ENV: str = "development"

    # Gemini AI (legacy)
    GEMINI_API_KEY: Optional[str] = None

    # Groq AI
    GROQ_API_KEY: Optional[str] = None

    # SMTP Email Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None
    SMTP_FROM_NAME: str = "SportGuard Support"

    class Config:
        env_file = ".env"
        extra = "ignore"   # silently ignore any unknown keys in .env


settings = Settings()

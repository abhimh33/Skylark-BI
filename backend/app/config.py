"""
Configuration module for the SkyLark BI Agent.
Handles environment variables and application settings.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # monday.com API Configuration
    MONDAY_API_KEY: str
    MONDAY_API_URL: str = "https://api.monday.com/v2"
    DEALS_BOARD_ID: str
    WORK_ORDERS_BOARD_ID: str
    
    # Groq API Configuration
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    
    # Application Settings
    APP_NAME: str = "SkyLark BI Agent"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # API Rate Limiting
    MONDAY_RATE_LIMIT_PER_MINUTE: int = 60
    GROQ_RATE_LIMIT_PER_MINUTE: int = 30
    
    # Pagination Settings
    MONDAY_PAGE_SIZE: int = 100

    # Cache TTL (seconds)
    CACHE_BOARD_TTL: int = 180       # monday.com board data: 3 min
    CACHE_RESPONSE_TTL: int = 300    # AI response cache: 5 min
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

"""
Dependency injection for FastAPI.
"""

from functools import lru_cache
from typing import Generator
import logging

from .config import get_settings, Settings
from .monday_client import MondayClient
from .data_cleaner import DataCleaner
from .ai_service import AIService

logger = logging.getLogger(__name__)


def get_monday_client() -> MondayClient:
    """Get monday.com client instance."""
    return MondayClient()


def get_data_cleaner() -> DataCleaner:
    """Get data cleaner instance."""
    return DataCleaner()


def get_ai_service() -> AIService:
    """Get AI service instance."""
    return AIService()


# Export settings getter
__all__ = [
    "get_settings",
    "get_monday_client",
    "get_data_cleaner",
    "get_ai_service",
]

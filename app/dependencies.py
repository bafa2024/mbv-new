"""
Shared dependencies for the application
"""

import logging
from typing import Dict, Any
from fastapi import Depends, HTTPException, status
from app.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def get_settings():
    """Get application settings"""
    return settings


def validate_mapbox_credentials():
    """Validate that Mapbox credentials are configured"""
    if not settings.MAPBOX_TOKEN or not settings.MAPBOX_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mapbox credentials not configured"
        )
    return True


# In-memory storage (to be replaced with database in production)
class AppState:
    def __init__(self):
        self.active_visualizations: Dict[str, Any] = {}
        self.active_sessions: Dict[str, Any] = {}
        self.batch_jobs: Dict[str, Any] = {}
        self.active_datasets: Dict[str, Any] = {}
        self.uploaded_files: Dict[str, Any] = {}


app_state = AppState()


def get_app_state() -> AppState:
    """Get application state"""
    return app_state
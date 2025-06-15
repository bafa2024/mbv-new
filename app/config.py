"""
Configuration settings for the Weather Visualization Platform
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Base paths
    BASE_DIR: Path = Path(__file__).parent.parent.absolute()
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    PROCESSED_DIR: Path = BASE_DIR / "processed"
    RECIPE_DIR: Path = BASE_DIR / "recipes"
    STATIC_DIR: Path = BASE_DIR / "static"
    TEMPLATES_DIR: Path = BASE_DIR / "templates"
    
    # Mapbox configuration
    MAPBOX_TOKEN: str = ""
    MAPBOX_PUBLIC_TOKEN: str = ""
    MAPBOX_USERNAME: str = ""
    
    # AWS configuration (optional)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    
    # Application configuration
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # File upload limits
    MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500MB
    MAX_BATCH_SIZE: int = 10
    
    # Tile processing
    DEFAULT_TILE_SIZE: int = 512
    MAX_ZOOM_LEVEL: int = 10
    MIN_ZOOM_LEVEL: int = 0
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Create directories if they don't exist
for dir_path in [
    settings.UPLOAD_DIR,
    settings.PROCESSED_DIR,
    settings.RECIPE_DIR,
    settings.STATIC_DIR,
    settings.TEMPLATES_DIR
]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Default tileset configuration
DEFAULT_TILESET = {
    "id": "mapbox.gfs-winds",
    "name": "Global Weather Data (Default)",
    "type": "default",
    "format": "raster-array"
}
"""
Custom exceptions for the application
"""

from typing import Optional


class WeatherVisualizationError(Exception):
    """Base exception for the application"""
    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class FileProcessingError(WeatherVisualizationError):
    """Raised when file processing fails"""
    pass


class MapboxError(WeatherVisualizationError):
    """Raised when Mapbox operations fail"""
    pass


class TilesetCreationError(MapboxError):
    """Raised when tileset creation fails"""
    pass


class DatasetCreationError(MapboxError):
    """Raised when dataset creation fails"""
    pass


class ValidationError(WeatherVisualizationError):
    """Raised when input validation fails"""
    pass


class AuthenticationError(WeatherVisualizationError):
    """Raised when authentication fails"""
    pass
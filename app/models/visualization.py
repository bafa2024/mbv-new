"""
Visualization-related Pydantic models
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class ProcessingStatus(BaseModel):
    """Processing status model"""
    job_id: str
    status: str
    message: str
    tileset_id: Optional[str] = None
    visualization_url: Optional[str] = None
    error: Optional[str] = None


class VisualizationStatus(BaseModel):
    """Visualization status model"""
    job_id: str
    status: str
    tileset_id: Optional[str] = None
    mapbox_tileset: Optional[str] = None
    error: Optional[str] = None
    warning: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    format: Optional[str] = None
    actual_format: Optional[str] = None
    requested_format: Optional[str] = None
    wind_components: Optional[Dict[str, str]] = None
    scalar_vars: Optional[List[str]] = None
    vector_pairs: Optional[List[Dict[str, str]]] = None
    source_layer: Optional[str] = None
    publish_job_id: Optional[str] = None
    visualization_type: Optional[str] = None
    use_client_animation: Optional[bool] = None
    session_id: Optional[str] = None
    bounds: Optional[Dict[str, float]] = None
    center: Optional[List[float]] = None
    zoom: Optional[int] = None
    batch_id: Optional[str] = None


class WindDataResponse(BaseModel):
    """Wind data response model"""
    success: bool
    grid: Optional[Dict[str, Any]] = None
    u_component: Optional[List[List[float]]] = None
    v_component: Optional[List[List[float]]] = None
    speed: Optional[List[List[float]]] = None
    metadata: Optional[Dict[str, Any]] = None
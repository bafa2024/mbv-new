"""
Upload-related Pydantic models
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Upload response model"""
    success: bool
    job_id: Optional[str] = None
    tileset_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    wind_components: Optional[Dict[str, str]] = None
    bounds: Optional[Dict[str, float]] = None
    center: Optional[List[float]] = None
    zoom: Optional[int] = None
    visualization_type: Optional[str] = None
    requested_format: Optional[str] = None
    scalar_vars: Optional[List[str]] = None
    vector_pairs: Optional[List[Dict[str, str]]] = None
    previews: Optional[Dict[str, Any]] = None
    wind_data: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    batch_id: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class BatchUploadResponse(BaseModel):
    """Batch upload response model"""
    batch_id: str
    total_files: int
    processed_files: int
    status: str
    files: List[Dict[str, Any]]
    errors: List[Dict[str, str]]
    created_at: Optional[str] = None
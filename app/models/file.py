"""
File-related Pydantic models
"""

from typing import Optional, Dict, List, Any
from datetime import datetime
from pydantic import BaseModel


class FileInfo(BaseModel):
    """File information model"""
    id: str
    filename: str
    original_filename: str
    size: int
    upload_date: str
    status: str
    metadata: Optional[Dict[str, Any]] = None
    tileset_id: Optional[str] = None
    job_id: Optional[str] = None
    processing_status: Optional[str] = None
    error: Optional[str] = None
    batch_id: Optional[str] = None


class FileListResponse(BaseModel):
    """File list response model"""
    success: bool
    files: List[FileInfo]
    total: int


class FileDeleteResponse(BaseModel):
    """File deletion response model"""
    success: bool
    message: str
    file_id: Optional[str] = None


class BatchDeleteResponse(BaseModel):
    """Batch file deletion response model"""
    success: bool
    deleted: List[str]
    errors: List[Dict[str, str]]
    message: str
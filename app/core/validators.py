"""
Input validation functions
"""

from typing import Dict, Any
from fastapi import UploadFile


def validate_netcdf_file(file: UploadFile) -> Dict[str, Any]:
    """Validate that uploaded file is a valid NetCDF file"""
    if not file.filename.endswith('.nc'):
        return {
            'valid': False,
            'error': 'Only NetCDF (.nc) files are allowed'
        }
    
    # Validate filename doesn't contain problematic characters
    invalid_chars = ['/', '\\', '..', '~', '|', '>', '<', ':', '*', '?', '"']
    if any(char in file.filename for char in invalid_chars):
        return {
            'valid': False,
            'error': 'Filename contains invalid characters'
        }
    
    # Check if filename is too long
    if len(file.filename) > 255:
        return {
            'valid': False,
            'error': 'Filename is too long (max 255 characters)'
        }
    
    return {'valid': True}


def validate_tileset_name(name: str) -> Dict[str, Any]:
    """Validate tileset name according to Mapbox requirements"""
    if not name:
        return {'valid': True}  # Empty is valid, will be auto-generated
    
    # Check length
    if len(name) > 32:
        return {
            'valid': False,
            'error': 'Tileset name must be 32 characters or less'
        }
    
    # Check characters
    import re
    if not re.match(r'^[a-z0-9\-_]+$', name.lower()):
        return {
            'valid': False,
            'error': 'Tileset name can only contain lowercase letters, numbers, hyphens, and underscores'
        }
    
    return {'valid': True}


def validate_batch_size(file_count: int, max_size: int) -> Dict[str, Any]:
    """Validate batch upload size"""
    if file_count > max_size:
        return {
            'valid': False,
            'error': f'Too many files. Maximum batch size is {max_size}'
        }
    
    if file_count == 0:
        return {
            'valid': False,
            'error': 'No files provided'
        }
    
    return {'valid': True}
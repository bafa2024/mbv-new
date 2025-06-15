"""
Data formatting utilities
"""

from typing import Any, Dict, List
import json
from datetime import datetime


def format_file_size(bytes_size: int) -> str:
    """Format file size in human-readable format"""
    if bytes_size == 0:
        return '0 Bytes'
    
    k = 1024
    sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
    i = 0
    
    while bytes_size >= k and i < len(sizes) - 1:
        bytes_size /= k
        i += 1
    
    return f"{bytes_size:.2f} {sizes[i]}"


def format_datetime(dt: datetime) -> str:
    """Format datetime for display"""
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def format_tileset_id(raw_id: str) -> str:
    """Format tileset ID for display"""
    # Remove username prefix if present
    if '.' in raw_id:
        return raw_id.split('.', 1)[1]
    return raw_id


def format_wind_speed(speed: float, units: str = "m/s") -> str:
    """Format wind speed with units"""
    return f"{speed:.1f} {units}"


def format_coordinates(lat: float, lon: float) -> str:
    """Format coordinates for display"""
    lat_dir = 'N' if lat >= 0 else 'S'
    lon_dir = 'E' if lon >= 0 else 'W'
    
    return f"{abs(lat):.3f}°{lat_dir}, {abs(lon):.3f}°{lon_dir}"


def format_json_response(data: Any, pretty: bool = False) -> str:
    """Format data as JSON string"""
    if pretty:
        return json.dumps(data, indent=2, sort_keys=True)
    else:
        return json.dumps(data, separators=(',', ':'))


def format_error_message(error: Exception) -> Dict[str, Any]:
    """Format error for API response"""
    return {
        "error": str(error),
        "type": type(error).__name__,
        "timestamp": datetime.now().isoformat()
    }


def format_metadata_summary(metadata: Dict[str, Any]) -> str:
    """Format metadata dictionary as summary string"""
    if not metadata:
        return "No metadata available"
    
    parts = []
    
    if 'dimensions' in metadata:
        dims = metadata['dimensions']
        parts.append(f"Dimensions: {', '.join(f'{k}={v}' for k, v in dims.items())}")
    
    if 'variables' in metadata:
        vars_count = len(metadata['variables'])
        parts.append(f"Variables: {vars_count}")
    
    return " | ".join(parts)
"""
NetCDF file processing logic
"""

import xarray as xr
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from app.dependencies import logger, settings
from app.core.wind_analyzer import find_wind_components, extract_wind_data_for_client


async def process_netcdf_file(
    file_path: Path,
    job_id: str,
    create_tileset: bool,
    tileset_name: Optional[str],
    visualization_type: str,
    batch_id: Optional[str] = None
) -> Dict[str, Any]:
    """Process NetCDF file and extract metadata"""
    try:
        # Convert Path to string for xarray
        file_path_str = str(file_path)
        ds = xr.open_dataset(file_path_str)
        
        # Log file info
        logger.info(f"Opened NetCDF file: {file_path}")
        logger.info(f"Dimensions: {dict(ds.dims)}")
        logger.info(f"Variables: {list(ds.data_vars)}")
        logger.info(f"Coordinates: {list(ds.coords)}")
        
        # Extract metadata
        metadata = {
            "dimensions": dict(ds.dims),
            "variables": list(ds.data_vars),
            "coordinates": list(ds.coords),
            "attributes": dict(ds.attrs)
        }
        
        # Find wind components
        wind_components = find_wind_components(ds)
        
        # Get all scalar variables
        scalar_vars = []
        vector_pairs = []
        
        if wind_components:
            logger.info(f"Found wind components: {wind_components}")
            vector_pairs.append({
                "name": "wind",
                "u": wind_components["u"],
                "v": wind_components["v"]
            })
            scalar_vars = [v for v in ds.data_vars if v not in [wind_components["u"], wind_components["v"]]]
        else:
            logger.warning("No wind components found in NetCDF file")
            scalar_vars = list(ds.data_vars)
        
        # Get bounds
        bounds = get_dataset_bounds(ds)
        if bounds:
            logger.info(f"Dataset bounds: {bounds}")
        else:
            logger.warning("Could not determine dataset bounds")
        
        # Calculate optimal center and zoom
        center, zoom = calculate_optimal_view(bounds) if bounds else (None, None)
        
        # Get data previews
        previews = get_data_previews(ds)
        
        # Extract wind data for client-side animation
        wind_data = None
        if wind_components and visualization_type in ['raster-array', 'client-side']:
            wind_data = extract_wind_data_for_client(ds, wind_components, bounds)
        
        # Generate tileset ID
        tileset_id = generate_tileset_id(file_path, tileset_name, batch_id)
        
        # Store visualization info
        from app.dependencies import get_app_state
        app_state = get_app_state()
        
        app_state.active_visualizations[job_id] = {
            "file_path": str(file_path),
            "tileset_id": tileset_id,
            "metadata": metadata,
            "wind_components": wind_components,
            "bounds": bounds,
            "center": center,
            "zoom": zoom,
            "visualization_type": visualization_type,
            "requested_format": "raster-array" if visualization_type == "raster-array" else "vector",
            "created_at": datetime.now().isoformat(),
            "status": "processing",
            "scalar_vars": scalar_vars,
            "vector_pairs": vector_pairs,
            "session_id": job_id,
            "batch_id": batch_id
        }
        
        ds.close()
        
        return {
            "success": True,
            "job_id": job_id,
            "tileset_id": tileset_id,
            "metadata": metadata,
            "wind_components": wind_components,
            "bounds": bounds,
            "center": center,
            "zoom": zoom,
            "visualization_type": visualization_type,
            "requested_format": "raster-array" if visualization_type == "raster-array" else "vector",
            "scalar_vars": scalar_vars,
            "vector_pairs": vector_pairs,
            "previews": previews,
            "wind_data": wind_data,
            "session_id": job_id,
            "batch_id": batch_id
        }
        
    except Exception as e:
        logger.error(f"Error in process_netcdf_file: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Try to provide helpful error message
        error_msg = str(e)
        if "No such file" in error_msg:
            error_msg = "NetCDF file could not be read. Please ensure it's a valid NetCDF format."
        elif "decode" in error_msg:
            error_msg = "NetCDF file encoding error. The file may be corrupted."
        
        raise Exception(error_msg)


def get_dataset_bounds(ds: xr.Dataset) -> Optional[Dict[str, float]]:
    """Extract geographic bounds from dataset"""
    try:
        # Find lat/lon coordinates
        lat_names = ['lat', 'latitude', 'y', 'Y']
        lon_names = ['lon', 'longitude', 'x', 'X']
        
        lat_coord = None
        lon_coord = None
        
        for name in lat_names:
            if name in ds.coords:
                lat_coord = ds.coords[name]
                break
                
        for name in lon_names:
            if name in ds.coords:
                lon_coord = ds.coords[name]
                break
        
        if lat_coord is not None and lon_coord is not None:
            return {
                "north": float(lat_coord.max()),
                "south": float(lat_coord.min()),
                "east": float(lon_coord.max()),
                "west": float(lon_coord.min())
            }
    except:
        pass
    
    return None


def calculate_optimal_view(bounds: Dict[str, float]) -> Tuple[List[float], int]:
    """Calculate optimal center point and zoom level for given bounds"""
    if not bounds:
        return None, None
    
    # Calculate center
    center_lon = (bounds['east'] + bounds['west']) / 2
    center_lat = (bounds['north'] + bounds['south']) / 2
    
    # Calculate zoom level based on bounds
    lat_diff = bounds['north'] - bounds['south']
    lon_diff = bounds['east'] - bounds['west']
    
    # Use the larger dimension to calculate zoom
    max_diff = max(lat_diff, lon_diff)
    
    # Approximate zoom calculation
    if max_diff > 180:
        zoom = 1
    elif max_diff > 90:
        zoom = 2
    elif max_diff > 45:
        zoom = 3
    elif max_diff > 22:
        zoom = 4
    elif max_diff > 11:
        zoom = 5
    elif max_diff > 5.5:
        zoom = 6
    elif max_diff > 2.8:
        zoom = 7
    elif max_diff > 1.4:
        zoom = 8
    else:
        zoom = 9
    
    return [center_lon, center_lat], zoom


def get_data_previews(ds: xr.Dataset, max_vars: int = 5) -> Dict[str, Any]:
    """Get preview statistics for variables"""
    previews = {}
    
    for var_name in list(ds.data_vars)[:max_vars]:
        try:
            var_data = ds[var_name]
            if 'time' in var_data.dims:
                var_data = var_data.isel(time=0)
            
            values = var_data.values.flatten()
            values = values[~np.isnan(values)]  # Remove NaN values
            
            if len(values) > 0:
                previews[var_name] = {
                    "min": float(np.min(values)),
                    "max": float(np.max(values)),
                    "mean": float(np.mean(values)),
                    "units": var_data.attrs.get("units", "unknown")
                }
        except:
            pass
    
    return previews


def generate_tileset_id(
    file_path: Path,
    tileset_name: Optional[str],
    batch_id: Optional[str]
) -> str:
    """Generate a unique tileset ID"""
    if not tileset_name:
        filename = file_path.stem.split('_', 1)[-1]  # Remove job_id prefix
        tileset_name = ''.join(c for c in filename if c.isalnum() or c in '-_')[:20]
        if not tileset_name:
            tileset_name = "weather_data"
    
    # Sanitize tileset name
    tileset_name = tileset_name.lower()
    tileset_name = ''.join(c if c.isalnum() or c in '-_' else '_' for c in tileset_name)
    tileset_name = '_'.join(part for part in tileset_name.split('_') if part)
    
    # Create short timestamp
    timestamp = datetime.now().strftime("%m%d%H%M")
    prefix = "wx"
    
    # Add batch indicator if part of batch
    if batch_id:
        prefix = f"wxb_{batch_id[:8]}"
    
    # Ensure tileset ID is under 32 chars
    max_name_length = 32 - len(prefix) - len(timestamp) - 2  # 2 for underscores
    if len(tileset_name) > max_name_length:
        tileset_name = tileset_name[:max_name_length]
    
    tileset_id = f"{prefix}_{tileset_name}_{timestamp}"
    tileset_id = tileset_id.lower()
    tileset_id = ''.join(c for c in tileset_id if c.isalnum() or c in '-_')
    tileset_id = tileset_id[:32].rstrip('_')
    
    logger.info(f"Generated tileset_id: {tileset_id}")
    
    return tileset_id
"""
Wind data analysis and extraction
"""

import numpy as np
import xarray as xr
from typing import Dict, Optional, Tuple, Any
from app.dependencies import logger


def find_wind_components(ds: xr.Dataset) -> Optional[Dict[str, str]]:
    """Find U and V wind components in dataset"""
    u_patterns = ['u', 'u10', 'u_wind', 'u_component', 'eastward', 'ugrd', 'u-component', 'uas']
    v_patterns = ['v', 'v10', 'v_wind', 'v_component', 'northward', 'vgrd', 'v-component', 'vas']
    
    u_var = None
    v_var = None
    
    for var in ds.data_vars:
        var_lower = var.lower()
        if not u_var and any(p in var_lower for p in u_patterns):
            u_var = var
        elif not v_var and any(p in var_lower for p in v_patterns):
            v_var = var
    
    if u_var and v_var:
        return {"u": u_var, "v": v_var}
    return None


def extract_wind_data_for_client(
    ds: xr.Dataset,
    wind_components: Dict[str, str],
    bounds: Optional[Dict[str, float]]
) -> Optional[Dict[str, Any]]:
    """Extract wind data in a format suitable for client-side animation"""
    try:
        u_var = ds[wind_components['u']]
        v_var = ds[wind_components['v']]
        
        # Handle time dimension
        if 'time' in u_var.dims:
            u_var = u_var.isel(time=0)
            v_var = v_var.isel(time=0)
        
        # Get coordinate arrays
        lats = ds.lat.values if 'lat' in ds else ds.latitude.values
        lons = ds.lon.values if 'lon' in ds else ds.longitude.values
        
        # Subsample if data is too large
        max_points = 150
        lat_step = max(1, len(lats) // max_points)
        lon_step = max(1, len(lons) // max_points)
        
        lats_sub = lats[::lat_step]
        lons_sub = lons[::lon_step]
        u_sub = u_var.values[::lat_step, ::lon_step]
        v_sub = v_var.values[::lat_step, ::lon_step]
        
        # Handle NaN values
        u_sub = np.nan_to_num(u_sub, nan=0.0)
        v_sub = np.nan_to_num(v_sub, nan=0.0)
        
        # Calculate speed
        speed = np.sqrt(u_sub**2 + v_sub**2)
        
        return {
            "grid": {
                "lats": lats_sub.tolist(),
                "lons": lons_sub.tolist(),
                "shape": list(u_sub.shape)
            },
            "u_component": u_sub.tolist(),
            "v_component": v_sub.tolist(),
            "speed": speed.tolist(),
            "metadata": {
                "units": u_var.attrs.get('units', 'm/s')
            }
        }
    except Exception as e:
        logger.error(f"Error extracting wind data for client: {e}")
        return None


def calculate_wind_statistics(
    ds: xr.Dataset,
    wind_components: Dict[str, str]
) -> Dict[str, float]:
    """Calculate wind statistics from dataset"""
    try:
        u_var = ds[wind_components['u']]
        v_var = ds[wind_components['v']]
        
        # Handle time dimension
        if 'time' in u_var.dims:
            u_var = u_var.isel(time=0)
            v_var = v_var.isel(time=0)
        
        # Calculate speed
        speed = np.sqrt(u_var.values**2 + v_var.values**2)
        
        # Remove NaN values for statistics
        speed_flat = speed.flatten()
        speed_flat = speed_flat[~np.isnan(speed_flat)]
        
        if len(speed_flat) > 0:
            return {
                "min_speed": float(np.min(speed_flat)),
                "max_speed": float(np.max(speed_flat)),
                "mean_speed": float(np.mean(speed_flat)),
                "std_speed": float(np.std(speed_flat))
            }
        else:
            return {
                "min_speed": 0.0,
                "max_speed": 0.0,
                "mean_speed": 0.0,
                "std_speed": 0.0
            }
    except Exception as e:
        logger.error(f"Error calculating wind statistics: {e}")
        return {
            "min_speed": 0.0,
            "max_speed": 0.0,
            "mean_speed": 0.0,
            "std_speed": 0.0
        }
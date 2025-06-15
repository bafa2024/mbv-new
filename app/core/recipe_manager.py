"""
Recipe file management for tilesets
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from app.dependencies import settings, logger


def save_recipe_info(tileset_id: str, result: Dict[str, Any], viz_info: Dict[str, Any]):
    """Save recipe information for future reference"""
    recipe_path = settings.RECIPE_DIR / f"recipe_{tileset_id}.json"
    
    # Ensure we capture the actual format that was created
    actual_format = result.get('format', 'vector')
    if 'raster' in str(result.get('tileset_id', '')).lower() or result.get('format') == 'raster-array':
        actual_format = 'raster-array'
    
    recipe_data = {
        "tileset_id": tileset_id,
        "mapbox_tileset": result['tileset_id'],
        "created": datetime.now().isoformat(),
        "format": actual_format,
        "actual_format": actual_format,
        "requested_format": viz_info.get('requested_format', 'vector'),
        "source_layer": result.get('source_layer', 'weather_data' if actual_format == 'vector' else '10winds'),
        "recipe_id": result.get('recipe_id'),
        "publish_job_id": result.get('publish_job_id'),
        "scalar_vars": viz_info.get("scalar_vars", []),
        "vector_pairs": viz_info.get("vector_pairs", []),
        "visualization_type": viz_info.get('visualization_type', 'vector'),
        "is_raster_array": actual_format == 'raster-array',
        "use_client_animation": viz_info.get('use_client_animation', False),
        "session_id": viz_info.get('session_id'),
        "bounds": viz_info.get('bounds'),
        "center": viz_info.get('center'),
        "zoom": viz_info.get('zoom'),
        "batch_id": viz_info.get('batch_id')
    }
    
    try:
        with open(str(recipe_path), 'w') as f:
            json.dump(recipe_data, f, indent=2)
        logger.info(f"Saved recipe info to {recipe_path}")
    except Exception as e:
        logger.error(f"Failed to save recipe: {e}")


def get_recipe_info(tileset_id: str) -> Optional[Dict[str, Any]]:
    """Get recipe information for a tileset"""
    # Extract short ID if full tileset ID provided
    tileset_short_id = tileset_id.split('.')[-1] if '.' in tileset_id else tileset_id
    
    # Look for recipe files
    recipe_files = list(settings.RECIPE_DIR.glob(f"*{tileset_short_id}*.json"))
    
    if not recipe_files:
        return None
    
    try:
        with open(recipe_files[0], 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading recipe file: {e}")
        return None


def delete_recipe(tileset_id: str) -> bool:
    """Delete recipe file for a tileset"""
    recipe_files = list(settings.RECIPE_DIR.glob(f"*{tileset_id}*.json"))
    
    deleted = False
    for recipe_file in recipe_files:
        try:
            recipe_file.unlink()
            logger.info(f"Deleted recipe: {recipe_file}")
            deleted = True
        except Exception as e:
            logger.error(f"Error deleting recipe: {e}")
    
    return deleted